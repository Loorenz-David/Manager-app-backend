"""Serialization helpers for issue type domain objects."""

from beyo_manager.models.tables.issue_types.issue_category_config import IssueCategoryConfig
from beyo_manager.models.tables.issue_types.issue_type import IssueType


def serialize_issue_type(row: IssueType) -> dict:
    return {
        "client_id": row.client_id,
        "name": row.name,
        "source": row.source.value,
        "created_at": row.created_at.isoformat(),
        "created_by_id": row.created_by_id,
    }


def serialize_issue_category_config(row: IssueCategoryConfig, issue_type_name: str) -> dict:
    return {
        "client_id": row.client_id,
        "item_category_id": row.item_category_id,
        "issue_type_id": row.issue_type_id,
        "base_time_seconds": row.base_time_seconds,
        "issue_type_name": issue_type_name,
    }
