@echo off
setlocal
cd /d "%~dp0"
echo VIGIL Studio v4.8 - Professional MIT-BIH Reference Report
echo.
echo Enter the full path to 100_reference_annotations.csv (not the raw 100.atr file).
set /p "SOURCE=Annotation CSV path: "
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\reference_annotation_report.py "%SOURCE%"
) else (
  py -3.12 scripts\reference_annotation_report.py "%SOURCE%"
)
echo.
pause
