# -*- coding: utf-8 -*-
"""Вырезать светлую кайму снаружи тёмного контура спрайтов тела.

Алгоритм: итеративно (до `passes` слоёв) прозрачным делаем светлые
пиксели тела, соседние с ПРОЗРАЧНОСТЬЮ. Каждый следующий слой уже не
касается оригинального края, поэтому максимальная глубина снятия =
`passes` пикселей — глубже контур не трогается.

Строй-гард: если белый пиксель, который изначально находился глубже
`passes` от края (брюшко/морда, замкнутые контуром), стал прозрачным —
скрипт АБОРТИТ, не сохранив файл.

part_* (частицы) и face_* (лица) не чистятся: их белоснежность —
смысловая, а не ореол.
"""
import os
import sys

sys.path.insert(0, r'C:\pylib')
import numpy as np
from PIL import Image
from scipy import ndimage

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   'assets', 'sprites',
                   sys.argv[1] if len(sys.argv) > 1 else 'hamster')
SKIP_PREFIX = ('part_', 'face_')
PASS = 3


def clean(a0, hi, sp, passes=PASS, hi_min=175, sp_max=100):
    a = a0.copy()
    for _ in range(passes):
        transp = (a == 0)
        if transp.all():
            break
        nb_t = np.zeros_like(transp)
        nb_t[1:, :] |= transp[:-1, :]
        nb_t[:-1, :] |= transp[1:, :]
        nb_t[:, 1:] |= transp[:, :-1]
        nb_t[:, :-1] |= transp[:, 1:]
        sel = (a > 0) & nb_t & (hi >= hi_min) & (sp <= sp_max)
        if not sel.any():
            break
        a[sel] = 0
    return a


def main():
    files = sorted(f for f in os.listdir(OUT)
                   if f.endswith('.png')
                   and not f.startswith(SKIP_PREFIX)
                   and f not in ('preview.png', 'icon.png'))
    for f in files:
        p = os.path.join(OUT, f)
        im = Image.open(p)
        a0 = np.asarray(im.getchannel('A'), dtype=np.uint8)
        rgb = np.asarray(im.convert('RGB'), dtype=np.int16)
        hi = rgb.max(2)
        sp = hi - rgb.min(2)
        # гард: белые пиксели глубже PASS от исходного края
        dist = ndimage.distance_transform_edt(a0 == 0)
        protected = (a0 > 0) & (hi > 230) & (sp < 25) & (dist > PASS)
        a1 = clean(a0, hi, sp)
        lost = int((protected & (a1 == 0)).sum())
        if lost:
            print('ABORT on %s: lost %d interior white px' % (f, lost))
            raise SystemExit(1)
        rgb_u8 = np.asarray(im.convert('RGB'))
        Image.fromarray(np.dstack([rgb_u8, a1]), 'RGBA').save(p)
        removed = int(((a0 > 0) & (a1 == 0)).sum())
        print('%-20s removed=%5d' % (f, removed))
    print('OK: rim cleaned, interior white intact')


main()


