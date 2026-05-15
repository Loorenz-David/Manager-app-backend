#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() {
    echo "[bootstrap-local] $1"
}

if [[ "${BOOTSTRAP_RESET_STATE:-0}" == "1" ]]; then
    log "Reset requested. Removing docker volumes and migration files"
    docker compose down -v || true
    rm -f migrations/versions/*.py
fi

if [[ ! -d ".venv" ]]; then
    log "Creating virtual environment (.venv)"
    python3 -m venv .venv
fi

log "Activating .venv"
source .venv/bin/activate

log "Installing dependencies"
pip install -r requirements.txt -r requirements-dev.txt

if [[ ! -f ".env" ]]; then
    log "Creating .env from .env.example"
    cp .env.example .env
fi

log "Starting docker services"
make dev-up

log "Creating database if missing"
PYTHONPATH=. APP_ENV=development python -m scripts.create_db

log "Waiting for services"
PYTHONPATH=. APP_ENV=development python -m scripts.wait_for_services

if ! compgen -G "migrations/versions/*.py" > /dev/null; then
    log "No migration found. Generating initial schema migration"
    APP_ENV=development alembic revision --autogenerate -m "Initial schema"
else
    log "Migration file detected. Skipping autogenerate"
fi

log "Applying migrations"
APP_ENV=development alembic upgrade head

log "Applying Postgres triggers"
PYTHONPATH=. APP_ENV=development python scripts/apply_db_triggers.py

log "Done. Start API with: make run"
