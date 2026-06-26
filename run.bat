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

:: 2. Setup Virtual Environment
if not exist ".venv" (
    echo Creating Python virtual environment (.venv)...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Check and Setup FFmpeg
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    if exist ".venv\Scripts\ffmpeg.exe" (
        echo [INFO] Local FFmpeg detected in virtual environment.
    ) else (
        echo [INFO] FFmpeg not found. Automatically downloading FFmpeg...
        powershell -Command "$zipUrl = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'; $zipPath = 'ffmpeg.zip'; $extractPath = 'ffmpeg_temp'; Write-Host 'Downloading FFmpeg essentials zip (approx. 90MB)...'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath; Write-Host 'Extracting...'; Expand-Archive -Path $zipPath -DestinationPath $extractPath; Write-Host 'Installing to virtual environment...'; $ffmpegExe = Get-ChildItem -Path $extractPath -Filter 'ffmpeg.exe' -Recurse | Select-Object -First 1; $ffprobeExe = Get-ChildItem -Path $extractPath -Filter 'ffprobe.exe' -Recurse | Select-Object -First 1; if ($ffmpegExe) { Copy-Item $ffmpegExe.FullName -Destination '.venv\Scripts' -Force }; if ($ffprobeExe) { Copy-Item $ffprobeExe.FullName -Destination '.venv\Scripts' -Force }; Write-Host 'Cleaning up...'; Remove-Item -Path $zipPath -Force; Remove-Item -Path $extractPath -Recurse -Force; Write-Host 'FFmpeg installed successfully!'"
        if !errorlevel! neq 0 (
            echo [WARNING] Failed to download FFmpeg automatically.
            echo CPU fallback mode will be used. Precise trimming and GPU-accelerated decoding require FFmpeg.
            echo.
        )
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
