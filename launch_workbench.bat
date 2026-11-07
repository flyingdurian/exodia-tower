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
echo Launching the existing FastAPI app, not a static file server.
echo Local address: http://127.0.0.1:8765/test-workbench
echo The native artwork release registry remains locked.
echo.
where py >nul 2>nul
if not errorlevel 1 (
  set "EXODIA_PY=py -3"
) else (
  set "EXODIA_PY=python"
)
start "EXODIA Tower FastAPI" cmd /k "%EXODIA_PY% main.py"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='http://127.0.0.1:8765/test-workbench'; for($i=0;$i -lt 60;$i++){ try { $response=Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 1; if($response.StatusCode -eq 200){ Start-Process $u; exit 0 } } catch {} ; Start-Sleep -Milliseconds 300 }; exit 1"
if errorlevel 1 (
  echo.
  echo The EXODIA web service did not become ready.
  echo Inspect the separate FastAPI console and install dependencies:
  echo   python -m pip install -r orchestrator/requirements.txt
  pause
  exit /b 1
)
echo 33-state workbench opened. Leave the EXODIA FastAPI window running.
endlocal
