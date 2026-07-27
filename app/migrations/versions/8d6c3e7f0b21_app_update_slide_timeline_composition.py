"""app_update slide timeline composition

Adds slide timeline fields (playback_mode, duration_ms, composition_schema_version)
and the app_update_slide_elements table for timed, layered text/media elements.
Non-destructive: existing slides default to manual playback, schema version 1, and
have no elements (rendered via the serialization-time legacy adapter).

Revision ID: 8d6c3e7f0b21
Revises: 7c5b2d6e9a1f
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8d6c3e7f0b21"
down_revision: Union[str, None] = "7c5b2d6e9a1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# playback enum is used in add_column, which does NOT auto-create the type — so
# it is created explicitly and marked create_type=False. The element enum is used
# in create_table, which DOES auto-create it (default create_type=True) — so it is
# NOT created explicitly, to avoid a duplicate CREATE TYPE.
_PLAYBACK_ENUM = sa.Enum(
    "manual", "timed", "media_driven",
    name="app_update_slide_playback_mode_enum",
    create_type=False,
)
_ELEMENT_TYPE_ENUM = sa.Enum(
    "media", "text",
    name="app_update_slide_element_type_enum",
)


def upgrade() -> None:
    _PLAYBACK_ENUM.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "app_update_presentation_slides",
        sa.Column(
            "playback_mode",
            _PLAYBACK_ENUM,
            nullable=False,
            server_default="manual",
        ),
    )
    op.add_column(
        "app_update_presentation_slides",
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "app_update_presentation_slides",
        sa.Column(
            "composition_schema_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    op.create_table(
        "app_update_slide_elements",
        sa.Column("slide_id", sa.String(length=64), nullable=False),
        sa.Column("element_type", _ELEMENT_TYPE_ENUM, nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("layer_index", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=True),
        sa.Column("media_id", sa.String(length=64), nullable=True),
        sa.Column("text_content", sa.String(length=4096), nullable=True),
        sa.Column("layout", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("style", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("enter_animation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exit_animation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["slide_id"], ["app_update_presentation_slides.client_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["media_id"], ["app_update_slide_media.client_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint(
            "slide_id", "sequence_order", name="uq_app_update_slide_elements_slide_sequence"
        ),
        sa.CheckConstraint("start_ms >= 0", name="ck_app_update_slide_elements_start_non_negative"),
        sa.CheckConstraint(
            "end_ms IS NULL OR end_ms > start_ms",
            name="ck_app_update_slide_elements_end_after_start",
        ),
    )
    op.create_index(
        op.f("ix_app_update_slide_elements_slide_id"),
        "app_update_slide_elements",
        ["slide_id"],
    )
    op.create_index(
        op.f("ix_app_update_slide_elements_media_id"),
        "app_update_slide_elements",
        ["media_id"],
    )
    op.create_index(
        "ix_app_update_slide_elements_order",
        "app_update_slide_elements",
        ["slide_id", "layer_index", "sequence_order", "start_ms"],
    )

    # Drop the server defaults; values are supplied by the ORM going forward.
    op.alter_column("app_update_presentation_slides", "playback_mode", server_default=None)
    op.alter_column(
        "app_update_presentation_slides", "composition_schema_version", server_default=None
    )


def downgrade() -> None:
    op.drop_index("ix_app_update_slide_elements_order", table_name="app_update_slide_elements")
    op.drop_index(
        op.f("ix_app_update_slide_elements_media_id"), table_name="app_update_slide_elements"
    )
    op.drop_index(
        op.f("ix_app_update_slide_elements_slide_id"), table_name="app_update_slide_elements"
    )
    op.drop_table("app_update_slide_elements")

    op.drop_column("app_update_presentation_slides", "composition_schema_version")
    op.drop_column("app_update_presentation_slides", "duration_ms")
    op.drop_column("app_update_presentation_slides", "playback_mode")

    op.execute("DROP TYPE IF EXISTS app_update_slide_element_type_enum")
    op.execute("DROP TYPE IF EXISTS app_update_slide_playback_mode_enum")
