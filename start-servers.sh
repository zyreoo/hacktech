#!/usr/bin/env bash
# From repo root: ./start-servers.sh
# Backend: http://127.0.0.1:8000  |  UI: http://localhost:3000
python run_hub.py &
HUB_PID=$!
(cd ui && npm run dev) &
UI_PID=$!
echo "Backend (hub): http://127.0.0.1:8000  (PID $HUB_PID)"
echo "UI:           http://localhost:3000  (PID $UI_PID)"
echo "Ctrl+C to stop both."
trap "kill $HUB_PID $UI_PID 2>/dev/null; exit" INT TERM
wait
