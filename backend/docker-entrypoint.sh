#!/bin/sh
# Mirrors the manual steps in README.md ("alembic upgrade head" then
# uvicorn) so the image behaves the same as running it by hand.
set -e

alembic upgrade head
exec uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8001}"
