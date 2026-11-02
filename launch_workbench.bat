@echo off
cd /d "%~dp0"
echo EXODIA Albedo Visual Workbench
start "" "http://localhost:8765/test_workbench.html"
py -3 -m http.server 8765 --directory orchestrator\frontend
pause
