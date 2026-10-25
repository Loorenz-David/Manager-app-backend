"""update_item refuses an article_number/sku already used by another active item.

Both columns carry a partial unique index (`uix_items_workspace_article_number`,
`uix_items_workspace_sku`); without the pre-check the write reached the index and
surfaced as an IntegrityError — a generic 500 instead of a 409.
"""

import pytest

from beyo_manager.errors.validation import ConflictError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.services.commands.items.update_item import update_item
from tests.helpers.stock_report import make_ctx, seed_stock_report_workspace

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def _other_item(db_session, seeded, **fields):
    other = Item(
        client_id=f"{seeded.item.client_id}_other",
        workspace_id=seeded.workspace.client_id,
        quantity=1,
        **fields,
    )
    db_session.add(other)
    await db_session.flush()
    return other


async def _update_item(db_session, seeded, **fields):
    ctx = make_ctx(
        db_session,
        seeded,
        incoming_data={"client_id": seeded.item.client_id, **fields},
    )
    return await update_item(ctx)


@pytest.mark.parametrize("field", ["article_number", "sku"])
async def test_duplicate_of_active_item_is_refused(db_session, field):
    seeded = await seed_stock_report_workspace(db_session)
    await _other_item(db_session, seeded, **{field: "DUP-1"})
    before = getattr(seeded.item, field)

    with pytest.raises(ConflictError):
        await _update_item(db_session, seeded, **{field: "DUP-1"})

    assert getattr(await db_session.get(Item, seeded.item.client_id), field) == before


@pytest.mark.parametrize("field", ["article_number", "sku"])
async def test_value_of_deleted_item_is_accepted(db_session, field):
    seeded = await seed_stock_report_workspace(db_session)
    await _other_item(db_session, seeded, is_deleted=True, **{field: "DUP-1"})

    await _update_item(db_session, seeded, **{field: "DUP-1"})

    assert getattr(await db_session.get(Item, seeded.item.client_id), field) == "DUP-1"


async def test_resending_own_article_number_is_accepted(db_session):
    seeded = await seed_stock_report_workspace(db_session)

    await _update_item(db_session, seeded, article_number=seeded.item.article_number, designer="x")

    assert (await db_session.get(Item, seeded.item.client_id)).designer == "x"
