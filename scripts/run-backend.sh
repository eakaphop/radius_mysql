#!/usr/bin/env bash
# Run the backend manually (no systemd / Docker / nginx).
# First run: creates the venv and installs deps. Subsequent runs just start uvicorn.
set -euo pipefail

cd "$(dirname "$0")/../backend"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -e ".[dev]"
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
