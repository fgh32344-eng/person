@echo off
rem ============================================================
rem  Wang Yaowei - Personal Portfolio  launcher
rem
rem  IMPORTANT - keep this file ASCII-only and saved as CP936.
rem  cmd.exe parses .bat byte by byte using the system ANSI code
rem  page. Chinese text in a .bat file is easily corrupted into
rem  mojibake, and mojibake bytes can be treated as command
rem  separators, which shreds set/if/goto lines.
rem
rem  The Chinese startup banner is therefore printed by Python
rem  (backend/app.py), which handles console encoding itself.
rem  Do NOT add "chcp 65001" here: it conflicts with the CP936
rem  file content and turns the banner into double-encoded text.
rem ============================================================
setlocal enableextensions

set "SCRIPT_DIR=%~dp0"
set "PYTHON="

rem ---- 1. system py launcher ----
where py >nul 2>nul
if not errorlevel 1 set "PYTHON=py"

rem ---- 2. python on PATH ----
if not defined PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON=python"
)

rem ---- 3. bundled DSH python runtime ----
if not defined PYTHON (
  set "BUNDLED=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
  if exist "%BUNDLED%" set "PYTHON=%BUNDLED%"
)

if not defined PYTHON (
  echo.
  echo   [ERROR] Python not found. Please install Python 3.10+ :
  echo   https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

rem ---- defaults (override by setting these before launch) ----
if "%PORTFOLIO_HOST%"=="" set "PORTFOLIO_HOST=127.0.0.1"
if "%PORTFOLIO_PORT%"=="" set "PORTFOLIO_PORT=8000"

rem app.py picks FastAPI when available and otherwise falls back
rem to the zero-dependency standard library server.
"%PYTHON%" "%SCRIPT_DIR%backend\app.py"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  echo.
  echo   Server exited with code %EXITCODE%.
  echo   If a module is missing, run:
  echo     pip install -r "%SCRIPT_DIR%backend\requirements.txt"
  echo   Or use the zero-dependency mode directly:
  echo     python "%SCRIPT_DIR%backend\server.py"
  echo.
  pause
)

endlocal
