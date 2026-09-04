@echo off
rem Furmula launcher - starts without a console window
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "main.py"
