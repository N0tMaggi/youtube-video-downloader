@echo off
REM Install dependencies and run downloader

REM Ensure the script is running with administrative privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process '%~f0' -Verb runAs"
    exit /b
)

REM Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.x and rerun this script.
    pause
    exit /b 1
)

REM Install required Python packages (force latest to avoid YouTube signature breaks)
python -m pip install --upgrade -r requirements.txt

REM Check for FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo FFmpeg not found. Attempting installation via winget...
    winget install ffmpeg
)

REM Start the downloader
python downloader.py

