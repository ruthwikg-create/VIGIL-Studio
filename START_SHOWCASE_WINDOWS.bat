@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo Python Launcher missing. Install Python 3.12 x64.
 pause
 exit /b 1
)
set "PYSEL="
for %%V in (3.12 3.11 3.13) do (
 if not defined PYSEL (
  py -%%V -c "import sys" >nul 2>nul && set "PYSEL=-%%V"
 )
)
if not defined PYSEL (
 echo Python 3.11, 3.12 or 3.13 is required.
 pause
 exit /b 1
)
if not exist .venv\Scripts\python.exe (
 py %PYSEL% -m venv .venv
 if errorlevel 1 (pause & exit /b 1)
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed & pause & exit /b 1)
.venv\Scripts\python.exe launch_showcase.py
if errorlevel 1 pause
