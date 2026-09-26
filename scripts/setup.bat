@echo off
rem Create a local virtual environment in the project folder and install the game.
setlocal
cd /d "%~dp0.."
if exist .venv\Scripts\python.exe goto install
where py >nul 2>nul
if errorlevel 1 goto plain_python
py -3 -m venv .venv
if errorlevel 1 goto failed
goto install

:plain_python
python -m venv .venv
if errorlevel 1 goto failed

:install
.venv\Scripts\python.exe -m pip install -e .
if errorlevel 1 goto failed
echo Setup complete. Double-click scripts\run.bat to play.
exit /b 0

:failed
echo Setup failed. Install Python 3.10 or newer from python.org, then try again.
echo An internet connection is needed for the first installation.
pause
exit /b 1
