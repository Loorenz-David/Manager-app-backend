from datetime import datetime, timezone
from uuid import uuid4

from beyo_manager.domain.items.enums import ItemCurrencyEnum
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.services.queries.items.lookup.internal_db import InternalDbLookupHandler


async def _seed_workspace_and_user(db_session, token):
    workspace = Workspace(client_id=f"ws_{token}", name=f"Lookup {token}")
    user = User(client_id=f"usr_{token}", username=f"lookup_{token}", email=f"lookup_{token}@example.com", password="secret")
    db_session.add(workspace)
    await db_session.flush()
    db_session.add(user)
    await db_session.flush()
    return workspace, user


async def test_internal_db_lookup_returns_purchase_price_from_current_valuation(db_session):
    token = uuid4().hex[:10]
    workspace, user = await _seed_workspace_and_user(db_session, token)
    item = Item(client_id=f"itm_{token}", workspace_id=workspace.client_id, article_number="ART-1", created_by_id=user.client_id)
    db_session.add(item)
    await db_session.flush()

    old_valuation = ItemValuation(
        client_id=f"ival_old_{token}", workspace_id=workspace.client_id, item_id=item.client_id,
        purchase_cost_minor=50000, currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id,
    )
    db_session.add(old_valuation)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    old_valuation.superseded_at = now
    await db_session.flush()

    current_valuation = ItemValuation(
        client_id=f"ival_current_{token}", workspace_id=workspace.client_id, item_id=item.client_id,
        purchase_cost_minor=123456, currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id,
        created_at=now,
    )
    db_session.add(current_valuation)
    await db_session.flush()
    old_valuation.superseded_by_id = current_valuation.client_id
    await db_session.flush()

    result = await InternalDbLookupHandler().lookup("ART-1", None, db_session, workspace.client_id)

    assert result is not None
    assert result.purchase_price_minor == 123456


async def test_internal_db_lookup_returns_null_purchase_price_without_valuation(db_session):
    token = uuid4().hex[:10]
    workspace, user = await _seed_workspace_and_user(db_session, token)
    item = Item(client_id=f"itm_{token}", workspace_id=workspace.client_id, article_number="ART-2", created_by_id=user.client_id)
    db_session.add(item)
    await db_session.flush()

    result = await InternalDbLookupHandler().lookup("ART-2", None, db_session, workspace.client_id)

    assert result is not None
    assert result.purchase_price_minor is None


async def test_internal_db_lookup_ignores_superseded_valuation_purchase_price(db_session):
    token = uuid4().hex[:10]
    workspace, user = await _seed_workspace_and_user(db_session, token)
    item = Item(client_id=f"itm_{token}", workspace_id=workspace.client_id, article_number="ART-3", created_by_id=user.client_id)
    db_session.add(item)
    await db_session.flush()

    valuation = ItemValuation(
        client_id=f"ival_{token}", workspace_id=workspace.client_id, item_id=item.client_id,
        purchase_cost_minor=99900, currency=ItemCurrencyEnum.SWEDISH_KRONA, created_by_id=user.client_id,
    )
    db_session.add(valuation)
    await db_session.flush()
    valuation.superseded_at = valuation.created_at
    await db_session.flush()

    result = await InternalDbLookupHandler().lookup("ART-3", None, db_session, workspace.client_id)

    assert result is not None
    assert result.purchase_price_minor is None
