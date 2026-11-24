@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo First install dependencies using START_WINDOWS.bat
 pause
 exit /b 1
)
set "PY=.venv\Scripts\python.exe"
%PY% -m pip install "pytest>=8,<10"
if errorlevel 1 goto :fail
set "OUTPUT=engineering_evidence\CHECK_%RANDOM%_%RANDOM%"
%PY% scripts\collect_engineering_evidence.py --output "%OUTPUT%"
if errorlevel 1 goto :fail
echo Evidence collected under %OUTPUT%. This is NOT hospital approval.
pause
exit /b 0
:fail
echo Evidence collection or verification FAILED. Clinical use is blocked.
pause
exit /b 1
