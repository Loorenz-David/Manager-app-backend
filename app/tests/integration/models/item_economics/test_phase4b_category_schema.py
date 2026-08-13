from __future__ import annotations

import importlib
import inspect as python_inspect
import re

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from beyo_manager.models import Base
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.workspaces.workspace import Workspace
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum


@pytest.mark.integration
async def test_phase4b_live_schema_reuses_enum_and_matches_model(db_session):
    connection = await db_session.connection()

    def inspect_schema(sync_connection):
        reflected = inspect(sync_connection)
        group_columns = {column["name"]: column for column in reflected.get_columns("production_cost_groups")}
        indexes = {index["name"]: index for index in reflected.get_indexes("production_cost_groups")}
        context = MigrationContext.configure(sync_connection, opts={"compare_type": True})
        diffs = compare_metadata(context, Base.metadata)
        return group_columns, indexes, diffs

    columns, indexes, diffs = await connection.run_sync(inspect_schema)
    assert columns["major_category"]["nullable"] is False
    assert indexes["uix_production_cost_groups_major_category_active"]["unique"] is True
    assert indexes["uix_production_cost_groups_major_category_active"]["column_names"] == [
        "workspace_id",
        "major_category",
    ]

    enum_metadata = await connection.execute(
        text(
            """
            SELECT a.attnotnull, t.typname, i.indisunique,
                   pg_get_expr(i.indpred, i.indrelid)
            FROM pg_attribute AS a
            JOIN pg_class AS c ON c.oid = a.attrelid
            JOIN pg_type AS t ON t.oid = a.atttypid
            JOIN pg_index AS i ON i.indexrelid = 'uix_production_cost_groups_major_category_active'::regclass
            WHERE c.relname = 'production_cost_groups' AND a.attname = 'major_category'
            """
        )
    )
    not_null, type_name, unique, predicate = enum_metadata.one()
    assert not_null is True
    assert type_name == "item_major_category_enum"
    assert unique is True
    assert predicate == "(is_deleted = false)"
    enum_count = await connection.scalar(text("SELECT count(*) FROM pg_type WHERE typname = 'item_major_category_enum'"))
    assert enum_count == 1

    assert not any("production_cost_groups" in repr(diff) for diff in diffs)


def test_phase4b_migration_has_report_first_preflight_and_enum_reuse():
    migration = importlib.import_module(
        "migrations.versions.5caae620088c_add_major_category_to_production_cost_groups"
    )
    source = python_inspect.getsource(migration.upgrade)
    ddl_position = source.index("op.add_column")
    assert source.index("SELECT client_id") < ddl_position
    assert source.index("RuntimeError") < ddl_position
    assert "group_ids" in source
    assert "dependent_counts" in source
    assert "production_cost_group_sections" in source
    assert "production_cost_basis_versions" in source
    assert "item_cost_evaluations" in source
    assert "client_ids=" in source
    assert "server_default" not in source
    assert "UPDATE" not in source
    assert migration._item_major_category_enum.create_type is False


def test_phase4b_migration_downgrade_drops_only_owned_column_and_index():
    migration = importlib.import_module(
        "migrations.versions.5caae620088c_add_major_category_to_production_cost_groups"
    )
    source = python_inspect.getsource(migration.downgrade)
    assert source.index("op.drop_index") < source.index("op.drop_column")
    assert "DROP TYPE" not in source.upper()
    assert not re.search(r"item_major_category_enum[^\n]*\.drop\(", source)


async def _actor(db_session, suffix: str):
    workspace = Workspace(client_id=f"ws_{suffix}", name=f"workspace {suffix}")
    user = User(
        client_id=f"usr_{suffix}",
        username=f"user_{suffix}",
        email=f"{suffix}@example.test",
        password="test",
    )
    db_session.add_all([workspace, user])
    await db_session.flush()
    return workspace, user


def _group(workspace, user, name: str, category: ItemMajorCategoryEnum, *, deleted: bool = False):
    return ProductionCostGroup(
        workspace_id=workspace.client_id,
        name=name,
        major_category=category,
        created_by_id=user.client_id,
        is_deleted=deleted,
    )


@pytest.mark.integration
async def test_phase4b_index_conflict_row_shares_only_workspace_and_category(db_session):
    workspace, user = await _actor(db_session, "category_conflict")
    first = _group(workspace, user, "First", ItemMajorCategoryEnum.WOOD)
    second = _group(workspace, user, "Second", ItemMajorCategoryEnum.WOOD)
    db_session.add(first)
    await db_session.flush()
    with pytest.raises(IntegrityError) as raised:
        async with db_session.begin_nested():
            db_session.add(second)
            await db_session.flush()
    assert "uix_production_cost_groups_major_category_active" in str(raised.value)


@pytest.mark.integration
async def test_phase4b_index_predicate_allows_deleted_row(db_session):
    workspace, user = await _actor(db_session, "category_deleted")
    first = _group(workspace, user, "Deleted", ItemMajorCategoryEnum.WOOD, deleted=True)
    second = _group(workspace, user, "Active", ItemMajorCategoryEnum.WOOD)
    db_session.add_all([first, second])
    await db_session.flush()

@pytest.mark.integration
async def test_phase4b_index_key_accepts_two_categories_in_one_workspace(db_session):
    workspace, user = await _actor(db_session, "category_key")
    db_session.add_all(
        [
            _group(workspace, user, "Wood", ItemMajorCategoryEnum.WOOD),
            _group(workspace, user, "Seat", ItemMajorCategoryEnum.SEAT),
        ]
    )
    await db_session.flush()


@pytest.mark.integration
async def test_phase4b_index_key_accepts_same_category_in_two_workspaces(db_session):
    workspace_a, user_a = await _actor(db_session, "category_workspace_a")
    workspace_b, user_b = await _actor(db_session, "category_workspace_b")
    db_session.add_all(
        [
            _group(workspace_a, user_a, "Wood A", ItemMajorCategoryEnum.WOOD),
            _group(workspace_b, user_b, "Wood B", ItemMajorCategoryEnum.WOOD),
        ]
    )
    await db_session.flush()
