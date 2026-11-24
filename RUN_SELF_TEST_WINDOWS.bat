@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Install Python research dependencies first using START_WINDOWS.bat or INSTALL_FULL_RESEARCH_WINDOWS.bat.
 pause
 exit /b 1
)
set "PY=.venv\Scripts\python.exe"
echo === VIGIL Studio v4.7 -- local software verification ===
%PY% -m pip install "pytest>=8,<10"
if errorlevel 1 goto :fail
%PY% -c "import torch, safetensors" >nul 2>nul
if errorlevel 1 (
 echo Optional deep learning libraries are not installed. Running base suite without the PyTorch integration tests.
 %PY% -m pytest -q tests --ignore=tests/test_ai_research_v2.py
) else (
 %PY% -m pytest -q tests
)
if errorlevel 1 goto :fail
%PY% -m vigil_studio.environment catalog
if errorlevel 1 goto :fail
%PY% -m vigil_studio.environment plan --preset research-multimodal-30gb
if errorlevel 1 goto :fail
if not exist "selftest" mkdir selftest
%PY% -m vigil_studio.environment stress-test examples\synthetic_agreement.csv --channel ECG --out selftest\SYNTHETIC_stress_test.json
if errorlevel 1 goto :fail
%PY% scripts\make_synthetic_ai_fixture.py selftest\SYNTHETIC_cohort
if errorlevel 1 goto :fail
%PY% -m vigil_studio.ai validate selftest\SYNTHETIC_cohort\manifest_SYNTHETIC_ENGINEERING_TEST_ONLY.csv
if errorlevel 1 goto :fail
echo.
echo Software self-test passed. All waveform fixtures are SYNTHETIC.
echo This does NOT verify model accuracy on real patients, clinical safety or regulatory approval.
pause
exit /b 0
:fail
echo.
echo Self-test failed. Do not treat the software as verified.
pause
exit /b 1
