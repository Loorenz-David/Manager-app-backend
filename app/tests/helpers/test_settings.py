from __future__ import annotations


def assert_deterministic_environment(env: dict[str, str]) -> None:
    required = ["DATABASE_URL", "REDIS_URL", "ENVIRONMENT"]
    missing = [key for key in required if not env.get(key)]
    if missing:
        raise RuntimeError(f"Missing deterministic test settings: {', '.join(missing)}")
