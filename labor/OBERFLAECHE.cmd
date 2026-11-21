@echo off
cd /d "%~dp0"
python oberflaeche.py
if errorlevel 1 pause
