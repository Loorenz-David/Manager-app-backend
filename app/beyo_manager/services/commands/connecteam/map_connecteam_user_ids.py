"""Map canonical Connecteam CSV users to existing work profiles."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.core.logging.config import log_event
from beyo_manager.domain.connecteam.enums import ConnecteamUserMappingStatusEnum as Status
from beyo_manager.domain.connecteam.normalize_username import (
    build_external_full_name,
    normalize_username,
)
from beyo_manager.domain.connecteam.user_csv_rows import ConnecteamCsvUser
from beyo_manager.domain.connecteam.user_mapping_report import (
    ConnecteamUserMappingReport,
    ConnecteamUserMappingRow,
)
from beyo_manager.models.tables.users.user_work_profile import UserWorkProfile
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.queries.users.get_connecteam_mapping_candidates import (
    InternalConnecteamMappingCandidate,
    get_connecteam_mapping_candidates,
)

logger = logging.getLogger(__name__)


def _row(
    user: ConnecteamCsvUser,
    *,
    status: Status,
    full_name: str | None,
    normalized_name: str | None,
    candidate: InternalConnecteamMappingCandidate | None = None,
    detail: str | None = None,
) -> ConnecteamUserMappingRow:
    return ConnecteamUserMappingRow(
        user_id=user.user_id,
        first_name=user.first_name,
        last_name=user.last_name,
        external_full_name=full_name,
        normalized_external_name=normalized_name,
        internal_username=candidate.username if candidate else None,
        internal_user_id=candidate.user_id if candidate else None,
        user_work_profile_id=candidate.user_work_profile_id if candidate else None,
        workspace_id=candidate.workspace_id if candidate else None,
        existing_connecteam_user_id=(
            str(candidate.connecteam_user_id) if candidate and candidate.connecteam_user_id else None
        ),
        status=status,
        detail=detail,
        source_row_number=user.row_number,
    )


def _candidate_indexes(candidates: list[InternalConnecteamMappingCandidate]):
    by_name: dict[str, list[InternalConnecteamMappingCandidate]] = defaultdict(list)
    by_connecteam_id: dict[str, list[InternalConnecteamMappingCandidate]] = defaultdict(list)
    for candidate in candidates:
        by_name[normalize_username(candidate.username)].append(candidate)
        if candidate.connecteam_user_id is not None:
            by_connecteam_id[str(candidate.connecteam_user_id)].append(candidate)
    return by_name, by_connecteam_id


async def map_connecteam_user_ids(
    session: AsyncSession,
    *,
    csv_users: list[ConnecteamCsvUser],
    apply: bool,
    workspace_id: str | None,
) -> ConnecteamUserMappingReport:
    """Classify every CSV row and optionally apply conflict-free proposals."""

    caller_had_transaction = session.in_transaction()
    log_event(
        "connecteam_user_mapping_started",
        provider="connecteam",
        workspace_id=workspace_id or "all",
        apply=apply,
        user_count=len(csv_users),
    )

    names: list[tuple[ConnecteamCsvUser, str | None, str | None]] = []
    by_normalized_name: dict[str, list[ConnecteamCsvUser]] = defaultdict(list)
    for user in csv_users:
        full_name = build_external_full_name(user.first_name, user.last_name)
        normalized_name = normalize_username(full_name) if full_name is not None else None
        names.append((user, full_name, normalized_name))
        if normalized_name is not None:
            by_normalized_name[normalized_name].append(user)

    candidates = await get_connecteam_mapping_candidates(session, workspace_id=workspace_id)
    by_name, by_connecteam_id = _candidate_indexes(candidates)
    rows: list[ConnecteamUserMappingRow] = []
    proposed_rows: list[ConnecteamUserMappingRow] = []
    proposed_ids: dict[str, ConnecteamUserMappingRow] = {}
    csv_user_id_counts: dict[int, int] = defaultdict(int)
    for user in csv_users:
        csv_user_id_counts[user.user_id] += 1

    for user, full_name, normalized_name in names:
        if csv_user_id_counts[user.user_id] > 1:
            rows.append(
                _row(
                    user,
                    status=Status.DUPLICATE_EXTERNAL_FULL_NAME,
                    full_name=full_name,
                    normalized_name=normalized_name,
                    detail="duplicate Connecteam userId rows in CSV were not applied",
                )
            )
            continue
        if normalized_name is None:
            rows.append(
                _row(
                    user,
                    status=Status.INVALID_EXTERNAL_NAME,
                    full_name=None,
                    normalized_name=None,
                    detail="firstName and lastName are both empty",
                )
            )
            continue
        if len(by_normalized_name[normalized_name]) > 1:
            rows.append(
                _row(
                    user,
                    status=Status.DUPLICATE_EXTERNAL_FULL_NAME,
                    full_name=full_name,
                    normalized_name=normalized_name,
                    detail="multiple CSV users have the same normalized full name",
                )
            )
            continue

        matching_candidates = by_name.get(normalized_name, [])
        if not matching_candidates:
            rows.append(
                _row(
                    user,
                    status=Status.EXTERNAL_USER_UNMATCHED,
                    full_name=full_name,
                    normalized_name=normalized_name,
                    detail="no users.username matched exactly after normalization",
                )
            )
            log_event("connecteam_user_unmatched", provider="connecteam")
            continue
        if len(matching_candidates) > 1:
            rows.append(
                _row(
                    user,
                    status=Status.WORK_PROFILE_AMBIGUOUS,
                    full_name=full_name,
                    normalized_name=normalized_name,
                    candidate=matching_candidates[0],
                    detail="multiple eligible work profiles or normalized usernames matched",
                )
            )
            continue

        candidate = matching_candidates[0]
        if candidate.user_work_profile_id is None:
            rows.append(
                _row(
                    user,
                    status=Status.WORK_PROFILE_NOT_FOUND,
                    full_name=full_name,
                    normalized_name=normalized_name,
                    candidate=candidate,
                    detail="matched user has no eligible work profile",
                )
            )
            continue

        proposed_id = str(user.user_id)
        assigned_rows = by_connecteam_id.get(proposed_id, [])
        if any(existing.user_work_profile_id != candidate.user_work_profile_id for existing in assigned_rows):
            rows.append(
                _row(
                    user,
                    status=Status.CONNECTEAM_ID_ALREADY_ASSIGNED,
                    full_name=full_name,
                    normalized_name=normalized_name,
                    candidate=candidate,
                    detail="Connecteam ID is already assigned to another work profile",
                )
            )
            continue
        if proposed_id in proposed_ids and proposed_ids[proposed_id].user_work_profile_id != candidate.user_work_profile_id:
            rows.append(
                _row(
                    user,
                    status=Status.CONNECTEAM_ID_ALREADY_ASSIGNED,
                    full_name=full_name,
                    normalized_name=normalized_name,
                    candidate=candidate,
                    detail="Connecteam ID is proposed for another work profile in this run",
                )
            )
            continue
        if candidate.connecteam_user_id is not None:
            current_id = str(candidate.connecteam_user_id)
            if current_id == proposed_id:
                rows.append(
                    _row(
                        user,
                        status=Status.ALREADY_MAPPED_SAME_ID,
                        full_name=full_name,
                        normalized_name=normalized_name,
                        candidate=candidate,
                    )
                )
            else:
                rows.append(
                    _row(
                        user,
                        status=Status.EXISTING_DIFFERENT_CONNECTEAM_ID,
                        full_name=full_name,
                        normalized_name=normalized_name,
                        candidate=candidate,
                        detail="existing Connecteam ID will never be overwritten",
                    )
                )
            continue

        proposed = _row(
            user,
            status=Status.PROPOSED,
            full_name=full_name,
            normalized_name=normalized_name,
            candidate=candidate,
        )
        rows.append(proposed)
        proposed_rows.append(proposed)
        proposed_ids[proposed_id] = proposed
        log_event("connecteam_user_mapping_proposed", provider="connecteam")

    report = ConnecteamUserMappingReport(
        rows=tuple(rows),
        workspace_id=workspace_id,
        dry_run=not apply,
        applied=False,
    )
    already_mapped_count = sum(
        row.status is Status.ALREADY_MAPPED_SAME_ID for row in report.rows
    )
    if already_mapped_count:
        log_event(
            "connecteam_user_already_mapped",
            provider="connecteam",
            count=already_mapped_count,
        )
    if not apply or report.identity_conflicts_present or not proposed_rows:
        if report.identity_conflicts_present:
            log_event("connecteam_user_mapping_conflict", provider="connecteam")
        return report

    # The initial candidate SELECT opens a read transaction. Only end it here when
    # this command owns the session; a caller-owned transaction must remain intact.
    if not caller_had_transaction:
        await session.rollback()

    async with maybe_begin(session):
        profile_ids = [row.user_work_profile_id for row in proposed_rows]
        profiles = (
            await session.execute(
                select(UserWorkProfile).where(UserWorkProfile.client_id.in_(profile_ids))
            )
        ).scalars().all()
        profiles_by_id = {profile.client_id: profile for profile in profiles}
        for row in proposed_rows:
            profile = profiles_by_id.get(row.user_work_profile_id)
            if profile is None:
                raise RuntimeError("A proposed user work profile disappeared before mapping.")
            if profile.connecteam_user_id is not None and str(profile.connecteam_user_id) != str(row.user_id):
                raise RuntimeError("A proposed user work profile received a different mapping before apply.")
            profile.connecteam_user_id = str(row.user_id)
        await session.flush()

    updated_rows = tuple(
        replace(row, status=Status.UPDATED) if row.status is Status.PROPOSED else row
        for row in rows
    )
    log_event("connecteam_user_mapping_committed", provider="connecteam", updated_count=len(proposed_rows))
    return ConnecteamUserMappingReport(
        rows=updated_rows,
        workspace_id=workspace_id,
        dry_run=False,
        applied=True,
    )
