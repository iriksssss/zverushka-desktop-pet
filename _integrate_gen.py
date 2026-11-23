# -*- coding: utf-8 -*-
"""Встройка догенерированных поз (23.11) в assets/sprites/<питомец>.

Вход:  _gen/<pet>_<pose>.png (светло-серый фон #FBFBFB)
Выход: assets/sprites/<pet>/react_*.png

  cat_joy     -> cat/react_06.png     (ЗАМЕНА обрезанного кадра радости)
  cat_playful -> cat/react_07.png
  cat_jump    -> cat/react_19.png     (воздушный прыжок)
  cat_angry   -> cat/react_17.png     (злой: нахмурен, лапа поднята)
  ter_playful -> terrier/react_07.png (play-bow)
  ter_jump    -> terrier/react_19.png
  ter_angry   -> terrier/react_17.png (злой: нахмуренные брови)
  ham_angry2  -> hamster/react_20.png (злой: V-брови, лапы скрещены)

Запуск: python _integrate_gen.py
"""
import os
import sys

sys.path.insert(0, r'C:\pylib')
import numpy as np
from PIL import Image
from scipy import ndimage

BASE = os.path.dirname(os.path.abspath(__file__))

MAP = {
    'cat_joy':     ('cat', 'react_06'),
    'cat_playful': ('cat', 'react_07'),
    'cat_angry':   ('cat', 'react_17'),
    'cat_jump':    ('cat', 'react_19'),
    'ter_playful': ('terrier', 'react_07'),
    'ter_angry':   ('terrier', 'react_17'),
    'ter_jump':    ('terrier', 'react_19'),
    'ham_angry2':  ('hamster', 'react_20'),
}


def make_transparent(img):
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


def main():
    for src_name, (pet, out_name) in MAP.items():
        src = os.path.join(BASE, '_gen', src_name + '.png')
        out_dir = os.path.join(BASE, 'assets', 'sprites', pet)
        img = crop_bbox(keep_largest(make_transparent(Image.open(src))))
        if img is None:
            print('!! пусто:', src_name)
            continue
        path = os.path.join(out_dir, out_name + '.png')
        img.save(path)
        print('%-12s -> %s/%s  %dx%d' % (src_name, pet, out_name,
                                         img.width, img.height))


if __name__ == '__main__':
    main()
