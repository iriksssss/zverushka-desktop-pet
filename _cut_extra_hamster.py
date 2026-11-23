# -*- coding: utf-8 -*-
"""Донарезка кадров хомяка из hamster_refs/msg17_part06.png (лист реакций).

react_18 — «расплющенный» хомяк (ряд 2, середина) -> поза испуга/crouch
react_19 — прыжок в воздухе (ряд 3, середина; тень под ним НЕ входит)

Координаты компонентов найдены анализом связных областей.
Запуск: python _cut_extra_hamster.py
"""
import os
import sys

sys.path.insert(0, r'C:\pylib')
import numpy as np
from PIL import Image
from scipy import ndimage

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, 'hamster_refs', 'msg17_part06.png')
OUT = os.path.join(BASE, 'assets', 'sprites', 'hamster')

# (имя, y0, y1, x0, x1) — bbox компонента на исходном листе 1600x1920
FRAMES = {
    'react_18': (497, 617, 424, 725),   # расплющенный (широкий и низкий)
    'react_19': (667, 873, 715, 907),   # прыжок в воздухе (без тени)
}


def make_transparent(img):
    """Светлый фон -> альфа 0 (flood fill от краёв, как в _cut_new_pet)."""
    arr = np.asarray(img.convert('RGB'), dtype=np.int16)
    hi = arr.max(axis=2)
    spread = hi - arr.min(axis=2)
    grayish = (hi >= 225) & (spread <= 40)
    labeled, n = ndimage.label(grayish)
    if n:
        border = set(np.unique(np.concatenate([
            labeled[0, :], labeled[-1, :], labeled[:, 0], labeled[:, -1]])))
        border.discard(0)
        bg = np.isin(labeled, list(border))
        a = np.where(bg, 0, 255).astype(np.uint8)
    else:
        a = np.full(arr.shape[:2], 255, dtype=np.uint8)
    return Image.fromarray(np.dstack([arr.astype(np.uint8), a]), 'RGBA')


def main():
    sheet = make_transparent(Image.open(SRC))
    for name, (y0, y1, x0, x1) in FRAMES.items():
        cell = sheet.crop((x0, y0, x1 + 1, y1 + 1))
        # подрезать по альфе с небольшим полем
        bbox = cell.getchannel('A').getbbox()
        if bbox:
            bx0, by0, bx1, by1 = bbox
            pad = 4
            cell = cell.crop((max(0, bx0 - pad), max(0, by0 - pad),
                              min(cell.width, bx1 + pad),
                              min(cell.height, by1 + pad)))
        path = os.path.join(OUT, name + '.png')
        cell.save(path)
        print('%-10s %4dx%-4d -> %s' % (name, cell.width, cell.height, path))


if __name__ == '__main__':
    main()
