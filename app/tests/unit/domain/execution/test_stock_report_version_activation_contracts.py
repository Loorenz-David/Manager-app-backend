"""The scheduled draft activation's execution contract (stock-report draft versions,
plan §5.1, R-1): the payload survives the JSON round trip the scheduler row and the
execution payload put it through, and the type is wired into **all four**
registries — a missing `QUEUE_MAP` entry leaves the task OPEN forever while the
scheduler row is already `FIRED` (the router only logs `no queue mapped`). The
end-to-end chain is `test_draft_version_scheduling.py`; this names the registry
that broke when it breaks."""

from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.domain.execution.payloads.stock_report_version_activation import (
    StockReportVersionActivationPayload,
)
from beyo_manager.domain.schedulers.enums import DelayedSchedulerTypeEnum
from beyo_manager.services.infra.execution.task_router import QUEUE_MAP
from beyo_manager.services.infra.schedulers.delayed_scheduler_runner import (
    DELAYED_TYPE_TO_TASK_TYPE,
)
from beyo_manager.services.tasks.stock_report.handle_activate_stock_report_snapshot_version import (
    handle_activate_stock_report_snapshot_version,
)
from beyo_manager.workers.tasks_worker import HANDLER_MAP

pytestmark = pytest.mark.unit


def test_the_payload_round_trips_through_json():
    payload = StockReportVersionActivationPayload(
        workspace_id="ws_1",
        version_id="srv_1",
        scheduled_by_user_id=None,
        scheduled_for="2026-10-05T04:00:00+00:00",
    )
    assert (
        StockReportVersionActivationPayload(**json.loads(json.dumps(asdict(payload))))
        == payload
    )


def test_the_type_is_wired_into_all_four_registries():
    assert (
        DelayedSchedulerTypeEnum.STOCK_REPORT_VERSION_ACTIVATION.value
        == TaskType.STOCK_REPORT_VERSION_ACTIVATION.value
        == "stock_report_version_activation"
    )
    assert (
        DELAYED_TYPE_TO_TASK_TYPE[
            DelayedSchedulerTypeEnum.STOCK_REPORT_VERSION_ACTIVATION
        ]
        is TaskType.STOCK_REPORT_VERSION_ACTIVATION
    )
    assert QUEUE_MAP[TaskType.STOCK_REPORT_VERSION_ACTIVATION] == "queue:tasks"
    assert (
        HANDLER_MAP[TaskType.STOCK_REPORT_VERSION_ACTIVATION]
        is handle_activate_stock_report_snapshot_version
    )
