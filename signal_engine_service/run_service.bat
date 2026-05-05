@echo off
REM AI Signal Engine Service - Direct Start Script
REM This runs the signal engine directly

cd /d "%~dp0"
set PYTHONPATH=%~dp0..

call "%~dp0..\.venv\Scripts\activate.bat"
python world_class_signal_engine.py
