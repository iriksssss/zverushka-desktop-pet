# -*- mode: python ; coding: utf-8 -*-
"""Сборка Zverushka.exe (PyInstaller).

Запуск:  python -m PyInstaller Zverushka.spec
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(SPEC))

# PySide6/PIL/numpy стоят в C:\\pylib — делаем доступными на всём пути сборки
sys.path.insert(0, r'C:\pylib')
sys.path.insert(0, HERE)

a = Analysis(
    [os.path.join(HERE, 'app.py')],
    pathex=[HERE, r'C:\pylib'],
    binaries=[],
    datas=[
        (os.path.join(HERE, 'assets', 'sprites'), os.path.join('assets', 'sprites')),
        (os.path.join(HERE, 'assets', 'sounds'), os.path.join('assets', 'sounds')),
    ],
    hiddenimports=['PySide6.QtMultimedia', 'numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pandas', 'scipy'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ZverushkaDbg',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(HERE, 'assets', 'sprites', 'hamster', 'icon.ico'),
)
