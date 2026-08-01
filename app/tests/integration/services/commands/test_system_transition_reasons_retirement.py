"""Phase 4 — retirement & constraints.

Three things this phase must get right, none of which a naive test catches:

1. The CHECK constraint must reject a step record carrying both explanations, and must NOT reject
   the derived declared-state row, which carries both **by design**. Real data contains zero
   instances of the second case, so it has to be constructed deliberately.
2. `pause_ended_shift` must remain selectable through the real endpoint. `list_pause_reasons`
   filters `is_deleted`, so a soft-delete would silently remove it from the worker's pause sheet.
3. `pause_case_created` and its historical references must be untouched.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason


pytestmark = pytest.mark.asyncio


async def _any_workspace_with_catalog(db_session) -> str:
    workspace_id = await db_session.scalar(
        select(PauseReason.workspace_id).where(PauseReason.is_deleted.is_(False)).limit(1)
    )
    assert workspace_id is not None, "no workspace holds a pause-reason catalog"
    return workspace_id


async def test_constraint_rejects_a_step_record_carrying_both_explanations(db_session):
    """T2, enforced by the database rather than by every future writer remembering."""
    workspace_id = await _any_workspace_with_catalog(db_session)
    step_id = await db_session.scalar(
        text("SELECT client_id FROM task_steps WHERE workspace_id = :w LIMIT 1"),
        {"w": workspace_id},
    )
    if step_id is None:
        pytest.skip("no task step in this workspace to attach a state record to")
    reason_id = await db_session.scalar(
        select(PauseReason.client_id).where(
            PauseReason.workspace_id == workspace_id,
            PauseReason.is_deleted.is_(False),
        ).limit(1)
    )

    with pytest.raises(Exception) as excinfo:
        await db_session.execute(
            text(
                """
                INSERT INTO step_state_records
                    (client_id, workspace_id, step_id, state, pause_reason_id,
                     transition_reason, entered_at, created_at, taken_from_average,
                     recorded_time_marked_wrong, is_deleted)
                VALUES
                    ('ssr_ck_probe_both', :w, :s, 'paused', :r,
                     :t, now(), now(), false, false, false)
                """
            ),
            {
                "w": workspace_id,
                "s": step_id,
                "r": reason_id,
                "t": TransitionReasonEnum.OTHER_TASK_PRIORITY.value,
            },
        )
    assert "ck_step_state_records_transition_xor_catalog" in str(excinfo.value)
    await db_session.rollback()


async def test_constraint_does_not_reject_the_declared_state_projection(db_session):
    """The one documented exception — and the reason the constraint is table-scoped.

    A declaration-sourced segment on `user_shift_state_records` carries
    `worker_declared_state` AND the catalog reason the worker chose. Both facts are true and both
    are wanted, so mutual exclusion is asserted on `step_state_records` only.

    Real data contains **zero** rows of this shape today, so a test seeded from production would
    pass while a constraint that wrongly covered both tables shipped.
    """
    workspace_id = await _any_workspace_with_catalog(db_session)
    user_id = await db_session.scalar(
        text("SELECT client_id FROM users LIMIT 1")
    )
    reason_id = await db_session.scalar(
        select(PauseReason.client_id).where(
            PauseReason.workspace_id == workspace_id,
            PauseReason.is_deleted.is_(False),
        ).limit(1)
    )
    entered = datetime.now(timezone.utc) - timedelta(days=365)

    await db_session.execute(
        text(
            """
            INSERT INTO user_shift_state_records
                (client_id, workspace_id, user_id, state, reason, transition_reason,
                 entered_at, exited_at, manually_recorded)
            VALUES
                ('uss_declared_probe', :w, :u, 'in_pause', :r, :t,
                 :entered, :exited, true)
            """
        ),
        {
            "w": workspace_id,
            "u": user_id,
            "r": reason_id,
            "t": TransitionReasonEnum.WORKER_DECLARED_STATE.value,
            "entered": entered,
            "exited": entered + timedelta(minutes=5),
        },
    )

    both = await db_session.scalar(
        text(
            "SELECT count(*) FROM user_shift_state_records "
            "WHERE client_id = 'uss_declared_probe' "
            "AND reason IS NOT NULL AND transition_reason IS NOT NULL"
        )
    )
    assert both == 1, "the declared-state projection must be able to carry both explanations"
    await db_session.rollback()


async def test_pause_ended_shift_is_still_selectable_through_the_endpoint(db_session):
    """It stays because a worker picks it, and `list_pause_reasons` filters `is_deleted`.

    Asserted through the query service rather than by reading the row, because the filter — not the
    row's existence — is what decides whether the pause sheet offers it.
    """
    from beyo_manager.services.queries.pause_reasons.list_pause_reasons import list_pause_reasons
    from beyo_manager.services.context import ServiceContext

    workspace_id = await _any_workspace_with_catalog(db_session)
    ctx = ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr_probe", "role_name": "manager"},
        incoming_data={},
        session=db_session,
    )

    result = await list_pause_reasons(ctx)
    slugs = {r.get("slug") for r in result["pause_reasons"]}

    assert "pause_ended_shift" in slugs, (
        "pause_ended_shift vanished from the picker. It is an ordinary worker-selectable reason "
        "and the pause sheet offers it; list_pause_reasons filters is_deleted, so soft-deleting "
        "the row removes the worker's ability to state that reason at all"
    )
    assert "pause_other_task_priority" not in slugs, (
        "the retired system row is still offered; nothing resolves it and nobody selects it"
    )


async def test_retirement_left_the_guarded_populations_alone(db_session):
    """`pause_case_created` is a stale value with 7 historical references phase 3 preserved."""
    anchor_refs = await db_session.scalar(
        text(
            "SELECT count(*) FROM step_state_records s "
            "JOIN pause_reasons p ON p.client_id = s.pause_reason_id "
            "WHERE p.slug = 'pause_case_created'"
        )
    )
    assert anchor_refs == 7, (
        f"expected the 7 preserved pause_case_created references, found {anchor_refs}"
    )

    ended_shift_refs = await db_session.scalar(
        text(
            "SELECT count(*) FROM step_state_records s "
            "JOIN pause_reasons p ON p.client_id = s.pause_reason_id "
            "WHERE p.slug = 'pause_ended_shift'"
        )
    )
    assert ended_shift_refs > 0, (
        "pause_ended_shift references disappeared — a worker's pick and a clock-out write were "
        "historically indistinguishable, so these are real worker choices"
    )


async def test_no_row_is_system_managed_any_more(db_session):
    """The flag is inert contract. Nothing sets it, nothing reads it for behaviour."""
    remaining = await db_session.scalar(
        text("SELECT count(*) FROM pause_reasons WHERE is_system_managed = true")
    )
    assert remaining == 0
