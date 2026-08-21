from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from aura_semantic_predictive_core_v2 import AuraIndex


class AuraBomIngestV2Tests(unittest.TestCase):
    def test_small_json_with_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "bom.json"
            p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"topic":"ORIGIN_PRIME", "text":"reverse tranception"}).encode("utf-8"))
            idx = AuraIndex(root / "aura.sqlite3")
            try:
                r = idx.ingest_paths([p])
                self.assertEqual(r["files_indexed"], 1)
                self.assertGreater(r["records_indexed"], 0)
                self.assertGreater(len(idx.semantic_search("ORIGIN_PRIME reverse")), 0)
            finally:
                idx.close()

    def test_streamed_root_array_with_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "bom-large.json"
            payload = [{"id": i, "text": "черная дыра горизонт событий"} for i in range(20)]
            p.write_bytes(b"\xef\xbb\xbf" + json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            idx = AuraIndex(root / "aura.sqlite3")
            try:
                r = idx.ingest_paths([p], stream_threshold=1)
                self.assertEqual(r["files_indexed"], 1)
                self.assertEqual(r["records_indexed"], 20)
            finally:
                idx.close()


if __name__ == "__main__":
    unittest.main()
