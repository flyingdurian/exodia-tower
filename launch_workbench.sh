#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/orchestrator"
echo "EXODIA Tower - 33-state Albedo development review"
echo "Serving existing FastAPI app at http://127.0.0.1:${PORT:-8765}/test-workbench"
echo "All production artwork remains locked until explicit image-specific approval."
if command -v xdg-open >/dev/null 2>&1; then
  (sleep 2; xdg-open "http://127.0.0.1:${PORT:-8765}/test-workbench" >/dev/null 2>&1 || true) &
elif command -v open >/dev/null 2>&1; then
  (sleep 2; open "http://127.0.0.1:${PORT:-8765}/test-workbench" >/dev/null 2>&1 || true) &
fi
exec python3 main.py
