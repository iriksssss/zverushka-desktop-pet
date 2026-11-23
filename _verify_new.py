# -*- coding: utf-8 -*-
"""Проверка новых механик (11.18):
1) высота КОНТЕНТА всех кадров лент одинакова (не «плывёт» на пиксели);
2) низ контента всех кадров на одной базовой линии;
3) grabbed/scared без спрайтов с рукой (react_11..13);
4) стартовый «пол» = верх панели задач;
5) в меню трея есть «На панель задач».
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, r'C:\pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

app = QApplication([])
from app import PetWindow          # noqa: E402
from sprites import get_aligned    # noqa: E402

win = PetWindow()
win.show()
pet, S = win.pet, win.pet.sprites
fails = []


def content_bbox(img):
    a = img.convertToFormat(QImage.Format.Format_Alpha8)
    w, h, bpl = a.width(), a.height(), a.bytesPerLine()
    arr = np.frombuffer(a.constBits(), np.uint8,
                        a.sizeInBytes()).reshape(h, bpl)[:, :w]
    ys, xs = np.where(arr > 8)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


# --- 1+2: по каждой ленте рендерим все кадры и меряем контент ---
# ЕДИНЫЙ размер: высота контента всегда body_height() = base_h, база = пол.
CH = int(win.pet.body_height())
print('== ленты: высота контента / базовая линия (единый размер) ==')
if win.pet.body_height() != win.pet.base_h:
    fails.append('body_height() != base_h — размер не единый')
for label, sheet in [('gait', S.GAIT), ('sit', S.SIT), ('sleep', S.SLEEP)] + \
                    [(k, v) for k, v in sorted(S.REACT.items())] + \
                    [('face_' + k, v) for k, v in sorted(S.FRONT.items())] + \
                    [('side_' + k, v) for k, v in sorted(S.SIDE.items())]:
    hs, bases = [], []
    for name in sheet:
        img, cx, pad = get_aligned(S.pet, name, CH, False)
        bb = content_bbox(img)
        if bb is None:
            fails.append(f'{label}/{name}: пустой кадр')
            continue
        hs.append(bb[3] - bb[1] + 1)
        bases.append(bb[3] - pad)  # y низа контента относительно «пола»
    spread_h = max(hs) - min(hs)
    spread_b = max(bases) - min(bases)
    tag = 'OK ' if spread_h <= 1 and spread_b <= 1 else 'FAIL'
    if tag == 'FAIL':
        fails.append(f'{label}: высота {spread_h}px / база {spread_b}px')
    print(f'{tag} {label:12s} h={min(hs)}..{max(hs)} база={min(bases)}..{max(bases)}')

# --- 3: рука не используется ---
hand = {'react_11', 'react_12', 'react_13'}
used = set(S.REACT.get('grabbed', [])) | set(S.SIDE.get('scared', []))
for d in (S.REACT, S.SIDE, S.FRONT):
    for k, v in d.items():
        if hand & set(v):
            fails.append(f'рука в маппинге {k}: {v}')
print('== grabbed:', S.REACT.get('grabbed'), ' scared:', S.SIDE.get('scared'))

# --- 4: пол = верх панели задач ---
bar = win._taskbar_rect()
expect = win.geom.bottom() - 4
if bar and win.geom.top() <= bar[1] <= win.geom.bottom() and \
        bar[1] > win.geom.bottom() - 120:
    expect = bar[1]
if abs(win.floor_y - expect) > 1:
    fails.append(f'floor_y={win.floor_y} != ожидаемый {expect}')
print('== taskbar:', bar, ' floor_y:', win.floor_y, ' ожидалось:', expect)

# --- 5: пункт меню ---
menu = win._tray.contextMenu()
titles = [a.text() for a in menu.actions()]
print('== меню:', titles)
if not any('панел' in t.lower() for t in titles):
    fails.append('в меню нет пункта возврата на панель задач')
if not any('уменьшить' in t.lower() for t in titles):
    fails.append('в меню нет пункта уменьшения фигурки')
if not any('увеличить' in t.lower() for t in titles):
    fails.append('в меню нет пункта увеличения фигурки')

# --- бонус: один кадр = одно изображение (кроссфейд удалён) ---
img = QImage(win.size(), QImage.Format_ARGB32_Premultiplied)
img.fill(0xFF202030)
p = QPainter(img)
win.pet.paint(p)
p.end()
print('== paint() отработал без кроссфейда')

# --- 6: облачко с фразой рисуется ---
import json as _json
ph_path = os.path.join('assets', 'sprites', 'phrases.json')
try:
    phrases = _json.load(open(ph_path, encoding='utf-8'))['phrases']
    print('== фраз в phrases.json:', len(phrases))
    if len(phrases) < 10:
        fails.append('мало фраз в phrases.json')
except Exception as e:
    fails.append(f'phrases.json не читается: {e}')
    phrases = []
win.pet.say('Ты молодец!')
if not win.pet.bubble_active():
    fails.append('облачко не активировалось')
win.pet.bubble_left = win.pet.bubble_dur - 0.5  # после fade-in
img2 = QImage(win.size(), QImage.Format_ARGB32_Premultiplied)
img2.fill(0xFF202030)
p = QPainter(img2)
win.pet.paint(p)
p.end()
# пиксели облачка над головой: ищем отличия от кадра без облачка
a1 = np.frombuffer(img.constBits(), np.uint8, img.sizeInBytes())
a2 = np.frombuffer(img2.constBits(), np.uint8, img2.sizeInBytes())
diff = int((a1 != a2).sum())
print('== облачко: изменённых байт кадра:', diff)
if diff < 1000:
    fails.append('облачко не нарисовалось (мало изменений кадра)')
win.pet.bubble_left = 0.0

# --- 7: цикл шага — середина ленты (без «разворотных» кадров) ---
print('== GAIT:', S.GAIT)
if len(S.GAIT) < 4:
    fails.append('цикл шага короче 4 кадров')

print()
if fails:
    print('ПРОВАЛЫ:')
    for f in fails:
        print(' -', f)
    sys.exit(1)
print('ВСЕ ПРОВЕРКИ ПРОШЛИ')
app.quit()
