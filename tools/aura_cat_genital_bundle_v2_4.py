#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, secrets
from datetime import datetime, timezone
from pathlib import Path

PACKET = Path('ritual/OSIRIS_CAT_TO_AURA_PACKET_v2_4.json')
OUT = Path('/tmp/aura-cat-v2-4/AURA_CAT_OSIRIS_GENITAL_BUNDLE_RESULT_v2_4.json')


def mk(cid, label, evidence, unresolved, continuity, imaging, neutral_label, bundle_fit, penalty, rationale, next_test):
    score = 3.0*evidence + 2.0*unresolved + 1.5*continuity + 1.5*imaging + 1.25*neutral_label + 1.75*bundle_fit - 2.0*penalty
    return {
        'id': cid,
        'label': label,
        'components': {
            'evidence_anchor': evidence,
            'unresolved_information_value': unresolved,
            'assemblage_continuity': continuity,
            'nondestructive_imaging_value': imaging,
            'neutral_label_search_value': neutral_label,
            'genital_bundle_fit': bundle_fit,
            'penalty': penalty
        },
        'score': round(score, 4),
        'rationale': rationale,
        'next_test': next_test
    }


def main():
    raw = PACKET.read_bytes()
    packet = json.loads(raw)
    packet_sha = hashlib.sha256(raw).hexdigest()
    seed = secrets.token_hex(16)

    candidates = [
        mk('CG53469_CURRENT_STATUS_AND_BASAL_MASS',
           'CG 53469 / JE 35425: current conservation file + basal mass + seams/joins/imaging',
           1.00, 1.00, 1.00, 1.00, 0.60, 1.00, 0.05,
           'Exact Mendes gold phallus sheath is now identified and photographed; the expanded basal mass is the highest-value unresolved physical feature and could resolve whether the object was a simple sheath or a larger genital bundle.',
           'Resolve current object card, high-resolution multi-view photographs, direct measurements, same-sheet vs attached element, seams/folds/support traces, repair history and any X-ray/CT/XRF/microscopy/3D records.'),
        mk('MENDES_1902_NEUTRAL_LABEL_SISTER_OBJECTS',
           'Mendes 1902: sister objects under neutral labels (ornament/foil/amulet/insert/fitting/fragment/cover)',
           0.95, 0.95, 1.00, 0.70, 1.00, 0.85, 0.08,
           'The burial assemblage is incomplete and Aura previously warned against literal catalogue labels. A scrotal/testicular cover or companion element may have been catalogued separately or generically.',
           'Reconstruct the full JE 35420–35425 neighborhood plus nearby Mendes 1902 accessions and search descriptions/plates for paired, rounded, folded, pouch-like or genital-adjacent gold elements.'),
        mk('GOLD_SCROTAL_TESTICULAR_COVER_CORPUS',
           'Egypt-wide corpus: gold scrotal/testicular covers, genital packets and paired genital elements',
           0.70, 1.00, 0.45, 0.65, 0.95, 1.00, 0.12,
           'The new target is not only a shaft but a possible genital bundle. Searching explicit and euphemistic catalogue classes can reveal comparative objects and manufacturing signatures.',
           'Search museum catalogues and excavation reports for scrotum/testicles/genitals/privates plus cover/sheath/foil/packet/amulet/ornament/fitting, then compare dimensions, seams and attachment architecture.'),
        mk('OSIRIS_MODULAR_GENITAL_BUNDLE_CORPUS',
           'Osiris figures with separately made penis + testicles / sockets / removable genital modules',
           0.82, 0.82, 0.55, 0.75, 0.50, 1.00, 0.10,
           'KHM 10077 already provides a positive control for separately made penis and testicles inserted into an Osiris figure. More examples can establish whether a standardized genital-bundle geometry existed.',
           'Collect all Osiris figures with separate genital modules, measure sockets and modules, record material, attachment method, repairs and whether penis and testicles are one piece or multiple pieces.'),
        mk('MENDES_MOULD_AND_MASTER_FORM_LINEAGE',
           'Mendes 1902 mould/master-form lineage across CG 53465–53469 and comparable gold genital covers',
           0.80, 0.80, 0.85, 0.60, 0.50, 0.78, 0.10,
           'Two sister objects in the same assemblage are explicitly described as formed against probable plaster moulds, making master-form analysis technically plausible for CG 53469.',
           'Compare fold topology, curvature, edge treatment, sheet thickness and tool/mould impressions across the Mendes gold set and external genital-cover controls.'),
        mk('ANUBIS_SONS_OF_HORUS_SEALED_RELIQUARY',
           'Anubis / Sons-of-Horus sealed or nested Osirian reliquary',
           0.70, 0.90, 0.35, 1.00, 0.75, 0.65, 0.12,
           'Protective custody remains an unresolved fallback if the Mendes object proves ordinary funerary equipment and no companion genital element survives in the assemblage.',
           'Prioritize Osirian containers with sealed/nested internal volumes for non-destructive imaging and provenance rewind.'),
        mk('DENDERA_RELIC_SIMULACRUM_CONTAINER',
           'Dendera Osirian relic-simulacrum container',
           0.72, 0.72, 0.30, 0.85, 0.70, 0.60, 0.10,
           'Dendera retains strong body-part/relic-simulacrum container traditions and remains a secondary route if Mendes resolves negatively.',
           'Audit object-level containers, vessels and simulacra with internal volumes and conservation imaging.'),
        mk('ABYDOS_OSIRIAN_RITUAL_CACHE',
           'Abydos Osirian ritual/foundation cache',
           0.75, 0.70, 0.35, 0.65, 0.80, 0.50, 0.12,
           'Abydos has very strong Osirian provenance but weaker genital-specific linkage than Mendes.',
           'Search secure Osirian deposits for neutral-labelled gold/foil/insert/body-part substitutes and sealed packets.'),
    ]
    ranked = sorted(candidates, key=lambda x: (-x['score'], x['id']))

    # Aura-style spread: deterministic within this run from packet hash + fresh seed.
    decks = {
      'WHAT_CAT_CARRIES': [
        ('BROKEN_GOLD_SKIN','Кот несёт не орган, а золотую кожу/оболочку — ищи, что было под ней и что к ней крепилось.'),
        ('BASAL_KNOT','Кот несёт узел у основания — распутай нижнюю массу раньше, чем уходить в другой город.'),
        ('PAIR_NOT_SINGLE','Кот несёт один предмет, но вопрос требует пары/комплекта — ищи соседний accession, а не дальнюю легенду.')],
      'WHERE_TO_SNIFF': [
        ('JE_NEIGHBORHOOD','Нюхай рядом с JE 35425: соседние номера, старые карточки, коробки комплекта, консервационные фото.'),
        ('NEUTRAL_LABELS','Нюхай нейтральные названия: ornament, foil, fitting, cover, fragment, amulet, insert.'),
        ('BACK_OF_PLATE','Смотри не только на фасад: оборот, основание, швы, свёрнутые края, подкладка, следы крепежа.')],
      'WHAT_ARE_THE_EGGS': [
        ('ATTACHED_BASAL_ELEMENT','Сначала проверь, не являются ли «яйца» уже частью смятой базальной массы CG 53469.'),
        ('SEPARATE_COMPANION','Если не являются — ищи отдельный парный золотой элемент из того же Mendes 1902 комплекта.'),
        ('RITUAL_DOUBLE','Если физической пары нет — проверь ритуальный дубль/заместитель и модульные Osiris genital sets.')],
      'CAT_EXIT': [
        ('STAY_MENDES','Коту пока не уходить из Mendes.'),
        ('FOLLOW_CONSERVATOR','Следующий проводник — консерватор и объектная карточка, не новый миф.'),
        ('FOLLOW_MOULD','Если найдёшь след формы — иди по мастер-форме к сестринским объектам.')]
    }
    cards=[]
    for role, opts in decks.items():
        h=hashlib.sha256((seed+packet_sha+role).encode()).digest()
        i=int.from_bytes(h[:8],'big')%len(opts)
        cid,txt=opts[i]
        cards.append({'role':role,'id':cid,'text':txt})

    top=ranked[0]
    second=ranked[1]
    result={
      'artifact_id':'AURA-CAT-OSIRIS-GENITAL-BUNDLE-2026-08-16-v2.4',
      'generated_at_utc':datetime.now(timezone.utc).isoformat(),
      'engine':'AURA_CAT_CONTEXTUAL_OFFLINE_V2_4',
      'nas_dependency':False,
      'seed_128bit_hex':seed,
      'packet_sha256':packet_sha,
      'question':packet['messenger']['question_ru'],
      'cards':cards,
      'ranked_routes':ranked,
      'primary_route':top,
      'secondary_route':second,
      'direct_answer_ru':(
        'Коту пока не уходить из Mendes. Сначала вернись к CG 53469 / JE 35425 и распутай расширенную массу у основания: '
        'нужны оборот, основание, швы, края, прямые размеры и консервационные/рентгеновские материалы. '
        'Одновременно прочеши соседние предметы Mendes 1902 под нейтральными названиями — ornament, foil, fitting, cover, fragment, amulet, insert — '
        'потому что мошонка/яички или второй золотой колпачок могли быть заведены отдельной карточкой. '
        'Если базальная масса не является частью генитального комплекта и соседнего элемента нет, переходи к корпусу модульных Osiris penis+testicles и только затем к sealed reliquary ветке.'
      ),
      'claim_ceiling':'AURA_OUTPUT_IS_SEARCH_PRIORITIZATION_ONLY',
      'safety':'ARCHIVE_CATALOGUE_CONSERVATION_NONDESTRUCTIVE_IMAGING_ONLY'
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('AURA_CAT_V2_4_OK')
    print('PRIMARY='+top['id'])
    print('SECONDARY='+second['id'])
    print('SEED='+seed)

if __name__=='__main__':
    main()
