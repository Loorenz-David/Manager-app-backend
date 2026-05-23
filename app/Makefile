.PHONY: dev-up dev-up-full dev-down dev-logs db-create db-init db-migrate run

# Hybrid mode: run app locally, infra in Docker.
dev-up:
	docker compose up -d postgres redis

# Full containerized mode: backend + worker + infra.
dev-up-full:
	docker compose --profile app up -d

dev-down:
	docker compose down

dev-logs:
	docker compose logs -f

db-create:
	PYTHONPATH=. APP_ENV=development python3 -m scripts.create_db

db-init:
	PYTHONPATH=. APP_ENV=development python3 -m scripts.create_db
	PYTHONPATH=. APP_ENV=development python3 -m scripts.wait_for_services

db-migrate:
	@if [ -z "$$(ls migrations/versions/*.py 2>/dev/null)" ]; then \
		echo "[db-migrate] No migration found — generating initial schema"; \
		APP_ENV=development alembic revision --autogenerate -m "initial_schema"; \
	fi
	APP_ENV=development alembic upgrade head

run:
	APP_ENV=development python3 run.py

# Testing
test:
	pytest -m 'not e2e'

test-unit:
	pytest tests/unit -m unit

test-integration:
	pytest tests/integration -m integration

test-e2e:
	pytest tests/e2e -m e2e

# Worker runtime
worker:
	PYTHONPATH=. python worker.py

worker-dev:
	PYTHONPATH=. APP_ENV=development python scripts/worker.py

presence-worker:
	PYTHONPATH=. APP_ENV=development python -m beyo_manager.workers.presence_worker

analytics-worker:
	PYTHONPATH=. APP_ENV=development python -m beyo_manager.workers.analytics_worker

notification-worker:
	PYTHONPATH=. APP_ENV=development python -m beyo_manager.workers.notification_worker

worker-logs:
	docker compose logs -f worker

# Scheduler runners
delayed-scheduler:
	PYTHONPATH=. APP_ENV=development python -m beyo_manager.workers.delayed_scheduler_runner

recurring-scheduler:
	PYTHONPATH=. APP_ENV=development python -m beyo_manager.workers.recurring_scheduler_runner

task-router:
	PYTHONPATH=. APP_ENV=development python -m beyo_manager.workers.task_router_process

# Run before every production deploy
pre-deploy:
	APP_ENV=production alembic upgrade head
	APP_ENV=production PYTHONPATH=. python scripts/apply_db_triggers.py

# CI and validation
lint:
	python -m ruff check .

format:
	python -m ruff format .

validate:
	python scripts/ci_validate.py

# Replayability
replay:
	python scripts/replay.py events --dry-run

# Operational CLI
seed:
	python scripts/ops.py seed

logs:
	docker compose logs -f

inspect:
	python scripts/ops.py inspect

reset-db:
	python scripts/ops.py reset-db --dry-run True

.PHONY: dev-up dev-down test lint format validate worker seed logs replay inspect reset-db presence-worker analytics-worker notification-worker
