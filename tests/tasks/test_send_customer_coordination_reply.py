from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import EmailThreadEntityTypeEnum
from beyo_manager.domain.items.enums import ItemMajorCategoryEnum, ItemStateEnum
from beyo_manager.domain.tasks.enums import (
    TaskCustomerCoordinationStateEnum,
    TaskFulfillmentMethodEnum,
    TaskItemRoleEnum,
    TaskStateEnum,
    TaskTypeEnum,
)
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.commands.tasks.requests.send_customer_coordination_reply_request import (
    SendCustomerCoordinationReplyRequest,
)
from beyo_manager.services.commands.tasks.send_customer_coordination_reply import (
    send_customer_coordination_reply,
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


class _Session:
    def __init__(self, *, execute_results: list[Any] | None = None):
        self.execute_results = list(execute_results or [])
        self._in_transaction = False

    def in_transaction(self) -> bool:
        return self._in_transaction

    def begin(self):
        session = self

        class _Begin:
            async def __aenter__(self):
                session._in_transaction = True
                return None

            async def __aexit__(self, exc_type, exc, tb):
                session._in_transaction = False
                return False

        return _Begin()

    async def execute(self, _query):
        if self.execute_results:
            return _Result(self.execute_results.pop(0))
        return _Result(None)


def _ctx(session: _Session, incoming_data: dict[str, Any]) -> ServiceContext:
    return ServiceContext(
        identity={"workspace_id": "ws_1", "user_id": "usr_owner", "role_name": "manager"},
        incoming_data=incoming_data,
        session=cast(AsyncSession, session),
    )


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


def _thread(task_id: str, coordination_id: str, *, entity_type: str | None = None) -> EmailThread:
    thread = EmailThread(
        workspace_id="ws_1",
        connection_id="ecn_1",
        entity_type=entity_type or EmailThreadEntityTypeEnum.TASK_CUSTOMER_COORDINATION.value,
        entity_client_id=coordination_id,
        major_entity_type=EmailThreadEntityTypeEnum.TASK.value,
        major_entity_client_id=task_id,
        subject_normalized="hello",
    )
    thread.client_id = "eth_1"
    return thread


def _coordination(task_id: str, coordination_id: str) -> TaskCustomerCoordination:
    coordination = TaskCustomerCoordination(
        workspace_id="ws_1",
        task_id=task_id,
        state=TaskCustomerCoordinationStateEnum.PENDING,
        created_at=datetime(2026, 7, 6, tzinfo=timezone.utc),
    )
    coordination.client_id = coordination_id
    return coordination


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


def _latest_message(subject: str) -> EmailMessage:
    message = EmailMessage(
        workspace_id="ws_1",
        connection_id="ecn_1",
        thread_id="eth_1",
        direction="outbound",
        from_address="sender@example.com",
        subject=subject,
    )
    message.client_id = "emsg_1"
    message.created_at = datetime(2026, 7, 6, tzinfo=timezone.utc)
    return message


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


def test_send_customer_coordination_reply_request_rejects_missing_thread_client_id() -> None:
    with pytest.raises(PydanticValidationError):
        SendCustomerCoordinationReplyRequest.model_validate(
            {
                "task_id": "tsk_1",
                "text_body": "Hello",
            }
        )


def test_send_customer_coordination_reply_request_requires_body() -> None:
    with pytest.raises(PydanticValidationError):
        SendCustomerCoordinationReplyRequest.model_validate(
            {
                "task_id": "tsk_1",
                "thread_client_id": "eth_1",
            }
        )


@pytest.mark.asyncio
async def test_send_customer_coordination_reply_enriches_and_reuses_thread_subject(monkeypatch) -> None:
    session = _Session(
        execute_results=[
            _task("tsk_1", "cus_1"),
            _thread("tsk_1", "tcc_1"),
            _coordination("tsk_1", "tcc_1"),
            _customer("cus_1", email="alpha@example.com"),
            _latest_message("Existing subject"),
            [_item_context_row("tsk_1")],
        ]
    )
    delegated_calls: list[dict] = []

    async def _send_email(delegated_ctx):
        delegated_calls.append(delegated_ctx.incoming_data)
        return {"enqueued": True, "task_client_id": "task_1", "thread_client_id": "eth_1", "message_client_id": "emsg_2"}

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.send_customer_coordination_reply.send_email",
        _send_email,
    )

    result = await send_customer_coordination_reply(
        _ctx(
            session,
            {
                "task_id": "tsk_1",
                "thread_client_id": "eth_1",
                "text_body": "Hi {{customer_name}}, your {{task_type}} is {{task_state}}.",
            },
        )
    )

    assert result["enqueued"] is True
    assert delegated_calls[0]["thread_client_id"] == "eth_1"
    assert delegated_calls[0]["to_addresses"] == ["alpha@example.com"]
    assert delegated_calls[0]["subject"] == "Existing subject"
    assert delegated_calls[0]["text_body"] == "Hi Customer cus_1, your Pre Order is Ready."


@pytest.mark.asyncio
async def test_send_customer_coordination_reply_enriches_subject_override(monkeypatch) -> None:
    session = _Session(
        execute_results=[
            _task("tsk_1", "cus_1"),
            _thread("tsk_1", "tcc_1"),
            _coordination("tsk_1", "tcc_1"),
            _customer("cus_1", email="alpha@example.com"),
            _latest_message("Existing subject"),
            [_item_context_row("tsk_1")],
        ]
    )
    delegated_calls: list[dict] = []

    async def _send_email(delegated_ctx):
        delegated_calls.append(delegated_ctx.incoming_data)
        return {"enqueued": True}

    monkeypatch.setattr(
        "beyo_manager.services.commands.tasks.send_customer_coordination_reply.send_email",
        _send_email,
    )

    await send_customer_coordination_reply(
        _ctx(
            session,
            {
                "task_id": "tsk_1",
                "thread_client_id": "eth_1",
                "subject": "Update for {{customer_name}}",
                "html_body": "<p>{{task_type}} / {{task_state}}</p>",
            },
        )
    )

    assert delegated_calls[0]["subject"] == "Update for Customer cus_1"
    assert delegated_calls[0]["html_body"] == "<p>Pre Order / Ready</p>"


@pytest.mark.asyncio
async def test_send_customer_coordination_reply_rejects_thread_task_mismatch() -> None:
    session = _Session(
        execute_results=[
            _task("tsk_1", "cus_1"),
            _thread("tsk_other", "tcc_1"),
        ]
    )

    with pytest.raises(ValidationError, match="does not belong to the provided task"):
        await send_customer_coordination_reply(
            _ctx(
                session,
                {
                    "task_id": "tsk_1",
                    "thread_client_id": "eth_1",
                    "text_body": "Hello",
                },
            )
        )


@pytest.mark.asyncio
async def test_send_customer_coordination_reply_rejects_non_coordination_thread() -> None:
    session = _Session(
        execute_results=[
            _task("tsk_1", "cus_1"),
            _thread("tsk_1", "tcc_1", entity_type=EmailThreadEntityTypeEnum.CUSTOMER.value),
        ]
    )

    with pytest.raises(ValidationError, match="is not a task customer coordination thread"):
        await send_customer_coordination_reply(
            _ctx(
                session,
                {
                    "task_id": "tsk_1",
                    "thread_client_id": "eth_1",
                    "text_body": "Hello",
                },
            )
        )


@pytest.mark.asyncio
async def test_send_customer_coordination_reply_raises_not_found_when_task_missing() -> None:
    session = _Session(execute_results=[None])

    with pytest.raises(NotFound, match="Task not found"):
        await send_customer_coordination_reply(
            _ctx(
                session,
                {
                    "task_id": "tsk_missing",
                    "thread_client_id": "eth_1",
                    "text_body": "Hello",
                },
            )
        )
