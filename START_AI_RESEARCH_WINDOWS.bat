@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run INSTALL_ADVANCED_AI_WINDOWS.bat first to set up AI libraries.
 pause
 exit /b 1
)
.venv\Scripts\python.exe launch.py
if errorlevel 1 pause
