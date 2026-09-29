"""Which background tasks reach systems outside this deployment.

Every TaskType is classified here, as outbound or internal, so adding a type forces
a decision (tests/unit/services/infra/execution/test_outbound_task_guard.py).

With OUTBOUND_INTEGRATIONS_ENABLED=false (staging, local) outbound tasks are
cancelled instead of run: the router cancels them rather than queueing them, and a
worker cancels any it still receives. Internal work — analytics, presence, step
completion, in-app notifications — runs normally.
"""

from datetime import datetime

from beyo_manager.config import settings
from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum, TaskType
from beyo_manager.errors.external_service import OutboundIntegrationsDisabledError
from beyo_manager.models.tables.execution.execution_task import ExecutionTask

OUTBOUND_TASK_TYPES: frozenset[TaskType] = frozenset({
    # Web Push to browser push services
    TaskType.SEND_PUSH_NOTIFICATION,
    # Email: SMTP send and IMAP mailbox sync
    TaskType.SEND_EMAIL_MESSAGES,
    TaskType.SEND_COORDINATION_EMAIL_BATCH,
    TaskType.EMAIL_INBOX_SYNC,
    TaskType.EMAIL_SYNC_TARGETED,
    # Scanner (location tracker)
    TaskType.LOCATION_TRACKER_PUSH_LOCATIONS,
    # Shopify Admin API, including webhook registration
    TaskType.SHOPIFY_PROCESS_WEBHOOK,
    TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP,
    TaskType.SHOPIFY_REMOVE_WEBHOOKS_FOR_SHOP,
    TaskType.SHOPIFY_RECONCILE_SHOP,
    TaskType.SHOPIFY_PROCESS_PRODUCTS,
    # Outbound HTTP webhooks
    TaskType.DELIVER_WEBHOOK,
    # Addressed to people outside the workspace; classified by intent, since their
    # handlers are not implemented yet.
    TaskType.DELAYED_NOTIFY_TO_CUSTOMER,
    TaskType.DELAYED_SEND_REPORT,
    TaskType.RECURRING_SEND_REPORT,
})

INTERNAL_TASK_TYPES: frozenset[TaskType] = frozenset({
    TaskType.NOTIFICATION,
    TaskType.CREATE_NOTIFICATIONS,
    TaskType.DELAYED_REMINDER,
    TaskType.DELAYED_BATCH_NOTIFICATION,
    TaskType.RECURRING_REMINDER,
    TaskType.UPLOAD_IMAGE,
    TaskType.DELAYED_STEP_COMPLETION,
    TaskType.STOCK_REPORT_VERSION_ACTIVATION,
    TaskType.RECURRING_PIN_TASK,
    TaskType.AUTO_CLOCK_OUT_OPEN_SHIFTS,
    TaskType.RECORD_VIEW_START,
    TaskType.RECORD_VIEW_END,
    TaskType.PROCESS_STEP_TRANSITION,
    TaskType.PROCESS_ITEM_COST_RESULT,
    # Processes a webhook Connecteam already delivered; makes no outbound call.
    TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY,
})

OUTBOUND_DISABLED_REASON = (
    "Cancelled: outbound integrations are disabled in this environment "
    "(OUTBOUND_INTEGRATIONS_ENABLED=false)."
)


def outbound_blocked(task_type: TaskType) -> bool:
    return task_type in OUTBOUND_TASK_TYPES and not settings.outbound_integrations_enabled


def require_outbound_integrations() -> None:
    """Refuse a request-path call that reaches a third party with stored credentials.

    Tasks are covered by the router and workers; this covers the few API routes that
    call a mailbox or a Shopify shop directly. Defence in depth only: on a staging that
    holds a production copy, the network egress allow-list is the boundary.
    """
    if not settings.outbound_integrations_enabled:
        raise OutboundIntegrationsDisabledError()


def cancel_outbound_task(task: ExecutionTask, now: datetime) -> None:
    task.state        = ExecutionTaskStateEnum.CANCEL
    task.last_error   = OUTBOUND_DISABLED_REASON
    task.completed_at = now
    task.worker_id    = None
    task.locked_at    = None
