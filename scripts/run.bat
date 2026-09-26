@echo off
rem Launch the game from source, running setup first if needed.
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe call "%~dp0setup.bat"
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -c "import pygame" >nul 2>nul
if errorlevel 1 call "%~dp0setup.bat"
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m cars %*
if errorlevel 1 pause
