#!/usr/bin/env bash
set -Eeuo pipefail

echo "Starting Caption Extraction Frontend..."

# Choose port
export PORT="${FRONTEND_PORT:-${PORT:-3000}}"

need() { command -v "$1" >/dev/null 2>&1; }

# From here on, we expect a JS app (server.js or package.json)
if ! need node; then
  echo "Error: Node.js is not installed. Install from https://nodejs.org/"
  exit 1
fi
if ! need npm; then
  echo "Error: npm is not installed."
  exit 1
fi

# Helper to run via npx or npm exec
run_npx() {
  if need npx; then
    npx --yes "$@"
  else
    npm exec -- "$@"
  fi
}

# Detect package manager (pnpm > yarn > npm)
PKG_MGR="${PKG_MGR:-}"
if [[ -z "$PKG_MGR" ]]; then
  if need pnpm; then PKG_MGR=pnpm
  elif need yarn; then PKG_MGR=yarn
  else PKG_MGR=npm
  fi
fi

install_deps() {
  case "$PKG_MGR" in
    pnpm) pnpm install ;;
    yarn) yarn install ;;
    npm)  npm install  ;;
    *)    echo "Unknown package manager: $PKG_MGR"; exit 1 ;;
  esac
}

run_script() {
  local script="$1"
  case "$PKG_MGR" in
    pnpm) exec pnpm "$script" ;;
    yarn) exec yarn "$script" ;;
    npm)  exec npm run "$script" ;;
  esac
}

# Install dependencies if needed
if [[ -f package.json && ! -d node_modules ]]; then
  echo "Installing Node.js dependencies with $PKG_MGR..."
  install_deps
fi

# Optional Tailwind build if config present
if [[ -f tailwind.config.js && -f public/css/input.css ]]; then
  echo "Building Tailwind CSS (via npx)..."
  run_npx tailwindcss -i ./public/css/input.css -o ./public/css/output.css || echo "Tailwind build skipped."
fi

echo "Starting frontend on http://localhost:${PORT}"

# Start priority:
# 1) server.js (custom server)
# 2) package.json scripts: dev > start
# 3) Vite (vite.config.*)
# 4) Static server via npx (http-server or serve)
if [[ -f server.js ]]; then
  exec node server.js
elif [[ -f package.json ]]; then
  if grep -q '"dev"\s*:' package.json; then
    run_script dev
  elif grep -q '"start"\s*:' package.json; then
    run_script start
  else
    # Try Vite directly via npx
    if ls vite.config.* >/dev/null 2>&1; then
      exec run_npx vite --port "$PORT"
    else
      echo "No dev/start script found in package.json. Falling back to a static server..."
      if need npx; then
        if run_npx http-server -v >/dev/null 2>&1; then
          exec run_npx http-server -p "$PORT" -c-1 .
        else
          exec run_npx serve -l "$PORT" -s .
        fi
      else
        echo "npx not available; cannot start a fallback static server."
        exit 1
      fi
    fi
  fi
else
  echo "No frontend entry found (server.js or package.json)."
  if need npx; then
    echo "Serving current directory statically via npx..."
    if run_npx http-server -v >/dev/null 2>&1; then
      exec run_npx http-server -p "$PORT" -c-1 .
    else
      exec run_npx serve -l "$PORT" -s .
    fi
  else
    echo "npx not available; using Python simple HTTP server as a last resort..."
    exec python -m http.server "$PORT"
  fi
fi
