from tools.aura_habitat_spiral_peer_v1 import OUTPUT_SCHEMA, reflect


def packet():
    return {
        "schema": "janus.aura_spi.spiral_event.v1",
        "session_id": "s1",
        "generation": 1,
        "intent_id": "b" * 64,
        "source_ref": "TEST",
        "trigger_text": "black hole semantic predictive model with Habitat and DemiHead",
        "constraints": {
            "symbolic_reflection_only": True,
            "prediction_authority": False,
            "evidence_authority": False,
            "may_not_replace_intent": True,
        },
    }


def test_reflection_is_reproducible_and_non_authoritative():
    a = reflect(packet())
    b = reflect(packet())
    assert a["schema"] == OUTPUT_SCHEMA
    assert a["deterministic_seed_sha256"] == b["deterministic_seed_sha256"]
    assert a["reflection_text"] == b["reflection_text"]
    assert a["predictive_label_authority"] is False
    assert a["scientific_evidence_authority"] is False
    assert a["may_train_predictive_head"] is False
    assert a["may_resolve_forecast"] is False
    assert a["may_replace_primary_intent"] is False


def test_authority_escalation_rejected():
    bad = packet()
    bad["constraints"]["prediction_authority"] = True
    try:
        reflect(bad)
    except ValueError as exc:
        assert "AUTHORITY_ESCALATION" in str(exc)
    else:
        raise AssertionError("Aura authority escalation must fail closed")
