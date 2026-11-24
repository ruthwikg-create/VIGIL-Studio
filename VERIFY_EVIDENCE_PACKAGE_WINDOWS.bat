@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Drag your exported VIGIL evidence ZIP onto this .bat file, or enter the full path below.
  set /p "PACKAGE=Evidence ZIP: "
) else (
  set "PACKAGE=%~1"
)
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\verify_evidence_package.py "%PACKAGE%"
) else (
  py -3.12 scripts\verify_evidence_package.py "%PACKAGE%"
)
echo.
pause
