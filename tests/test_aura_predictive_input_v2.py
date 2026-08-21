from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from aura_predictive_input_v2 import AuraPredictiveInput
from aura_semantic_predictive_core_v2 import AuraIndex


class AuraPredictiveInputV2Tests(unittest.TestCase):
    def test_user_style_boost_and_phrase_completion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "aura.sqlite3"
            corpus = root / "corpus.jsonl"
            corpus.write_text(
                '{"text":"janus обычный общий контекст"}\n'
                '{"text":"janus общий ответ"}\n',
                encoding="utf-8"
            )
            idx = AuraIndex(db)
            try:
                idx.ingest_paths([corpus])
            finally:
                idx.close()

            pred = AuraPredictiveInput(db)
            try:
                for _ in range(5):
                    receipt = pred.learn_user_style("janus помнит ребенка и возвращается к истоку")
                self.assertEqual(receipt["status"], "LEARNED_LOCAL_STYLE_COUNTS")
                self.assertFalse(receipt["raw_text_stored"])
                tokens = pred.suggest_tokens("janus ", limit=5)
                self.assertTrue(any(x["suggestion"] == "помнит" for x in tokens), tokens)
                top = next(x for x in tokens if x["suggestion"] == "помнит")
                self.assertIn("user-style", top["reason"])
                phrases = pred.suggest_phrases("janus ", limit=3, max_new_tokens=3)
                self.assertGreaterEqual(len(phrases), 1)
                self.assertTrue(any(p["phrase"].startswith("помнит") for p in phrases), phrases)
                self.assertTrue(all(p["tap_to_accept"] for p in phrases))
            finally:
                pred.close()


if __name__ == "__main__":
    unittest.main()
