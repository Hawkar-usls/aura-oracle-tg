#!/usr/bin/env python3
"""AURA Signal10 v2: calibrated ten-class forecasting with explicit source contracts.

No general model can learn unseen independent uniform entropy from an event index.
This module separates the uniform entropy null from a *different*, observable
signal-bearing task. It cannot authenticate physical witnesses or retrocausality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any


MODEL_SCHEMA = "janus.aura.signal10.model.v2"
FORECAST_SCHEMA = "janus.aura.signal10.forecast.v2"
HISTORY_SCHEMA = "janus.aura.signal10.history.v2"
OBSERVATION_SCHEMA = "janus.aura.signal10.observations.v2"
SOURCE_NULL = "DECLARED_INDEPENDENT_UNIFORM_NO_SIGNAL"
SOURCE_SIGNAL = "PRE_EVENT_OBSERVABLE_SIGNAL"
SOURCES = {SOURCE_NULL, SOURCE_SIGNAL}
PRIOR_PSEUDOCOUNT_PER_DIGIT = 1
N_DIGITS = 10
MIN_VALIDATION_EVENTS = 50
VALIDATION_FRACTION = 0.2


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def _integer(value: Any, lo: int | None = None) -> bool:
    return type(value) is int and (lo is None or value >= lo)


def _digit(value: Any) -> bool:
    return _integer(value, 0) and value < N_DIGITS


def check_history(history: Any, trained_at_ns: int) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(history, dict) or history.get("schema") != HISTORY_SCHEMA:
        raise ValueError("HISTORY_SCHEMA_REQUIRED")
    source = history.get("source")
    if source not in SOURCES:
        raise ValueError("EXPLICIT_PROCESS_SOURCE_REQUIRED")
    events = history.get("events")
    if not isinstance(events, list):
        raise ValueError("TRAINING_EVENTS_REQUIRED")
    if source == SOURCE_SIGNAL and len(events) < 50:
        raise ValueError("SIGNAL_TRAINING_NEEDS_AT_LEAST_50_EVENTS")
    if not _integer(trained_at_ns, 1):
        raise ValueError("TRAINING_TIMESTAMP_INVALID")
    last_outcome_ns = -1
    for trial, row in enumerate(events, 1):
        if not isinstance(row, dict) or row.get("trial") != trial:
            raise ValueError("TRAINING_TRIAL_ORDER_INVALID")
        when = row.get("outcome_observed_ns")
        if not _integer(when, 1) or not last_outcome_ns < when < trained_at_ns:
            raise ValueError("FUTURE_LABEL_OR_NONMONOTONIC_TRAINING_TIME")
        last_outcome_ns = when
        if not _digit(row.get("outcome")):
            raise ValueError("TRAINING_DIGIT_INVALID")
        if source == SOURCE_NULL:
            if row.get("signal") is not None or row.get("signal_observed_ns") is not None:
                raise ValueError("INDEPENDENT_SOURCE_MUST_NOT_CONTAIN_PREDICTIVE_SIGNAL")
        else:
            if not _digit(row.get("signal")):
                raise ValueError("PRE_EVENT_SIGNAL_REQUIRED")
            signal_time = row.get("signal_observed_ns")
            if not _integer(signal_time, 1) or not signal_time < when:
                raise ValueError("POST_EVENT_SIGNAL_LEAKAGE")
    return source, events


def fit(history: dict[str, Any], *, trained_at_ns: int) -> dict[str, Any]:
    """Fit a smoothed categorical likelihood P(outcome|pre-event signal).

    The null branch is *identically* uniform regardless of training labels.
    This is required when no signal can causally inform an independent draw.
    """
    source, events = check_history(history, trained_at_ns)
    counts = [[0 for _ in range(N_DIGITS)] for _ in range(N_DIGITS)]
    split = len(events) - max(MIN_VALIDATION_EVENTS, int(len(events) * VALIDATION_FRACTION))
    validation = events[split:] if source == SOURCE_SIGNAL and split >= 50 else []
    training = events[:split] if validation else events
    qualification = "UNIFORM_NULL" if source == SOURCE_NULL else "UNIFORM_UNQUALIFIED_INSUFFICIENT_VALIDATION"
    validation_logloss = None
    if source == SOURCE_SIGNAL:
        for row in training:
            counts[row["signal"]][row["outcome"]] += 1
        if validation:
            losses = []
            for row in validation:
                conditional_counts = counts[row["signal"]]
                conditional_n = sum(conditional_counts) + 10 * PRIOR_PSEUDOCOUNT_PER_DIGIT
                losses.append(-math.log((conditional_counts[row["outcome"]] +
                                          PRIOR_PSEUDOCOUNT_PER_DIGIT) / conditional_n))
            validation_logloss = round(math.fsum(losses) / len(losses), 12)
            qualification = ("VALIDATED_CONDITIONAL" if validation_logloss < math.log(N_DIGITS)
                             else "UNIFORM_FALLBACK_NO_VALIDATED_SKILL")
    model = {
        "schema": MODEL_SCHEMA,
        "model_id": "AURA_SIGNAL10_CALIBRATED_V2",
        "trained_at_ns": trained_at_ns,
        "source": source,
        "signal_definition": ("PRE_EVENT_CATEGORICAL_VALUE_0_TO_9" if source == SOURCE_SIGNAL else "NO_SIGNAL"),
        "counts_by_signal_and_digit": counts,
        "pseudocount_per_digit": PRIOR_PSEUDOCOUNT_PER_DIGIT,
        "training_examples": len(events),
        "coefficient_training_examples": len(training) if source == SOURCE_SIGNAL else 0,
        "validation_examples": len(validation),
        "validation_logloss_nats": validation_logloss,
        "validation_uniform_logloss_nats": round(math.log(N_DIGITS), 12),
        "qualification": qualification,
        "training_sha256": digest(history),
        "post_event_features_permitted": False,
        "future_outcomes_used": False,
        "physical_retrocausality_authority": False,
        "production_authority": False,
    }
    return {"model": model, "model_sha256": digest(model)}


def checked_model(wrapper: Any) -> dict[str, Any]:
    if not isinstance(wrapper, dict) or not isinstance(wrapper.get("model"), dict):
        raise ValueError("MODEL_WRAPPER_REQUIRED")
    model = wrapper["model"]
    if model.get("schema") != MODEL_SCHEMA or digest(model) != wrapper.get("model_sha256"):
        raise ValueError("MODEL_COMMITMENT_MISMATCH")
    if (model.get("model_id") != "AURA_SIGNAL10_CALIBRATED_V2" or
            model.get("source") not in SOURCES or
            model.get("pseudocount_per_digit") != PRIOR_PSEUDOCOUNT_PER_DIGIT or
            not _integer(model.get("trained_at_ns"), 1) or
            not _integer(model.get("training_examples"), 0) or
            not _integer(model.get("coefficient_training_examples"), 0) or
            not _integer(model.get("validation_examples"), 0) or
            model.get("post_event_features_permitted") is not False or
            model.get("future_outcomes_used") is not False or
            model.get("physical_retrocausality_authority") is not False or
            model.get("production_authority") is not False or
            not isinstance(model.get("training_sha256"), str) or
            len(model["training_sha256"]) != 64):
        raise ValueError("MODEL_AUTHORITY_OR_CONFIGURATION_DRIFT")
    counts = model.get("counts_by_signal_and_digit")
    if (not isinstance(counts, list) or len(counts) != N_DIGITS or
            any(not isinstance(row, list) or len(row) != N_DIGITS or
                any(not _integer(n, 0) for n in row) for row in counts)):
        raise ValueError("COUNTS_MATRIX_INVALID")
    if model["source"] == SOURCE_NULL and (
            any(sum(row) for row in counts) or model.get("qualification") != "UNIFORM_NULL"):
        raise ValueError("INDEPENDENT_NULL_MODEL_MUST_BE_UNIFORM")
    if (model["source"] == SOURCE_SIGNAL and (
            sum(map(sum, counts)) != model["coefficient_training_examples"] or
            model["coefficient_training_examples"] + model["validation_examples"] != model["training_examples"] or
            model.get("qualification") not in {
                "VALIDATED_CONDITIONAL", "UNIFORM_FALLBACK_NO_VALIDATED_SKILL",
                "UNIFORM_UNQUALIFIED_INSUFFICIENT_VALIDATION"})):
        raise ValueError("TRAINING_COUNTS_MISMATCH")
    return model


def probabilities(wrapper: dict[str, Any], signal: int | None) -> list[float]:
    model = checked_model(wrapper)
    if model["source"] == SOURCE_NULL:
        if signal is not None:
            raise ValueError("CSPRNG_SIGNAL_NOT_ALLOWED")
        return [0.1] * N_DIGITS
    if not _digit(signal):
        raise ValueError("OBSERVABLE_SIGNAL_REQUIRED")
    if model["qualification"] != "VALIDATED_CONDITIONAL":
        return [0.1] * N_DIGITS
    counts = model["counts_by_signal_and_digit"][signal]
    denominator = sum(counts) + N_DIGITS * PRIOR_PSEUDOCOUNT_PER_DIGIT
    return [(count + PRIOR_PSEUDOCOUNT_PER_DIGIT) / denominator for count in counts]


def forecast(wrapper: dict[str, Any], schedule: list[dict[str, Any]], *, prepared_at_ns: int) -> dict[str, Any]:
    """Freeze all ten-class probability vectors before any scheduled draw.

    `signal_observed_ns` and `target_not_before_ns` are assertions, not hardware attestation.
    """
    model = checked_model(wrapper)
    if not _integer(prepared_at_ns, model["trained_at_ns"] + 1):
        raise ValueError("FORECAST_BEFORE_MODEL_FREEZE")
    if not isinstance(schedule, list) or not 1 <= len(schedule) <= 10000:
        raise ValueError("SCHEDULE_COUNT_INVALID")
    predictions = []
    last_target = prepared_at_ns
    for trial, row in enumerate(schedule, 1):
        if not isinstance(row, dict) or row.get("trial") != trial:
            raise ValueError("SCHEDULE_TRIAL_ORDER_INVALID")
        target = row.get("target_not_before_ns")
        if not _integer(target, last_target + 1):
            raise ValueError("SCHEDULE_MUST_BE_FUTURE_ORDERED")
        last_target = target
        signal = row.get("signal")
        signal_time = row.get("signal_observed_ns")
        if model["source"] == SOURCE_NULL:
            if signal is not None or signal_time is not None:
                raise ValueError("CSPRNG_SIGNAL_NOT_ALLOWED")
        elif not _integer(signal_time, 1) or signal_time > prepared_at_ns or not _digit(signal):
            raise ValueError("SIGNAL_MUST_BE_OBSERVED_BEFORE_FORECAST")
        p = probabilities(wrapper, signal)
        predictions.append({
            "trial": trial,
            "target_not_before_ns": target,
            "signal": signal,
            "probabilities_0_to_9": p,
            # Tie-breaker fixed from trial number, independent of outcomes.
            "digit": max(range(N_DIGITS), key=lambda k: (p[k], -((k - (trial - 1) % N_DIGITS) % N_DIGITS))),
        })
    packet = {
        "schema": FORECAST_SCHEMA,
        "model_sha256": wrapper["model_sha256"],
        "source": model["source"],
        "prepared_at_ns": prepared_at_ns,
        "predictions": predictions,
        "target_digits_observed": False,
        "physical_hardware_attestation": "ABSENT",
        "retrocausality_established": False,
    }
    return {"forecast": packet, "commitment_sha256": digest(packet)}


def score(frozen: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(frozen, dict) or not isinstance(frozen.get("forecast"), dict):
        raise ValueError("FORECAST_WRAPPER_REQUIRED")
    packet = frozen["forecast"]
    if packet.get("schema") != FORECAST_SCHEMA or frozen.get("commitment_sha256") != digest(packet):
        raise ValueError("FORECAST_COMMITMENT_MISMATCH")
    if (not isinstance(observed, dict) or observed.get("schema") != OBSERVATION_SCHEMA or
            observed.get("forecast_commitment_sha256") != frozen["commitment_sha256"]):
        raise ValueError("OBSERVATION_FORECAST_MISMATCH")
    rows = observed.get("outcomes")
    predictions = packet.get("predictions")
    if not isinstance(rows, list) or not isinstance(predictions, list) or len(rows) != len(predictions):
        raise ValueError("OUTCOME_COUNT_MISMATCH")
    log_losses, briers, hits = [], [], 0
    last_observed_ns = packet["prepared_at_ns"]
    for trial, (event, prediction) in enumerate(zip(rows, predictions), 1):
        if not isinstance(event, dict) or event.get("trial") != trial or not _digit(event.get("outcome")):
            raise ValueError("OUTCOME_OR_ORDER_INVALID")
        if (not _integer(event.get("outcome_observed_ns"), prediction["target_not_before_ns"]) or
                event["outcome_observed_ns"] <= last_observed_ns):
            raise ValueError("OUTCOME_OCCURRED_BEFORE_PREDICTION")
        last_observed_ns = event["outcome_observed_ns"]
        p = prediction["probabilities_0_to_9"]
        if (not isinstance(p, list) or len(p) != N_DIGITS or
                any(type(x) is not float or x <= 0 or x >= 1 for x in p) or
                not math.isclose(sum(p), 1, abs_tol=1e-12)):
            raise ValueError("INVALID_FORECAST_PROBABILITIES")
        label = event["outcome"]
        hits += prediction["digit"] == label
        log_losses.append(-math.log(p[label]))
        briers.append(sum((p[k] - (k == label)) ** 2 for k in range(N_DIGITS)) / N_DIGITS)
    n = len(rows)
    return {
        "schema": "janus.aura.signal10.score.v2",
        "source": packet["source"],
        "forecast_commitment_sha256": frozen["commitment_sha256"],
        "trials": n,
        "hits": int(hits),
        "mean_logloss_nats": round(math.fsum(log_losses) / n, 12),
        "mean_brier_divided_by_10": round(math.fsum(briers) / n, 12),
        "uniform_logloss_nats": round(math.log(N_DIGITS), 12),
        "uniform_brier_divided_by_10": 0.09,
        "evaluation_kind": "SYNTHETIC_OR_EXTERNAL_AS_DECLARED__NOT_ATTESTED",
        "evidence_for_precognition": False,
        "retrocausality_established": False,
    }


def synthetic_control(source: str, *, n_train: int = 800, n_test: int = 300,
                      seed: int = 20261020, signal_relevance: bool = True) -> dict[str, Any]:
    """Reproducible pre-event signal positive control and independent-signal null.

    Use separate RNG streams, and never feed the test labels into `fit` or
    `forecast`. This is a simulated software test, not a physical demonstration.
    """
    if source not in SOURCES or n_train < 50 or n_test < 1:
        raise ValueError("SYNTHETIC_CONTROL_ARGUMENTS_INVALID")
    rng = random.Random(seed)
    events = []
    for i in range(n_train + n_test):
        signal = rng.randrange(10) if source == SOURCE_SIGNAL else None
        outcome = ((signal if rng.random() < 0.83 else rng.randrange(10))
                   if source == SOURCE_SIGNAL and signal_relevance else rng.randrange(10))
        target = 100_000_000 + i * 1_000_000  # 1 ms simulated spacing; not calibrated time
        events.append({"trial": i + 1, "signal": signal,
                       "signal_observed_ns": target - 200_000 if signal is not None else None,
                       "outcome": outcome, "outcome_observed_ns": target})
    train = [dict(e, trial=i + 1) for i, e in enumerate(events[:n_train])]
    heldout = events[n_train:]
    history = {"schema": HISTORY_SCHEMA, "source": source, "events": train}
    trained_at_ns = train[-1]["outcome_observed_ns"] + 10
    wrapper = fit(history, trained_at_ns=trained_at_ns)
    prepared_at_ns = trained_at_ns + 10
    schedule = [{"trial": i + 1, "signal": e["signal"],
                 "signal_observed_ns": prepared_at_ns - 1 if source == SOURCE_SIGNAL else None,
                 "target_not_before_ns": e["outcome_observed_ns"] - 1}
                for i, e in enumerate(heldout)]
    frozen = forecast(wrapper, schedule, prepared_at_ns=prepared_at_ns)
    obs = {"schema": OBSERVATION_SCHEMA, "forecast_commitment_sha256": frozen["commitment_sha256"],
           "outcomes": [{"trial": i + 1, "outcome": e["outcome"],
                         "outcome_observed_ns": e["outcome_observed_ns"]}
                        for i, e in enumerate(heldout)]}
    return {"source": source, "model_sha256": wrapper["model_sha256"],
            "train_examples": n_train, "test_examples": n_test,
            "signal_relevance_in_simulated_process": signal_relevance if source == SOURCE_SIGNAL else None,
            "qualification": wrapper["model"]["qualification"],
            "internal_validation_logloss": wrapper["model"]["validation_logloss_nats"],
            "test_labels_exposed_to_fit": False,
            "synthetic_simulation_only": True, "holdout_score": score(frozen, obs)}


def main() -> int:
    parser = argparse.ArgumentParser(description="AURA Signal10 v2; no retrocausal authority")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("controls", help="Reproducible simulated positive/negative tests")
    train = sub.add_parser("train", help="Fit and validate on training history only")
    train.add_argument("--history", type=Path, required=True)
    train.add_argument("--trained-at-ns", type=int, required=True)
    train.add_argument("--output", type=Path, required=True)
    predict = sub.add_parser("forecast", help="Freeze ten-class predictions before future events")
    predict.add_argument("--model", type=Path, required=True)
    predict.add_argument("--schedule", type=Path, required=True)
    predict.add_argument("--prepared-at-ns", type=int, required=True)
    predict.add_argument("--output", type=Path, required=True)
    resolve = sub.add_parser("score", help="Score independently supplied later outcomes")
    resolve.add_argument("--forecast", type=Path, required=True)
    resolve.add_argument("--observations", type=Path, required=True)
    resolve.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "controls":
        print(json.dumps({"schema": "janus.aura.signal10.control_suite.v2",
                          "predictable_process": synthetic_control(SOURCE_SIGNAL),
                          "irrelevant_pre_event_signal": synthetic_control(SOURCE_SIGNAL, signal_relevance=False),
                          "independent_uniform_process": synthetic_control(SOURCE_NULL),
                          "physical_experiment_performed": False}, indent=2, sort_keys=True))
        return 0
    if args.action == "train":
        result = fit(json.loads(args.history.read_text(encoding="utf-8")),
                     trained_at_ns=args.trained_at_ns)
    elif args.action == "forecast":
        result = forecast(json.loads(args.model.read_text(encoding="utf-8")),
                          json.loads(args.schedule.read_text(encoding="utf-8")),
                          prepared_at_ns=args.prepared_at_ns)
    else:
        result = score(json.loads(args.forecast.read_text(encoding="utf-8")),
                       json.loads(args.observations.read_text(encoding="utf-8")))
    # Write-once prevents accidental overwrite of frozen research artifacts.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"action": args.action, "output": str(args.output),
                      "sha256": digest(result)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
