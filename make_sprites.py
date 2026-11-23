# -*- coding: utf-8 -*-
"""One-time sprite preprocessing.

Считывает листы из assets/raw (серо-белый фон, Kimi), делает фон
прозрачным (flood fill от краёв), режет кадры и сохраняет в
assets/sprites + sprite_index.json.

ВАЖНО: имена файлов Kimi НЕ совпадают с содержимым!
Истинный маппинг (проверен визуально 11.17):
  facesheet.png     (2048x1536)  сетка 4x3  - 12 лиц
  walk.png          (3072x1024)  8 кадров   - ходьба
  master.png        (2048x1024)  4 кадра    - референс-позы (dash.png = байт-дубль)
  reactionsheet.png (2048x1024)  4 кадра    - СИДИТ (3 сбоку + 1 спереди)
  particles.png     (2048x1024)  4 кадра    - СПИТ клубком
  sit_idle.png      (2048x1024)  сетка 4x2  - ЧАСТИЦЫ (7 штук)
  sleep.png         (1600x1920)  ~19 поз    - РЕАКЦИИ (росты 3/3/5/3/2/3)
  icon.png          (1024x1024)  лицо-иконка
"""
import json
import os
import sys

sys.path.insert(0, r'C:\pylib')
import numpy as np
from PIL import Image
from scipy import ndimage

BASE = os.path.dirname(os.path.abspath(__file__))
# python make_sprites.py [hamster|terrier] — листы берутся из assets/raw_<питомец>
PET = sys.argv[1] if len(sys.argv) > 1 else 'hamster'
RAW = os.path.join(BASE, 'assets', 'raw' if PET == 'hamster' else 'raw_' + PET)
OUT = os.path.join(BASE, 'assets', 'sprites', PET)
os.makedirs(OUT, exist_ok=True)


def make_transparent(img):
    """Фон Kimi -> альфа 0.

    Фон листа: (251-252, серый, разброс 1-3). Кремовый животик
    (255,243,205) тоже светлый, поэтому фон ищем flood fill-ом от
    краёв: сероватые пиксели, СВЯЗАННЫЕ с границей = фон. Животик
    замкнут тёмным контуром и не связан с фоном -> остаётся.
    """
    arr = np.asarray(img.convert('RGB'), dtype=np.int16)
    hi = arr.max(axis=2)
    spread = hi - arr.min(axis=2)
    grayish = (hi >= 238) & (spread <= 34)
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


def keep_largest(img, min_area=60):
    """Убрать мелкие осколки-артефакты Kimi в одной клетке."""
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
    a = img.getchannel('A')
    bbox = a.getbbox()
    if not bbox:
        return None
    x0, y0, x1, y1 = bbox
    return img.crop((max(0, x0 - pad), max(0, y0 - pad),
                     min(img.width, x1 + pad), min(img.height, y1 + pad)))


def split_row(img, n):
    w, h = img.size
    cw = w // n
    return [img.crop((i * cw, 0, (i + 1) * cw, h)) for i in range(n)]


def split_grid(img, cols, rows):
    w, h = img.size
    cw, ch = w // cols, h // rows
    out = []
    for ry in range(rows):
        for rx in range(cols):
            out.append(img.crop((rx * cw, ry * ch, (rx + 1) * cw, (ry + 1) * ch)))
    return out


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
    """Авто-нарезка листа: строки по гориз. проекции,
    кадры в строке по вертикальной."""
    a = np.asarray(img.getchannel('A')) > 0
    rows = segments(a.sum(axis=1), min_size=20, gap=10)
    out = []
    for ry0, ry1 in rows:
        for cx0, cx1 in segments(a[ry0:ry1, :].sum(axis=0), min_size=12, gap=8):
            out.append(img.crop((cx0, ry0, cx1, ry1)))
    return out


index = {}


index = {}


def save(name, cell):
    cell = keep_largest(cell)
    c = crop_bbox(cell)
    if c is None:
        return None
    c.save(os.path.join(OUT, name + '.png'))
    index[name] = [c.width, c.height]
    print('  %-24s %4dx%-4d' % (name, c.width, c.height))
    return c


print('facesheet.png (12 лиц)')
FACES = ['normal', 'happy', 'loved', 'surprised', 'scared', 'angry',
         'grumpy', 'sleepy', 'lonely', 'curious', 'shy', 'yawn']
fs = make_transparent(Image.open(os.path.join(RAW, 'facesheet.png')))
for i, cell in enumerate(split_grid(fs, 4, 3)):
    save('face_' + FACES[i], cell)

print('walk.png (8 кадров)')
for i, cell in enumerate(split_row(make_transparent(Image.open(os.path.join(RAW, 'walk.png'))), 8)):
    save('walk_%d' % i, cell)

print('master.png (референс)')
for i, cell in enumerate(split_row(make_transparent(Image.open(os.path.join(RAW, 'master.png'))), 4)):
    save('ref_%d' % i, cell)

print('reactionsheet.png -> SIT (4 кадра)')
for i, cell in enumerate(split_row(make_transparent(Image.open(os.path.join(RAW, 'reactionsheet.png'))), 4)):
    save('sit_%d' % i, cell)

print('particles.png -> SLEEP (4 клубка)')
for i, cell in enumerate(split_row(make_transparent(Image.open(os.path.join(RAW, 'particles.png'))), 4)):
    save('sleep_%d' % i, cell)

print('sit_idle.png -> PARTICLES (4x2)')
PARTS = ['heart_s', 'heart_b', 'zzz', 'smoke', 'dust', 'cloud', 'star', '']
ps = make_transparent(Image.open(os.path.join(RAW, 'sit_idle.png')))
for i, cell in enumerate(split_grid(ps, 4, 2)):
    if i < len(PARTS) and PARTS[i]:
        save('part_' + PARTS[i], cell)

print('sleep.png -> REACTIONS (авто-нарезка)')
rs = make_transparent(Image.open(os.path.join(RAW, 'sleep.png')))
cells = auto_split(rs)
print('  найдено %d поз' % len(cells))
for i, cell in enumerate(cells):
    save('react_%02d' % i, cell)

print('icon.png')
icon = keep_largest(make_transparent(Image.open(os.path.join(RAW, 'icon.png'))))
save('icon', crop_bbox(icon))
Image.open(os.path.join(OUT, 'icon.png')).resize((64, 64)).save(
    os.path.join(OUT, 'icon.ico'), sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
print('  icon.ico (16/32/48/64)')

with open(os.path.join(OUT, 'sprite_index.json'), 'w', encoding='utf-8') as f:
    json.dump(index, f, indent=1, ensure_ascii=False)
print('total sprites: %d' % len(index))

# превью для быстрой проверки
imgs = [(n, Image.open(os.path.join(OUT, n + '.png'))) for n in sorted(index)]
cell_w = cell_h = 170
per_row = 8
grid = Image.new('RGBA', (cell_w * per_row, cell_h * ((len(imgs) + per_row - 1) // per_row)), (30, 30, 40, 255))
for i, (n, im) in enumerate(imgs):
    s = min(1.0, 150.0 / max(im.width, im.height))
    im2 = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.NEAREST)
    x, y = (i % per_row) * cell_w, (i // per_row) * cell_h
    grid.paste(im2, (x + (cell_w - im2.width) // 2, y + (cell_h - im2.height) // 2), im2)
grid.save(os.path.join(OUT, 'preview.png'))
print('preview: assets/sprites/preview.png')

