# -*- coding: utf-8 -*-
"""Нарезка сгенерированных листов нового питомца в assets/sprites/<питомец>.

Вход:  assets/raw_<питомец>/walk.png, sit.png, react_a.png, react_b.png,
       react_c.png, icon.png   (фон — однородный светло-серый #FBFBFB)
Выход: assets/sprites/<питомец>/walk_0..5, sit_0..1, react_*, sleep_0,
       icon.png/ico, part_* (копируются от хомяка — частицы универсальные).

Запуск: python _cut_new_pet.py terrier
"""
import os
import shutil
import sys

sys.path.insert(0, r'C:\pylib')
import numpy as np
from PIL import Image
from scipy import ndimage

BASE = os.path.dirname(os.path.abspath(__file__))
PET = sys.argv[1]
RAW = os.path.join(BASE, 'assets', 'raw_' + PET)
OUT = os.path.join(BASE, 'assets', 'sprites', PET)
os.makedirs(OUT, exist_ok=True)


def make_transparent(img):
    """Светло-серый фон -> альфа 0 (flood fill от краёв, как в make_sprites)."""
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


def keep_largest(img, min_area=80):
    """Оставить только крупные связные области (убрать осколки генерации)."""
    a = np.asarray(img.getchannel('A'), dtype=np.uint8).copy()
    if a.max() == 0:
        return img
    lab, n = ndimage.label(a > 0)
    if n <= 1:
        return img
    sizes = np.bincount(lab.ravel())
    keep = set(np.where(sizes >= max(min_area, sizes[1:].max() * 0.15))[0].tolist()) - {0}
    a[~np.isin(lab, list(keep))] = 0
    return Image.fromarray(np.dstack([np.asarray(img.convert('RGB')), a]), 'RGBA')


def crop_bbox(img, pad=4):
    bbox = img.getchannel('A').getbbox()
    if not bbox:
        return None
    x0, y0, x1, y1 = bbox
    return img.crop((max(0, x0 - pad), max(0, y0 - pad),
                     min(img.width, x1 + pad), min(img.height, y1 + pad)))


def split_row(img, n):
    w, h = img.size
    cw = w // n
    return [img.crop((i * cw, 0, (i + 1) * cw, h)) for i in range(n)]


def segments(projection, min_size=12, gap=6):
    """Диапазоны [start, end) ненулевых значений проекции."""
    nz = projection > 0
    segs, start = [], None
    for i, v in enumerate(nz):
        if v and start is None:
            start = i
        elif not v and start is not None:
            segs.append([start, i])
            start = None
    if start is not None:
        segs.append([start, len(nz)])
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < gap:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [s for s in merged if s[1] - s[0] >= min_size]


def auto_split(img):
    """Нарезка по проекции альфы: объекты могут пересекать середину листа
    (подушка сна у терьера вылезала за половину — split_row её резал)."""
    a = np.asarray(img.getchannel('A')) > 0
    rows = segments(a.sum(axis=1), min_size=20, gap=10)
    out = []
    for ry0, ry1 in rows:
        for cx0, cx1 in segments(a[ry0:ry1, :].sum(axis=0), min_size=12, gap=8):
            out.append(img.crop((cx0, ry0, cx1, ry1)))
    return out


def save(name, cell):
    c = crop_bbox(keep_largest(cell))
    if c is None:
        print('  !! пустая клетка:', name)
        return None
    c.save(os.path.join(OUT, name + '.png'))
    print('  %-12s %4dx%-4d' % (name, c.width, c.height))
    return c


def load(name):
    return make_transparent(Image.open(os.path.join(RAW, name)))


print('== %s: walk (4 кадра -> walk_1..4, крайние = копии для GAIT) ==' % PET)
cells = split_row(load('walk.png'), 4)
for i, cell in enumerate(cells):
    save('walk_%d' % (i + 1), cell)
shutil.copy(os.path.join(OUT, 'walk_1.png'), os.path.join(OUT, 'walk_0.png'))
shutil.copy(os.path.join(OUT, 'walk_4.png'), os.path.join(OUT, 'walk_5.png'))

print('== %s: sit (2 кадра) ==' % PET)
for i, cell in enumerate(split_row(load('sit.png'), 2)):
    save('sit_%d' % i, cell)

print('== %s: react_a -> react_00/01/02/05 ==' % PET)
for name, cell in zip(['react_00', 'react_01', 'react_02', 'react_05'],
                      split_row(load('react_a.png'), 4)):
    save(name, cell)

print('== %s: react_b -> react_06/08/14/15 ==' % PET)
for name, cell in zip(['react_06', 'react_08', 'react_14', 'react_15'],
                      split_row(load('react_b.png'), 4)):
    save(name, cell)

print('== %s: react_c -> react_16 + sleep_0 (авто-нарезка) ==' % PET)
cells_c = auto_split(load('react_c.png'))
if len(cells_c) != 2:
    print('  !! ожидалось 2 объекта, найдено %d — режу пополам' % len(cells_c))
    cells_c = split_row(load('react_c.png'), 2)
for name, cell in zip(['react_16', 'sleep_0'], cells_c):
    save(name, cell)

# react_03 — «второй кадр дыхания» для FRONT normal: копия react_00
shutil.copy(os.path.join(OUT, 'react_00.png'), os.path.join(OUT, 'react_03.png'))

print('== %s: icon ==' % PET)
_icon_raw = Image.open(os.path.join(RAW, 'icon.png')).convert('RGBA')
# у генерации «с прозрачным фоном» альфа вся ≤254 и есть полупрозрачный
# ореол: жёстко обнуляем слабую альфу, чтобы иконка не светилась в трее
_ia = np.asarray(_icon_raw.getchannel('A'))
_ia = np.where(_ia < 32, 0, 255).astype(np.uint8)
_icon_raw = Image.fromarray(np.dstack([np.asarray(_icon_raw.convert('RGB')), _ia]), 'RGBA')
icon = crop_bbox(keep_largest(_icon_raw))
icon.save(os.path.join(OUT, 'icon.png'))
icon.resize((64, 64), Image.LANCZOS).save(
    os.path.join(OUT, 'icon.ico'),
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
print('  icon.png/ico')

print('== %s: part_* (копия от хомяка) ==' % PET)
ham = os.path.join(BASE, 'assets', 'sprites', 'hamster')
for f in os.listdir(ham):
    if f.startswith('part_') and f.endswith('.png'):
        shutil.copy(os.path.join(ham, f), os.path.join(OUT, f))
        print(' ', f)

print('ГОТОВО:', OUT)
