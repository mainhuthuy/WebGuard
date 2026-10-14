#!/usr/bin/env bash
# One-click dev setup for WebGuard (Linux / macOS / Git Bash).
#
# Checks prerequisites, creates the backend virtualenv, installs backend + frontend
# dependencies and creates the .env files from their examples. Safe to re-run: it never
# overwrites an existing .env or recreates an existing virtualenv.
#
# Usage:
#   ./scripts/setup-dev.sh            full local setup
#   ./scripts/setup-dev.sh --check    only verify prerequisites; change nothing
#   ./scripts/setup-dev.sh --docker   start the hot-reload Docker stack instead
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_ONLY=0
USE_DOCKER=0

for arg in "$@"; do
  case "$arg" in
    --check)  CHECK_ONLY=1 ;;
    --docker) USE_DOCKER=1 ;;
    -h|--help) sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg (try --help)" >&2; exit 2 ;;
  esac
done

if [ -t 1 ]; then C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_STEP=$'\033[36m'; C_OFF=$'\033[0m'
else C_OK=""; C_WARN=""; C_ERR=""; C_STEP=""; C_OFF=""; fi
step() { printf '\n%s==> %s%s\n' "$C_STEP" "$1" "$C_OFF"; }
ok()   { printf '  %s[ok]%s   %s\n' "$C_OK" "$C_OFF" "$1"; }
warn() { printf '  %s[warn]%s %s\n' "$C_WARN" "$C_OFF" "$1"; }
fail() { printf '  %s[FAIL]%s %s\n' "$C_ERR" "$C_OFF" "$1"; FAILED=1; }
FAILED=0

# "major.minor" of a command's --version output, or empty if absent.
version_of() { "$@" 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -n1 || true; }
# true if $1 >= $2 (both major.minor)
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }

step "Checking prerequisites"

PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    v="$(version_of "$candidate" --version)"
    if [ -n "$v" ] && ver_ge "$v" 3.12; then PY="$candidate"; ok "Python $v ($candidate)"; break; fi
  fi
done
if [ -z "$PY" ] && [ "$USE_DOCKER" -eq 0 ]; then fail "Python 3.12+ not found (https://www.python.org/downloads/)"; fi

if command -v node >/dev/null 2>&1 && ver_ge "$(version_of node --version)" 18.0; then
  ok "Node.js $(version_of node --version)"
elif [ "$USE_DOCKER" -eq 0 ]; then fail "Node.js 18+ not found (https://nodejs.org/)"; fi

if command -v git >/dev/null 2>&1; then ok "Git"; else warn "Git not found (only needed to contribute)"; fi

DOCKER_OK=0
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then DOCKER_OK=1; ok "Docker (daemon running)"
  else warn "Docker installed but the daemon is not running"; fi
else warn "Docker not found (optional for local dev, required for --docker)"; fi
if [ "$USE_DOCKER" -eq 1 ] && [ "$DOCKER_OK" -eq 0 ]; then fail "--docker needs a running Docker daemon"; fi

if [ "$FAILED" -ne 0 ]; then echo; echo "Prerequisites missing - fix the items marked FAIL and re-run." >&2; exit 1; fi
if [ "$CHECK_ONLY" -eq 1 ]; then printf '\n%sAll prerequisites OK.%s\n' "$C_OK" "$C_OFF"; exit 0; fi

if [ "$USE_DOCKER" -eq 1 ]; then
  step "Starting hot-reload Docker stack"
  (cd "$ROOT/docker" && docker compose -f docker-compose.dev.yml up -d --build)
  printf '\n%sFrontend: http://localhost:5173   API docs: http://localhost:8000/docs%s\n' "$C_OK" "$C_OFF"
  echo "Stop with: docker compose -f docker/docker-compose.dev.yml down"
  exit 0
fi

step "Creating .env files (existing ones are kept)"
for dir in backend frontend; do
  example="$ROOT/$dir/.env.example"; target="$ROOT/$dir/.env"
  [ -f "$example" ] || continue
  if [ -f "$target" ]; then ok "$dir/.env already exists - left untouched"
  else cp "$example" "$target"; ok "created $dir/.env"; fi
done

step "Backend: virtualenv + dependencies"
VENV="$ROOT/backend/.venv"
if [ ! -d "$VENV" ]; then "$PY" -m venv "$VENV"; ok "created backend/.venv"; else ok "backend/.venv already exists"; fi
# venv layout differs: bin/ on Linux/macOS, Scripts/ on Windows (Git Bash)
if [ -x "$VENV/bin/python" ]; then VENV_PY="$VENV/bin/python"; else VENV_PY="$VENV/Scripts/python.exe"; fi
(cd "$ROOT/backend" && "$VENV_PY" -m pip install --quiet --upgrade pip && "$VENV_PY" -m pip install --quiet -e ".[dev]")
ok "backend dependencies installed"

step "Frontend: npm ci"
(cd "$ROOT/frontend" && npm ci --no-audit --no-fund)
ok "frontend dependencies installed"

printf '\n%sSetup complete.%s\n' "$C_OK" "$C_OFF"
cat <<'EOF'

Run the app (two terminals):
  Backend : cd backend && source .venv/bin/activate && python -m uvicorn app.main:app --reload
  Frontend: cd frontend && npm run dev

Then open http://localhost:5173  (API docs: http://localhost:8000/docs)
Run the checks CI runs:  cd backend && ruff check app tests && pytest   |   cd frontend && npm run lint && npm test
EOF
