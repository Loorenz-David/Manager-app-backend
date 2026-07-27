"""Audience-mode validation and target-matching semantics. Pure, no I/O.

Matching semantics (applied consistently):
- Within one target dimension, values use OR.
- Across dimensions, restrictions use AND.
- An empty target dimension means "unrestricted" for that dimension.

``all_matching``      -> app AND workspace AND role AND (direct user, if any user targets).
``selected_users_only`` -> the acting user MUST be directly targeted, AND app AND
                          workspace. Role targets are ignored in this mode.
"""

from beyo_manager.domain.app_update_presentations.enums import AudienceModeEnum
from beyo_manager.errors.validation import ValidationError


def validate_audience_mode(mode: AudienceModeEnum, user_target_count: int) -> None:
    """``selected_users_only`` requires at least one direct user target."""
    if mode == AudienceModeEnum.SELECTED_USERS_ONLY and user_target_count < 1:
        raise ValidationError(
            "A 'selected_users_only' presentation must target at least one user."
        )


def presentation_matches_context(
    *,
    audience_mode: AudienceModeEnum,
    app_targets: set[str],
    role_targets: set[str],
    workspace_targets: set[str],
    user_targets: set[str],
    app_key: str,
    workspace_id: str,
    role_name: str,
    user_id: str,
) -> bool:
    app_ok = not app_targets or app_key in app_targets
    workspace_ok = not workspace_targets or workspace_id in workspace_targets

    if audience_mode == AudienceModeEnum.SELECTED_USERS_ONLY:
        # Direct targeting is required; role targets are ignored.
        return app_ok and workspace_ok and user_id in user_targets

    role_ok = not role_targets or role_name in role_targets
    user_ok = not user_targets or user_id in user_targets
    return app_ok and workspace_ok and role_ok and user_ok
