from sqlalchemy import func, select

from beyo_manager.domain.tasks.enums import TaskCustomerCoordinationStateEnum
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.services.context import ServiceContext


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


async def count_task_customer_coordination_states(ctx: ServiceContext) -> dict:
    requested_states = _split_csv(ctx.query_params.get("customer_coordination_states"))

    stmt = (
        select(TaskCustomerCoordination.state, func.count(TaskCustomerCoordination.client_id))
        .where(TaskCustomerCoordination.workspace_id == ctx.workspace_id)
        .group_by(TaskCustomerCoordination.state)
    )

    if requested_states:
        stmt = stmt.where(TaskCustomerCoordination.state.in_(requested_states))

    rows = (await ctx.session.execute(stmt)).all()
    raw = {state.value: count for state, count in rows}

    if requested_states:
        return {state: raw.get(state, 0) for state in requested_states}

    return {state.value: raw.get(state.value, 0) for state in TaskCustomerCoordinationStateEnum}
