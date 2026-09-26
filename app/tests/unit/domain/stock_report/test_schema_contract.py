import pytest
from pathlib import Path
from beyo_manager.models import Base
from beyo_manager.models.tables.tasks.task import Task


@pytest.mark.unit
def test_stock_report_metadata_has_required_tables_and_task_server_default():
    tables = Base.metadata.tables
    assert {
        "stock_report_items",
        "stock_task_assignments",
        "stock_report_history_records",
        "stock_report_repair_records",
    } <= set(tables)
    assert Task.__table__.c.is_stock_assignment.server_default is not None
    assert "resolved_early" in str(tables["stock_task_assignments"].indexes)
    assert {
        constraint.name
        for constraint in tables["stock_report_items"].constraints
        if constraint.name
    } >= {
        "ck_stock_report_items_quantity_requested_nonneg",
        "ck_stock_report_items_quantity_in_queue_nonneg",
        "ck_stock_report_items_quantity_in_progress_nonneg",
        "ck_stock_report_items_quantity_awaiting_nonneg",
    }
    assert "ck_stock_task_assignments_quantity_positive" in {
        constraint.name
        for constraint in tables["stock_task_assignments"].constraints
        if constraint.name
    }
    assert "ck_stock_report_history_records_quantity_awaiting_nonneg" in {
        constraint.name
        for constraint in tables["stock_report_history_records"].constraints
        if constraint.name
    }


@pytest.mark.unit
def test_stock_report_partial_unique_indexes_have_workspace_and_active_predicates():
    items = {
        index.name: index
        for index in Base.metadata.tables["stock_report_items"].indexes
    }
    assignments = {
        index.name: index
        for index in Base.metadata.tables["stock_task_assignments"].indexes
    }
    assert "uix_stock_report_items_identity_active" in items
    assert items["uix_stock_report_items_identity_active"].unique
    assert [column.name for column in items["uix_stock_report_items_identity_active"].columns] == [
        "workspace_id",
        "item_category_id",
        "properties_signature",
    ]
    assert "is_deleted = false" in str(
        items["uix_stock_report_items_identity_active"].dialect_options["postgresql"]["where"]
    )
    for name in (
        "uix_stock_task_assignments_item_active",
        "uix_stock_task_assignments_task_active",
    ):
        assert name in assignments
        assert assignments[name].unique
        expected_columns = [
            "workspace_id",
            "item_id" if name.endswith("item_active") else "task_id",
        ]
        assert [column.name for column in assignments[name].columns] == expected_columns
        predicate = str(assignments[name].dialect_options["postgresql"]["where"])
        assert predicate == (
            "is_deleted = false AND state IN ('in_queue', 'in_progress', 'awaiting')"
        )
        assert "is_deleted = false" in predicate
        assert "in_queue" in predicate
        assert "in_progress" in predicate
        assert "awaiting" in predicate
        assert "resolved_early" not in predicate


@pytest.mark.unit
def test_stock_report_migration_downgrade_removes_each_owned_enum_type():
    migration = (
        Path(__file__).parents[4]
        / "migrations/versions/10d97764a5a7_create_stock_report_tables.py"
    )
    source = migration.read_text()
    for enum_name in (
        "stock_task_assignment_state_enum",
        "stock_report_history_record_type_enum",
        "stock_report_priority_enum",
        "stock_report_repair_target_kind_enum",
    ):
        assert f"DROP TYPE {enum_name}" in source


@pytest.mark.unit
def test_stock_report_migration_declares_all_owned_counter_checks():
    migration = (
        Path(__file__).parents[4]
        / "migrations/versions/10d97764a5a7_create_stock_report_tables.py"
    )
    source = migration.read_text()
    for constraint_name in (
        "ck_stock_report_items_quantity_requested_nonneg",
        "ck_stock_report_items_quantity_in_queue_nonneg",
        "ck_stock_report_items_quantity_in_progress_nonneg",
        "ck_stock_report_items_quantity_awaiting_nonneg",
        "ck_stock_task_assignments_quantity_positive",
        "ck_stock_report_history_records_quantity_awaiting_nonneg",
    ):
        assert constraint_name in source


# ---------------------------------------------------------------------------
# The snapshot layer (2026-09-26)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_snapshot_tables_exist_and_the_row_lost_its_position_columns():
    tables = Base.metadata.tables
    assert {"stock_report_snapshot_versions", "stock_report_item_snapshots"} <= set(tables)
    row_columns = {column.name for column in tables["stock_report_items"].columns}
    assert "priority" not in row_columns
    assert "priority_order" not in row_columns
    assert "ix_stock_report_items_workspace_priority_order" not in {
        index.name for index in tables["stock_report_items"].indexes
    }


@pytest.mark.unit
def test_one_active_version_and_one_active_snapshot_per_row_are_database_facts():
    versions = {
        index.name: index
        for index in Base.metadata.tables["stock_report_snapshot_versions"].indexes
    }
    snapshots = {
        index.name: index
        for index in Base.metadata.tables["stock_report_item_snapshots"].indexes
    }
    active_version = versions["uix_stock_report_snapshot_versions_active"]
    assert active_version.unique
    assert [column.name for column in active_version.columns] == ["workspace_id"]
    assert "closed_at IS NULL" in str(
        active_version.dialect_options["postgresql"]["where"]
    )
    active_snapshot = snapshots["uix_stock_report_item_snapshots_row_active"]
    assert active_snapshot.unique
    assert [column.name for column in active_snapshot.columns] == [
        "workspace_id",
        "stock_report_item_id",
    ]
    assert "closed_at IS NULL" in str(
        active_snapshot.dialect_options["postgresql"]["where"]
    )
    board = snapshots["ix_stock_report_item_snapshots_workspace_priority_order"]
    assert [column.name for column in board.columns] == [
        "workspace_id",
        "priority",
        "priority_order",
    ]


@pytest.mark.unit
def test_snapshot_checks_pair_the_position_and_floor_every_quantity():
    names = {
        constraint.name
        for constraint in Base.metadata.tables["stock_report_item_snapshots"].constraints
        if constraint.name
    }
    assert {
        "ck_stock_report_item_snapshots_priority_order_pairing",
        "ck_stock_report_item_snapshots_quantity_requested_nonneg",
        "ck_stock_report_item_snapshots_quantity_in_queue_nonneg",
        "ck_stock_report_item_snapshots_quantity_in_progress_nonneg",
        "ck_stock_report_item_snapshots_quantity_awaiting_nonneg",
        "ck_stock_report_item_snapshots_quantity_missing_nonneg",
        "ck_stock_report_item_snapshots_quantity_resolved_nonneg",
        "uq_stock_report_item_snapshots_version_row",
    } <= names
    column = Base.metadata.tables["stock_report_item_snapshots"].columns["quantity_resolved"]
    assert column.nullable is False
    assert column.server_default.arg == "0"


@pytest.mark.unit
def test_snapshot_migrations_reuse_the_priority_enum_and_drop_the_row_columns():
    versions = Path(__file__).parents[4] / "migrations/versions"
    create = (versions / "11e1d0d47686_create_stock_report_snapshot_tables.py").read_text()
    drop = (
        versions / "2f7a9c3e5b1d_drop_priority_columns_from_stock_report_items.py"
    ).read_text()
    # The shared enum is referenced, never re-created and never dropped.
    assert 'name="stock_report_priority_enum", create_type=False' in create
    assert "DROP TYPE stock_report_priority_enum" not in create
    assert "ADD VALUE IF NOT EXISTS 'item_snapshot'" in create
    # The completion memory (2026-09-26 addendum) is in the create revision, amended
    # before publication — no fourth revision.
    assert 'sa.Column("quantity_resolved", sa.Integer(), server_default="0", nullable=False)' in create
    assert "ck_stock_report_item_snapshots_quantity_resolved_nonneg" in create
    assert 'op.drop_column("stock_report_items", "priority")' in drop
    assert 'op.drop_column("stock_report_items", "priority_order")' in drop
    assert 'op.drop_index(\n        "ix_stock_report_items_workspace_priority_order"' in drop
