@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo No project .venv found. Run START_WINDOWS.bat once to set up dependencies.
  exit /b 1
)
echo.
echo VIGIL ECG LOCATION BENCHMARK - RESEARCH ONLY, NOT FOR PATIENT CARE
set /p DATA_DIR=Enter extracted MIT-BIH directory [D:\Biomedical_Datasets\MITBIH]: 
if not defined DATA_DIR set "DATA_DIR=D:\Biomedical_Datasets\MITBIH"
set /p MODE=Run [1] Record 100 only, or [2] all 48 records? [1]: 
if not defined MODE set "MODE=1"
for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set "DAY=%%a_%%b_%%c"
set "OUTPUT_DIR=%USERPROFILE%\Documents\VIGIL_Research_Benchmark_%RANDOM%_%RANDOM%"
if "%MODE%"=="2" (
  ".venv\Scripts\python.exe" scripts\clinical_readiness_benchmark.py --dataset "%DATA_DIR%" --out "%OUTPUT_DIR%"
) else (
  ".venv\Scripts\python.exe" scripts\clinical_readiness_benchmark.py --dataset "%DATA_DIR%" --out "%OUTPUT_DIR%" --record 100
)
set "RESULT=%ERRORLEVEL%"
echo.
echo See report folder: "%OUTPUT_DIR%"
if not "%RESULT%"=="0" echo The run was incomplete or failed; inspect REPORT.md and results.json if created.
echo.
pause
exit /b %RESULT%
