#!/usr/bin/env python3
"""AURA Oracle scientific-hypothesis *proposal* bridge for existing JANUS Rowan.

No metaphysical/precognitive prediction, no Rowan calls, no secrets,
no inference of stability from pTM/lDDT, no self-resolving forecasts.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from urllib.request import Request,urlopen

STATE_URL="https://raw.githubusercontent.com/Hawkar-usls/janus-meta-registry/main/data/rowan/CANONICAL_STATE.json"
SCHEMA="janus.aura.rowan_hypothesis_packet.v1"
HYPOTHESES=(
 ("H_CONFIDENCE_SIGNAL","Delta pTM / lDDT may have rank association with processed BBC1 assay labels"),
 ("H_NULL_SIGNAL","Confidence may be nearly invariant under point mutations despite distinct assay labels"),
 ("H_ASSAY_CONFOUND","Source preprocessing or position-based selection may explain an apparent relationship"),
 ("H_DOMAIN_SHIFT","Any within-BBC1 relationship may fail on unseen proteins or independent assays"),
)
SEARCH=(
 {"id":"RAW_ASSAY_LINEAGE","question":"Locate original Tsuboyama BBC1/1TG0 raw assay tables, units, replicates, and score transformation","terms":["Tsuboyama 2023 BBC1 1TG0 cDNA proteolysis raw stability ddG assay","ProteinGym BBC1 processing normalization Tsuboyama 2023"],"kind":"BEETLE_DISCOVERY_ONLY"},
 {"id":"NEGATIVE_CONTROLS","question":"Locate independent mutation-stability controls and confidence/fold-score failure cases","terms":["Boltz-2 protein stability prediction pTM mutation limitations","protein structure confidence versus thermodynamic mutation stability validation"],"kind":"BEETLE_DISCOVERY_ONLY"},
 {"id":"EXTERNAL_HOLDOUT","question":"Find external proteins with experimental mutational stability where prediction can be independently tested","terms":["ProteinGym independent DMS proteolysis assays mutation heldout proteins benchmark"],"kind":"BEETLE_DISCOVERY_ONLY"},
)
def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def make_packet(state):
    if not isinstance(state,dict) or state.get("schema_id")!="janus.rowan.observer_state.v1":
        raise ValueError("INVALID_ROWAN_CANONICAL_SCHEMA")
    run=state.get("latest_durable_external_run")
    count=state.get("last_completed_mutants")
    source=state.get("underlying_state_is_derived_from")
    status=state.get("latest_scientific_status")
    if type(run) is not int or run<=0 or type(count) is not int or not 0<=count<=8:
        raise ValueError("INVALID_RUN_OR_COMPLETION")
    if not isinstance(source,str) or len(source)!=64 or any(c not in "0123456789abcdef" for c in source):
        raise ValueError("INVALID_SOURCE_SHA")
    if status not in {"INCOMPLETE_NO_CALIBRATION","EXPLORATORY_STRATIFIED_DESCRIPTIVE_ONLY"}:
        raise ValueError("UNRECOGNIZED_SCIENCE_STATUS")
    if count<8 and status!="INCOMPLETE_NO_CALIBRATION":
        raise ValueError("PREMATURE_CALIBRATION_STATUS")
    candidates=[{"id":name,"statement":sentence,"status":"HYPOTHESIS_ONLY__NOT_MEASURED",
                 "empirical_truth_probability":None} for name,sentence in HYPOTHESES]
    # Fixed priority only selects *questions to ask*, not claimed probabilities.
    current=("RAW_ASSAY_LINEAGE" if count<8 else "EXTERNAL_HOLDOUT")
    proposal={
        "schema_id":SCHEMA,
        "generator":"EXISTING_AURA_ORACLE_REPOSITORY__DETERMINISTIC_HYPOTHESIS_PROTOCOL",
        "source":{"repository":"Hawkar-usls/janus-meta-registry",
                  "path":"data/rowan/CANONICAL_STATE.json","state_sha256":digest(state),
                  "upstream_run":run,"upstream_artifact_sha256":source,
                  "completed_mutants":count},
        "question":"Does structural confidence correspond to independent experimental mutation effects?",
        "hypotheses":candidates,"search_proposals":list(SEARCH),
        "next_discriminating_question_id":current,
        "decision_rule":"Independent source verification and TOPA adversarial replay before scientific promotion",
        "hypothesis_priority_is_probabilistic_forecast":False,
        "information_gain":"NOT_ESTIMATED_NO_CALIBRATED_HYPOTHESIS_PRIORS",
        "brier_score":"NOT_COMPUTABLE_WITHOUT_PRE-REGISTERED_PROBABILITY_AND_EXTERNAL_OUTCOME",
        "source_has_unseen_outcome":False,
        "bounded_authority":{"may_steer_beetle_metadata_search":True,
             "may_notify_demiurge_of_test_proposals":True,
             "may_resolve_own_forecast":False,"may_submit_rowan_jobs":False,
             "may_modify_rowan_credit_budget":False,"may_change_model_weights":False,
             "may_promote_TPOA_scientific_gate":False},
        "epistemic_status":"HYPOTHESIS_AND_FALSIFIER_PROPOSAL_ONLY",
    }
    proposal["packet_digest_sha256"]=digest(proposal)
    return proposal

def fetch_state():
    with urlopen(Request(STATE_URL,headers={"User-Agent":"AURA-ROWAN-RESEARCH-QUESTIONS/1"}),timeout=25) as r:
        blob=r.read(32001)
    if len(blob)>32000:raise ValueError("STATE_OVERSIZE")
    return json.loads(blob.decode("utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input")
    ap.add_argument("--output",default="research/rowan/LATEST_HYPOTHESES.json")
    args=ap.parse_args()
    try:
        state=json.loads(Path(args.input).read_text()) if args.input else fetch_state()
        obj=make_packet(state)
        out=Path(args.output)
        out.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n"
        if not out.exists() or out.read_bytes()!=raw:out.write_bytes(raw)
        print("AURA_ROWAN=HYPOTHESES_PREPARED_NO_PROVIDER_CALL")
        print("AURA_ROWAN_SOURCE_RUN="+str(obj["source"]["upstream_run"]))
        return 0
    except (OSError,ValueError,TypeError,KeyError):
        print("AURA_ROWAN=INPUT_GATE_HOLD")
        return 2

if __name__=="__main__":raise SystemExit(main())
