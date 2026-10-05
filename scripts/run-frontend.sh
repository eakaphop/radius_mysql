#!/usr/bin/env bash
# Run the frontend dev server manually (vite, port 5174).
set -euo pipefail

cd "$(dirname "$0")/../frontend"

if [ ! -d node_modules ]; then
  npm install
fi

exec npm run dev
