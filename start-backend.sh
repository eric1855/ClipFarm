#!/usr/bin/env bash
set -Eeuo pipefail

echo "Starting Caption Extraction API Backend..."

# Base Python
PY_BIN="${PY_BIN:-python}"

# Create virtual environment if requested
VENV_PY="$PY_BIN"
if [[ -n "${USE_VENV:-1}" ]]; then
  VENV_DIR="${VENV_DIR:-.venv}"
  if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating Python virtual environment in $VENV_DIR ..."
    "$PY_BIN" -m venv "$VENV_DIR"
  fi
  # Compute interpreter inside venv (Windows vs POSIX)
  if [[ -f "$VENV_DIR/bin/python" ]]; then
    VENV_PY="$VENV_DIR/bin/python"
  elif [[ -f "$VENV_DIR/Scripts/python.exe" ]]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
  elif [[ -f "$VENV_DIR/Scripts/python" ]]; then
    VENV_PY="$VENV_DIR/Scripts/python"
  fi
fi

echo "Installing Python dependencies..."
"$VENV_PY" -m pip install --upgrade pip >/dev/null
"$VENV_PY" -m pip install -r requirements.txt

# Warn if no OpenAI API key is present (some endpoints require it)
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  if [[ -f .env ]]; then
    echo "Note: OPENAI_API_KEY not set in environment. .env will be loaded by the app."
  else
    echo "Warning: OPENAI_API_KEY not set. Set it in .env or the environment to use clip selection endpoints."
  fi
fi

export PORT="${PORT:-8000}"
echo "Starting FastAPI on http://localhost:${PORT} (backend.api:app)"
exec "$VENV_PY" -m uvicorn backend.api:app --host 0.0.0.0 --port "$PORT" --reload
