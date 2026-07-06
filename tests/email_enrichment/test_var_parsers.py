from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from beyo_manager.domain.tasks.enums import (
    TaskFulfillmentMethodEnum,
    TaskStateEnum,
    TaskTypeEnum,
)
from beyo_manager.services.infra.email_enrichment.context import EnrichmentContext
from beyo_manager.services.infra.email_enrichment.var_parsers.customer_parsers import (
    parse_customer_address,
    parse_customer_email,
    parse_customer_name,
    parse_customer_phone,
)
from beyo_manager.services.infra.email_enrichment.var_parsers.item_parsers import (
    parse_item_article_number,
    parse_item_category,
    parse_item_sku,
)
from beyo_manager.services.infra.email_enrichment.var_parsers.task_parsers import (
    _SWEDISH_WEEKDAYS,
    parse_task_fulfillment_method,
    parse_task_scheduled_time,
    parse_task_state,
    parse_task_type,
)


def test_customer_parsers_cover_all_supported_fields() -> None:
    customer = SimpleNamespace(
        display_name="Alice Andersson",
        primary_email="alice@example.com",
        primary_phone_number="+46701234567",
        address={"street": "Storgatan 1", "city": "Stockholm"},
    )
    context = EnrichmentContext(customer=customer)

    assert parse_customer_name(context) == "Alice Andersson"
    assert parse_customer_email(context) == "alice@example.com"
    assert parse_customer_phone(context) == "+46701234567"
    assert parse_customer_address(context) == "Storgatan 1, Stockholm"
    assert parse_customer_name(EnrichmentContext()) == ""


def test_task_parsers_cover_enum_and_schedule_formatting() -> None:
    current_year = datetime.now(timezone.utc).year
    start = datetime(current_year, 7, 4, tzinfo=timezone.utc)
    end = datetime(current_year, 7, 5, tzinfo=timezone.utc)
    next_year_dt = datetime(current_year + 1, 1, 2, tzinfo=timezone.utc)
    task = SimpleNamespace(
        task_type=TaskTypeEnum.PRE_ORDER,
        fulfillment_method=TaskFulfillmentMethodEnum.PICKUP_AT_STORE,
        state=TaskStateEnum.WORKING,
        scheduled_start_at=start,
        scheduled_end_at=end,
    )

    start_day = _SWEDISH_WEEKDAYS[start.weekday()]
    end_day = _SWEDISH_WEEKDAYS[end.weekday()]
    next_year_day = _SWEDISH_WEEKDAYS[next_year_dt.weekday()]

    assert parse_task_type(EnrichmentContext(task=task)) == "Pre Order"
    assert parse_task_fulfillment_method(EnrichmentContext(task=task)) == "Pickup At Store"
    assert parse_task_state(EnrichmentContext(task=task)) == "Working"
    assert parse_task_scheduled_time(EnrichmentContext()) == ""
    assert parse_task_scheduled_time(
        EnrichmentContext(
            task=SimpleNamespace(
                scheduled_start_at=None,
                scheduled_end_at=None,
            )
        )
    ) == "—"
    assert parse_task_scheduled_time(
        EnrichmentContext(
            task=SimpleNamespace(
                scheduled_start_at=start,
                scheduled_end_at=start,
            )
        )
    ) == f"Juli, {start_day} 4"
    assert parse_task_scheduled_time(EnrichmentContext(task=task)) == f"Juli, {start_day} 4 → Juli, {end_day} 5"
    assert parse_task_scheduled_time(
        EnrichmentContext(
            task=SimpleNamespace(
                scheduled_start_at=next_year_dt,
                scheduled_end_at=next_year_dt,
            )
        )
    ) == f"{current_year + 1} Januari, {next_year_day} 2"


def test_item_parsers_cover_value_and_empty_fallbacks() -> None:
    item = SimpleNamespace(article_number="ART-1", sku="SKU-1")
    category = SimpleNamespace(name="Sofas")
    context = EnrichmentContext(item=item, item_category=category)

    assert parse_item_article_number(context) == "ART-1"
    assert parse_item_sku(context) == "SKU-1"
    assert parse_item_category(context) == "Sofas"
    assert parse_item_article_number(EnrichmentContext()) == ""
    assert parse_item_category(EnrichmentContext(item=item)) == ""
