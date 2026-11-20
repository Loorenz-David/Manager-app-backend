import re

import pytest
from sqlalchemy.dialects import postgresql

from beyo_manager.domain.items.sku_prefixes import (
    ITEM_CATEGORY_SKU_PREFIXES,
    next_sku_sequence,
    sku_sequence_pattern,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.items.suggest_item_sku import suggest_item_sku


def test_prefixes_do_not_collide_case_insensitively():
    lowered = [prefix.lower() for prefix in ITEM_CATEGORY_SKU_PREFIXES.values()]
    assert len(lowered) == len(set(lowered))


def test_first_sku_of_the_day_is_one():
    assert next_sku_sequence([], "T", "201126") == 1


def test_counts_mixed_case_and_missing_dash():
    skus = ["CH3-201126", "Ch5-201126", "ch2201126"]
    assert next_sku_sequence(skus, "Ch", "201126") == 6
    assert next_sku_sequence(["Bsh9201126"], "Bsh", "201126") == 10


def test_ignores_other_days_and_longer_prefixes():
    skus = ["Sd7-191126", "Sdt3-201126", "Sd2-201126", "XSd9-201126", "Sd4-2011260", None, ""]
    assert next_sku_sequence(skus, "Sd", "201126") == 3
    assert next_sku_sequence(["Chd4-201126"], "Ch", "201126") == 1


def test_pattern_renders_as_case_insensitive_postgres_regex():
    from beyo_manager.models.tables.items.item import Item

    clause = Item.sku.regexp_match(sku_sequence_pattern("T", "201126"), flags="i")
    sql = str(clause.compile(dialect=postgresql.dialect()))
    assert "~*" in sql
    assert re.match(sku_sequence_pattern("T", "201126"), "T12-201126")


class _FakeSession:
    def __init__(self, category_name, skus):
        self.category_name = category_name
        self.skus = skus

    async def scalar(self, _stmt):
        return self.category_name

    async def scalars(self, _stmt):
        return iter(self.skus)


def _ctx(session, **query_params):
    return ServiceContext(
        incoming_data={},
        query_params=query_params,
        identity={"workspace_id": "ws-1", "user_id": "u-1"},
        session=session,
    )


async def test_suggests_next_sku_for_mapped_category():
    session = _FakeSession("Dining Tables", ["T1-201126", "t2-201126"])
    result = await suggest_item_sku(_ctx(session, item_category_id="itc-1", date_code="201126"))
    assert result == {"sku": "T3-201126", "prefix": "T", "sequence": 3}


async def test_unmapped_category_gets_no_suggestion():
    session = _FakeSession("Brand New Category", [])
    result = await suggest_item_sku(_ctx(session, item_category_id="itc-1", date_code="201126"))
    assert result == {"sku": None, "prefix": None, "sequence": None}


async def test_unknown_category_is_not_found():
    session = _FakeSession(None, [])
    with pytest.raises(NotFound):
        await suggest_item_sku(_ctx(session, item_category_id="itc-x", date_code="201126"))


@pytest.mark.parametrize("date_code", ["", "20112", "2011266", "20-11-26"])
async def test_rejects_bad_date_code(date_code):
    session = _FakeSession("Dining Tables", [])
    with pytest.raises(ValidationError):
        await suggest_item_sku(_ctx(session, item_category_id="itc-1", date_code=date_code))
