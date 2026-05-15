from enum import StrEnum


class Permission(StrEnum):
    """Add app-specific backend permissions as METHOD:/api/v1/path entries."""
    pass


def resolve_permissions_for_role(role) -> dict:
    """Return JWT-ready backend and UI permissions for a role.

    Applications should replace this scaffold with the relational permission
    resolver once permission atoms and groups have been seeded.
    """
    return {
        "backend": [],
        "ui": {
            "apps": [],
            "pages": [],
            "buttons": [],
            "actions": [],
            "query_filters": [],
        },
    }
