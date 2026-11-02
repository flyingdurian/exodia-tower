#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Open http://localhost:8765/test_workbench.html"
python3 -m http.server 8765 --directory orchestrator/frontend
