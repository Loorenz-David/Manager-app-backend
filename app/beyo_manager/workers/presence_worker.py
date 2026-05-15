import asyncio

from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.services.infra.execution.worker_base import run_worker
from beyo_manager.services.tasks.presence.record_view_end import handle_record_view_end
from beyo_manager.services.tasks.presence.record_view_start import handle_record_view_start

HANDLER_MAP = {
    TaskType.RECORD_VIEW_START: handle_record_view_start,
    TaskType.RECORD_VIEW_END:   handle_record_view_end,
}

if __name__ == "__main__":
    asyncio.run(run_worker("queue:presence", HANDLER_MAP))
