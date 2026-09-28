from datetime import datetime, timezone

from sqlalchemy import select, update

from beyo_manager.domain.schedulers.enums import (
    DelayedSchedulerTypeEnum,
    SchedulerStateEnum,
)
from beyo_manager.models.tables.schedulers.delayed_scheduler import DelayedScheduler
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)


async def cancel_stock_report_version_schedulers(session, workspace_id):
    """Cancel the `ACTIVE` scheduled-activation rows of the workspace's versions
    (stock-report draft versions, plan §5.1, P-21). `delayed_schedulers` has no
    workspace column, so the rows are found by `event_client_id` among the version
    ids — which is why this runs immediately **before**
    `delete_stock_report_snapshot_versions` removes them."""
    await session.execute(
        update(DelayedScheduler)
        .where(
            DelayedScheduler.type
            == DelayedSchedulerTypeEnum.STOCK_REPORT_VERSION_ACTIVATION,
            DelayedScheduler.state == SchedulerStateEnum.ACTIVE,
            DelayedScheduler.event_client_id.in_(
                select(StockReportSnapshotVersion.client_id).where(
                    StockReportSnapshotVersion.workspace_id == workspace_id
                )
            ),
        )
        .values(
            state=SchedulerStateEnum.CANCELED, updated_at=datetime.now(timezone.utc)
        )
        .execution_options(synchronize_session=False)
    )
