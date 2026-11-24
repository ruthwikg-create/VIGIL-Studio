@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo Please install Python 3.11 to 3.13 and try again.
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
 echo Install Python 3.12 64-bit from python.org; Python 3.14 alone is not supported.
 pause
 exit /b 1
)
if not exist .venv py %PYSEL% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 (
 echo Dependency installation failed.
 pause
 exit /b 1
)
python launch.py
if errorlevel 1 pause
