import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).resolve().parents[1]/"tools"/"aura_rowan_research.py"
spec=importlib.util.spec_from_file_location("aura_rowan_research",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def state(count=0):
    return {"schema_id":"janus.rowan.observer_state.v1",
            "latest_durable_external_run":40147900977,
            "underlying_state_is_derived_from":"f7cbdd46d0f5a620dec8054e7e143f6137081586e471bd3790d7674f9ba0c604",
            "last_completed_mutants":count,
            "latest_scientific_status":"INCOMPLETE_NO_CALIBRATION" if count<8 else "EXPLORATORY_STRATIFIED_DESCRIPTIVE_ONLY"}

class Tests(unittest.TestCase):
    def test_initial_state_never_fabricates_prediction(self):
        p=m.make_packet(state())
        self.assertEqual(len(p["hypotheses"]),4)
        self.assertEqual(p["next_discriminating_question_id"],"RAW_ASSAY_LINEAGE")
        self.assertIsNone(p["hypotheses"][0]["empirical_truth_probability"])
        self.assertFalse(p["bounded_authority"]["may_submit_rowan_jobs"])
        self.assertFalse(p["bounded_authority"]["may_modify_rowan_credit_budget"])
    def test_complete_state_requests_external_holdout(self):
        self.assertEqual(m.make_packet(state(8))["next_discriminating_question_id"],"EXTERNAL_HOLDOUT")
    def test_identical_state_same_digest(self):
        self.assertEqual(m.make_packet(state()),m.make_packet(state()))
    def test_invalid_public_source_hash_fails(self):
        s=state();s["underlying_state_is_derived_from"]="not-sha"
        with self.assertRaises(ValueError):m.make_packet(s)
    def test_premature_calibration_fails(self):
        s=state(3);s["latest_scientific_status"]="EXPLORATORY_STRATIFIED_DESCRIPTIVE_ONLY"
        with self.assertRaises(ValueError):m.make_packet(s)
    def test_strict_number_type(self):
        s=state();s["last_completed_mutants"]=True
        with self.assertRaises(ValueError):m.make_packet(s)
    def test_oracle_research_cannot_resolve_self(self):
        p=m.make_packet(state())
        self.assertFalse(p["bounded_authority"]["may_resolve_own_forecast"])
        self.assertEqual(p["brier_score"],"NOT_COMPUTABLE_WITHOUT_PRE-REGISTERED_PROBABILITY_AND_EXTERNAL_OUTCOME")

if __name__=="__main__":unittest.main()
