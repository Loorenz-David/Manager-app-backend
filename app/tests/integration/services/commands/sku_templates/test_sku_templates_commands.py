import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.tasks.enums import TaskTypeEnum
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.sku_templates.sku_template import SkuTemplate
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.commands.bootstrap.phases.seed_sku_templates import seed_sku_templates
from beyo_manager.services.commands.sku_templates.create_sku_template import create_sku_template
from beyo_manager.services.commands.sku_templates.reserve_sku_scalar import reserve_sku_scalar
from beyo_manager.services.commands.sku_templates.update_sku_template import update_sku_template
from beyo_manager.services.context import ServiceContext


async def _seed_identity(db_session):
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"SKU workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"sku_user_{suffix}",
        email=f"sku_{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


def _ctx(session, workspace, user, incoming_data):
    return ServiceContext(
        identity={"workspace_id": workspace.client_id, "user_id": user.client_id},
        incoming_data=incoming_data,
        session=session,
    )


@pytest.mark.integration
async def test_create_update_conflict_and_reserve_monotonicity(db_session):
    workspace, user = await _seed_identity(db_session)
    ctx = _ctx(
        db_session,
        workspace,
        user,
        {
            "task_type": "pre_order",
            "prefix": "pre",
            "separator": "-",
            "initial_scalar": 6,
        },
    )

    created = await create_sku_template(ctx)
    assert created["prefix"] == "PRE"
    assert created["next_sku_preview"] == "PRE-7"

    with pytest.raises(ConflictError):
        await create_sku_template(ctx)

    ctx.incoming_data = {"client_id": created["client_id"], "prefix": "ORD"}
    updated = await update_sku_template(ctx)
    assert updated["prefix"] == "ORD"

    ctx.incoming_data = {"task_type": TaskTypeEnum.PRE_ORDER}
    first = await reserve_sku_scalar(ctx)
    second = await reserve_sku_scalar(ctx)
    assert [first["reserved_scalar"], second["reserved_scalar"]] == [7, 8]
    assert first["sku"] == "ORD-7"
    row = await db_session.scalar(select(SkuTemplate).where(SkuTemplate.client_id == created["client_id"]))
    assert row.last_scalar == 8


@pytest.mark.integration
async def test_update_rejects_lowering_last_scalar(db_session):
    workspace, user = await _seed_identity(db_session)
    ctx = _ctx(
        db_session,
        workspace,
        user,
        {"task_type": "pre_order", "prefix": "PRE", "initial_scalar": 6},
    )
    created = await create_sku_template(ctx)

    # Raising the counter is allowed.
    ctx.incoming_data = {"client_id": created["client_id"], "last_scalar": 10}
    raised = await update_sku_template(ctx)
    assert raised["last_scalar"] == 10

    # Lowering it below the current value would re-issue reserved scalars.
    ctx.incoming_data = {"client_id": created["client_id"], "last_scalar": 3}
    with pytest.raises(ValidationError):
        await update_sku_template(ctx)

    row = await db_session.scalar(select(SkuTemplate).where(SkuTemplate.client_id == created["client_id"]))
    assert row.last_scalar == 10


@pytest.mark.integration
async def test_concurrent_reserves_return_distinct_scalars(db_session):
    workspace, user = await _seed_identity(db_session)
    ctx = _ctx(db_session, workspace, user, {"task_type": "pre_order", "prefix": "PRE"})
    created = await create_sku_template(ctx)
    await db_session.commit()

    from beyo_manager.models.database import _session_factory

    async def _reserve():
        session = _session_factory()
        try:
            return await reserve_sku_scalar(
                _ctx(session, workspace, user, {"task_type": TaskTypeEnum.PRE_ORDER})
            )
        finally:
            await session.close()

    first, second = await asyncio.gather(_reserve(), _reserve())
    assert {first["reserved_scalar"], second["reserved_scalar"]} == {1, 2}
    row = await db_session.scalar(select(SkuTemplate).where(SkuTemplate.client_id == created["client_id"]))
    assert row.last_scalar == 2


@pytest.mark.integration
async def test_seed_sku_templates_is_idempotent_and_does_not_reset_counter(db_session):
    workspace, _ = await _seed_identity(db_session)

    first = await seed_sku_templates(db_session, workspace.client_id)
    row = await db_session.scalar(
        select(SkuTemplate).where(SkuTemplate.client_id == first[TaskTypeEnum.PRE_ORDER.value])
    )
    row.last_scalar = 9
    await db_session.flush()
    second = await seed_sku_templates(db_session, workspace.client_id)

    assert first == second
    assert row.prefix == "PRE_ORDER"
    assert row.pad_width == 0
    assert row.last_scalar == 9
