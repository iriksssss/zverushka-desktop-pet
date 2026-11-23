# -*- coding: utf-8 -*-
"""Зверушка на рабочем столе: прозрачное окно + win32 click-through."""
import json
import os
import sys
import time

import ctypes
import math
from ctypes import wintypes

sys.path.insert(0, r'C:\pylib')

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import (QAction, QActionGroup, QCursor, QIcon, QPainter,
                           QPixmap)
from PySide6.QtWidgets import (QApplication, QMenu, QMessageBox,
                               QSystemTrayIcon, QWidget)

from brain import Brain, A_RUN, A_SIT, A_SLEEP, A_JUMP, A_FALL
from pet import Pet
from progress import Progress, ACHIEVEMENTS
import sprites as sprites_mod
from sprites import (DEFAULT_PET, PetSprites, available_pets, icon_path,
                     pet_display_name)

HERE = os.path.dirname(os.path.abspath(__file__))
import sys as _sys


def _load_phrases():
    """Мотивационные фразы для облачка (assets/sprites/phrases.json)."""
    p = os.path.join(sprites_mod.SPRITES_ROOT, 'phrases.json')
    try:
        with open(p, encoding='utf-8') as f:
            data = json.load(f)
        phrases = [s for s in data.get('phrases', []) if isinstance(s, str)]
        if phrases:
            return phrases
    except Exception:
        pass
    return ['Ты молодец!', 'У тебя всё получится!', 'Ты супер!']


PHRASES = _load_phrases()

# Дразнящие реплики зверушки в «Догонялках» (после того, как её поймали)
TEASES = [
    'Не поймаешь!', 'Слишком медленно!', 'Я быстрее!',
    'Хи-хи, ещё разок!', 'Почти-почти!', 'Тут я, а тут меня нет!',
    'Догоняй-догоняй!', 'А вот и нет!',
]

# Мини-игры: длительность, кулдаун, подсказки для меню и облачка
GAMES = {
    'tag': {
        'name': 'Догонялки', 'secs': 20.0, 'cooldown': 300.0,
        'menu': 'Играть в догонялки',
        'tip': '20 секунд: зверушка носится по всему экрану — поймай её кликом! Прервать — крестик в углу',
        'start': 'Догонялки! Поймай меня за %d секунд!',
        'unit': ('раз', 'раза', 'раз'),      # «поймано 7 раз»
        'result': 'Поймано %d %s! Рекорд: %d',
        'best_key': 'best_score',
    },
    'feed': {
        'name': 'Лакомства', 'secs': 30.0, 'cooldown': 300.0,
        'menu': 'Играть в лакомства',
        'tip': '30 секунд: кликай по светлой дорожке — зверушка добежит и съест! Прервать — крестик в углу',
        'start': 'Кликай по светлой дорожке внизу — я добегу и съем!',
        'unit': ('лакомство', 'лакомства', 'лакомств'),
        'result': 'Съедено %d %s! Рекорд: %d',
        'best_key': 'feed_best',
    },
    'bub': {
        'name': 'Пузырьки', 'secs': 30.0, 'cooldown': 300.0,
        'menu': 'Играть в пузырьки',
        'tip': '30 секунд: лопай пузырьки вокруг зверушки кликом! Прервать — крестик в углу',
        'start': 'Пузырьки! Лопай их кликом, сколько успеешь!',
        'unit': ('пузырёк', 'пузырька', 'пузырьков'),
        'result': 'Лопнуто %d %s! Рекорд: %d',
        'best_key': 'bub_best',
    },
}


def _days_word(n):
    """день/дня/дней для строки стрика."""
    if n % 10 == 1 and n % 100 != 11:
        return 'день'
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return 'дня'
    return 'дней'


def _score_word(n):
    """раз/раза для итога догонялок («поймано 1 раз / 3 раза / 7 раз»)."""
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return 'раза'
    return 'раз'


def _noun(n, forms):
    """Склонение существительного: _noun(5, ('пузырёк','пузырька','пузырьков')).

    forms = (форма для 1, форма для 2-4, форма для 5-20)."""
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return forms[1]
    return forms[2]


def _app_dir():
    """Каталог для данных: рядом с EXE (frozen) или с исходниками."""
    if getattr(_sys, 'frozen', False):
        d = os.path.dirname(_sys.executable)
        if os.access(d, os.W_OK):
            return d
        d = os.path.join(os.path.expanduser('~'), 'DesktopPet')
        os.makedirs(d, exist_ok=True)
        return d
    return HERE


SETTINGS_PATH = os.path.join(_app_dir(), 'settings.json')
# scale по умолчанию 0.4 — первая зверушка на чужом ПК маленькая и не
# мешает; увеличивается из меню (23.11, по просьбе пользователя)
DEFAULTS = {'scale': 0.4, 'speed': 1.0, 'pet': 'hamster',
            'pos_x': None}

# Подсказка «как общаться со зверушкой» (пункт меню трея)
HINTS_TEXT = (
    '• Клик — радуется\n'
    '• Клик во сне — просыпается с потягушками\n'
    '• 5+ кликов подряд — злится (дым из ушей)\n'
    '• Двойной клик — смущается и подпрыгивает\n'
    '• Навести курсор на 3 секунды — умиляется, сердечки\n'
    '• Перетащить мышью — висит «в руке»; отпустить над окном —\n'
    '  сядет на его кромку, над столом — вернётся на панель задач\n'
    '• Без внимания: через ~4 минуты засыпает на подушке,\n'
    '  через 10 минут — скучает\n'
    '• Примерно раз в час — облачко с тёплой фразой\n'
    '• Игры — в меню «Игры»: догонялки, лакомства, пузырьки\n'
    '• Прогресс, уровни и ачивки — в меню «Прогресс»'
)

# ---------- win32 ----------
user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008


def _exstyle(hwnd):
    return user32.GetWindowLongW(hwnd, GWL_EXSTYLE)


def _set_exstyle(hwnd, style):
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


def set_topmost(hwnd, on=True):
    style = _exstyle(hwnd)
    style = (style & ~WS_EX_TOPMOST) | (WS_EX_TOPMOST if on else 0)
    _set_exstyle(hwnd, style)


def cursor_pos():
    g = QCursor.pos()
    return g


# ---------- один экземпляр ----------
k32 = ctypes.windll.kernel32
k32.CreateMutexW.restype = ctypes.c_void_p   # полный 64-битный handle
_SINGLETON_MUTEX = None


def _already_running():
    """Именованный мьютекс win32: True, если зверушка уже запущена."""
    global _SINGLETON_MUTEX
    m = k32.CreateMutexW(None, False, 'DesktopPet_Zverushka_Singleton')
    if not m:
        return False   # мьютекс не создан — не блокируем запуск
    _SINGLETON_MUTEX = m   # держим, пока жив процесс
    return k32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


class PetWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = self._load_settings()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        screen = QApplication.primaryScreen()
        self.geom = screen.geometry()
        self.resize(self.geom.size())
        self.move(self.geom.topLeft())

        # Старт — всегда на панели задач: «пол» = верхний край панели
        # (или низ экрана, если панель не найдена / не снизу).
        self.floor_y = self._taskbar_top()
        self.brain = Brain()
        self.pet = Pet(self.brain)
        self.pet.base_h = 130.0 * self.settings['scale']
        self.pet.speed = 60.0 * self.settings['speed']
        px = self.settings['pos_x']
        if px is None:
            px = self.geom.center().x()
        px = max(self.geom.left() + 20, min(px, self.geom.right() - 20))
        self.pet.pos = QPointF(px, self.floor_y)

        self._hwnd = int(self.winId())
        style = _exstyle(self._hwnd)
        style |= WS_EX_TOOLWINDOW | WS_EX_TOPMOST
        _set_exstyle(self._hwnd, style)
        self._click_through = True

        self.dragging = False
        self.drag_off = (0, 0)
        self._drag_moved = 0.0
        self._suppress_dbl_release = False  # второй release двойного клика
        self._tick_n = 0
        self._last_face = None
        # опора под зверушкой: None = панель задач/уровень, иначе hwnd окна,
        # на чьей верхней кромке она стоит; _walk_x — границы прогулки
        self._support = None
        self._walk_x = None               # None = весь экран
        self._fall = None                 # {'vy': float} во время падения
        # мини-игры: вид активной игры, её конец и счёт, кулдауны по видам
        self._game_kind = None              # None | 'tag' | 'feed' | 'bub'
        self._game_end = 0.0
        self._game_score = 0
        self._game_cd = {k: 0.0 for k in GAMES}
        self._game_pause = 0.0              # пауза-умиление после поимки
        self._tag_target = None             # цель бега (x, y) в догонялках
        self._treats = []                   # лакомства: [{'x', 'bob'}]
        self._feed_eat_until = 0.0          # зверушка жуёт (не дёргать её)
        self._bubbles = []                  # пузырьки: [{'x','y','r','vy','t'}]
        self._pops = []                     # вспышки лопнувших пузырьков
        self._bubble_spawn = 0.0
        # прогресс (XP/уровни/ачивки/стрик) — хранится в settings.json
        self.progress = Progress(self.settings.get('progress'))
        self._tray = self._make_tray()
        self._load_pet(self.settings.get('pet', DEFAULT_PET))
        self._progress_events(self.progress.on_new_day())
        self._progress_events(self.progress.on_pet_seen(
            self.settings['pet'], available_pets(), time.time()))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(30)  # ~33 fps — плавнее
        self._last_t = None

    def ground_y(self):
        return self.floor_y

    @staticmethod
    def _taskbar_rect():
        """Прямоугольник панели задач (x, y, x2, y2) через win32."""
        try:
            from ctypes import wintypes
            hwnd = user32.FindWindowW('Shell_TrayWnd', None)
            if not hwnd:
                return None
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            return (r.left, r.top, r.right, r.bottom)
        except Exception:
            return None

    def _taskbar_top(self):
        """Y «пола» на панели задач: верхняя кромка панели, если она снизу
        и попадает в границы экрана (иначе — низ экрана)."""
        bar = self._taskbar_rect()
        if bar:
            top = bar[1]
            if self.geom.top() <= top <= self.geom.bottom() and \
                    top > self.geom.bottom() - 120:
                return top
        return self.geom.bottom() - 4

    def go_to_taskbar(self):
        """Вернуть зверушку на панель задач (пункт меню трея)."""
        y = self._taskbar_top()
        if abs(self.floor_y - y) < 2:
            return  # уже там
        self._support = None
        self._walk_x = None
        self._fall = None
        self.floor_y = y
        self.pet.pos.setY(y)
        self.brain.dropped()  # радостный прыжок «я вернулся!»
        self.save_settings()
        self.update()

    # ---------- опора под зверушкой: край окна или панель задач ----------
    # служебные окна, которые нельзя считать «опорой»
    _SKIP_CLASSES = ('Shell_TrayWnd', 'Shell_SecondaryTrayWnd',
                     'Progman', 'WorkerW')

    @staticmethod
    def _window_info(hwnd):
        """Видимые границы окна (left, top, right, bottom) или None,
        если окно не годится в опору (скрыто / свёрнуто / наше /
        служебное / слишком мелкое)."""
        try:
            if not hwnd or not user32.IsWindow(hwnd):
                return None
            if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                return None
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == os.getpid():
                return None          # наши собственные окна
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            if buf.value in PetWindow._SKIP_CLASSES:
                return None
            r = wintypes.RECT()
            # DWMWA_EXTENDED_FRAME_BOUNDS (9): видимая рамка окна без
            # невидимых теневых полей Win10/11 (GetWindowRect их включает,
            # и зверушка «висела бы» в ~7 px над видимой кромкой)
            try:
                if ctypes.windll.dwmapi.DwmGetWindowAttribute(
                        hwnd, 9, ctypes.byref(r),
                        ctypes.sizeof(r)) != 0:
                    user32.GetWindowRect(hwnd, ctypes.byref(r))
            except Exception:
                user32.GetWindowRect(hwnd, ctypes.byref(r))
            rect = (r.left, r.top, r.right, r.bottom)
            if rect[2] - rect[0] < 60 or rect[3] - rect[1] < 40:
                return None
            return rect
        except Exception:
            return None

    def _good_support(self, hwnd, rect):
        """Годится ли окно в опору для посадки.

        НЕ годится: ① развёрнутое на весь экран (IsZoomed) — его верхняя
        кромка совпадает с верхом экрана, и зверушка оказалась бы ЗА
        экраном («пропадает», баг 23.11); ② окно, чья кромка настолько
        близко к верху экрана, что фигурка над ней не помещается."""
        try:
            if user32.IsZoomed(hwnd):
                return False
        except Exception:
            pass
        return rect[1] >= self.geom.top() + self.pet.top_clearance()

    def _edge_below(self, hwnd, x, y):
        """rect окна hwnd, если его верхняя кромка НИЖЕ точки (x, y)
        (+6 px допуск), накрывает её по X и окно — годная опора;
        иначе None."""
        rect = self._window_info(hwnd)
        if rect and rect[0] <= x <= rect[2] and rect[1] > y + 6 \
                and self._good_support(hwnd, rect):
            return rect
        return None

    def _landing_support(self, x, y):
        """Окно-опора СТРОГО НИЖЕ точки (x, y): после переноса зверушка
        всегда падает ВНИЗ (23.11, вторая итерация). Если отпустить её
        НАД окном — она падает на его верхнюю кромку; если отпустить НА
        ФОНЕ окна (точка отпускания ниже кромки) — она пролетает мимо и
        падает на панель задач. Возвращает (hwnd, rect) самого верхнего
        по z-order подходящего окна или None."""
        found = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND,
                                         wintypes.LPARAM)

        def _cb(hwnd, lp):
            try:
                rect = self._edge_below(hwnd, x, y)
                if rect:
                    found.append((hwnd, rect))
                    return False      # EnumWindows идёт в z-order: хватит
            except Exception:
                pass
            return True

        user32.EnumWindows(WNDENUMPROC(_cb), 0)
        return found[0] if found else None

    def _begin_fall(self):
        """Падение (или короткий подскок вверх) к текущей опоре floor_y."""
        dy = self.floor_y - self.pet.pos.y()
        if abs(dy) < 6:
            self.pet.pos.setY(self.floor_y)
            self.brain.dropped()      # уже на месте — просто радость
        else:
            self._fall = {'vy': 0.0}
            self.brain.falling()      # удивлённая «воздушная» поза
        self.update()

    def _tick_fall(self, dt):
        """Физика падения: вниз — с ускорением, вверх — плавный подскок."""
        if not self._fall:
            return
        y = self.pet.pos.y()
        target = self.floor_y
        dy = target - y
        if dy >= 0:
            f = self._fall
            f['vy'] = min(f['vy'] + 2600.0 * dt, 1400.0)
            y += f['vy'] * dt
            if y >= target:
                self._land()
                return
        else:   # опора выше текущей точки — короткий ease-подскок
            y += dy * min(1.0, dt * 10.0)
            if y - target > -2:
                self._land()
                return
        self.pet.pos.setY(y)
        self.update()

    def _land(self):
        """Коснулась опоры: закрепиться и радостно подпрыгнуть."""
        self.pet.pos.setY(self.floor_y)
        self._fall = None
        self.brain.landed()
        self.update()

    def _check_support(self):
        """Слежение за окном-опорой: закрыли/свернули/развернули на весь
        экран — падаем на панель задач; окно сдвинули — «пол» следует
        за его верхней кромкой."""
        rect = self._window_info(self._support)
        if rect is None or not self._good_support(self._support, rect):
            self._support = None
            self._walk_x = None
            self.floor_y = float(self._taskbar_top())
            self._begin_fall()
            return
        self._walk_x = (float(rect[0]), float(rect[2]))
        if abs(rect[1] - self.floor_y) > 8:
            self.floor_y = float(rect[1])
            self._begin_fall()
        elif abs(rect[1] - self.floor_y) > 2:
            self.floor_y = float(rect[1])
            self.pet.pos.setY(self.floor_y)

    def _load_pet(self, pet):
        """Привязать спрайты питомца (папка assets/sprites/<pet>)."""
        pets = available_pets()
        if pet not in pets:
            pet = DEFAULT_PET if DEFAULT_PET in pets else pets[0]
        self.settings['pet'] = pet
        self.pet.sprites = PetSprites(pet)
        self.pet.body_frame = 0.0
        ip = icon_path(pet)
        if os.path.isfile(ip):
            app_icon = QIcon(ip)
            QApplication.setWindowIcon(app_icon)
            self._tray.setIcon(app_icon)
        self._tray.setToolTip(pet_display_name(pet))
        self.update()

    def set_pet(self, pet):
        self._load_pet(pet)
        self._progress_events(self.progress.on_pet_seen(
            pet, available_pets(), time.time()))
        self.save_settings()

    def _make_tray(self):
        icon = QApplication.windowIcon()
        tray = QSystemTrayIcon(icon, self)
        menu = QMenu()
        pause = QAction('Пауза', menu, checkable=True)
        pause.toggled.connect(self.toggle_pause)
        menu.addAction(pause)
        menu.addSeparator()
        a = QAction('Спрятать', menu)
        a.triggered.connect(lambda: self.setVisible(False))
        menu.addAction(a)
        a = QAction('Показать', menu)
        a.triggered.connect(lambda: self.setVisible(True))
        menu.addAction(a)
        a = QAction('На панель задач', menu)
        a.setToolTip('Вернуть зверушку бегать по панели задач')
        a.triggered.connect(self.go_to_taskbar)
        menu.addAction(a)
        a = QAction('Подбодри меня', menu)
        a.setToolTip('Зверушка скажет что-нибудь тёплое')
        a.triggered.connect(self.cheer_me)
        menu.addAction(a)
        a = QAction('Что умеет зверушка…', menu)
        a.setToolTip('Какие действия вызывают эмоции и реакции')
        a.triggered.connect(self._show_hints)
        menu.addAction(a)
        self._m_games = QMenu('Игры', menu)
        self._m_game = {}                   # kind -> QAction
        for kind, g in GAMES.items():
            act = QAction(g['menu'], self._m_games)
            act.setToolTip(g['tip'])
            act.triggered.connect(
                lambda _=False, k=kind: self.start_game(k))
            self._m_games.addAction(act)
            self._m_game[kind] = act
        menu.addMenu(self._m_games)
        menu.addSeparator()
        # --- прогресс (RPG-lite) ---
        self._m_info = QAction('', menu)
        self._m_info.setEnabled(False)
        menu.addAction(self._m_info)
        self._m_progress = QMenu('Прогресс', menu)
        menu.addMenu(self._m_progress)
        menu.addSeparator()
        a = QAction('Уменьшить фигурку', menu)
        a.triggered.connect(lambda: self.scale_pet(0.85))
        menu.addAction(a)
        a = QAction('Увеличить фигурку', menu)
        a.triggered.connect(lambda: self.scale_pet(1.15))
        menu.addAction(a)
        menu.addSeparator()
        # выбор питомца (эксклюзивная группа: галочка всегда одна)
        pets = available_pets()
        if len(pets) > 1:
            sub = QMenu('Питомец', menu)
            grp = QActionGroup(sub)
            grp.setExclusive(True)
            for p in pets:
                act = QAction(pet_display_name(p), sub, checkable=True)
                act.setChecked(p == self.settings.get('pet', DEFAULT_PET))
                act.triggered.connect(lambda _=False, pp=p: self.set_pet(pp))
                grp.addAction(act)
                sub.addAction(act)
            menu.addMenu(sub)
        menu.addSeparator()
        a = QAction('Выход', menu)
        a.triggered.connect(self.quit_app)
        menu.addAction(a)
        tray.setContextMenu(menu)
        tray.setToolTip('Зверушка')
        tray.show()
        menu.aboutToShow.connect(self._refresh_progress_menu)
        return tray

    # ---------- прогресс (RPG-lite) ----------
    def _show_hints(self):
        """Подсказка «Что умеет зверушка» — сводка действий и реакций.
        Окно поверх всех (наш fullscreen-пол — topmost)."""
        box = QMessageBox(QMessageBox.Information, 'Что умеет зверушка',
                          HINTS_TEXT, QMessageBox.Ok, self)
        box.setWindowFlags(box.windowFlags() | Qt.WindowStaysOnTopHint)
        box.exec()

    def cheer_me(self):
        """«Подбодри меня» из меню: облачко по требованию (+XP)."""
        self.pet.say(self.pet.rng.choice(PHRASES))
        self._progress_events(self.progress.on_phrase(time.time(), manual=True))

    # ---------- мини-игры ----------
    def game_active(self):
        return self._game_kind is not None and time.time() < self._game_end

    def start_game(self, kind):
        """Запуск мини-игры (вид kind из GAMES)."""
        now = time.time()
        g = GAMES[kind]
        if self.game_active() or now < self._game_cd[kind]:
            return
        if self.brain.tempo <= 0:
            self.pet.say('Сними меня с паузы — тогда поиграем!')
            return
        self._game_kind = kind
        self._game_end = now + g['secs']
        self._game_score = 0
        self._game_pause = 0.0
        self._tag_target = None
        self._treats = []
        self._bubbles = []
        self._pops = []
        self._feed_eat_until = 0.0
        self._bubble_spawn = 0.0
        self._fall = None               # игра прерывает падение
        if kind == 'tag':
            # догонялки — бег по ВСЕМУ экрану: оконная опора снимается
            self._support = None
            self._walk_x = None
        self.brain.set_face('happy', 3.0)
        if kind == 'tag':
            self.brain.do(A_RUN, g['secs'] + 5.0, force=True)
        else:
            self.brain.do(A_SIT, g['secs'] + 5.0, force=True)
        start = g['start']
        self.pet.say(start % g['secs'] if '%d' in start else start, 3.5)
        self.update()

    def _game_hit(self):
        """Поймали зверушку в догонялках: она замирает, умиляется,
        дразнится — и через пару секунд снова убегает."""
        now = time.time()
        if now < self._game_pause:
            return  # уже поймана, дожидаемся возобновления
        self._game_score += 1
        self._game_pause = now + 1.8
        self.brain.do(A_SIT, 2.0, force=True)
        self.brain.set_face('loved', 1.6, force=True)
        self.pet.burst('hearts')
        self.pet.say(self.pet.rng.choice(TEASES), 1.8)
        self.update()

    def _end_game(self):
        now = time.time()
        kind = self._game_kind
        g = GAMES[kind]
        self._game_kind = None
        self._game_end = 0.0
        self._game_cd[kind] = now + g['cooldown']
        self._treats = []
        self._bubbles = []
        self._pops = []
        self._tag_target = None
        if kind == 'tag':
            # после догонялок зверушка остаётся на том уровне, где бегала
            self.floor_y = self.pet.pos.y()
        score = self._game_score
        self.brain.do(A_SIT, 3.0, force=True)
        # сначала события прогресса (level-up/ачивки), потом итог игры —
        # он важнее для игрока и должен остаться в облачке последним
        self._progress_events(self.progress.on_game_end(score, now, kind))
        best = self.progress.d[GAMES[kind].get('best_key', 'best_score')]
        self.pet.say(g['result'] % (score, _noun(score, g['unit']), best), 6.0)
        self.save_settings()
        self.update()

    def _tick_game(self, dt):
        """Логика активной игры на каждом тике."""
        if not self.game_active():
            if self._game_kind is not None:
                self._end_game()
            return
        kind = self._game_kind
        if kind == 'tag':
            self._tick_game_tag(dt)
        elif kind == 'feed':
            self._tick_game_feed(dt)
        elif kind == 'bub':
            self._tick_game_bub(dt)

    # --- догонялки: убегать по ВСЕМУ экрану к случайным точкам ---
    def _tick_game_tag(self, dt):
        now = time.time()
        if now < self._game_pause:
            return  # поймана: сидит и умиляется
        if self.brain.action != A_RUN:
            self.brain.do(A_RUN, 5.0, force=True)
        pet, rng = self.pet, self.pet.rng
        # выбор новой цели: случайная точка экрана, желательно далеко
        if self._tag_target is None:
            pad = pet.edge_pad()
            top = self.geom.top() + pet.top_clearance()
            bot = self.geom.bottom() - 8
            tx, ty = pet.pos.x(), pet.pos.y()
            for _ in range(10):
                tx = rng.uniform(self.geom.left() + pad,
                                 self.geom.right() - pad)
                ty = rng.uniform(top, bot)
                if ((tx - pet.pos.x()) ** 2 +
                        (ty - pet.pos.y()) ** 2) ** 0.5 > 3 * pet.base_h:
                    break
            self._tag_target = (tx, ty)
        tx, ty = self._tag_target
        dx, dy = tx - pet.pos.x(), ty - pet.pos.y()
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 12:
            self._tag_target = None
            return
        # бег к цели: скорость как у обычного бега (×3.0), кадры от пути
        step = min(dist, pet.speed * 3.0 * dt * self.brain.tempo)
        pet.pos.setX(pet.pos.x() + dx / dist * step)
        pet.pos.setY(pet.pos.y() + dy / dist * step)
        self.brain.direction = 1 if dx >= 0 else -1
        pet.body_frame += step / max(7.0, pet.body_height() * 0.16)
        pet.px_walked += step

    # --- лакомства: бежать к ближайшему лакомству и съедать ---
    def _game_close_rect(self):
        """Кнопка-крестик «прервать игру» — правый верхний угол экрана."""
        from PySide6.QtCore import QRectF
        r = 20.0
        cx, cy = self.geom.right() - 52.0, self.geom.top() + 52.0
        return QRectF(cx - r, cy - r, 2 * r, 2 * r)

    def _game_zone_contains(self, p):
        """Игровая зона кликов вне тела зверушки (нужна для click-through)."""
        if not self.game_active():
            return False
        if self._game_close_rect().contains(p):
            return True
        if self._game_kind == 'feed':
            return abs(p.y() - self.floor_y) < 70
        if self._game_kind == 'bub':
            return any((b['x'] - p.x()) ** 2 + (b['y'] - p.y()) ** 2
                       <= (b['r'] + 6) ** 2 for b in self._bubbles)
        return False

    def _place_treat(self, x):
        """Поставить лакомство на дорожку (не больше 3 одновременно)."""
        if len(self._treats) >= 3:
            return
        x = max(self.geom.left() + 30, min(x, self.geom.right() - 30))
        self._treats.append({'x': float(x), 'bob': self.pet.rng.random() * 6.28})
        self.update()

    def _tick_game_feed(self, dt):
        now = time.time()
        if now < self._feed_eat_until:
            return  # жуёт
        if not self._treats:
            if self.brain.action not in (A_SIT,):
                self.brain.do(A_SIT, 5.0, force=True)
            return
        # ближайшее лакомство
        tx = min(self._treats, key=lambda t: abs(t['x'] - self.pet.pos.x()))['x']
        dx = tx - self.pet.pos.x()
        if abs(dx) < self.pet.base_h * 0.28:
            # дошёл — съесть
            self._treats = [t for t in self._treats if abs(t['x'] - tx) > 1]
            self._game_score += 1
            self._feed_eat_until = now + 1.1
            self.brain.do(A_SIT, 1.2, force=True)
            self.brain.set_face('loved', 1.2, force=True)
            self.pet.burst('hearts')
            self.update()
            return
        self.brain.direction = 1 if dx > 0 else -1
        if self.brain.action != A_RUN:
            self.brain.do(A_RUN, 5.0, force=True)

    # --- пузырьки: спавн, всплытие, лопанье кликом ---
    def _pop_bubble(self, b):
        self._bubbles.remove(b)
        self._game_score += 1
        self._pops.append({'x': b['x'], 'y': b['y'], 'age': 0.0})
        # зверушка радуется лопнувшему пузырьку
        if self.pet.rng.random() < 0.4:
            self.brain.do(A_JUMP, force=True)
        self.brain.set_face('happy', 1.2)
        self.update()

    def _tick_game_bub(self, dt):
        rng = self.pet.rng
        # спавн: пузырёк каждые ~0.9 с, не больше 8 одновременно
        self._bubble_spawn -= dt
        if self._bubble_spawn <= 0 and len(self._bubbles) < 8:
            self._bubble_spawn = 0.9
            x = self.pet.pos.x() + rng.uniform(-4.5, 4.5) * self.pet.base_h
            x = max(self.geom.left() + 40, min(x, self.geom.right() - 40))
            self._bubbles.append({
                'x': x,
                'y': self.floor_y + rng.uniform(10, 40),
                'r': rng.uniform(13, 24),
                'vy': rng.uniform(55, 95),
                't': rng.uniform(0, 6.28),
            })
        top = max(self.geom.top() + 40, self.floor_y - 5.5 * self.pet.base_h)
        for b in list(self._bubbles):
            b['t'] += dt * 3.0
            b['y'] -= b['vy'] * dt
            b['x'] += 22.0 * dt * math.sin(b['t'])
            if b['y'] < top:
                self._bubbles.remove(b)
        for p in list(self._pops):
            p['age'] += dt
            if p['age'] > 0.35:
                self._pops.remove(p)
        # зверушка не дремлет во время игры
        if self.brain.action in (A_SLEEP,):
            self.brain.do(A_SIT, 3.0, force=True)

    def _progress_events(self, events):
        """Показать результаты прогресса: level-up, ачивки, фокус-бонус."""
        if not events:
            return
        for ev in events:
            if isinstance(ev, tuple) and ev[0] == 'level_up':
                lvl = ev[1]
                self.pet.say('Уровень %d — %s! ✨' % (lvl, self.progress.title()), 6.0)
                self.pet.burst('jump')
            elif isinstance(ev, tuple) and ev[0] == 'achievement':
                name = ACHIEVEMENTS.get(ev[1], (ev[1], ''))[0]
                self.pet.say('Достижение: %s! 🏆' % name, 6.0)
                self.pet.burst('hearts')
            elif isinstance(ev, tuple) and ev[0] == 'focus_bonus':
                self.pet.say('Ты так сосредоточенно работаешь — я горжусь!', 6.0)
        self.save_settings()

    def _refresh_progress_menu(self):
        """Обновить динамические пункты меню перед показом."""
        lvl, cur, need = self.progress.level_progress()
        self._m_info.setText('Ур. %d · %s · %d/%d XP' % (
            lvl, self.progress.title(), cur, need))
        # мини-игры: доступность по кулдауну каждого вида
        now = time.time()
        for kind, g in GAMES.items():
            act = self._m_game[kind]
            if self.game_active() and self._game_kind == kind:
                act.setEnabled(False)
                act.setText('%s: игра идёт!' % g['name'])
            elif self.game_active():
                act.setEnabled(False)
                act.setText(g['menu'])
            elif now < self._game_cd[kind]:
                act.setEnabled(False)
                left = int((self._game_cd[kind] - now) / 60) + 1
                act.setText('%s (отдохнёт ~%d мин)' % (g['name'], left))
            else:
                act.setEnabled(True)
                act.setText(g['menu'])
        # журнал достижений
        self._m_progress.clear()
        got = self.progress.d['achievements']
        streak = self.progress.d['streak']
        s = self._m_progress.addAction(
            'Стрик: %d %s подряд · путь лапами: %.0f пx' % (
                streak, _days_word(streak), self.progress.d['walk_px']))
        s.setEnabled(False)
        g = self._m_progress.addAction(
            'Догонялки: %d игр · рекорд %d · всего попаданий %d' % (
                self.progress.d['games'], self.progress.d['best_score'],
                self.progress.d['catches_total']))
        g.setEnabled(False)
        g = self._m_progress.addAction(
            'Лакомства: %d игр · рекорд %d · всего съедено %d' % (
                self.progress.d['feed_games'], self.progress.d['feed_best'],
                self.progress.d['feed_total']))
        g.setEnabled(False)
        g = self._m_progress.addAction(
            'Пузырьки: %d игр · рекорд %d · всего лопнуто %d' % (
                self.progress.d['bub_games'], self.progress.d['bub_best'],
                self.progress.d['bub_total']))
        g.setEnabled(False)
        self._m_progress.addSeparator()
        for key, (name, desc) in ACHIEVEMENTS.items():
            if key in got:
                a = self._m_progress.addAction('✓ %s — %s' % (name, desc))
            else:
                a = self._m_progress.addAction('· %s — %s' % (name, desc))
                a.setEnabled(False)

    # ---------- тик ----------
    def _on_tick(self):
        now = time.time()
        dt = min(0.25, max(0.005, now - (self._last_t or now)))
        self._last_t = now
        self._tick_n += 1
        # в догонялках зверушкой движет игра (бег по всему экрану) —
        # обычное горизонтальное move() и «пол» не применяем
        tag_2d = self.game_active() and self._game_kind == 'tag'
        if not tag_2d:
            self.pet.move(dt)
        floor = self.pet.pos.y() if (self.dragging or tag_2d or self._fall) \
            else self.ground_y()
        # границы прогулки: весь экран или ширина окна-опоры
        wl, wr = self._walk_x or (self.geom.left(), self.geom.right())
        self.pet.tick(dt, floor, wl, wr)
        self._tick_fall(dt)
        self._handle_drag()
        self._handle_events()
        self._tick_game(dt)
        self._update_hover(dt)
        # опора-окно жива и на месте? (проверка ~раз в 1.2 с)
        if self._support and self._tick_n % 40 == 0 and not self.dragging \
                and not self._fall and not tag_2d:
            self._check_support()
        self._update_click_through()
        # прогресс: пройденный путь + аптайм/фокус-бонус
        if self.pet.px_walked > 0:
            px, self.pet.px_walked = self.pet.px_walked, 0.0
            self._progress_events(self.progress.on_walk(px, now))
        if not self.dragging:
            self._progress_events(
                self.progress.on_tick(dt, self.brain.idle, now))
        if self._tick_n % 50 == 0:
            set_topmost(self._hwnd, True)  # Windows иногда отнимает topmost
        a = self.brain.action
        idle = a in ('sit', 'sleep') and not self.pet.particles \
            and not self.pet.bubble_active() and not self.game_active() \
            and not self._treats and not self._bubbles and not self._pops
        if idle and self._tick_n % 5 != 0 and self._last_face == self.brain.face:
            return  # в покое редкая перерисовка
        self._last_face = self.brain.face
        self.update()

    def _handle_drag(self):
        if not self.dragging:
            return
        pos = cursor_pos()
        tx = pos.x() - self.drag_off[0]
        ty = pos.y() - self.drag_off[1]
        dist = ((tx - self.pet.pos.x()) ** 2 +
                (ty - self.pet.pos.y()) ** 2) ** 0.5
        self._drag_moved += dist
        pad = self.pet.edge_pad()
        self.pet.pos.setX(min(max(tx, self.geom.left() + pad),
                              self.geom.right() - pad))
        # вертикаль: макушка самой высокой позы не должна уходить за верх
        self.pet.pos.setY(min(max(ty, self.geom.top() +
                                  self.pet.top_clearance()),
                              self.geom.bottom() - 8))
        if self._drag_moved > 12:
            # Лапки перебирают ОТ ПЕРЕМЕЩЕНИЯ курсора (кадр на ~половину
            # роста фигурки), а не от тиков таймера: держишь неподвижно —
            # зверёк висит спокойно, несёшь — слегка дрыгает лапками.
            self.pet.body_frame += dist / max(20.0, self.pet.base_h * 0.5)
            self.update()

    def _handle_events(self):
        b = self.brain
        now = time.time()
        for ev in b.events:
            kind = ev[0]
            if kind == 'hearts':
                self.pet.burst('hearts')
                self._progress_events(self.progress.on_loved(now))
            elif kind == 'pyoo':
                self._progress_events(self.progress.on_click(now))
            elif kind == 'jump':
                self.pet.burst('jump')
                self._progress_events(self.progress.on_click(now, double=True))
            elif kind == 'angry':
                self.pet.burst('angry')
            elif kind == 'drop':
                self.pet.burst('drop')
            elif kind == 'curious':
                self.pet.burst('curious')
                b.set_face('curious', 2.5)
            elif kind == 'wake':
                b.set_face('surprised', 2.0)
            elif kind == 'zzz_start':
                self._progress_events(self.progress.on_zzz(now))
            elif kind == 'phrase':
                self.pet.say(self.pet.rng.choice(PHRASES))
                self._progress_events(self.progress.on_phrase(now))
        b.events.clear()

    def _update_hover(self, dt):
        """Наведение курсора: копим время ховера для умиления.

        Реакция испуга на резкое движение курсора УБРАНА по требованию
        пользователя (23.11): подвод курсора — это всегда намеренное
        внимание, зверушка не должна пугаться или грустить."""
        cur = cursor_pos()
        over = self.pet.contains(QPointF(cur.x(), cur.y()))
        self.brain.hover_tick(dt, over)

    def _update_click_through(self):
        cur = cursor_pos()
        p = QPointF(cur.x(), cur.y())
        over = self.pet.contains(p) or self._game_zone_contains(p)
        ct = not over
        if ct == self._click_through:
            return
        self._click_through = ct
        style = _exstyle(self._hwnd)
        style = (style | WS_EX_TRANSPARENT) if ct else (style & ~WS_EX_TRANSPARENT)
        _set_exstyle(self._hwnd, style)

    # ---------- мышь ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            p = e.globalPosition().toPoint()
            # мини-игры: клики по игровым объектам (лакомства, пузырьки)
            if self.game_active():
                if self._game_close_rect().contains(QPointF(p.x(), p.y())):
                    self._end_game()      # крестик — прервать игру досрочно
                    e.accept()
                    return
                if self._game_kind == 'bub':
                    for b in list(self._bubbles):
                        if ((b['x'] - p.x()) ** 2 +
                                (b['y'] - p.y()) ** 2) <= (b['r'] + 6) ** 2:
                            self._pop_bubble(b)
                            e.accept()
                            return
                elif self._game_kind == 'feed' and \
                        not self.pet.contains(QPointF(p.x(), p.y())):
                    self._place_treat(p.x())
                    e.accept()
                    return
            if self.pet.contains(QPointF(p.x(), p.y())):
                self.dragging = True
                self._drag_moved = 0.0
                self.drag_off = (p.x() - int(self.pet.pos.x()),
                                 p.y() - int(self.pet.pos.y()))
                self.brain.grabbed()
                e.accept()

    def mouseDoubleClickEvent(self, e):
        self.brain.click(double=True)
        self.pet.body_frame = 0.0
        # следующий release — «хвост» двойного клика: не превращать его
        # в ещё один одиночный клик (перекрывал бы реакцию на дабл-клик)
        self._suppress_dbl_release = True

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        # Qt шлёт дабл-клик как press → release → dblclick → release:
        # последний release приходит при dragging=False, флаг «хвоста»
        # дабл-клика надо снять и здесь, иначе он проглотит СЛЕДУЮЩИЙ клик.
        if not self.dragging:
            self._suppress_dbl_release = False
            return
        self.dragging = False
        if self._drag_moved > 12:
            # ПОСАДКА: зверушка ВСЕГДА падает вниз. Если под ногами
            # (строго ниже точки отпускания) есть верхняя кромка окна —
            # приземляется на неё и гуляет в пределах окна; если её
            # отпустили НА ФОНЕ окна (кромка выше точки отпускания) или
            # над рабочим столом — падает на панель задач
            land = self._landing_support(self.pet.pos.x(),
                                         self.pet.pos.y())
            if land:
                self._support, rect = land
                self.floor_y = float(rect[1])
                self._walk_x = (float(rect[0]), float(rect[2]))
            else:
                self._support = None
                self._walk_x = None
                self.floor_y = float(self._taskbar_top())
            self.brain.released_grabbed()   # тихо выйти из позы «в руках»
            self._begin_fall()              # и падать на опору
            self.save_settings()
        elif self.game_active() and self._game_kind == 'tag':
            self.brain.released_grabbed()  # выйти из позы «в руках»...
            self._game_hit()               # ...и засчитать попадание
        elif self._suppress_dbl_release:
            self._suppress_dbl_release = False
            self.brain.released_grabbed()  # просто выйти из позы «в руках»
        else:
            self.brain.click()
        self.pet.body_frame = 0.0
        e.accept()

    # ---------- трей ----------
    def toggle_pause(self, paused):
        self.brain.tempo = 0.0 if paused else 1.0
        self.save_settings()

    def quit_app(self):
        """Настоящий выход: сохранить настройки и завершить ПРОЦЕСС.

        Просто self.close() недостаточно: setQuitOnLastWindowClosed(False),
        и приложение оставалось бы жить без окна и трея («зомби»)."""
        self.save_settings()
        QApplication.quit()

    def scale_pet(self, k):
        self.settings['scale'] = min(2.5, max(0.4, self.settings['scale'] * k))
        self.pet.base_h = 130.0 * self.settings['scale']
        self.save_settings()

    # ---------- paint ----------
    def paintEvent(self, e):
        p = QPainter(self)
        self.pet.paint(p)
        self._paint_game(p)
        p.end()

    def _paint_game(self, p):
        """Объекты мини-игр: лакомства на дорожке, пузырьки, вспышки."""
        from PySide6.QtGui import QPen, QColor, QBrush
        from PySide6.QtCore import QRectF
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        now = time.time()
        # лакомства: ВИДИМАЯ «дорожка» вдоль пола (по ней кликают),
        # пока лакомств нет — пульсирующие подсказки, куда ставить
        if self.game_active() and self._game_kind == 'feed':
            band_h = 46.0
            rect = QRectF(self.geom.left() + 18, self.floor_y - band_h / 2,
                          self.geom.width() - 36, band_h)
            p.setPen(QPen(QColor(150, 110, 60, 170), 2,
                          Qt.PenStyle.DashLine))
            p.setBrush(QColor(255, 240, 200, 55))
            p.drawRoundedRect(rect, 12, 12)
            if not self._treats:
                pulse = 0.5 + 0.5 * math.sin(now * 5.0)
                alpha = int(90 + 120 * pulse)
                p.setPen(QPen(QColor(150, 110, 60, alpha), 2))
                p.setBrush(QColor(255, 235, 190, int(alpha * 0.45)))
                cx = self.pet.pos.x()
                for hx in (cx - 170, cx + 170, cx - 340, cx + 340):
                    if rect.left() + 24 < hx < rect.right() - 24:
                        r = 9 + 3 * pulse
                        hy = self.floor_y
                        p.drawEllipse(QRectF(hx - r, hy - r, 2 * r, 2 * r))
        # лакомства: печенька, чуть «дышит» на месте
        for t in self._treats:
            r = self.pet.base_h * 0.13
            bob = math.sin(now * 4.0 + t['bob']) * r * 0.15
            x, y = t['x'], self.floor_y - r + bob
            p.setPen(QPen(QColor(90, 55, 25), 2))
            p.setBrush(QColor(198, 134, 66))
            p.drawEllipse(QRectF(x - r, y - r, 2 * r, 2 * r))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(80, 45, 20))
            for ox, oy in ((-0.4, -0.2), (0.25, 0.1), (-0.05, 0.4)):
                p.drawEllipse(QRectF(x + ox * r - r * 0.16,
                                     y + oy * r - r * 0.16,
                                     r * 0.32, r * 0.32))
        # пузырьки: полупрозрачная сфера с бликом
        for b in self._bubbles:
            r = b['r']
            p.setPen(QPen(QColor(255, 255, 255, 190), 2))
            p.setBrush(QColor(200, 225, 255, 70))
            p.drawEllipse(QRectF(b['x'] - r, b['y'] - r, 2 * r, 2 * r))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 200))
            p.drawEllipse(QRectF(b['x'] - r * 0.55, b['y'] - r * 0.6,
                                 r * 0.42, r * 0.30))
        # вспышки лопнувших: расходящееся колечко
        for pop in self._pops:
            t01 = pop['age'] / 0.35
            r = 8 + 26 * t01
            p.setPen(QPen(QColor(255, 255, 255, int(220 * (1 - t01))), 3))
            p.setBrush(QBrush())
            p.drawEllipse(QRectF(pop['x'] - r, pop['y'] - r, 2 * r, 2 * r))
        # крестик «прервать игру» — правый верхний угол, всегда под рукой
        if self.game_active():
            rect = self._game_close_rect()
            cx, cy = rect.center().x(), rect.center().y()
            r = rect.width() / 2
            p.setPen(QPen(QColor(120, 60, 50, 220), 2))
            p.setBrush(QColor(255, 235, 230, 200))
            p.drawEllipse(rect)
            p.setPen(QPen(QColor(150, 50, 40, 230), 3))
            d = r * 0.42
            p.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))
            p.drawLine(QPointF(cx - d, cy + d), QPointF(cx + d, cy - d))
        p.restore()

    # ---------- settings ----------
    def _load_settings(self):
        s = dict(DEFAULTS)
        try:
            with open(SETTINGS_PATH, encoding='utf-8') as f:
                s.update(json.load(f))
        except Exception:
            pass
        return s

    def save_settings(self):
        self.settings['pos_x'] = int(self.pet.pos.x())
        # pos_y намеренно НЕ сохраняем: при запуске зверушка всегда
        # возвращается на панель задач.
        self.settings.pop('pos_y', None)
        self.settings['progress'] = self.progress.d
        try:
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=1)
        except Exception:
            pass

    def closeEvent(self, e):
        self.save_settings()
        super().closeEvent(e)


def main():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName('DesktopPet')
    # защита от двойного запуска: зверушка живёт в трее, и второй запуск
    # просто рисует второго хомяка поверх первого
    if _already_running():
        QMessageBox.information(
            None, 'Зверушка уже запущена',
            'Зверушка уже работает — посмотрите в системный трей '
            '(иконка рядом с часами, возможно, в свёрнутых иконках).')
        return
    # иконка выбранного питомца (до создания окна)
    s = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, encoding='utf-8') as f:
            s.update(json.load(f))
    except Exception:
        pass
    pets = available_pets()
    pet = s.get('pet', DEFAULT_PET)
    if pet not in pets:
        pet = DEFAULT_PET if DEFAULT_PET in pets else pets[0]
    app.setWindowIcon(QIcon(icon_path(pet)))
    win = PetWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()


