# -*- coding: utf-8 -*-
"""Мозг зверушки: две независимые FSM — Action (тело) и Emotion (лицо)."""
import random

# Действия (тело)
A_WALK, A_RUN, A_SIT, A_SLEEP = 'walk', 'run', 'sit', 'sleep'
A_JUMP, A_CROUCH, A_STRETCH, A_GRABBED = 'jump', 'crouch', 'stretch', 'grabbed'
A_FALL = 'fall'                     # падение на опору после переноса

# Приоритеты лиц (чем выше, тем сильнее)
P = {'dragged': 10, 'surprised': 9, 'angry': 7,
     'loved': 6, 'happy': 5, 'shy': 5, 'curious': 4,
     'sleepy': 3, 'lonely': 3, 'content': 2, 'playful': 2, 'normal': 0}


class Brain:
    def __init__(self, rng=random.Random):
        self.rng = rng()
        self.action = A_SIT
        self.action_left = 4.0          # сколько сек осталось в действии
        self.direction = 1
        self.face = 'normal'
        self.face_left = 0.0
        self.face_priority = 0
        self.idle = 0.0                 # сек с последнего клика
        self.grumpy_time = 0.0          # сек с последнего клика (для злости)
        self.clicks_fast = 0            # клики за последние 5 с
        self._click_times = []
        self.time = 0.0                 # общее время
        self.hover_time = 0.0
        self.loved_fired = False
        self.tempo = 1.0                # множитель скорости (tray: пауза=0)
        self.events = []                # события для звука/частиц: (kind,)
        # мотивационное облачко: примерно раз в час (±10 мин)
        self.phrase_in = self._next_phrase_delay()

    def _next_phrase_delay(self):
        return 3600.0 + self.rng.uniform(-600.0, 600.0)

    # ---------- ЛИЦА ----------
    def set_face(self, name, duration, force=False):
        pr = P.get(name, 0)
        if force or pr >= self.face_priority:
            self.face, self.face_left, self.face_priority = name, duration, pr
        elif name == self.face:
            self.face_left = max(self.face_left, duration)

    def tick_face(self, dt):
        self.time += dt
        self.idle += dt
        # мотивационная фраза раз в ~час (не во сне и не в переносе)
        self.phrase_in -= dt
        if self.phrase_in <= 0:
            self.phrase_in = self._next_phrase_delay()
            if self.action not in (A_SLEEP, A_GRABBED):
                self.events.append(('phrase',))
        if self.face_left > 0:
            self.face_left -= dt
            if self.face_left <= 0:
                self.face_priority = 0
                self._context_face()
        # сонливость/грусть по времени без внимания — НО не во время
        # наведения курсора: если пользователь смотрит на зверушку,
        # она не грустит и не клюёт носом (баг 23.11: ховер по долго
        # спящей зверушке показывал печальную мордочку вместо умиления)
        if self.face_priority < P['sleepy'] and self.hover_time <= 0:
            if self.idle > 600:
                self.set_face('lonely', 1.0)
            elif self.idle > 300:
                self.set_face('sleepy', 1.0)
        # сидит без дела — иногда блаженствует (content) или дурачится
        # (playful): живая смена настроений в покое
        if self.action == A_SIT and self.face == 'normal' and \
                self.rng.random() < dt * 0.055:
            self.set_face(self.rng.choice(['content', 'content', 'playful']),
                          self.rng.uniform(2.5, 4.5))
        # по телу: грусть/стыд превращаем в обычное сидение
        # (поза под эмоцией выбирается в Pet._pick_sheet)
        if self.action in ('lonely', 'shy'):
            self.do(A_SIT, 8.0)

    def _context_face(self):
        self.face = 'sleepy' if self.action == A_SLEEP else 'normal'

    # ---------- ДЕЙСТВИЯ ----------
    def do(self, action, duration=None, force=False):
        if action == self.action and not force and duration is None:
            return
        self.action = action
        if duration is None:
            duration = self._default_duration(action)
        self.action_left = duration
        if action in (A_WALK, A_RUN) and self.direction == 0:
            self.direction = 1

    def _default_duration(self, action):
        r = self.rng
        return {A_WALK: r.uniform(4, 10), A_RUN: r.uniform(1.6, 3.0),
                A_SIT: r.uniform(5, 12), A_SLEEP: r.uniform(240, 480),
                A_JUMP: 1.0, A_CROUCH: 0.6, A_STRETCH: 0.9,
                A_GRABBED: 9999, A_FALL: 9999}[action]

    def tick_action(self, dt, x, screen_left, screen_right):
        if self.action in (A_GRABBED, A_FALL):
            return
        self.action_left -= dt * self.tempo
        moving = self.action in (A_WALK, A_RUN)
        if moving:
            if x <= screen_left:
                self.direction = 1
                self.events.append(('curious',))
            elif x >= screen_right:
                self.direction = -1
                self.events.append(('curious',))
        if self.action_left <= 0:
            self._pick_action()

    def _pick_action(self):
        r = self.rng
        if self.action == A_SLEEP:          # просыпается с потягушками
            self.do(A_STRETCH)
            return
        w = {A_WALK: 5, A_SIT: 4, A_RUN: 1.5 if self.idle > 20 else 0.4}
        if self.idle > 240:
            w[A_SLEEP] = min(6.0, (self.idle - 240) / 60.0)
        total = sum(w.values())
        roll = r.uniform(0, total)
        acc = 0
        for a, weight in w.items():
            acc += weight
            if roll <= acc:
                self.do(a)
                if a == A_SLEEP:
                    self.events.append(('zzz_start',))
                return

    # ---------- ВВОД ----------
    def released_grabbed(self):
        """Отпустили после захвата БЕЗ переноса (просто нажали и отпустили):
        выйти из позы «в руках», иначе зверушка застревала в ней навсегда
        (у grabbed длительность 9999 и tick_action её не истекает)."""
        self.face_priority = 0
        if self.action == A_GRABBED:
            self.do(A_SIT, 4.0)

    def click(self, double=False):
        if self.action == A_GRABBED:
            self.released_grabbed()
        now = self.time
        self._click_times = [t for t in self._click_times if now - t < 5.0]
        self._click_times.append(now)
        self.clicks_fast = len(self._click_times)
        self.idle = 0.0
        if self.action == A_SLEEP:
            self.do(A_STRETCH)
            self.events.append(('wake',))
        if self.clicks_fast >= 5:
            self.set_face('angry', 5.0)
            self.events.append(('angry',))
        elif double:
            self.set_face('shy', 4.0)
            self.events.append(('jump',))
        else:
            self.set_face('happy', 3.0)
            self.events.append(('pyoo',))
        if self.action in (A_SIT,):
            self.do(self.rng.choice([A_SIT, A_WALK, A_SIT]))

    def hover_tick(self, dt, hovering):
        if hovering:
            self.hover_time += dt
            if self.hover_time > 3 and not self.loved_fired:
                # не перебиваем сильные эмоции (злость/удивление):
                # подождём, пока они пройдут — защёлка ставится только
                # после РЕАЛЬНОГО показа умиления, иначе оно терялось
                if self.face_priority <= P['loved']:
                    self.set_face('loved', 4.0)
                    self.events.append(('hearts',))
                    self.loved_fired = True
        else:
            self.hover_time = 0.0
            self.loved_fired = False

    def dropped(self):
        self.set_face('surprised', 2.0, force=True)
        self.do(A_JUMP)
        self.events.append(('drop',))

    def falling(self):
        """Начало падения на опору после переноса: удивлённая мордочка
        и «воздушная» поза, пока app не вызовет landed()."""
        self.set_face('surprised', 99.0, force=True)
        self.do(A_FALL, 9999, force=True)

    def landed(self):
        """Долетела до опоры (край окна / панель задач): радостный прыжок."""
        self.face_priority = 0
        self.set_face('happy', 2.5)
        self.do(A_JUMP)
        self.events.append(('drop',))

    def grabbed(self):
        self.set_face('surprised', 99.0, force=True)
        self.do(A_GRABBED)

    def released_drag(self):
        self.face_priority = 0
        self.dropped()
