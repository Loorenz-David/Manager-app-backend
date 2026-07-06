# PLAN_task_customer_coordination_email_batch_20260704

## Metadata

- Plan ID: `PLAN_task_customer_coordination_email_batch_20260704`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-04T19:00:00Z`
- Last updated at (UTC): `2026-07-04T13:16:55Z`
- Related issue/ticket: none
- Intention plan: none

## Goal and intent

- Goal: Add a `POST /tasks/customer-coordination/email-batch` endpoint that sends an enriched, per-target email to the customers of a given list of task IDs, using the existing SMTP batch infrastructure and a new reusable content enrichment layer.
- Business/user intent: Let managers send a single templated message (e.g., a pickup notification) to multiple customers at once, with the body automatically personalised per customer/task using `{{var}}` placeholders.
- Non-goals: Content enrichment for entity types other than task/customer/item (future); email scheduling or queuing; modifying `send_email_batch` command internals.

## Scope

- In scope:
  - New `services/infra/email_enrichment/` module with `EnrichmentContext`, `ContentEnricher`, and var-parser registry.
  - Eleven built-in var parsers: `customer_name`, `customer_email`, `customer_phone`, `customer_address`, `task_scheduled_time`, `task_type`, `task_fulfillment_method`, `task_state`, `item_article_number`, `item_sku`, `item_category`.
  - Swedish date/time formatting for `task_scheduled_time`.
  - New command `send_customer_coordination_email_batch` in `services/commands/tasks/`.
  - New request model `SendCustomerCoordinationEmailBatchRequest` in `services/commands/tasks/requests/`.
  - New route `POST /tasks/customer-coordination/email-batch` added to `routers/api_v1/tasks.py` before the `/{task_id}` wildcard group.
  - Audit event `task.customer_coordination.email_batch_sent` registered in `domain/tasks/__init__.py`.
  - Unit tests for the enricher, the var parsers, and the command.

- Out of scope:
  - Changes to `send_email_batch` command or its request model.
  - Enrichment vars for entities beyond task, customer, item.
  - HTML sanitisation of enriched output.
  - IMAP thread-sync for the created threads (callers can use the existing targeted-sync endpoint).

- Assumptions:
  - `TaskCustomerCoordination` may or may not exist for a given task; tasks with no active TCC are skipped.
  - Tasks with no `customer_id`, no associated `Customer`, or a customer with a `None` or empty `primary_email` are skipped with reason logged in the response.
  - Only the most recently created TCC per task is used for entity linkage (`ORDER BY created_at DESC LIMIT 1` per task).
  - The primary task item (`role='primary'`, `removed_at IS NULL`) is used for item vars; if absent, item/item_category vars render as empty string.
  - Enum values are formatted by replacing underscores with spaces and title-casing each word (e.g., `"pickup_at_store"` → `"Pickup At Store"`).
  - Swedish month/weekday names are hardcoded; no locale library dependency.
  - Unknown `{{vars}}` in content are left unchanged (not replaced, not errored).
  - Max 50 task IDs per request (safely within the 200-target batch-send ceiling).

## Clarifications required

_(none — all design decisions are resolved above)_

## Acceptance criteria

1. `POST /tasks/customer-coordination/email-batch` with 3 task IDs where one task has no customer email returns `skipped_count: 1`, `attempted_count: 2`, and correct `thread_client_id` + `message_client_id` per sent result.
2. A `{{customer_name}}` placeholder in `text_body` is replaced with `customer.display_name` for each target independently.
3. A `{{task_scheduled_time}}` placeholder formats Swedish month/day names, omits the year when the scheduled date's year equals the current year, and formats as `"Start → End"` when start ≠ end.
4. `{{unknown_var}}` in content is left unchanged.
5. All eleven built-in vars are covered by unit tests.
6. Route is declared before `/{task_id}` in the router; `GET /tasks/customer-coordination/counts` (already present) remains unaffected.
7. Audit event `task.customer_coordination.email_batch_sent` is written on success.
8. `python3 -m compileall` passes on all new and modified files.
9. Pytest passes on all new test files.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: layering rules, cross-feature borrow discipline
- `backend/architecture/04_context.md`: `ServiceContext` usage
- `backend/architecture/05_errors.md`: `NotFound`, `PermissionDenied`, `DomainError` usage
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: `maybe_begin` transaction rule, subordinate-command pattern, session-call safety
- `backend/architecture/07_queries.md` + `backend/architecture/07_queries_local.md`: offset pagination, query structure
- `backend/architecture/09_routers.md`: handler wiring, static-before-wildcard route ordering
- `backend/architecture/21_naming_conventions.md`: file and symbol naming
- `backend/architecture/40_identity.md`: workspace scoping
- `backend/architecture/41_user.md`: permission guards
- `backend/architecture/42_event.md`: audit event registration and `write_audit` call shape

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: `maybe_begin` owner/subordinate mode, ALL DB reads inside `maybe_begin`, autobegin invariant
- `backend/architecture/07_queries_local.md`: offset replaces cursor pagination

### File read intent — pattern vs. relational

Permitted reads (relational — understanding what exists):
- `models/tables/tasks/task.py` — field names, nullable fields, enum columns
- `models/tables/tasks/task_customer_coordination.py` — `client_id`, `task_id`, `state`, `created_at`
- `models/tables/customers/customer.py` — `primary_email`, `display_name`, `primary_phone_number`, `address`
- `models/tables/items/item.py` — `article_number`, `sku`, `item_category_id`
- `models/tables/items/item_category.py` — `name`
- `models/tables/tasks/task_item.py` — join keys `task_id`, `item_id`, `role`, `removed_at`
- `services/commands/emails/send_email_batch.py` — to understand `_build_target_records` flow and provider call shape (what exists, not how to write)
- `services/infra/email_providers/base.py` — `OutboundMessage`, `BatchSendResult` shapes
- `routers/api_v1/tasks.py` — existing route order to find correct insertion point
- `domain/tasks/enums.py` — enum string values for formatting

Prohibited reads (pattern — contract covers these):
- Any other command file for `session.add / flush` shape → `06_commands.md`
- Any other router file for handler skeleton → `09_routers.md`

### Skill selection

- Primary skill: none specified; follow contracts directly.
- Router trigger terms: `POST`, `/customer-coordination/email-batch`

---

## Implementation plan

### Step 1 — `EnrichmentContext` dataclass

**File**: `app/beyo_manager/services/infra/email_enrichment/context.py` _(new)_

```python
from __future__ import annotations
from dataclasses import dataclass, field

# Import only at TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from beyo_manager.models.tables.tasks.task import Task
    from beyo_manager.models.tables.customers.customer import Customer
    from beyo_manager.models.tables.items.item import Item
    from beyo_manager.models.tables.items.item_category import ItemCategory


@dataclass
class EnrichmentContext:
    task: "Task | None" = None
    customer: "Customer | None" = None
    item: "Item | None" = None
    item_category: "ItemCategory | None" = None
```

**File**: `app/beyo_manager/services/infra/email_enrichment/__init__.py` _(new, empty)_

---

### Step 2 — `ContentEnricher` class

**File**: `app/beyo_manager/services/infra/email_enrichment/enricher.py` _(new)_

```python
import re
from beyo_manager.services.infra.email_enrichment.context import EnrichmentContext

VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class ContentEnricher:
    def __init__(self, var_map: dict):
        # var_map: dict[str, Callable[[EnrichmentContext], str]]
        self._var_map = var_map

    def enrich(self, text: str, context: EnrichmentContext) -> str:
        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            parser = self._var_map.get(var_name)
            if parser is None:
                return match.group(0)  # leave unknown vars unchanged
            return parser(context)
        return VAR_PATTERN.sub(_replace, text)
```

No DB access, no I/O. Pure text transformation.

---

### Step 3 — Customer var parsers

**File**: `app/beyo_manager/services/infra/email_enrichment/var_parsers/__init__.py` _(new, empty)_

**File**: `app/beyo_manager/services/infra/email_enrichment/var_parsers/customer_parsers.py` _(new)_

Parsers to implement (each is `def parser_name(ctx: EnrichmentContext) -> str`):

| var name | source | fallback |
|---|---|---|
| `customer_name` | `ctx.customer.display_name` | `""` |
| `customer_email` | `ctx.customer.primary_email` | `""` |
| `customer_phone` | `ctx.customer.primary_phone_number` | `""` |
| `customer_address` | `ctx.customer.address` (JSON dict) | `""` |

For `customer_address`: join non-None values from keys `["street", "city", "postal_code", "country"]` with `", "`. If none of those keys exist, join all dict values.

```python
def _format_address(address: dict | None) -> str:
    if not address:
        return ""
    parts = [address.get(k) for k in ("street", "city", "postal_code", "country")]
    filtered = [str(p) for p in parts if p]
    if filtered:
        return ", ".join(filtered)
    return ", ".join(str(v) for v in address.values() if v)
```

---

### Step 4 — Item var parsers

**File**: `app/beyo_manager/services/infra/email_enrichment/var_parsers/item_parsers.py` _(new)_

| var name | source | fallback |
|---|---|---|
| `item_article_number` | `ctx.item.article_number` | `""` |
| `item_sku` | `ctx.item.sku` | `""` |
| `item_category` | `ctx.item_category.name` | `""` |

All return `""` when the context field is `None`.

---

### Step 5 — Task var parsers

**File**: `app/beyo_manager/services/infra/email_enrichment/var_parsers/task_parsers.py` _(new)_

| var name | source | notes |
|---|---|---|
| `task_type` | `ctx.task.task_type.value` | enum format |
| `task_fulfillment_method` | `ctx.task.fulfillment_method.value` | enum format, nullable |
| `task_state` | `ctx.task.state.value` | enum format |
| `task_scheduled_time` | `ctx.task.scheduled_start_at` + `ctx.task.scheduled_end_at` | Swedish datetime format |

**Enum formatting helper**:
```python
def _format_enum(value: str) -> str:
    return " ".join(word.capitalize() for word in value.split("_"))
```

**Swedish datetime constants**:
```python
_SWEDISH_MONTHS = [
    "Januari", "Februari", "Mars", "April", "Maj", "Juni",
    "Juli", "Augusti", "September", "Oktober", "November", "December",
]
_SWEDISH_WEEKDAYS = [
    "Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag",
]
```

**`_format_dt(dt: datetime, current_year: int) -> str`** helper:
```python
from datetime import datetime, timezone

def _format_dt(dt: datetime, current_year: int) -> str:
    month = _SWEDISH_MONTHS[dt.month - 1]
    weekday = _SWEDISH_WEEKDAYS[dt.weekday()]  # 0=Monday
    day = dt.day
    if dt.year == current_year:
        return f"{month}, {weekday} {day}"
    return f"{dt.year} {month}, {weekday} {day}"
```

**`task_scheduled_time` parser logic**:
```python
def _parse_task_scheduled_time(ctx: EnrichmentContext) -> str:
    if ctx.task is None:
        return ""
    start = ctx.task.scheduled_start_at
    end = ctx.task.scheduled_end_at
    current_year = datetime.now(timezone.utc).year
    if start is None and end is None:
        return "—"
    if start is None:
        return _format_dt(end, current_year)
    if end is None:
        return _format_dt(start, current_year)
    if start == end:
        return _format_dt(start, current_year)
    return f"{_format_dt(start, current_year)}  →  {_format_dt(end, current_year)}"
```

---

### Step 6 — Var parser registry

**File**: `app/beyo_manager/services/infra/email_enrichment/var_parsers/registry.py` _(new)_

```python
from beyo_manager.services.infra.email_enrichment.var_parsers.customer_parsers import (
    parse_customer_name,
    parse_customer_email,
    parse_customer_phone,
    parse_customer_address,
)
from beyo_manager.services.infra.email_enrichment.var_parsers.item_parsers import (
    parse_item_article_number,
    parse_item_sku,
    parse_item_category,
)
from beyo_manager.services.infra.email_enrichment.var_parsers.task_parsers import (
    parse_task_type,
    parse_task_fulfillment_method,
    parse_task_state,
    parse_task_scheduled_time,
)

VAR_PARSER_MAP: dict = {
    "customer_name": parse_customer_name,
    "customer_email": parse_customer_email,
    "customer_phone": parse_customer_phone,
    "customer_address": parse_customer_address,
    "task_type": parse_task_type,
    "task_fulfillment_method": parse_task_fulfillment_method,
    "task_state": parse_task_state,
    "task_scheduled_time": parse_task_scheduled_time,
    "item_article_number": parse_item_article_number,
    "item_sku": parse_item_sku,
    "item_category": parse_item_category,
}
```

To add a new var in the future: write a parser function in the appropriate `*_parsers.py` file and add it here.

---

### Step 7 — Request model

**File**: `app/beyo_manager/services/commands/tasks/requests/send_customer_coordination_email_batch_request.py` _(new)_

```python
from pydantic import BaseModel, Field, model_validator


class SendCustomerCoordinationEmailBatchRequest(BaseModel):
    connection_client_id: str
    task_ids: list[str] = Field(..., min_length=1, max_length=50)
    subject: str = Field(..., min_length=1, max_length=255)
    text_body: str | None = None
    html_body: str | None = None

    @model_validator(mode="after")
    def require_at_least_one_body(self) -> "SendCustomerCoordinationEmailBatchRequest":
        if self.text_body is None and self.html_body is None:
            raise ValueError("text_body or html_body is required")
        return self
```

---

### Step 8 — Orchestrator command

**File**: `app/beyo_manager/services/commands/tasks/send_customer_coordination_email_batch.py` _(new)_

**ALL DB reads and writes must be inside the single `maybe_begin` block. No `session.execute()` outside it.**

High-level structure:

```python
async def send_customer_coordination_email_batch(ctx: ServiceContext) -> dict:
    request = SendCustomerCoordinationEmailBatchRequest.model_validate(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        # 1. Load connection
        connection = await _load_connection(ctx, request.connection_client_id)
        assert_can_send_from_connection(ctx.user_id, connection.owner_user_id)

        # 2. Load tasks
        tasks = await _load_tasks(ctx, request.task_ids)
        tasks_by_id = {t.client_id: t for t in tasks}

        # 3. Load customers (one query, WHERE client_id IN customer_ids from tasks)
        customer_ids = [t.customer_id for t in tasks if t.customer_id]
        customers_by_id = await _load_customers(ctx, customer_ids)

        # 4. Load most recent TCC per task (one query)
        tccs_by_task_id = await _load_tccs(ctx, request.task_ids)

        # 5. Load primary items + categories for the task_ids (one join query)
        item_ctx_by_task_id = await _load_item_contexts(ctx, request.task_ids)

        # 6. Build enricher from registry
        enricher = ContentEnricher(VAR_PARSER_MAP)

        now = datetime.now(timezone.utc)
        outbound_messages: list[OutboundMessage] = []
        rows: list[dict] = []
        skipped: list[dict] = []

        for task_id in request.task_ids:
            task = tasks_by_id.get(task_id)
            if task is None:
                skipped.append({"task_client_id": task_id, "reason": "task_not_found"})
                continue
            tcc = tccs_by_task_id.get(task_id)
            if tcc is None:
                skipped.append({"task_client_id": task_id, "reason": "no_coordination_record"})
                continue
            customer = customers_by_id.get(task.customer_id) if task.customer_id else None
            if customer is None or not customer.primary_email:
                skipped.append({"task_client_id": task_id, "reason": "no_customer_email"})
                continue

            item_ctx = item_ctx_by_task_id.get(task_id)
            enrich_ctx = EnrichmentContext(
                task=task,
                customer=customer,
                item=item_ctx.item if item_ctx else None,
                item_category=item_ctx.item_category if item_ctx else None,
            )

            enriched_subject = enricher.enrich(request.subject, enrich_ctx)
            enriched_text = enricher.enrich(request.text_body, enrich_ctx) if request.text_body else None
            enriched_html = enricher.enrich(request.html_body, enrich_ctx) if request.html_body else None

            rfc_message_id = f"<{ULID()}@{connection.smtp_host}>"
            thread = EmailThread(
                workspace_id=ctx.workspace_id,
                connection_id=connection.client_id,
                entity_type="task_customer_coordination",
                entity_client_id=tcc.client_id,
                major_entity_type="task",
                major_entity_client_id=task.client_id,
                topic=None,
                subject_normalized=normalize_subject(enriched_subject),
                last_message_at=now,
            )
            ctx.session.add(thread)
            await ctx.session.flush()

            message = EmailMessage(
                workspace_id=ctx.workspace_id,
                connection_id=connection.client_id,
                thread_id=thread.client_id,
                direction=EmailMessageDirectionEnum.OUTBOUND.value,
                from_address=connection.email_address,
                from_name=connection.display_name,
                to_addresses_json=[customer.primary_email],
                cc_addresses_json=[],
                bcc_addresses_json=[],
                subject=enriched_subject,
                text_body=enriched_text,
                html_body=enriched_html,
                body_preview=(enriched_text or "")[:300] or None,
                rfc_message_id=rfc_message_id,
                in_reply_to=None,
                references_json=[],
                sent_or_received_at=now,
                created_by_user_id=ctx.user_id,
            )
            ctx.session.add(message)
            await ctx.session.flush()

            outbound_messages.append(OutboundMessage(
                from_address=connection.email_address,
                from_name=connection.display_name,
                to_addresses=[customer.primary_email],
                cc_addresses=[],
                bcc_addresses=[],
                subject=enriched_subject,
                text_body=enriched_text,
                html_body=enriched_html,
                rfc_message_id=rfc_message_id,
                in_reply_to=None,
                references=[],
            ))
            rows.append({
                "task_client_id": task_id,
                "coordination_client_id": tcc.client_id,
                "thread": thread,
                "message": message,
                "to_address": customer.primary_email,
            })

        # 7. Send batch via SMTP provider
        batch_result = await get_email_provider(connection).send_email_batch(outbound_messages)

        # 8. Map results
        response_results: list[dict] = []
        sent_count = 0
        failed_count = 0
        for row, send_result in zip(rows, batch_result.results, strict=True):
            if send_result.success:
                sent_count += 1
            else:
                failed_count += 1
            response_results.append({
                "task_client_id": row["task_client_id"],
                "coordination_client_id": row["coordination_client_id"],
                "thread_client_id": row["thread"].client_id,
                "message_client_id": row["message"].client_id,
                "to_address": row["to_address"],
                "send_success": send_result.success,
                "send_error": send_result.error,
            })

        response = {
            "attempted_count": len(rows),
            "sent_count": sent_count,
            "failed_count": failed_count,
            "skipped_count": len(skipped),
            "results": response_results,
            "skipped": skipped,
        }

        await write_audit(
            session=ctx.session,
            event="task.customer_coordination.email_batch_sent",
            workspace_id=ctx.workspace_id,
            actor_user_id=ctx.user_id,
            resource_type="email_connection",
            resource_client_id=connection.client_id,
            detail={
                "attempted_count": len(rows),
                "sent_count": sent_count,
                "failed_count": failed_count,
                "skipped_count": len(skipped),
                "connection_id": connection.client_id,
            },
        )

    return response
```

**Private loader functions** (all called inside `maybe_begin`):

`_load_connection(ctx, connection_client_id) -> EmailConnection`:
```python
SELECT EmailConnection
WHERE workspace_id=ctx.workspace_id
  AND client_id=connection_client_id
  AND deleted_at IS NULL
# raise NotFound if None
```

`_load_tasks(ctx, task_ids) -> list[Task]`:
```python
SELECT Task
WHERE workspace_id=ctx.workspace_id
  AND client_id IN task_ids
  AND is_deleted = false
```

`_load_customers(ctx, customer_ids) -> dict[str, Customer]`:
```python
SELECT Customer
WHERE workspace_id=ctx.workspace_id
  AND client_id IN customer_ids
  AND is_deleted = false
# return {c.client_id: c}
```

`_load_tccs(ctx, task_ids) -> dict[str, TaskCustomerCoordination]`:
```python
# Load all TCCs for these task_ids, then in Python take the latest by created_at per task_id
SELECT TaskCustomerCoordination
WHERE workspace_id=ctx.workspace_id
  AND task_id IN task_ids
# group in Python: latest = max by created_at; return {tcc.task_id: latest_tcc}
```

`_load_item_contexts(ctx, task_ids) -> dict[str, _ItemCtx]`:
```python
# _ItemCtx is a local dataclass: item: Item, item_category: ItemCategory | None
SELECT TaskItem JOIN Item JOIN ItemCategory (left join)
WHERE TaskItem.workspace_id=ctx.workspace_id
  AND TaskItem.task_id IN task_ids
  AND TaskItem.role = 'primary'
  AND TaskItem.removed_at IS NULL
  AND Item.is_deleted = false
# return {task_item.task_id: _ItemCtx(item=item, item_category=item_category)}
```

**Imports required**:
```
from datetime import datetime, timezone
from dataclasses import dataclass

from sqlalchemy import select
from ulid import ULID

from beyo_manager.domain.emails.enums import EmailMessageDirectionEnum
from beyo_manager.domain.emails.guards import assert_can_send_from_connection
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_connection import EmailConnection
from beyo_manager.models.tables.emails.email_message import EmailMessage
from beyo_manager.models.tables.emails.email_thread import EmailThread
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_customer_coordination import TaskCustomerCoordination
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_category import ItemCategory
from beyo_manager.services.commands.tasks.requests.send_customer_coordination_email_batch_request import (
    SendCustomerCoordinationEmailBatchRequest,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.audit.write_audit import write_audit
from beyo_manager.services.infra.email_providers.base import OutboundMessage
from beyo_manager.services.infra.email_providers.registry import get_email_provider
from beyo_manager.services.infra.email_providers.smtp_imap.reply_matcher import normalize_subject
from beyo_manager.services.infra.email_enrichment.context import EnrichmentContext
from beyo_manager.services.infra.email_enrichment.enricher import ContentEnricher
from beyo_manager.services.infra.email_enrichment.var_parsers.registry import VAR_PARSER_MAP
```

---

### Step 9 — Router route + audit event registration

**File**: `app/beyo_manager/routers/api_v1/tasks.py` _(modified)_

Add at the top of the import block:
```python
from beyo_manager.services.commands.tasks.send_customer_coordination_email_batch import (
    send_customer_coordination_email_batch,
)
from beyo_manager.services.commands.tasks.requests.send_customer_coordination_email_batch_request import (
    SendCustomerCoordinationEmailBatchRequest,
)
```

Add new route body class (only new fields not already in a command-layer model):

The router uses `SendCustomerCoordinationEmailBatchRequest` directly as the body type — do NOT define a local body class. This is the same discipline applied to `send_email_batch` and `sync_email_threads_batch_targeted`.

Add route before the `/{task_id}` wildcard group (after the existing `/customer-coordination/counts` route at ~line 395):

```python
@router.post("/customer-coordination/email-batch")
async def route_send_customer_coordination_email_batch(
    body: SendCustomerCoordinationEmailBatchRequest,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(send_customer_coordination_email_batch, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Verify**: `POST /tasks/customer-coordination/email-batch` must appear BEFORE `@router.get("/{task_id}")` (line ~398 in current file). Insert after line ~395 (the `route_count_task_customer_coordination_states` function).

**File**: `app/beyo_manager/domain/tasks/__init__.py` _(modified — currently empty)_

```python
from beyo_manager.services.infra.audit.audited_events import register_audited_events

register_audited_events({
    "task.customer_coordination.email_batch_sent",
})
```

---

### Step 10 — Tests

**File**: `tests/email_enrichment/test_content_enricher.py` _(new)_

Cases to cover:
- Known var replaced with parser output.
- Unknown var left unchanged (`{{unknown}}` stays as `{{unknown}}`).
- Multiple vars in one string, all replaced.
- `None` text returns `None` (or caller guards before calling — document which).
- Empty string returns empty string.

**File**: `tests/email_enrichment/test_var_parsers.py` _(new)_

Cases to cover for each parser (use minimal dataclass stubs, not ORM instances — set needed fields directly):

| parser | test case |
|---|---|
| `customer_name` | returns `display_name`; returns `""` when customer is `None` |
| `customer_email` | returns `primary_email` |
| `customer_phone` | returns `primary_phone_number` or `""` |
| `customer_address` | dict with `street`, `city` → `"Storgatan 1, Stockholm"`; `None` → `""` |
| `task_type` | `"pre_order"` → `"Pre Order"` |
| `task_fulfillment_method` | `"pickup_at_store"` → `"Pickup At Store"`; `None` → `""` |
| `task_state` | `"working"` → `"Working"` |
| `task_scheduled_time` | both `None` → `"—"`; same start/end → single formatted date; different start/end → `"start → end"`; same year as current → no year prefix; different year → year prefix |
| `item_article_number` | value or `""` |
| `item_sku` | value or `""` |
| `item_category` | category name or `""` when item_category is `None` |

**File**: `tests/tasks/test_send_customer_coordination_email_batch.py` _(new)_

Test cases:
1. **Happy path (2 tasks, 1 skip)**: mock session returns `connection`, `tasks`, `customers`, `tccs`, `item_contexts`; one task has no customer email → `skipped_count=1`, `attempted_count=1`, correct result shape.
2. **All enriched**: `{{customer_name}}` in `text_body` → replaced per target independently.
3. **Connection not found**: session returns `None` for connection query → `NotFound` raised → `run_service` returns error.
4. **Permission denied**: `connection.owner_user_id != ctx.user_id` and not admin → `PermissionDenied`.
5. **Validation — 0 task_ids**: Pydantic raises before DB → 422 at HTTP layer.
6. **Validation — no body**: neither `text_body` nor `html_body` → Pydantic raises.
7. **SMTP partial failure**: one `SendResult(success=False)` → `failed_count=1`, error captured in result, DB records still committed.

Use same mock-session pattern as `test_email_batch_send.py` (`_Session`, `_Provider`, `_Begin`, `_ScalarResult`).

---

## Risks and mitigations

- Risk: Multiple TCCs per task (no unique constraint on `task_id`).
  Mitigation: Python-side group-by-task_id taking max `created_at`. Document assumption in code comment.

- Risk: `task.customer_id` is not None but customer is soft-deleted (`is_deleted=true`).
  Mitigation: `_load_customers` filters `is_deleted=false`. Customer will be absent from `customers_by_id` → skip with `reason: "no_customer_email"`.

- Risk: `{{` or `}}` in legitimate email content (e.g., CSS styles in HTML body).
  Mitigation: Regex requires `\w+` between `{{` and `}}`. CSS `{}` blocks use single braces — not matched. Double-brace `{{` in non-var context is rare in transactional email. Document limitation.

- Risk: Router insertion point shifts as file grows.
  Mitigation: Plan explicitly names the `route_count_task_customer_coordination_states` function as the insertion anchor. Codex must verify `POST /customer-coordination/email-batch` appears before `@router.get("/{task_id}")`.

- Risk: `send_email_batch` called as a subordinate command (same session) would work, but the content is per-target-enriched so one batch-send call cannot serve all targets with a uniform body.
  Mitigation: The orchestrator calls `get_email_provider(connection).send_email_batch()` (the SMTP layer method) directly — NOT the `send_email_batch` command. DB work (thread/message creation) is done directly in the orchestrator. This is an intentional cross-feature borrow at the infra layer, not a command-to-command call.

- Risk: SMTP sends happen inside `maybe_begin`, holding the DB transaction open during network I/O.
  Mitigation: Accepted trade-off for v1 (same as `send_email_batch`). Future hardening: move provider call after `maybe_begin` exits and handle partial failure with a compensation pass.

---

## Validation plan

```
python3 -m compileall -q \
  app/beyo_manager/services/infra/email_enrichment \
  app/beyo_manager/services/commands/tasks/send_customer_coordination_email_batch.py \
  app/beyo_manager/services/commands/tasks/requests/send_customer_coordination_email_batch_request.py \
  app/beyo_manager/routers/api_v1/tasks.py \
  app/beyo_manager/domain/tasks/__init__.py
```
Expected: no output (no errors).

```
SECRET_KEY=test JWT_SECRET_KEY=test \
DATABASE_URL=postgresql+asyncpg://test:test@localhost/test \
REDIS_URL=redis://localhost:6379/0 \
FIELD_ENCRYPTION_KEY=5bWjAcj8ntcwF3pB1N90J3FJfL4wx0W1K3J2AevM2lM= \
PYTHONPATH=app app/.venv/bin/python -m pytest \
  tests/email_enrichment/ \
  tests/tasks/test_send_customer_coordination_email_batch.py \
  -v
```
Expected: all tests pass.

---

## Review log

_(to be filled after implementation)_

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `david`
