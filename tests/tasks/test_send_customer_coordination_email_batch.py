from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import EmailConnectionStatusEnum, EmailProviderTypeEnum
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum, ItemStateEnum
from beyo_manager.domain.tasks.enums import (
    TaskFulfillmentMethodEnum,
    TaskCustomerCoordinationStateEnum,
    TaskItemRoleEnum,
    TaskStateEnum,
    TaskTypeEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.permissions import PermissionDenied
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.tasks.requests.send_customer_coordination_email_batch_request import (
    SendCustomerCoordinationEmailBatchRequest,
)
from beyo_manager.services.commands.tasks.send_customer_coordination_email_batch import (
    send_customer_coordination_email_batch,
)
from beyo_manager.services.context import ServiceContext


class _ScalarList:
    def __init__(self, values: list[Any]):
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class _Result:
    def __init__(self, value: Any):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self) -> _ScalarList:
        if self._value is None:
            return _ScalarList([])
        if isinstance(self._value, list):
            return _ScalarList(self._value)
        return _ScalarList([self._value])

    def all(self) -> list[Any]:
        if self._value is None:
            return []
        return list(self._value)


class _Begin:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Session:
    def __init__(self, *, execute_results: list[Any] | None = None):
        self.execute_results = list(execute_results or [])
        self.added: list[Any] = []
        self.flush_calls = 0

    def in_transaction(self) -> bool:
        return False

    def begin(self):
        return _Begin()

    async def execute(self, _query):
        if self.execute_results:
            return _Result(self.execute_results.pop(0))
        return _Result(None)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_calls += 1
        for obj in self.added:
            if isinstance(obj, EmailThread) and not getattr(obj, "client_id", None):
                obj.client_id = f"eth_{self.flush_calls:02d}"
            if isinstance(obj, EmailMessage) and not getattr(obj, "client_id", None):
                obj.client_id = f"emsg_{self.flush_calls:02d}"


def _ctx(session: _Session, incoming_data: dict[str, Any], *, user_id: str = "usr_owner") -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": "ws_1", "user_id": user_id, "role_name": "manager"},
        incoming_data=incoming_data,
        session=cast(AsyncSession, session),
    )


def _connection(*, owner_user_id: str = "usr_owner") -> EmailConnection:
    connection = EmailConnection(
        workspace_id="ws_1",
        owner_user_id=owner_user_id,
        email_address="sender@example.com",
        display_name="Sender",
        provider_type=EmailProviderTypeEnum.SMTP_IMAP.value,
        status=EmailConnectionStatusEnum.ACTIVE.value,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_security="starttls",
        smtp_username="sender@example.com",
        smtp_password_encrypted="encrypted",
        imap_host="imap.example.com",
        imap_port=993,
        imap_security="ssl",
        imap_username="sender@example.com",
        imap_password_encrypted="encrypted",
        inbox_folder="INBOX",
    )
    connection.client_id = "ecn_1"
    return connection


def _task(task_id: str, customer_id: str | None) -> Task:
    year = datetime.now(timezone.utc).year
    task = Task(
        workspace_id="ws_1",
        task_scalar_id=1,
        task_type=TaskTypeEnum.PRE_ORDER,
        state=TaskStateEnum.READY,
        customer_id=customer_id,
        fulfillment_method=TaskFulfillmentMethodEnum.PICKUP_AT_STORE,
        scheduled_start_at=datetime(year, 7, 4, tzinfo=timezone.utc),
        scheduled_end_at=datetime(year, 7, 5, tzinfo=timezone.utc),
    )
    task.client_id = task_id
    return task


def _customer(customer_id: str, *, email: str | None) -> Customer:
    customer = Customer(
        workspace_id="ws_1",
        display_name=f"Customer {customer_id}",
        primary_email=email,
        primary_phone_number="+46701234567",
        address={"street": "Storgatan 1", "city": "Stockholm"},
    )
    customer.client_id = customer_id
    return customer


def _coordination(task_id: str, coordination_id: str, created_at: datetime) -> TaskCustomerCoordination:
    coordination = TaskCustomerCoordination(
        workspace_id="ws_1",
        task_id=task_id,
        state=TaskCustomerCoordinationStateEnum.PENDING,
        created_at=created_at,
    )
    coordination.client_id = coordination_id
    return coordination


def _item_context_row(task_id: str) -> tuple[TaskItem, Item, ItemCategory]:
    task_item = TaskItem(
        workspace_id="ws_1",
        task_id=task_id,
        item_id="itm_1",
        role=TaskItemRoleEnum.PRIMARY,
    )
    item = Item(workspace_id="ws_1", article_number="ART-1", sku="SKU-1", state=ItemStateEnum.PENDING)
    item.client_id = "itm_1"
    category = ItemCategory(workspace_id="ws_1", name="Sofas", major_category=ItemMajorCategoryEnum.SEAT)
    category.client_id = "itc_1"
    return task_item, item, category


@pytest.mark.asyncio
async def test_send_customer_coordination_email_batch_enriches_per_target_and_skips_missing_email(
    monkeypatch,
) -> None:
    session = _Session(
        execute_results=[
            _connection(),
            [_task("tsk_1", "cus_1"), _task("tsk_2", "cus_2")],
            [_customer("cus_1", email="alpha@example.com"), _customer("cus_2", email=None)],
            [
                _coordination("tsk_1", "tcc_1", datetime(2026, 7, 1, tzinfo=timezone.utc)),
                _coordination("tsk_2", "tcc_2", datetime(2026, 7, 2, tzinfo=timezone.utc)),
            ],
            [_item_context_row("tsk_1"), _item_context_row("tsk_2")],
        ]
    )
    create_task_calls: list[dict] = []

    async def _create_instant_task(**kwargs):
        create_task_calls.append(kwargs)

        class _Task:
            client_id = "task_1"

        return _Task()

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.send_customer_coordination_email_batch.create_instant_task",
        _create_instant_task,
    )

    result = await send_customer_coordination_email_batch(
        _ctx(
            session,
            {
                "connection_client_id": "ecn_1",
                "task_ids": ["tsk_1", "tsk_2"],
                "subject": "Hej {{customer_name}}",
                "text_body": "Din {{task_type}} är {{task_state}} för {{task_scheduled_time}}.",
            },
        )
    )

    assert result["job_id"] == "task_1"
    assert result["status"] == "queued"
    assert result["queued_count"] == 1
    assert result["skipped_count"] == 1
    assert result["skipped"] == [{"task_client_id": "tsk_2", "reason": "no_customer_email"}]
    created_messages = [item for item in session.added if isinstance(item, EmailMessage)]
    assert len(created_messages) == 1
    assert created_messages[0].subject == "Hej Customer cus_1"
    assert "Pre Order" in (created_messages[0].text_body or "")
    assert "Ready" in (created_messages[0].text_body or "")
    assert "{{" not in (created_messages[0].text_body or "")
    assert create_task_calls[0]["task_type"].value == "send_email_messages"
    assert create_task_calls[0]["payload"]["message_ids"] == ["emsg_02"]
    assert create_task_calls[0]["payload"]["request_kind"] == "coordination_batch"


@pytest.mark.asyncio
async def test_send_customer_coordination_email_batch_raises_not_found_when_connection_missing() -> None:
    session = _Session(execute_results=[None])

    with pytest.raises(NotFound):
        await send_customer_coordination_email_batch(
            _ctx(
                session,
                {
                    "connection_client_id": "ecn_missing",
                    "task_ids": ["tsk_1"],
                    "text_body": "Hello",
                    "subject": "Hi",
                },
            )
        )


@pytest.mark.asyncio
async def test_send_customer_coordination_email_batch_raises_permission_denied_for_other_owner() -> None:
    session = _Session(execute_results=[_connection(owner_user_id="usr_other")])

    with pytest.raises(PermissionDenied):
        await send_customer_coordination_email_batch(
            _ctx(
                session,
                {
                    "connection_client_id": "ecn_1",
                    "task_ids": ["tsk_1"],
                    "text_body": "Hello",
                    "subject": "Hi",
                },
                user_id="usr_owner",
            )
        )


def test_send_customer_coordination_email_batch_request_rejects_empty_task_ids() -> None:
    with pytest.raises(PydanticValidationError):
        SendCustomerCoordinationEmailBatchRequest.model_validate(
            {
                "connection_client_id": "ecn_1",
                "task_ids": [],
                "subject": "Hi",
                "text_body": "Hello",
            }
        )


def test_send_customer_coordination_email_batch_request_requires_body() -> None:
    with pytest.raises(PydanticValidationError):
        SendCustomerCoordinationEmailBatchRequest.model_validate(
            {
                "connection_client_id": "ecn_1",
                "task_ids": ["tsk_1"],
                "subject": "Hi",
            }
        )


@pytest.mark.asyncio
async def test_auto_resolves_connection_when_connection_client_id_omitted(monkeypatch) -> None:
    session = _Session(
        execute_results=[
            [_connection()],
            [],
            [],
            [],
            [],
        ]
    )
    async def _create_instant_task(**kwargs):
        class _Task:
            client_id = "task_1"

        return _Task()

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.send_customer_coordination_email_batch.create_instant_task",
        _create_instant_task,
    )

    result = await send_customer_coordination_email_batch(
        _ctx(
            session,
            {
                "task_ids": ["tsk_missing"],
                "subject": "Hi",
                "text_body": "Hello",
            },
        )
    )

    assert result["skipped_count"] == 1
    assert result["skipped"][0]["reason"] == "task_not_found"


@pytest.mark.asyncio
async def test_auto_resolve_raises_not_found_when_no_active_connection() -> None:
    session = _Session(execute_results=[[]])

    with pytest.raises(NotFound, match="No active email connection"):
        await send_customer_coordination_email_batch(
            _ctx(
                session,
                {
                    "task_ids": ["tsk_1"],
                    "subject": "Hi",
                    "text_body": "Hello",
                },
            )
        )


@pytest.mark.asyncio
async def test_auto_resolve_raises_validation_error_when_multiple_connections() -> None:
    session = _Session(execute_results=[[_connection(), _connection()]])

    with pytest.raises(ValidationError, match="Multiple email connections"):
        await send_customer_coordination_email_batch(
            _ctx(
                session,
                {
                    "task_ids": ["tsk_1"],
                    "subject": "Hi",
                    "text_body": "Hello",
                },
            )
        )
