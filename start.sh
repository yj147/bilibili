#!/bin/bash
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "Starting Bili-Sentinel..."

python -m backend.main > /tmp/sentinel-backend.log 2>&1 &
BACKEND_PID=$!

cd "$PROJECT_ROOT/frontend" && npx next dev > /tmp/sentinel-frontend.log 2>&1 &
FRONTEND_PID=$!

echo "Backend: http://localhost:8000 (PID: $BACKEND_PID)"
echo "Frontend: http://localhost:3000 (PID: $FRONTEND_PID)"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped'; exit" INT TERM
wait
