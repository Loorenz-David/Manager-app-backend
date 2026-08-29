"""The purchase API backfill writes properties through the production write path.

_apply_properties owns no snapshot logic of its own: it re-checks that the row
still looks the way planning saw it, then hands the blob to
apply_properties_snapshot — the single owner of the three snapshot columns, and
the same helper the three creation endpoints use. These tests pin that the blob,
its derived signature and the snapshot timestamp always move together, and that
a row which changed under the run is left alone.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from beyo_manager.domain.items.properties_signature import compute_properties_signature
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from scripts.purchase_api.backfill_from_purchase_api import (
    ACTION_UPDATE,
    APPLY_APPLIED,
    APPLY_DRIFTED,
    FIELD_PROPERTIES,
    Lookup,
    _apply_properties,
    decide,
    snapshot_item,
)

ENCODED_ATTRIBUTES = (
    '[{"key":"upholstery","label":"Upholstery","value":"Down"},'
    '{"key":"wood_type","label":"Type of Wood","value":"Teak"}]'
)
PARSED_ATTRIBUTES = {"upholstery": "Down", "wood_type": "Teak"}
ESTABLISHED = datetime(2026, 8, 1, tzinfo=timezone.utc)


async def _seed(db_session) -> tuple[Workspace, User]:
    suffix = uuid4().hex[:8]
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"Workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.com",
        password="secret",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


async def _seed_item(db_session, workspace, user, **kwargs) -> Item:
    item = Item(
        workspace_id=workspace.client_id,
        article_number=f"ART-{uuid4().hex[:8]}",
        created_by_id=user.client_id,
        **kwargs,
    )
    db_session.add(item)
    await db_session.flush()
    return item


def _identity(workspace, user) -> dict:
    return {
        "workspace_id": workspace.client_id,
        "user_id": user.client_id,
        "username": user.username,
    }


def _properties_plan(item: Item, attributes=ENCODED_ATTRIBUTES):
    """Plan this item exactly the way a real run would, then take the properties plan."""
    lookup = Lookup(
        status="ok",
        data={
            "article_number": item.article_number,
            "purchase_price": 100,
            "currency": "SEK",
            "attributes": attributes,
        },
    )
    plans = decide(item=snapshot_item(item, None), lookup=lookup)
    return next(plan for plan in plans if plan.field_name == FIELD_PROPERTIES)


async def _reload(db_session, client_id: str) -> Item:
    """Read the row back from the database, not from the identity map.

    _apply_properties only mutates the ORM object; in a real run its caller
    _apply_one owns the transaction and commits it. Here the fixture owns the
    transaction, so the flush has to be explicit, and it has to come before the
    refresh, which would otherwise discard the pending change.
    """
    await db_session.flush()
    item = await db_session.scalar(select(Item).where(Item.client_id == client_id))
    await db_session.refresh(item)
    return item


@pytest.mark.integration
async def test_a_first_snapshot_writes_the_blob_its_signature_and_the_timestamp(db_session):
    workspace, user = await _seed(db_session)
    item = await _seed_item(db_session, workspace, user)
    plan = _properties_plan(item)
    assert plan.action == ACTION_UPDATE

    result = await _apply_properties(db_session, _identity(workspace, user), plan)

    assert result == APPLY_APPLIED
    written = await _reload(db_session, item.client_id)
    assert written.properties == PARSED_ATTRIBUTES
    assert written.properties_signature == compute_properties_signature(PARSED_ATTRIBUTES)
    assert written.properties_snapshot_at is not None
    assert written.updated_by_id == user.client_id


@pytest.mark.integration
async def test_the_stored_signature_always_describes_the_stored_blob(db_session):
    """The narrowing tier reads the signature alone, so a divergence is silent."""
    workspace, user = await _seed(db_session)
    item = await _seed_item(db_session, workspace, user)

    await _apply_properties(db_session, _identity(workspace, user), _properties_plan(item))

    written = await _reload(db_session, item.client_id)
    assert written.properties_signature == compute_properties_signature(written.properties)


@pytest.mark.integration
async def test_a_new_profile_replaces_the_old_one_and_moves_the_snapshot_time(db_session):
    workspace, user = await _seed(db_session)
    stored = {"wood_type": "Oak"}
    item = await _seed_item(
        db_session,
        workspace,
        user,
        properties=stored,
        properties_signature=compute_properties_signature(stored),
        properties_snapshot_at=ESTABLISHED,
    )

    plan = _properties_plan(item)
    assert plan.reason == "profile_changed"
    result = await _apply_properties(db_session, _identity(workspace, user), plan)

    assert result == APPLY_APPLIED
    written = await _reload(db_session, item.client_id)
    assert written.properties == PARSED_ATTRIBUTES
    assert written.properties_snapshot_at > ESTABLISHED


@pytest.mark.integration
async def test_a_row_that_changed_since_planning_is_left_alone(db_session):
    workspace, user = await _seed(db_session)
    item = await _seed_item(db_session, workspace, user)
    plan = _properties_plan(item)

    # Somebody else snapshots the item between planning and writing.
    interloper = {"wood_type": "Walnut"}
    item.properties = interloper
    item.properties_signature = compute_properties_signature(interloper)
    item.properties_snapshot_at = ESTABLISHED
    await db_session.flush()

    result = await _apply_properties(db_session, _identity(workspace, user), plan)

    assert result == APPLY_DRIFTED
    written = await _reload(db_session, item.client_id)
    assert written.properties == interloper
    assert written.properties_snapshot_at == ESTABLISHED


@pytest.mark.integration
async def test_an_item_in_another_workspace_is_never_touched(db_session):
    workspace, user = await _seed(db_session)
    other_workspace, other_user = await _seed(db_session)
    item = await _seed_item(db_session, workspace, user)
    plan = _properties_plan(item)

    result = await _apply_properties(db_session, _identity(other_workspace, other_user), plan)

    assert result == APPLY_DRIFTED
    written = await _reload(db_session, item.client_id)
    assert written.properties is None


@pytest.mark.integration
async def test_a_deleted_item_is_never_touched(db_session):
    workspace, user = await _seed(db_session)
    item = await _seed_item(db_session, workspace, user)
    plan = _properties_plan(item)
    item.is_deleted = True
    await db_session.flush()

    result = await _apply_properties(db_session, _identity(workspace, user), plan)

    assert result == APPLY_DRIFTED
    written = await _reload(db_session, item.client_id)
    assert written.properties is None
