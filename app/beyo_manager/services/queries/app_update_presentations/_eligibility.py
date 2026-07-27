"""Shared eligibility + newest-version reduction for consumer read queries."""

from beyo_manager.domain.app_update_presentations.audience_rules import (
    presentation_matches_context,
)
from beyo_manager.models.tables.app_update_presentations.presentation import (
    AppUpdatePresentation,
)
from beyo_manager.services.context import ServiceContext


def is_eligible(ctx: ServiceContext, presentation: AppUpdatePresentation, app_key: str) -> bool:
    return presentation_matches_context(
        audience_mode=presentation.audience_mode,
        app_targets={t.app_key.value for t in presentation.app_targets},
        role_targets={t.role_key.value for t in presentation.role_targets},
        workspace_targets={t.workspace_id for t in presentation.workspace_targets},
        user_targets={t.user_id for t in presentation.user_targets},
        app_key=app_key,
        workspace_id=ctx.workspace_id,
        role_name=ctx.role_name,
        user_id=ctx.user_id,
    )


def newest_version_per_logical(
    presentations: list[AppUpdatePresentation],
) -> list[AppUpdatePresentation]:
    """Reduce to the highest ``version`` per ``logical_client_id``.

    This is the newest-version-wins rule: within one announcement, only the
    latest version a user is eligible for is servable; older versions are
    superseded.
    """
    winners: dict[str, AppUpdatePresentation] = {}
    for presentation in presentations:
        current = winners.get(presentation.logical_client_id)
        if current is None or presentation.version > current.version:
            winners[presentation.logical_client_id] = presentation
    return list(winners.values())
