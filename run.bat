@echo off
setlocal
python "%~dp0get_sauce.py" %*
if errorlevel 1 (
  echo.
  echo get-sauce.py exited with an error.
  pause
)
