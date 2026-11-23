# -*- coding: utf-8 -*-
"""Загрузка спрайтов выбранного питомца.

Структура: assets/sprites/<питомец>/*.png. Спрайты разных питомцев
имеют одинаковые имена (walk_*, sit_*, react_*...), но число кадров
моет отличаться — PetSprites сама определяет, какие есть по факту,
и маппинг эмоций гибко сжимается под доступные кадры.
"""
import json
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QTransform, QImage, QPixmap

try:
    import numpy as _np
except Exception:  # numpy нет — bbox считать не сможем, работаем по старому
    _np = None


def assets_root():
    """Корень папки assets (спрайты, звуки, phrases.json).

    В frozen-сборке (PyInstaller) ищем СНАРУЖИ от EXE (onedir-раздача:
    пользователь может править phrases.json и докладывать спрайты),
    затем во вложенном _internal и в sys._MEIPASS (onefile)."""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        for cand in (os.path.join(exe_dir, 'assets'),
                     os.path.join(exe_dir, '_internal', 'assets'),
                     os.path.join(getattr(sys, '_MEIPASS', exe_dir),
                                  'assets')):
            if os.path.isdir(cand):
                return cand
        return os.path.join(exe_dir, 'assets')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


SPRITES_ROOT = os.path.join(assets_root(), 'sprites')
DEFAULT_PET = 'hamster'

# Отображаемые имена питомцев (в меню и тултипе — по-русски)
PET_NAMES = {
    'hamster': 'Хомячок',
    'terrier': 'Скотч-терьер',
    'cat': 'Котик',
}


def pet_display_name(pet):
    return PET_NAMES.get(pet, pet.title())

# размер исходников пиксель-арт: масштабирование делаем SMOOTH
# (сглаживает рваные края) + кэш, чтобы не масштабить каждый тик
_PX_CACHE = {}
_FRAME_CACHE = {}
_BBOX_CACHE = {}   # (pet, name) -> (x0, y0, x1, y1) НЕпрозрачного контента


def _content_bbox(pet, name):
    """Прямоугольник непрозрачного контента спрайта (в пикселях исходника).

    Нужен для рендера «по контенту»: все кадры ленты рисуются с одинаковой
    высотой КОНТЕНТА и общей базовой линией (низ контента на полу), поэтому
    фигурка не «прыгает» размером на несколько пикселей от кадра к кадру.
    """
    key = (pet, name)
    bb = _BBOX_CACHE.get(key)
    if bb is not None:
        return bb
    src = _pix(pet, name)
    bb = (0, 0, max(0, src.width() - 1), max(0, src.height() - 1))
    if _np is not None and not src.isNull():
        try:
            a = src.toImage().convertToFormat(QImage.Format.Format_Alpha8)
            w, h, bpl = a.width(), a.height(), a.bytesPerLine()
            buf = a.constBits()
            arr = _np.frombuffer(buf, _np.uint8,
                                 a.sizeInBytes()).reshape(h, bpl)[:, :w]
            ys, xs = _np.where(arr > 8)
            if len(xs):
                bb = (int(xs.min()), int(ys.min()),
                      int(xs.max()), int(ys.max()))
        except Exception:
            pass
    _BBOX_CACHE[key] = bb
    return bb


def pet_dir(pet):
    return os.path.join(SPRITES_ROOT, pet)


def available_pets():
    """Подпапки, содержащие хотя бы один walk/sit/.react спрайт."""
    out = []
    if not os.path.isdir(SPRITES_ROOT):
        return out
    for d in sorted(os.listdir(SPRITES_ROOT)):
        p = os.path.join(SPRITES_ROOT, d)
        if os.path.isdir(p) and any(f.startswith(('walk_', 'sit_', 'react_'))
                                    and f.endswith('.png')
                                    for f in os.listdir(p)):
            out.append(d)
    return out or [DEFAULT_PET]


def icon_path(pet):
    return os.path.join(pet_dir(pet), 'icon.png')


# Покадровые переопределения для питомцев со СГЕНЕРИРОВАННОЙ раскадровкой.
# У хомячка все позы нарисованы в одном размере — чередование кадров даёт
# живую анимацию. У терьера и котика соседние react-кадры — это РАЗНЫЕ позы
# (сидя ↔ стоя столбиком ↔ лёжа), их чередование выглядит мельтешением,
# а выравнивание по высоте контента делает «вытянутые» кадры визуально
# меньше. Поэтому каждая эмоция/реакция у них — ОДИН статичный кадр,
# а живость дают частицы, покачивание корпуса и наклоны (pet.py).
_POSE_OVERRIDES = {
    'terrier': {
        'FRONT.normal': ['react_00'],
        'FRONT.happy': ['react_06'],
        'FRONT.loved': ['react_06'],
        'FRONT.curious': ['react_05'],
        'FRONT.surprised': ['react_01'],
        'FRONT.content': ['react_08'],   # довольный, глаза закрыты
        'FRONT.playful': ['react_07'],   # игривый (play-bow)
        'SIDE.scared': ['react_14'],
        'SIDE.lonely': ['react_16'],
        'SIDE.angry': ['react_17'],   # злой: нахмурен, лапа поднята
        'REACT.crouch': ['react_14'],
        'REACT.jump': ['react_19'],    # реальный «воздушный» кадр
        # «в руках»: висячая поза react_02 — читается как поднятый
        'REACT.grabbed': ['react_02'],
        'REACT.stretch': ['react_05'],
    },
    'cat': {
        'FRONT.normal': ['react_00'],
        'FRONT.happy': ['react_06'],
        'FRONT.loved': ['react_06'],     # радость с поднятыми лапами
        'FRONT.curious': ['react_05'],
        'FRONT.surprised': ['react_01'],
        'FRONT.content': ['react_08'],   # довольный, глаза закрыты
        'FRONT.playful': ['react_07'],   # игривый (лапка поднята)
        'SIDE.scared': ['react_14'],
        'SIDE.lonely': ['react_16'],
        'SIDE.angry': ['react_17'],   # злой: нахмуренные брови
        'REACT.crouch': ['react_14'],
        'REACT.jump': ['react_19'],    # реальный «воздушный» кадр
        'REACT.grabbed': ['react_02'],
        'REACT.stretch': ['react_05'],
    },
}


def clear_caches():
    _PX_CACHE.clear()
    _FRAME_CACHE.clear()
    _BBOX_CACHE.clear()


# Ручные поправки масштаба кадров для питомцев с разнородными
# сгенерированными позами: 1.0 = базовая высота, меньше — поза рендерится
# меньше. Подобраны визуально по сеткам _pose_grid.py (_size_<pet>.png),
# чтобы фигурка выглядела ОДИНАКОВОГО размера во всех позах: у лежачих
# и «столбиковых» поз контент вытянут иначе, и равная высота контента
# делает их визуально крупнее/меньше остальных. Кадры вне таблицы — 1.0.
POSE_SCALE = {
    'hamster': {
        'react_18': 0.52,   # расплющенный (широкий и низкий) — испуг
        'react_19': 0.92,   # прыжок в воздухе
    },
    'terrier': {
        'sleep_0': 0.85,
        'react_02': 1.05,   # висячая поза «в руках»
        'react_05': 0.92, 'react_06': 0.95, 'react_08': 0.97,
        'react_07': 0.85,   # play-bow (широкий и низкий)
        'react_14': 0.80,   # лёжа (испуг/злость)
        'react_15': 0.95,
        'react_16': 0.90,   # лёжа, грустная
        'react_19': 0.92,   # прыжок в воздухе
    },
    'cat': {
        'sleep_0': 0.92,
        'react_05': 0.92,
        'react_06': 0.95,   # радость с поднятыми лапами (перегенерирован)
        'react_07': 0.95,   # игривый, лапка поднята
        'react_14': 0.78,   # лёжа (испуг/злость)
        'react_15': 0.95,
        'react_16': 0.82,   # лёжа, грустная
        'react_19': 0.92,   # прыжок в воздухе
    },
}


def _pix(pet, name):
    key = (pet, name)
    im = _PX_CACHE.get(key)
    if im is None:
        im = QPixmap(os.path.join(pet_dir(pet), name + '.png'))
        _PX_CACHE[key] = im
    return im


def _scaled(pet, name, h, flip):
    key = (pet, name, h, flip)
    im = _FRAME_CACHE.get(key)
    if im is not None:
        return im
    src = _pix(pet, name)
    h = max(1, int(h))
    if flip:
        tr = QTransform()
        tr.scale(-1, 1)
        src = src.transformed(tr, Qt.TransformationMode.SmoothTransformation)
    w = max(1, int(src.width() * h / max(1, src.height())))
    im = src.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation).toImage()
    _FRAME_CACHE[key] = im
    return im


def get(pet, name, h, flip=False):
    """Спрайт высотой h (плавное масштабирование, кэшированный)."""
    return _scaled(pet, name, int(h), bool(flip))


def get_aligned(pet, name, content_h, flip=False):
    """Спрайт, обрезанный до контента и отмасштабированный ровно до
    высоты content_h.

    Возвращает (image, cx_off, pad_bottom):
      image      — QImage с контентом впритык (без прозрачных полей),
                   высота ровно content_h;
      cx_off     — x центра контента внутри image (для центровки по pos.x);
      pad_bottom — всегда 0 (низ image = низ контента = «пол»).

    Это убирает «пульсацию» размера: у кадров одной ленты поля прозрачности
    разные, и масштаб «по высоте файла» давал разную высоту фигурки.
    """
    key = (pet, name, int(content_h), bool(flip), 'aligned')
    hit = _FRAME_CACHE.get(key)
    if hit is not None:
        return hit
    src = _pix(pet, name)
    if src.isNull():
        img = QImage(1, 1, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        _FRAME_CACHE[key] = (img, 0.5, 0)
        return _FRAME_CACHE[key]
    x0, y0, x1, y1 = _content_bbox(pet, name)
    crop = src.copy(x0, y0, x1 - x0 + 1, y1 - y0 + 1)
    if flip:
        tr = QTransform()
        tr.scale(-1, 1)
        crop = crop.transformed(tr, Qt.TransformationMode.SmoothTransformation)
    # высоту задаём жёстко (ширина — по пропорции): огромная рамка по X
    content_h = max(1, int(content_h))
    img = crop.scaled(100000, content_h, Qt.AspectRatioMode.KeepAspectRatio,
                      Qt.TransformationMode.SmoothTransformation).toImage()
    res = (img, img.width() / 2.0, 0)
    _FRAME_CACHE[key] = res
    return res


class PetSprites:
    """Названия спрайтов одного питомца (реальный маппинг — make_sprites.py).

    Автоматически определяет число кадров по наличию файлов,
    поэтому новый питомец может дать минимум кадров (хотя бы walk_0/sit_0)
    и всё равно работать.
    """

    def __init__(self, pet=DEFAULT_PET):
        self.pet = pet
        self._scan()

    # ---- авто-определение кадров ----
    def _scan(self):
        d = pet_dir(self.pet)
        have = set(os.listdir(d)) if os.path.isdir(d) else set()

        def count(prefix, start=0):
            n = 0
            i = start
            while (('%s_%d' % (prefix, i)) + '.png' in have or
                   ('%s_%02d' % (prefix, i)) + '.png' in have):
                n += 1
                i += 1
            return n

        self.walk_n = max(1, count('walk'))
        self.sit_n = max(1, count('sit'))
        self.sleep_n = max(1, count('sleep'))
        # react-кадры могут идти с ПРОПУСКАМИ (react_00..03, 05, 06...):
        # считаем по факту наличия файлов, а не подряд
        reacts = sorted(f[:-4] for f in have
                        if f.startswith('react_') and f.endswith('.png'))
        self.react_n = len(reacts)

        self.WALK = ['walk_%d' % i for i in range(self.walk_n)]
        self.SIT = ['sit_%d' % i for i in range(self.sit_n)]
        self.SLEEP = ['sleep_%d' % i for i in range(self.sleep_n)]
        self.REACT_ALL = reacts
        # Цикл шага: крайние кадры исходной ленты — «развороты» (вид со
        # спины), поэтому для ходьбы/бега берём середину ленты — кадры
        # одного ракурса 3/4, движение выглядит цельным, без скольжения.
        self.GAIT = list(self.WALK[1:-1]) if len(self.WALK) >= 4 else self.WALK

        # эмоции: списки по убыванию предпочтения — берём первый
        # список, целиком присутствующий в арте
        def pick(cands):
            for names in cands:
                if len(names) and all(n + '.png' in have for n in names):
                    return list(names)
            # запас: любой имеющийся react или сидение
            return self.REACT_ALL[:1] or self.SIT

        self.FRONT = {
            'normal': pick([['react_00', 'react_03'], ['react_00'], self.SIT]),
            'happy': pick([['react_06', 'react_07'], ['react_06'],
                           ['react_02'], self.SIT]),
            'loved': pick([['react_08', 'react_06'], ['react_08'],
                           ['react_06'], self.SIT]),
            'curious': pick([['react_05'], ['react_01'], self.SIT]),
            'surprised': pick([['react_01', 'react_02'], ['react_01'],
                               self.SIT]),
            'shy': pick([['react_15'], ['react_03'], self.SIT]),
            # довольный (глаза закрыты, мурлычет) и игривый (дурачится) —
            # случайные смены настроения, пока сидит (brain.tick_face)
            'content': pick([['react_10'], ['react_08'], self.SIT]),
            'playful': pick([['react_07', 'react_09'], ['react_07'],
                             ['react_06'], self.SIT]),
        }
        self.FRONT['sleepy'] = self.SLEEP

        def pick1(cands):
            for names in cands:
                if len(names) and all(n + '.png' in have for n in names):
                    return list(names)
            return self.SIT

        # ВАЖНО: react_11, react_12, react_13 — позы, где хомяка держит РУКА.
        # По требованию пользователя они НЕ используются нигде.
        self.SIDE = {
            'scared': pick1([['react_14', 'react_05'], ['react_14'], self.SIT]),
            'lonely': pick1([['react_16', 'react_17'], ['react_16'], self.SIT]),
            'angry': pick1([['react_20'], ['react_09'], self.SIT]),
        }
        self.REACT = {
            # испуг/приседание: react_18 — «расплющенный» хомяк из
            # референсов (part06); у терьера/котика — лежачий react_14
            'crouch': pick1([['react_18'], ['react_00', 'react_05'],
                             ['react_00'], self.SIT]),
            # прыжок: react_19 — реальный «воздушный» кадр из референсов;
            # если его нет — стоячая радость
            'jump': pick1([['react_19'], ['react_06', 'react_08'],
                           ['react_06'], ['react_02'], self.SIT]),
            # перенос мышью: «поднятый» хомяк без чужой руки в кадре
            'grabbed': pick1([['react_02', 'react_01'], ['react_02'], self.SIT]),
            'stretch': pick1([['react_05', 'react_03'], ['react_05'], self.SIT]),
        }
        # падение на опору после переноса: воздушный кадр (или прыжок)
        self.FALL = ['react_19'] if self.has('react_19') \
            else list(self.REACT['jump'])
        self.PART = {
            'heart_s': 'part_heart_s', 'heart_b': 'part_heart_b',
            'zzz': 'part_zzz', 'smoke': 'part_smoke', 'dust': 'part_dust',
            'cloud': 'part_cloud', 'star': 'part_star',
        }
        self._apply_overrides()

    def _apply_overrides(self):
        """Применить _POSE_OVERRIDES: одиночные кадры вместо чередования
        разнородных поз (см. комментарий у _POSE_OVERRIDES). Кадр
        применяется только если файл реально существует."""
        rules = _POSE_OVERRIDES.get(self.pet)
        if not rules:
            return
        tables = {'FRONT': self.FRONT, 'SIDE': self.SIDE, 'REACT': self.REACT}
        for slot, frames in rules.items():
            table_name, key = slot.split('.')
            if all(self.has(f) for f in frames):
                tables[table_name][key] = list(frames)

    def has(self, name):
        return os.path.isfile(os.path.join(pet_dir(self.pet), name + '.png'))
