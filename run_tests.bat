@echo off
setlocal
python -m unittest discover -s tests -v
if errorlevel 1 pause
