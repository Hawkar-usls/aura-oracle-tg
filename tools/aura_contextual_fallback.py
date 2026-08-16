#!/usr/bin/env python3
"""NAS-independent, evidence-informed Aura fallback.

This is a research-prioritization heuristic with an Aura-style spread. It is not
prophecy, archaeology, or evidence of a physical location.
"""
from __future__ import annotations

import hashlib
import json
import math
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

PACKET = Path("ritual/OSIRIS_FULL_EVIDENCE_PACKET.json")
OUT = Path("/tmp/aura-contextual-artifact/AURA_CONTEXTUAL_OSIRIS_RESULT.json")


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def candidate(cid, label, locality, osiris, phallus, provenance, container,
              unresolved, blind_resonance, negative_control_penalty, rationale,
              disconfirm):
    # Transparent bounded score. No term is a probability.
    score = (
        3.0 * osiris
        + 3.0 * phallus
        + 2.5 * provenance
        + 1.5 * container
        + 1.0 * unresolved
        + 0.75 * blind_resonance
        - 2.0 * negative_control_penalty
    )
    return {
        "id": cid,
        "label": label,
        "locality": locality,
        "components": {
            "osiris_link": osiris,
            "phallus_specificity": phallus,
            "provenance_strength": provenance,
            "container_hidden_content_fit": container,
            "unresolved_information_value": unresolved,
            "blind_seed_resonance": blind_resonance,
            "negative_control_penalty": negative_control_penalty,
        },
        "score": round(score, 4),
        "rationale": rationale,
        "disconfirming_test": disconfirm,
    }


def main():
    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    seed_hex = secrets.token_hex(16)
    seed_int = int(seed_hex, 16)

    # Candidate definitions encode only relationships already present in the
    # evidence packet. Values are heuristic feature weights, not factual odds.
    candidates = [
        candidate(
            "MENDES_1902_CG53465_53469_NONLITERAL_GOLD_OBJECT",
            "Mendes 1902: CG 53465–53469, especially an object catalogued as amulet/substitute/fragment rather than 'phallus'",
            "Mendes / Tell el-Ruba",
            1.00, 1.00, 0.95, 0.55, 1.00, 1.00, 0.10,
            "The same burial combines explicit Osirian priestly context, a documented gold phallus sheath, an incomplete assemblage, and unresolved Cairo catalogue concordance. The blind Aura seed independently favoured a ritual substitute inside a priestly assemblage.",
            "Resolve all five CG object cards and show that every item is fully identified ordinary funerary equipment with complete provenance and no anomalous substitute/fragment/container relationship."
        ),
        candidate(
            "MENDES_SECONDARY_CACHE_OR_PRIESTLY_SUBSTITUTE",
            "Mendes: secondary cache / priestly assemblage containing an Osirian ritual substitute or unidentified body-part symbol",
            "Mendes / Tell el-Ruba",
            0.95, 0.85, 0.70, 0.85, 0.90, 1.00, 0.15,
            "Mendes is phallus-specific in Egyptian ritual geography; false/parallel burial traditions make secondary custody plausible as a search class; the blind spread pointed to secondary cache + priestly assemblage + ritual substitute.",
            "A complete excavation/conservation inventory showing no such secondary cache, sealed niche, unidentified substitute, or Osirian body-part object in the relevant contexts."
        ),
        candidate(
            "ANUBIS_SONS_OF_HORUS_SEALED_RELIQUARY",
            "Anubis / Sons of Horus associated sealed or nested reliquary with an independently Osirian provenance",
            "Egyptian funerary collections; locality to be resolved object-by-object",
            0.95, 0.45, 0.70, 1.00, 0.95, 0.85, 0.10,
            "BD17/BD151 make this the strongest protective-custody route; hidden sacred objects, chests, shrines and nested containers are materially attested controls. The missing edge is phallus-specific custody.",
            "Non-destructive imaging and object records consistently explain internal contents as ordinary embalming material, casting cores, repairs or unrelated organs with no phallus/body-part relation."
        ),
        candidate(
            "DENDERA_RELIC_SIMULACRUM_CONTAINER",
            "Dendera Osirian relic-simulacrum / body-part reliquary container",
            "Dendera",
            0.95, 0.70, 0.75, 0.95, 0.80, 0.80, 0.10,
            "Dendera preserves explicit Osirian relic-simulacrum and vessel traditions, making it a high-value container branch when morphology is unknown.",
            "Published object-by-object provenance and imaging show only ritual simulacra with no separate internal object or ambiguous body-part component."
        ),
        candidate(
            "ABYDOS_OSIRIAN_RITUAL_CACHE",
            "Abydos Osirian ritual/foundation cache containing a non-anatomically catalogued body-part substitute",
            "Abydos",
            1.00, 0.55, 0.90, 0.65, 0.75, 0.75, 0.10,
            "Abydos has exceptionally strong Osirian cult provenance and known ritual deposits; the weakness is lack of a current phallus-specific object link.",
            "A systematic accession/deposit audit yields no phallic/body-part substitute, unidentified insert, sealed packet or relevant amulet in secure Osirian contexts."
        ),
        candidate(
            "MEMPHIS_SAQQARA_GOLD_PHALLIC_AMULET_LINEAGE",
            "Memphis/Saqqara gold phallic amulet lineage and workshop/provenance chain",
            "Memphis / Saqqara",
            0.65, 0.95, 0.80, 0.30, 0.70, 0.75, 0.25,
            "Gold phallic objects exist here and provide a useful material/type control; direct identification with an Osirian relic is absent.",
            "Metrology, inscriptions and provenance establish these as ordinary standardized funerary/fertility amulets unrelated to Osirian relic traditions."
        ),
        candidate(
            "BM_1973_0501_23_INTERNAL_CONTENT",
            "BM 1973,0501.23 damaged-root terracotta insert: non-destructive internal-content check",
            "Probably Naukratis; British Museum",
            0.15, 1.00, 0.80, 0.80, 0.95, 0.55, 0.55,
            "Its internal state is genuinely unresolved and a damaged root makes imaging informative, but it lacks direct Osirian provenance and belongs to a broader terracotta insert technology.",
            "Radiography/micro-CT shows homogeneous ceramic or an ordinary production cavity with no independent nested object."
        ),
        candidate(
            "TERRACOTTA_MASTER_FORM_NETWORK",
            "Naukratis–Memphis terracotta phallus mould/mandrel network",
            "Naukratis / Memphis",
            0.20, 1.00, 0.75, 0.20, 0.80, 0.45, 0.45,
            "Serial mould production and detachable phallus technology are supported. This is valuable for metrology but currently weak for relic identity.",
            "Calibrated 3D comparison shows the apparent near-matches derive from different moulds/workshops and no stable master geometry exists."
        ),
        candidate(
            "MENDES_FEMALE_GENITAL_MIRROR_CONTROL",
            "Mendes female-genital/fertility mirror-control corpus",
            "Mendes / Tell el-Ruba",
            0.35, 0.05, 0.70, 0.20, 0.65, 0.30, 0.50,
            "This is a falsification control against phallus-only confirmation bias, not a leading relic hypothesis.",
            "The female-genital corpus remains materially and contextually distinct from Osirian body-part/relic traditions."
        ),
    ]

    ranked = sorted(candidates, key=lambda c: (-c["score"], c["id"]))
    top = ranked[0]

    # Aura-style cards are selected from evidence tensions using a reproducible
    # digest of the random seed + packet, but the primary target is score-led.
    packet_hash = hashlib.sha256(PACKET.read_bytes()).hexdigest()
    card_sets = {
        "PAST": [
            ("DECOY_PROVENANCE", "Ложные погребения / разветвлённый provenance"),
            ("RIVER_BRANCH", "Река — поздняя литературная ветка, не проверенная последняя координата"),
            ("RITUAL_RECONSTRUCTION", "Ритуальная реконструкция отделяет функцию от оригинала"),
        ],
        "OBSTACLE": [
            ("CATALOGUE_NAME_TRAP", "Предмет может называться не 'phallus', а амулетом, вставкой, фрагментом или заместителем"),
            ("PROVENANCE_FRACTURE", "Комплект Mendes 1902 неполон из-за раннего изъятия части находок"),
            ("CUSTODY_HANDOFF_UNKNOWN", "Неизвестен переход от враждебной к защитной custody"),
        ],
        "GUIDE": [
            ("CG_CONCORDANCE", "Разрешить CG 53465–53469 предмет за предметом"),
            ("NONDESTRUCTIVE_IMAGING", "Искать полости/вложенные объекты рентгеном/CT, не вскрытием"),
            ("FUNCTIONAL_LABEL_SEARCH", "Искать по функциональному имени: substitute / amulet / votive / insert / fragment"),
        ],
    }

    cards = []
    for role, options in card_sets.items():
        digest = hashlib.sha256((seed_hex + packet_hash + role).encode()).digest()
        idx = int.from_bytes(digest[:8], "big") % len(options)
        cid, text = options[idx]
        cards.append({"role": role, "id": cid, "text": text})
    cards.append({"role": "OUTCOME", "id": top["id"], "text": top["label"]})

    # Confidence here means separation of heuristic scores, not epistemic truth.
    margin = top["score"] - ranked[1]["score"]
    heuristic_separation = clamp(0.5 + margin / 8.0)

    result = {
        "artifact_id": "AURA-CONTEXTUAL-OSIRIS-RESULT-2026-08-16-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine": "AURA_CONTEXTUAL_OFFLINE_V1",
        "nas_dependency": False,
        "network_dependency": False,
        "seed_128bit_hex": seed_hex,
        "evidence_packet_sha256": packet_hash,
        "cards": cards,
        "primary_target": top,
        "ranked_candidates": ranked,
        "heuristic_score_margin_to_second": round(margin, 4),
        "heuristic_separation": round(heuristic_separation, 4),
        "direct_answer": (
            "Сначала проверяй Mendes 1902 и CG 53465–53469, но не ищи только слово 'phallus': "
            "приоритет — золотой/ритуальный предмет из осирианского жреческого комплекта, который каталогизирован как "
            "амулет, заместитель, вставка или неопределённый фрагмент. Разреши все пять карточек и provenance до объекта; "
            "если там нет такого кандидата, следующий маршрут — запечатанные/вложенные Osirian reliquaries Anubis/Sons-of-Horus класса."
        ),
        "claim_ceiling": "AURA_CONTEXTUAL_OUTPUT_IS_A_HEURISTIC_SEARCH_PRIORITY_NOT_LOCATION_EVIDENCE",
        "safety": "ARCHIVE_CATALOGUE_CONSERVATION_AND_NONDESTRUCTIVE_IMAGING_ONLY",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("AURA_CONTEXTUAL_OK")
    print("PRIMARY_TARGET=" + top["id"])
    print("PACKET_SHA256=" + packet_hash)


if __name__ == "__main__":
    main()
