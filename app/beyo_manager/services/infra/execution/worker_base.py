import asyncio
import logging
import random
import signal
import socket
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from beyo_manager.config import settings
from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.models.database import get_db_session
from beyo_manager.models.tables.execution.execution_task import ExecutionTask
from beyo_manager.services.infra.redis import get_redis_client

logger = logging.getLogger(__name__)

BACKOFF_SECONDS = [30, 120, 300]
BACKOFF_JITTER  = 0.15  # ±15%

HANDLER_TIMEOUT_SECONDS: dict[str, int] = {
    "default":                       300,   # 5 minutes
    "upload_image":                  3600,  # 1 hour
    "send_report":                   600,   # 10 minutes
    "email_sync_targeted":           300,   # 5 minutes
    "send_coordination_email_batch": 300,   # 5 minutes
    "send_email_messages":           300,   # 5 minutes
    "location_tracker_push_locations": 300, # 5 minutes
    "shopify_process_products":      900,   # 15 minutes
}

TaskHandlerFn = Callable[[dict, str], Awaitable[None]]

_shutdown_event: asyncio.Event = asyncio.Event()


def _register_shutdown_handler() -> None:
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown_event.set)


async def run_worker(
    queue_name: str,
    handler_map: dict[TaskType, TaskHandlerFn],
) -> None:
    _register_shutdown_handler()
    loop = asyncio.get_event_loop()
    redis = get_redis_client(settings.redis_url)
    worker_id = f"{socket.gethostname()}:{queue_name}:{int(time.time())}"
    logger.info("worker_start | queue=%s worker_id=%s", queue_name, worker_id)

    current_task_id: str | None = None
    try:
        while not _shutdown_event.is_set():
            # Run blpop in thread pool so the event loop stays responsive to SIGTERM
            raw = await loop.run_in_executor(None, lambda: redis.blpop(queue_name, timeout=2))
            if not raw:
                continue
            current_task_id = raw[1] if isinstance(raw[1], str) else raw[1].decode()
            await _process_task(current_task_id, worker_id, handler_map)
            current_task_id = None
    finally:
        if current_task_id:
            await _rescue_in_flight_task(current_task_id)
        logger.info("worker_shutdown | queue=%s worker_id=%s", queue_name, worker_id)


async def _execute_with_timeout(
    handler: TaskHandlerFn,
    raw_payload: dict,
    task_client_id: str,
    task_type_value: str,
) -> None:
    timeout = HANDLER_TIMEOUT_SECONDS.get(task_type_value, HANDLER_TIMEOUT_SECONDS["default"])
    try:
        await asyncio.wait_for(handler(raw_payload, task_client_id), timeout=timeout)
    except asyncio.TimeoutError:
        raise RuntimeError(f"Handler timed out after {timeout}s")


async def _process_task(
    task_client_id: str,
    worker_id: str,
    handler_map: dict[TaskType, TaskHandlerFn],
) -> None:
    # Session 1 — claim (closes immediately after)
    task_type, raw_payload = await _claim_task(task_client_id, worker_id)
    if task_type is None:
        return

    handler = handler_map.get(task_type)
    if not handler:
        await _mark_no_handler(task_client_id, task_type)
        return

    # Session 2 — handler runs via task_db_session(); pool slot is free here
    start = time.monotonic()
    try:
        await _execute_with_timeout(handler, raw_payload, task_client_id, task_type.value)
        elapsed_ms = (time.monotonic() - start) * 1000
        # Session 3 — finalize (closes immediately after)
        await _finalize_task(task_client_id, worker_id, task_type, elapsed_ms)
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        await _fail_task(task_client_id, worker_id, task_type, exc, elapsed_ms)


async def _claim_task(
    task_client_id: str,
    worker_id: str,
) -> tuple[TaskType | None, dict]:
    now = datetime.now(timezone.utc)
    async for session in get_db_session():
        result = await session.execute(
            select(ExecutionTask)
            .where(
                ExecutionTask.client_id == task_client_id,
                ExecutionTask.state == ExecutionTaskStateEnum.PENDING,
            )
            .with_for_update(skip_locked=True)
        )
        task = result.scalar_one_or_none()
        if task is None:
            logger.info("task_id=%s already claimed — skipping", task_client_id)
            return None, {}

        task.state      = ExecutionTaskStateEnum.IN_PROGRESS
        task.worker_id  = worker_id
        task.locked_at  = now
        task.started_at = now

        await session.refresh(task, attribute_names=["payload"])
        raw_payload = task.payload.payload if task.payload else {}
        task_type = task.task_type
        await session.commit()
        return task_type, raw_payload


async def _mark_no_handler(task_client_id: str, task_type: TaskType) -> None:
    logger.error("no handler | task_type=%s task_id=%s", task_type, task_client_id)
    async for session in get_db_session():
        result = await session.execute(
            select(ExecutionTask).where(ExecutionTask.client_id == task_client_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.state      = ExecutionTaskStateEnum.FAIL
            task.last_error = "No handler registered for task_type."
            await session.commit()


async def _finalize_task(
    task_client_id: str,
    worker_id: str,
    task_type: TaskType,
    elapsed_ms: float,
) -> None:
    async for session in get_db_session():
        result = await session.execute(
            select(ExecutionTask).where(ExecutionTask.client_id == task_client_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.state        = ExecutionTaskStateEnum.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info(
                "task_completed | task_id=%s task_type=%s worker=%s elapsed_ms=%.1f",
                task_client_id, task_type.value, worker_id, elapsed_ms,
            )


async def _fail_task(
    task_client_id: str,
    worker_id: str,
    task_type: TaskType,
    exc: Exception,
    elapsed_ms: float,
) -> None:
    logger.error(
        "task_failed | task_id=%s task_type=%s worker=%s elapsed_ms=%.1f error=%s",
        task_client_id, task_type.value, worker_id, elapsed_ms, str(exc)[:200],
    )
    async for session in get_db_session():
        result = await session.execute(
            select(ExecutionTask).where(ExecutionTask.client_id == task_client_id)
        )
        task = result.scalar_one_or_none()
        if task:
            await _schedule_retry_or_fail(session, task, exc)


async def _rescue_in_flight_task(task_client_id: str) -> None:
    """Called in finally block on SIGTERM — rescues in-flight task to RETRY_SCHEDULED."""
    async for session in get_db_session():
        result = await session.execute(
            select(ExecutionTask).where(ExecutionTask.client_id == task_client_id)
        )
        task = result.scalar_one_or_none()
        if task and task.state == ExecutionTaskStateEnum.IN_PROGRESS:
            task.state         = ExecutionTaskStateEnum.RETRY_SCHEDULED
            task.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            logger.warning("worker_sigterm_rescue | task_id=%s", task_client_id)
            await session.commit()


async def _schedule_retry_or_fail(session, task: ExecutionTask, exc: Exception) -> None:
    task.try_count  += 1
    task.last_error  = str(exc)[:1024]

    if task.try_count < task.max_try:
        base   = BACKOFF_SECONDS[min(task.try_count - 1, len(BACKOFF_SECONDS) - 1)]
        jitter = base * BACKOFF_JITTER
        delay  = base + random.uniform(-jitter, jitter)
        task.state         = ExecutionTaskStateEnum.RETRY_SCHEDULED
        task.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=max(delay, 1))
        logger.warning(
            "task_id=%s retry_scheduled | attempt=%d next_retry_at=%s",
            task.client_id, task.try_count, task.next_retry_at,
        )
    else:
        task.state = ExecutionTaskStateEnum.FAIL
        logger.error(
            "task_id=%s permanently failed | attempt=%d error=%s",
            task.client_id, task.try_count, task.last_error,
        )
    await session.commit()
