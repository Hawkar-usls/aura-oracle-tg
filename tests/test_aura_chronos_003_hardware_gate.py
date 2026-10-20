"""Synthetic-only CHRONOS-003 evidence validator tests; NO live hardware involved."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("aura_chronos_003_hardware_gate", ROOT / "tools" / "aura_chronos_003_hardware_gate.py")
gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)


class Chronos003HardwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="chronos003-test-keys-")
        cls.private_key = Path(cls.temp.name) / "fixture-private.pem"
        cls.public_key = Path(cls.temp.name) / "fixture-public.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(cls.private_key)], check=True,
                       capture_output=True)
        subprocess.run(["openssl", "pkey", "-in", str(cls.private_key), "-pubout", "-out", str(cls.public_key)],
                       check=True, capture_output=True)
        cls.frozen = json.loads((ROOT / "experiments" / "AURA-NATIVE10-forecast-v1-frozen.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def fixture_statement(self):
        prepared_ns = self.frozen["forecast"]["prepared_at_unix_ns"]
        published_ns = prepared_ns + 1_000_000_000
        entropy_start_ns = published_ns + 2_000_000_000
        first_event_ns = entropy_start_ns + 1_000_000_000
        return {
            "schema": gate.STATEMENT_SCHEMA,
            "experiment": "CHRONOS-003-NATIVE10-EXTERNAL",
            "forecast_sha256": self.frozen["commitment_sha256"],
            "forecast_git_commit": gate.CHRONOS002_NATIVE10_FREEZE_COMMIT,
            "origin": "EXTERNAL_LAB_OBSERVER",
            "observer_id": "SYNTHETIC_TEST_FIXTURE_NOT_A_LAB",
            "git_commit_timing_evidence_ref": "fixture://git-commit-clock-fake",
            "forecast_commit_publication_utc_ns": published_ns,
            "entropy_start_utc_ns": entropy_start_ns,
            "clock": {
                "type": "GNSS_PPS", "manufacturer": "FIXTURE", "model": "NOT_REAL", "serial": "TEST",
                "calibration_evidence_ref": "fixture://calibration", "traceability_evidence_ref": "fixture://traceability",
                "lock_state_log_ref": "fixture://lock", "offset_measurement_ref": "fixture://offset",
                "jitter_measurement_ref": "fixture://jitter", "max_abs_utc_offset_ns": 20000,
                "max_utc_uncertainty_ns": 30000,
            },
            "rng": {
                "type": "HARDWARE_TRNG", "manufacturer": "FIXTURE", "model": "NOT_REAL", "serial": "TEST",
                "calibration_evidence_ref": "fixture://rng-cal", "entropy_health_evidence_ref": "fixture://health",
                "raw_entropy_archive_ref": "fixture://raw", "extractor_implementation_ref": "fixture://extractor",
                "digit_extraction": "REJECTION_SAMPLED_UNIFORM_0_TO_9",
            },
            "events": [
                {"trial": i + 1, "digit": i % 10, "event_utc_ns": first_event_ns + i * 1_000_000,
                 "capture_monotonic_ns": 200_000_000_000 + i * 1_000_000,
                 "time_uncertainty_ns": 30000, "clock_locked_at_capture": True,
                 "raw_entropy_record_ref": f"fixture://fake-entropy-{i + 1}"}
                for i in range(100)
            ],
            "signed_record_archive_ref": "fixture://synthetic-not-evidence",
        }

    def signed_bundle(self, statement):
        with tempfile.TemporaryDirectory(prefix="chronos003-test-sign-") as directory:
            data = Path(directory) / "statement.json"
            signature = Path(directory) / "sig.bin"
            data.write_bytes(gate.canonical(statement))
            subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(self.private_key),
                            "-rawin", "-in", str(data), "-out", str(signature)], check=True,
                           capture_output=True)
            return {"schema": gate.SCHEMA, "statement": statement,
                    "signature_ed25519_base64": base64.b64encode(signature.read_bytes()).decode("ascii")}

    def test_synthetic_signed_packet_passes_format_only_hardware_blocked(self):
        result = gate.audit(self.frozen, self.signed_bundle(self.fixture_statement()), public_key=self.public_key)
        self.assertEqual(result["cryptographic_signature_integrity"], "PASS_WITH_SUPPLIED_PUBLIC_KEY")
        self.assertEqual(result["evidence_structural_and_claimed_cadence"], "PASS")
        self.assertTrue(result["hardware_gate"].startswith("BLOCKED_"))
        self.assertFalse(result["physical_retrocausality_established"])
        self.assertFalse(result["trusted_key_identity_established"])
        self.assertFalse(result["physical_clock_calibration_verified"])
        self.assertEqual(result["event_timing_as_asserted"]["min_interval_ns"], 1_000_000)
        self.assertEqual(result["score_on_unauthenticated_physical_assertions_only"]["trials"], 100)

    def test_changed_digit_invalidates_signature(self):
        packet = self.signed_bundle(self.fixture_statement())
        packet["statement"]["events"][0]["digit"] = 9
        with self.assertRaisesRegex(ValueError, "SIGNATURE_INVALID"):
            gate.audit(self.frozen, packet, public_key=self.public_key)

    def test_commitment_change_rejected(self):
        statement = self.fixture_statement()
        statement["forecast_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "FROZEN_FORECAST_MISMATCH"):
            gate.check_statement(statement, self.frozen)

    def test_different_git_commit_disallowed(self):
        statement = self.fixture_statement()
        statement["forecast_git_commit"] = "1" * 40
        with self.assertRaisesRegex(ValueError, "INITIAL_FREEZE_COMMIT_REQUIRED"):
            gate.check_statement(statement, self.frozen)

    def test_entropy_earlier_than_commit_rejected(self):
        statement = self.fixture_statement()
        statement["entropy_start_utc_ns"] = statement["forecast_commit_publication_utc_ns"]
        with self.assertRaisesRegex(ValueError, "MUST_PREDATE_PUBLICATION_AND_ENTROPY"):
            gate.check_statement(statement, self.frozen)

    def test_jitter_more_than_allowed_rejected(self):
        statement = self.fixture_statement()
        statement["events"][10]["event_utc_ns"] += 500_000
        with self.assertRaisesRegex(ValueError, "CADENCE_OUT_OF_SPEC"):
            gate.check_statement(statement, self.frozen)

    def test_clock_lock_missing_rejected(self):
        statement = self.fixture_statement()
        statement["events"][12]["clock_locked_at_capture"] = False
        with self.assertRaisesRegex(ValueError, "CLOCK_LOCK_NOT_ATTESTED"):
            gate.check_statement(statement, self.frozen)

    def test_rng_without_health_reference_rejected(self):
        statement = self.fixture_statement()
        statement["rng"]["entropy_health_evidence_ref"] = ""
        with self.assertRaisesRegex(ValueError, "RNG_ENTROPY_HEALTH_EVIDENCE_REF"):
            gate.check_statement(statement, self.frozen)

    def test_clock_uncertainty_over_budget_rejected(self):
        statement = self.fixture_statement()
        statement["clock"]["max_utc_uncertainty_ns"] = 1_000_000
        with self.assertRaisesRegex(ValueError, "ERROR_BUDGET_TOO_LARGE"):
            gate.check_statement(statement, self.frozen)

    def test_replay_missing_public_key_rejected(self):
        packet = self.signed_bundle(self.fixture_statement())
        with self.assertRaisesRegex(ValueError, "PUBLIC_KEY_MISSING"):
            gate.audit(self.frozen, packet, public_key=Path(self.temp.name) / "no-key.pem")

    def test_reordering_events_rejected(self):
        statement = self.fixture_statement()
        statement["events"][1], statement["events"][2] = statement["events"][2], statement["events"][1]
        with self.assertRaisesRegex(ValueError, "NONCANONICAL_EVENT_ORDER"):
            gate.check_statement(statement, self.frozen)

    def test_boolean_digit_not_accepted(self):
        statement = self.fixture_statement()
        statement["events"][0]["digit"] = True
        with self.assertRaisesRegex(ValueError, "INVALID_DIGIT"):
            gate.check_statement(statement, self.frozen)


if __name__ == "__main__":
    unittest.main()
