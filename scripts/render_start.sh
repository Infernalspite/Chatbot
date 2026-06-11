#!/usr/bin/env bash
set -euo pipefail

export API_URL="${API_URL:-http://127.0.0.1:8000}"

python backend/setup_db.py

(
  cd backend
  python -m uvicorn main:app --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

sleep 5

python -m streamlit run frontend/app.py \
  --server.address 0.0.0.0 \
  --server.port "${PORT:-10000}" \
  --server.headless true \
  --browser.gatherUsageStats false
