import logging
from beyo_manager.models.tables.stock_report.stock_report_repair_record import (
    StockReportRepairRecord,
)

logger = logging.getLogger(__name__)


def _text(value):
    return (
        None
        if value is None
        else (str(value).lower() if isinstance(value, bool) else str(value))
    )


async def write_repair_record(
    session,
    *,
    workspace_id,
    target_kind,
    target_client_id,
    field,
    stored_value,
    recomputed_value,
    trigger,
    created_by_id,
    now,
    delta=None,
):
    record = StockReportRepairRecord(
        workspace_id=workspace_id,
        target_kind=target_kind,
        target_client_id=target_client_id,
        field=field,
        stored_value=_text(stored_value),
        recomputed_value=_text(recomputed_value),
        trigger=trigger,
        created_by_id=created_by_id,
        created_at=now,
    )
    session.add(record)
    logger.warning(
        "stock-report repair row=%s field=%s stored=%s recomputed=%s delta=%s trigger=%s",
        target_client_id,
        field,
        stored_value,
        recomputed_value,
        delta,
        trigger,
    )
    return record
