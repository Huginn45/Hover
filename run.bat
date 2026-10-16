@echo off
chcp 65001 >nul
title Hover - Desktop Screenshot & Pin Utility
cd /d "%~dp0"

echo ===================================================
echo   Starting Hover...
echo ===================================================

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe main.py
) else (
    python main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Hover stopped with error code %ERRORLEVEL%.
    pause
)
