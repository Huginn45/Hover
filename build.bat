@echo off
chcp 65001 >nul
title Building Hover Executable
cd /d "%~dp0"

echo ===================================================
echo   Building Hover Standalone Windows Executable
echo ===================================================

if not exist "venv\Scripts\pyinstaller.exe" (
    echo PyInstaller not found in venv. Installing...
    venv\Scripts\pip install pyinstaller
)

venv\Scripts\pyinstaller --clean --noconsole --onefile --name="Hover" --icon="assets\icon.ico" --add-data="assets;assets" main.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================================
    echo   BUILD SUCCESSFUL!
    echo   Your standalone app is ready at:
    echo   dist\Hover.exe
    echo ===================================================
) else (
    echo.
    echo Build failed with error code %ERRORLEVEL%.
)
pause
