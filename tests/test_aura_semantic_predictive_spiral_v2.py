from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from aura_5d_spiral_v2 import run as run_5d
from aura_habitat_spiral_peer_v2 import reflect
from aura_semantic_predictive_core_v2 import AuraIndex, choose_question, update_candidates


class AuraV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "aura.sqlite3"
        self.registry = self.root / "registry"
        self.registry.mkdir()
        (self.registry / "alpha.json").write_text(json.dumps({
            "artifact": "JANUS black hole semantic memory",
            "principles": ["return is not reset", "position may repeat but state must advance"],
            "topic": "hawking radiation horizon information"
        }, ensure_ascii=False), encoding="utf-8")
        (self.registry / "beta.jsonl").write_text(
            json.dumps({"topic": "Aura predictive input suggests next word", "phrase": "черная дыра излучает"}, ensure_ascii=False) + "\n" +
            json.dumps({"topic": "HRain structural context", "phrase": "черная дыра горизонт событий"}, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        # Root array forced through ijson streaming path by threshold=1.
        (self.registry / "stream.json").write_text(json.dumps([
            {"topic": "iNaiHR associative semantics", "value": "семантика значение контекст"},
            {"topic": "DemiHead preserves disagreement", "value": "association is not evidence"}
        ], ensure_ascii=False), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_registry_ingest_search_and_autocomplete(self) -> None:
        idx = AuraIndex(self.db)
        try:
            receipt = idx.ingest_paths([self.registry], stream_threshold=1)
            self.assertEqual(receipt["files_seen"], 3)
            self.assertEqual(receipt["files_indexed"], 3)
            self.assertGreaterEqual(receipt["records_indexed"], 5)
            hits = idx.semantic_search("черная дыра")
            self.assertGreaterEqual(len(hits), 1)
            suggestions = idx.autocomplete("черная ")
            self.assertTrue(any(s["suggestion"] == "дыра" for s in suggestions))
            q = idx.registry_discriminator("janus")
            self.assertIn(q["status"], {"QUESTION_READY", "NO_DISCRIMINATING_FEATURE", "INSUFFICIENT_CANDIDATES"})
            stats = idx.stats()
            self.assertGreater(stats["indexed_records"], 0)
            self.assertFalse(stats["index_is_source_of_truth"])
        finally:
            idx.close()

    def test_incremental_skip(self) -> None:
        idx = AuraIndex(self.db)
        try:
            idx.ingest_paths([self.registry])
            second = idx.ingest_paths([self.registry])
            self.assertEqual(second["files_indexed"], 0)
        finally:
            idx.close()

    def test_generic_information_gain_engine(self) -> None:
        candidates = [
            {"id": "A", "weight": 1.0, "features": {"metal": 0.95, "round": 0.9}},
            {"id": "B", "weight": 1.0, "features": {"metal": 0.05, "round": 0.8}},
            {"id": "C", "weight": 1.0, "features": {"metal": 0.05, "round": 0.1}},
            {"id": "D", "weight": 1.0, "features": {"metal": 0.95, "round": 0.2}},
        ]
        q = choose_question(candidates)
        self.assertEqual(q["status"], "QUESTION_READY")
        self.assertGreater(q["information_gain_bits"], 0)
        self.assertFalse(q["proprietary_akinator_code_used"])
        updated = update_candidates(candidates, q["feature"], "YES")
        self.assertAlmostEqual(sum(x["weight"] for x in updated), 1.0, places=7)

    def test_forecast_requires_external_resolution(self) -> None:
        idx = AuraIndex(self.db)
        try:
            fc = idx.open_forecast("RAIN_TOMORROW", 0.7, "24h", {"cloud": 1})
            with self.assertRaises(ValueError):
                idx.resolve_forecast(fc["forecast_id"], 1, resolver="AURA_ORACLE")
            resolved = idx.resolve_forecast(fc["forecast_id"], 1, resolver="EXTERNAL_OBSERVATION")
            self.assertEqual(resolved["status"], "RESOLVED")
            prior = idx.forecast_prior("RAIN_TOMORROW")
            self.assertEqual(prior["resolved_count"], 1)
        finally:
            idx.close()

    def test_spiral_is_not_circle_and_supports_non_tail_growth(self) -> None:
        idx = AuraIndex(self.db)
        try:
            idx.ingest_paths([self.registry])
        finally:
            idx.close()
        payload = {
            "generation": 4,
            "intent_id": "a" * 64,
            "source_ref": "UNIT_TEST",
            "text": "Сначала построй структуру. Потом добавь семантические связи. Но обязательно вернись к началу и проверь позднее ограничение."
        }
        patch = [{
            "op": "SPLICE_BETWEEN",
            "left_id": "S0001",
            "right_id": "S0002",
            "node": {
                "id": "MID",
                "label": "non-tail abstraction",
                "kind": "ABSTRACTION",
                "source_segment_ids": ["S0001", "S0002"]
            }
        }]
        out = run_5d(payload, db_path=self.db, patches=patch)
        self.assertEqual(out["analysis_mode"], "SPIRAL_5D")
        self.assertEqual(out["graph"]["logical_order"][:3], ["S0001", "MID", "S0002"])
        self.assertEqual(out["axes"]["D5_SPIRAL_ABSTRACTION"]["origin_prime"]["generation"], 5)
        self.assertNotEqual(
            out["origin_state_hash"],
            out["axes"]["D5_SPIRAL_ABSTRACTION"]["origin_prime"]["origin_prime_state_hash"]
        )
        self.assertFalse(out["integrity"]["source_text_mutated"])

    def test_peer_v2_keeps_authority_firewall(self) -> None:
        idx = AuraIndex(self.db)
        try:
            idx.ingest_paths([self.registry])
        finally:
            idx.close()
        old = os.environ.get("AURA_INTELLIGENCE_DB")
        os.environ["AURA_INTELLIGENCE_DB"] = str(self.db)
        try:
            packet = {
                "schema": "janus.aura_spi.spiral_event.v1",
                "session_id": "s-test",
                "generation": 1,
                "intent_id": "b" * 64,
                "source_ref": "UNIT_TEST",
                "trigger_text": "Черная дыра и семантическая память. Но обязательно проверь обратный проход.",
                "constraints": {
                    "symbolic_reflection_only": True,
                    "prediction_authority": False,
                    "evidence_authority": False,
                    "may_not_replace_intent": True
                }
            }
            out = reflect(packet)
            self.assertEqual(out["status"], "REFLECTION_READY_SPIRAL_5D")
            self.assertFalse(out["predictive_label_authority"])
            self.assertFalse(out["scientific_evidence_authority"])
            self.assertFalse(out["predictive_ai"]["aura_may_resolve_own_forecast"])
            self.assertEqual(out["spiral_geometry"]["law"], "POSITION_MAY_REPEAT_BUT_STATE_MUST_ADVANCE")
            self.assertFalse(out["spiral_geometry"]["cycle_model"])
        finally:
            if old is None:
                os.environ.pop("AURA_INTELLIGENCE_DB", None)
            else:
                os.environ["AURA_INTELLIGENCE_DB"] = old


if __name__ == "__main__":
    unittest.main()
