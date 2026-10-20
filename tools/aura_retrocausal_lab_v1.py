#!/usr/bin/env python3
"""AURA Retrocausal Lab: forward forecasts and backward goal planning.

The word 'retrocausal' names a *planning perspective*, not a physical claim.
No information travels backwards in time and no action is executed here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "janus.aura.retrocausal_lab.v1"
REQUEST_SCHEMA = "janus.aura.retrocausal_lab.request.v1"
RESOLUTION_SCHEMA = "janus.aura.retrocausal_lab.resolution.v1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def utc_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("UTC_ISO8601_TIMESTAMP_REQUIRED")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_TIMESTAMP") from exc
    if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise ValueError("UTC_TIMESTAMP_REQUIRED")
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def real_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}_MUST_BE_NUMBER")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name}_MUST_BE_FINITE")
    return value


def nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def plan(request: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Use only preregistered inputs; rank *hypothetical* actions by expected utility."""
    if not isinstance(request, dict) or request.get("schema") != REQUEST_SCHEMA:
        raise ValueError("UNSUPPORTED_REQUEST_SCHEMA")
    question = nonempty(request.get("question"), "QUESTION")
    as_of = utc_time(request.get("as_of"))
    target_at = utc_time(request.get("target_at"))
    created = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not as_of < target_at:
        raise ValueError("TARGET_MUST_BE_AFTER_AS_OF")
    if as_of > created:
        raise ValueError("AS_OF_CANNOT_BE_IN_FUTURE")

    evidence = request.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("EVIDENCE_MUST_BE_LIST")
    seen_evidence: set[str] = set()
    for row in evidence:
        if not isinstance(row, dict):
            raise ValueError("EVIDENCE_MUST_BE_OBJECT")
        eid = nonempty(row.get("id"), "EVIDENCE_ID")
        if eid in seen_evidence:
            raise ValueError("DUPLICATE_EVIDENCE_ID")
        seen_evidence.add(eid)
        # BOTH availability and event time must precede the cutoff; no look-ahead.
        if utc_time(row.get("observed_at")) > as_of or utc_time(row.get("available_at")) > as_of:
            raise ValueError("FUTURE_INFORMATION_LEAKAGE")

    utilities = request.get("outcome_utilities")
    if not isinstance(utilities, dict) or len(utilities) < 2 or len(utilities) > 32:
        raise ValueError("OUTCOME_UTILITIES_REQUIRE_2_TO_32_OUTCOMES")
    values: dict[str, float] = {}
    for key, value in utilities.items():
        values[nonempty(key, "OUTCOME_ID")] = real_number(value, "UTILITY")

    actions = request.get("actions")
    if not isinstance(actions, list) or not (2 <= len(actions) <= 32):
        raise ValueError("ACTIONS_REQUIRE_2_TO_32_ITEMS")
    ids: set[str] = set()
    scored = []
    for row in actions:
        if not isinstance(row, dict):
            raise ValueError("ACTION_MUST_BE_OBJECT")
        aid = nonempty(row.get("id"), "ACTION_ID")
        if aid in ids:
            raise ValueError("DUPLICATE_ACTION_ID")
        ids.add(aid)
        probs = row.get("forecast")
        if not isinstance(probs, dict) or set(probs) != set(values):
            raise ValueError("ACTION_FORECAST_MUST_COVER_ALL_OUTCOMES")
        p = {key: real_number(probs[key], "PROBABILITY") for key in values}
        if any(v < 0 or v > 1 for v in p.values()) or abs(sum(p.values()) - 1) > 1e-9:
            raise ValueError("PROBABILITIES_MUST_SUM_TO_ONE")
        cost = real_number(row.get("cost", 0), "COST")
        if cost < 0:
            raise ValueError("COST_CANNOT_BE_NEGATIVE")
        expected = sum(p[k] * values[k] for k in values) - cost
        scored.append({
            "id": aid,
            "label": nonempty(row.get("label", aid), "ACTION_LABEL"),
            "forecast": p,
            "cost": cost,
            "expected_net_utility": round(expected, 12),
            "reversible": row.get("reversible") is True,
            "automatically_executable": False,
            "causal_identification": "NOT_ESTABLISHED",
        })

    baseline = nonempty(request.get("baseline_action_id"), "BASELINE_ACTION_ID")
    if baseline not in ids:
        raise ValueError("BASELINE_ACTION_NOT_FOUND")
    baseline_score = next(a["expected_net_utility"] for a in scored if a["id"] == baseline)
    for row in scored:
        row["delta_vs_baseline_assumed_model"] = round(row["expected_net_utility"] - baseline_score, 12)
    scored.sort(key=lambda a: (-a["expected_net_utility"], a["id"]))
    best = scored[0]

    prediction = {
        "schema": SCHEMA,
        "question": question,
        "as_of": iso(as_of),
        "target_at": iso(target_at),
        "prepared_at": iso(created),
        "study_class": "PROSPECTIVE_CANDIDATE" if created < target_at else "RETROSPECTIVE_SIMULATION_ONLY",
        "evidence_manifest": evidence,
        "evidence_manifest_sha256": digest(evidence),
        "outcome_utilities": values,
        "baseline_action_id": baseline,
        "action_scenarios": scored,
        "highest_scoring_scenario_id": best["id"],
        "decision_status": "HUMAN_REVIEW_REQUIRED_NO_AUTOMATION",
        "provenance": "USER_SUPPLIED_FORECASTS_NOT_LEARNED_CAUSAL_EFFECTS",
    }
    return {
        "prediction": prediction,
        "commitment_sha256": digest(prediction),
        "timestamp_attestation": "LOCAL_CLOCK_ONLY__EXTERNAL_TIMESTAMP_REQUIRED_FOR_BLIND_CLAIMS",
        "epistemic_boundary": "NO_PHYSICAL_RETROCAUSALITY_OR_FUTURE_INFORMATION_CLAIM",
    }


def resolve(frozen: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    """Score only the actual chosen action with an independent observed outcome."""
    if not isinstance(frozen, dict) or not isinstance(observation, dict):
        raise ValueError("OBJECTS_REQUIRED")
    prediction = frozen.get("prediction")
    if not isinstance(prediction, dict) or prediction.get("schema") != SCHEMA or digest(prediction) != frozen.get("commitment_sha256"):
        raise ValueError("FROZEN_PREDICTION_COMMITMENT_MISMATCH")
    if observation.get("schema") != RESOLUTION_SCHEMA:
        raise ValueError("UNSUPPORTED_RESOLUTION_SCHEMA")
    resolver = nonempty(observation.get("resolver"), "RESOLVER")
    if resolver.upper().startswith("AURA") or resolver.upper().startswith("JANUS"):
        raise ValueError("EXTERNAL_RESOLVER_REQUIRED")
    refs = observation.get("evidence_refs")
    if not isinstance(refs, list) or not refs or any(not isinstance(r, str) or not r.strip() for r in refs):
        raise ValueError("INDEPENDENT_EVIDENCE_REFERENCES_REQUIRED")
    resolved = utc_time(observation.get("resolved_at"))
    if resolved < utc_time(prediction["target_at"]):
        raise ValueError("OBSERVATION_BEFORE_TARGET")
    outcome = nonempty(observation.get("observed_outcome_id"), "OBSERVED_OUTCOME_ID")
    if outcome not in prediction["outcome_utilities"]:
        raise ValueError("UNKNOWN_OUTCOME")
    chosen = nonempty(observation.get("actual_action_id"), "ACTUAL_ACTION_ID")
    selected = next((a for a in prediction["action_scenarios"] if a["id"] == chosen), None)
    if selected is None:
        raise ValueError("ACTUAL_ACTION_NOT_IN_FORECAST")
    probs = selected["forecast"]
    brier = sum((p - int(k == outcome)) ** 2 for k, p in probs.items()) / len(probs)
    logloss = -math.log(max(probs[outcome], 1e-15))
    return {
        "schema": "janus.aura.retrocausal_lab.score.v1",
        "forecast_commitment_sha256": frozen["commitment_sha256"],
        "study_class": prediction["study_class"],
        "actual_action_id": chosen,
        "observed_outcome_id": outcome,
        "brier_multiclass_mean": round(brier, 12),
        "log_loss_nats": round(logloss, 12),
        "resolution": {"resolver": resolver, "resolved_at": iso(resolved), "evidence_refs": refs},
        "evidence_independently_verified": False,
        "counterfactual_effect_established": False,
        "physical_retrocausality_established": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="AURA backward-goal decision lab; no physical retrocausal claims")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan")
    p.add_argument("request", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--seal", action="store_true", help="Fortune Cookie encryption, key required; no plaintext output")
    r = sub.add_parser("resolve")
    r.add_argument("frozen", type=Path)
    r.add_argument("observation", type=Path)
    r.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.command == "plan":
        result = plan(json.loads(args.request.read_text(encoding="utf-8")))
        if args.seal:
            from aura_fortune_cookie import load_master_key, seal_bytes
            key = load_master_key()  # fail closed before creating output
            result = seal_bytes(canonical_bytes(result), key, label="AURA_RETROCAUSAL_PLAN_V1", public_status="FROZEN")
    else:
        result = resolve(json.loads(args.frozen.read_text(encoding="utf-8")), json.loads(args.observation.read_text(encoding="utf-8")))
    output = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as dest:  # never overwrite a frozen record
            dest.write(output)
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
