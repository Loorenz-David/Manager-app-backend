"""Shared mechanics for item-economics configuration commands."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ConflictError, ValidationError
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.item_economics.production_cost_basis_version import ProductionCostBasisVersion
from beyo_manager.models.tables.item_economics.production_cost_group import ProductionCostGroup
from beyo_manager.models.tables.items.item import Item
from beyo_manager.domain.item_economics.configuration import resolve_economics_selection
from beyo_manager.domain.item_economics.configuration import resolve_major_category
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit


INDEX_IDENTITIES = {
    "uix_production_cost_groups_name_active": "ITEM_COST_GROUP_NAME_TAKEN",
    "uix_production_cost_groups_major_category_active": "ITEM_COST_GROUP_CATEGORY_TAKEN",
    "uix_production_cost_group_sections_active": "ITEM_COST_SECTION_ALREADY_GROUPED",
    "uix_production_cost_basis_versions_open": "ITEM_COST_CONCURRENT_BASIS_VERSION",
    "uix_cost_model_versions_open": "ITEM_COST_CONCURRENT_MODEL_VERSION",
    "uix_cost_model_terms_purchase_cost": "ITEM_COST_PURCHASE_TERM_DUPLICATE",
    "uix_cost_model_terms_name_active": "ITEM_COST_TERM_NAME_TAKEN",
    "uix_item_valuations_current": "ITEM_COST_CONCURRENT_VALUATION",
    "uix_item_cost_evaluations_current": "ITEM_COST_CONCURRENT_COMMIT",
}


def translate_integrity_error(exc: IntegrityError) -> None:
    """Translate only registered partial-unique indexes; preserve unknown errors."""
    message = str(exc.orig)
    for index_name, identity in INDEX_IDENTITIES.items():
        if index_name in message:
            raise ConflictError(f"{identity}: configuration conflicts with an existing row") from exc
    raise exc


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def admission_error(prefix: str, effective_from: date | None, open_version: object | None, today: date) -> None:
    """Enforce the complete §7A.4 open-row/request matrix."""
    if effective_from is not None and effective_from > today:
        raise ValidationError(f"{prefix}_EFFECTIVE_FROM_FUTURE: effective_from cannot be after today")
    if open_version is None:
        return
    open_from = getattr(open_version, "effective_from", None)
    if effective_from is None:
        raise ValidationError(f"{prefix}_EFFECTIVE_FROM_REQUIRED: effective_from is required")
    if open_from is not None and effective_from <= open_from:
        raise ValidationError(f"{prefix}_EFFECTIVE_FROM_NOT_AFTER_OPEN: effective_from must be after the open version")


async def get_group(ctx: ServiceContext, client_id: str) -> ProductionCostGroup:
    statement = select(ProductionCostGroup).where(
        ProductionCostGroup.workspace_id == ctx.workspace_id,
        ProductionCostGroup.client_id == client_id,
        ProductionCostGroup.is_deleted.is_(False),
    )
    row = await ctx.session.scalar(statement)
    if row is None:
        raise NotFound("Production cost group not found.")
    return row


async def get_basis(ctx: ServiceContext, client_id: str, *, for_update: bool = False) -> ProductionCostBasisVersion:
    statement = select(ProductionCostBasisVersion).where(
        ProductionCostBasisVersion.workspace_id == ctx.workspace_id,
        ProductionCostBasisVersion.client_id == client_id,
        ProductionCostBasisVersion.is_deleted.is_(False),
    )
    if for_update:
        statement = statement.with_for_update()
    row = await ctx.session.scalar(statement)
    if row is None:
        raise NotFound("Production cost basis version not found.")
    return row


async def get_model(ctx: ServiceContext, client_id: str, *, for_update: bool = False) -> CostModelVersion:
    statement = select(CostModelVersion).where(
        CostModelVersion.workspace_id == ctx.workspace_id,
        CostModelVersion.client_id == client_id,
        CostModelVersion.is_deleted.is_(False),
    )
    if for_update:
        statement = statement.with_for_update()
    row = await ctx.session.scalar(statement)
    if row is None:
        raise NotFound("Cost model version not found.")
    return row


async def audit(ctx: ServiceContext, event: str, resource_type: str, resource_id: str, detail: dict | None = None) -> None:
    await write_audit(
        ctx.session,
        event=event,
        workspace_id=ctx.workspace_id,
        actor_user_id=ctx.user_id,
        actor_label=ctx.identity.get("username") or ctx.identity.get("email"),
        resource_type=resource_type,
        resource_client_id=resource_id,
        detail=detail,
    )


async def write_item_valuation_chain_in_session(
    session,
    *,
    workspace_id: str,
    item_id: str,
    expected_sale_price_minor: int | None,
    purchase_cost_minor: int | None,
    currency,
    created_by_id: str,
    now: datetime | None = None,
) -> ItemValuation:
    """Advance the valuation chain using the shared S1/S2/S3 write shape."""
    now = now or datetime.now(timezone.utc)
    old = await session.scalar(
        select(ItemValuation).where(
            ItemValuation.workspace_id == workspace_id,
            ItemValuation.item_id == item_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        )
    )
    close_result = await session.execute(
        update(ItemValuation)
        .where(
            ItemValuation.workspace_id == workspace_id,
            ItemValuation.item_id == item_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        )
        .values(superseded_at=now)
    )
    valuation = ItemValuation(
        workspace_id=workspace_id,
        item_id=item_id,
        expected_sale_price_minor=expected_sale_price_minor,
        purchase_cost_minor=purchase_cost_minor,
        currency=currency,
        created_at=now,
        created_by_id=created_by_id,
    )
    session.add(valuation)
    try:
        await session.flush()
    except IntegrityError as exc:
        translate_integrity_error(exc)
    if close_result.rowcount == 1 and old is not None:
        await session.execute(
            update(ItemValuation)
            .where(ItemValuation.client_id == old.client_id)
            .values(superseded_by_id=valuation.client_id)
        )
        await session.flush()
    return valuation


async def _load_preview_inputs(ctx: ServiceContext, item: Item):
    """Load the complete live configuration used by valuation previews and auto-commit."""
    groups = (
        await ctx.session.execute(
            select(ProductionCostGroup).where(
                ProductionCostGroup.workspace_id == ctx.workspace_id,
                ProductionCostGroup.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    basis_versions = (
        await ctx.session.execute(
            select(ProductionCostBasisVersion).where(
                ProductionCostBasisVersion.workspace_id == ctx.workspace_id,
                ProductionCostBasisVersion.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    cost_model_versions = (
        await ctx.session.execute(
            select(CostModelVersion).where(
                CostModelVersion.workspace_id == ctx.workspace_id,
                CostModelVersion.is_deleted.is_(False),
            )
        )
    ).scalars().all()
    selection = resolve_economics_selection(
        resolve_major_category(item.item_major_category_snapshot),
        groups,
        basis_versions,
        cost_model_versions,
        today_utc(),
    )
    terms = []
    if selection.cost_model_version is not None:
        terms = (
            await ctx.session.execute(
                select(CostModelTerm).where(
                    CostModelTerm.workspace_id == ctx.workspace_id,
                    CostModelTerm.cost_model_version_id == selection.cost_model_version.client_id,
                    CostModelTerm.is_deleted.is_(False),
                ).order_by(CostModelTerm.created_at.asc(), CostModelTerm.client_id.asc())
            )
        ).scalars().all()
    return selection, terms


AfterLock = Callable[[], Awaitable[None]]
