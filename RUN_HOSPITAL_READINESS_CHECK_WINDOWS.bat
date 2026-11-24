@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo The research environment is not installed. Run START_WINDOWS.bat first.
  pause
  exit /b 1
)
set /p WORKSPACE=Workspace path [default: %USERPROFILE%\VIGILStudio_Workspace]: 
if "%WORKSPACE%"=="" set "WORKSPACE=%USERPROFILE%\VIGILStudio_Workspace"
set "DEST=readiness_runs\CHECK_%RANDOM%_%RANDOM%"
"%PYTHON%" scripts\hospital_readiness_check.py --workspace "%WORKSPACE%" --output "%DEST%"
if errorlevel 1 echo Engineering checks require review; medical release remains BLOCKED.
echo Reports saved under %DEST%
pause
