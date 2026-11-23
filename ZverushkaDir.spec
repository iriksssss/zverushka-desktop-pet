# -*- mode: python ; coding: utf-8 -*-
"""Сборка ONEDIR-раздачи Zverushka (PyInstaller).

В отличие от Zverushka.spec (onefile), здесь приложение — ПАПКА:
dist\\Zverushka\\Zverushka.exe + _internal\\ (библиотеки).
Папка assets (спрайты, звуки, phrases.json) НЕ упаковывается, а
копируется рядом с exe скриптом _rebuild.bat — так phrases.json и
спрайты остаются доступными для правки пользователем.

Запуск:  python -m PyInstaller ZverushkaDir.spec --noconfirm --clean
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
    datas=[],
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
    [],
    exclude_binaries=True,
    name='Zverushka',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(HERE, 'assets', 'sprites', 'hamster', 'icon.ico'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Zverushka',
)
