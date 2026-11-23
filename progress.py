# -*- coding: utf-8 -*-
"""Прогресс зверушки: опыт, уровни, титулы, достижения, стрик дней.

Всё состояние — в одном dict (хранится в settings.json, секция "progress").
Модуль не знает о Qt: приложение кормит его событиями (клик, обнимашки,
пройденный путь, аптайм), а тот возвращает список произошедших событий
('level_up', ('achievement', key), ...), которые приложение показывает.

Экономика опыта (в час активного общения выходит ~150-250 XP):
  клик +2 (анти-фарм: не больше 30 XP за 10 минут кликами),
  обнимашки (ховер >3с) +5, двойной клик +3,
  облачко-фраза +10, «подбодри меня» +4,
  каждые 5 минут аптайма +2, фокус 25 минут без кликов +15,
  каждые 20 000 px пройденного пути +1.
"""
import datetime

# порог уровня L (L>=1): столько ВСЕГО XP нужно для уровня L
# 1:0 2:50 3:150 4:300 5:500 6:750 7:1050 8:1400 9:1800 10:2250 ...
def xp_total_for_level(level):
    return 25 * (level - 1) * level


TITLES = [  # (мин. уровень, титул)
    (15, 'Легенда рабочего стола'),
    (12, 'Хранитель стола'),
    (9, 'Напарник'),
    (6, 'Компаньон'),
    (4, 'Дружок'),
    (2, 'Знакомец'),
    (1, 'Новичок'),
]

ACHIEVEMENTS = {  # ключ -> (название, описание)
    'first_click': ('Первый контакт', 'Кликнуть зверушку впервые'),
    'clicks_100': ('100 кликов дружбы', 'Накопить 100 кликов'),
    'clicks_1000': ('1000 кликов — уже традиция', 'Накопить 1000 кликов'),
    'loves_10': ('10 обнимашек', '10 раз довести зверушку до мимими'),
    'phrases_10': ('10 тёплых слов', 'Увидеть 10 облачков с фразами'),
    'walk_100k': ('Прогулка в 100 000 пикселей', 'Суммарный путь лапами'),
    'walk_1m': ('Марафон лапами', '1 000 000 пикселей пути'),
    'zzz_5': ('Сторож снов', '5 раз застать зверушку спящей'),
    'days_3': ('Три дня вместе', 'Стрик 3 дня подряд'),
    'days_7': ('Неделя вместе', 'Стрик 7 дней подряд'),
    'days_30': ('Месяц дружбы', 'Стрик 30 дней подряд'),
    'all_pets': ('Знакомство со всеми', 'Побывать каждой зверушкой'),
    'level_5': ('Растём!', 'Достичь 5 уровня'),
    'level_10': ('Двузначная цифра', 'Достичь 10 уровня'),
    'game_first': ('Первая догонялка!', 'Сыграть в догонялки впервые'),
    'catch_5': ('5 попаданий за игру', 'Поймать зверушку 5 раз за одну игру'),
    'catch_10': ('10 попаданий за игру', 'Поймать зверушку 10 раз за одну игру'),
    'catch_15': ('15 попаданий за игру', 'Поймать зверушку 15 раз за одну игру'),
    'games_5': ('Завсегдатай догонялок', 'Сыграть 5 игр в догонялки'),
    'games_20': ('20 догонялок', 'Сыграть 20 игр в догонялки'),
    'feed_first': ('Первое лакомство', 'Сыграть в лакомства впервые'),
    'feed_8': ('Сладкоежка', 'Съесть 8 лакомств за одну игру'),
    'feed_30': ('Милый обжора', 'Съесть 30 лакомств суммарно'),
    'bub_first': ('Первый пузырёк', 'Сыграть в пузырьки впервые'),
    'bub_15': ('Ловец пузырей', 'Лопнуть 15 пузырьков за одну игру'),
    'bub_60': ('Мыльная опера', 'Лопнуть 60 пузырьков суммарно'),
}

DEFAULTS = {
    'xp': 0,
    'clicks': 0, 'loves': 0, 'phrases': 0, 'zzz_seen': 0,
    'walk_px': 0.0,
    'streak': 0, 'last_day': None,
    'pets_seen': [],
    'achievements': {},          # key -> дата ISO
    'games': 0,                  # сыграно догонялок
    'best_score': 0,             # рекорд попаданий за игру
    'catches_total': 0,          # всего попаданий
    'feed_games': 0,             # сыграно в «Лакомства»
    'feed_best': 0,              # рекорд съеденного за игру
    'feed_total': 0,             # всего съедено лакомств
    'bub_games': 0,              # сыграно в «Пузырьки»
    'bub_best': 0,               # рекорд лопнутых за игру
    'bub_total': 0,              # всего лопнуто пузырьков
    '_click_xp_win': [],         # метки клик-XP за 10 минут (анти-фарм)
    '_uptime_acc': 0.0,          # сек до следующих +2 за аптайм
    '_walk_acc': 0.0,            # px до следующего +1 за путь
    '_focus_done': False,        # фокус-бонус уже выдан (до след. клика)
}

CLICK_XP_CAP = 30          # XP максимум за 10 минут кликами
CLICK_XP_WINDOW = 600.0    # сек
FOCUS_SECS = 1500.0        # 25 минут без кликов = фокус-бонус


class Progress:
    def __init__(self, data=None):
        self.d = dict(DEFAULTS)
        if data:
            self.d.update({k: v for k, v in data.items() if k in DEFAULTS})

    # ---------- уровни ----------
    def level(self):
        xp = self.d['xp']
        l = 1
        while xp >= xp_total_for_level(l + 1):
            l += 1
        return l

    def level_progress(self):
        """(текущий уровень, XP внутри уровня, XP до следующего)."""
        l = self.level()
        base = xp_total_for_level(l)
        nxt = xp_total_for_level(l + 1)
        return l, self.d['xp'] - base, nxt - base

    def title(self):
        l = self.level()
        for min_l, t in TITLES:
            if l >= min_l:
                return t
        return TITLES[-1][1]

    # ---------- ядро ----------
    @staticmethod
    def _level_of(xp):
        l = 1
        while xp >= xp_total_for_level(l + 1):
            l += 1
        return l

    def add_xp(self, amount, now):
        """Начислить XP. Возвращает список событий ('level_up', new_level)."""
        old_level = self._level_of(self.d['xp'])
        self.d['xp'] += amount
        events = []
        if self.level() > old_level:
            events.append(('level_up', self.level()))
            for key in ('level_5', 'level_10'):
                if self.level() >= int(key.split('_')[1]):
                    events += self._unlock(key, now)
        return events

    def _unlock(self, key, now):
        if key in self.d['achievements']:
            return []
        self.d['achievements'][key] = datetime.date.today().isoformat()
        return [('achievement', key)]

    def _click_xp_allowed(self, now):
        win = [t for t in self.d['_click_xp_win'] if now - t < CLICK_XP_WINDOW]
        self.d['_click_xp_win'] = win
        return sum(win) < CLICK_XP_CAP

    # ---------- события от приложения ----------
    def on_click(self, now, double=False):
        self.d['clicks'] += 1
        self.d['_focus_done'] = False
        events = []
        if self._click_xp_allowed(now):
            xp = 3 if double else 2
            self.d['_click_xp_win'] = self.d['_click_xp_win'] + [xp]
            events += self.add_xp(xp, now)
        if self.d['clicks'] == 1:
            events += self._unlock('first_click', now)
        if self.d['clicks'] >= 100:
            events += self._unlock('clicks_100', now)
        if self.d['clicks'] >= 1000:
            events += self._unlock('clicks_1000', now)
        return events

    def on_loved(self, now):
        self.d['loves'] += 1
        events = self.add_xp(5, now)
        if self.d['loves'] >= 10:
            events += self._unlock('loves_10', now)
        return events

    def on_phrase(self, now, manual=False):
        self.d['phrases'] += 1
        events = self.add_xp(4 if manual else 10, now)
        if self.d['phrases'] >= 10:
            events += self._unlock('phrases_10', now)
        return events

    def on_zzz(self, now):
        self.d['zzz_seen'] += 1
        if self.d['zzz_seen'] >= 5:
            return self._unlock('zzz_5', now)
        return []

    def on_walk(self, px, now):
        self.d['walk_px'] += px
        self.d['_walk_acc'] += px
        events = []
        while self.d['_walk_acc'] >= 20000:
            self.d['_walk_acc'] -= 20000
            events += self.add_xp(1, now)
        if self.d['walk_px'] >= 100000:
            events += self._unlock('walk_100k', now)
        if self.d['walk_px'] >= 1000000:
            events += self._unlock('walk_1m', now)
        return events

    def on_tick(self, dt, idle_secs, now):
        """Аптайм (+2 каждые 5 мин) и фокус-бонус (+15 за 25 мин тишины)."""
        events = []
        self.d['_uptime_acc'] += dt
        while self.d['_uptime_acc'] >= 300:
            self.d['_uptime_acc'] -= 300
            events += self.add_xp(2, now)
        if idle_secs >= FOCUS_SECS and not self.d['_focus_done']:
            self.d['_focus_done'] = True
            events += self.add_xp(15, now)
            events.append(('focus_bonus',))
        return events

    def on_new_day(self, today=None):
        """Стрик дней. Возвращает события достижений."""
        today = today or datetime.date.today().isoformat()
        if self.d['last_day'] == today:
            return []
        yesterday = (datetime.date.today() -
                     datetime.timedelta(days=1)).isoformat()
        self.d['streak'] = self.d['streak'] + 1 if self.d['last_day'] == yesterday else 1
        self.d['last_day'] = today
        events = []
        for key, need in (('days_3', 3), ('days_7', 7), ('days_30', 30)):
            if self.d['streak'] >= need:
                events += self._unlock(key, today)
        return events

    def on_pet_seen(self, pet, all_pets, now):
        seen = set(self.d['pets_seen'])
        seen.add(pet)
        self.d['pets_seen'] = sorted(seen)
        if set(all_pets) <= seen:
            return self._unlock('all_pets', now)
        return []

    def on_game_end(self, score, now, kind='tag'):
        """Итог мини-игры: счётчики, рекорд, XP (2 за очко, учитывается
        максимум 15 очков) и ачивки соответствующей игры."""
        events = self.add_xp(min(score, 15) * 2, now)
        if kind == 'tag':
            self.d['games'] += 1
            self.d['catches_total'] += score
            self.d['best_score'] = max(self.d['best_score'], score)
            if self.d['games'] == 1:
                events += self._unlock('game_first', now)
            if self.d['games'] >= 5:
                events += self._unlock('games_5', now)
            if self.d['games'] >= 20:
                events += self._unlock('games_20', now)
            for key, need in (('catch_5', 5), ('catch_10', 10),
                              ('catch_15', 15)):
                if score >= need:
                    events += self._unlock(key, now)
        elif kind == 'feed':
            self.d['feed_games'] += 1
            self.d['feed_total'] += score
            self.d['feed_best'] = max(self.d['feed_best'], score)
            if self.d['feed_games'] == 1:
                events += self._unlock('feed_first', now)
            if score >= 8:
                events += self._unlock('feed_8', now)
            if self.d['feed_total'] >= 30:
                events += self._unlock('feed_30', now)
        elif kind == 'bub':
            self.d['bub_games'] += 1
            self.d['bub_total'] += score
            self.d['bub_best'] = max(self.d['bub_best'], score)
            if self.d['bub_games'] == 1:
                events += self._unlock('bub_first', now)
            if score >= 15:
                events += self._unlock('bub_15', now)
            if self.d['bub_total'] >= 60:
                events += self._unlock('bub_60', now)
        return events

