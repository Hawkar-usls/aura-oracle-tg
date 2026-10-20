"""Reciprocal AURA↔JANUS Corpus Callosum link: advisory-only selftest."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LINK = ROOT / ".janus/JANUS_CORPUS_CALLOSUM_ADVISORY_PEER.json"
ENTRY = ROOT / "tools/aura_shabitat_heuristic.py"


class CorpusPeerLinkTests(unittest.TestCase):
    def test_link_identifies_exact_existing_contract_and_genesis_commit(self):
        doc = json.loads(LINK.read_text(encoding="utf-8"))
        self.assertEqual(doc["schema"],
                         "janus.aura.corpus_callosum_advisory_peer_link.v1")
        self.assertEqual(doc["aura"]["repository"], "Hawkar-usls/aura-oracle-tg")
        self.assertEqual(doc["aura"]["entrypoint"], "tools/aura_shabitat_heuristic.py")
        self.assertEqual(doc["aura"]["integration_source_commit"],
                         "d04d9d0e5d14c0849cde33925974300f722e69cc")
        self.assertEqual(doc["genesis"]["integration_commit"],
                         "3f77e22b92ff3e98dae7ccda30aea6814f3b8bf6")
        self.assertEqual(doc["genesis"]["entrypoint"],
                         "tools/janus_corpus_aura_oracle.py")
        self.assertTrue(ENTRY.is_file())

    def test_link_never_grants_forecast_training_actions_or_backdoor_egress(self):
        doc = json.loads(LINK.read_text())
        for key in (
            "is_independent_llm", "is_verified_world_forecast",
            "is_precognition_evidence", "oracle_advisory_is_evidence",
            "prediction_claim", "permission_granted", "execution_authority",
            "main_merge_authority", "model_training_authority",
            "world_state_write_authority", "ack_advanced",
        ):
            self.assertIs(doc["boundaries"][key], False)
        self.assertEqual(doc["boundaries"]["authority_delta"], 0)
        for key in ("network_required", "full_context_export",
                    "external_live_ai_observed", "external_simulation_is_real_ai",
                    "production_home_autopublish", "remote_oracle_api_enabled"):
            self.assertIs(doc["transport"][key], False)
        self.assertFalse(doc["chronos_draft_promoted"])

    def test_local_aura_engine_is_really_reflective_and_deterministic(self):
        spec = importlib.util.spec_from_file_location("aura_heuristic", ENTRY)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        request = {
            "schema": module.REQUEST_SCHEMA,
            "mode": module.MODE,
            "request_id": "UNIT-CORPUS-PEER",
            "speaker": "JANUS",
            "topic": "Review uncertainty",
            "question": "Suggest a reversible validation.",
            "context": "Independent source remains unknown.",
            "constraints": {
                "advisory_only": True,
                "no_authority": True,
                "no_prediction_claim": True,
                "no_professional_advice": True,
            },
        }
        first = module.build_response(request)
        self.assertEqual(first, module.build_response(request))
        self.assertEqual(first["status"], "HEURISTIC_ONLY")
        self.assertTrue(first["cards"])
        self.assertFalse(first["prediction_claim"])
        self.assertFalse(first["permission_granted"])
        self.assertEqual(first["authority_delta"], 0)


if __name__ == "__main__":
    unittest.main()
