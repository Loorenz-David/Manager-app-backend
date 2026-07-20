"""Stable report models for Connecteam user mapping operations."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .enums import ConnecteamUserMappingStatusEnum


IDENTITY_CONFLICT_STATUSES = frozenset(
    {
        ConnecteamUserMappingStatusEnum.DUPLICATE_EXTERNAL_FULL_NAME,
        ConnecteamUserMappingStatusEnum.EXISTING_DIFFERENT_CONNECTEAM_ID,
        ConnecteamUserMappingStatusEnum.CONNECTEAM_ID_ALREADY_ASSIGNED,
        ConnecteamUserMappingStatusEnum.WORK_PROFILE_AMBIGUOUS,
    }
)


@dataclass(frozen=True)
class ConnecteamUserMappingRow:
    user_id: int
    first_name: str
    last_name: str
    external_full_name: str | None
    normalized_external_name: str | None
    internal_username: str | None
    internal_user_id: str | None
    user_work_profile_id: str | None
    workspace_id: str | None
    existing_connecteam_user_id: str | None
    status: ConnecteamUserMappingStatusEnum
    detail: str | None = None
    source_row_number: int | None = None

    def to_dict(self) -> dict[str, object | None]:
        return {
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "external_full_name": self.external_full_name,
            "normalized_external_name": self.normalized_external_name,
            "internal_username": self.internal_username,
            "internal_user_id": self.internal_user_id,
            "user_work_profile_id": self.user_work_profile_id,
            "workspace_id": self.workspace_id,
            "existing_connecteam_user_id": self.existing_connecteam_user_id,
            "status": self.status.value,
            "detail": self.detail,
            "source_row_number": self.source_row_number,
        }


@dataclass(frozen=True)
class ConnecteamUserMappingReport:
    source_file: str = ""
    workspace_id: str | None = None
    rows: tuple[ConnecteamUserMappingRow, ...] = ()
    dry_run: bool = True
    applied: bool = False
    warnings: tuple[str, ...] = ()

    @property
    def identity_conflicts_present(self) -> bool:
        return any(row.status in IDENTITY_CONFLICT_STATUSES for row in self.rows)

    @property
    def status_counts(self) -> dict[str, int]:
        counts = Counter(row.status.value for row in self.rows)
        return {status.value: counts.get(status.value, 0) for status in ConnecteamUserMappingStatusEnum}

    def to_dict(self) -> dict[str, object]:
        return {
            "source_file": self.source_file,
            "workspace_id": self.workspace_id,
            "dry_run": self.dry_run,
            "applied": self.applied,
            "identity_conflicts_present": self.identity_conflicts_present,
            "status_counts": self.status_counts,
            "warnings": list(self.warnings),
            "rows": [row.to_dict() for row in self.rows],
        }
