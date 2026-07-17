#!/usr/bin/env bash
# render_start.sh — Simplified startup script.
# Streamlit has been replaced with a static HTML/JS/CSS frontend
# served directly by FastAPI (mounted at root via StaticFiles).
# The proxy on port 10000 forwards ALL traffic to FastAPI on port 8000.
set -euo pipefail

export API_URL="${API_URL:-http://127.0.0.1:8000}"
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

# Run DB setup/migrations once on startup
python backend/setup_db.py

# Start FastAPI backend (serves both the API and the static frontend)
(
  cd backend
  python -m uvicorn main:app --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

# Give uvicorn a moment to bind before starting the proxy
sleep 3

# Start the thin port-10000 proxy that Render expects
python scripts/render_proxy.py
