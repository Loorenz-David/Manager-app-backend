from beyo_manager.services.queries.stock_report.consistency import (
    compute_stock_report_divergences,
)


async def get_stock_report_consistency(ctx):
    return {
        "workspace_id": ctx.workspace_id,
        "checked_at": ctx.now.isoformat(),
        "divergences": await compute_stock_report_divergences(
            ctx.session, ctx.workspace_id
        ),
    }
