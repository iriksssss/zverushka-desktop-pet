# -*- coding: utf-8 -*-
"""Визуальная проверка цикла ходьбы: 8 последовательных кадров рендера."""
import os, sys
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, r'C:\pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

app = QApplication([])
from app import PetWindow
win = PetWindow(); win.show()
win._on_tick(); win._on_tick()
win.brain.do('walk', 99.0)

frames = []
for i in range(40):
    win._on_tick()
    if i % 5 == 4:  # каждые ~5 тиков — кадр
        img = QImage(win.size(), QImage.Format_ARGB32_Premultiplied)
        img.fill(0xFFEEEEEE)
        p = QPainter(img); win.pet.paint(p); p.end()
        r = win.pet.footprint().adjusted(-30, -20, 30, 10).toAlignedRect()
        frames.append(img.copy(r))

W = sum(f.width() for f in frames) + 10 * len(frames)
H = max(f.height() for f in frames)
sheet = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
sheet.fill(0xFFEEEEEE)
p = QPainter(sheet)
x = 5
# общая «линия пола» для визуальной проверки базовой линии
floor_rel = None
for f in frames:
    p.drawImage(x, H - f.height(), f)
    x += f.width() + 10
p.end()
sheet.save('_walk_anim_strip.png')
print('saved, frames:', len(frames))
