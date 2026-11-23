# -*- coding: utf-8 -*-
"""Визуальная проверка: сетка поз для каждого питомца, рендер через
РЕАЛЬНЫЙ Pet.paint (как в приложении). Плюс «линейка» всех поз на одной
линии пола — контроль, что фигурка выглядит одинакового размера.
Сохраняет _grid_<pet>.png и _size_<pet>.png. Запуск: store-python."""
import os
import sys

sys.path.insert(0, r'C:\pylib')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor, QFont, QPen
from PySide6.QtCore import QPointF, Qt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brain import Brain
from pet import Pet
from sprites import PetSprites

H = 150.0
POSES = [
    ('sit', 'normal', 0), ('sit', 'happy', 0), ('sit', 'loved', 0),
    ('sit', 'content', 0), ('sit', 'playful', 0),
    ('walk', 'normal', 0), ('walk', 'normal', 2), ('run', 'normal', 1),
    ('sleep', 'sleepy', 0), ('grabbed', 'surprised', 0),
    ('fall', 'surprised', 0),
    ('sit', 'lonely', 0), ('sit', 'angry', 0), ('jump', 'happy', 1),
    ('crouch', 'scared', 0),
]
CELL = 300


def make_pet(pet_name):
    b = Brain()
    pet = Pet(b)
    pet.sprites = PetSprites(pet_name)
    pet.base_h = H
    return pet, b


def render_cell(pet, b, action, face, frame):
    b.action, b.face, b.direction, b.time = action, face, 1, 0.0
    b.action_left = 99.0
    pet.body_frame = float(frame)
    pet.particles = []
    pet.bubble_text = None
    pet.pos = QPointF(CELL / 2, CELL - 30)
    img = QImage(CELL, CELL, QImage.Format.Format_ARGB32)
    img.fill(QColor(246, 242, 236, 255))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(QPen(QColor(180, 170, 160), 1))
    p.drawLine(0, CELL - 30, CELL, CELL - 30)
    pet.paint(p)
    p.end()
    return img


def grid(pet_name):
    pet, b = make_pet(pet_name)
    cols = 4
    rows = (len(POSES) + cols - 1) // cols
    w, h = CELL * cols, CELL * rows + 26
    sheet = QImage(w, h, QImage.Format.Format_ARGB32)
    sheet.fill(QColor(255, 255, 255, 255))
    p = QPainter(sheet)
    p.setFont(QFont('Segoe UI', 11))
    p.setPen(QColor(20, 20, 20))
    for i, (a, f, fr) in enumerate(POSES):
        ri, ci = divmod(i, cols)
        p.drawText(ci * CELL + 6, 26 + ri * CELL + 14, '%s/%s f%d' % (a, f, fr))
        p.drawImage(ci * CELL, 26 + ri * CELL,
                    render_cell(pet, b, a, f, fr))
    p.end()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '_grid_%s.png' % pet_name)
    sheet.save(out)
    print('saved', out)


def size_strip(pet_name):
    """Все позы в ряд на одной линии пола с горизонтальной линейкой —
    контроль, что фигурки одного визуального размера."""
    pet, b = make_pet(pet_name)
    names = []
    for a, f, fr in POSES:
        b.action, b.face, b.direction, b.time = a, f, 1, 0.0
        b.action_left = 99.0
        pet.body_frame = float(fr)
        sheet_, idx = pet._pick_sheet()
        names.append(('%s/%s' % (a, f), sheet_[idx]))
    cw = 260
    w, h = cw * len(names), 360
    sheet = QImage(w, h, QImage.Format.Format_ARGB32)
    sheet.fill(QColor(255, 255, 255, 255))
    p = QPainter(sheet)
    p.setFont(QFont('Segoe UI', 9))
    floor = 330
    for k in range(5):
        y = floor - H * k * 0.25
        p.setPen(QPen(QColor(200, 60, 60, 120), 1, Qt.PenStyle.DashLine))
        p.drawLine(0, int(y), w, int(y))
    p.setPen(QPen(QColor(60, 60, 200), 1))
    p.drawLine(0, floor, w, floor)
    import sprites as sm
    for ci, (label, name) in enumerate(names):
        b.action = 'sit'
        sc = pet._pose_scale(name)
        body_h = H * sc
        img, cx, _ = sm.get_aligned(pet_name, name, int(body_h), False)
        p.drawImage(int(ci * cw + cw / 2 - cx), int(floor - body_h), img)
        p.setPen(QColor(20, 20, 20))
        p.drawText(ci * cw + 6, 346, '%s x%.2f' % (name, sc))
    p.end()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '_size_%s.png' % pet_name)
    sheet.save(out)
    print('saved', out)


if __name__ == '__main__':
    app = QGuiApplication([])
    for pn in ('hamster', 'terrier', 'cat'):
        grid(pn)
        size_strip(pn)
