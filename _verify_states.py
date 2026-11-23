# -*- coding: utf-8 -*-
"""Регрессионный тест состояний зверушки (11.18, третья заявка).

Проверяет исправленные баги и все переходы FSM мозга:
1) ХОВЕР: курсор >3 с над зверушкой -> лицо loved + сердечки
   (раньше tick_face гасил hover_time каждый тик — loved не наступал НИКОГДА);
2) ОДИНОЧНЫЙ КЛИК: больше не застревает в позе «в руках»
   (раньше grabbed с длительностью 9999 не сбрасывался);
3) «хвост» дабл-клика: release при dragging=False снимает флаг подавления,
   иначе он проглатывал следующий одиночный клик;
4) остальные переходы: сон->побудка, злость за 5 кликов, стыд за дабл-клик,
   испуг, сонливость/тоска по idle, облачко-фраза раз в ~час (не во сне).
"""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, r'C:\pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QEvent, QPointF, Qt                     # noqa: E402
from PySide6.QtGui import QMouseEvent                             # noqa: E402
from PySide6.QtWidgets import QApplication                        # noqa: E402

app = QApplication([])
from brain import Brain, A_GRABBED, A_SIT, A_SLEEP, A_STRETCH, A_WALK  # noqa: E402
from app import PetWindow                                          # noqa: E402

fails = []


def check(name, ok, extra=''):
    print(('  OK  ' if ok else ' FAIL ') + name + (f'  [{extra}]' if extra and not ok else ''))
    if not ok:
        fails.append(name)


def drain(b):
    ev = [e[0] for e in b.events]
    b.events.clear()
    return ev


print('== МОЗГ: ховер и любовь ==')
b = Brain()
for _ in range(40):                       # 40 x 0.1 c = 4 с ховера
    b.hover_tick(0.1, True)
    b.tick_face(0.1)                      # декремент больше не должен мешать
check('hover 4 с -> лицо loved', b.face == 'loved', b.face)
check('hover 4 с -> событие hearts', 'hearts' in drain(b))
check('loved_fired взведён', b.loved_fired)
b.hover_tick(0.1, False)
check('курсор ушёл -> hover сброшен', b.hover_time == 0.0 and not b.loved_fired)

print('== МОЗГ: захват и клики ==')
b = Brain()
b.grabbed()
check('grabbed -> поза в руках', b.action == A_GRABBED)
b.click()
check('клик из grabbed -> вышел из рук', b.action != A_GRABBED, b.action)
check('клик из grabbed -> лицо happy', b.face == 'happy', b.face)

b = Brain()
b.grabbed()
b.released_grabbed()
check('released_grabbed -> сел', b.action == A_SIT and b.face_priority == 0)

b = Brain()
b.do(A_SLEEP, 100.0)
b.click()
check('клик во сне -> потягушки', b.action == A_STRETCH, b.action)
check('клик во сне -> событие wake', 'wake' in drain(b))

b = Brain()
for _ in range(5):                        # 5 кликов < 5 с
    b.tick_face(0.05)
    b.click()
check('5 быстрых кликов -> злится', b.face == 'angry', b.face)
check('злость -> событие angry', 'angry' in drain(b))

b = Brain()
b.click(double=True)
check('дабл-клик -> стыдится', b.face == 'shy', b.face)
check('дабл-клик -> событие jump', 'jump' in drain(b))

print('== МОЗГ: испуга НЕТ (убран 23.11), бросок, одиночество ==')
check('у Brain нет метода scare (испуг убран)', not hasattr(Brain, 'scare'))
check('в приоритетах лиц нет scared', 'scared' not in
      __import__('brain').P)

b = Brain()
b.dropped()
check('бросок -> прыжок', b.action == 'jump', b.action)
check('бросок -> удивлён', b.face == 'surprised', b.face)

b = Brain()
b.tick_face(301.0)
check('5 мин без внимания -> сонный', b.face == 'sleepy', b.face)
b = Brain()
b.tick_face(601.0)
check('10 мин без внимания -> тоскует', b.face == 'lonely', b.face)

print('== МОЗГ: облачко-фраза ==')
b = Brain()
b.phrase_in = 0.01
b.tick_face(0.02)
check('таймер фразы -> событие phrase', 'phrase' in drain(b))
check('фраза переотложена на ~час', 3000 <= b.phrase_in <= 4200, f'{b.phrase_in:.0f}')

b = Brain()
b.do(A_SLEEP, 100.0)
b.phrase_in = 0.01
b.tick_face(0.02)
check('во сне фраза НЕ всплывает', 'phrase' not in drain(b))

b = Brain()
b.grabbed()
b.phrase_in = 0.01
b.tick_face(0.02)
check('в руках фраза НЕ всплывает', 'phrase' not in drain(b))

import random
ok = all(240 <= Brain(rng=lambda: random.Random(i))._default_duration(A_SLEEP) <= 480
         for i in range(50))
check('сон длится 240–480 с', ok)

print('== МОЗГ: ховер без грусти (23.11) ==')
b = Brain()
b.idle = 700.0                      # давно без кликов — был бы lonely
for _ in range(50):                 # 5 с ховера
    b.hover_tick(0.1, True)
    b.tick_face(0.1)
check('ховер после 10 мин idle -> НЕ тоскует', b.face != 'lonely', b.face)
check('ховер после 10 мин idle -> умиляется', b.face == 'loved', b.face)
for _ in range(70):                 # ещё 7 с: loved истекает, грусть не вернётся
    b.hover_tick(0.1, True)
    b.tick_face(0.1)
check('долгий ховер -> грусть не возвращается',
      b.face in ('normal', 'loved', 'content', 'playful'), b.face)
b.face, b.face_left, b.face_priority = 'normal', 0, 0
b.hover_tick(0.1, False)            # курсор ушёл
b.tick_face(0.1)
check('курсор ушёл, idle>600 -> снова тоскует', b.face == 'lonely', b.face)

# защёлка loved_fired не должна съедать умиление, если в момент
# срабатывания (3 с ховера) лицо занято сильной эмоцией (злость/удивление):
# как только эмоция спадёт, умиление всё равно показывается
print('== МОЗГ: ховер, занятое лицо не съедает умиление ==')
b = Brain()
for _ in range(35):                 # 3.5 с ховера
    b.hover_tick(0.1, True)
    b.tick_face(0.1)
    if _ == 28:                     # незадолго до отметки 3 с — злость
        b.set_face('angry', 1.0, force=True)
check('злость на 3-й секунде ховера показана', b.face == 'angry', b.face)
check('защёлка loved НЕ взведена (лицо было занято)', not b.loved_fired)
for _ in range(15):                 # ещё 1.5 с ховера — злость спадает
    b.hover_tick(0.1, True)
    b.tick_face(0.1)
check('после злости умиление всё же показано', b.face == 'loved', b.face)

print('== МОЗГ: падение на опору ==')
b = Brain()
b.falling()
check('falling -> действие fall', b.action == 'fall', b.action)
check('falling -> удивлён', b.face == 'surprised', b.face)
b.tick_action(1.0, 100, 0, 1000)
check('fall не истекает сам (ждёт landed)', b.action == 'fall', b.action)
b.landed()
check('landed -> прыжок', b.action == 'jump', b.action)
check('landed -> лицо happy', b.face == 'happy', b.face)

print('== МОЗГ: сидячие смены настроения ==')
b = Brain()
b.do(A_SIT, 99.0)
seen = set()
for _ in range(6000):               # ~10 мин сидения
    b.tick_face(0.1)
    if b.face in ('content', 'playful'):
        seen.add(b.face)
        b.face, b.face_left, b.face_priority = 'normal', 0, 0
check('за ~10 мин сидения были content и playful',
      seen == {'content', 'playful'}, str(seen))

print('== ПРИЛОЖЕНИЕ: мышиные события ==')
win = PetWindow()
win.show()
pet = win.pet
cx, cy = pet.pos.x(), pet.pos.y() - pet.base_h / 2


def mouse(etype, button=Qt.MouseButton.LeftButton,
          buttons=Qt.MouseButton.LeftButton):
    gp = QPointF(cx, cy)
    return QMouseEvent(etype, QPointF(20, 20), gp, button, buttons,
                       Qt.KeyboardModifier.NoModifier)


# одиночный клик: press -> release (без движения)
win.mousePressEvent(mouse(QEvent.Type.MouseButtonPress))
check('press -> поза в руках', win.brain.action == A_GRABBED, win.brain.action)
win.mouseReleaseEvent(mouse(QEvent.Type.MouseButtonRelease,
                            buttons=Qt.MouseButton.NoButton))
check('release без движения -> НЕ застрял в руках',
      win.brain.action != A_GRABBED, win.brain.action)
check('release без движения -> радуется', win.brain.face == 'happy', win.brain.face)

# дабл-клик: press -> release -> dblclick -> release
win.mousePressEvent(mouse(QEvent.Type.MouseButtonPress))
win.mouseReleaseEvent(mouse(QEvent.Type.MouseButtonRelease,
                            buttons=Qt.MouseButton.NoButton))
win.mouseDoubleClickEvent(mouse(QEvent.Type.MouseButtonDblClick))
check('дабл-клик -> стыдится', win.brain.face == 'shy', win.brain.face)
check('флаг хвоста взведён', win._suppress_dbl_release)
win.mouseReleaseEvent(mouse(QEvent.Type.MouseButtonRelease,
                            buttons=Qt.MouseButton.NoButton))
check('хвост дабл-клика снял флаг', not win._suppress_dbl_release)

# следующий одиночный клик НЕ проглочен флагом
win.brain.face, win.brain.face_left, win.brain.face_priority = 'normal', 0, 0
win.mousePressEvent(mouse(QEvent.Type.MouseButtonPress))
win.mouseReleaseEvent(mouse(QEvent.Type.MouseButtonRelease,
                            buttons=Qt.MouseButton.NoButton))
check('клик после дабл-клика -> радуется', win.brain.face == 'happy',
      win.brain.face)
check('клик после дабл-клика -> не в руках',
      win.brain.action != A_GRABBED, win.brain.action)

print('== ПРИЛОЖЕНИЕ: посадка на край окна (23.11) ==')
# симулируем перенос: окно под точкой отпускания -> падение на его кромку
win._landing_support = lambda x, y: (777, (300.0, 700.0, 900.0, 1000.0))
win.pet.pos.setY(400.0)             # держим зверушку ВЫШЕ кромки окна
cx, cy = pet.pos.x(), pet.pos.y() - pet.base_h / 2   # курсор на фигурке
win.mousePressEvent(mouse(QEvent.Type.MouseButtonPress))
win._drag_moved = 100.0             # был реальный перенос
win.mouseReleaseEvent(mouse(QEvent.Type.MouseButtonRelease,
                            buttons=Qt.MouseButton.NoButton))
check('перенос над окном -> опора = окно', win._support == 777)
check('перенос над окном -> пол = верх окна', win.floor_y == 700.0,
      f'{win.floor_y:.0f}')
check('перенос над окном -> началось падение',
      win._fall is not None and win.brain.action == 'fall', win.brain.action)
for _ in range(200):                # гравитация доводит до опоры
    win._tick_fall(0.05)
    if not win._fall:
        break
check('падение завершилось на кромке окна',
      win._fall is None and abs(win.pet.pos.y() - 700.0) < 1,
      f'{win.pet.pos.y():.0f}')
check('после падения — радостный прыжок', win.brain.action == 'jump',
      win.brain.action)
check('границы прогулки = ширина окна', win._walk_x == (300.0, 900.0))

# прогулка ограничена окном: фигурка не уходит за его края
wl, wr = win._walk_x
win.brain.do(A_WALK, 99.0, force=True)
win.pet.pos.setX(50.0)              # далеко за левым краем окна
win.pet.tick(0.05, win.floor_y, wl, wr)
check('на окне фигурка не уходит за его край', win.pet.pos.x() > 300.0,
      f'{win.pet.pos.x():.0f}')

# окно закрыли -> падение на панель задач
win._window_info = lambda hwnd: None
win._check_support()
check('окно закрыто -> опора снята', win._support is None)
check('окно закрыто -> пол = панель задач',
      abs(win.floor_y - win._taskbar_top()) < 2, f'{win.floor_y:.0f}')

# окно, РАЗВЁРНУТОЕ на весь экран, опорой НЕ является: его верхняя
# кромка = верх экрана, зверушка оказалась бы за экраном («пропадает»,
# баг 23.11) — опора только у окон с кромкой ниже верха экрана
check('развёрнутое окно (кромка = верх экрана) — не опора',
      not win._good_support(555, (0.0, 0.0, 2560.0, 1440.0)))
check('обычное окно — опора',
      win._good_support(555, (300.0, 700.0, 900.0, 1000.0)))
# окно-опора развернули на весь экран, пока зверушка на нём стояла
win._support = 555
win._window_info = lambda hwnd: (0.0, 0.0, 2560.0, 1440.0)
win._check_support()
check('опора развернулась на весь экран -> опора снята',
      win._support is None)
check('опора развёрнулась -> пол = панель задач',
      abs(win.floor_y - win._taskbar_top()) < 2, f'{win.floor_y:.0f}')

# правило «только вниз» (23.11, вторая итерация): опора — только окно,
# чья кромка СТРОГО НИЖЕ точки отпускания; если отпустили НА ФОНЕ окна
# (кромка выше) — опоры нет, зверушка падает на панель задач
win._window_info = lambda hwnd: ((300.0, 700.0, 900.0, 1000.0)
                                 if hwnd == 777 else None)
check('кромка окна НИЖЕ точки отпускания -> опора',
      win._edge_below(777, 500.0, 400.0) == (300.0, 700.0, 900.0, 1000.0))
check('отпущена НА ФОНЕ окна (кромка выше) -> НЕ опора',
      win._edge_below(777, 500.0, 800.0) is None)
check('точка отпускания вне окна по X -> НЕ опора',
      win._edge_below(777, 100.0, 400.0) is None)

# перенос над рабочим столом -> панель задач
win._fall = None
win._landing_support = lambda x, y: None
win.pet.pos.setY(300.0)
cx, cy = pet.pos.x(), pet.pos.y() - pet.base_h / 2   # курсор на фигурке
win.mousePressEvent(mouse(QEvent.Type.MouseButtonPress))
win._drag_moved = 100.0
win.mouseReleaseEvent(mouse(QEvent.Type.MouseButtonRelease,
                            buttons=Qt.MouseButton.NoButton))
check('перенос над столом -> опоры-окна нет', win._support is None)
check('перенос над столом -> пол = панель задач',
      abs(win.floor_y - win._taskbar_top()) < 2, f'{win.floor_y:.0f}')
for _ in range(300):
    win._tick_fall(0.05)
    if not win._fall:
        break
check('падение на панель задач завершилось',
      win._fall is None and abs(win.pet.pos.y() - win.floor_y) < 1,
      f'{win.pet.pos.y():.0f}')

win.close()

print()
if fails:
    print('ПРОВАЛЕНО:', ', '.join(fails))
    sys.exit(1)
print('ВСЕ ПРОВЕРКИ СОСТОЯНИЙ ПРОШЛИ')
