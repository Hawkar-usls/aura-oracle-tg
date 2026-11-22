"""AURA-TACHYON source-bound, advisory-only bridge safety regression tests."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools import aura_tachyon_retrobound_bridge as bridge

FIXTURE = Path(__file__).parent / "fixtures" / "tachyon_retrobound_r1_validation_20261123.json"


class AuraTachyonBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.raw = bridge.load_pinned(FIXTURE)

    def test_pinned_source_is_exact_original_blob(self):
        self.assertEqual(bridge.git_blob_sha(self.raw), bridge.PINNED_BLOB_SHA1)
        self.assertEqual(self.source["schema"], bridge.SOURCE_SCHEMA)

    def test_advisory_exactly_source_bound(self):
        packet = bridge.make_advisory(self.source, self.raw)
        self.assertTrue(bridge.verify_advisory(packet))
        self.assertEqual(packet["source"]["commit_sha"], bridge.PINNED_COMMIT)
        self.assertEqual(packet["evidence_metrics"]["reference_default"]["n"], 40000)

    def test_5d_is_analysis_not_physical_five_dimensions(self):
        packet = bridge.make_advisory(self.source, self.raw)
        axes = packet["five_axis_spiral"]
        self.assertEqual(len([k for k in axes if k.startswith("D")]), 5)
        self.assertFalse(axes["real_physical_spacetime_dimensions_measured"])
        self.assertFalse(axes["origin_prime_claim"])

    def test_three_competing_physical_explanations_remain_separate(self):
        packet = bridge.make_advisory(self.source, self.raw)
        ids = [h["id"] for h in packet["hypotheses"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("H_FORWARD_POSTSELECTION", ids)
        self.assertIn("H_CAUSAL_NULL", ids)
        self.assertIn("H_RETROCAUSAL_PHYSICAL", ids)
        self.assertTrue(all(h["physical_truth_probability"] is None for h in packet["hypotheses"]))

    def test_no_world_prediction_or_model_mutation(self):
        packet = bridge.make_advisory(self.source, self.raw)
        self.assertTrue(all(v is False for k,v in packet["governance"].items() if k.startswith("may_") or k.endswith("authorized")))
        self.assertIsNone(packet["hypothesis_discrimination"]["calibrated_forecast_probability"])

    def test_changed_source_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.json"
            path.write_bytes(self.raw + b"\n")
            with self.assertRaisesRegex(ValueError, "SOURCE_BLOB_MISMATCH"):
                bridge.load_pinned(path)

    def test_changed_source_object_rejected_even_with_pinned_bytes(self):
        forged = copy.deepcopy(self.source)
        forged["scientific_interpretation"]["physical_retrocausality_demonstrated"] = True
        with self.assertRaisesRegex(ValueError, "SOURCE_OBJECT_BYTES_MISMATCH"):
            bridge.make_advisory(forged, self.raw)

    def test_future_probability_promotion_refused(self):
        packet = bridge.make_advisory(self.source, self.raw)
        packet["hypothesis_discrimination"]["calibrated_forecast_probability"] = 0.99
        packet["packet_digest_sha256"] = bridge.digest({k:v for k,v in packet.items() if k != "packet_digest_sha256"})
        with self.assertRaisesRegex(ValueError, "AURA_NOT_CALIBRATED"):
            bridge.verify_advisory(packet)

    def test_authority_promotion_refused_even_if_digest_recomputed(self):
        packet = bridge.make_advisory(self.source, self.raw)
        packet["governance"]["may_change_tachyon_weights"] = True
        packet["packet_digest_sha256"] = bridge.digest({k:v for k,v in packet.items() if k != "packet_digest_sha256"})
        with self.assertRaisesRegex(ValueError, "ADVISORY_AUTHORITY_PROMOTION"):
            bridge.verify_advisory(packet)

    def test_corrupted_advisory_digest_rejected(self):
        packet = bridge.make_advisory(self.source, self.raw)
        packet["packet_digest_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "ADVISORY_DIGEST_MISMATCH"):
            bridge.verify_advisory(packet)

    def test_missing_both_arms_or_altered_statistics_rejected(self):
        wrong = copy.deepcopy(self.source)
        del wrong["paired_default"]["arms"]["postselection"]
        with self.assertRaisesRegex(ValueError, "REQUIRED_THREE_ARMS"):
            bridge.validate_source(wrong)
        wrong = copy.deepcopy(self.source)
        wrong["paired_default"]["arms"]["two_boundary"]["hidden_past_future_correlation"] = 0.9
        with self.assertRaisesRegex(ValueError, "PAIRED_DIFFERENCE_MISMATCH"):
            bridge.validate_source(wrong)

    def test_physical_claim_promotion_rejected(self):
        wrong = copy.deepcopy(self.source)
        wrong["scientific_interpretation"]["physical_retrocausality_demonstrated"] = True
        with self.assertRaisesRegex(ValueError, "PHYSICAL_OR_PRODUCTION_CLAIM"):
            bridge.validate_source(wrong)

    def test_missing_and_nonfinite_rejected(self):
        wrong = copy.deepcopy(self.source)
        wrong["paired_default"]["rho"] = float("nan")
        with self.assertRaisesRegex(ValueError, "NONFINITE"):
            bridge.validate_source(wrong)
        wrong = copy.deepcopy(self.source)
        wrong["paired_alternative"]["future_parameter_counts"]["1"] = 10000
        with self.assertRaisesRegex(ValueError, "CHOICE_COUNTS"):
            bridge.validate_source(wrong)

    def test_cli_writes_advisory_local_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "advisory.json"
            self.assertEqual(bridge.main_argv([str(FIXTURE), str(out)]), 0)
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(bridge.verify_advisory(packet))


if __name__ == "__main__":
    unittest.main()
