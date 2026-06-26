@echo off
setlocal enabledelayedexpansion
title Talkshow Person Video Trimmer - Antigravity

echo Checking system requirements...

:: 1. Detect and Validate Python 3.12
set PYTHON_CMD=
py -3.12 -c "import sys" >nul 2>nul
if %errorlevel% EQU 0 (
    set PYTHON_CMD=py -3.12
) else (
    python -c "import sys; exit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
    if !errorlevel! EQU 0 (
        set PYTHON_CMD=python
    )
)

if "%PYTHON_CMD%" == "" (
    echo [ERROR] Python 3.12 was not detected as the active interpreter.
    echo This application is verified for Python 3.12 64-bit to match onnxruntime-gpu.
    echo.
    echo Checking for default Python version...
    where python >nul 2>nul
    if !errorlevel! EQU 0 (
        for /f "tokens=*" %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set CURRENT_VER=%%v
        echo Found active Python version !CURRENT_VER!.
        echo [WARNING] Running on Python !CURRENT_VER! may cause installation failures for onnxruntime-gpu==1.20.1.
        set /p CHOOSE_PROCEED="Do you want to proceed anyway? (Y/N): "
        if /i "!CHOOSE_PROCEED!" neq "Y" (
            exit /b 1
        )
        set PYTHON_CMD=python
    ) else (
        echo [ERROR] No Python installation was detected in system PATH.
        echo Please install Python 3.12 64-bit and add it to PATH.
        pause
        exit /b 1
    )
)

echo Using Python interpreter: %PYTHON_CMD%

:: 2. Setup Virtual Environment
if not exist ".venv" (
    echo Creating Python virtual environment [.venv]...
    %PYTHON_CMD% -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Check and Setup FFmpeg
where ffmpeg >nul 2>nul
if %errorlevel% EQU 0 goto FFMPEG_OK
if exist ".venv\Scripts\ffmpeg.exe" (
    echo [INFO] Local FFmpeg detected in virtual environment.
    goto FFMPEG_OK
)

echo [INFO] FFmpeg not found. Automatically downloading FFmpeg...
powershell -Command "$zipUrl = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'; $zipPath = 'ffmpeg.zip'; $extractPath = 'ffmpeg_temp'; Write-Host 'Downloading FFmpeg essentials zip [approx. 90MB]...'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath; Write-Host 'Extracting...'; Expand-Archive -Path $zipPath -DestinationPath $extractPath; Write-Host 'Installing to virtual environment...'; $ffmpegExe = Get-ChildItem -Path $extractPath -Filter 'ffmpeg.exe' -Recurse | Select-Object -First 1; $ffprobeExe = Get-ChildItem -Path $extractPath -Filter 'ffprobe.exe' -Recurse | Select-Object -First 1; if ($ffmpegExe) { Copy-Item $ffmpegExe.FullName -Destination '.venv\Scripts' -Force }; if ($ffprobeExe) { Copy-Item $ffprobeExe.FullName -Destination '.venv\Scripts' -Force }; Write-Host 'Cleaning up...'; Remove-Item -Path $zipPath -Force; Remove-Item -Path $extractPath -Recurse -Force; Write-Host 'FFmpeg installed successfully!'"
if !errorlevel! neq 0 (
    echo [WARNING] Failed to download FFmpeg automatically.
    echo CPU fallback mode will be used. Precise trimming and GPU-accelerated decoding require FFmpeg.
    echo.
)

:FFMPEG_OK

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
