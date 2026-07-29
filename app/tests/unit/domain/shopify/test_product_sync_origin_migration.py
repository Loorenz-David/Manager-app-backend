from __future__ import annotations

import importlib

import pytest


class _RecordingOp:
    def __init__(self) -> None:
        self.added_columns: list[tuple[str, object]] = []
        self.created_indexes: list[tuple] = []
        self.executed_sql: list[str] = []
        self.altered_columns: list[tuple] = []
        self.dropped_indexes: list[tuple] = []
        self.dropped_columns: list[tuple] = []

    def add_column(self, table_name, column) -> None:
        self.added_columns.append((table_name, column))

    def create_index(self, *args, **kwargs) -> None:
        self.created_indexes.append((args, kwargs))

    def execute(self, statement) -> None:
        self.executed_sql.append(str(statement))

    def alter_column(self, *args, **kwargs) -> None:
        self.altered_columns.append((args, kwargs))

    def drop_index(self, *args, **kwargs) -> None:
        self.dropped_indexes.append((args, kwargs))

    def drop_column(self, *args, **kwargs) -> None:
        assert not kwargs
        self.dropped_columns.append(args)


@pytest.mark.unit
def test_origin_migration_backfills_preorders_and_only_converts_unfinished_payloads(
    monkeypatch,
) -> None:
    migration = importlib.import_module(
        "migrations.versions.d8e4f1a2c6b7_add_shopify_product_sync_origins"
    )
    recorder = _RecordingOp()
    monkeypatch.setattr(migration, "op", recorder)

    migration.upgrade()

    columns = {column.name: column for _table, column in recorder.added_columns}
    assert columns["sync_origin"].nullable is False
    assert columns["sync_origin"].server_default.arg == "standard_product_sync"
    assert columns["source_entity_type"].nullable is True
    assert columns["source_entity_id"].nullable is True

    sql = "\n".join(recorder.executed_sql).lower()
    assert "event.event_type = 'preorder'" in sql
    assert "task.task_type = 'pre_order'" in sql
    assert "sync_origin = 'preorder_task'" in sql
    assert "source_entity_type = 'task'" in sql
    assert "status in ('pending', 'processing')" in sql
    assert "stage <> 'inventory_set'" in sql
    assert "'quantity', adjustment -> 'quantity_to_add'" in sql
    assert "normalized_payload #- '{inventory,adjustments}'" in sql
    assert "shopify_inventory_adjustments" not in sql
    assert any(
        kwargs.get("server_default") == "set"
        for _args, kwargs in recorder.altered_columns
    )


@pytest.mark.unit
def test_origin_migration_downgrade_removes_only_new_identity_columns(
    monkeypatch,
) -> None:
    migration = importlib.import_module(
        "migrations.versions.d8e4f1a2c6b7_add_shopify_product_sync_origins"
    )
    recorder = _RecordingOp()
    monkeypatch.setattr(migration, "op", recorder)

    migration.downgrade()

    assert recorder.dropped_columns == [
        ("shopify_product_sync_items", "source_entity_id"),
        ("shopify_product_sync_items", "source_entity_type"),
        ("shopify_product_sync_items", "sync_origin"),
    ]
    assert any(
        kwargs.get("server_default") == "add"
        for _args, kwargs in recorder.altered_columns
    )
    assert recorder.executed_sql == []
