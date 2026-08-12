from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from beyo_manager.domain.item_economics.serializers import serialize_cost_model_version
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.item_economics.cost_model_term import CostModelTerm
from beyo_manager.models.tables.item_economics.cost_model_version import CostModelVersion
from beyo_manager.services.commands.item_economics._common import admission_error, audit, today_utc, translate_integrity_error
from beyo_manager.services.commands.item_economics.requests import parse_cost_model_version_create_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_cost_model_version(ctx: ServiceContext) -> dict:
    request = parse_cost_model_version_create_request(ctx.incoming_data)
    names = [term.name for term in request.terms]
    if len(names) != len(set(names)):
        raise ValidationError("ITEM_COST_TERM_NAME_TAKEN: term names must be unique within a version")
    purchase_terms = [
        term for term in request.terms
        if term.calculation_type.value == "item_purchase_cost"
    ]
    if len(purchase_terms) > 1:
        raise ValidationError("ITEM_COST_PURCHASE_TERM_DUPLICATE: only one item_purchase_cost term is allowed")
    for term in request.terms:
        if term.calculation_type.value == "percentage_of_expected_sale_price":
            if term.percent_value is None or term.fixed_amount_minor is not None:
                raise ValidationError("ITEM_COST_TERM_SHAPE_INVALID: percentage term has an invalid value shape")
        elif term.calculation_type.value == "fixed_amount":
            if term.percent_value is not None or term.fixed_amount_minor is None:
                raise ValidationError("ITEM_COST_TERM_SHAPE_INVALID: fixed term has an invalid value shape")
        elif term.percent_value is not None or term.fixed_amount_minor is not None:
            raise ValidationError("ITEM_COST_TERM_SHAPE_INVALID: purchase-cost term has an invalid value shape")

    async with maybe_begin(ctx.session):
        open_version = await ctx.session.scalar(
            select(CostModelVersion).where(
                CostModelVersion.workspace_id == ctx.workspace_id,
                CostModelVersion.effective_to.is_(None),
                CostModelVersion.is_deleted.is_(False),
            )
        )
        admission_error("ITEM_COST_MODEL_VERSION", request.effective_from, open_version, today_utc())
        if open_version is not None:
            open_version.effective_to = request.effective_from
        version = CostModelVersion(
            workspace_id=ctx.workspace_id,
            effective_from=request.effective_from,
            currency=request.currency,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(version)
        try:
            await ctx.session.flush()
            terms = [
                CostModelTerm(
                    workspace_id=ctx.workspace_id,
                    cost_model_version_id=version.client_id,
                    name=term.name,
                    calculation_type=term.calculation_type,
                    percent_value=term.percent_value,
                    fixed_amount_minor=term.fixed_amount_minor,
                    created_by_id=ctx.user_id,
                )
                for term in request.terms
            ]
            ctx.session.add_all(terms)
            await ctx.session.flush()
        except IntegrityError as exc:
            translate_integrity_error(exc)
        await audit(ctx, "cost_model_version.created", "cost_model_version", version.client_id)
    return {
        "cost_model_version": serialize_cost_model_version(version, terms),
    }
