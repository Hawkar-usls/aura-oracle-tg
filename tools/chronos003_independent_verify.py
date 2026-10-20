#!/usr/bin/env python3
"""Standalone software-blind receipt scorer, independent of AURA and the RNG runner.

Verify raw future observations and recompute evidence metrics. It cannot prove
hardware clock quality, remote-run integrity, or physical retrocausality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_FORECAST_SHA = "c1dd23d52fc283b53f300a9b349845491d8a56a0ad024ff773cd9bf71741e129"
EXPECTED_FREEZE_COMMIT = "4162f4beb5a927ef45eacbf109aefdb6dad1cfc8"
RESULT_SCHEMA = "janus.aura.chronos003.software_blind_result.v1"
TRIALS = 100


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def exact_binomial_upper(hits: int) -> float:
    return math.fsum(math.comb(100, i) * (0.1 ** i) * (0.9 ** (100 - i))
                     for i in range(hits, 101))


def verify(frozen: Any, receipt: Any, *, expected_source: str = "GITHUB_HOSTED_OS_CSPRNG_NOT_HARDWARE_ATTESTED") -> dict[str, Any]:
    if not isinstance(frozen, dict) or not isinstance(frozen.get("forecast"), dict):
        raise ValueError("INDEPENDENT_FORECAST_WRAPPER_REQUIRED")
    f = frozen["forecast"]
    if (frozen.get("commitment_sha256") != EXPECTED_FORECAST_SHA or
            digest(f) != EXPECTED_FORECAST_SHA or
            f.get("model_sha256") != "c0525ea5c052f8e2c255ff2ade9be66be11e94af034176263c39187d9656f66e"):
        raise ValueError("INDEPENDENT_FORECAST_COMMITMENT_MISMATCH")
    predictions = f.get("predictions")
    if not isinstance(predictions, list) or len(predictions) != TRIALS:
        raise ValueError("INDEPENDENT_FORECAST_100_REQUIRED")
    if not isinstance(receipt, dict) or not isinstance(receipt.get("result"), dict):
        raise ValueError("INDEPENDENT_RESULT_WRAPPER_REQUIRED")
    result = receipt["result"]
    if receipt.get("result_sha256") != digest(result):
        raise ValueError("INDEPENDENT_RECEIPT_SHA_MISMATCH")
    if (result.get("schema") != RESULT_SCHEMA or
            result.get("experiment") != "CHRONOS-003-SOFTONLY-NATIVE10-R1" or
            result.get("source") != expected_source or
            result.get("primary_run_policy") != "FIRST_GITHUB_RUN_ATTEMPT_ONLY_NO_SUBSTITUTION" or
            result.get("forecast_sha256") != EXPECTED_FORECAST_SHA or
            result.get("forecast_freeze_git_commit") != EXPECTED_FREEZE_COMMIT or
            result.get("atomic_grade_timestamp_attested") is not False or
            result.get("external_physical_rng_attested") is not False or
            result.get("physical_retrocausality_established") is not False):
        raise ValueError("INDEPENDENT_PROVENANCE_AND_HARDWARE_GATE_MISMATCH")
    if expected_source == "GITHUB_HOSTED_OS_CSPRNG_NOT_HARDWARE_ATTESTED" and (
            result.get("github_actions_run_attempt_as_asserted") != "1" or
            not str(result.get("github_actions_run_id_as_asserted", "")).isdigit()):
        raise ValueError("INDEPENDENT_FIRST_RUN_ATTESTATION_NOT_PRESENT")
    events = result.get("observations")
    if not isinstance(events, list) or len(events) != TRIALS:
        raise ValueError("INDEPENDENT_100_OBSERVATIONS_REQUIRED")
    prior_monotonic, prior_utc = None, None
    hits, logloss, brier, frequencies, waits = 0, [], [], [0] * 10, []
    validation_ns = result.get("pre_draw_validation_utc_ns")
    if type(validation_ns) is not int or validation_ns <= f["prepared_at_unix_ns"]:
        raise ValueError("INDEPENDENT_PRE_DRAW_VALIDATION_TIME_INVALID")
    for i, (event, prediction) in enumerate(zip(events, predictions), 1):
        if not isinstance(event, dict) or type(event.get("trial")) is not int or event["trial"] != i:
            raise ValueError("INDEPENDENT_NONCANONICAL_EVENT_ORDER")
        digit = event.get("outcome")
        if type(digit) is not int or digit not in range(10):
            raise ValueError("INDEPENDENT_DIGIT_INVALID")
        before, ready, utc, delay = (event.get("before_wait_monotonic_ns"),
                                      event.get("ready_monotonic_ns"), event.get("draw_utc_ns"),
                                      event.get("wait_monotonic_ns"))
        if any(type(x) is not int for x in (before, ready, utc, delay)):
            raise ValueError("INDEPENDENT_TIMESTAMPS_INVALID")
        if ready <= before or delay != ready - before or utc <= validation_ns:
            raise ValueError("INDEPENDENT_NEGATIVE_OR_PRECOMMIT_TIMING")
        if prior_monotonic is not None and (before <= prior_monotonic or utc <= prior_utc):
            raise ValueError("INDEPENDENT_DRAW_ORDER_INVERTED")
        prior_monotonic, prior_utc = ready, utc
        p = prediction.get("probabilities_0_to_9")
        if (prediction.get("trial") != i or not isinstance(p, list) or len(p) != 10 or
                any(type(value) is not float or value <= 0 or value >= 1 for value in p) or
                abs(math.fsum(p) - 1) > 1e-11):
            raise ValueError("INDEPENDENT_PROBABILITY_VECTOR_INVALID")
        choice = max(range(10), key=lambda j: (p[j], -j))
        if type(prediction.get("digit")) is not int or prediction["digit"] != choice:
            raise ValueError("INDEPENDENT_POINT_CHOICE_INVALID")
        frequencies[digit] += 1
        hits += int(choice == digit)
        logloss.append(-math.log(p[digit]))
        brier.append(math.fsum((p[j] - int(j == digit)) ** 2 for j in range(10)) / 10)
        waits.append(delay)
    tail = exact_binomial_upper(hits)
    all_waits_above_1ms = all(v >= 1_000_000 for v in waits)
    return {
        "schema": "janus.aura.chronos003.independent_software_audit.v1",
        "result_sha256": receipt["result_sha256"],
        "forecast_sha256": EXPECTED_FORECAST_SHA,
        "score_independently_recomputed": True,
        "first_run_provenance_as_asserted": result.get("github_actions_run_id_as_asserted"),
        "trials": TRIALS,
        "hits": hits,
        "expected_hits_null": 10,
        "exact_one_sided_p": round(tail, 12),
        "predeclared_alpha": 0.01,
        "null_hypothesis": "INDEPENDENT_UNIFORM_DIGITS_P_HIT_0_1",
        "point_accuracy_flag": "NEEDS_INDEPENDENT_REPLICATION_IF_VALID" if tail <= 0.01 else "NO_ABOVE_CHANCE_EVIDENCE",
        "multiclass_logloss_nats": round(math.fsum(logloss) / TRIALS, 12),
        "multiclass_brier_divided_by_ten": round(math.fsum(brier) / TRIALS, 12),
        "uniform_logloss_nats": round(math.log(10), 12),
        "uniform_brier_divided_by_ten": 0.09,
        "outcome_digit_frequencies": frequencies,
        "min_observed_wait_ms": round(min(waits) / 1_000_000, 6),
        "max_observed_wait_ms": round(max(waits) / 1_000_000, 6),
        "measured_minimum_wait_1ms_pass": all_waits_above_1ms,
        "clock_precision_or_absolute_error_attested": False,
        "physical_rng_independence_attested": False,
        "cryptographic_external_witness_attested": False,
        "hardware_gate": "BLOCKED_NO_DEVICE",
        "physical_retrocausality_established": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent audit: no AURA or runner imports")
    parser.add_argument("--forecast", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    audit = verify(json.loads(args.forecast.read_text(encoding="utf-8")),
                   json.loads(args.receipt.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(audit, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")
    print(json.dumps(audit, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
