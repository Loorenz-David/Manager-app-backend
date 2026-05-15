from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "beyo_manager"


def _run(cmd: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(
        cmd,
        cwd=ROOT,
        check=check,
        text=True,
        env=env,
        stdout=None,
        stderr=None,
    )


def _capture(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        check=False,
        text=True,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _ensure_env_file() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        return
    example_path = ROOT / ".env.example"
    if not example_path.exists():
        raise RuntimeError(".env.example is missing.")
    shutil.copyfile(example_path, env_path)


def _read_env_value(key: str) -> str:
    if os.environ.get(key):
        return os.environ[key]
    env_path = ROOT / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def _require_env() -> None:
    if not _read_env_value("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is missing.")
    if not _read_env_value("REDIS_URL"):
        raise RuntimeError("REDIS_URL is missing.")


def _require_docker_compose() -> None:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker CLI is not installed or is not on PATH.")
    result = _capture(["docker", "compose", "version"])
    if result.returncode != 0:
        raise RuntimeError(f"Docker Compose is unavailable: {result.stderr.strip()}")


def _pick_host_port(preferred: int) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", preferred))
            return str(preferred)
        except OSError:
            pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return str(sock.getsockname()[1])


def _validation_env() -> dict[str, str]:
    env = os.environ.copy()
    postgres_port = env.get("POSTGRES_PORT") or _pick_host_port(5432)
    redis_port = env.get("REDIS_PORT") or _pick_host_port(6379)
    app_port = env.get("PORT") or _pick_host_port(5000)
    env["POSTGRES_PORT"] = postgres_port
    env["REDIS_PORT"] = redis_port
    env["PORT"] = app_port
    env["DATABASE_URL"] = f"postgresql+asyncpg://postgres:postgres@127.0.0.1:{postgres_port}/{APP_NAME}"
    env["REDIS_URL"] = f"redis://127.0.0.1:{redis_port}/0"
    env["UVICORN_RELOAD"] = "0"
    return env


def _wait_for_compose_services(env: dict[str, str], timeout_seconds: int = 90) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        pg = _capture(["docker", "compose", "exec", "-T", "postgres", "pg_isready", "-U", "postgres", "-d", APP_NAME], env=env)
        redis = _capture(["docker", "compose", "exec", "-T", "redis", "redis-cli", "ping"], env=env)
        if pg.returncode == 0 and redis.returncode == 0 and "PONG" in redis.stdout:
            return
        last_error = (pg.stderr + redis.stderr + pg.stdout + redis.stdout).strip()
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for Docker Compose services: {last_error}")


def _create_database_if_missing(env: dict[str, str]) -> None:
    query = f"SELECT 1 FROM pg_database WHERE datname = '{APP_NAME}'"
    result = _capture(["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-tAc", query], env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to inspect PostgreSQL databases: {result.stderr.strip()}")
    if result.stdout.strip() == "1":
        return
    _run(["docker", "compose", "exec", "-T", "postgres", "createdb", "-U", "postgres", APP_NAME], env=env)


def _wait_for_health(env: dict[str, str], timeout_seconds: int = 60) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_error: str | None = None
    url = f"http://127.0.0.1:{env['PORT']}/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
                if response.status == 200:
                    return data
                last_error = f"HTTP {response.status}: {body}"
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(1)
    raise RuntimeError(f"FastAPI health check did not become healthy: {last_error}")


def main() -> None:
    _ensure_env_file()
    _require_env()
    _require_docker_compose()
    env = _validation_env()
    _run(["docker", "compose", "up", "-d"], env=env)
    _wait_for_compose_services(env)
    _create_database_if_missing(env)
    _run([sys.executable, "-m", "scripts.wait_for_services"], env=env)
    _run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env)

    app = subprocess.Popen([sys.executable, "run.py"], cwd=ROOT, env=env, text=True)
    try:
        data = _wait_for_health(env)
        services = data.get("services", {})
        if services.get("db") != "ok":
            raise RuntimeError(f"DB health check failed: {services.get('db')}")
        if services.get("redis") != "ok":
            raise RuntimeError(f"Redis health check failed: {services.get('redis')}")
        print("Bootstrap validation passed.")
    finally:
        app.terminate()
        try:
            app.wait(timeout=10)
        except subprocess.TimeoutExpired:
            app.kill()
            app.wait(timeout=10)


if __name__ == "__main__":
    main()
