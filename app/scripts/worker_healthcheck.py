from beyo_manager.workers.health import worker_healthcheck


if __name__ == "__main__":
    health = worker_healthcheck()
    if health.get("redis") != "ok":
        raise SystemExit(1)
