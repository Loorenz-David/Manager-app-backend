"""Every task type is classified as outbound or internal, and the switch defaults on.

A new TaskType fails here until someone decides whether it reaches a third party,
because staging relies on the outbound set to keep email, Web Push, Shopify and
Scanner traffic from leaving the environment.
"""

from __future__ import annotations

import pytest

from beyo_manager.config import Settings, settings
from beyo_manager.domain.execution.enums import TaskType
from beyo_manager.services.infra.execution.outbound import (
    INTERNAL_TASK_TYPES,
    OUTBOUND_TASK_TYPES,
    outbound_blocked,
)

pytestmark = pytest.mark.unit


def test_every_task_type_is_classified_exactly_once():
    assert OUTBOUND_TASK_TYPES.isdisjoint(INTERNAL_TASK_TYPES)
    assert OUTBOUND_TASK_TYPES | INTERNAL_TASK_TYPES == set(TaskType)


@pytest.mark.parametrize(
    "task_type",
    [
        TaskType.SEND_PUSH_NOTIFICATION,
        TaskType.SEND_EMAIL_MESSAGES,
        TaskType.EMAIL_INBOX_SYNC,
        TaskType.EMAIL_SYNC_TARGETED,
        TaskType.LOCATION_TRACKER_PUSH_LOCATIONS,
        TaskType.SHOPIFY_SYNC_WEBHOOKS_FOR_SHOP,
        TaskType.SHOPIFY_PROCESS_PRODUCTS,
        TaskType.DELIVER_WEBHOOK,
    ],
)
def test_known_third_party_calls_are_outbound(task_type):
    assert task_type in OUTBOUND_TASK_TYPES


@pytest.mark.parametrize(
    "task_type",
    [
        TaskType.CREATE_NOTIFICATIONS,
        TaskType.DELAYED_STEP_COMPLETION,
        TaskType.AUTO_CLOCK_OUT_OPEN_SHIFTS,
        TaskType.STOCK_REPORT_VERSION_ACTIVATION,
        TaskType.PROCESS_STEP_TRANSITION,
        TaskType.RECORD_VIEW_START,
    ],
)
def test_internal_work_is_never_blocked(monkeypatch, task_type):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", False)
    assert outbound_blocked(task_type) is False


def test_outbound_tasks_are_blocked_only_when_the_switch_is_off(monkeypatch):
    monkeypatch.setattr(settings, "outbound_integrations_enabled", True)
    assert not any(outbound_blocked(t) for t in OUTBOUND_TASK_TYPES)

    monkeypatch.setattr(settings, "outbound_integrations_enabled", False)
    assert all(outbound_blocked(t) for t in OUTBOUND_TASK_TYPES)


def test_the_switch_defaults_on_so_hosts_without_it_keep_todays_behaviour(monkeypatch):
    monkeypatch.delenv("OUTBOUND_INTEGRATIONS_ENABLED", raising=False)
    monkeypatch.setenv("SECRET_KEY", "fixture")
    monkeypatch.setenv("JWT_SECRET_KEY", "fixture")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://fixture@127.0.0.1:1/fixture")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    monkeypatch.setenv("CONNECTEAM_WEBHOOK_ENABLED", "false")

    assert Settings(_env_file=None).outbound_integrations_enabled is True

    monkeypatch.setenv("OUTBOUND_INTEGRATIONS_ENABLED", "false")
    assert Settings(_env_file=None).outbound_integrations_enabled is False
