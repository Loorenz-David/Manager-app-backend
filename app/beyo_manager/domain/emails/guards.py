from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.routers.utils.roles import ADMIN, MANAGER


def assert_can_access_connection(
    ctx_user_id: str,
    ctx_role_name: str,
    connection_owner_user_id: str,
) -> None:
    if ctx_user_id == connection_owner_user_id:
        return
    if ctx_role_name in (ADMIN, MANAGER):
        return
    raise PermissionDenied("You do not have access to this email connection.")


def assert_can_send_from_connection(
    ctx_user_id: str,
    connection_owner_user_id: str,
) -> None:
    if ctx_user_id != connection_owner_user_id:
        raise PermissionDenied("You can only send from your own email connections.")


def is_connection_active(status: EmailConnectionStatusEnum | str) -> bool:
    value = status.value if isinstance(status, EmailConnectionStatusEnum) else status
    return value == EmailConnectionStatusEnum.ACTIVE.value
