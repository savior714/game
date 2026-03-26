@echo off
setlocal enableextensions

REM Dev launcher: start local server and open browser.
REM Usage:
REM   dev.bat                  -> main page (index.html)
REM   dev.bat math             -> math game
REM   dev.bat english          -> english game
REM   dev.bat korean           -> korean game
REM   dev.bat marble           -> marble game
REM   dev.bat math --no-browser -> server only

cd /d "%~dp0"

if not exist "serve_game.py" (
  echo [ERROR] "serve_game.py" not found in: %cd%
  echo         Run this from the repo root.
  exit /b 1
)

set "PY_EXE="
for %%P in (py python python3) do (
  where %%P >nul 2>nul
  if not errorlevel 1 (
    set "PY_EXE=%%P"
    goto :py_found
  )
)

:py_found
if not defined PY_EXE (
  echo [ERROR] Python not found. Install Python and ensure it's on PATH.
  echo         Recommended: install Python 3.x and enable "py" launcher.
  exit /b 1
)

if /i "%PY_EXE%"=="py" (
  py -3 "serve_game.py" %*
) else (
  "%PY_EXE%" "serve_game.py" %*
)

endlocal
