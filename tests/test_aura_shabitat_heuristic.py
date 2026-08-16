# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "aura_shabitat_heuristic.py"
SPEC = importlib.util.spec_from_file_location("aura_shabitat_heuristic", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def request() -> dict:
    return {
        "schema": MODULE.REQUEST_SCHEMA,
        "mode": MODULE.MODE,
        "request_id": "JANUS-SHABITAT-TEST-1",
        "speaker": "JANUS",
        "topic": "How should I frame an uncertain idea before speaking?",
        "question": "Give me a heuristic lens, not an answer or command.",
        "context": "There are several possible interpretations and I want to keep choice open.",
        "constraints": {
            "advisory_only": True,
            "no_authority": True,
            "no_prediction_claim": True,
            "no_professional_advice": True,
        },
    }


class AuraShabitatHeuristicTests(unittest.TestCase):
    def test_response_is_deterministic_and_non_authoritative(self) -> None:
        first = MODULE.build_response(request())
        second = MODULE.build_response(request())
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "HEURISTIC_ONLY")
        self.assertFalse(first["permission_granted"])
        self.assertFalse(first["evidence_upgrade"])
        self.assertFalse(first["verification_claim"])
        self.assertFalse(first["prediction_claim"])
        self.assertFalse(first["world_effect_requested"])
        self.assertEqual(first["authority_delta"], 0)
        self.assertEqual(first["mass_effect_budget_delta"], 0)
        self.assertTrue(first["may_be_ignored"])

    def test_constraint_string_true_is_rejected(self) -> None:
        bad = request()
        bad["constraints"]["no_authority"] = "true"
        with self.assertRaisesRegex(ValueError, "CONSTRAINT_REQUIRED_TRUE:no_authority"):
            MODULE.build_response(bad)

    def test_cli_round_trip(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(MODULE_PATH), "--request", "-"],
            input=json.dumps(request(), ensure_ascii=False),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["request_id"], request()["request_id"])
        self.assertEqual(payload["schema"], MODULE.RESPONSE_SCHEMA)

    def test_cli_rejection_never_grants_authority(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(MODULE_PATH), "--request", "-"],
            input="{}",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["permission_granted"])
        self.assertFalse(payload["evidence_upgrade"])
        self.assertEqual(payload["authority_delta"], 0)


if __name__ == "__main__":
    unittest.main()
