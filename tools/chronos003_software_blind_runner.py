#!/usr/bin/env python3
"""One-shot post-commit OS-CSPRNG challenge against a frozen AURA NATIVE10 head.

This runner is separate from AURA and imports no oracle code. It does not
authenticate a hardware timebase or an independent external laboratory.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import time
from typing import Any, Callable


SCHEMA = "janus.aura.chronos003.software_blind_result.v1"
MARKER_SCHEMA = "janus.aura.chronos003.software_one_shot_marker.v1"
FORECAST_SHA256 = "c1dd23d52fc283b53f300a9b349845491d8a56a0ad024ff773cd9bf71741e129"
MODEL_SHA256 = "c0525ea5c052f8e2c255ff2ade9be66be11e94af034176263c39187d9656f66e"
FORECAST_FILE_SHA256 = "bbe6345d5a8d8da2f224315be3999b3ea601f64d4fed2a34cd6c6d82f2813388"
MODEL_FILE_SHA256 = "f0367bd7321de4a28957ad82cbffc171ff73628339d2dfe1ec81672e2b839655"
NATIVE_SOURCE_SHA256 = "f0c976d06b3394ee7de692bcbc7c0e9f6578bb504f5dce78cf7bfa6e334e1b96"
FROZEN_GIT_COMMIT = "4162f4beb5a927ef45eacbf109aefdb6dad1cfc8"
TRIALS = 100
MIN_DELAY_NS = 1_000_000


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def hash_json(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def independently_reconstruct_probabilities(weights: list[list[float]], index: int) -> list[float]:
    angle_ten = (2 * math.pi * (index % 10)) / 10
    angle_hundred = (2 * math.pi * index) / 100
    x = [1, math.sin(angle_ten), math.cos(angle_ten), math.sin(angle_hundred), math.cos(angle_hundred)]
    z = [math.fsum(w * v for w, v in zip(row, x)) for row in weights]
    exp_z = [math.exp(zk - max(z)) for zk in z]
    denominator = math.fsum(exp_z)
    return [0.5 * (v / denominator) + 0.05 for v in exp_z]


def validate_before_entropy(forecast_path: Path, model_path: Path, marker_path: Path,
                            native_source_path: Path) -> dict[str, Any]:
    expected_files = [
        (forecast_path, FORECAST_FILE_SHA256, "FORECAST_FILE_DRIFT"),
        (model_path, MODEL_FILE_SHA256, "MODEL_FILE_DRIFT"),
        (native_source_path, NATIVE_SOURCE_SHA256, "NATIVE_SOURCE_DRIFT"),
    ]
    for path, expected, message in expected_files:
        if hash_file(path) != expected:
            raise ValueError(message)
    forecast_wrapper = json.loads(forecast_path.read_text(encoding="utf-8"))
    model_wrapper = json.loads(model_path.read_text(encoding="utf-8"))["frozen_model"]
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker.get("schema") != MARKER_SCHEMA or marker.get("experiment") != "CHRONOS-003-SOFTONLY-NATIVE10-R1":
        raise ValueError("SOFTWARE_ONE_SHOT_MARKER_INVALID")
    if marker.get("forecast_sha256") != FORECAST_SHA256 or marker.get("model_sha256") != MODEL_SHA256:
        raise ValueError("MARKER_FROZEN_COMMITMENTS_MISMATCH")
    if marker.get("freeze_git_commit") != FROZEN_GIT_COMMIT:
        raise ValueError("MARKER_FROZEN_GIT_COMMIT_MISMATCH")
    if marker.get("new_outcomes_generated_before_trigger") is not False:
        raise ValueError("MARKER_PRIOR_OUTCOME_ASSERTION_REQUIRED")
    if marker.get("primary_run_policy") != "FIRST_GITHUB_RUN_ATTEMPT_ONLY_NO_SUBSTITUTION":
        raise ValueError("NONCANONICAL_PRIMARY_RUN_POLICY")
    if (forecast_wrapper.get("commitment_sha256") != FORECAST_SHA256 or
            hash_json(forecast_wrapper.get("forecast")) != FORECAST_SHA256):
        raise ValueError("FORECAST_INTERNAL_SHA_MISMATCH")
    forecast = forecast_wrapper["forecast"]
    if (forecast.get("schema") != "janus.aura.native_digit_head.forecast.v1" or
            forecast.get("trial_count") != TRIALS or forecast.get("model_sha256") != MODEL_SHA256 or
            forecast.get("test_outcomes_present") is not False or
            forecast.get("hardware_clock_attestation") != "NOT_PROVIDED"):
        raise ValueError("FORECAST_HARDWARE_OR_TRAINING_PROVENANCE_DRIFT")
    if model_wrapper.get("model_sha256") != MODEL_SHA256 or hash_json(model_wrapper.get("model")) != MODEL_SHA256:
        raise ValueError("MODEL_INTERNAL_SHA_MISMATCH")
    model = model_wrapper["model"]
    if (model.get("model_id") != "AURA_NATIVE_SOFTMAX_10CLASS_V1" or
            model.get("future_random_outcomes_used") is not False or
            model.get("semantic_hash_digit_decoder_used") is not False or
            len(model.get("weights", [])) != 10):
        raise ValueError("MODEL_PROVENANCE_INVALID")
    rows = forecast.get("predictions")
    if not isinstance(rows, list) or len(rows) != TRIALS:
        raise ValueError("EXPECTED_100_FROZEN_PROBABILITY_VECTORS")
    for i, row in enumerate(rows):
        expected = independently_reconstruct_probabilities(model["weights"], i)
        p = row.get("probabilities_0_to_9")
        if (row.get("trial") != i + 1 or
                row.get("nominal_offset_ms_after_independent_runner_start") != i + 1 or
                not isinstance(p, list) or len(p) != 10 or
                any(type(x) is not float or abs(x - expected[j]) > 1e-12 for j, x in enumerate(p)) or
                abs(math.fsum(p) - 1) > 1e-11):
            raise ValueError("FROZEN_TEN_CLASS_PROBABILITIES_NOT_REPRODUCIBLE")
        choice = max(range(10), key=lambda d: (p[d], -d))
        if type(row.get("digit")) is not int or row["digit"] != choice:
            raise ValueError("FROZEN_POINT_DIGIT_NOT_REPRODUCIBLE")
    if time.time_ns() <= forecast["prepared_at_unix_ns"]:
        raise ValueError("SOFTWARE_DRAW_BEFORE_PRECOMMIT")
    return {"marker": marker, "forecast": forecast, "forecast_wrapper": forecast_wrapper}


def draw_after_validation(preverified: dict[str, Any], *,
                          randbelow: Callable[[int], int] = secrets.randbelow,
                          sleep: Callable[[float], None] = time.sleep,
                          monotonic_ns: Callable[[], int] = time.perf_counter_ns,
                          wall_ns: Callable[[], int] = time.time_ns,
                          source: str = "GITHUB_HOSTED_OS_CSPRNG_NOT_HARDWARE_ATTESTED") -> dict[str, Any]:
    if source not in {"GITHUB_HOSTED_OS_CSPRNG_NOT_HARDWARE_ATTESTED", "SYNTHETIC_UNIT_TEST_NOT_REAL"}:
        raise ValueError("UNSUPPORTED_RUN_PROVENANCE")
    validated_at_ns = wall_ns()
    if validated_at_ns <= preverified["forecast"]["prepared_at_unix_ns"]:
        raise ValueError("DRAW_TIME_BEFORE_FROZEN_FORECAST")
    observations = []
    for i in range(TRIALS):
        before = monotonic_ns()
        sleep(MIN_DELAY_NS / 1_000_000_000)
        ready = monotonic_ns()
        outcome = randbelow(10)
        drawn_at = wall_ns()
        if type(outcome) is not int or not 0 <= outcome <= 9:
            raise ValueError("OS_CSPRNG_DIGIT_OUT_OF_RANGE")
        if ready < before or drawn_at <= validated_at_ns:
            raise ValueError("RUNNER_CLOCK_OR_DRAW_ORDER_INVALID")
        observations.append({
            "trial": i + 1, "outcome": outcome, "wait_monotonic_ns": ready - before,
            "before_wait_monotonic_ns": before, "ready_monotonic_ns": ready,
            "draw_utc_ns": drawn_at,
        })
    result = {
        "schema": SCHEMA,
        "experiment": preverified["marker"]["experiment"],
        "source": source,
        "primary_run_policy": preverified["marker"]["primary_run_policy"],
        "forecast_sha256": FORECAST_SHA256,
        "model_sha256": MODEL_SHA256,
        "forecast_freeze_git_commit": FROZEN_GIT_COMMIT,
        "runner_git_sha_as_asserted": os.getenv("GITHUB_SHA", "LOCAL_SYNTHETIC_TEST_NO_GIT_SHA"),
        "github_actions_run_id_as_asserted": os.getenv("GITHUB_RUN_ID", "LOCAL_SYNTHETIC_TEST"),
        "github_actions_run_attempt_as_asserted": os.getenv("GITHUB_RUN_ATTEMPT", "LOCAL_SYNTHETIC_TEST"),
        "pre_draw_validation_utc_ns": validated_at_ns,
        "completed_at_utc": utc_now(),
        "nominal_wait_ms": 1,
        "clock": "perf_counter_ns_and_time_ns_OS_SOFTWARE_ONLY",
        "atomic_grade_timestamp_attested": False,
        "external_physical_rng_attested": False,
        "outcomes_generated_by_runner": True,
        "physical_retrocausality_established": False,
        "observations": observations,
    }
    return {"result": result, "result_sha256": hash_json(result)}


def main() -> int:
    parser = argparse.ArgumentParser(description="One post-commit blind OS-CSPRNG run; no physical clock")
    parser.add_argument("--forecast", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--marker", required=True, type=Path)
    parser.add_argument("--native-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1" or not os.environ.get("GITHUB_RUN_ID"):
        raise ValueError("REQUIRES_FIRST_GITHUB_ACTIONS_ATTEMPT_ONLY")
    checked = validate_before_entropy(args.forecast, args.model, args.marker, args.native_source)
    result = draw_after_validation(checked)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": "100_FUTURE_OS_CSPRNG_DIGITS_DRAWN_AFTER_VALIDATION",
                      "result_sha256": result["result_sha256"],
                      "clock_hardware_attested": False, "physical_retrocausality_established": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
