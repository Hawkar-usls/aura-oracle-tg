"""Independent protocol checks for the millisecond digit experiment."""
import importlib.util
import json
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "tools" / "aura_chronos_002.py"
spec = importlib.util.spec_from_file_location("aura_chronos_002", SOURCE)
chronos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chronos)


class Chronos002Tests(unittest.TestCase):
    def setUp(self):
        self.wrapper = chronos.freeze(list(range(10)) * 10,
                                      source="BASELINE_CYCLE_NOT_AURA", delay_ms=1)

    def test_100_predictions_required(self):
        with self.assertRaisesRegex(ValueError, "EXACTLY_100"):
            chronos.freeze([0] * 99, source="BASELINE_CYCLE_NOT_AURA")

    def test_reject_boolean_digit(self):
        with self.assertRaisesRegex(ValueError, "DIGITS_0_TO_9"):
            chronos.freeze([False] + [0] * 99, source="BASELINE_CYCLE_NOT_AURA")

    def test_tampering_rejected_before_random_draw(self):
        self.wrapper["frozen"]["predictions"][0] = 9
        calls = []
        def rng(n):
            calls.append(n)
            return 0
        with self.assertRaisesRegex(ValueError, "COMMITMENT_MISMATCH"):
            chronos.execute(self.wrapper, randbelow=rng)
        self.assertEqual(calls, [])

    def test_no_random_draws_during_freeze(self):
        self.assertEqual(chronos.check_freeze(self.wrapper)["source"], "BASELINE_CYCLE_NOT_AURA")

    def test_genuine_100_trail_timing_and_scoring(self):
        # Deterministic injected outcomes are only for a unit test, not evidence.
        count = [0]
        def rng(_):
            count[0] += 1
            return 0
        result = chronos.execute(self.wrapper, randbelow=rng)
        self.assertEqual(count[0], 100)
        self.assertEqual(result["hits"], 10)
        self.assertEqual(result["number_of_trials"], 100)
        self.assertFalse(result["oracle_ability_established"])
        self.assertFalse(result["clock"]["atomic_or_gps_ptp_time_attested"])
        self.assertGreaterEqual(result["clock"]["min_measured_wait_ms"], 1)
        self.assertEqual(result["statistical_flag"], "NO_EVIDENCE_ABOVE_CHANCE")

    def test_binomial_tail_monotonic(self):
        self.assertAlmostEqual(chronos.upper_binomial_tail(0), 1, places=12)
        self.assertGreater(chronos.upper_binomial_tail(10), chronos.upper_binomial_tail(20))
        self.assertLess(chronos.upper_binomial_tail(20), 0.01)

    def test_committed_baseline_artifacts_consistent(self):
        folder = Path(__file__).resolve().parents[1] / "experiments"
        frozen = json.loads((folder / "CHRONOS-002-baseline-frozen.json").read_text(encoding="utf-8"))
        observed = json.loads((folder / "CHRONOS-002-baseline-result.json").read_text(encoding="utf-8"))
        self.assertEqual(chronos.check_freeze(frozen)["source"], "BASELINE_CYCLE_NOT_AURA")
        self.assertEqual(observed["forecast_commitment_sha256"], frozen["commitment_sha256"])
        self.assertEqual(observed["hits"], sum(int(row["hit"]) for row in observed["observations"]))
        self.assertEqual(observed["exact_one_sided_p_value"],
                         round(chronos.upper_binomial_tail(observed["hits"]), 12))


if __name__ == "__main__":
    unittest.main()
