@echo off
setlocal enabledelayedexpansion
title Talkshow Person Video Trimmer - Antigravity

echo Checking system requirements...

:: 1. Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not found in system PATH.
    echo Please install Python 3.12 (64-bit) and add it to PATH.
    pause
    exit /b 1
)

:: 2. Check FFmpeg installation
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] FFmpeg was not found in your system PATH.
    echo CPU fallback mode will be used. Precise trimming and GPU-accelerated decoding require FFmpeg.
    echo.
)

:: 3. Setup Virtual Environment
if not exist ".venv" (
    echo Creating Python virtual environment (.venv)...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: 4. Verify/Install Python dependencies
echo Verifying Python dependencies...
python -c "import PySide6, cv2, numpy, onnxruntime" >nul 2>nul
if %errorlevel% neq 0 (
    echo Dependencies are missing or incomplete. Installing from requirements.txt...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
) else (
    echo All dependencies are satisfied.
)

:: 5. Start the Application
echo Starting Talkshow Person Video Trimmer...
python main.py

endlocal
