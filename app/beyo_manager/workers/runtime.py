from __future__ import annotations

from rq import Worker

from beyo_manager.config import settings
from beyo_manager.core.logging.config import configure_logging, log_event
from beyo_manager.queues.registry import QUEUE_NAMES
from beyo_manager.services.infra.redis import get_redis_client
from beyo_manager.workers.logging import bind_worker_context


def run_worker(worker_name: str = "worker") -> None:
    configure_logging()
    bind_worker_context(worker_name)
    connection = get_redis_client(settings.redis_url)
    worker = Worker(QUEUE_NAMES, connection=connection, name=worker_name)
    log_event("worker.start", worker_id=worker_name)
    worker.work(with_scheduler=True)
