#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from typing import Any

PACKET_SCHEMA = "janus.aura_spi.spiral_event.v1"
OUTPUT_SCHEMA = "janus.aura_spi.aura_reflection.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
WORDS = re.compile(r"[A-Za-zА-Яа-яЁё0-9_𓀀-𓿿]+", re.UNICODE)
STOP = {
    "the", "and", "for", "with", "from", "this", "that", "как", "это", "для", "что", "или",
    "наш", "наша", "они", "она", "его", "ему", "при", "без", "через", "будет", "быть",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def salient(text: str, n: int = 6) -> list[str]:
    tokens = [w.lower() for w in WORDS.findall(text) if len(w) >= 3]
    counts = Counter(w for w in tokens if w not in STOP)
    return [w for w, _ in counts.most_common(n)]


def validate(packet: dict[str, Any]) -> None:
    if packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("AURA_SPI_PACKET_SCHEMA_REQUIRED")
    if not isinstance(packet.get("session_id"), str) or not packet["session_id"]:
        raise ValueError("SESSION_ID_REQUIRED")
    if not isinstance(packet.get("generation"), int) or packet["generation"] < 1:
        raise ValueError("GENERATION_REQUIRED")
    intent = packet.get("intent_id")
    if not isinstance(intent, str) or HEX64.fullmatch(intent) is None:
        raise ValueError("INTENT_ID_LOWERCASE_HEX64_REQUIRED")
    if not isinstance(packet.get("trigger_text"), str) or not packet["trigger_text"].strip():
        raise ValueError("TRIGGER_TEXT_REQUIRED")
    constraints = packet.get("constraints")
    if not isinstance(constraints, dict):
        raise ValueError("CONSTRAINTS_REQUIRED")
    required_false = ["prediction_authority", "evidence_authority"]
    if any(constraints.get(k) is not False for k in required_false):
        raise ValueError("AURA_AUTHORITY_ESCALATION_REJECT")
    if constraints.get("may_not_replace_intent") is not True:
        raise ValueError("AURA_INTENT_REPLACEMENT_REJECT")


def reflect(packet: dict[str, Any]) -> dict[str, Any]:
    validate(packet)
    text = packet["trigger_text"]
    keys = salient(text)
    focus = ", ".join(keys) if keys else "исходная формулировка"
    seed = digest(packet)

    cards = [
        {
            "role": "MIRROR",
            "text": f"Зеркало: какие структуры повторяются вокруг [{focus}], если убрать названия и оставить отношения?",
        },
        {
            "role": "TENSION",
            "text": "Напряжение: какая самая привлекательная интерпретация здесь может быть ложной, и какой факт первым её разрушит?",
        },
        {
            "role": "COUNTERPOINT",
            "text": "Контрапункт: что предсказывала бы противоположная модель при тех же наблюдаемых данных?",
        },
        {
            "role": "NEXT_GATE",
            "text": "Следующий gate: выбери наблюдение или измерение, которое различит конкурирующие объяснения, а не просто добавит ещё одну похожую историю.",
        },
    ]
    reflection = " ".join(card["text"] for card in cards)
    return {
        "schema": OUTPUT_SCHEMA,
        "status": "REFLECTION_READY",
        "session_id": packet["session_id"],
        "generation": packet["generation"],
        "intent_id": packet["intent_id"],
        "source_ref": packet.get("source_ref"),
        "deterministic_seed_sha256": seed,
        "salient_terms": keys,
        "cards": cards,
        "reflection_text": reflection,
        "predictive_label_authority": False,
        "scientific_evidence_authority": False,
        "may_train_semantic_memory": True,
        "may_train_predictive_head": False,
        "may_resolve_forecast": False,
        "may_replace_primary_intent": False,
        "claim_ceiling": "SYMBOLIC_REFLECTION_AND_SEARCH_PRIORITIZATION_ONLY_NOT_PROPHECY_NOT_EVIDENCE",
    }


def main() -> int:
    try:
        raw = sys.stdin.read()
        packet = json.loads(raw)
        if not isinstance(packet, dict):
            raise ValueError("JSON_OBJECT_REQUIRED")
        sys.stdout.write(json.dumps(reflect(packet), ensure_ascii=False, sort_keys=True) + "\n")
        return 0
    except Exception as exc:
        sys.stderr.write(f"aura_habitat_spiral_peer_v1: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
