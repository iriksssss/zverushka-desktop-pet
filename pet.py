# -*- coding: utf-8 -*-
"""Сама зверюшка: позиция, движение, анимация, частицы, хит-тест."""
import math
import random

from PySide6.QtCore import QPointF, QRectF

from sprites import POSE_SCALE, _content_bbox, get, get_aligned

# Размер фигурки: рендер — ПО КОНТЕНТУ (get_aligned): высота не «плывёт»
# от кадра к кадру из-за разных прозрачных полей в файлах, низ контента —
# на линии пола. Для питомцев с разнородными сгенерированными позами
# (терьер, котик) действует ручная таблица масштабов POSE_SCALE
# (sprites.py): коэффициенты подобраны визуально по сетке _pose_grid.py
# так, чтобы фигурка выглядела одинакового размера во всех позах.


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'age', 'name', 'size', 'flip')

    def __init__(self, x, y, vx, vy, life, name, size, flip=False):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.age = life, 0.0
        self.name, self.size, self.flip = name, size, flip

    def tick(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    @property
    def alpha(self):
        t = self.age / self.life
        return 1.0 if t < 0.6 else max(0.0, 1.0 - (t - 0.6) / 0.4)


class Pet:
    def __init__(self, brain):
        self.brain = brain
        self.rng = random.Random()
        self.sprites = None           # PetSprites — задаётся из app.py
        self.pos = QPointF(0, 0)      # центр низа зверушки (на «полу»)
        self.base_h = 120.0             # базовая высота (scale в настройках)
        self.body_frame = 0.0
        self.particles = []
        self.zzz_timer = 0.0
        self.speed = 60.0               # px/сек хода (базово)
        self.px_walked = 0.0            # путь с прошлого тика (для прогресса)
        # облачко с фразой (мотивашка): текст + сколько секунд осталось
        self.bubble_text = None
        self.bubble_left = 0.0
        self.bubble_dur = 5.0
        self._edge_pad = {}             # (pet, base_h) -> отступ от края

    # ---------- размеры ----------
    def body_height(self):
        """Базовая высота тела. РЕНДЕР конкретного кадра дополнительно
        умножается на _pose_scale (таблица POSE_SCALE) — фигурка
        выглядит одинаковой, а не растёт/уменьшается от позы к позе."""
        return self.base_h

    def _pose_scale(self, name):
        """Масштаб конкретного кадра из таблицы POSE_SCALE (подобран
        визуально по _pose_grid.py). Кадры вне таблицы — 1.0."""
        if self.sprites is None:
            return 1.0
        return POSE_SCALE.get(self.sprites.pet, {}).get(name, 1.0)

    def top_clearance(self):
        """Максимальная высота рендера среди всех кадров: на столько
        выше «пола» может подниматься макушка (для клэмпа переноса —
        чтобы позы не обрезались верхним краем экрана)."""
        if self.sprites is None:
            return self.base_h
        key = (self.sprites.pet, int(self.base_h), 'top')
        val = self._edge_pad.get(key)
        if val is None:
            S = self.sprites
            names = set(S.WALK + S.SIT + S.SLEEP + S.REACT_ALL)
            val = self.base_h * max(1.0, max(
                self._pose_scale(n) for n in names))
            self._edge_pad[key] = val
        return val

    def edge_pad(self):
        """Половина ширины самого широкого кадра при текущем масштабе.

        pos.x — ЦЕНТР фигурки, поэтому без этого отступа широкие позы
        (лёжа, испуг) наполовину уходят за край экрана и обрезаются."""
        if self.sprites is None:
            return 16.0
        key = (self.sprites.pet, int(self.base_h))
        pad = self._edge_pad.get(key)
        if pad is None:
            pad = 16.0
            S = self.sprites
            names = set(S.WALK + S.SIT + S.SLEEP + S.REACT_ALL)
            for n in names:
                x0, y0, x1, y1 = _content_bbox(S.pet, n)
                w, hh = (x1 - x0 + 1), max(1, y1 - y0 + 1)
                pad = max(pad, w / hh * self.base_h *
                          self._pose_scale(n) * 0.5)
            self._edge_pad[key] = pad
        return pad

    def footprint(self):
        """Прямоугольник-тело вокруг позиции (для хит-теста)."""
        h = self.body_height()
        w = h * 0.85
        h2 = h * 0.95
        return QRectF(self.pos.x() - w / 2, self.pos.y() - h2, w, h2)

    def contains(self, p, margin=12.0):
        return self.footprint().adjusted(-margin, -margin, margin, margin).contains(p)

    # ---------- обновление ----------
    def tick(self, dt, ground_y, screen_left, screen_right, margin=16.0):
        b = self.brain
        dts = dt * b.tempo
        if dts <= 0:
            return
        # отступ от краёв — по реальной ширине самого широкого кадра:
        # широкие позы не должны обрезаться краем экрана
        margin = max(margin, self.edge_pad())
        left = screen_left + margin
        right = screen_right - margin
        if right < left:
            # окно-опора уже фигурки: стоим по центру опоры
            left = right = (left + right) / 2.0
        self.pos = QPointF(max(left, min(right, self.pos.x())), ground_y)
        b.tick_face(dt)
        b.tick_action(dts, self.pos.x(), left, right)
        # В движении (walk/run) кадры переключаются от ПРОЙДЕННОГО ПУТИ
        # (см. move) — так лапы не «проскальзывают» и темп анимации всегда
        # совпадает со скоростью. В остальных действиях — от времени.
        if b.action not in ('walk', 'run'):
            self.body_frame += dts * self._anim_speed()
        for p in list(self.particles):
            p.tick(dts)
            if p.age >= p.life:
                self.particles.remove(p)
        if self.bubble_left > 0:
            self.bubble_left = max(0.0, self.bubble_left - dts)
        # пыль из-под лап на бегу
        if b.action == 'run' and self.rng.random() < dts * 8.0:
            self.add_particle('dust', dx=-0.30 * b.direction, dy=-0.02,
                              vx=-22 * b.direction, vy=-7,
                              life=0.55, size=self.base_h * 0.15)
        if b.action == 'sleep':
            self.zzz_timer -= dts
            if self.zzz_timer <= 0:
                self.zzz_timer = 1.6
                self.add_particle('zzz', dx=0.1, dy=-1.0, vx=14, vy=-24,
                                  life=2.2, size=self.base_h * 0.26)
        if b.face == 'angry' and self.rng.random() < dts * 3.0:
            self.add_particle('smoke', dx=self.rng.uniform(-0.1, 0.1), dy=-1.02,
                              vx=self.rng.uniform(-6, 6), vy=-28,
                              life=1.0, size=self.base_h * 0.14)

    def _anim_speed(self):
        a = self.brain.action
        return {'sit': 0.8, 'sleep': 1.0, 'jump': 8.0, 'crouch': 12.0,
                'stretch': 3.0, 'grabbed': 4.0, 'fall': 2.0}.get(a, 1.0)

    def move(self, dt):
        b = self.brain
        if b.tempo <= 0:
            return
        if b.action in ('walk', 'run'):
            # бег заметно быстрее ходьбы (×3.0), но кадры переключаются
            # от ПРОЙДЕННОГО ПУТИ — лапы перебирают ровно с той скоростью,
            # с которой фигурка едет по экрану, без «скольжения» и без
            # мельтешения (stride подобран так, чтобы на бегу было
            # ~9-10 кадров/с: перебор лап виден, но не рябит).
            # Формула одинакова для всех зверушек — скорости равны.
            k = 3.0 if b.action == 'run' else 1.0
            dx = b.direction * self.speed * k * dt * b.tempo
            self.pos.setX(self.pos.x() + dx)
            stride = max(7.0, self.body_height() *
                         (0.075 if b.action == 'walk' else 0.16))
            self.body_frame += abs(dx) / stride
            self.px_walked += abs(dx)   # суммарный путь лапами (прогресс)

    # ---------- частицы ----------
    def add_particle(self, name, dx=0.0, dy=-1.0, vx=0.0, vy=-20.0,
                     life=1.4, size=None, flip=False):
        size = size or self.base_h * 0.2
        self.particles.append(Particle(
            self.pos.x() + dx * self.base_h, self.pos.y() + dy * self.base_h,
            vx, vy, life, name, size, flip))

    def burst(self, kind):
        h = self.base_h
        r = self.rng
        if kind == 'hearts':
            for _ in range(5):
                self.add_particle(r.choice(['heart_s', 'heart_b']),
                                  dx=r.uniform(-0.3, 0.3), dy=-1.0,
                                  vx=r.uniform(-24, 24), vy=r.uniform(-46, -30),
                                  life=r.uniform(1.2, 2.0), size=h * 0.15)
        elif kind in ('jump', 'drop'):
            self.add_particle('star', dx=0.2, dy=-1.05, vx=18, vy=-38, life=1.0, size=h * 0.2)
            self.add_particle('dust', dx=-0.28, dy=-0.02, vx=-16, vy=-8, life=0.7, size=h * 0.2)
            self.add_particle('dust', dx=0.28, dy=-0.02, vx=16, vy=-8, life=0.7, size=h * 0.2)
        elif kind == 'angry':
            for _ in range(3):
                self.add_particle('smoke', dx=r.uniform(-0.15, 0.15), dy=-1.02,
                                  vx=r.uniform(-8, 8), vy=-32, life=1.0, size=h * 0.14)
        elif kind == 'curious':
            self.add_particle('star', dx=0.15 * self.brain.direction, dy=-1.05,
                              vx=6 * self.brain.direction, vy=-20, life=0.9, size=h * 0.15)

    # ---------- отрисовка ----------
    def _pick_sheet(self):
        """Выбор ПОЛНОГО тела (эмоция вшита в позу). Без оверлея мордочки."""
        S = self.sprites
        b = self.brain
        a = b.action
        f = b.face
        n = int(self.body_frame)
        if a in ('walk', 'run'):
            # один цикл шага (S.GAIT) и для шага, и для бега — отличается
            # только темп (stride в move) и наклон корпуса (paint)
            sheet = S.GAIT
            return sheet, n % len(sheet)
        if a == 'sleep':
            return S.SLEEP, n % len(S.SLEEP)
        if a == 'fall':
            # падение на опору: «воздушный» кадр (react_19), без прыжкового
            # squash — высоту задаёт физика падения в app._tick_fall
            return S.FALL, n % len(S.FALL)
        if a in S.REACT:  # jump / crouch / stretch / grabbed
            sheet = S.REACT[a]
            return sheet, n % len(sheet)
        if a in ('lonely', 'shy'):
            # спец-позы тела под эмоцией (со своей мордой)
            sheet = S.SIDE.get(f) or S.SIDE.get('lonely') or S.SIT
            return sheet, n % len(sheet)
        # сидение: спереди с эмоцией или сбоку с обычной мордой
        if a == 'sit':
            if f in S.FRONT:
                sheet = S.FRONT[f]
            elif f in S.SIDE:
                sheet = S.SIDE[f]
            else:
                sheet = S.SIT
                return sheet, [0, min(1, len(sheet) - 1)][n % 2]
            return sheet, n % len(sheet)
        return S.SIT, 0

    def say(self, text, dur=5.0):
        """Показать облачко с фразой над головой на dur секунд."""
        self.bubble_text = text
        self.bubble_left = dur
        self.bubble_dur = dur

    def bubble_active(self):
        return bool(self.bubble_text) and self.bubble_left > 0

    # ---------- отрисовка ----------
    def paint(self, painter):
        if self.sprites is None:
            return
        b = self.brain
        h = self.base_h
        flip = b.direction < 0
        a = b.action
        # покачивание в такт шагу: два «приземления» за цикл из 6 кадров
        amp = {'walk': 0.016, 'run': 0.022}.get(a, 0.0)
        bob = math.sin(self.body_frame * math.pi / 3.0) * amp * h
        if a == 'sleep':
            # медленное «дыхание» во сне (позиционный bob, размер не меняется)
            bob = math.sin(self.body_frame * 1.2) * 0.008 * h
        # подскок при прыжке
        squash = 0.0
        if a == 'jump':
            squash = -abs(math.sin(min(self.body_frame, math.pi))) * 0.16 * h

        # Тело рисуется ОДНИМ кадром (никаких кроссфейдов — двойных
        # изображений), отмасштабированным по КОНТЕНТУ, с поправкой
        # из POSE_SCALE для разнородных поз (терьер/котик).
        base_h = self.body_height()
        sheet, idx = self._pick_sheet()
        name = sheet[idx]
        body_h = base_h * self._pose_scale(name)
        img, cx_off, pad_bottom = get_aligned(self.sprites.pet, name,
                                              int(body_h), flip)
        floor_line = self.pos.y() + bob + squash
        if a == 'run':
            # наклон корпуса вперёд на бегу (вокруг точки опоры)
            painter.save()
            painter.translate(self.pos.x(), floor_line)
            painter.rotate(6.0 * b.direction)
            painter.drawImage(int(-cx_off), int(-body_h - pad_bottom), img)
            painter.restore()
        elif a == 'grabbed':
            # перенос: вместо мельтешения кадрами — плавное покачивание
            # всей фигурки (как зверёк, висящий в руке): лёгкий маятник
            # от времени + отклик на движение мыши (body_frame растёт
            # от пройденного курсором пути, см. app._handle_drag).
            sway = math.sin(b.time * 2.2) * 1.6 + \
                math.sin(self.body_frame * 0.9) * 3.5
            painter.save()
            painter.translate(self.pos.x(), floor_line)
            painter.rotate(sway)
            painter.drawImage(int(-cx_off), int(-body_h - pad_bottom), img)
            painter.restore()
        else:
            bx = int(self.pos.x() - cx_off)
            by = int(floor_line - body_h - pad_bottom)
            painter.drawImage(bx, by, img)

        # частицы (с затуханием через opacity)
        painter.save()
        for p in self.particles:
            alpha = p.alpha
            if alpha <= 0.02:
                continue
            img = get(self.sprites.pet, self.sprites.PART.get(p.name, 'part_star'),
                      int(p.size), p.flip)
            painter.setOpacity(alpha)
            painter.drawImage(int(p.x) - img.width() // 2,
                              int(p.y) - img.height() // 2, img)
        painter.restore()

        if self.bubble_active():
            self._paint_bubble(painter, body_h)

    def _paint_bubble(self, painter, body_h):
        """Облачко с фразой: белое скруглённое + хвостик к голове.

        Плавно появляется и гаснет (0.3 с). Положение — над головой,
        с зажимом в границы экрана, чтобы не улетать за край."""
        from PySide6.QtGui import QFont, QFontMetrics, QPen, QColor
        from PySide6.QtCore import QRectF, QPointF, Qt

        font = QFont('Segoe UI', max(9, int(self.base_h * 0.085)))
        font.setBold(True)
        fm = QFontMetrics(font)
        text = self.bubble_text
        tw = fm.horizontalAdvance(text)
        th = fm.height()
        pad_x, pad_y = 10, 7
        bw, bh = tw + 2 * pad_x, th + 2 * pad_y
        dev_w = painter.device().width()
        x = min(max(8.0, self.pos.x() - bw / 2), dev_w - bw - 8.0)
        # низ облачка — над головой с небольшим зазором
        y = self.pos.y() - body_h - 10 - bh
        if y < 6:
            y = self.pos.y() + 6  # совсем у края экрана — покажем снизу

        # плавность появления/исчезновения
        fade = min(1.0, (self.bubble_dur - self.bubble_left) / 0.3,
                   self.bubble_left / 0.3)
        painter.save()
        painter.setOpacity(max(0.0, fade))
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor(70, 45, 30), 2))
        painter.setBrush(QColor(255, 255, 250))
        painter.drawRoundedRect(QRectF(x, y, bw, bh), 9, 9)
        # хвостик
        tail_cx = min(max(x + 14, self.pos.x()), x + bw - 14)
        painter.drawPolygon([QPointF(tail_cx - 6, y + bh - 1),
                             QPointF(tail_cx + 6, y + bh - 1),
                             QPointF(self.pos.x(), y + bh + 9)])
        painter.setPen(QColor(60, 40, 28))
        painter.setFont(font)
        painter.drawText(QRectF(x + pad_x, y + pad_y, tw, th),
                         Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

