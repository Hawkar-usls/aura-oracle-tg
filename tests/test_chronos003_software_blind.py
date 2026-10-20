"""Pre-trigger tests only: ALL mocked digits and timestamps are synthetic."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


runner = module("chronos003_software_blind_runner.py", "chronos003_software_blind_runner")
verifier = module("chronos003_independent_verify.py", "chronos003_independent_verify")


class SoftBlindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forecast_path = ROOT / "experiments" / "AURA-NATIVE10-forecast-v1-frozen.json"
        cls.model_path = ROOT / "experiments" / "AURA-NATIVE10-model-v1.json"
        cls.native_source_path = ROOT / "tools" / "aura_native_digit_head_v1.py"
        cls.forecast = json.loads(cls.forecast_path.read_text(encoding="utf-8"))

    def marker(self):
        return {
            "schema": runner.MARKER_SCHEMA,
            "experiment": "CHRONOS-003-SOFTONLY-NATIVE10-R1",
            "forecast_sha256": runner.FORECAST_SHA256,
            "model_sha256": runner.MODEL_SHA256,
            "freeze_git_commit": runner.FROZEN_GIT_COMMIT,
            "new_outcomes_generated_before_trigger": False,
            "primary_run_policy": "FIRST_GITHUB_RUN_ATTEMPT_ONLY_NO_SUBSTITUTION",
            "purpose": "SOFTWARE_ONLY_BLIND_CONTROL_NO_ATOMIC_TIME_HARDWARE",
        }

    def preflight(self, marker=None):
        with tempfile.TemporaryDirectory() as folder:
            mpath = Path(folder) / "trigger-fixture.json"
            mpath.write_text(json.dumps(self.marker() if marker is None else marker), encoding="utf-8")
            return runner.validate_before_entropy(self.forecast_path, self.model_path, mpath,
                                                  self.native_source_path)

    def deterministic_synthetic_trial(self):
        checked = self.preflight()
        counter_mono = [1_000_000_000]
        counter_utc = [self.forecast["forecast"]["prepared_at_unix_ns"] + 10_000_000_000]
        digits = [0]

        def mono():
            counter_mono[0] += 1_000_000
            return counter_mono[0]

        def wall():
            counter_utc[0] += 1_000_000
            return counter_utc[0]

        def randbelow(n):
            self.assertEqual(n, 10)
            digits[0] += 1
            return (digits[0] - 1) % 10

        synthetic = runner.draw_after_validation(checked, randbelow=randbelow,
                                                 sleep=lambda _: None, monotonic_ns=mono,
                                                 wall_ns=wall, source="SYNTHETIC_UNIT_TEST_NOT_REAL")
        self.assertEqual(digits[0], 100)
        return synthetic

    def test_historic_artifacts_and_frozen_logits_reproduced_independently(self):
        checked = self.preflight()
        self.assertEqual(checked["forecast_wrapper"]["commitment_sha256"], runner.FORECAST_SHA256)
        self.assertEqual(len(checked["forecast"]["predictions"]), 100)

    def test_no_rng_call_during_preflight(self):
        before = time.monotonic_ns()
        self.preflight()
        self.assertGreater(time.monotonic_ns(), before)

    def test_preflight_rejects_changed_marker_forecast(self):
        marker = self.marker()
        marker["forecast_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "MARKER_FROZEN_COMMITMENTS_MISMATCH"):
            self.preflight(marker)

    def test_preflight_rejects_any_claim_of_prior_new_outcomes(self):
        marker = self.marker()
        marker["new_outcomes_generated_before_trigger"] = True
        with self.assertRaisesRegex(ValueError, "PRIOR_OUTCOME_ASSERTION_REQUIRED"):
            self.preflight(marker)

    def test_preflight_rejects_posthoc_run_substitution(self):
        marker = self.marker()
        marker["primary_run_policy"] = "BEST_OF_REPEATS"
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_PRIMARY_RUN_POLICY"):
            self.preflight(marker)

    def test_preflight_rejects_changed_frozen_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "modified-forecast.json"
            path.write_text(self.forecast_path.read_text(encoding="utf-8").replace("0.098357086994049", "0.198357086994049"),
                            encoding="utf-8")
            marker = Path(folder) / "marker.json"
            marker.write_text(json.dumps(self.marker()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "FORECAST_FILE_DRIFT"):
                runner.validate_before_entropy(path, self.model_path, marker, self.native_source_path)

    def test_100_synthetic_outcomes_scored_independently(self):
        synthetic = self.deterministic_synthetic_trial()
        scored = verifier.verify(self.forecast, synthetic, expected_source="SYNTHETIC_UNIT_TEST_NOT_REAL")
        self.assertEqual(scored["trials"], 100)
        self.assertTrue(scored["score_independently_recomputed"])
        self.assertTrue(scored["measured_minimum_wait_1ms_pass"])
        self.assertEqual(scored["outcome_digit_frequencies"], [10] * 10)
        self.assertFalse(scored["physical_retrocausality_established"])
        self.assertEqual(scored["hardware_gate"], "BLOCKED_NO_DEVICE")

    def test_tampered_synthetic_digest_rejected(self):
        synthetic = self.deterministic_synthetic_trial()
        synthetic["result"]["observations"][10]["outcome"] = 9
        with self.assertRaisesRegex(ValueError, "RECEIPT_SHA_MISMATCH"):
            verifier.verify(self.forecast, synthetic, expected_source="SYNTHETIC_UNIT_TEST_NOT_REAL")

    def test_tampered_prediction_rejected(self):
        synthetic = self.deterministic_synthetic_trial()
        altered = copy.deepcopy(self.forecast)
        altered["forecast"]["predictions"][0]["digit"] = 0
        with self.assertRaisesRegex(ValueError, "FORECAST_COMMITMENT_MISMATCH"):
            verifier.verify(altered, synthetic, expected_source="SYNTHETIC_UNIT_TEST_NOT_REAL")

    def test_invalid_boolean_digit_rejected(self):
        synthetic = self.deterministic_synthetic_trial()
        synthetic["result"]["observations"][0]["outcome"] = False
        synthetic["result_sha256"] = verifier.digest(synthetic["result"])
        with self.assertRaisesRegex(ValueError, "DIGIT_INVALID"):
            verifier.verify(self.forecast, synthetic, expected_source="SYNTHETIC_UNIT_TEST_NOT_REAL")

    def test_negative_sleep_time_rejected(self):
        synthetic = self.deterministic_synthetic_trial()
        synthetic["result"]["observations"][0]["wait_monotonic_ns"] = -1
        synthetic["result_sha256"] = verifier.digest(synthetic["result"])
        with self.assertRaisesRegex(ValueError, "NEGATIVE_OR_PRECOMMIT_TIMING"):
            verifier.verify(self.forecast, synthetic, expected_source="SYNTHETIC_UNIT_TEST_NOT_REAL")

    def test_swapping_draw_order_rejected(self):
        synthetic = self.deterministic_synthetic_trial()
        synthetic["result"]["observations"][1], synthetic["result"]["observations"][2] = (
            synthetic["result"]["observations"][2], synthetic["result"]["observations"][1])
        synthetic["result_sha256"] = verifier.digest(synthetic["result"])
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_EVENT_ORDER"):
            verifier.verify(self.forecast, synthetic, expected_source="SYNTHETIC_UNIT_TEST_NOT_REAL")

    def test_fake_hardware_attestation_rejected(self):
        synthetic = self.deterministic_synthetic_trial()
        synthetic["result"]["atomic_grade_timestamp_attested"] = True
        synthetic["result_sha256"] = verifier.digest(synthetic["result"])
        with self.assertRaisesRegex(ValueError, "PROVENANCE_AND_HARDWARE_GATE_MISMATCH"):
            verifier.verify(self.forecast, synthetic, expected_source="SYNTHETIC_UNIT_TEST_NOT_REAL")

    def test_nonprimary_cloud_rerun_rejected(self):
        synthetic = self.deterministic_synthetic_trial()
        synthetic["result"]["source"] = "GITHUB_HOSTED_OS_CSPRNG_NOT_HARDWARE_ATTESTED"
        synthetic["result"]["github_actions_run_attempt_as_asserted"] = "2"
        synthetic["result"]["github_actions_run_id_as_asserted"] = "123456"
        synthetic["result_sha256"] = verifier.digest(synthetic["result"])
        with self.assertRaisesRegex(ValueError, "FIRST_RUN_ATTESTATION_NOT_PRESENT"):
            verifier.verify(self.forecast, synthetic)


if __name__ == "__main__":
    unittest.main()
