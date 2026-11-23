# -*- coding: utf-8 -*-
"""Проверить, что EXE пересобраны ПОСЛЕ правки pet.py."""
import os

base = os.path.dirname(os.path.abspath(__file__))
p = os.path.getmtime(os.path.join(base, 'pet.py'))
e = os.path.getmtime(os.path.join(base, 'dist', 'Zverushka.exe'))
d = os.path.getmtime(os.path.join(base, 'dist', 'ZverushkaDbg.exe'))
import datetime
f = lambda t: datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
print('pet.py         :', f(p))
print('Zverushka.exe  :', f(e))
print('ZverushkaDbg   :', f(d))
print('EXE newer than pet.py:', (e > p) and (d > p))
