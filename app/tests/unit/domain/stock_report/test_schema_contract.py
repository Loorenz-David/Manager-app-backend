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
# The snapshot layer (2026-09-26) and its draft states (2026-09-28)
# ---------------------------------------------------------------------------

_ACTIVE_PAIR = "active_at IS NOT NULL AND closed_at IS NULL"


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
    """"Active" is the pair, not `closed_at` alone: a draft is a second open
    version with a second open snapshot per row, and both indexes must let it in."""
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
    assert str(active_version.dialect_options["postgresql"]["where"]) == _ACTIVE_PAIR
    active_snapshot = snapshots["uix_stock_report_item_snapshots_row_active"]
    assert active_snapshot.unique
    assert [column.name for column in active_snapshot.columns] == [
        "workspace_id",
        "stock_report_item_id",
    ]
    assert str(active_snapshot.dialect_options["postgresql"]["where"]) == _ACTIVE_PAIR
    # An ordering group is `(version_id, priority)` over open snapshots.
    assert "ix_stock_report_item_snapshots_workspace_priority_order" not in snapshots
    board = snapshots["ix_stock_report_item_snapshots_version_priority_order"]
    assert [column.name for column in board.columns] == [
        "version_id",
        "priority",
        "priority_order",
    ]
    assert str(board.dialect_options["postgresql"]["where"]) == "closed_at IS NULL"
    assert "ix_stock_report_snapshot_versions_workspace_created_at" in versions


@pytest.mark.unit
def test_snapshot_checks_pair_the_position_and_floor_every_quantity():
    table = Base.metadata.tables["stock_report_item_snapshots"]
    names = {constraint.name for constraint in table.constraints if constraint.name}
    assert {
        "ck_stock_report_item_snapshots_priority_order_pairing",
        "ck_stock_report_item_snapshots_quantity_requested_scanner_nonneg",
        "ck_stock_report_item_snapshots_quantity_requested_manual_nonneg",
        "ck_stock_report_item_snapshots_quantity_in_queue_nonneg",
        "ck_stock_report_item_snapshots_quantity_in_progress_nonneg",
        "ck_stock_report_item_snapshots_quantity_awaiting_nonneg",
        "ck_stock_report_item_snapshots_quantity_missing_nonneg",
        "ck_stock_report_item_snapshots_quantity_resolved_nonneg",
        "ck_stock_report_item_snapshots_scanner_iff_activated",
        "ck_stock_report_item_snapshots_missing_set_once_activated",
        "ck_stock_report_item_snapshots_closed_implies_activated",
        "uq_stock_report_item_snapshots_version_row",
    } <= names
    assert "ck_stock_report_item_snapshots_quantity_requested_nonneg" not in names
    column = table.columns["quantity_resolved"]
    assert column.nullable is False
    assert column.server_default.arg == "0"


@pytest.mark.unit
def test_the_draft_columns_are_nullable_and_the_old_requested_column_is_gone():
    """The wire's `quantity_requested` is derived; no column carries that name on
    the snapshot table any more (plan §3.3), so the next writer cannot read the
    Scanner column as the wire value."""
    snapshots = Base.metadata.tables["stock_report_item_snapshots"].columns
    assert "quantity_requested" not in snapshots
    assert snapshots["quantity_requested_scanner"].nullable is True
    assert snapshots["quantity_requested_scanner"].server_default is None
    assert snapshots["quantity_requested_manual"].nullable is True
    assert snapshots["quantity_missing"].nullable is True
    assert snapshots["quantity_missing"].server_default is None
    assert snapshots["active_at"].nullable is True
    versions = Base.metadata.tables["stock_report_snapshot_versions"]
    columns = versions.columns
    assert columns["active_at"].nullable is True
    assert columns["title"].nullable is True
    assert columns["title"].type.length == 200
    assert columns["scheduled_activation_at"].nullable is True
    assert columns["scheduled_activation_keeps_active_missing"].nullable is False
    assert columns["scheduled_activation_keeps_active_missing"].server_default is not None
    assert {
        "ck_stock_report_snapshot_versions_closed_implies_activated",
        "ck_stock_report_snapshot_versions_schedule_only_on_draft",
    } <= {constraint.name for constraint in versions.constraints if constraint.name}
    history = Base.metadata.tables["stock_report_history_records"].columns
    assert history["quantity_requested_source"].nullable is False
    assert history["quantity_requested_source"].server_default.arg == "scanner"


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


@pytest.mark.unit
def test_draftable_migration_renames_the_column_and_guards_its_downgrade():
    """The requested column is **renamed**, never dropped and re-added (the values
    survive), every new check and enum value is declared, and the downgrade refuses
    while a draft or a manual value exists (plan §3.6 step 9)."""
    source = (
        Path(__file__).parents[4]
        / "migrations/versions/3b8d2f7a9c41_make_stock_report_versions_draftable.py"
    ).read_text()
    assert 'new_column_name="quantity_requested_scanner"' in source
    assert 'op.drop_column(_SNAPSHOTS, "quantity_requested")' not in source
    for name in (
        "ck_stock_report_item_snapshots_scanner_iff_activated",
        "ck_stock_report_item_snapshots_missing_set_once_activated",
        "ck_stock_report_item_snapshots_closed_implies_activated",
        "ck_stock_report_item_snapshots_quantity_requested_manual_nonneg",
        "ck_stock_report_snapshot_versions_closed_implies_activated",
        "ck_stock_report_snapshot_versions_schedule_only_on_draft",
        "ix_stock_report_item_snapshots_version_priority_order",
        "ix_stock_report_snapshot_versions_workspace_created_at",
        "ADD VALUE IF NOT EXISTS 'quantity_requested_override'",
        "ADD VALUE IF NOT EXISTS 'stock_report_version_activation'",
        "ADD VALUE IF NOT EXISTS 'snapshot_version'",
        "stock_report_quantity_requested_source_enum",
    ):
        assert name in source, name
    assert source.count("ADD VALUE IF NOT EXISTS 'stock_report_version_activation'") == 2
    # The downgrade guard names both conditions and raises before any DDL.
    downgrade = source[source.index("def downgrade"):]
    assert "WHERE active_at IS NULL" in downgrade
    assert "WHERE quantity_requested_manual IS NOT NULL" in downgrade
    assert downgrade.index("raise RuntimeError") < downgrade.index("op.drop_column")
