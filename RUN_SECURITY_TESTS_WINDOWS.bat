@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run START_WINDOWS.bat once to install base dependencies.
  pause
  exit /b 1
)
set "PY=.venv\Scripts\python.exe"
%PY% -m pip install -r requirements-security.txt "pytest>=8,<10"
if errorlevel 1 goto :fail
%PY% -m pytest -q tests\test_safety_engineering_v47.py
if errorlevel 1 goto :fail
echo Research security engineering checks passed. CLINICAL RELEASE IS STILL BLOCKED.
pause
exit /b 0
:fail
echo Security engineering checks FAILED. Do not use for patient care.
pause
exit /b 1
