from decimal import Decimal

from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile


def _serialize_decimal_4(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value:.4f}"


def serialize_user_work_profile(uwp: UserWorkProfile) -> dict:
    return {
        "salary_per_hour_before_tax": _serialize_decimal_4(uwp.salary_per_hour_before_tax),
        "salary_per_hour_after_tax": _serialize_decimal_4(uwp.salary_per_hour_after_tax),
    }


def serialize_user_profile(user: User, work_profile: UserWorkProfile | None = None) -> dict:
    data = {
        "client_id": user.client_id,
        "username": user.username,
        "email": user.email,
        "phone_number": user.phone_number,
        "profile_picture": user.profile_picture,
        "languages": user.languages,
        "language_preference": user.language_preference,
        "online": user.online,
        "created_at": user.created_at.isoformat(),
    }
    if work_profile is not None:
        data["work_profile"] = serialize_user_work_profile(work_profile)
    return data


def serialize_user_list_item(
    user: User,
    role_client_id: str,
    role_name: str,
    workspace_role_client_id: str,
    workspace_role_name: str,
    working_sections: list[dict],
) -> dict:
    return {
        "client_id": user.client_id,
        "username": user.username,
        "email": user.email,
        "phone_number": user.phone_number,
        "profile_picture": user.profile_picture,
        "role": {
            "client_id": role_client_id,
            "name": role_name,
        },
        "workspace_role": {
            "client_id": workspace_role_client_id,
            "name": workspace_role_name,
        },
        "working_sections": working_sections,
    }


def serialize_user_working_section_member(user: User) -> dict:
    return {
        "client_id": user.client_id,
        "username": user.username,
        "profile_picture": user.profile_picture,
    }


def serialize_user_worker_stat(user: User) -> dict:
    return {
        "client_id": user.client_id,
        "username": user.username,
        "profile_picture": user.profile_picture,
        "last_online": user.last_online.isoformat() if user.last_online else None,
    }


def serialize_user_compact_with_role(
    user: User,
    role_client_id: str,
    role_name: str,
    workspace_role_client_id: str,
    workspace_role_name: str,
) -> dict:
    return {
        "client_id": user.client_id,
        "username": user.username,
        "profile_picture": user.profile_picture,
        "role": {
            "client_id": role_client_id,
            "name": role_name,
        },
        "workspace_role": {
            "client_id": workspace_role_client_id,
            "name": workspace_role_name,
        },
    }
