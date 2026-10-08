#!/usr/bin/env bash
# Runs GeoMeasure locally:  bash run.sh  (or bash run.sh 8080 for another port)
# The first run sets up .venv, installs the requirements and creates a dev .env. After that it just
# applies migrations and starts the server, and only reinstalls when a requirements file changes.
set -euo pipefail
cd "$(dirname "$0")"

PORT="${1:-8000}"

# I try python3 first, but on Windows that can be the Store stub, so I check it actually runs.
PY=""
for p in python3 python; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c "import sys" >/dev/null 2>&1; then PY="$p"; break; fi
done
[ -n "$PY" ] || { echo "Python 3.12+ is needed but I couldn't find it on PATH." >&2; exit 1; }

if [ ! -d .venv ]; then
  echo "Creating .venv ..."
  "$PY" -m venv .venv
fi

# Windows venvs put python in Scripts/, everywhere else it's bin/.
if [ -x .venv/Scripts/python.exe ]; then VPY=.venv/Scripts/python.exe; else VPY=.venv/bin/python; fi

# The stamp file lets me skip pip unless requirements changed since the last install.
STAMP=.venv/.installed
if [ ! -f "$STAMP" ] || [ requirements.txt -nt "$STAMP" ] || [ requirements-dev.txt -nt "$STAMP" ]; then
  echo "Installing requirements ..."
  "$VPY" -m pip install -q --upgrade pip
  "$VPY" -m pip install -q -r requirements.txt -r requirements-dev.txt
  touch "$STAMP"
fi

# For local runs I start from .env.example with DEBUG on, so no SECRET_KEY is needed.
if [ ! -f .env ]; then
  echo "Creating .env for local development (DEBUG=True) ..."
  sed 's/^DEBUG=.*/DEBUG=True/' .env.example > .env
fi

"$VPY" manage.py migrate --noinput

echo "GeoMeasure is starting on http://127.0.0.1:$PORT  (Ctrl+C to stop)"
exec "$VPY" manage.py runserver "127.0.0.1:$PORT"
