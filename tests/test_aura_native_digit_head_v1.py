"""Guardrail and reproducibility tests for AURA's native softmax ten-class head."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "aura_native_digit_head_v1.py"
spec = importlib.util.spec_from_file_location("aura_native_digit_head_v1", SCRIPT)
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)


class Native10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = json.loads((ROOT / "experiments" / "CHRONOS-002-baseline-result.json").read_text(encoding="utf-8"))
        cls.fit = native.fit(cls.history)

    def test_historical_dataset_has_fixed_commitment(self):
        labels = native.extract_historical_outcomes(self.history, fitted_at_ns=time.time_ns())
        self.assertEqual(native.digest(labels), native.FROZEN_TRAINING_OUTCOMES_SHA256)
        self.assertEqual(len(labels), 100)

    def test_trainable_native_probabilistic_head_not_hash_decoder(self):
        model = native.checked_model(self.fit["frozen_model"])
        self.assertEqual(len(model["weights"]), 10)
        self.assertEqual(len(model["weights"][0]), len(native.FEATURE_NAMES))
        self.assertFalse(model["semantic_hash_digit_decoder_used"])
        p0 = native.probabilities(model["weights"], 0)
        p1 = native.probabilities(model["weights"], 1)
        self.assertAlmostEqual(sum(p0), 1, places=12)
        self.assertTrue(all(0 < p < 1 for p in p0))
        self.assertNotEqual(p0, p1)

    def test_training_is_reproducible(self):
        again = native.fit(self.history)
        self.assertEqual(self.fit["frozen_model"]["model"]["weights"], again["frozen_model"]["model"]["weights"])

    def test_holdout_only_evaluated(self):
        receipt = self.fit["training_receipt"]
        self.assertFalse(receipt["validation_used_for_training_or_selection"])
        self.assertEqual(len(self.fit["frozen_model"]["model"]["training_trials"]), 80)
        self.assertEqual(len(self.fit["frozen_model"]["model"]["heldout_validation_trials"]), 20)

    def test_future_training_timestamp_rejected(self):
        altered = copy.deepcopy(self.history)
        altered["observations"][99]["draw_unix_ns"] = time.time_ns() + 1_000_000_000
        with self.assertRaisesRegex(ValueError, "FUTURE_DATA"):
            native.fit(altered)

    def test_training_outcome_modification_rejected(self):
        altered = copy.deepcopy(self.history)
        altered["observations"][0]["outcome"] = (altered["observations"][0]["outcome"] + 1) % 10
        with self.assertRaisesRegex(ValueError, "FROZEN_TRAINING_OUTCOMES_DRIFT"):
            native.fit(altered)

    def test_model_tampering_rejected(self):
        altered = copy.deepcopy(self.fit["frozen_model"])
        altered["model"]["weights"][0][0] += 1
        with self.assertRaisesRegex(ValueError, "COMMITMENT_MISMATCH"):
            native.checked_model(altered)

    def test_100_probability_vectors_before_outcomes(self):
        frozen = native.forecast(self.fit["frozen_model"])
        packet = native.checked_forecast(frozen)
        self.assertEqual(len(packet["predictions"]), 100)
        self.assertTrue(all(len(x["probabilities_0_to_9"]) == 10 for x in packet["predictions"]))
        self.assertFalse(packet["test_outcomes_present"])
        self.assertFalse(packet["atomic_grade_evidence_allowed"])
        self.assertEqual(packet["hardware_clock_attestation"], "NOT_PROVIDED")
        self.assertFalse(packet["millisecond_prediction_horizon_claimed"])
        self.assertTrue(all(row["nominal_offset_ms_after_independent_runner_start"] == i + 1
                            for i, row in enumerate(packet["predictions"])))

    def test_tampered_forecast_rejected(self):
        frozen = native.forecast(self.fit["frozen_model"])
        frozen["forecast"]["predictions"][0]["digit"] = (frozen["forecast"]["predictions"][0]["digit"] + 1) % 10
        with self.assertRaisesRegex(ValueError, "COMMITMENT_MISMATCH"):
            native.checked_forecast(frozen)

    def test_hardware_gate_fails_closed_even_with_self_assertion(self):
        with self.assertRaisesRegex(ValueError, "NOT_AVAILABLE"):
            native.hardware_time_gate({"claimed_atomic_clock": True, "signed": True})

    def test_external_outcomes_need_independent_resolver(self):
        frozen = native.forecast(self.fit["frozen_model"])
        observed = {"schema": native.OBSERVATION_SCHEMA, "forecast_commitment_sha256": frozen["commitment_sha256"],
                    "resolver": "AURA_SELF", "evidence_refs": ["test:not-independent"],
                    "observed_at_unix_ns": time.time_ns() + 100_000,
                    "outcomes": [0] * 100}
        with self.assertRaisesRegex(ValueError, "EXTERNAL_RESOLVER_REQUIRED"):
            native.score_external(frozen, observed)
        observed["resolver"] = "FIXTURE_INDEPENDENT_OBSERVER_ASSERTED"
        score = native.score_external(frozen, observed)
        self.assertEqual(score["trials"], 100)
        self.assertFalse(score["atomic_grade_claim_allowed"])
        self.assertEqual(score["independent_evidence_authentication"], "NOT_IMPLEMENTED")

    def test_committed_model_and_forecast_replay(self):
        folder = ROOT / "experiments"
        artifact = json.loads((folder / "AURA-NATIVE10-model-v1.json").read_text(encoding="utf-8"))
        model_wrapper = artifact["frozen_model"]
        model = native.checked_model(model_wrapper)
        self.assertEqual(model["weights"], self.fit["frozen_model"]["model"]["weights"])
        self.assertEqual(artifact["training_receipt"]["model_sha256"], model_wrapper["model_sha256"])
        frozen = json.loads((folder / "AURA-NATIVE10-forecast-v1-frozen.json").read_text(encoding="utf-8"))
        packet = native.checked_forecast(frozen)
        self.assertEqual(packet["model_sha256"], model_wrapper["model_sha256"])
        for i, row in enumerate(packet["predictions"]):
            expected = [round(value, 15) for value in native.probabilities(model["weights"], i)]
            self.assertEqual(row["probabilities_0_to_9"], expected)


if __name__ == "__main__":
    unittest.main()
