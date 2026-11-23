# -*- coding: utf-8 -*-
"""Тест RPG-прогресса (progress.py) и его привязки к приложению."""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, r'C:\pylib')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QPointF                        # noqa: E402
from PySide6.QtGui import QImage, QPainter            # noqa: E402
from PySide6.QtWidgets import QApplication            # noqa: E402

app = QApplication([])
from progress import Progress, xp_total_for_level    # noqa: E402
from app import PetWindow                             # noqa: E402

fails = []


def check(name, ok, extra=''):
    print(('  OK  ' if ok else ' FAIL ') + name + (f'  [{extra}]' if extra and not ok else ''))
    if not ok:
        fails.append(name)


print('== уровни и титулы ==')
check('пороги: ур1=0 ур2=50 ур3=150', (xp_total_for_level(1), xp_total_for_level(2),
      xp_total_for_level(3)) == (0, 50, 150))
p = Progress()
check('0 XP -> ур 1 Новичок', p.level() == 1 and p.title() == 'Новичок')
p = Progress({'xp': 50})
check('50 XP -> ур 2 Знакомец', p.level() == 2 and p.title() == 'Знакомец')
p = Progress({'xp': 149})
check('149 XP -> всё ещё ур 2', p.level() == 2)
p = Progress({'xp': 5250})
check('5250 XP -> ур 15 Легенда', p.level() == 15 and p.title() == 'Легенда рабочего стола',
      p.title())
p = Progress({'xp': 0})
check('ур 1 Новичок с нуля', p.level() == 1)

print('== начисление XP ==')
p = Progress()
ev = p.add_xp(50, 0.0)
check('переход порога -> level_up', ('level_up', 2) in ev, str(ev))
ev = p.add_xp(10, 0.0)
check('без перехода -> тихо', ev == [], str(ev))

print('== клики и анти-фарм ==')
p = Progress()
for i in range(20):
    p.on_click(float(i * 10))
check('20 кликов: XP не больше капа 30', p.d['xp'] <= 30, str(p.d['xp']))
check('счётчик кликов = 20', p.d['clicks'] == 20)
check('ачивка first_click', 'first_click' in p.d['achievements'])
p = Progress()
for i in range(100):
    p.on_click(float(i))
check('100 кликов -> clicks_100', 'clicks_100' in p.d['achievements'])

print('== обнимашки / фразы / сны ==')
p = Progress()
for i in range(10):
    p.on_loved(float(i))
check('10 обнимашек -> loves_10', 'loves_10' in p.d['achievements'])
check('обнимашки дают XP (10x5)', p.d['xp'] == 50, str(p.d['xp']))
p = Progress()
for i in range(10):
    p.on_phrase(float(i))
check('10 фраз -> phrases_10', 'phrases_10' in p.d['achievements'])
p = Progress()
for i in range(5):
    p.on_zzz(float(i))
check('5 снов -> zzz_5', 'zzz_5' in p.d['achievements'])

print('== путь, аптайм, фокус ==')
p = Progress()
p.on_walk(100000.0, 0.0)
check('100k пикселей -> walk_100k', 'walk_100k' in p.d['achievements'])
check('путь даёт XP (100k/20k=5)', p.d['xp'] == 5, str(p.d['xp']))
p = Progress()
p.on_tick(300.0, 0.0, 0.0)
check('5 минут аптайма -> +2 XP', p.d['xp'] == 2, str(p.d['xp']))
ev = p.on_tick(10.0, 1501.0, 0.0)
check('фокус 25 мин -> бонус', ('focus_bonus',) in ev and p.d['xp'] >= 15, str(ev))
ev2 = p.on_tick(10.0, 1600.0, 0.0)
check('фокус-бонус не дублируется', ('focus_bonus',) not in ev2)
p.on_click(0.0)
ev3 = p.on_tick(10.0, 1700.0, 0.0)
check('после клика фокус снова доступен', ('focus_bonus',) in ev3)

print('== стрик дней ==')
import datetime
p = Progress()
today = datetime.date.today()
yest = (today - datetime.timedelta(days=1)).isoformat()
p.d['last_day'] = yest
p.d['streak'] = 2
ev = p.on_new_day()
check('вчера+сегодня -> стрик 3', p.d['streak'] == 3, str(p.d['streak']))
check('стрик 3 -> days_3', 'days_3' in p.d['achievements'])
ev = p.on_new_day()
check('повтор в тот же день — тихо', ev == [] and p.d['streak'] == 3)
p2 = Progress()
p2.d['last_day'] = '2020-01-01'
p2.d['streak'] = 5
p2.on_new_day()
check('пропуск дней -> стрик с 1', p2.d['streak'] == 1, str(p2.d['streak']))

print('== питомцы и сериализация ==')
p = Progress()
p.on_pet_seen('hamster', ['hamster', 'terrier', 'cat'], 0.0)
check('один питомец — ачивки нет', 'all_pets' not in p.d['achievements'])
p.on_pet_seen('terrier', ['hamster', 'terrier', 'cat'], 0.0)
p.on_pet_seen('cat', ['hamster', 'terrier', 'cat'], 0.0)
check('все три -> all_pets', 'all_pets' in p.d['achievements'])
p2 = Progress(p.d)
check('round-trip сохраняет xp/ачивки', p2.d['xp'] == p.d['xp']
      and p2.d['achievements'] == p.d['achievements'])

print('== догонялки (progress) ==')


def ach_keys(events):
    return [e[1] for e in events if isinstance(e, tuple) and e[0] == 'achievement']


p = Progress()
ev = p.on_game_end(7, 0.0)
check('первая игра -> game_first', 'game_first' in ach_keys(ev), str(ev))
check('7 попаданий -> catch_5', 'catch_5' in ach_keys(ev))
check('7 попаданий -> 14 XP', p.d['xp'] == 14, str(p.d['xp']))
check('рекорд = 7', p.d['best_score'] == 7)
ev = p.on_game_end(12, 1.0)
check('вторая игра: game_first не дублируется', 'game_first' not in ach_keys(ev))
check('12 попаданий -> catch_10', 'catch_10' in ach_keys(ev))
check('рекорд вырос до 12', p.d['best_score'] == 12)
ev = p.on_game_end(3, 2.0)
check('3 попадания: рекорд не падает', p.d['best_score'] == 12)
check('счётчик игр = 3', p.d['games'] == 3)
p = Progress()
for i in range(5):
    p.on_game_end(0, float(i))
check('5 игр -> games_5', 'games_5' in p.d['achievements'])
p = Progress()
ev = p.on_game_end(20, 0.0)
check('20 попаданий -> catch_15', 'catch_15' in ach_keys(ev))
check('XP ограничен 15 попаданиями (30 XP)', p.d['xp'] == 30, str(p.d['xp']))

print('== лакомства и пузырьки (progress) ==')
p = Progress()
ev = p.on_game_end(9, 0.0, 'feed')
check('первые лакомства -> feed_first', 'feed_first' in ach_keys(ev), str(ev))
check('9 лакомств -> feed_8', 'feed_8' in ach_keys(ev))
check('feed: счётчики', p.d['feed_games'] == 1 and p.d['feed_best'] == 9
      and p.d['feed_total'] == 9)
ev = p.on_game_end(25, 1.0, 'feed')
check('feed: рекорд вырос, тотал 34', p.d['feed_best'] == 25
      and p.d['feed_total'] == 34)
check('feed: 30 суммарно -> feed_30', 'feed_30' in ach_keys(ev))
check('feed не трогает догонялки', p.d['games'] == 0)
p = Progress()
ev = p.on_game_end(16, 0.0, 'bub')
check('первые пузырьки -> bub_first', 'bub_first' in ach_keys(ev), str(ev))
check('16 пузырьков -> bub_15', 'bub_15' in ach_keys(ev))
ev = p.on_game_end(50, 1.0, 'bub')
check('bub: тотал 66 -> bub_60', 'bub_60' in ach_keys(ev), str(ev))
check('bub: счётчики', p.d['bub_games'] == 2 and p.d['bub_best'] == 50)
p = Progress()
p.on_game_end(1, 0.0, 'tag')
check('tag по-прежнему работает с kind', p.d['games'] == 1)

print('== привязка к приложению ==')
win = PetWindow()
win.show()
check('у окна есть progress', hasattr(win, 'progress'))
check('меню: инфо-строка', win._m_info is not None)
check('меню: прогресс', win._m_progress is not None)
win._refresh_progress_menu()
check('инфо-строка заполнена', 'Ур.' in win._m_info.text(), win._m_info.text())
check('журнал ачивок непустой', len(win._m_progress.actions()) > 5)
# все питомцы рендерятся без ошибок
ok = True
try:
    for pet in ('hamster', 'terrier', 'cat'):
        win._load_pet(pet)
        img = QImage(400, 300, QImage.Format.Format_ARGB32)
        img.fill(0)
        pnt = QPainter(img)
        win.pet.pos.setX(200.0)
        win.pet.pos.setY(250.0)
        win.pet.paint(pnt)
        pnt.end()
except Exception as e:
    ok, err = False, repr(e)
check('все питомцы рисуются', ok, err if not ok else '')

print('== догонялки (приложение) ==')
import time as _time
check('меню: пункты всех игр есть',
      all(k in win._m_game for k in ('tag', 'feed', 'bub')))
# прогресс живёт в settings.json между запусками — считаем ОТНОСИТЕЛЬНО
g0 = win.progress.d['games']
best0 = win.progress.d['best_score']
win.start_game('tag')
check('игра запущена', win.game_active() and win._game_kind == 'tag')
check('зверушка убегает', win.brain.action == 'run', win.brain.action)
# бег по всему экрану: суммарный путь большой и Y тоже меняется
import math as _m
path = 0.0
prev = (win.pet.pos.x(), win.pet.pos.y())
ys = set()
for _ in range(60):
    win._tick_game(0.05)
    cur = (win.pet.pos.x(), win.pet.pos.y())
    path += _m.dist(prev, cur)
    ys.add(round(cur[1]))
    prev = cur
check('догонялки: зверушка бегает (путь > 300px)', path > 300,
      f'{path:.0f}px')
check('догонялки: движение 2D (разные y)', len(ys) > 3, str(len(ys)))
for _ in range(3):
    win._game_hit()
    win._game_pause = 0.0      # в бою пауза-умиление между поимками
check('3 попадания засчитаны', win._game_score == 3)
win._game_hit()
check('4-е попадание засчитано', win._game_score == 4)
win._game_hit()
check('в паузе-умилении попадания не считаются', win._game_score == 4)
# ускоряем конец игры
win._game_end = _time.time() - 0.01
win._tick_game(0.03)
check('игра завершена', not win.game_active())
check('игра записана в прогресс', win.progress.d['games'] == g0 + 1)
check('рекорд = max(был, 4)', win.progress.d['best_score'] == max(best0, 4))
check('кулдаун включён', _time.time() < win._game_cd['tag'])
win._refresh_progress_menu()
check('пункт недоступен в кулдауне', not win._m_game['tag'].isEnabled())
check('текст кулдауна', 'отдохнёт' in win._m_game['tag'].text(),
      win._m_game['tag'].text())
win._game_cd['tag'] = 0.0
win._refresh_progress_menu()
check('после кулдауна доступна', win._m_game['tag'].isEnabled())

print('== лакомства (приложение) ==')
fg0 = win.progress.d['feed_games']
win.start_game('feed')
check('игра запущена', win.game_active() and win._game_kind == 'feed')
win._place_treat(win.pet.pos.x() + 300)
check('лакомство поставлено', len(win._treats) == 1)
win._place_treat(win.pet.pos.x() - 200)
win._place_treat(win.pet.pos.x())
win._place_treat(win.pet.pos.x() + 50)
check('максимум 3 лакомства', len(win._treats) == 3)
# подгоняем зверушку к лакомству и ждём поедания
win.pet.pos.setX(win._treats[0]['x'])
win._tick_game(0.03)
check('лакомство съедено', win._game_score == 1 and len(win._treats) == 2)
check('зверушка жуёт (пауза)', _time.time() < win._feed_eat_until)
check('игровая зона дорожки ловит клики',
      win._game_zone_contains(QPointF(500, win.floor_y)))
check('вне дорожки игровой зоны нет',
      not win._game_zone_contains(QPointF(500, win.floor_y - 500)))
win._game_end = _time.time() - 0.01
win._tick_game(0.03)
check('игра завершена, лакомства убраны',
      not win.game_active() and win._treats == [])
check('прогресс: feed_games +1', win.progress.d['feed_games'] == fg0 + 1)
check('прогресс: рекорд лакомств', win.progress.d['feed_best'] >= 1)

print('== пузырьки (приложение) ==')
win._game_cd['feed'] = 0.0
bg0 = win.progress.d['bub_games']
win.start_game('bub')
check('игра запущена', win.game_active() and win._game_kind == 'bub')
for _ in range(40):
    win._tick_game(0.1)
check('пузырьки появились', len(win._bubbles) > 0, str(len(win._bubbles)))
b = dict(win._bubbles[0])
win._pop_bubble(win._bubbles[0])
check('пузырёк лопнул: +1 очко, вспышка',
      win._game_score == 1 and len(win._pops) == 1)
check('зона клика по пузырю', any(
    win._game_zone_contains(QPointF(bb['x'], bb['y'])) for bb in win._bubbles) or
    len(win._bubbles) == 0)
win._game_end = _time.time() - 0.01
win._tick_game(0.03)
check('игра завершена, пузырьки убраны',
      not win.game_active() and win._bubbles == [])
check('прогресс: bub_games +1', win.progress.d['bub_games'] == bg0 + 1)

print('== прерывание игры крестиком ==')
win.start_game('tag')
check('игра tag запущена снова', win.game_active())
check('крестик в игровой зоне',
      win._game_zone_contains(win._game_close_rect().center()))
win._end_game()
check('игра прервана', not win.game_active())

win._load_pet('hamster')
win.close()

print()
if fails:
    print('ПРОВАЛЕНО:', ', '.join(fails))
    sys.exit(1)
print('ВСЕ ПРОВЕРКИ ПРОГРЕССА ПРОШЛИ')
