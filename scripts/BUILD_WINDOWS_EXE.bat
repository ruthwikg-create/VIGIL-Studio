@echo off
setlocal
cd /d "%~dp0.."
echo ========================================================
echo VIGIL Studio - Windows release build (local workstation)
echo ========================================================
where py >nul 2>nul
if errorlevel 1 (
 echo ERROR: Install Python 3.11, 3.12 or 3.13 from python.org
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
 echo ERROR: Please install Python 3.12 64-bit.
 pause
 exit /b 1
)
py %PYSEL% -m venv .venv
if errorlevel 1 exit /b 1
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 (
 echo Dependency installation failed.
 pause
 exit /b 1
)
python -m pytest -q tests
if errorlevel 1 (
 echo Tests failed; refusing to release binary.
 pause
 exit /b 1
)
pyinstaller --noconfirm --clean --windowed --onedir --name "VIGILStudio" ^
 --collect-all matplotlib --collect-all mne --collect-all wfdb --collect-submodules scipy --collect-submodules sklearn ^
 --hidden-import=tkinter --hidden-import=reportlab --hidden-import=mne --collect-submodules vigil_studio ^
 --add-data "docs;docs" --add-data "examples;examples" --add-data "vigil_studio/assets;vigil_studio/assets" ^
 --icon "vigil_studio/assets/vigil_signal_icon.ico" launch.py
if errorlevel 1 (
 echo Build failed. Check the terminal output.
 pause
 exit /b 1
)
echo.
echo Build output: dist\VIGILStudio\VIGILStudio.exe
echo WARNING: .exe is a RESEARCH application and NOT a medical device.
pause
