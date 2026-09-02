#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main():
    module = load_json(".janus/JANUS_MODULE.json")
    bridge = load_json(".janus/JANUS_ORACLE_BRIDGE.json")
    organism = load_json(".janus/JANUS_ORGANISM_LINK.json")
    index = (ROOT / "index.html").read_text(encoding="utf-8")

    assert module["schema"] == "janus.repository_module.descriptor.v1"
    assert module["module_id"] == "AURA_ORACLE"
    assert module["repository"] == "Hawkar-usls/aura-oracle-tg"
    assert module["role"] == "SYMBOLIC_IMAGINATION_AND_CREATIVE_ADVISOR"
    assert module["actuator"]["authority_lane"] == "BRANCH_AND_VERIFY"
    assert module["actuator"]["direct_main_write"] is False
    assert module["actuator"]["autonomous_merge"] is False
    assert "AURA_ORACLE_MODULE_TEST" in module["verification_profiles"]

    assert organism["organ_key"] == "symbolic_imagination"
    assert organism["authority"] == "ZERO_EMPIRICAL_AUTHORITY"
    assert organism["authority_delta"] == 0

    assert bridge["gateway"]["repository"] == "Hawkar-usls/Janus"
    assert bridge["execution_law"] == "AURA_UI -> JANUS_GATEWAY -> PYTHIA_ORACLE -> AURA_UI"
    assert bridge["authority"]["empirical_authority"] is False
    assert bridge["authority"]["automatic_truth_promotion"] is False

    for endpoint in ("/api/get_user_state", "/api/generate_cards", "/api/interpret"):
        assert endpoint in index, f"AURA frontend lost JANUS endpoint {endpoint}"

    print("AURA_JANUS_ORACLE_MODULE=PASS")


if __name__ == "__main__":
    main()
