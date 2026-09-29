# syntax=docker/dockerfile:1

# One image for every backend process. The container command picks the process
# (API, task router, a queue worker, a scheduler, the migration job); nothing here
# is specific to one of them.
#
# Configuration comes only from real environment variables at run time. No .env
# file is copied in (see .dockerignore), so `Settings` finds none to load.

ARG PYTHON_IMAGE=python:3.12.14-slim-trixie
FROM ${PYTHON_IMAGE}

# PYTHONPATH=/app lets path-form commands (`python scripts/apply_db_triggers.py`)
# import `beyo_manager`, as the systemd units and the deploy script do today.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# tini runs as PID 1 and forwards signals. Without it, a process with no SIGTERM
# handler of its own (the task router and both schedulers) ignores `docker stop`
# and is killed only after the stop timeout.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app \
       --shell /usr/sbin/nologin app

WORKDIR /app

# Dependencies first, so a code-only change reuses this layer.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Source stays owned by root: the app user can read and run it but not change it.
COPY . .
RUN python -m compileall -q /app

ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="managerbeyo-backend" \
      org.opencontainers.image.source="https://github.com/Loorenz-David/Manager-app-backend" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.created="${BUILD_DATE}"

USER app
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default process: the API. Deliberately not `run.py` (the local-development
# launcher): that silently moves to another port when 8000 is taken and blocks
# for up to 60 s waiting for the database before listening. The 30 s graceful
# shutdown matches REQUEST_TIMEOUT_SECONDS, the longest any request may run, so
# `docker stop` lets in-flight requests finish and can never hang indefinitely.
# One process only: Socket.IO connection state is held in-process.
CMD ["uvicorn", "beyo_manager.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "30"]
