@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title VIGIL Studio v3 - Genuine Large Research Environment Installer
color 0B
echo ================================================================
echo  VIGIL Studio v3 - advanced biomedical AI research environment
echo ================================================================
echo.
echo RESEARCH USE ONLY. NOT a medical device or diagnostic system.
echo Requires internet, Python 3.11 x64, and recommended 50+ GB free for multimodal collection.
echo Real public data will come from PhysioNet; foundation AI from Hugging Face.
echo This installer is not an offline 10 GB archive.
echo.
where py >nul 2>nul
if errorlevel 1 (
 echo Python launcher not found. Install Python 3.11 x64 from python.org.
 pause
 exit /b 1
)
py -3.11 -c "import platform; assert platform.architecture()[0]=='64bit'" >nul 2>nul
if errorlevel 1 (
 echo Python 3.11 x64 is required for the optional MOMENT AI engine.
 pause
 exit /b 1
)
set "DEFAULTWS=%USERPROFILE%\VIGILStudio_Workspace"
echo Choose a drive with enough storage. For example: D:\VIGIL_Research_Data
set /p "USERWS=Research workspace path [default: %DEFAULTWS%]: "
if not defined USERWS set "USERWS=%DEFAULTWS%"
set "VIGIL_STUDIO_WORKSPACE=%USERWS%"
if not exist "%VIGIL_STUDIO_WORKSPACE%" mkdir "%VIGIL_STUDIO_WORKSPACE%"
if not exist "%VIGIL_STUDIO_WORKSPACE%" (
 echo ERROR: Could not create research workspace folder.
 pause
 exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
 py -3.11 -m venv .venv
 if errorlevel 1 goto :fail
)
call ".venv\Scripts\activate.bat"
python -c "import os; from pathlib import Path; Path('VIGIL_WORKSPACE_PATH.txt').write_text(os.environ['VIGIL_STUDIO_WORKSPACE'],encoding='utf-8')"
if errorlevel 1 goto :fail
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -r requirements.txt -r requirements-ai.txt "pytest>=8,<10"
if errorlevel 1 goto :fail
python -m pytest -q tests
if errorlevel 1 (
 echo ERROR: Source tests failed. Refusing to continue.
 pause
 exit /b 1
)
echo.
python -m vigil_studio.environment --workspace "%VIGIL_STUDIO_WORKSPACE%" plan --preset research-multimodal-30gb
if errorlevel 1 goto :fail
echo.
echo Official public datasets (source licensing must be reviewed):
echo  MIT-BIH, AFDB, NSRDB, PTB-XL, Large ECG, CINC2020, EEGMMI, Sleep-EDF, BIDMC, sEMG.
echo  See https://physionet.org/ for dataset licenses and source citations.
echo  MOMENT-1-large model: https://huggingface.co/AutonLab/MOMENT-1-large
set /p "CONFIRM=After reading those licenses, type DOWNLOAD to authorize downloads: "
if /I not "%CONFIRM%"=="DOWNLOAD" (
 echo No downloads performed. You can still run START_WINDOWS.bat.
 pause
 exit /b 0
)
echo.
echo Downloading datasets from their official sites. Large downloads may fail on unstable networks.
python -m vigil_studio.environment --workspace "%VIGIL_STUDIO_WORKSPACE%" install-preset --preset research-multimodal-30gb --accept-licenses --continue-on-error
if errorlevel 1 echo WARNING: One or more datasets did not install. See output; rerun to retry.
echo.
echo Downloading and verifying the optional MOMENT foundation checkpoint...
python -m vigil_studio.ai --workspace "%VIGIL_STUDIO_WORKSPACE%" download-moment --accept-license
if errorlevel 1 echo WARNING: MOMENT not installed or did not pass integrity verification. Check network/model package.
python -m vigil_studio.environment --workspace "%VIGIL_STUDIO_WORKSPACE%" snapshot --out "%VIGIL_STUDIO_WORKSPACE%\environment_snapshot.json"
if errorlevel 1 goto :fail
echo.
echo ================================================================
echo Setup complete or partially complete. Inspect environment_snapshot.json.
echo Some sources may fail to download; do not assume completion.
echo ================================================================
echo.
python launch.py "%VIGIL_STUDIO_WORKSPACE%"
if errorlevel 1 goto :fail
exit /b 0
:fail
echo.
echo ERROR: Setup failed. Inspect the printed error. No clinical claims made.
pause
exit /b 1
