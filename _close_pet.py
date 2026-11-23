# -*- coding: utf-8 -*-
"""Корректно закрыть работающую Зверушку: WM_CLOSE её окну (равносильно
«Выход» из трея — с сохранением настроек). Работает, когда taskkill
бессилен («Отказано в доступе» из неинтерактивного shell)."""
import ctypes
import ctypes.wintypes as w
import subprocess
import sys
import time

user32 = ctypes.windll.user32
WM_CLOSE = 0x0010
WM_QUIT = 0x0012


def _all_threads(pids):
    """Все потоки указанных процессов (Toolhelp32Snapshot)."""
    k32 = ctypes.windll.kernel32
    TH32CS_SNAPTHREAD = 0x00000004

    class THREADENTRY32(ctypes.Structure):
        _fields_ = [('dwSize', w.DWORD), ('cntUsage', w.DWORD),
                    ('th32ThreadID', w.DWORD), ('th32OwnerProcessID', w.DWORD),
                    ('tpBasePri', w.LONG), ('tpDeltaPri', w.LONG),
                    ('dwFlags', w.DWORD)]

    out = set()
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if not snap or snap == ctypes.c_void_p(-1).value:
        return out
    te = THREADENTRY32()
    te.dwSize = ctypes.sizeof(THREADENTRY32)
    ok = k32.Thread32First(snap, ctypes.byref(te))
    while ok:
        if te.th32OwnerProcessID in pids:
            out.add(te.th32ThreadID)
        ok = k32.Thread32Next(snap, ctypes.byref(te))
    k32.CloseHandle(snap)
    return out


def pet_pids(exe_name='Zverushka.exe'):
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ' + exe_name,
                        '/FO', 'CSV', '/NH'], capture_output=True, text=True)
    pids = set()
    for line in r.stdout.splitlines():
        if exe_name[:-4] in line:
            try:
                pids.add(int(line.split(',')[1].strip().strip('"')))
            except (ValueError, IndexError):
                pass
    return pids


def close_pet(exe_name='Zverushka.exe', wait=5.0):
    pids = pet_pids(exe_name)
    if not pids:
        print('не запущена')
        return True
    sent = 0

    # Главное окно зверушки — owned (Qt Tool), EnumWindows его НЕ видит.
    # Идём через EnumChildWindows рабочего стола: главному окну шлём
    # WM_CLOSE (прячет окно), а GUI-потоку — WM_QUIT (завершает процесс,
    # равносильно «Выход» из трея с сохранением настроек).
    threads = set()

    @ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    def cb(hwnd, lp):
        nonlocal sent
        pid = w.DWORD()
        tid = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            threads.add(tid)
            cls = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, cls, 64)
            if cls.value.startswith('Qt6') and 'QWindow' in cls.value:
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                sent += 1
        return True

    user32.EnumChildWindows(user32.GetDesktopWindow(), cb, 0)
    # Потоки без окон (главный поток «безголового» экземпляра, у которого
    # окно уже закрыто) ищем через Toolhelp32 — иначе WM_QUIT до них
    # не доходит и процесс остаётся жить.
    threads |= _all_threads(pids)
    for tid in threads:
        user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)
    print('WM_CLOSE окнам:', sent, ' WM_QUIT потокам:', len(threads))
    t = time.time()
    while time.time() - t < wait:
        if not pet_pids(exe_name):
            print('закрыта')
            return True
        time.sleep(0.3)
    print('НЕ закрылась за', wait, 'с; остались PID:', pet_pids(exe_name))
    return False


if __name__ == '__main__':
    exe = sys.argv[1] if len(sys.argv) > 1 else 'Zverushka.exe'
    sys.exit(0 if close_pet(exe) else 1)
