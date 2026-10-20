from __future__ import annotations

from datetime import datetime, timezone
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from aura_retrocausal_lab_v1 import REQUEST_SCHEMA, RESOLUTION_SCHEMA, plan, resolve

NOW = datetime(2026, 10, 20, 1, 0, tzinfo=timezone.utc)


def scenario() -> dict:
    return {
        "schema": REQUEST_SCHEMA,
        "question": "Which reversible action best supports the desired November outcome?",
        "as_of": "2026-10-20T00:00:00Z",
        "target_at": "2026-11-01T00:00:00Z",
        "evidence": [{"id": "E0", "observed_at": "2026-10-19T17:00:00Z", "available_at": "2026-10-19T18:00:00Z"}],
        "outcome_utilities": {"SUCCESS": 1.0, "FAILURE": 0.0},
        "baseline_action_id": "WAIT",
        "actions": [
            {"id": "WAIT", "label": "Do nothing", "reversible": True, "forecast": {"SUCCESS": .3, "FAILURE": .7}},
            {"id": "TEST", "label": "Run safe pilot", "reversible": True, "cost": .05, "forecast": {"SUCCESS": .8, "FAILURE": .2}},
        ],
    }


class RetrocausalLabTests(unittest.TestCase):
    def test_backward_planning_ranks_scenarios_and_never_executes(self):
        result = plan(scenario(), now=NOW)
        p = result["prediction"]
        self.assertEqual(p["highest_scoring_scenario_id"], "TEST")
        self.assertEqual(p["study_class"], "PROSPECTIVE_CANDIDATE")
        self.assertAlmostEqual(p["action_scenarios"][0]["delta_vs_baseline_assumed_model"], .45)
        self.assertTrue(all(not x["automatically_executable"] for x in p["action_scenarios"]))
        self.assertIn("NO_PHYSICAL", result["epistemic_boundary"])

    def test_rejects_observation_from_the_future(self):
        data = scenario()
        data["evidence"][0]["available_at"] = "2026-10-21T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "FUTURE_INFORMATION_LEAKAGE"):
            plan(data, now=NOW)

    def test_rejects_future_as_of_and_unordered_horizon(self):
        data = scenario()
        data["as_of"] = "2026-10-21T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "AS_OF_CANNOT_BE_IN_FUTURE"):
            plan(data, now=NOW)
        data["target_at"] = "2026-10-20T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "TARGET_MUST_BE_AFTER_AS_OF"):
            plan(data, now=NOW)

    def test_rejects_malformed_probabilities_and_duplicate_ids(self):
        data = scenario()
        data["actions"][1]["forecast"]["SUCCESS"] = 1.2
        with self.assertRaisesRegex(ValueError, "PROBABILITIES_MUST_SUM_TO_ONE"):
            plan(data, now=NOW)
        data = scenario()
        data["actions"][1]["id"] = "WAIT"
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ACTION_ID"):
            plan(data, now=NOW)

    def test_retroactive_reconstruction_not_prospective(self):
        result = plan(scenario(), now=datetime(2027, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(result["prediction"]["study_class"], "RETROSPECTIVE_SIMULATION_ONLY")

    def test_resolution_checks_integrity_and_external_witness(self):
        frozen = plan(scenario(), now=NOW)
        resolution = {
            "schema": RESOLUTION_SCHEMA,
            "resolver": "INDEPENDENT_OBSERVER",
            "resolved_at": "2026-11-02T00:00:00Z",
            "observed_outcome_id": "SUCCESS",
            "actual_action_id": "TEST",
            "evidence_refs": ["external:experiment-42"],
        }
        result = resolve(frozen, resolution)
        self.assertAlmostEqual(result["brier_multiclass_mean"], .04)
        self.assertFalse(result["counterfactual_effect_established"])
        self.assertFalse(result["evidence_independently_verified"])
        bad = copy.deepcopy(frozen)
        bad["prediction"]["action_scenarios"][0]["forecast"]["SUCCESS"] = .99
        with self.assertRaisesRegex(ValueError, "COMMITMENT_MISMATCH"):
            resolve(bad, resolution)
        resolution["resolver"] = "AURA_ORACLE"
        with self.assertRaisesRegex(ValueError, "EXTERNAL_RESOLVER_REQUIRED"):
            resolve(frozen, resolution)

    def test_resolution_disallows_unobserved_counterfactual_and_early_result(self):
        frozen = plan(scenario(), now=NOW)
        row = {"schema": RESOLUTION_SCHEMA, "resolver": "INDEPENDENT_LAB", "resolved_at": "2026-10-30T00:00:00Z", "observed_outcome_id": "SUCCESS", "actual_action_id": "TEST", "evidence_refs": ["external:one"]}
        with self.assertRaisesRegex(ValueError, "OBSERVATION_BEFORE_TARGET"):
            resolve(frozen, row)
        row["resolved_at"] = "2026-11-02T00:00:00Z"
        row["actual_action_id"] = "UNPLANNED"
        with self.assertRaisesRegex(ValueError, "ACTUAL_ACTION_NOT_IN_FORECAST"):
            resolve(frozen, row)


if __name__ == "__main__":
    unittest.main()
