from sqlalchemy import and_, select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.tasks.task_step import TaskStep
from beyo_manager.models.tables.tasks.task_step_acknowledgment import TaskStepAcknowledgment
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.task_step_acknowledgments._reassigned_steps_filters import (
    reassigned_steps_where_clauses,
)
from beyo_manager.services.queries.utils.upholstery_grouping import (
    build_primary_item_upholstery_group_columns,
)
from beyo_manager.services.queries.working_sections.step_record_payload import (
    load_step_with_latest_record,
)
from beyo_manager.services.queries.working_sections.steps_list_payload import (
    build_steps_list_payload,
)


async def get_task_step(ctx: ServiceContext) -> dict:
    """Return one step in the section-list card shape.

    The detail surface fetches a step it may not hold a list page for (opened
    from the last-active card, from page 2+ of a section list, or from a push
    deep link), so the payload must be the *same* object the list hands over —
    built by the same builder, not a second one that drifts from it.

    Visibility matches ``/working-sections/{id}/steps``: workspace scope, a live
    step on a live task. The list route applies no working-section membership
    gate, so neither does this one.
    """
    step_id = ctx.incoming_data.get("step_id")

    step = await load_step_with_latest_record(ctx, step_id) if step_id else None
    if step is None:
        # Missing, deleted, on a deleted task, or in another workspace — one
        # answer for all four, deliberately: the caller may not learn which.
        raise NotFound("Step not found.")

    # `is_reassigned`, on the same definition the section list and the
    # reassigned list share, narrowed to this one step.
    reassigned_result = await ctx.session.execute(
        select(TaskStepAcknowledgment.step_id)
        .join(
            TaskStep,
            and_(
                TaskStep.client_id == TaskStepAcknowledgment.step_id,
                TaskStep.workspace_id == ctx.workspace_id,
                TaskStep.is_deleted.is_(False),
            ),
        )
        .where(
            TaskStepAcknowledgment.step_id == step.client_id,
            *reassigned_steps_where_clauses(ctx),
        )
        .limit(1)
    )
    reassigned_step_ids = {row[0] for row in reassigned_result.all()}

    # The three upholstery_group_* columns are properties of the step's own
    # primary item, not of the page it was listed in, so they are resolved here
    # unconditionally. A grouped list page and this route therefore agree; an
    # ungrouped list page sends nulls, and a per-step cache fed by both must not
    # be able to blank a real value. See the answer handoff.
    group_key_column, group_image_column, group_upholstery_id_column = (
        build_primary_item_upholstery_group_columns(ctx.workspace_id, step.task_id)
    )
    group_row = (
        await ctx.session.execute(
            select(group_key_column, group_image_column, group_upholstery_id_column)
        )
    ).one()
    group_key, group_image_url, group_upholstery_id = group_row

    items_payload = await build_steps_list_payload(
        ctx,
        page_ids=[step.client_id],
        reassigned_step_ids=reassigned_step_ids,
        group_key_by_step_id={step.client_id: group_key},
        group_image_by_step_id={step.client_id: group_image_url},
        group_uph_id_by_step_id={step.client_id: group_upholstery_id},
    )
    if not items_payload:
        raise NotFound("Step not found.")

    return {"step": items_payload[0]}
