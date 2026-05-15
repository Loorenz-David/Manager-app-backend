from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryMetadata:
    max_attempts: int = 5
    backoff_seconds: int = 10


DEFAULT_RETRY = RetryMetadata()
