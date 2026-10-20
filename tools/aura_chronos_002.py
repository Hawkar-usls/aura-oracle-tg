#!/usr/bin/env python3
"""CHRONOS-002: millisecond-timed prospective digit-guessing experiment.

This is a measurement harness, not an atomic clock or a precognition model.
The baseline guesses are explicitly NOT forecasts produced by AURA.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import secrets
import time
from typing import Any, Callable


SCHEMA = "janus.aura.chronos.digits.v1"
N = 100
ALPHABET = 10
NULL_HIT_PROBABILITY = 1 / ALPHABET
ALPHA = 0.01


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def validate_digits(digits: Any) -> list[int]:
    if not isinstance(digits, list) or len(digits) != N:
        raise ValueError("EXACTLY_100_PREDICTIONS_REQUIRED")
    if any(type(x) is not int or x < 0 or x >= ALPHABET for x in digits):
        raise ValueError("PREDICTIONS_MUST_BE_DIGITS_0_TO_9")
    return digits


def freeze(digits: list[int], *, source: str, delay_ms: int = 1) -> dict[str, Any]:
    validate_digits(digits)
    if not isinstance(delay_ms, int) or isinstance(delay_ms, bool) or not 1 <= delay_ms <= 1000:
        raise ValueError("DELAY_MS_OUT_OF_RANGE_1_TO_1000")
    if source not in {"BASELINE_CYCLE_NOT_AURA", "EXTERNAL_ORACLE_FILE_UNVERIFIED"}:
        raise ValueError("UNSUPPORTED_SOURCE")
    record = {
        "schema": SCHEMA,
        "experiment": "CHRONOS-002",
        "protocol_version": 1,
        "prepared_at_utc": utc_now(),
        "prepared_at_unix_ns": time.time_ns(),
        "source": source,
        "predictions": list(digits),
        "trials": N,
        "outcome_generation": "secrets.randbelow(10) from OS CSPRNG, called only after freeze verification",
        "target_minimum_delay_ms_per_trial": delay_ms,
        "timing": "perf_counter_ns monotonic; time_ns wall-clock annotation; not atomic-clock-attested",
        "null_hypothesis": "independent uniform digit, Pr(hit)=0.1",
        "decision_rule": "one-sided exact binomial P(X>=hits) <= 0.01; needs independent replication",
        "multiplicity": "one preregistered 100-trial test; no optional stopping",
        "external_timestamp_attested": False,
        "physical_retrocausality_claimed": False,
    }
    return {"frozen": record, "commitment_sha256": sha256(record)}


def check_freeze(wrapper: Any) -> dict[str, Any]:
    if not isinstance(wrapper, dict) or not isinstance(wrapper.get("frozen"), dict):
        raise ValueError("FROZEN_WRAPPER_REQUIRED")
    record = wrapper["frozen"]
    if record.get("schema") != SCHEMA or sha256(record) != wrapper.get("commitment_sha256"):
        raise ValueError("FREEZE_COMMITMENT_MISMATCH")
    validate_digits(record.get("predictions"))
    if record.get("trials") != N or record.get("target_minimum_delay_ms_per_trial") not in range(1, 1001):
        raise ValueError("UNSUPPORTED_FROZEN_PROTOCOL")
    return record


def upper_binomial_tail(hits: int) -> float:
    return math.fsum(math.comb(N, k) * (NULL_HIT_PROBABILITY ** k) *
                     ((1 - NULL_HIT_PROBABILITY) ** (N - k)) for k in range(hits, N + 1))


def execute(wrapper: dict[str, Any], *,
            randbelow: Callable[[int], int] = secrets.randbelow,
            sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    """A separate phase: generate each actual outcome strictly after the freeze."""
    record = check_freeze(wrapper)
    if time.time_ns() <= record["prepared_at_unix_ns"]:
        raise ValueError("DRAW_BEFORE_FREEZE")
    delay_ms = record["target_minimum_delay_ms_per_trial"]
    observations = []
    started_utc = utc_now()
    started_ns = time.perf_counter_ns()
    for index, guess in enumerate(record["predictions"]):
        before_ns = time.perf_counter_ns()
        sleep(delay_ms / 1000.0)
        draw_ns = time.perf_counter_ns()
        # Clock stability may be imperfect; record actual intervals, not nominal ones.
        outcome = randbelow(ALPHABET)
        if type(outcome) is not int or not 0 <= outcome < ALPHABET:
            raise ValueError("INVALID_RANDOM_GENERATOR_OUTPUT")
        observations.append({
            "trial": index + 1,
            "prediction": guess,
            "outcome": outcome,
            "hit": guess == outcome,
            "actual_wait_ms": round((draw_ns - before_ns) / 1_000_000, 6),
            "draw_unix_ns": time.time_ns(),
        })
    ended_ns = time.perf_counter_ns()
    hits = sum(int(r["hit"]) for r in observations)
    p_value = upper_binomial_tail(hits)
    return {
        "schema": "janus.aura.chronos.digits.result.v1",
        "experiment": "CHRONOS-002",
        "source": record["source"],
        "forecast_commitment_sha256": wrapper["commitment_sha256"],
        "started_at_utc": started_utc,
        "completed_at_utc": utc_now(),
        "clock": {
            "monotonic": "time.perf_counter_ns",
            "nominal_resolution_ns": round(time.get_clock_info("perf_counter").resolution * 1e9),
            "atomic_or_gps_ptp_time_attested": False,
            "total_measured_ms": round((ended_ns - started_ns) / 1_000_000, 6),
            "min_measured_wait_ms": min(r["actual_wait_ms"] for r in observations),
            "max_measured_wait_ms": max(r["actual_wait_ms"] for r in observations),
        },
        "number_of_trials": N,
        "hits": hits,
        "expected_hits_under_null": N * NULL_HIT_PROBABILITY,
        "hit_rate": round(hits / N, 6),
        "exact_one_sided_p_value": round(p_value, 12),
        "alpha_predeclared": ALPHA,
        "statistical_flag": "EXCEEDS_PREREGISTERED_CHANCE_THRESHOLD_NEEDS_REPLICATION" if p_value <= ALPHA else "NO_EVIDENCE_ABOVE_CHANCE",
        "oracle_ability_established": False,
        "retrocausality_established": False,
        "external_timestamp_attested": False,
        "observations": observations,
    }


def write_new_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="CHRONOS-002 preregistered millisecond digit forecast lab")
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--provider", choices=["baseline", "oracle-file"], default="baseline")
    prepare.add_argument("--predictions", type=Path, help="JSON list of 100 digits from the real Oracle")
    prepare.add_argument("--delay-ms", type=int, default=1)
    prepare.add_argument("--output", type=Path, required=True)
    reveal = sub.add_parser("reveal")
    reveal.add_argument("--frozen", type=Path, required=True)
    reveal.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        if args.provider == "oracle-file":
            if args.predictions is None:
                parser.error("--predictions required for oracle-file")
            digits = validate_digits(json.loads(args.predictions.read_text(encoding="utf-8")))
            source = "EXTERNAL_ORACLE_FILE_UNVERIFIED"
        else:
            if args.predictions is not None:
                parser.error("--predictions only allowed with oracle-file")
            digits = list(range(ALPHABET)) * (N // ALPHABET)
            source = "BASELINE_CYCLE_NOT_AURA"
        wrapper = freeze(digits, source=source, delay_ms=args.delay_ms)
        write_new_json(args.output, wrapper)
        print(json.dumps({"phase": "FORECAST_FROZEN", "source": source,
                          "commitment_sha256": wrapper["commitment_sha256"],
                          "predictions": N, "first_draw_has_not_happened": True}))
    else:
        wrapper = json.loads(args.frozen.read_text(encoding="utf-8"))
        result = execute(wrapper)
        write_new_json(args.output, result)
        print(json.dumps({"phase": "DRAW_AND_SCORE_COMPLETED", "source": result["source"],
                          "hits": result["hits"], "expected_hits": 10,
                          "p_value": result["exact_one_sided_p_value"],
                          "clock": result["clock"],
                          "statistical_flag": result["statistical_flag"],
                          "oracle_ability_established": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
