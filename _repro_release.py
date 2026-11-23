# -*- coding: utf-8 -*-
"""Живая репродукция багов 23.11 (реальный QPA, НЕ offscreen):

Фаза A: ховер на котике (QCursor наводится на тело, 6 с) — лог лица.
Фаза B: перенос котика и отпускание над обычным окном (dummy 700,320
        900x500) — лог pos/floor/support, скриншот.
Фаза C: перенос и отпускание над РАЗВЁРНУТЫМ окном — ожидаем панель
        задач (регрессия «пропадает / садится сверху»).

Лог — _repro_log.txt, скриншоты — _repro_B.png / _repro_C.png.
"""
import os
import subprocess
import sys
import time
import traceback

sys.path.insert(0, r'C:\pylib')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QEvent, QPointF, Qt, QTimer, QLocale
from PySide6.QtGui import QMouseEvent, QCursor, QGuiApplication
from PySide6.QtWidgets import QApplication

from app import PetWindow

LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '_repro_log.txt'), 'w', encoding='utf-8')


def log(msg):
    LOG.write('%.2f %s\n' % (time.time() - T0, msg))
    LOG.flush()


app = QApplication([])
win = PetWindow()

# ловим исключения в тике — замороженный/пропавший питомец без ошибок
# в консоли был главным подозрением
orig_tick = win._on_tick


def safe_tick():
    try:
        orig_tick()
    except Exception:
        log('EXCEPTION in _on_tick:\n' + traceback.format_exc())


win.timer.timeout.disconnect()
win.timer.timeout.connect(safe_tick)

win.show()
T0 = time.time()

dummies = []


def spawn_dummy(mode=None):
    cmd = [sys.executable, os.path.join(os.path.dirname(
        os.path.abspath(__file__)), '_dummy_win.py')]
    if mode:
        cmd.append(mode)
    p = subprocess.Popen(cmd)
    dummies.append(p)
    return p


def mkev(etype, gx, gy):
    pos = QPointF(float(gx), float(gy))
    return QMouseEvent(etype, pos, pos, Qt.MouseButton.LeftButton,
                       Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)


def state(tag):
    log('%s: pos=(%d,%d) floor=%s action=%s face=%s hover=%.2f '
        'fall=%s support=%s walk_x=%s' % (
            tag, win.pet.pos.x(), win.pet.pos.y(), win.floor_y,
            win.brain.action, win.brain.face, win.brain.hover_time,
            bool(win._fall), win._support, win._walk_x))


def shot(name, box=None):
    scr = QGuiApplication.primaryScreen().grabWindow(0)
    img = scr.toImage()
    if box:
        img = img.copy(*box)
    img.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), name))
    log('shot %s saved' % name)


# ---------- сценарий ----------
step = {'i': 0}


def scenario():
    i = step['i']
    step['i'] += 1
    pet = win.pet
    cx, cy = int(pet.pos.x()), int(pet.pos.y() - pet.base_h * 0.5)

    if i == 1:
        log('=== init ===')
        state('init')
        win.set_pet('cat')
        return
    # --- фаза A: ховер на котике ---
    if 2 <= i <= 25:  # ~6 с: держим курсор на котике (перенацеливаем)
        QCursor.setPos(cx, cy)
        if i % 4 == 0:
            state('hover')
        if i == 25:
            log('=== hover done: loved_fired=%s face=%s ===' % (
                win.brain.loved_fired, win.brain.face))
        return
    # --- фаза B: перенос НАД окном (кромка ниже) -> посадка на окно ---
    if i == 26:
        spawn_dummy(None)
        time.sleep(1.5)
        return
    if i == 28:
        QCursor.setPos(cx, cy)
        win.mousePressEvent(mkev(QEvent.Type.MouseButtonPress, cx, cy))
        state('press')
        return
    if 29 <= i <= 38:  # тащим НАД окно (цель: 900, 200; кромка ~289)
        t = (i - 28) / 10.0
        QCursor.setPos(int(cx + (900 - cx) * t), int(cy + (200 - cy) * t))
        return
    if i == 39:
        QCursor.setPos(900, 200)
        win.mouseReleaseEvent(mkev(QEvent.Type.MouseButtonRelease, 900, 200))
        state('release-above-window')
        return
    if 40 <= i <= 52:
        if i % 3 == 0:
            state('after-release-above')
        if i == 52:
            shot('_repro_B.png', (600, 100, 1100, 500))
        return
    # --- фаза B2: отпустить НА ФОНЕ окна -> падение на панель задач ---
    if i == 53:
        cx2, cy2 = int(pet.pos.x()), int(pet.pos.y() - pet.base_h * 0.5)
        QCursor.setPos(cx2, cy2)
        win.mousePressEvent(mkev(QEvent.Type.MouseButtonPress, cx2, cy2))
        state('pressB2')
        return
    if 54 <= i <= 63:  # тащим НА ФОН окна (цель: 900, 420 — ниже кромки)
        cx2, cy2 = int(pet.pos.x()), int(pet.pos.y() - pet.base_h * 0.5)
        t = (i - 53) / 10.0
        QCursor.setPos(int(cx2 + (900 - cx2) * t), int(cy2 + (420 - cy2) * t))
        return
    if i == 64:
        QCursor.setPos(900, 420)
        win.mouseReleaseEvent(mkev(QEvent.Type.MouseButtonRelease, 900, 420))
        state('release-on-window-bg')
        return
    if 65 <= i <= 72:
        if i % 3 == 0:
            state('after-release-bg')
        return
    # --- фаза C: перенос над РАЗВЁРНУТЫМ окном ---
    if i == 73:
        spawn_dummy('max')
        time.sleep(1.5)
        return
    if i == 75:
        cx2, cy2 = int(pet.pos.x()), int(pet.pos.y() - pet.base_h * 0.5)
        QCursor.setPos(cx2, cy2)
        win.mousePressEvent(mkev(QEvent.Type.MouseButtonPress, cx2, cy2))
        state('press2')
        return
    if 76 <= i <= 85:
        cx2, cy2 = int(pet.pos.x()), int(pet.pos.y() - pet.base_h * 0.5)
        t = (i - 75) / 10.0
        QCursor.setPos(int(cx2 + (1500 - cx2) * t),
                       int(cy2 + (700 - cy2) * t))
        return
    if i == 86:
        QCursor.setPos(1500, 700)
        win.mouseReleaseEvent(mkev(QEvent.Type.MouseButtonRelease,
                                   1500, 700))
        state('release-over-maximized')
        return
    if 87 <= i <= 102:
        if i % 3 == 0:
            state('after-release-max')
        if i == 102:
            shot('_repro_C.png')
            log('=== done ===')
            for d in dummies:
                d.terminate()
            app.quit()
        return


timer = QTimer()
timer.timeout.connect(scenario)
timer.start(250)
sys.exit(app.exec())
