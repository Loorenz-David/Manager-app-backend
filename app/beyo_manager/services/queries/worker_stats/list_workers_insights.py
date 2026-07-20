from beyo_manager.domain.analytics.serializers import serialize_insight
from beyo_manager.domain.roles.enums import RoleNameEnum
from beyo_manager.domain.users.serializers import serialize_user_worker_stat
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.analytics.compute_worker_insights import compute_worker_insights
from beyo_manager.services.queries.worker_stats._roster import load_worker_page, resolve_work_date


async def list_workers_insights(ctx: ServiceContext) -> dict:
    work_date = resolve_work_date(ctx.query_params.get("work_date"))
    workers, workers_pagination = await load_worker_page(
        ctx, roles=(RoleNameEnum.WORKER, RoleNameEnum.MANAGER)
    )
    worker_ids = [user.client_id for user in workers]
    insights_by_user = await compute_worker_insights(ctx, worker_ids, work_date)

    worker_results = [
        {
            "user": serialize_user_worker_stat(user),
            "insights": [
                serialize_insight(insight)
                for insight in insights_by_user.get(user.client_id, [])
            ],
        }
        for user in workers
    ]
    return {"workers": worker_results, "workers_pagination": workers_pagination}
