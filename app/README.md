# beyo_manager

## Runtime Modes

### Hybrid local mode (default)

Run backend locally; run infra in Docker:

```bash
make dev-up
cp .env.example .env
alembic upgrade head
python run.py
```

### Full containerized mode

Run backend + worker + PostgreSQL + Redis in Docker Compose:

```bash
make dev-up-full
```

Or directly:

```bash
docker compose --profile app up -d
```

### Validation mode (isolated)

Bootstrap validation intentionally uses dynamic host ports so it does not collide
with services already running on a developer machine.

```bash
python scripts/validate_bootstrap.py
```

### Shutdown

```bash
make dev-down
```

Or directly:

```bash
docker compose down
```

## Why dynamic validation ports exist

- Developer machines often already use 5432/6379/5000.
- Validation must run headless and deterministic in CI and local AI-agent loops.
- Isolation prevents accidental coupling to host-installed services.

## Deterministic runtime principles

- Health checks gate startup order for PostgreSQL and Redis.
- Services fail loudly when dependencies are unavailable.
- Environment contracts are explicit via `.env` and compose overrides.
- Runtime topology is modular-monolith-first: one backend app + one worker.
