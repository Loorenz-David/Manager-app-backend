from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, ValidationError as PydanticValidationError

from beyo_manager.config import settings
from beyo_manager.domain.connecteam.enums import (
    ConnecteamActivityTypeEnum,
    ConnecteamIntakeOutcomeEnum,
)
from beyo_manager.domain.connecteam.normalize_time_activity_event import normalize_time_activity_event
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.errors.base import DomainError
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.connecteam.webhook_verifier import (
    ConnecteamWebhookAuthError,
    verify_connecteam_webhook,
)
from beyo_manager.services.infra.execution.task_factory import create_instant_task
from beyo_manager.services.infra.redis import get_redis_client
from beyo_manager.services.infra.redis.keys import make_key
from beyo_manager.core.logging.config import log_event

logger = logging.getLogger(__name__)

__all__ = [
    "ConnecteamWebhookAuthError",
    "ConnecteamWebhookUnavailable",
    "InvalidConnecteamWebhookRequest",
    "UnsupportedConnecteamWebhookPayload",
    "enqueue_connecteam_time_activity_webhook",
]


class InvalidConnecteamWebhookRequest(DomainError):
    http_status = 400


class UnsupportedConnecteamWebhookPayload(DomainError):
    http_status = 422


class ConnecteamWebhookUnavailable(DomainError):
    http_status = 503


class ConnecteamWebhookRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    raw_body: bytes
    headers: dict[str, str]


@dataclass(frozen=True)
class ConnecteamWebhookAcceptance:
    event_key: str
    outcome: ConnecteamIntakeOutcomeEnum


def _parse(data: dict) -> ConnecteamWebhookRequest:
    try:
        return ConnecteamWebhookRequest.model_validate(data)
    except PydanticValidationError as exc:
        raise InvalidConnecteamWebhookRequest("Webhook request is invalid.") from exc


def _redis_client():
    if not settings.redis_url:
        return None
    try:
        return get_redis_client(settings.redis_url)
    except Exception:
        logger.warning("connecteam_webhook_dedup_degraded")
        return None


async def enqueue_connecteam_time_activity_webhook(ctx: ServiceContext) -> dict:
    request = _parse(ctx.incoming_data)
    if not settings.connecteam_webhook_enabled:
        raise ConnecteamWebhookUnavailable("Connecteam webhook integration is disabled.")

    # Authentication must precede JSON parsing and all persistence.
    verify_connecteam_webhook(request.raw_body, request.headers)
    log_event("connecteam_webhook_received", provider="connecteam", body_length=len(request.raw_body))
    try:
        payload = json.loads(request.raw_body)
    except (TypeError, ValueError) as exc:
        raise InvalidConnecteamWebhookRequest("Malformed webhook JSON.") from exc
    if not isinstance(payload, dict):
        raise InvalidConnecteamWebhookRequest("Webhook JSON must be an object.")

    try:
        event = normalize_time_activity_event(request.raw_body, payload)
    except DomainError as exc:
        raise UnsupportedConnecteamWebhookPayload(str(exc)) from exc

    if event.supported_event_type is None:
        log_event("connecteam_webhook_rejected", provider="connecteam", event_key=event.event_key,
                  connecteam_event_type=event.event_type, processing_status="unsupported_event_type")
        return {"event_key": event.event_key, "outcome": ConnecteamIntakeOutcomeEnum.UNSUPPORTED_EVENT_TYPE.value}
    if event.activity == ConnecteamActivityTypeEnum.MANUAL_BREAK:
        log_event("connecteam_webhook_rejected", provider="connecteam", event_key=event.event_key,
                  connecteam_event_type=event.event_type, activity_type=event.activity_type,
                  processing_status="ignored_activity_type")
        return {"event_key": event.event_key, "outcome": ConnecteamIntakeOutcomeEnum.IGNORED_ACTIVITY_TYPE.value}

    dedup_key = make_key("connecteam", "webhooks", "dedup", event.event_key)
    redis_client = _redis_client()
    dedup_claimed = True
    if redis_client is not None:
        try:
            dedup_claimed = bool(redis_client.set(dedup_key, "1", nx=True, ex=900))
        except Exception:
            dedup_claimed = True
            logger.warning("connecteam_webhook_dedup_degraded", extra={"event_key": event.event_key})
    if not dedup_claimed:
        log_event("connecteam_webhook_duplicate", provider="connecteam", event_key=event.event_key,
                  processing_status="duplicate")
        return {"event_key": event.event_key, "outcome": ConnecteamIntakeOutcomeEnum.DUPLICATE.value}

    try:
        async with maybe_begin(ctx.session):
            await create_instant_task(
                session=ctx.session,
                task_type=TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY,
                payload=event.as_payload(),
                max_try=5,
            )
    except Exception as exc:
        if redis_client is not None:
            try:
                redis_client.delete(dedup_key)
            except Exception:
                pass
        raise ConnecteamWebhookUnavailable("Connecteam webhook could not be durably accepted.") from exc

    if redis_client is not None:
        try:
            redis_client.expire(dedup_key, settings.connecteam_webhook_dedup_ttl_seconds)
        except Exception:
            logger.warning("connecteam_webhook_dedup_degraded", extra={"event_key": event.event_key})
    log_event("connecteam_webhook_enqueued", provider="connecteam", event_key=event.event_key,
              request_id=event.request_id, connecteam_event_type=event.event_type,
              activity_type=event.activity_type, processing_status="accepted")
    return {"event_key": event.event_key, "outcome": ConnecteamIntakeOutcomeEnum.ACCEPTED.value}
