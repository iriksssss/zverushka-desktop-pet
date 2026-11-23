@echo off
REM Clean shareable distribution (no user settings.json inside):
REM   dist_share\Zverushka\     copy of dist\Zverushka minus settings.json
REM   dist_share\Zverushka.zip  same folder, archived
REM RU: chistyij distributiv dlya peredachi: bez settings.json (progress
REM     poluchatelya nachnetsya s nulya, fajl sozdastsya pri pervom vyihode).
cd /d %~dp0

if not exist dist\Zverushka\Zverushka.exe (
    echo ERROR: build main dist first via _rebuild.bat
    exit /b 1
)

if exist dist_share rmdir /s /q dist_share
mkdir dist_share

echo settings.json> _share_exclude.txt
xcopy dist\Zverushka dist_share\Zverushka\ /e /i /q /exclude:_share_exclude.txt >nul
del _share_exclude.txt

powershell -NoProfile -Command "Compress-Archive -Path 'dist_share\Zverushka' -DestinationPath 'dist_share\Zverushka.zip' -Force"

echo SHARE_DONE: dist_share\Zverushka\ and dist_share\Zverushka.zip
