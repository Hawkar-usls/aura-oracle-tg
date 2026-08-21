#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from aura_5d_spiral_v2 import run as run_5d
from aura_semantic_predictive_core_v2 import AuraIndex, canonical_bytes

PACKET_SCHEMA = "janus.aura_spi.spiral_event.v1"
OUTPUT_SCHEMA = "janus.aura_spi.aura_reflection.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
WORDS = re.compile(r"[A-Za-zА-Яа-яЁёЇїІіЄєҐґ0-9_𓀀-𓿿]+", re.UNICODE)
STOP = {"the","and","for","with","from","this","that","как","это","для","что","или","наш","наша","они","она","его","ему","при","без","через","будет","быть"}


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def salient(text: str, n: int = 8) -> list[str]:
    toks = [w.lower() for w in WORDS.findall(text) if len(w) >= 3]
    counts = Counter(w for w in toks if w not in STOP)
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
    if constraints.get("prediction_authority") is not False or constraints.get("evidence_authority") is not False:
        raise ValueError("AURA_AUTHORITY_ESCALATION_REJECT")
    if constraints.get("may_not_replace_intent") is not True:
        raise ValueError("AURA_INTENT_REPLACEMENT_REJECT")


def reflect(packet: dict[str, Any]) -> dict[str, Any]:
    validate(packet)
    text = packet["trigger_text"]
    keys = salient(text)
    focus = ", ".join(keys) if keys else "исходная формулировка"
    seed = digest(packet)
    db_path = os.environ.get("AURA_INTELLIGENCE_DB", "state/aura_intelligence.sqlite3")
    db_available = Path(db_path).exists()

    deep = run_5d({
        "text": text,
        "generation": packet["generation"],
        "intent_id": packet["intent_id"],
        "source_ref": packet.get("source_ref"),
    }, db_path=db_path if db_available else None)

    semantic_hits = deep["axes"]["D4_INAIHR_ASSOCIATIVE"].get("semantic_hits", [])
    typing = deep.get("predictive_input", {}).get("suggestions", [])
    next_question = deep.get("information_gain")

    forecast_prior = None
    task_key = packet.get("forecast_task_key")
    if db_available and isinstance(task_key, str) and task_key:
        idx = AuraIndex(db_path)
        try:
            forecast_prior = idx.forecast_prior(task_key)
        finally:
            idx.close()

    recovered = deep.get("recovered_at_origin", [])
    recovered_text = " ".join(r["finding"] for r in recovered[:4]) if recovered else "Обратный проход не нашёл новой поддержанной зависимости."
    semantic_text = (
        f"Семантический корпус дал {len(semantic_hits)} контекстных кандидатов; они не являются доказательствами."
        if db_available else
        "Локальный семантический индекс ещё не подключён; 5D structural/reverse pass продолжает работать без синтетической подмены корпуса."
    )
    question_text = next_question.get("question") if isinstance(next_question, dict) else None

    cards = [
        {"role": "RECOVERED_AT_ORIGIN", "text": recovered_text},
        {"role": "MIRROR", "text": f"Зеркало: какие отношения повторяются вокруг [{focus}], если убрать имена объектов и оставить структуру?"},
        {"role": "HRAIN_STRUCTURAL", "text": "Структура: какие узлы, зависимости, gate, bottleneck или distant-link образуют LEFT_HRAIN-проекцию?"},
        {"role": "INAIHR_ASSOCIATIVE", "text": semantic_text},
        {"role": "TENSION", "text": "Напряжение: какая наиболее привлекательная интерпретация может быть ложной, и что первым её разрушит?"},
        {"role": "COUNTERPOINT", "text": "Контрапункт: что предсказывает противоположная модель при тех же наблюдаемых данных?"},
        {"role": "INFORMATION_GAIN", "text": question_text or "Следующий вопрос выбирается по ожидаемому уменьшению неопределённости, а не по драматичности."},
        {"role": "NEXT_GATE", "text": "Следующий gate: получить наблюдение, которое различит конкурирующие объяснения; Aura не может сама объявить прогноз сбывшимся."},
    ]
    reflection = " ".join(card["text"] for card in cards)

    return {
        "schema": OUTPUT_SCHEMA,
        "peer_version": "AURA_SEMANTIC_PREDICTIVE_SPIRAL_V2",
        "status": "REFLECTION_READY_SPIRAL_5D",
        "session_id": packet["session_id"],
        "generation": packet["generation"],
        "intent_id": packet["intent_id"],
        "source_ref": packet.get("source_ref"),
        "deterministic_seed_sha256": seed,
        "salient_terms": keys,
        "recovered_at_origin": recovered,
        "spiral_5d": deep,
        "spiral_geometry": {
            "cycle_model": False,
            "origin_n": deep["origin_state_hash"],
            "status": deep["spiral_status"],
            "origin_prime": deep["axes"]["D5_SPIRAL_ABSTRACTION"].get("origin_prime"),
            "law": "POSITION_MAY_REPEAT_BUT_STATE_MUST_ADVANCE",
        },
        "semantic_registry": {
            "db_available": db_available,
            "hit_count": len(semantic_hits),
            "hits": semantic_hits,
            "index_is_source_of_truth": False,
        },
        "predictive_input": {
            "enabled": True,
            "suggestions": typing,
            "auto_execute": False,
            "distinct_from_world_forecasting": True,
        },
        "information_gain": next_question,
        "predictive_ai": {
            "forecast_prior": forecast_prior,
            "aura_may_propose_probability": True,
            "aura_may_resolve_own_forecast": False,
            "forecast_probability_is_future_fact": False,
        },
        "cards": cards,
        "reflection_text": reflection,
        "may_train_semantic_memory": True,
        "may_train_typing_predictor": True,
        "predictive_label_authority": False,
        "scientific_evidence_authority": False,
        "may_train_predictive_head": False,
        "may_resolve_forecast": False,
        "may_replace_primary_intent": False,
        "command_authority": False,
        "raw_private_chain_of_thought_stored": False,
        "claim_ceiling": "SEMANTIC_REFLECTION_TYPING_PREDICTION_INFORMATION_GAIN_AND_FORECAST_PRIORS_NOT_PROPHECY_NOT_EVIDENCE",
    }


def main() -> int:
    try:
        packet = json.loads(sys.stdin.read())
        if not isinstance(packet, dict):
            raise ValueError("JSON_OBJECT_REQUIRED")
        sys.stdout.write(json.dumps(reflect(packet), ensure_ascii=False, sort_keys=True) + "\n")
        return 0
    except Exception as exc:
        sys.stderr.write(f"aura_habitat_spiral_peer_v2: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
