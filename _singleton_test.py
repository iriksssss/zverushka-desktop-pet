# -*- coding: utf-8 -*-
"""Тест single-instance: два процесса, второй должен увидеть, что первый жив."""
import subprocess
import sys
import time

HERE = r'G:\desktop_pet'
HOLD = (
    'import sys; sys.path.insert(0, %r); import app; '
    'assert not app._already_running(), "1-й запуск: думает, что уже идёт"; '
    'print("FIRST: not running (ok)"); '
    'import time; time.sleep(10)' % HERE
)
SECOND = (
    'import sys; sys.path.insert(0, %r); import app; '
    'print("SECOND: already_running =", app._already_running())' % HERE
)

holder = subprocess.Popen([sys.executable, '-c', HOLD])
time.sleep(2.5)
r = subprocess.run([sys.executable, '-c', SECOND], capture_output=True, text=True)
holder.terminate()
print(r.stdout.strip())
assert 'already_running = True' in r.stdout, 'FAIL: второй не увидел первый'
print('SINGLE-INSTANCE TEST: OK')
