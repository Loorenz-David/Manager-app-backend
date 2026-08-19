"""Task-scoped expected-sold-price scenario read model."""

from __future__ import annotations

from fractions import Fraction

from sqlalchemy import select

from beyo_manager.domain.item_economics.budget_division import (
    TYPICAL_METHOD,
    TYPICAL_MIN_SAMPLE_SIZE,
    TYPICAL_WINDOW_DAYS,
    _median,
    _step_state_is_excluded,
    group_steps_by_section,
)
from beyo_manager.domain.item_economics.calculator import CALCULATION_VERSION
from beyo_manager.domain.item_economics.enums import (
    CostModelTermCalculationTypeEnum,
    EconomicsStatusEnum,
)
from beyo_manager.domain.item_economics.price_scenario import (
    PriceModel,
    break_even_price_minor,
    ceil_to_step,
    collapse_terms,
    infeasible_at_or_below_minor,
    round_half_even,
    slider_domain,
)
from beyo_manager.domain.item_economics.serializers import (
    serialize_task_price_scenario,
)
from beyo_manager.models.tables.item_economics.item_valuation import ItemValuation
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.users.user import User
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.services.commands.item_economics._common import _load_preview_inputs
from beyo_manager.services.commands.item_economics.commit_item_cost_evaluation import (
    _ADMITTED_STATES,
)
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.item_economics.get_task_budget_status import (
    _load_task_and_item,
    get_task_budget_status,
)
from beyo_manager.services.queries.working_sections.get_working_section_typical_times import (
    typical_times_statement,
)


_MODEL_STATUSES = frozenset(
    {
        EconomicsStatusEnum.OK,
        EconomicsStatusEnum.INFEASIBLE,
        EconomicsStatusEnum.ITEM_UNVALUED,
        EconomicsStatusEnum.ITEM_MISSING_EXPECTED_PRICE,
        EconomicsStatusEnum.NOT_EVALUATED,
    }
)


def _has_purchase_term(terms: list[object]) -> bool:
    return any(
        getattr(term, "is_deleted", None) is not True
        and getattr(term, "calculation_type", None)
        is CostModelTermCalculationTypeEnum.ITEM_PURCHASE_COST
        for term in terms
    )


async def _current_valuation(ctx: ServiceContext, item_id: str) -> ItemValuation | None:
    return await ctx.session.scalar(
        select(ItemValuation).where(
            # This line only — workspace_id is redundant defence-in-depth: item_id is
            # already resolved workspace-scoped by
            # get_task_budget_status.py:_load_task_and_item, proven by
            # test_price_scenario_query.py:test_c10_task_resolution_is_workspace_scoped_and_hides_deleted.
            # All three below are load-bearing; two are proven. Drop superseded_at and
            # test_phase3_c1_saved_uses_current_valuation_in_a_supersession_chain goes red;
            # drop is_deleted and test_phase3_g2_soft_deleted_valuation_is_hidden_from_the_price_screen
            # goes red. item_id is NOT proven — measured whole-suite at re-review r4, deleting
            # it reddens nothing, because no fixture holds two items in one workspace. Drop it
            # in production and this returns another item's valuation: its price, its byline.
            ItemValuation.workspace_id == ctx.workspace_id,
            ItemValuation.item_id == item_id,
            ItemValuation.superseded_at.is_(None),
            ItemValuation.is_deleted.is_(False),
        )
    )


async def _typical_block(ctx: ServiceContext, task_id: str) -> dict:
    steps = (
        (
            await ctx.session.execute(
                select(TaskStep).where(
                    # Of these three, only task_id is load-bearing, and none of the three
                    # is proven. workspace_id is redundant defence-in-depth: task_id is
                    # already resolved workspace-scoped by
                    # get_task_budget_status.py:_load_task_and_item, proven by
                    # test_price_scenario_query.py:test_c10_task_resolution_is_workspace_scoped_and_hides_deleted.
                    # is_deleted is defence-in-depth too — budget_division.py:group_steps_by_section
                    # already skips deleted steps in Python, so this predicate cannot change
                    # a result. task_id IS load-bearing: without it this sums every task's
                    # steps in the workspace into one task's typical time — a wrong break-even,
                    # slider domain and suggested price, with no error. Measured whole-suite
                    # (workspace_id at review r1, the other two at re-review r4): dropping
                    # any of the three reddens nothing, because every
                    # _typical_block test uses the _TypicalSession fake, whose execute()
                    # discards the statement and never issues this SQL.
                    TaskStep.workspace_id == ctx.workspace_id,
                    TaskStep.task_id == task_id,
                    TaskStep.is_deleted.is_(False),
                )
            )
        )
        .scalars()
        .all()
    )
    participating = [
        group
        for group in group_steps_by_section(steps)
        if any(not _step_state_is_excluded(step) for step in group["steps"])
    ]
    section_ids = {group["working_section_id"] for group in participating}
    typicals: dict[str, int | None] = {}
    if section_ids:
        result = await ctx.session.execute(
            typical_times_statement(ctx.workspace_id).where(
                WorkingSection.client_id.in_(section_ids)
            )
        )
        typicals = {
            row.client_id: (
                int(row.typical_worker_seconds)
                if row.typical_worker_seconds is not None
                else None
            )
            for row in result
        }

    usable = [
        Fraction(typical, 1)
        for typical in (
            typicals.get(group["working_section_id"]) for group in participating
        )
        if typical is not None and typical > 0
    ]
    fallback = _median(usable) if usable else Fraction(0, 1)
    sections_without_sample = 0
    total_seconds = 0
    for group in participating:
        typical = typicals.get(group["working_section_id"])
        if typical is None or typical <= 0:
            sections_without_sample += 1
            resolved = fallback
        else:
            resolved = Fraction(typical, 1)
        total_seconds += round_half_even(resolved.numerator, resolved.denominator)

    sections_total = len(participating)
    return {
        "total_seconds": total_seconds,
        "is_estimated": sections_total == 0 or sections_without_sample > 0,
        "sections_without_sample": sections_without_sample,
        "sections_total": sections_total,
        "method": TYPICAL_METHOD,
        "window_days": TYPICAL_WINDOW_DAYS,
        "min_sample_size": TYPICAL_MIN_SAMPLE_SIZE,
    }


async def get_task_price_scenario(ctx: ServiceContext) -> dict:
    """Compose live configuration, task typicals, and the price-domain anchors."""

    # Accepted duplication (measured at phase 3): this re-reads task, item, the current
    # valuation and the preview inputs that get_task_budget_status has already loaded —
    # roughly eight redundant round trips on the common no-evaluation branch. Collapsing
    # it means returning those objects from get_task_budget_status, whose TaskBudgetStatus
    # carries item_id and the evaluation result but none of the objects re-read here — not
    # the Task, the Item, the selection, the terms or the valuation — and is a contract
    # other screens consume. Reusing this service is also what keeps status, binding and
    # the tenant boundary identical to them.
    budget_status = await get_task_budget_status(ctx)
    task, item = await _load_task_and_item(ctx)
    typical = await _typical_block(ctx, task.client_id)

    valuation = None
    created_by = None
    selection = None
    terms: list[object] = []
    if item is not None:
        valuation = await _current_valuation(ctx, item.client_id)
        if valuation is not None:
            created_by = await ctx.session.scalar(
                select(User).where(User.client_id == valuation.created_by_id)
            )
        selection, terms = await _load_preview_inputs(ctx, item)

    selection_ready = bool(
        selection is not None
        and selection.status is EconomicsStatusEnum.OK
        and selection.selected_group is not None
        and selection.basis_version is not None
        and selection.cost_model_version is not None
    )
    currency_agrees = bool(
        selection_ready
        and (
            valuation is None
            or valuation.currency
            == selection.basis_version.currency
            == selection.cost_model_version.currency
        )
    )
    can_commit = bool(
        item is not None
        and task.state in _ADMITTED_STATES
        and valuation is not None
        and selection_ready
        and currency_agrees
        and (not _has_purchase_term(terms) or valuation.purchase_cost_minor is not None)
    )

    model_data = None
    anchors = None
    domain = None
    binding_is_bound = budget_status.item_binding == "bound"
    if (
        binding_is_bound
        and budget_status.status in _MODEL_STATUSES
        and selection_ready
        and currency_agrees
    ):
        collapsed = collapse_terms(
            terms,
            valuation.purchase_cost_minor if valuation is not None else None,
        )
        if collapsed is not None:
            residual_percent_milli, constant_deduction_minor = collapsed
            price_model = PriceModel(
                residual_percent_milli=residual_percent_milli,
                constant_deduction_minor=constant_deduction_minor,
                cost_per_worker_minute_ten_thousandths=int(
                    selection.basis_version.cost_per_worker_minute_minor.scaleb(4)
                ),
            )
            break_even = break_even_price_minor(
                price_model,
                typical["total_seconds"],
            )
            infeasible = infeasible_at_or_below_minor(price_model)
            domain = slider_domain(break_even, item.quantity, infeasible)
            anchors = {
                "is_fundable": break_even is not None,
                "break_even_price_minor": break_even,
                "suggested_price_minor": (
                    ceil_to_step(break_even, domain.step_minor)
                    if domain is not None and break_even is not None
                    else None
                ),
                "infeasible_at_or_below_minor": infeasible,
            }
            model_data = {
                "cost_model_version_id": selection.cost_model_version.client_id,
                "basis_version_id": selection.basis_version.client_id,
                "price_model": price_model,
            }

    if not binding_is_bound:
        valuation = None
        created_by = None
        model_data = None
        anchors = None
        domain = None

    fingerprint = (
        f"{model_data['cost_model_version_id']}:{model_data['basis_version_id']}:"
        f"v{CALCULATION_VERSION}"
        if model_data is not None
        else None
    )
    return serialize_task_price_scenario(
        {
            "task_id": task.client_id,
            "status": budget_status.status,
            "item_binding": budget_status.item_binding,
            "can_commit": can_commit,
            "currency": valuation.currency if valuation is not None else None,
            "calculation_version": CALCULATION_VERSION,
            "config_fingerprint": fingerprint,
            "item": item,
            "saved": (
                {"valuation": valuation, "created_by": created_by}
                if valuation is not None
                else None
            ),
            "model": model_data,
            "typical": typical,
            "anchors": anchors,
            "domain": domain,
        }
    )


__all__ = ["get_task_price_scenario"]
