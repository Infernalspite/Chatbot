#!/usr/bin/env bash
set -euo pipefail

export API_URL="${API_URL:-http://127.0.0.1:8000}"
export STREAMLIT_URL="${STREAMLIT_URL:-http://127.0.0.1:8501}"
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

python backend/setup_db.py

(
  cd backend
  python -m uvicorn main:app --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

python -m streamlit run frontend/app.py \
  --server.address 127.0.0.1 \
  --server.port 8501 \
  --server.headless true \
  --browser.gatherUsageStats false \
  --server.enableCORS false \
  --server.enableXsrfProtection false &
STREAMLIT_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
  kill "$STREAMLIT_PID" 2>/dev/null || true
}
trap cleanup EXIT

sleep 5

python scripts/render_proxy.py
