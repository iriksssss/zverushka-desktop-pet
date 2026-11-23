# -*- coding: utf-8 -*-
"""Окно-мишень в отдельном процессе. Аргумент 'max' — развёрнутое окно."""
import sys

sys.path.insert(0, r'C:\pylib')

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer

app = QApplication([])
w = QWidget()
w.setWindowTitle('DummyTarget')
if len(sys.argv) > 1 and sys.argv[1] == 'max':
    w.showMaximized()
else:
    w.setGeometry(700, 320, 900, 500)
    w.show()
QTimer.singleShot(40000, app.quit)
app.exec()
