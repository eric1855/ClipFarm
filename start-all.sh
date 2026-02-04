#!/usr/bin/env bash
set -Eeuo pipefail

# Start both Backend and Frontend
echo "Starting Caption Extraction Application..."

# Cleanup background processes on exit
cleanup() {
  echo "\nStopping servers..."
  if [[ -n "${BACKEND_PID:-}" ]]; then kill "${BACKEND_PID}" 2>/dev/null || true; fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then kill "${FRONTEND_PID}" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

# Ensure scripts are executable
chmod +x ./start-backend.sh ./start-frontend.sh 2>/dev/null || true

# Start backend in background
echo "Starting backend server..."
./start-backend.sh &
BACKEND_PID=$!

# Give backend a moment to come up
sleep 2

# Start frontend in background (if script exists)
if [[ -f ./start-frontend.sh ]]; then
  echo "Starting frontend server..."
  ./start-frontend.sh &
  FRONTEND_PID=$!
else
  echo "No start-frontend.sh found; skipping frontend."
  FRONTEND_PID=""
fi

echo ""
echo "🚀 Caption Extraction Application is running!"
echo "   Backend API: http://localhost:${PORT:-8000}"
echo "   API Docs:   http://localhost:${PORT:-8000}/docs"
if [[ -n "${FRONTEND_PID:-}" ]]; then
  echo "   Frontend:   http://localhost:3000"
fi
echo "\nPress Ctrl+C to stop all servers"

# Wait for background processes
if [[ -n "${FRONTEND_PID:-}" ]]; then
  wait "$BACKEND_PID" "$FRONTEND_PID"
else
  wait "$BACKEND_PID"
fi

