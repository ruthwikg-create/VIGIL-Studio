@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Install dependencies first: run START_WINDOWS.bat or INSTALL_FULL_RESEARCH_WINDOWS.bat.
 pause
 exit /b 1
)
.venv\Scripts\python.exe launch.py
if errorlevel 1 pause
