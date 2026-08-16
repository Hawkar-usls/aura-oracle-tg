#!/usr/bin/env python3
"""Generic Aura Oracle heuristic bridge for JANUS Shabitat.

This module is intentionally reflective and non-authoritative. It does not
predict future events, verify claims, grant permission, or write JANUS world
state. Given a bounded conversational request it returns a deterministic
symbolic spread plus practical heuristic lenses that a caller may ignore.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any, Mapping

REQUEST_SCHEMA = "aura.oracle.shabitat_heuristic_request.v1"
RESPONSE_SCHEMA = "aura.oracle.shabitat_heuristic_response.v1"
MODE = "REFLECTIVE_HEURISTIC"

CARD_LIBRARY = (
    {
        "id": "MIRROR",
        "name": "Mirror",
        "lens": "Separate what is observed from what is being interpreted.",
        "question": "Which assumption would change the reading most if it were false?",
        "caution": "Familiarity and repetition are not evidence.",
    },
    {
        "id": "THRESHOLD",
        "name": "Threshold",
        "lens": "Prefer a reversible next step before an irreversible commitment.",
        "question": "What is the smallest move that preserves the most future choices?",
        "caution": "Urgency does not create authority.",
    },
    {
        "id": "LANTERN",
        "name": "Lantern",
        "lens": "Look for the missing piece of information with the highest value.",
        "question": "What single observation would most reduce uncertainty?",
        "caution": "A heuristic score is not a probability.",
    },
    {
        "id": "FORK",
        "name": "Fork",
        "lens": "Keep at least one materially different alternative hypothesis alive.",
        "question": "What would a reasonable person who disagrees examine first?",
        "caution": "One attractive explanation should not erase competitors.",
    },
    {
        "id": "ANCHOR",
        "name": "Anchor",
        "lens": "Return to the user-stated goal and constraints before optimizing details.",
        "question": "Which part of the goal is actually non-negotiable?",
        "caution": "Optimization can drift away from the original purpose.",
    },
    {
        "id": "OPEN_DOOR",
        "name": "Open Door",
        "lens": "Offer a useful direction without closing the other person's choice space.",
        "question": "Can the same help be offered with an easy refusal or exit?",
        "caution": "Care is not capture.",
    },
    {
        "id": "THREAD",
        "name": "Thread",
        "lens": "Trace provenance: source, transformation, receipt, and present claim.",
        "question": "Where is the first point where lineage becomes uncertain?",
        "caution": "Multiple echoes may still be one source.",
    },
    {
        "id": "CAT",
        "name": "Cat",
        "lens": "When a loop becomes unproductive, change the input before arguing with the loop.",
        "question": "Would a lighter neutral bridge restore perspective here?",
        "caution": "A mood-reset heuristic is not treatment or proof.",
    },
)

KEYWORD_LENSES = (
    (
        ("uncertain", "uncertainty", "unknown", "неизвест", "сомнен", "может", "maybe"),
        "Keep competing explanations explicit and name the cheapest disconfirming check.",
    ),
    (
        ("choose", "decision", "реш", "выбор", "вариант", "option"),
        "Rank the next moves by reversibility, information gain, and cost of being wrong.",
    ),
    (
        ("conflict", "argument", "спор", "конфликт", "disagree"),
        "Steelman the strongest opposing interpretation before choosing a response.",
    ),
    (
        ("create", "creative", "иде", "созда", "design", "story", "истор"),
        "Generate one deliberately different branch instead of only refining the first idea.",
    ),
    (
        ("evidence", "source", "proof", "доказ", "источник", "verify", "провер"),
        "Separate source identity, observation, inference, and confidence into different fields.",
    ),
)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256(value: Any) -> str:
    raw = value if isinstance(value, str) else _canonical(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _require_bool_true(mapping: Mapping[str, Any], key: str) -> None:
    if type(mapping.get(key)) is not bool or mapping.get(key) is not True:
        raise ValueError(f"AURA_SHABITAT_CONSTRAINT_REQUIRED_TRUE:{key}")


def validate_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("AURA_SHABITAT_REQUEST_MUST_BE_OBJECT")
    if value.get("schema") != REQUEST_SCHEMA:
        raise ValueError("AURA_SHABITAT_REQUEST_SCHEMA_MISMATCH")
    if value.get("mode") != MODE:
        raise ValueError("AURA_SHABITAT_MODE_MISMATCH")

    request_id = str(value.get("request_id") or "").strip()
    speaker = str(value.get("speaker") or "").strip()
    topic = str(value.get("topic") or "").strip()
    question = str(value.get("question") or "").strip()
    context = str(value.get("context") or "").strip()
    if not request_id or len(request_id) > 160:
        raise ValueError("AURA_SHABITAT_REQUEST_ID_INVALID")
    if not speaker or len(speaker) > 120:
        raise ValueError("AURA_SHABITAT_SPEAKER_INVALID")
    if not topic or len(topic) > 800:
        raise ValueError("AURA_SHABITAT_TOPIC_INVALID")
    if not question or len(question) > 2400:
        raise ValueError("AURA_SHABITAT_QUESTION_INVALID")
    if len(context) > 8000:
        raise ValueError("AURA_SHABITAT_CONTEXT_TOO_LONG")

    constraints = value.get("constraints")
    if not isinstance(constraints, Mapping):
        raise ValueError("AURA_SHABITAT_CONSTRAINTS_REQUIRED")
    for key in (
        "advisory_only",
        "no_authority",
        "no_prediction_claim",
        "no_professional_advice",
    ):
        _require_bool_true(constraints, key)

    return {
        "schema": REQUEST_SCHEMA,
        "mode": MODE,
        "request_id": request_id,
        "speaker": speaker,
        "topic": topic,
        "question": question,
        "context": context,
        "constraints": dict(constraints),
    }


def _select_cards(request: Mapping[str, Any], count: int = 3) -> list[dict[str, str]]:
    seed = _sha256(request)
    ranked = []
    for card in CARD_LIBRARY:
        digest = _sha256(seed + ":" + card["id"])
        ranked.append((digest, card))
    ranked.sort(key=lambda item: item[0])
    return [dict(item[1]) for item in ranked[:count]]


def _keyword_heuristics(request: Mapping[str, Any]) -> list[str]:
    haystack = " ".join(
        str(request.get(key) or "").lower()
        for key in ("topic", "question", "context")
    )
    rows = [lens for needles, lens in KEYWORD_LENSES if any(needle in haystack for needle in needles)]
    if not rows:
        rows.append("Name one alternative interpretation and one low-cost observation that could distinguish it.")
    return rows[:3]


def build_response(request: Mapping[str, Any]) -> dict[str, Any]:
    clean = validate_request(dict(request))
    cards = _select_cards(clean)
    heuristic_rows = _keyword_heuristics(clean)
    response = {
        "schema": RESPONSE_SCHEMA,
        "status": "HEURISTIC_ONLY",
        "request_id": clean["request_id"],
        "engine": "AURA_SHABITAT_REFLECTIVE_V1",
        "deterministic_request_sha256": _sha256(clean),
        "cards": cards,
        "heuristics": heuristic_rows,
        "questions": [card["question"] for card in cards],
        "cautions": [card["caution"] for card in cards],
        "decision_authority": "CALLER_RETAINS_CHOICE",
        "permission_granted": False,
        "evidence_upgrade": False,
        "verification_claim": False,
        "prediction_claim": False,
        "professional_advice": False,
        "world_effect_requested": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "may_be_ignored": True,
        "claim_ceiling": "AURA_HEURISTIC_IS_REFLECTIVE_INPUT_NOT_EVIDENCE_COMMAND_PERMISSION_OR_PREDICTION",
    }
    return response


def _read_request(path: str) -> dict[str, Any]:
    raw = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8").read()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("AURA_SHABITAT_REQUEST_MUST_BE_OBJECT")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aura Oracle reflective heuristic bridge for JANUS Shabitat")
    parser.add_argument("--request", default="-", help="JSON request file or '-' for stdin")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        response = build_response(_read_request(args.request))
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(json.dumps({
            "schema": RESPONSE_SCHEMA,
            "status": "HEURISTIC_REJECTED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "permission_granted": False,
            "evidence_upgrade": False,
            "authority_delta": 0,
        }, ensure_ascii=False, sort_keys=True, indent=2 if args.pretty else None))
        return 2
    print(json.dumps(response, ensure_ascii=False, sort_keys=True, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
