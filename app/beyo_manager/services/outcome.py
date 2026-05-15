from dataclasses import dataclass

from beyo_manager.errors.base import DomainError


@dataclass
class StatusOutcome:
    success: bool
    data: dict | list | None = None
    error: DomainError | None = None
