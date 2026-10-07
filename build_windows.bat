@echo off
setlocal
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.10+ and try again.
  pause
  exit /b 1
)
py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
pyinstaller --onefile --name get-sauce get_sauce.py
echo.
echo Built: dist\get-sauce.exe
pause
