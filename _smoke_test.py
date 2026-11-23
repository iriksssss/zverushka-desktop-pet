# -*- coding: utf-8 -*-
"""Смоук-тест без видимого окна: прогоняем тики, сохраняем рендер."""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, r'C:\pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QRect
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

app = QApplication([])
app.setWindowIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'assets', 'sprites', 'icon.png')))
from app import PetWindow

win = PetWindow()
win.show()

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_test_shots')
os.makedirs(OUT, exist_ok=True)


def shot(name):
    img = QImage(win.size(), QImage.Format_ARGB32_Premultiplied)
    img.fill(0xFF202030)
    p = QPainter(img)
    win.pet.paint(p)
    p.end()
    # обрезать к контуру зверюшки + отступ
    r = win.pet.footprint().adjusted(-40, -60, 60, 20).toAlignedRect()
    img.copy(r).save(os.path.join(OUT, name + '.png'))
    print(name, 'action=', win.brain.action, 'face=', win.brain.face,
          'x=', int(win.pet.pos.x()))


# разогреть спрайты
win._on_tick(); win._on_tick()

win.brain.do('walk', 5.0)
for i in range(60):
    win._on_tick()
shot('walk_1')

win.brain.do('walk', 99.0)
win.brain.direction = -1
for i in range(30):
    win._on_tick()
shot('walk_flip')

win.brain.do('sit', 99.0)
for i in range(20):
    win._on_tick()
shot('sit')

win.brain.set_face('loved', 5.0)
win.pet.burst('hearts')
for i in range(10):
    win._on_tick()
shot('sit_loved')

win.brain.set_face('angry', 5.0)
win.pet.burst('angry')
for i in range(8):
    win._on_tick()
shot('sit_angry')

win.brain.do('sleep', 99.0)
for i in range(30):
    win._on_tick()
shot('sleep')

win.brain.do('crouch', 99.0)
win.brain.set_face('scared', 5.0, force=True)
win.pet.burst('scared')
for i in range(6):
    win._on_tick()
shot('crouch_scared')

win.brain.do('jump', 99.0)
win.pet.burst('jump')
for i in range(6):
    win._on_tick()
shot('jump')

print('OK — shots in', OUT)
app.quit()
