#!/bin/bash
# Start Luminate Cookbook locally (FastAPI). Survives moved project folders.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"
PYTHON="./venv/bin/python3"

if [[ ! -x "$PYTHON" ]]; then
  echo "No usable ./venv — creating one…"
  /usr/bin/python3 -m venv venv
  PYTHON="./venv/bin/python3"
  "$PYTHON" -m pip install -U pip
  "$PYTHON" -m pip install -r requirements.txt
  "$PYTHON" -m playwright install chromium || true
fi

# Prefer module form so stale shebangs (from a moved checkout) don't break startup
echo "Luminate Cookbook → http://${HOST}:${PORT}"
echo "Tools: /upload  /banner  /pagebuilder  /email-beautifier   API docs: /docs"
echo "Stop: Ctrl+C"
exec "$PYTHON" -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
