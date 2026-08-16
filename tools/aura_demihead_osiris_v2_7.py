#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, secrets
from datetime import datetime, timezone
from pathlib import Path

PACKET = Path('ritual/OSIRIS_DEMIHEAD_TO_AURA_PACKET_v2_7.json')
OUT = Path('/tmp/aura-demihead-v2-7/AURA_DEMIHEAD_OSIRIS_INTERNAL_CONTENT_RESULT_v2_7.json')


def mk(cid, label, evidence, info, directness, nondestructive, target_specificity, comparative, penalty, rationale, next_test):
    score = (
        3.0 * evidence +
        2.2 * info +
        2.0 * directness +
        1.8 * nondestructive +
        2.2 * target_specificity +
        1.2 * comparative -
        2.0 * penalty
    )
    return {
        'id': cid,
        'label': label,
        'components': {
            'evidence_anchor': evidence,
            'information_value': info,
            'directness': directness,
            'nondestructive_value': nondestructive,
            'target_specificity': target_specificity,
            'comparative_value': comparative,
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
        mk(
            'CG53469_NONDESTRUCTIVE_INTERNAL_CONTENT',
            'CG 53469: X-ray / CT / micro-CT for material beneath the gold skin',
            1.00, 1.00, 1.00, 1.00, 1.00, 0.95, 0.03,
            'Louvre E 13463 establishes a direct material precedent for a mummified biological phallus inside a metallic sheet. This does not identify CG 53469, but it removes the empty-sheath default and makes internal imaging the highest-value discriminating test.',
            'Obtain or request radiography/CT/micro-CT of CG 53469 and classify the interior as empty/collapsed gold, homogeneous support, discrete organic-density core, mineral/resin core, or mixed/paired basal content.'
        ),
        mk(
            'CG53469_BASAL_TOPOLOGY_AND_SEAMS',
            'CG 53469: resolve the crumpled basal mass, joins, seams and bilateral geometry',
            0.98, 1.00, 0.95, 0.95, 1.00, 0.90, 0.03,
            'KHM 10077 and the Morimoto mummy demonstrate that penis+testicles/scrotum can be a separately formed genital module. The unresolved basal mass is therefore a target-specific morphology problem, not a decorative footnote.',
            'Acquire front/back/left/right/base macro photographs or 3D imaging and test whether the basal mass is continuous sheet, a separately attached element, a deliberately paired/sac-like form, or mere collapse/support residue.'
        ),
        mk(
            'CAIRO_CONSERVATION_HISTORY_AND_CURRENT_MASS',
            'Cairo conservation file: current mass, repairs, packing, removed contents and old photographs',
            0.95, 0.98, 0.92, 1.00, 1.00, 0.78, 0.04,
            'A conservation intervention could explain internal packing, missing content, changed shape or the present basal mass. Current mass versus Vernier 1927 and pre-restoration photographs can distinguish object history from ancient anatomy.',
            'Request the current measured mass, treatment history, X-ray history, packing/support records, pre-restoration images and notes about any material removed from inside or around the sheath.'
        ),
        mk(
            'MENDES_NONADJACENT_JE_COMPANION_SEARCH',
            'Mendes 1902: non-adjacent JE/CG companion element search',
            0.85, 0.90, 0.68, 0.70, 0.82, 0.85, 0.08,
            'The immediate CG 53470–53475 sequence is now a negative local control. If a companion genital element existed, it may have a non-adjacent inventory number, neutral label, or documented loss in the fractured 1902 assemblage.',
            'Search JE 354xx and Mendes 1902 records for neutral plaque/foil/fragment/cover/fitting/insert/amulet entries, especially paired or rounded gold-sheet pieces with compatible provenance and dimensions.'
        ),
        mk(
            'METAL_SHEATH_WITH_ORGANIC_CORE_COMPARATIVE_CORPUS',
            'Comparative corpus: preserved biological genital tissue inside metallic or gilded coverings',
            0.82, 0.78, 0.55, 0.72, 0.48, 1.00, 0.10,
            'Louvre E 13463 and BM EA74284 show that preserved/gilded genital tissue is materially attested. A broader corpus can improve interpretation of radiographic density and construction, but it is less target-specific than imaging CG 53469 itself.',
            'Collect published imaging, section descriptions, dimensions, wrapping architecture and conservation notes for E 13463, EA74284 and comparable genital mummy fragments.'
        ),
        mk(
            'MODULAR_OSIRIS_GENITAL_BUNDLE_COMPARISON',
            'Comparative corpus: modular Osiris penis + testicles/scrotum units',
            0.80, 0.75, 0.50, 0.65, 0.45, 1.00, 0.10,
            'KHM 10077 is a strong positive control for modular Osirian genital construction, but statue technology cannot by itself establish the anatomy of a funerary gold sheath.',
            'Measure and classify known detachable Osiris genital modules, sockets, bilateral basal morphology, attachment method and material, then compare only after CG 53469 imaging is obtained.'
        )
    ]
    ranked = sorted(candidates, key=lambda x: (-x['score'], x['id']))

    decks = {
        'PAST': [
            ('GOLD_SKIN_NOT_EMPTY_BY_DEFAULT', 'Раньше золотая оболочка могла казаться достаточным описанием предмета. Теперь это больше не безопасная исходная точка: реальный орган внутри металлической кожи материально засвидетельствован в другом музейном объекте.'),
            ('LOCAL_SISTER_SEARCH_CLOSED', 'Ближайший хвост Mendes уже прочёсан и дал отрицательный локальный контроль: отдельные подписанные яички рядом не лежат. Значит, главный вопрос вернулся внутрь самого CG 53469.'),
            ('BUNDLE_TECHNOLOGY_ATTESTED', 'Отдельно изготовленные penis+testicles/scrotum модули существуют в египетском материале. Поэтому смятое основание нельзя автоматически списывать на случайную деформацию.')
        ],
        'OBSTACLE': [
            ('CRUMPLED_BASE_HIDES_TOPOLOGY', 'Главное препятствие — смятая базальная масса: один фронтальный вид не различает анатомический компонент, сложенную фольгу, наполнитель и ремонт.'),
            ('CATALOGUE_NAME_IS_NOT_CONTENT_SCAN', 'Название «Enveloppe de phallus» описывает форму/функцию оболочки, но не сообщает, пустая ли она сейчас и была ли пустой изначально.'),
            ('CONSERVATION_HISTORY_CAN_MIMIC_ANATOMY', 'Ремонт, подкладка или старый наполнитель могут имитировать внутренний объект. Без истории консервации даже интересная плотность останется двусмысленной.')
        ],
        'GUIDE': [
            ('XRAY_FIRST', 'Иди не в следующий миф и не в следующий город. Иди сквозь золото: рентген/CT прежде всего.'),
            ('BASE_PLUS_SEAMS', 'Смотри основание как отдельную задачу: оборот, боковые виды, швы, свёрнутые края и связь базальной массы со стержнем.'),
            ('CONSERVATOR_IS_THE_GATEKEEPER', 'Следующий проводник — карточка хранения и консерватор: текущая масса, старые снимки, ремонты, удалённые или вложенные материалы.')
        ],
        'OUTCOME': [
            ('ORGANIC_CORE_BRANCH', 'Если внутри проявится дискретное органоподобное ядро, ветка резко сужается к биологическому/органическому содержимому, но всё ещё не к «реликвии Осириса» без независимой provenance-проверки.'),
            ('PAIRED_BASE_BRANCH', 'Если основание покажет намеренную парную/мешковидную структуру, приоритет получит genital-bundle гипотеза и сравнение с модульными penis+testicles/scrotum controls.'),
            ('EMPTY_OR_SUPPORT_BRANCH', 'Если CT покажет только сложенную фольгу или однородную подкладку, Mendes-гипотеза не ломается целиком, но конкретная ветка «орган под оболочкой» закрывается и поиск уходит в non-adjacent JE/provenance.')
        ]
    }

    cards = []
    for role, opts in decks.items():
        h = hashlib.sha256((seed + packet_sha + role).encode()).digest()
        idx = int.from_bytes(h[:8], 'big') % len(opts)
        cid, text = opts[idx]
        cards.append({'role': role, 'id': cid, 'text': text})

    result = {
        'artifact_id': 'AURA-DEMIHEAD-OSIRIS-INTERNAL-CONTENT-2026-08-16-v2.7',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine': 'AURA_DEMIHEAD_CONTEXTUAL_OFFLINE_V2_7',
        'nas_dependency': False,
        'messenger': 'DEMIHEAD',
        'cat_status': 'RESTING_NOT_SENT_TO_ORACLE',
        'seed_128bit_hex': seed,
        'packet_sha256': packet_sha,
        'question': packet['messenger']['question_ru'],
        'cards': cards,
        'ranked_routes': ranked,
        'primary_route': ranked[0],
        'secondary_route': ranked[1],
        'direct_answer_ru': (
            'ДемиХед, главный следующий след находится не рядом с CG 53469, а под его золотой оболочкой. '
            'Первым действием ставь рентген/CT или micro-CT самого CG 53469 и одновременно разрешай смятую базальную массу по обороту, боковым видам и швам. '
            'Ищи четыре взаимоисключающие класса: пустая/сложенная фольга; однородная подкладка или ремонт; дискретное органическое/смоляное ядро; отдельная парная или мешковидная базальная структура. '
            'Запасной след — консервационная история и текущая масса: старые снимки, ремонты, упаковка и сведения о когда-либо удалённом содержимом. '
            'Только если эти ветки ничего не дадут, возвращайся к non-adjacent Mendes JE companion search. '
            'Ни один из этих исходов сам по себе не аутентифицирует буквальную реликвию Осириса.'
        ),
        'claim_ceiling': 'AURA_OUTPUT_IS_SEARCH_PRIORITIZATION_ONLY_NOT_ARCHAEOLOGICAL_PROOF',
        'safety': 'ARCHIVE_CATALOGUE_CONSERVATION_NONDESTRUCTIVE_IMAGING_ONLY'
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('AURA_DEMIHEAD_V2_7_OK')
    print('PRIMARY=' + ranked[0]['id'])
    print('SECONDARY=' + ranked[1]['id'])
    print('SEED=' + seed)


if __name__ == '__main__':
    main()
