@echo off
chcp 65001 >nul
title Enlisted Oracle
cd /d "%~dp0"

REM --- проверка, что установка была ---
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Зависимости не установлены.
    echo Сначала запусти install.bat
    echo.
    pause
    exit /b 1
)

REM --- запуск ---
python gui.py

REM --- если упало, оставить окно открытым ---
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Программа завершилась с ошибкой. Смотри лог выше.
    pause
)