# -*- coding: utf-8 -*-
"""Проверка standalone-запуска: виден ли хомяк на экране.

Делается скриншот и ищется кластер «хомячьего» оранжевого
(R>150, 70<G<190, B<120) в нижней части экрана (район панели задач).
Запускать ВНУТРЕННИМ python (PIL ImageGrab), НЕ Store-python из C:\pylib —
весь смысл теста в том, что C:\pylib на момент запуска зверушки недоступен.
"""
import sys

from PIL import ImageGrab

img = ImageGrab.grab()
w, h = img.size
px = img.load()

band_top = int(h * 0.86)          # нижняя часть экрана
hits = []
for y in range(band_top, h, 2):
    for x in range(0, w, 2):
        r, g, b = px[x, y][:3]
        if r > 150 and 70 < g < 190 and b < 120:
            hits.append((x, y))

if len(hits) < 40:
    print(f'FAIL: оранжевых точек {len(hits)} (< 40) — хомяк не виден')
    sys.exit(1)

xs = [p[0] for p in hits]
ys = [p[1] for p in hits]
cx = sum(xs) / len(xs)
cy = sum(ys) / len(ys)
spread_x = max(xs) - min(xs)
print(f'OK: хомяк виден, точек {len(hits)}, центр ~({cx:.0f},{cy:.0f}), '
      f'разброс по x {spread_x}px, экран {w}x{h}')
