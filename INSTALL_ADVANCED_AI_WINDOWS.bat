@echo off
setlocal
cd /d "%~dp0"
title VIGIL Studio - Advanced AI Research Setup
where py >nul 2>nul
if errorlevel 1 (
 echo Python 3.11 is required for the optional MOMENT engine.
 pause
 exit /b 1
)
py -3.11 -c "import sys" >nul 2>nul
if errorlevel 1 (
 echo Install Python 3.11 x64 from python.org for the pretrained foundation model.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 py -3.11 -m venv .venv
 if errorlevel 1 exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-ai.txt
if errorlevel 1 (
 echo Required AI dependencies could not be installed. Check network and Python 3.11.
 pause
 exit /b 1
)
python -m vigil_studio.ai model-status
if errorlevel 1 exit /b 1
echo.
echo AI libraries installed. The 1.39 GB pretrained MOMENT model is OPTIONAL.
echo To install the model after checking its MIT license and data handling:
echo     python -m vigil_studio.ai download-moment --accept-license
echo.
echo Model URL: https://huggingface.co/AutonLab/MOMENT-1-large
pause
