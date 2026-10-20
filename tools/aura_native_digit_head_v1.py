#!/usr/bin/env python3
"""AURA native ten-class probability head for pre-event digit forecasting.

An explicitly trained softmax classifier, not a hash of symbolic/oracle output.
Its features are available at forecast time; independent CSPRNG outcomes should
still be unpredictable, and this head has no physical precognition authority.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any


MODEL_SCHEMA = "janus.aura.native_digit_head.model.v1"
FORECAST_SCHEMA = "janus.aura.native_digit_head.forecast.v1"
TRAINING_RECEIPT_SCHEMA = "janus.aura.native_digit_head.training_receipt.v1"
OBSERVATION_SCHEMA = "janus.aura.native_digit_head.external_observation.v1"
CLASS_COUNT = 10
TRIALS = 100
TRAIN_TRIALS = 80
VALIDATION_TRIALS = 20
EPOCHS = 400
LEARNING_RATE = 0.3
L2 = 0.4
UNIFORM_BLEND = 0.5
FEATURE_NAMES = ["bias", "phase10_sin", "phase10_cos", "phase100_sin", "phase100_cos"]
# Immutable baseline outcomes committed in CHRONOS-002, in trial order.
FROZEN_TRAINING_OUTCOMES_SHA256 = "2eda20d5d0fd3c368b7359562ebfd811941b0058394ca033a73cb9e6df80f529"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def features(trial_zero_based: int) -> tuple[float, ...]:
    """Schedule-only covariates, never target digits or future wall timestamps."""
    if type(trial_zero_based) is not int or not 0 <= trial_zero_based < TRIALS:
        raise ValueError("TRIAL_INDEX_OUT_OF_RANGE")
    phase10 = 2 * math.pi * (trial_zero_based % 10) / 10
    phase100 = 2 * math.pi * trial_zero_based / 100
    return 1.0, math.sin(phase10), math.cos(phase10), math.sin(phase100), math.cos(phase100)


def softmax(logits: list[float]) -> list[float]:
    high = max(logits)
    expv = [math.exp(x - high) for x in logits]
    denom = math.fsum(expv)
    return [x / denom for x in expv]


def probabilities(weights: list[list[float]], trial_index: int) -> list[float]:
    x = features(trial_index)
    if len(weights) != CLASS_COUNT or any(len(row) != len(x) for row in weights):
        raise ValueError("TEN_CLASS_WEIGHT_MATRIX_REQUIRED")
    logits = [math.fsum(w * v for w, v in zip(row, x)) for row in weights]
    p = softmax(logits)
    # Predeclared conservative shrinkage, fixed before the validation set.
    return [(1 - UNIFORM_BLEND) * value + UNIFORM_BLEND / CLASS_COUNT for value in p]


def point_choice(p: list[float]) -> int:
    return max(range(CLASS_COUNT), key=lambda d: (p[d], -d))


def scored_rows(weights: list[list[float]], labels: list[int], *, offset: int) -> dict[str, float]:
    if not labels:
        raise ValueError("LABELS_REQUIRED")
    losses, briers, hits = [], [], 0
    for j, label in enumerate(labels):
        p = probabilities(weights, offset + j)
        losses.append(-math.log(p[label]))
        briers.append(math.fsum((p[k] - int(k == label)) ** 2 for k in range(CLASS_COUNT)) / CLASS_COUNT)
        hits += int(point_choice(p) == label)
    return {
        "logloss_nats": round(math.fsum(losses) / len(labels), 12),
        "mean_multiclass_brier": round(math.fsum(briers) / len(labels), 12),
        "point_accuracy": round(hits / len(labels), 12),
        "uniform_reference_logloss_nats": round(math.log(CLASS_COUNT), 12),
        "uniform_reference_mean_brier": 0.09,
    }


def extract_historical_outcomes(record: Any, *, fitted_at_ns: int) -> list[int]:
    if not isinstance(record, dict) or record.get("schema") != "janus.aura.chronos.digits.result.v1":
        raise ValueError("HISTORICAL_RESULT_SCHEMA_REQUIRED")
    if record.get("source") != "BASELINE_CYCLE_NOT_AURA":
        raise ValueError("FROZEN_CONTROL_TRAINING_SOURCE_REQUIRED")
    rows = record.get("observations")
    if not isinstance(rows, list) or len(rows) != TRIALS:
        raise ValueError("EXACTLY_100_HISTORICAL_ROWS_REQUIRED")
    labels = []
    previous_ns = -1
    for expected_trial, row in enumerate(rows, 1):
        if not isinstance(row, dict) or row.get("trial") != expected_trial:
            raise ValueError("NONCANONICAL_TRIAL_ORDER")
        outcome = row.get("outcome")
        when_ns = row.get("draw_unix_ns")
        if type(outcome) is not int or not 0 <= outcome < CLASS_COUNT:
            raise ValueError("HISTORICAL_OUTCOME_INVALID")
        if type(when_ns) is not int or not previous_ns < when_ns < fitted_at_ns:
            raise ValueError("TRAINING_FUTURE_DATA_OR_TIMESTAMP_REORDER")
        previous_ns = when_ns
        labels.append(outcome)
    if digest(labels) != FROZEN_TRAINING_OUTCOMES_SHA256:
        raise ValueError("FROZEN_TRAINING_OUTCOMES_DRIFT")
    return labels


def fit(history: dict[str, Any], *, trained_at_ns: int | None = None) -> dict[str, Any]:
    trained_at_ns = time.time_ns() if trained_at_ns is None else trained_at_ns
    labels = extract_historical_outcomes(history, fitted_at_ns=trained_at_ns)
    training = labels[:TRAIN_TRIALS]
    weights = [[0.0] * len(FEATURE_NAMES) for _ in range(CLASS_COUNT)]
    for _ in range(EPOCHS):
        gradients = [[0.0] * len(FEATURE_NAMES) for _ in range(CLASS_COUNT)]
        for i, label in enumerate(training):
            x = features(i)
            ps = softmax([math.fsum(w * f for w, f in zip(row, x)) for row in weights])
            for k in range(CLASS_COUNT):
                error = ps[k] - int(k == label)
                for j, fj in enumerate(x):
                    gradients[k][j] += error * fj
        for k in range(CLASS_COUNT):
            for j in range(len(FEATURE_NAMES)):
                penalty = 0 if j == 0 else L2 * weights[k][j]
                weights[k][j] -= LEARNING_RATE * (gradients[k][j] / TRAIN_TRIALS + penalty)
    # Fix model coefficients after training; preserve holdout independence.
    weights = [[round(value, 12) for value in row] for row in weights]
    model = {
        "schema": MODEL_SCHEMA,
        "model_id": "AURA_NATIVE_SOFTMAX_10CLASS_V1",
        "built_at_utc": utc_now(),
        "built_at_unix_ns": trained_at_ns,
        "weights": weights,
        "feature_names": FEATURE_NAMES,
        "training_source": "CHRONOS_002_PRIOR_BASELINE_CONTROL_ONLY",
        "training_outcomes_sha256": FROZEN_TRAINING_OUTCOMES_SHA256,
        "training_trials": list(range(1, TRAIN_TRIALS + 1)),
        "heldout_validation_trials": list(range(TRAIN_TRIALS + 1, TRIALS + 1)),
        "hyperparameters_frozen": {"epochs": EPOCHS, "learning_rate": LEARNING_RATE, "l2_nonbias": L2,
                                    "uniform_blend": UNIFORM_BLEND, "optimizer": "FULL_BATCH_GRADIENT_DESCENT"},
        "outcome_leakage_prohibited": True,
        "future_random_outcomes_used": False,
        "semantic_hash_digit_decoder_used": False,
        "physical_retrocausality_claimed": False,
    }
    model_wrap = {"model": model, "model_sha256": digest(model)}
    receipt = {
        "schema": TRAINING_RECEIPT_SCHEMA,
        "model_sha256": model_wrap["model_sha256"],
        "train_metrics": scored_rows(weights, training, offset=0),
        "validation_metrics_untuned": scored_rows(weights, labels[TRAIN_TRIALS:], offset=TRAIN_TRIALS),
        "validation_used_for_training_or_selection": False,
        "statistical_claim": "SINGLE_HISTORICAL_80_20_SPLIT__NO_PREDICTIVE_ABILITY_CLAIM",
    }
    return {"frozen_model": model_wrap, "training_receipt": receipt}


def checked_model(wrapper: Any) -> dict[str, Any]:
    if not isinstance(wrapper, dict) or not isinstance(wrapper.get("model"), dict):
        raise ValueError("MODEL_WRAPPER_REQUIRED")
    model = wrapper["model"]
    if model.get("schema") != MODEL_SCHEMA or digest(model) != wrapper.get("model_sha256"):
        raise ValueError("MODEL_COMMITMENT_MISMATCH")
    if model.get("model_id") != "AURA_NATIVE_SOFTMAX_10CLASS_V1":
        raise ValueError("MODEL_IDENTIFIER_MISMATCH")
    if model.get("feature_names") != FEATURE_NAMES or model.get("training_outcomes_sha256") != FROZEN_TRAINING_OUTCOMES_SHA256:
        raise ValueError("MODEL_FEATURES_OR_TRAINING_DRIFT")
    if model.get("hyperparameters_frozen") != {"epochs": EPOCHS, "learning_rate": LEARNING_RATE,
                                                  "l2_nonbias": L2, "uniform_blend": UNIFORM_BLEND,
                                                  "optimizer": "FULL_BATCH_GRADIENT_DESCENT"}:
        raise ValueError("MODEL_HYPERPARAMETERS_DRIFT")
    _ = probabilities(model["weights"], 0)
    return model


def forecast(model_wrapper: dict[str, Any], *, delay_ms: int = 1,
             as_of_ns: int | None = None) -> dict[str, Any]:
    model = checked_model(model_wrapper)
    if type(delay_ms) is not int or not 1 <= delay_ms <= 1000:
        raise ValueError("DELAY_MS_OUT_OF_RANGE")
    as_of_ns = time.time_ns() if as_of_ns is None else as_of_ns
    if as_of_ns <= model["built_at_unix_ns"]:
        raise ValueError("FORECAST_BEFORE_MODEL_FREEZE")
    rows = []
    for i in range(TRIALS):
        p = probabilities(model["weights"], i)
        rows.append({"trial": i + 1, "nominal_offset_ms_after_independent_runner_start": (i + 1) * delay_ms,
                     "probabilities_0_to_9": [round(v, 15) for v in p],
                     "digit": point_choice(p)})
    packet = {
        "schema": FORECAST_SCHEMA,
        "model_id": model["model_id"],
        "model_sha256": model_wrapper["model_sha256"],
        "prepared_at_utc": utc_now(),
        "prepared_at_unix_ns": as_of_ns,
        "predictions": rows,
        "trial_count": TRIALS,
        "minimum_interval_ms": delay_ms,
        "schedule_anchor": "INDEPENDENT_RUNNER_START_AFTER_FORECAST_COMMIT__NOT_FORECAST_TIMESTAMP",
        "millisecond_prediction_horizon_claimed": False,
        "prospective_test": True,
        "test_outcomes_present": False,
        "score_plan": "multiclass_logloss_and_mean_brier_vs_uniform; exact_one_sided_binomial_point_hits",
        "primary_alpha": 0.01,
        "hardware_clock_attestation": "NOT_PROVIDED",
        "atomic_grade_evidence_allowed": False,
        "external_rng_evidence": "PENDING_FUTURE_INDEPENDENT_SOURCE",
        "execution_authority": False,
    }
    return {"forecast": packet, "commitment_sha256": digest(packet)}


def checked_forecast(wrapper: Any) -> dict[str, Any]:
    if not isinstance(wrapper, dict) or not isinstance(wrapper.get("forecast"), dict):
        raise ValueError("FORECAST_WRAPPER_REQUIRED")
    p = wrapper["forecast"]
    if p.get("schema") != FORECAST_SCHEMA or digest(p) != wrapper.get("commitment_sha256"):
        raise ValueError("FORECAST_COMMITMENT_MISMATCH")
    rows = p.get("predictions")
    if not isinstance(rows, list) or len(rows) != TRIALS or p.get("trial_count") != TRIALS:
        raise ValueError("FORECAST_COUNT_INVALID")
    for i, row in enumerate(rows):
        if row.get("trial") != i + 1 or type(row.get("digit")) is not int or row["digit"] not in range(10):
            raise ValueError("FORECAST_DIGIT_OR_ORDER_INVALID")
        probs = row.get("probabilities_0_to_9")
        if (not isinstance(probs, list) or len(probs) != CLASS_COUNT or
                any(type(v) is not float or not 0 <= v <= 1 for v in probs) or
                abs(math.fsum(probs) - 1) > 1e-11 or point_choice(probs) != row["digit"]):
            raise ValueError("TEN_CLASS_PROBABILITY_VECTOR_INVALID")
    return p


def hardware_time_gate(attestation: Any) -> None:
    """No trusted verification key/hardware source here: do not accept mere JSON flags."""
    raise ValueError("HARDWARE_PPS_PTP_ATTESTATION_NOT_AVAILABLE__ATOMIC_GRADE_CLAIM_FORBIDDEN")


def score_external(frozen: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    """No RNG or forecast revision here; independent observer must supply labels."""
    packet = checked_forecast(frozen)
    if not isinstance(observation, dict) or observation.get("schema") != OBSERVATION_SCHEMA:
        raise ValueError("EXTERNAL_OBSERVATION_SCHEMA_REQUIRED")
    if observation.get("forecast_commitment_sha256") != frozen["commitment_sha256"]:
        raise ValueError("OUTCOME_FORECAST_COMMITMENT_MISMATCH")
    resolver = observation.get("resolver")
    if (not isinstance(resolver, str) or not resolver.strip() or
            resolver.upper().startswith(("AURA", "JANUS"))):
        raise ValueError("EXTERNAL_RESOLVER_REQUIRED")
    refs = observation.get("evidence_refs")
    if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or not x.strip() for x in refs):
        raise ValueError("EXTERNAL_EVIDENCE_REFS_REQUIRED")
    observed_at = observation.get("observed_at_unix_ns")
    if type(observed_at) is not int or observed_at <= packet["prepared_at_unix_ns"]:
        raise ValueError("FUTURE_EVENT_MUST_FOLLOW_FORECAST")
    outcomes = observation.get("outcomes")
    if (not isinstance(outcomes, list) or len(outcomes) != TRIALS or
            any(type(d) is not int or d < 0 or d >= CLASS_COUNT for d in outcomes)):
        raise ValueError("EXACTLY_100_VALID_EXTERNAL_OUTCOMES_REQUIRED")
    losses, briers, hits = [], [], 0
    for row, outcome in zip(packet["predictions"], outcomes):
        p = row["probabilities_0_to_9"]
        losses.append(-math.log(p[outcome]))
        briers.append(math.fsum((p[k] - int(k == outcome)) ** 2 for k in range(CLASS_COUNT)) / CLASS_COUNT)
        hits += int(row["digit"] == outcome)
    tail = math.fsum(math.comb(TRIALS, k) * (0.1 ** k) * (0.9 ** (TRIALS - k))
                     for k in range(hits, TRIALS + 1))
    return {
        "schema": "janus.aura.native_digit_head.external_score.v1",
        "forecast_commitment_sha256": frozen["commitment_sha256"],
        "source_model_sha256": packet["model_sha256"],
        "observer_as_asserted": resolver,
        "evidence_refs_as_asserted": refs,
        "independent_evidence_authentication": "NOT_IMPLEMENTED",
        "trials": TRIALS,
        "hits": hits,
        "exact_one_sided_point_accuracy_p_value": round(tail, 12),
        "preregistered_alpha": packet["primary_alpha"],
        "chance_advantage_flag": "NEEDS_INDEPENDENT_REPLICATION" if tail <= packet["primary_alpha"] else "NOT_DETECTED",
        "mean_multiclass_logloss_nats": round(math.fsum(losses) / TRIALS, 12),
        "mean_multiclass_brier": round(math.fsum(briers) / TRIALS, 12),
        "uniform_reference_logloss_nats": round(math.log(CLASS_COUNT), 12),
        "uniform_reference_mean_brier": 0.09,
        "chance_point_hit_rate": 0.1,
        "physical_retrocausality_established": False,
        "atomic_grade_claim_allowed": False,
    }


def write_once(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="AURA native trained 10-class forecasts; no precognition claim")
    sub = parser.add_subparsers(dest="action", required=True)
    train = sub.add_parser("train")
    train.add_argument("--history", type=Path, required=True)
    train.add_argument("--output", type=Path, required=True)
    predict = sub.add_parser("forecast")
    predict.add_argument("--model", type=Path, required=True)
    predict.add_argument("--output", type=Path, required=True)
    predict.add_argument("--delay-ms", type=int, default=1)
    predict.add_argument("--require-hardware-clock", action="store_true")
    resolve = sub.add_parser("score")
    resolve.add_argument("--forecast", type=Path, required=True)
    resolve.add_argument("--observation", type=Path, required=True)
    resolve.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "train":
        result = fit(json.loads(args.history.read_text(encoding="utf-8")))
        write_once(args.output, result)
        print(json.dumps({"phase": "TRAINED_AND_VALIDATED", "model_sha256": result["frozen_model"]["model_sha256"],
                          "validation": result["training_receipt"]["validation_metrics_untuned"]}))
    elif args.action == "forecast":
        if args.require_hardware_clock:
            hardware_time_gate(None)
        result = forecast(json.loads(args.model.read_text(encoding="utf-8"))["frozen_model"], delay_ms=args.delay_ms)
        checked_forecast(result)
        write_once(args.output, result)
        print(json.dumps({"phase": "TEN_CLASS_FORECAST_FROZEN", "commitment_sha256": result["commitment_sha256"],
                          "trials": TRIALS, "atomic_clock_verified": False, "future_draws_executed": False}))
    else:
        result = score_external(json.loads(args.forecast.read_text(encoding="utf-8")),
                                json.loads(args.observation.read_text(encoding="utf-8")))
        write_once(args.output, result)
        print(json.dumps({"phase": "EXTERNALLY_SUPPLIED_OUTCOMES_SCORED", "hits": result["hits"],
                          "logloss": result["mean_multiclass_logloss_nats"],
                          "brier": result["mean_multiclass_brier"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
