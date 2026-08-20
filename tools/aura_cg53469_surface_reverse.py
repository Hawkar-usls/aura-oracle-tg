#!/usr/bin/env python3
"""Transparent bounded AURA heuristic for CG 53465-53469 surface-vs-interior priority.

This is a research-prioritization heuristic. It is not prophecy, archaeology,
or evidence that CG 53469 is a literal relic of Osiris.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

PACKET = Path("ritual/CG53465_53469_SURFACE_READING_AURA_QUESTION_2026-08-20.json")
OUT = Path("artifacts/AURA_CG53469_SURFACE_REVERSE_RESULT_2026-08-20.json")

WEIGHTS = {
    "information_gain": 3.0,
    "reversibility": 2.5,
    "prerequisite_fit": 2.0,
    "directness": 2.0,
    "availability": 1.5,
    "independence": 1.0,
    "cost_permission_penalty": -1.5,
}

CANDIDATES = [
    {
        "id": "SURFACE_TEXT_ICONOGRAPHY_CONCORDANCE",
        "label": "Recover and transcribe the complete non-invasive surface record of CG 53465-53469, prioritizing CG 53469 front/back/side and raking-light/RTI plus Vernier text, then bind every mark to the correct object number.",
        "information_gain": 1.00,
        "reversibility": 1.00,
        "prerequisite_fit": 1.00,
        "directness": 1.00,
        "availability": 0.80,
        "independence": 0.95,
        "cost_permission_penalty": 0.15,
        "disconfirming_condition": "High-resolution views plus catalogue descriptions show no readable inscription or distinctive object-specific iconography on CG 53469 and neighbouring motifs are fully generic funerary decoration."
    },
    {
        "id": "FULL_CATALOGUE_TEXT_ONLY",
        "label": "Recover only the complete Vernier catalogue prose for CG 53465-53469.",
        "information_gain": 0.82,
        "reversibility": 1.00,
        "prerequisite_fit": 0.90,
        "directness": 0.85,
        "availability": 0.95,
        "independence": 0.90,
        "cost_permission_penalty": 0.05,
        "disconfirming_condition": "The entries contain no inscription/iconography information beyond dimensions, material, manufacture and condition."
    },
    {
        "id": "WHOLE_ASSEMBLAGE_ICONOGRAPHY_ONLY",
        "label": "Classify visible motifs across CG 53465-53469 without obtaining new high-resolution views.",
        "information_gain": 0.70,
        "reversibility": 1.00,
        "prerequisite_fit": 0.65,
        "directness": 0.80,
        "availability": 1.00,
        "independence": 0.70,
        "cost_permission_penalty": 0.00,
        "disconfirming_condition": "Current plate resolution cannot separate meaningful signs from decoration or damage."
    },
    {
        "id": "CUSTODY_PROVENANCE_HANDOFF",
        "label": "Continue archival custody/provenance reconstruction before surface work.",
        "information_gain": 0.72,
        "reversibility": 1.00,
        "prerequisite_fit": 0.55,
        "directness": 0.65,
        "availability": 0.65,
        "independence": 1.00,
        "cost_permission_penalty": 0.20,
        "disconfirming_condition": "Custody is resolved but does not answer whether the object itself carries inscription/iconography."
    },
    {
        "id": "INTERNAL_IMAGING_CT_XRAY",
        "label": "Prioritize radiography/X-ray/CT of CG 53469.",
        "information_gain": 0.95,
        "reversibility": 0.95,
        "prerequisite_fit": 0.35,
        "directness": 0.75,
        "availability": 0.20,
        "independence": 1.00,
        "cost_permission_penalty": 0.75,
        "disconfirming_condition": "Imaging shows only collapsed/support/conservation material with no distinct internal object; surface remains unread."
    }
]


def score(c):
    return round(sum(WEIGHTS[k] * c[k] for k in WEIGHTS), 4)


def main():
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    packet_sha = hashlib.sha256(PACKET.read_bytes()).hexdigest()
    ranked = []
    for c in CANDIDATES:
        item = dict(c)
        item["score"] = score(item)
        ranked.append(item)
    ranked.sort(key=lambda x: (-x["score"], x["id"]))
    top = ranked[0]

    result = {
        "artifact_id": "AURA-CG53469-SURFACE-REVERSE-RESULT-2026-08-20-v1",
        "engine": "AURA_CONTEXTUAL_OFFLINE_TRANSPARENT_HEURISTIC",
        "question_artifact": str(PACKET),
        "question_sha256": packet_sha,
        "cards": [
            {"role": "PAST", "id": "OBJECT_IDENTITY_LOCKED", "text": "CG 53469 is the small object labelled 53.469; CG 53466 is the large central breast ornament."},
            {"role": "OBSTACLE", "id": "SURFACE_LEGIBILITY_GAP", "text": "The current historical plate cannot support a reliable inscription transcription, so decoration, damage and writing cannot yet be cleanly separated."},
            {"role": "GUIDE", "id": "SURFACE_FIRST_NONDESTRUCTIVE_READING", "text": "Read the exterior before the interior: high-resolution front/back/side plus raking-light/RTI and the full Vernier entries for the whole gold assemblage."},
            {"role": "OUTCOME", "id": "OBJECT_LEVEL_TEXT_ICONOGRAPHY_CONCORDANCE", "text": "Bind every readable mark, figure and formula to the correct CG object, then compare CG 53469 against the owner's independently attested titles and the neighbouring funerary program."}
        ],
        "primary_next_step": top["id"],
        "primary_next_step_text": top["label"],
        "why_this_first": "It is the strongest prerequisite gate: fully non-destructive, reversible, directly tests the user's surface-answer hypothesis, catches object-number misbinding, and can either reveal an inscription/iconographic program or falsify that route before requesting harder-to-obtain internal imaging.",
        "janus_reverse_operator": "KNOWN_OWNER_AND_BURIAL -> LOCK_OBJECT_NUMBERS -> WHOLE_ASSEMBLAGE_SURFACE_RECORD -> CG53469_SPECIFIC_MARKS -> COMPARE_WITH_INDEPENDENT_TITLES_AND_FUNERARY_FORMULAE -> ONLY_THEN_INTERNAL_IMAGING_IF_UNRESOLVED",
        "disconfirming_condition": top["disconfirming_condition"],
        "do_not_do_yet": [
            "Do not transcribe unreadable pixels as hieroglyphs.",
            "Do not treat CG 53466 as CG 53469.",
            "Do not infer literal Osiris relic identity from Nesbanebdjedet's Osirian priestly title.",
            "Do not make CT the first gate while the exterior and catalogue text remain incompletely read."
        ],
        "ranked_candidates": ranked,
        "claim_ceiling": "AURA_REFLECTIVE_RESEARCH_HEURISTIC_NOT_PROPHECY_OR_RELIC_EVIDENCE",
        "authority_delta": 0,
        "source_packet_boundaries_preserved": packet["hard_boundaries"]
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("AURA_OK")
    print("PRIMARY=" + top["id"])
    print("SCORE=" + str(top["score"]))


if __name__ == "__main__":
    main()
