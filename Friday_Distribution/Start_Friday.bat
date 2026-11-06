@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%~dp0..\.venv312\Scripts\python.exe"

if not exist "%PYTHON%" set "PYTHON=python"

"%PYTHON%" friday_reel_hud.py

if errorlevel 1 (
    echo.
    echo Friday stopped. Check the error above.
    pause
)
