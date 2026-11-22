#!/usr/bin/env python3
"""AURA Oracle <-> TACHYON RETROBOUND R1: bounded, source-pinned advisory peer.

Accepts ONE immutable TACHYON synthetic validation receipt from DemiHead.
Produces hypotheses/questions, never predictions, learning labels or proof.
Offline only: no network, autonomous loop, key, Telegram or production side effect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

SOURCE_SCHEMA = "janus.demihead.tachyon.retrobound_r1.validation_result.v1"
OUTPUT_SCHEMA = "janus.aura.tachyon.retrobound_r1.advisory.v1"
PINNED_REPOSITORY = "Hawkar-usls/Demi_Head"
PINNED_COMMIT = "a6f84e3707828f59946be3848e0bc128d9e2b8cc"
PINNED_SOURCE_PATH = "research/tachyon/retrobound_r1_validation_result_20261123.json"
PINNED_BLOB_SHA1 = "44f422bd450e1a29d4927235502868c49955002c"
SOURCE_STATUS = "ORIGINAL_PORT_PARITY_PASS__PAIRED_SYNTHETIC_CONTROLS_PASS__PHYSICAL_RETROCAUSALITY_HOLD"
MAX_BYTES = 80000

PHYSICAL_FALSE_FIELDS = (
    "no_signalling_for_arbitrary_observable_established",
    "independently_generated_future_physical_entropy",
    "externally_frozen_early_record_before_late_choice",
    "external_timekeeping_or_hardware_run",
    "physical_retrocausality_demonstrated",
    "usable_information_from_future_demonstrated",
    "conventional_postselection_explanation_excluded",
    "independent_external_replication",
    "real_human_subject_or_consciousness_measurement",
    "production_or_frozen_R5F_adoption",
)
REQUIRED_TRUE_FIELDS = (
    "mathematical_two_boundary_bias_reproduced",
    "source_port_deterministic_golden_replayed",
    "postselection_same_exact_distribution_by_model_derivation",
    "selected_public_early_parity_invariant_by_symmetry",
)


def canonical(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(obj: object) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


def _finite(value: object) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError("NONFINITE_NUMERIC_RESULT")
    return float(value)


def load_pinned(source: Path) -> tuple[dict, bytes]:
    raw = source.read_bytes()
    if not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("SOURCE_SIZE_REJECT")
    if git_blob_sha(raw) != PINNED_BLOB_SHA1:
        raise ValueError("SOURCE_BLOB_MISMATCH__NOT_TACHYON_FROZEN_RECEIPT")
    obj = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(obj, dict):
        raise ValueError("SOURCE_OBJECT_REQUIRED")
    return obj, raw


def _paired_section(sec: object, required: bool = True) -> dict:
    if not isinstance(sec, dict):
        raise ValueError("MISSING_PAIRED_SECTION")
    n = sec.get("trajectories_per_arm")
    if type(n) is not int or n < 100:
        raise ValueError("INVALID_TRIAL_COUNT")
    if sec.get("total_accepted_trajectories") != 3 * n or sec.get("all_arms_same_future_parameter_sequence") is not True:
        raise ValueError("UNEQUAL_ARMS_OR_CHOICE_SCHEDULE")
    choices = sec.get("future_parameter_counts")
    if not isinstance(choices, dict) or set(choices) != {"-1", "1"} or any(type(x) is not int or x <= 0 for x in choices.values()):
        raise ValueError("INVALID_FUTURE_CHOICE_COUNTS")
    if sum(choices.values()) != n:
        raise ValueError("CHOICE_COUNTS_DO_NOT_MATCH")
    steps = sec.get("steps")
    rho = _finite(sec.get("rho"))
    eta = _finite(sec.get("eta"))
    if type(steps) is not int or not 1 <= steps <= 32 or not 0 <= rho < 1 or not 0 <= eta < 1:
        raise ValueError("INVALID_MODEL_PARAMETERS")
    theory = eta * rho ** steps
    if not math.isclose(_finite(sec.get("theoretical_hidden_past_future_correlation")), theory, rel_tol=0, abs_tol=1e-10):
        raise ValueError("INCONSISTENT_HIDDEN_THEORY")
    if abs(_finite(sec.get("exact_public_parity_total_variation"))) > 1e-10:
        raise ValueError("PARITY_EXACT_TV_NOT_ZERO")
    arms = sec.get("arms")
    if not isinstance(arms, dict) or set(arms) != {"two_boundary", "causal_null", "postselection"}:
        raise ValueError("REQUIRED_THREE_ARMS")
    hidden = {}
    for arm, row in arms.items():
        if not isinstance(row, dict):
            raise ValueError("BAD_ARM")
        value = _finite(row.get("hidden_past_future_correlation"))
        delta = _finite(row.get("early_public_parity_delta"))
        z = _finite(row.get("early_public_parity_z"))
        cost = _finite(row.get("forward_draws_per_accepted"))
        if abs(value) > 1 or abs(delta) > 1 or abs(z) > 100 or cost < 1:
            raise ValueError("INVALID_ARM_RANGE")
        if arm != "postselection" and cost != 1.0:
            raise ValueError("NONPOSTSELECTION_COST_MISMATCH")
        hidden[arm] = value
    diff = hidden["two_boundary"] - hidden["postselection"]
    dkey = "paired_hidden_two_boundary_minus_postselection" if required else "paired_difference"
    if not math.isclose(_finite(sec.get(dkey)), diff, rel_tol=0, abs_tol=1e-9):
        raise ValueError("PAIRED_DIFFERENCE_MISMATCH")
    sekey = "paired_difference_standard_error" if required else "paired_difference_se"
    se = _finite(sec.get(sekey))
    if se <= 0:
        raise ValueError("INVALID_PAIRED_UNCERTAINTY")
    if not math.isclose(_finite(sec.get("paired_difference_z")), diff / se, rel_tol=0, abs_tol=1e-7):
        raise ValueError("PAIRED_Z_INCONSISTENT")
    if not math.isclose(_finite(sec.get("theoretical_expected_postselection_draws_per_accepted")), 1 + eta, rel_tol=0, abs_tol=1e-10):
        raise ValueError("COST_THEORY_MISMATCH")
    return {"n": n, "rho": rho, "eta": eta, "steps": steps, "theory": theory,
            "paired_difference": diff, "paired_standard_error": se,
            "paired_z": diff / se, "observed_hidden_correlations": hidden,
            "public_parity_tv": 0.0,
            "observed_forward_draws_per_postselected_history": _finite(arms["postselection"]["forward_draws_per_accepted"])}


def validate_source(obj: dict) -> dict:
    if obj.get("schema") != SOURCE_SCHEMA or obj.get("status") != SOURCE_STATUS:
        raise ValueError("SOURCE_SCHEMA_OR_STATUS_REJECT")
    implementation = obj.get("implementation")
    if not isinstance(implementation, dict) or implementation.get("repository") != PINNED_REPOSITORY:
        raise ValueError("UNTRUSTED_UPSTREAM_REPOSITORY")
    if implementation.get("production_models_changed") is not False:
        raise ValueError("PRODUCTION_MUTATION_REJECT")
    science = obj.get("scientific_interpretation")
    if not isinstance(science, dict):
        raise ValueError("SCIENCE_GATE_MISSING")
    if any(science.get(k) is not False for k in PHYSICAL_FALSE_FIELDS):
        raise ValueError("PHYSICAL_OR_PRODUCTION_CLAIM_PROMOTION_REJECT")
    if any(science.get(k) is not True for k in REQUIRED_TRUE_FIELDS):
        raise ValueError("MISSING_IN_MODEL_CONTROLS")
    if science.get("claim_ceiling") != "CLASSICAL_SYNTHETIC_MATHEMATICAL_VALIDATION_ONLY":
        raise ValueError("CLAIM_CEILING_MISMATCH")
    evidence = obj.get("validation_evidence")
    if not isinstance(evidence, dict) or any(evidence.get(k, {}).get("conclusion") != "success" for k in ("push", "pull_request")):
        raise ValueError("CI_EVIDENCE_REQUIRED")
    if evidence.get("unit_tests_passed") != 16 or evidence.get("unit_tests_total") != 16:
        raise ValueError("UNIT_TEST_RECEIPT_REJECT")
    if any(evidence.get(k, {}).get("passed") != 11 for k in ("common_choice_paired_main_checks", "common_choice_paired_alternative_checks")):
        raise ValueError("PAIRED_CI_GATES_MISSING")
    return {"default": _paired_section(obj.get("paired_default")),
            "alternative": _paired_section(obj.get("paired_alternative"), False)}


def make_advisory(obj: dict, raw: bytes) -> dict:
    if git_blob_sha(raw) != PINNED_BLOB_SHA1:
        raise ValueError("INPUT_DIGEST_NOT_PINNED")
    if not isinstance(obj, dict) or obj != json.loads(raw.decode("utf-8-sig")):
        raise ValueError("SOURCE_OBJECT_BYTES_MISMATCH")
    metrics = validate_source(obj)
    primary = metrics["default"]
    # All scores are descriptive statistics, NOT calibrated physical forecast probabilities.
    packet = {
        "schema": OUTPUT_SCHEMA,
        "peer": "AURA_ORACLE__HYPOTHESIS_DISCRIMINATION",
        "mode": "OFFLINE_READ_ONLY_ADVISORY",
        "source": {
            "repository": PINNED_REPOSITORY,
            "commit_sha": PINNED_COMMIT,
            "path": PINNED_SOURCE_PATH,
            "git_blob_sha1": PINNED_BLOB_SHA1,
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "source_json_canonical_sha256": digest(obj),
            "source_kind": "DEMIHEAD_TACHYON_R1_SYNTHETIC_CI_RECEIPT",
            "external_physical_witness": False,
        },
        "five_axis_spiral": {
            "D1_TEMPORAL_ORDER": "OFFLINE_B_IS_GIVEN_BEFORE_TWO_BOUNDARY_SAMPLING",
            "D2_MODEL_FIT": "TWO_BOUNDARY_AND_POSTSELECTION_SHARE_EXACT_PATH_LAW",
            "D3_EARLY_OBSERVABLE": "SELECTED_SPIN_PARITY_TV_ZERO_BY_SYMMETRY",
            "D4_PROVENANCE": "SOURCE_PINNED_DEMIHEAD_CI__NO_EXTERNAL_PHYSICAL_TIMESTAMPS",
            "D5_EVIDENCE_ASCENT": "PLATEAU_NO_NEW_PHYSICAL_IDENTIFIABILITY",
            "real_physical_spacetime_dimensions_measured": False,
            "origin_prime_claim": False,
        },
        "evidence_metrics": {
            "reference_default": primary,
            "reference_alternative": metrics["alternative"],
            "physical_signal_evidence": False,
            "real_future_forecast_skill_established": False,
        },
        "hypotheses": [
            {"id": "H_CAUSAL_NULL", "explanation": "Earlier external record independent of genuinely later free choice under controlled ordinary causality.", "physical_truth_probability": None, "status": "NOT_PHYSICALLY_TESTED"},
            {"id": "H_FORWARD_POSTSELECTION", "explanation": "Conditioning a forward-generated history reproduces exactly the RETROBOUND R1 conditional distribution.", "physical_truth_probability": None, "status": "MATHEMATICAL_EQUIVALENCE_SHOWN"},
            {"id": "H_RETROCAUSAL_PHYSICAL", "explanation": "A specified accessible early measurement would depend on a genuinely later independent physical choice.", "physical_truth_probability": None, "status": "UNIDENTIFIED_PREDICTION_NOT_TESTED"},
            {"id": "H_LEAKAGE_OR_SELECTION", "explanation": "Timing leaks, hidden prior choice, selection or apparatus bias can imitate physical effects.", "physical_truth_probability": None, "status": "MUST_CONTROL_PROSPECTIVELY"},
        ],
        "hypothesis_discrimination": {
            "question_id": "R2_FREEZE_BEFORE_LATE_ENTROPY",
            "question": "Can an independently frozen accessible early physical measurement discriminate a genuinely later independent setting, with every trial included and no postselection?",
            "R1_identifiability": "TWO_BOUNDARY_VS_POSTSELECTION_NOT_IDENTIFIABLE",
            "information_gain": "NOT_NUMERICALLY_ESTIMABLE_WITHOUT_PHYSICAL_LIKELIHOODS",
            "calibrated_forecast_probability": None,
            "prospective_controls": [
                "SPECIFY_PHYSICAL_READOUT_PREDICTION_DIFFERENT_FROM_FORWARD_POSTSELECTION",
                "INDEPENDENTLY_FREEZE_AND_TIMESTAMP_EARLY_READOUT_BEFORE_LATE_CHOICE",
                "GENUINELY_LATE_INDEPENDENT_PHYSICAL_ENTROPY",
                "APPEND_ONLY_ALL_TRIALS_LEDGER_INCLUDE_ABORTS",
                "PRECOMMITTED_FORWARD_AND_LEAKAGE_NULLS_WITH_MULTIPLICITY",
                "INDEPENDENT_BLINDED_EXTERNAL_CUSTODIAN",
            ],
        },
        "governance": {
            "scientific_verdict": "R1_SYNTHETIC_VALIDATION_PASS__PHYSICAL_RETROCAUSALITY_HOLD",
            "may_change_tachyon_weights": False,
            "may_submit_physical_experiment": False,
            "may_autoseal_or_publish_forecast": False,
            "may_assign_world_forecast_probability": False,
            "may_train_predictive_head": False,
            "may_resolve_own_forecast": False,
            "may_override_DemiHead_gate": False,
            "may_promote_production": False,
            "external_effect_authorized": False,
        },
    }
    packet["packet_digest_sha256"] = digest(packet)
    return packet


def verify_advisory(packet: dict) -> bool:
    if not isinstance(packet, dict) or packet.get("schema") != OUTPUT_SCHEMA:
        raise ValueError("BAD_ADVISORY_SCHEMA")
    signed = dict(packet)
    claimed = signed.pop("packet_digest_sha256", None)
    if claimed != digest(signed):
        raise ValueError("ADVISORY_DIGEST_MISMATCH")
    source = packet.get("source", {})
    if not isinstance(source, dict) or (source.get("commit_sha"), source.get("git_blob_sha1")) != (PINNED_COMMIT, PINNED_BLOB_SHA1):
        raise ValueError("UNPINNED_ADVISORY_SOURCE")
    governance = packet.get("governance", {})
    if not isinstance(governance, dict) or governance.get("scientific_verdict") != "R1_SYNTHETIC_VALIDATION_PASS__PHYSICAL_RETROCAUSALITY_HOLD":
        raise ValueError("INVALID_ADVISORY_SCIENCE_GATE")
    for key in ("may_change_tachyon_weights", "may_submit_physical_experiment",
                "may_autoseal_or_publish_forecast", "may_assign_world_forecast_probability",
                "may_train_predictive_head", "may_resolve_own_forecast",
                "may_override_DemiHead_gate", "may_promote_production",
                "external_effect_authorized"):
        if governance.get(key) is not False:
            raise ValueError("ADVISORY_AUTHORITY_PROMOTION_REJECT")
    if packet.get("hypothesis_discrimination", {}).get("calibrated_forecast_probability") is not None:
        raise ValueError("AURA_NOT_CALIBRATED_FOR_FUTURE")
    if packet.get("five_axis_spiral", {}).get("origin_prime_claim") is not False:
        raise ValueError("SPIRAL_STATE_PROMOTION_REJECT")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only source-pinned AURA <-> TACHYON advisory bridge")
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    try:
        source, raw = load_pinned(args.input)
        packet = make_advisory(source, raw)
        verify_advisory(packet)
        rendered = json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (ValueError, KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        print("AURA_TACHYON_RESEARCH_HOLD:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
