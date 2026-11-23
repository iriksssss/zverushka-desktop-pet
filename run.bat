@echo off
rem Зверушка на рабочем столе. Запуск: двойной клик.
cd /d "%~dp0"
if exist dist\Zverushka\Zverushka.exe (
    start "" dist\Zverushka\Zverushka.exe
) else if exist dist\Zverushka.exe (
    start "" dist\Zverushka.exe
) else (
    python app.py
)
