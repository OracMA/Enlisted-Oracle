@echo off
chcp 65001 >nul
title Enlisted Oracle - Установка
color 0B

echo ============================================
echo   Enlisted Oracle — Установка
echo ============================================
echo.

REM --- 1. Проверка Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в PATH.
    echo.
    echo Скачай Python 3.10+ отсюда: https://www.python.org/downloads/
    echo ВАЖНО: при установке поставь галочку "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [OK] Python найден: %PYVER%
echo.

REM --- 2. Проверка requirements.txt ---
if not exist requirements.txt (
    echo [ОШИБКА] Файл requirements.txt не найден рядом с install.bat.
    pause
    exit /b 1
)

REM --- 3. Установка зависимостей ---
echo [1/2] Устанавливаю зависимости из requirements.txt...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось установить зависимости.
    echo Проверь интернет-соединение и попробуй снова.
    pause
    exit /b 1
)

REM --- 4. Проверка ключевых модулей ---
echo.
echo [2/2] Проверяю установленные модули...
python -c "import PyQt6, PIL, rapidfuzz, numpy, psutil, chrome_lens_py" 2>nul
if errorlevel 1 (
    echo [ВНИМАНИЕ] Некоторые модули не установились.
    echo Попробуй запустить install.bat ещё раз.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   ✅ Установка завершена успешно!
echo ============================================
echo.
echo Теперь запусти run.bat
echo.
pause