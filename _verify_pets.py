# -*- coding: utf-8 -*-
"""Проверка спрайтов новых питомцев (terrier, cat):
1) оба питомца видны available_pets();
2) цикл шага GAIT = walk_1..walk_4 (4 кадра, как задумано);
3) все нужные ленты на месте (sit/sleep/FRONT/SIDE/REACT/part);
4) рендер get_aligned: высота контента всех кадров ровно заданная,
   низ контента на базовой линии (как у хомяка);
5) Pet полного цикла _pick_sheet не падает ни в одном состоянии.
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, r'C:\pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication          # noqa: E402

app = QApplication([])
from brain import Brain                             # noqa: E402
from pet import Pet                                 # noqa: E402
from sprites import PetSprites, available_pets, get_aligned  # noqa: E402

fails = []


def check(name, ok, extra=''):
    print(('  OK  ' if ok else ' FAIL ') + name + (f'  [{extra}]' if extra and not ok else ''))
    if not ok:
        fails.append(name)


pets = available_pets()
check('три питомца в меню', set(pets) >= {'hamster', 'terrier', 'cat'}, str(pets))

H = 142
for pet in ('terrier', 'cat'):
    print('== %s ==' % pet)
    S = PetSprites(pet)
    check(f'{pet}: GAIT 4 кадра', S.GAIT == ['walk_1', 'walk_2', 'walk_3', 'walk_4'],
          str(S.GAIT))
    check(f'{pet}: sit есть', len(S.SIT) >= 2, str(S.SIT))
    check(f'{pet}: sleep есть', len(S.SLEEP) >= 1)
    for face in ('normal', 'happy', 'loved', 'curious', 'surprised', 'shy'):
        check(f'{pet}: FRONT[{face}]', bool(S.FRONT.get(face)))
    for face in ('scared', 'lonely', 'angry'):
        check(f'{pet}: SIDE[{face}]', bool(S.SIDE.get(face)))
    for act in ('crouch', 'jump', 'grabbed', 'stretch'):
        check(f'{pet}: REACT[{act}]', bool(S.REACT.get(act)))
    # рендер каждой ленты: высота контента == H, низ на полу (pad_bottom==0)
    sheets = set(S.GAIT + S.SIT + S.SLEEP)
    for d in (S.FRONT, S.SIDE, S.REACT):
        for v in d.values():
            sheets.update(v)
    bad = []
    for name in sorted(sheets):
        img, cx, pad = get_aligned(pet, name, H)
        if img.height() != H or pad != 0 or img.width() < 10:
            bad.append(f'{name}:{img.width()}x{img.height()},pad={pad}')
    check(f'{pet}: единый размер рендера ({len(sheets)} лент)', not bad, '; '.join(bad))
    # частицы
    missing = [k for k, v in S.PART.items() if not S.has(v)]
    check(f'{pet}: все part_* на месте', not missing, str(missing))
    # полный цикл выбора кадров по всем действиям и лицам
    b = Brain()
    p = Pet(b)
    p.sprites = S
    ok = True
    try:
        for a in ('walk', 'run', 'sit', 'sleep', 'jump', 'crouch', 'stretch', 'grabbed'):
            for f in ('normal', 'happy', 'loved', 'curious', 'surprised',
                      'shy', 'scared', 'lonely', 'angry', 'sleepy'):
                        b.action, b.face = a, f
                        sheet, idx = p._pick_sheet()
                        get_aligned(pet, sheet[idx], H)
    except Exception as e:
        ok, err = False, repr(e)
    check(f'{pet}: все связки действие/лицо рендерятся', ok, err if not ok else '')

print('== масштабы поз / края экрана ==')
from sprites import POSE_SCALE  # noqa: E402

for pet in ('hamster', 'terrier', 'cat'):
    b = Brain()
    p = Pet(b)
    p.sprites = PetSprites(pet)
    p.base_h = 150.0
    if pet in POSE_SCALE:
        # у терьера/котика лежачие позы ужаты (у хомяка позы однородны,
        # его записи POSE_SCALE — только react_18/react_19)
        if pet != 'hamster':
            s16 = p._pose_scale('react_16')
            check(f'{pet}: лежачая поза ужата (react_16)', s16 < 0.95,
                  f'x{s16:.2f}')
        check(f'{pet}: сидячая поза = 1.0',
              p._pose_scale(p.sprites.SIT[0]) == 1.0)
        # все коэффициенты в разумных пределах
        vals = list(POSE_SCALE[pet].values())
        check(f'{pet}: POSE_SCALE в 0.5..1.3',
              all(0.5 <= v <= 1.3 for v in vals), str(vals))
    else:
        check(f'{pet}: хомяк без поправок',
              p._pose_scale('react_16') == 1.0)
    # отступ от краёв покрывает самый широкий кадр, вертикальный
    # clearance — самый высокий
    pad = p.edge_pad()
    check(f'{pet}: edge_pad разумный', 16 <= pad <= 200, f'{pad:.0f}')
    check(f'{pet}: top_clearance >= base_h', p.top_clearance() >= p.base_h)

print()
if fails:
    print('ПРОВАЛЕНО:', ', '.join(fails))
    sys.exit(1)
print('ВСЕ ПРОВЕРКИ НОВЫХ ПИТОМЦЕВ ПРОШЛИ')
