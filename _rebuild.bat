@echo off
rem Пересборка ONEDIR-раздачи: dist\Zverushka\Zverushka.exe + _internal\
rem + assets рядом (спрайты/phrases.json доступны для правки).
rem ВАЖНО: закройте работающую зверушку перед сборкой (_close_pet.py).
cd /d "%~dp0"
rem settings.json (прогресс!) выносим на время сборки: PyInstaller
rem с --clean пересоздаёт папку dist\Zverushka целиком
set BK=%TEMP%\zverushka_settings_backup.json
if exist dist\Zverushka\settings.json copy /Y dist\Zverushka\settings.json "%BK%" >nul
rem Python с PyInstaller: предпочитаем Store-Python пользователя
rem (в нём стоят PySide6/PyInstaller из C:\pylib), иначе python из PATH
set PY=python
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
"%PY%" -m PyInstaller ZverushkaDir.spec --noconfirm --clean || goto :err
rem assets кладём РЯДОМ с exe (не внутрь _internal) — редактируемые данные
xcopy /E /I /Y assets dist\Zverushka\assets >nul || goto :err
rem возвращаем прогресс на место (или переносим со старой onefile-раздачи)
if exist "%BK%" (
    copy /Y "%BK%" dist\Zverushka\settings.json >nul
) else if exist dist\settings.json (
    copy /Y dist\settings.json dist\Zverushka\settings.json >nul
)
echo BUILD_DONE
goto :eof
:err
echo BUILD_FAILED
exit /b 1
