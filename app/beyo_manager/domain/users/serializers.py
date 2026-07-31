from datetime import datetime
from decimal import Decimal

from beyo_manager.domain.transitions.labels import (
    is_transition_reason,
    resolve_transition_reason_label,
)
from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.users.user_declared_state_record import (
    UserDeclaredStateRecord,
)
from beyo_manager.models.tables.users.user_shift_state_record import UserShiftStateRecord
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


def serialize_declared_state(
    record: UserDeclaredStateRecord,
    pause_reason: PauseReason,
) -> dict:
    return {
        "id": record.client_id,
        "pause_reason": {
            "id": pause_reason.client_id,
            "name": pause_reason.name,
            "image_url": pause_reason.image_url,
        },
        "description": record.description,
        "entered_at": record.entered_at.isoformat(),
    }


def _serialize_pause_reason_reference(pause_reason: PauseReason) -> dict:
    return {
        "id": pause_reason.client_id,
        "name": pause_reason.name,
        "image_url": pause_reason.image_url,
    }


def _serialize_transition_reason_reference(
    transition_reason: str, label: dict[str, str | None]
) -> dict:
    """Same three fields as a catalog reference, so the published shape is unchanged.

    `id` is the transition value itself — the same key the analytics `pause_by_reason`
    map uses, so a client resolves both kinds of key the same way.
    """
    return {
        "id": transition_reason,
        "name": label["name"],
        "image_url": label["image_url"],
    }


def pause_reason_reference_is_unresolved(
    current: UserShiftStateRecord,
    pause_reason: PauseReason | None,
) -> bool:
    """A `par_…` id in `reason` that no longer joins to a catalog row.

    A row typed by `transition_reason` is NOT unresolved — it resolves through the
    code-owned map instead, which is the whole point of the vocabulary. Such a row
    carries `reason IS NULL`, so it already falls out here; the explicit guard makes
    that intentional rather than accidental, and keeps holding if a future row ever
    carries both.
    """
    if is_transition_reason(current.transition_reason):
        return False
    return (
        current.state is UserShiftStateEnum.IN_PAUSE
        and pause_reason is None
        and current.reason is not None
        and current.reason.startswith(f"{PauseReason.CLIENT_ID_PREFIX}_")
    )


def serialize_current_worker_shift_state(
    *,
    user_id: str,
    current: UserShiftStateRecord | None,
    shift_started_at: datetime | None = None,
    pause_reason: PauseReason | None = None,
    declared_record: UserDeclaredStateRecord | None = None,
    declared_pause_reason: PauseReason | None = None,
) -> dict:
    if current is None:
        return {
            "user_id": user_id,
            "clocked_in": False,
            "shift_started_at": None,
            "state": None,
            "state_entered_at": None,
            "pause_reason": None,
            "declared_state": None,
        }

    is_paused = current.state is UserShiftStateEnum.IN_PAUSE
    # PRECEDENCE (criterion 13), asserted rather than incidental: a catalog reference
    # wins over `transition_reason`, which wins over free-text `reason_text`. A catalog
    # row means a human chose it, which is strictly more specific than a system-typed
    # transition. After phase 2 the two are mutually exclusive on this table, but
    # "shouldn't happen" is not a behaviour — this is the behaviour.
    transition_label = (
        resolve_transition_reason_label(current.transition_reason)
        if is_paused and pause_reason is None
        else None
    )
    data = {
        "user_id": user_id,
        "clocked_in": True,
        "shift_started_at": shift_started_at.isoformat() if shift_started_at else None,
        "state": current.state.value,
        "state_entered_at": current.entered_at.isoformat(),
        "pause_reason": (
            _serialize_pause_reason_reference(pause_reason)
            if is_paused and pause_reason is not None
            else _serialize_transition_reason_reference(
                current.transition_reason, transition_label
            )
            if transition_label is not None
            else None
        ),
        "declared_state": (
            serialize_declared_state(declared_record, declared_pause_reason)
            if declared_record is not None and declared_pause_reason is not None
            else None
        ),
    }
    if (
        is_paused
        and current.reason is not None
        and pause_reason is None
        and transition_label is None  # a typed transition outranks free text
    ):
        data["reason_text"] = (
            None
            if pause_reason_reference_is_unresolved(current, pause_reason)
            else current.reason
        )
    return data
