from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ServiceContext:
    """Carries identity and incoming data through every operation.

    Rules
    -----
    - identity   : decoded JWT claims dict from get_jwt_claims()
    - incoming_data: validated request payload (Pydantic .model_dump() or plain dict)
    - session    : the request-scoped AsyncSession from get_db()
    - Never add boolean flags or config values here
    """
    identity: dict
    incoming_data: dict
    session: AsyncSession
    query_params: dict = field(default_factory=dict)

    # ── convenience accessors (read from JWT claims) ──────────────────────
    @property
    def user_id(self) -> str:
        return self.identity.get("user_id", "")

    @property
    def username(self) -> str:
        return self.identity.get("username", "")

    @property
    def workspace_id(self) -> str:
        return self.identity.get("workspace_id", "")

    @property
    def workspace_role_id(self) -> str:
        return self.identity.get("workspace_role_id", "")

    @property
    def role_name(self) -> str:
        return self.identity.get("role_name", "")

    @property
    def backend_permissions(self) -> list[str]:
        return self.identity.get("backend_permissions", [])

    def has_permission(self, permission: str) -> bool:
        return permission in self.backend_permissions

    def require_permission(self, permission: str) -> None:
        from beyo_manager.errors.permissions import PermissionDenied
        if not self.has_permission(permission):
            raise PermissionDenied(
                f"Your role does not have the '{permission}' permission."
            )
