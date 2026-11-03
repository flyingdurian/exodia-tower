@echo off
setlocal
cd /d "%~dp0orchestrator"
if errorlevel 1 (
  echo Unable to enter EXODIA orchestrator folder.
  pause
  exit /b 1
)
echo.
echo ==========================================================
echo EXODIA Tower - Albedo 33-State Development Workbench
echo ==========================================================
echo Local FastAPI server (not a static file server).
echo Web address: http://127.0.0.1:8765/test-workbench
echo All 33 production states remain locked pending artwork.
echo.
where py >nul 2>nul
if not errorlevel 1 (
  set "EXODIA_PY=py -3"
) else (
  set "EXODIA_PY=python"
)
start "" "http://127.0.0.1:8765/test-workbench"
%EXODIA_PY% main.py
if errorlevel 1 (
  echo.
  echo EXODIA startup failed. Install requirements from the repository:
  echo   python -m pip install -r orchestrator/requirements.txt
  echo Refresh the browser after a successful launch.
  pause
  exit /b 1
)
endlocal
