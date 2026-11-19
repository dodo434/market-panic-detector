#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -d "frontend/node_modules" ]; then
  (cd frontend && npm install)
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

"$PYTHON_BIN" -m uvicorn backend.api.app:app --host "${BACKEND_HOST:-127.0.0.1}" --port "${BACKEND_PORT:-8000}" &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT
(cd frontend && npm run dev -- --host 127.0.0.1)
