@echo off
rem Подмена раздачи после закрытия старой (elevated) зверушки:
rem удаляет старую папку dist\Zverushka и ставит свежую из dist_new.
rem Запускать ПОСЛЕ того, как старая зверушка закрыта (трей -> Выход).
cd /d "%~dp0"
tasklist | findstr /I "Zverushka.exe" >nul && (
    echo Zverushka.exe ещё работает - сначала закройте её (трей -^> Выход)
    exit /b 1
)
rmdir /S /Q dist\Zverushka 2>nul
del /Q dist\_Zverushka_prev.exe 2>nul
move dist_new\Zverushka dist\Zverushka >nul || (echo SWAP_FAILED & exit /b 1)
rmdir /S /Q dist_new 2>nul
echo SWAP_DONE
start "" dist\Zverushka\Zverushka.exe
