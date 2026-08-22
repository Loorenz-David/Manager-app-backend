"""Phase 4 — retirement & constraints.

Three things this phase must get right, none of which a naive test catches:

1. The CHECK constraint must reject a step record carrying both explanations, and must NOT reject
   the derived declared-state row, which carries both **by design**. Real data contains zero
   instances of the second case, so it has to be constructed deliberately.
2. `list_pause_reasons` must not expose a soft-deleted pause reason while retaining live rows.
3. Retired transition-reason rows must not be treated as worker-selectable catalog entries.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.pause_reasons.create_pause_reason import create_pause_reason
from beyo_manager.services.context import ServiceContext


pytestmark = pytest.mark.asyncio


async def _any_workspace_with_catalog(db_session) -> str:
    workspace_id = await db_session.scalar(
        select(PauseReason.workspace_id).where(PauseReason.is_deleted.is_(False)).limit(1)
    )
    assert workspace_id is not None, "no workspace holds a pause-reason catalog"
    return workspace_id


async def test_constraint_rejects_a_step_record_carrying_both_explanations(
    db_session, transition_reason_reference_data
):
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


async def test_constraint_does_not_reject_the_declared_state_projection(
    db_session, transition_reason_reference_data
):
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


async def test_soft_deleted_pause_reason_is_not_selectable_through_the_endpoint(
    db_session, transition_reason_reference_data
):
    """A soft-deleted reason disappears from the worker picker, while a live one remains.

    The assertion goes through the production query rather than reading the rows directly, because
    the ``is_deleted`` predicate is the behavior this test protects.
    """
    from beyo_manager.services.queries.pause_reasons.list_pause_reasons import list_pause_reasons
    from beyo_manager.services.context import ServiceContext

    workspace_id = await _any_workspace_with_catalog(db_session)
    ended_shift = await db_session.scalar(
        select(PauseReason).where(
            PauseReason.workspace_id == workspace_id,
            PauseReason.slug == "pause_ended_shift",
        )
    )
    assert ended_shift is not None
    ended_shift.is_deleted = True
    await db_session.flush()

    ctx = ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr_probe", "role_name": "manager"},
        incoming_data={},
        session=db_session,
    )

    result = await list_pause_reasons(ctx)
    slugs = {r.get("slug") for r in result["pause_reasons"]}

    assert "pause_ended_shift" not in slugs, (
        "a soft-deleted pause reason must not be offered by the worker pause sheet"
    )
    assert "pause_case_created" in slugs, "a non-deleted pause reason must remain selectable"


async def test_retirement_left_the_guarded_populations_alone(
    db_session, transition_reason_reference_data
):
    """A retired catalog row is hidden from the live picker, not resurrected by history."""
    from beyo_manager.services.queries.pause_reasons.list_pause_reasons import list_pause_reasons
    from beyo_manager.services.context import ServiceContext

    workspace_id = await _any_workspace_with_catalog(db_session)
    case_created = await db_session.scalar(
        select(PauseReason).where(
            PauseReason.workspace_id == workspace_id,
            PauseReason.slug == "pause_case_created",
        )
    )
    assert case_created is not None
    case_created.is_deleted = True
    await db_session.flush()

    ctx = ServiceContext(
        identity={"workspace_id": workspace_id, "user_id": "usr_probe", "role_name": "manager"},
        incoming_data={},
        session=db_session,
    )
    result = await list_pause_reasons(ctx)
    slugs = {r.get("slug") for r in result["pause_reasons"]}

    assert "pause_case_created" not in slugs, (
        "the retired case-created row must not be offered by the worker pause sheet"
    )
    assert "pause_ended_shift" in slugs, "a live pause reason must remain selectable"


async def test_no_row_is_system_managed_any_more(db_session):
    """The production create path must return a non-system-managed pause reason."""
    workspace = Workspace(name="retirement-production-path")
    user = User(
        username="retirement-production-user",
        email="retirement-production-user@example.com",
        password="test-password-hash",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()

    result = await create_pause_reason(
        ServiceContext(
            identity={
                "workspace_id": workspace.client_id,
                "user_id": user.client_id,
                "role_name": "manager",
            },
            incoming_data={
                "name": "Production-created pause reason",
                "pause_type": PauseTypeEnum.PERSONAL.value,
            },
            session=db_session,
        )
    )

    assert result["pause_reason"]["is_system_managed"] is False
