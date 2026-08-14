"""migrate legacy item money into item valuations with a reversible journal.

The pre-flight is deliberately report-first: no journal or valuation write is
allowed when legacy data is missing currency, negative, or unattributed.
"""

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from beyo_manager.models.base.identity import generate_id


revision: str = "5420acc6a7b3"
down_revision: Union[str, None] = "5caae620088c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JOURNAL = "item_valuation_migration_journal"
_LEGACY_AMOUNT = "(i.item_value_minor IS NOT NULL OR i.item_cost_minor IS NOT NULL)"
_NON_NEGATIVE_AMOUNTS = """
    (i.item_value_minor IS NULL OR i.item_value_minor >= 0)
    AND (i.item_cost_minor IS NULL OR i.item_cost_minor >= 0)
"""
_NO_VALUATION = """
    NOT EXISTS (
        SELECT 1
        FROM item_valuations existing_valuation
        WHERE existing_valuation.item_id = i.client_id
    )
"""


def _offending_ids(bind, predicate: str) -> list[str]:
    return list(
        bind.execute(
            sa.text(f"SELECT i.client_id FROM items i WHERE {predicate} ORDER BY i.client_id")
        ).scalars()
    )


def _create_journal() -> None:
    op.execute(
        sa.text(
            f"""
            CREATE TABLE IF NOT EXISTS {_JOURNAL} (
                item_client_id varchar(64) PRIMARY KEY,
                item_value_minor integer,
                item_cost_minor integer,
                item_currency item_currency_enum,
                valuation_client_id varchar(64)
            )
            """
        )
    )


def _journal_legacy_rows(bind) -> None:
    bind.execute(
        sa.text(
            f"""
            INSERT INTO {_JOURNAL}
                (item_client_id, item_value_minor, item_cost_minor, item_currency)
            SELECT i.client_id, i.item_value_minor, i.item_cost_minor, i.item_currency
            FROM items i
            WHERE i.item_value_minor IS NOT NULL
               OR i.item_cost_minor IS NOT NULL
               OR i.item_currency IS NOT NULL
            ON CONFLICT (item_client_id) DO NOTHING
            """
        )
    )


def _copy_eligible_valuations(bind) -> None:
    rows = bind.execute(
        sa.text(
            f"""
            SELECT
                i.client_id AS item_client_id,
                i.workspace_id,
                i.item_value_minor,
                i.item_cost_minor,
                i.item_currency,
                i.created_by_id
            FROM items i
            LEFT JOIN {_JOURNAL} j ON j.item_client_id = i.client_id
            WHERE i.is_deleted = false
              AND {_LEGACY_AMOUNT}
              AND i.item_currency IS NOT NULL
              AND {_NON_NEGATIVE_AMOUNTS}
              AND i.created_by_id IS NOT NULL
              AND j.valuation_client_id IS NULL
              AND {_NO_VALUATION}
            ORDER BY i.client_id
            """
        )
    ).mappings().all()

    now = datetime.now(timezone.utc)
    for row in rows:
        valuation_client_id = generate_id("ival")
        bind.execute(
            sa.text(
                """
                INSERT INTO item_valuations
                    (client_id, workspace_id, item_id, expected_sale_price_minor,
                     purchase_cost_minor, currency, superseded_at, superseded_by_id,
                     created_at, created_by_id, is_deleted, deleted_at, deleted_by_id)
                VALUES
                    (:client_id, :workspace_id, :item_id, :expected_sale_price_minor,
                     :purchase_cost_minor, :currency, NULL, NULL,
                     :created_at, :created_by_id, false, NULL, NULL)
                """
            ),
            {
                "client_id": valuation_client_id,
                "workspace_id": row["workspace_id"],
                "item_id": row["item_client_id"],
                "expected_sale_price_minor": row["item_value_minor"],
                "purchase_cost_minor": row["item_cost_minor"],
                "currency": row["item_currency"],
                "created_at": now,
                "created_by_id": row["created_by_id"],
            },
        )
        bind.execute(
            sa.text(
                f"""
                UPDATE {_JOURNAL}
                SET valuation_client_id = :valuation_client_id
                WHERE item_client_id = :item_client_id
                  AND valuation_client_id IS NULL
                """
            ),
            {"valuation_client_id": valuation_client_id, "item_client_id": row["item_client_id"]},
        )


def _assert_postconditions(bind) -> None:
    journal_count = bind.execute(sa.text(f"SELECT count(*) FROM {_JOURNAL}")).scalar_one()
    expected_journal_count = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM items
            WHERE item_value_minor IS NOT NULL
               OR item_cost_minor IS NOT NULL
               OR item_currency IS NOT NULL
            """
        )
    ).scalar_one()
    if journal_count != expected_journal_count:
        raise RuntimeError(
            f"item money migration journal count mismatch: {journal_count} != {expected_journal_count}"
        )

    unmigrated_eligible_count = bind.execute(
        sa.text(
            f"""
            SELECT count(*)
            FROM items i
            LEFT JOIN {_JOURNAL} j ON j.item_client_id = i.client_id
            WHERE i.is_deleted = false
              AND {_LEGACY_AMOUNT}
              AND i.item_currency IS NOT NULL
              AND {_NON_NEGATIVE_AMOUNTS}
              AND i.created_by_id IS NOT NULL
              AND j.valuation_client_id IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM item_valuations v
                  WHERE v.item_id = i.client_id
                    AND v.client_id IS DISTINCT FROM j.valuation_client_id
              )
            """
        )
    ).scalar_one()
    if unmigrated_eligible_count:
        raise RuntimeError(
            "item money migration left "
            f"{unmigrated_eligible_count} eligible item(s) unmigrated"
        )

    invalid_created = bind.execute(
        sa.text(
            f"""
            SELECT count(*)
            FROM item_valuations v
            JOIN {_JOURNAL} j ON j.valuation_client_id = v.client_id
            WHERE v.superseded_at IS NOT NULL
               OR v.is_deleted IS NOT FALSE
               OR v.currency IS NULL
            """
        )
    ).scalar_one()
    if invalid_created:
        raise RuntimeError(f"item money migration created invalid valuations: {invalid_created}")


def upgrade() -> None:
    bind = op.get_bind()

    p1 = _offending_ids(bind, f"{_LEGACY_AMOUNT} AND i.item_currency IS NULL")
    p2 = _offending_ids(bind, f"{_LEGACY_AMOUNT} AND (i.item_value_minor < 0 OR i.item_cost_minor < 0)")
    p3 = _offending_ids(bind, f"{_LEGACY_AMOUNT} AND i.created_by_id IS NULL")
    if p1 or p2 or p3:
        raise RuntimeError(
            "item money migration refused before any write: "
            f"P1 amount-without-currency client_ids={p1}; "
            f"P2 negative-amount client_ids={p2}; "
            f"P3 amount-without-creator client_ids={p3}"
        )

    _create_journal()
    _journal_legacy_rows(bind)
    _copy_eligible_valuations(bind)
    _assert_postconditions(bind)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            f"""
            UPDATE items i
            SET item_value_minor = j.item_value_minor,
                item_cost_minor = j.item_cost_minor,
                item_currency = j.item_currency
            FROM {_JOURNAL} j
            WHERE j.item_client_id = i.client_id
            """
        )
    )
    bind.execute(
        sa.text(
            f"""
            DELETE FROM item_valuations v
            USING {_JOURNAL} j
            WHERE j.valuation_client_id = v.client_id
            """
        )
    )
    op.execute(f"DROP TABLE IF EXISTS {_JOURNAL}")
