"""Adversarial contracts and held-out controls for AURA Signal10 v2."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("aura_signal10_v2", ROOT / "tools" / "aura_signal10_v2.py")
v2 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v2
spec.loader.exec_module(v2)


def training_records(source=v2.SOURCE_SIGNAL, count=60):
    events = []
    for i in range(count):
        signal = i % 10 if source == v2.SOURCE_SIGNAL else None
        outcome_at = 100_000_000 + i * 1_000_000
        events.append({"trial": i + 1, "signal": signal,
                       "signal_observed_ns": outcome_at - 100_000 if signal is not None else None,
                       "outcome": i % 10, "outcome_observed_ns": outcome_at})
    return {"schema": v2.HISTORY_SCHEMA, "source": source, "events": events}


class AuraSignal10Tests(unittest.TestCase):
    def setUp(self):
        self.history = training_records(count=150)
        self.freeze_ns = 300_000_000
        self.model = v2.fit(self.history, trained_at_ns=self.freeze_ns)
        self.schedule = [{"trial": 1, "signal": 3, "signal_observed_ns": self.freeze_ns + 1,
                          "target_not_before_ns": self.freeze_ns + 2_000_000}]

    def test_real_conditional_ten_class_head_not_hash(self):
        self.assertEqual(v2.checked_model(self.model)["training_examples"], 150)
        self.assertEqual(self.model["model"]["qualification"], "VALIDATED_CONDITIONAL")
        ps = v2.probabilities(self.model, 3)
        self.assertEqual(len(ps), 10)
        self.assertEqual(ps[3], 11 / 20)
        self.assertEqual(ps[2], 1 / 20)
        self.assertAlmostEqual(sum(ps), 1)
        self.assertEqual(self.model["model"]["physical_retrocausality_authority"], False)

    def test_independent_entropy_optimal_uniform(self):
        history = training_records(v2.SOURCE_NULL, count=150)
        model = v2.fit(history, trained_at_ns=self.freeze_ns)
        self.assertEqual(v2.probabilities(model, None), [0.1] * 10)
        self.assertRaisesRegex(ValueError, "CSPRNG_SIGNAL_NOT_ALLOWED", v2.probabilities, model, 2)
        forecast = v2.forecast(model, [{"trial": i + 1, "signal": None, "signal_observed_ns": None,
                                      "target_not_before_ns": self.freeze_ns + 1_000_000 * (i + 1)}
                                     for i in range(100)], prepared_at_ns=self.freeze_ns + 1)
        rows = forecast["forecast"]["predictions"]
        self.assertEqual([row["digit"] for row in rows], list(range(10)) * 10)
        self.assertTrue(all(row["probabilities_0_to_9"] == [0.1] * 10 for row in rows))

    def test_holdout_signal_positive_control(self):
        result = v2.synthetic_control(v2.SOURCE_SIGNAL)
        score = result["holdout_score"]
        self.assertGreater(score["hits"], 200)
        self.assertLess(score["mean_logloss_nats"], 1.25)
        self.assertLess(score["mean_brier_divided_by_10"], 0.05)
        self.assertFalse(result["test_labels_exposed_to_fit"])

    def test_holdout_null_control(self):
        result = v2.synthetic_control(v2.SOURCE_NULL)
        score = result["holdout_score"]
        self.assertEqual(score["mean_logloss_nats"], round(math.log(10), 12))
        self.assertEqual(score["mean_brier_divided_by_10"], 0.09)
        self.assertFalse(score["evidence_for_precognition"])
        self.assertFalse(score["retrocausality_established"])

    def test_irrelevant_real_preevent_signal_falls_back_to_uniform(self):
        result = v2.synthetic_control(v2.SOURCE_SIGNAL, signal_relevance=False)
        self.assertEqual(result["qualification"], "UNIFORM_FALLBACK_NO_VALIDATED_SKILL")
        self.assertEqual(result["holdout_score"]["mean_logloss_nats"], round(math.log(10), 12))
        self.assertEqual(result["holdout_score"]["mean_brier_divided_by_10"], 0.09)

    def test_control_reproducibility(self):
        for source in v2.SOURCES:
            self.assertEqual(v2.synthetic_control(source), v2.synthetic_control(source))

    def test_training_after_outcome_not_before(self):
        altered = copy.deepcopy(self.history)
        altered["events"][2]["signal_observed_ns"] = altered["events"][2]["outcome_observed_ns"]
        with self.assertRaisesRegex(ValueError, "POST_EVENT_SIGNAL_LEAKAGE"):
            v2.fit(altered, trained_at_ns=self.freeze_ns)

    def test_training_cannot_read_unobserved_future(self):
        altered = copy.deepcopy(self.history)
        altered["events"][-1]["outcome_observed_ns"] = self.freeze_ns + 1
        with self.assertRaisesRegex(ValueError, "FUTURE_LABEL"):
            v2.fit(altered, trained_at_ns=self.freeze_ns)

    def test_training_requires_signal_and_no_signal_for_independent_rng(self):
        altered = copy.deepcopy(self.history)
        altered["events"][3]["signal"] = None
        with self.assertRaisesRegex(ValueError, "PRE_EVENT_SIGNAL_REQUIRED"):
            v2.fit(altered, trained_at_ns=self.freeze_ns)
        altered["source"] = v2.SOURCE_NULL
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_SOURCE_MUST_NOT_CONTAIN"):
            v2.fit(altered, trained_at_ns=self.freeze_ns)

    def test_model_tampering_and_counts_consistency_rejected(self):
        changed = copy.deepcopy(self.model)
        changed["model"]["counts_by_signal_and_digit"][0][0] += 10
        with self.assertRaisesRegex(ValueError, "MODEL_COMMITMENT_MISMATCH"):
            v2.checked_model(changed)
        changed["model_sha256"] = v2.digest(changed["model"])
        with self.assertRaisesRegex(ValueError, "TRAINING_COUNTS_MISMATCH"):
            v2.checked_model(changed)

    def test_forecast_signals_must_exist_before_freeze(self):
        altered = copy.deepcopy(self.schedule)
        altered[0]["signal_observed_ns"] = self.freeze_ns + 200
        with self.assertRaisesRegex(ValueError, "SIGNAL_MUST_BE_OBSERVED"):
            v2.forecast(self.model, altered, prepared_at_ns=self.freeze_ns + 100)

    def test_forecast_targets_must_be_strictly_in_future(self):
        altered = copy.deepcopy(self.schedule)
        altered[0]["target_not_before_ns"] = self.freeze_ns + 1
        with self.assertRaisesRegex(ValueError, "SCHEDULE_MUST_BE_FUTURE"):
            v2.forecast(self.model, altered, prepared_at_ns=self.freeze_ns + 100)

    def test_scoring_rejects_tampered_forecasts_or_early_outcomes(self):
        frozen = v2.forecast(self.model, self.schedule, prepared_at_ns=self.freeze_ns + 100)
        observed = {"schema": v2.OBSERVATION_SCHEMA,
                    "forecast_commitment_sha256": frozen["commitment_sha256"],
                    "outcomes": [{"trial": 1, "outcome": 3,
                                  "outcome_observed_ns": self.freeze_ns + 3_000_000}]}
        score = v2.score(frozen, observed)
        self.assertEqual(score["hits"], 1)
        self.assertLess(score["mean_logloss_nats"], math.log(10))
        changed = copy.deepcopy(frozen)
        changed["forecast"]["predictions"][0]["probabilities_0_to_9"][3] = 0.999
        with self.assertRaisesRegex(ValueError, "FORECAST_COMMITMENT_MISMATCH"):
            v2.score(changed, observed)
        observed["outcomes"][0]["outcome_observed_ns"] = self.freeze_ns + 300
        with self.assertRaisesRegex(ValueError, "OUTCOME_OCCURRED_BEFORE_PREDICTION"):
            v2.score(frozen, observed)

    def test_r1_primary_record_preserved_as_negative(self):
        checkpoint = json.loads((ROOT / "experiments" /
                                 "CHRONOS-003-NATIVE10-software-primary-checkpoint.json").read_text())
        self.assertEqual(checkpoint["top1_hits"], 8)
        self.assertEqual(checkpoint["scientific_verdict"], "NO_EVIDENCE_ABOVE_CHANCE__PRIMARY_RESULT_IMMUTABLE")
        self.assertEqual(checkpoint["physical_retrocausality_established"], False)
        self.assertEqual(checkpoint["replace_primary_with_rerun"], False)

    def test_cli_train_forecast_score_write_once(self):
        with tempfile.TemporaryDirectory() as d:
            temp = Path(d)
            history_file = temp / "history.json"
            model_file = temp / "model.json"
            schedule_file = temp / "schedule.json"
            forecast_file = temp / "forecast.json"
            observation_file = temp / "observations.json"
            score_file = temp / "score.json"
            history_file.write_text(json.dumps(self.history))
            schedule_file.write_text(json.dumps(self.schedule))

            def command(*args):
                return subprocess.run([sys.executable, str(ROOT / "tools" / "aura_signal10_v2.py"), *args],
                                      capture_output=True, text=True)

            train = command("train", "--history", str(history_file), "--trained-at-ns", str(self.freeze_ns),
                            "--output", str(model_file))
            self.assertEqual(train.returncode, 0, train.stderr)
            self.assertEqual(v2.checked_model(json.loads(model_file.read_text()))["qualification"],
                             "VALIDATED_CONDITIONAL")
            again = command("train", "--history", str(history_file), "--trained-at-ns", str(self.freeze_ns),
                            "--output", str(model_file))
            self.assertNotEqual(again.returncode, 0, "Existing frozen file must not be overwritten")
            predicted = command("forecast", "--model", str(model_file), "--schedule", str(schedule_file),
                                "--prepared-at-ns", str(self.freeze_ns + 100), "--output", str(forecast_file))
            self.assertEqual(predicted.returncode, 0, predicted.stderr)
            frozen = json.loads(forecast_file.read_text())
            observation_file.write_text(json.dumps({"schema": v2.OBSERVATION_SCHEMA,
                "forecast_commitment_sha256": frozen["commitment_sha256"],
                "outcomes": [{"trial": 1, "outcome": 3, "outcome_observed_ns": self.freeze_ns + 3_000_000}]}))
            outcome = command("score", "--forecast", str(forecast_file),
                              "--observations", str(observation_file), "--output", str(score_file))
            self.assertEqual(outcome.returncode, 0, outcome.stderr)
            self.assertEqual(json.loads(score_file.read_text())["hits"], 1)


if __name__ == "__main__":
    unittest.main()
