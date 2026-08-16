#!/usr/bin/env python3
import json, os, random, hashlib
from pathlib import Path
from datetime import datetime, timezone

QUESTION_PATH = Path('ritual/OSIRIS_LOCATION_BLIND_QUESTION.json')
OUT = Path('/tmp/aura-offline/AURA_OFFLINE_OSIRIS_LOCATION_RESULT.json')

# Neutral symbolic search archetypes intentionally avoid current project favourites
# such as Mendes, named museum accession numbers, or previously promoted candidates.
DECK = [
    {
        'id':'SEALED_SHRINE',
        'emoji':'🗝️',
        'label':'Запечатанное святилище',
        'answer':'Сначала проверяй небольшой запечатанный культовый контейнер или внутреннюю нишу святилища, особенно объект, который выглядит завершённым снаружи, но имеет закрытый внутренний объём.'
    },
    {
        'id':'FOUNDATION_CACHE',
        'emoji':'🧱',
        'label':'Закладной тайник',
        'answer':'Сначала проверяй старые храмовые закладные депозиты и небольшие ритуальные тайники в основании сооружений — не главный саркофаг, а вторичный закрытый комплект.'
    },
    {
        'id':'HOLLOW_STATUETTE',
        'emoji':'🗿',
        'label':'Полая статуэтка',
        'answer':'Сначала проверяй полую культовую статуэтку или фигурку с закрытым технологическим отверстием: возможное содержимое должно искаться не снаружи, а внутри корпуса.'
    },
    {
        'id':'MUSEUM_FRAGMENT',
        'emoji':'🏺',
        'label':'Неприметный музейный фрагмент',
        'answer':'Сначала проверяй неопределённый маленький музейный фрагмент из старых раскопок, который был каталогизирован как деталь, амулет или обломок без точной функции.'
    },
    {
        'id':'BODY_PART_RELIQUARY',
        'emoji':'📦',
        'label':'Реликварий части тела',
        'answer':'Сначала проверяй сосуд или реликварий, связанный с отдельной частью тела: важнее надпись и контекст контейнера, чем внешнее сходство содержимого с фаллосом.'
    },
    {
        'id':'WRAPPED_PACKET',
        'emoji':'🧵',
        'label':'Свёрток в погребальном комплекте',
        'answer':'Сначала проверяй небольшой льняной или смоляной свёрток внутри погребального комплекта, особенно тот, который никогда не разворачивали и исследовали только визуально.'
    },
    {
        'id':'SECONDARY_TOMB_CACHE',
        'emoji':'⚱️',
        'label':'Вторичный тайник',
        'answer':'Сначала проверяй вторичный погребальный тайник или переиспользованную камеру, куда культовый предмет мог быть перенесён позднее, уже после первоначального погребения.'
    },
    {
        'id':'RITUAL_SUBSTITUTE',
        'emoji':'🪙',
        'label':'Ритуальный заместитель',
        'answer':'Сначала проверяй предмет, который каталогизирован как ритуальный заместитель, амулет или символ, а не как анатомическая деталь: искомое могло сохраниться под функциональным, а не буквальным названием.'
    },
    {
        'id':'CONSERVATION_ANOMALY',
        'emoji':'🔬',
        'label':'Аномалия на старом рентгене',
        'answer':'Сначала ищи старые рентгенограммы и conservation records закрытых культовых объектов: приоритет имеет отдельная внутренняя плотная аномалия, не объясняемая ремонтом или технологией изготовления.'
    },
    {
        'id':'PRIESTLY_ASSEMBLAGE',
        'emoji':'📿',
        'label':'Жреческий комплект',
        'answer':'Сначала проверяй полный комплект высокопоставленного осирианского жреца, включая мелкие амулеты и детали, которые были отделены от мумии при ранней расчистке и позже разошлись по каталогам.'
    },
    {
        'id':'WALL_CHAMBER',
        'emoji':'🧱',
        'label':'Ниша в стене',
        'answer':'Сначала проверяй документированные закрытые ниши и камеры в стенах храмовых или погребальных сооружений, где культовый предмет мог быть намеренно спрятан для защиты.'
    },
    {
        'id':'JAR_WITH_INSERT',
        'emoji':'🏺',
        'label':'Сосуд с вложением',
        'answer':'Сначала проверяй закрытый сосуд или банку с отдельным внутренним вложением, особенно если внешний объект связан с Анубисом, погребальной защитой или восстановлением тела.'
    }
]

qdoc = json.loads(QUESTION_PATH.read_text(encoding='utf-8'))
seed_bytes = os.urandom(16)
seed_hex = seed_bytes.hex()
seed_int = int.from_bytes(seed_bytes, 'big')
rng = random.Random(seed_int)

# Four-stage Aura-style spread, but only the outcome determines the direct search seed.
spread = rng.sample(DECK, 4)
roles = ['ПРОШЛОЕ','ПРЕГРАДА','СОВЕТ','ИТОГ']
cards = [
    {'role': role, 'id': card['id'], 'emoji': card['emoji'], 'label': card['label']}
    for role, card in zip(roles, spread)
]
outcome = spread[-1]

result = {
    'artifact_id':'AURA-OFFLINE-OSIRIS-LOCATION-BLIND-RESULT-2026-08-16-v1',
    'generated_at_utc':datetime.now(timezone.utc).isoformat(),
    'engine':{
        'mode':'AURA_OFFLINE_FALLBACK_V1',
        'nas_required':False,
        'network_required':False,
        'selection':'Python random.Random seeded from os.urandom(128-bit)',
        'seed_hex':seed_hex,
        'deck_size':len(DECK),
        'draw_without_replacement':4
    },
    'question_artifact':str(QUESTION_PATH),
    'question_sha256':hashlib.sha256(qdoc['question'].encode('utf-8')).hexdigest(),
    'cards':cards,
    'answer':outcome['answer'],
    'answer_class':outcome['id'],
    'claim_ceiling':'SYMBOLIC_BLIND_SEARCH_SEED_NOT_PHYSICAL_LOCATION_EVIDENCE'
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('AURA_OFFLINE_FALLBACK_OK')
