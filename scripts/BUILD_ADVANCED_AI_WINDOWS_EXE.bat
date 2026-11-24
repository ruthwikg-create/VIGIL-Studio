@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
title VIGIL Studio v3 - Advanced Native AI EXE Build
where py >nul 2>nul
if errorlevel 1 (
 echo Python 3.11 x64 is required to build the AI desktop executable.
 pause
 exit /b 1
)
py -3.11 -c "import platform; assert platform.architecture()[0]=='64bit'" >nul 2>nul
if errorlevel 1 (
 echo Install Python 3.11 x64 from python.org first.
 pause
 exit /b 1
)
if not exist .venv\Scripts\python.exe py -3.11 -m venv .venv
if errorlevel 1 goto :fail
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt -r requirements-ai.txt -r requirements-build.txt
if errorlevel 1 goto :fail
python -m pytest -q tests
if errorlevel 1 goto :fail
pyinstaller --noconfirm --clean --windowed --onedir --name VIGILStudioAI ^
 --collect-all torch --collect-all safetensors --collect-all huggingface_hub --collect-all momentfm ^
 --collect-all matplotlib --collect-all mne --collect-all wfdb ^
 --collect-submodules vigil_studio --collect-submodules scipy --collect-submodules sklearn ^
 --hidden-import tkinter --hidden-import reportlab ^
 --add-data "docs;docs" --add-data "examples;examples" --add-data "vigil_studio/assets;vigil_studio/assets" ^
 --icon "vigil_studio/assets/vigil_signal_icon.ico" launch.py
if errorlevel 1 goto :fail
if not exist dist\VIGILStudioAI\VIGILStudioAI.exe goto :fail
echo.
echo Built: dist\VIGILStudioAI\VIGILStudioAI.exe
echo Keep the ENTIRE dist\VIGILStudioAI directory together.
echo Source datasets and 1.39 GB model weights are installed separately by explicit consent.
echo No Windows executable is code-signed or clinically validated by this build.
pause
exit /b 0
:fail
echo Build failed. See error output; do not distribute partial executable as verified.
pause
exit /b 1
