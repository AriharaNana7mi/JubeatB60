@echo off
chcp 65001 >nul
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs -WorkingDirectory '%~dp0'"
    exit
)
cd /d "%~dp0"

echo ========================================
echo   Jubeat B60
echo ========================================
echo.

if not exist ".static\jubeat\bg_icon.png" (
    echo 首次使用，解压素材...
    python _assets.py
    echo.
)

echo [1/3] get_token...
python get_token.py
if %errorlevel% neq 0 (
    echo get_token failed
    pause
    exit /b 1
)
if not exist token.txt (
    echo token.txt not found
    pause
    exit /b 1
)

echo.
echo [2/3] crawl_scores...
python crawl_scores.py
if %errorlevel% neq 0 (
    echo crawl_scores failed
    pause
    exit /b 1
)

echo.
echo [3/3] generate...
python generate.py

pause
