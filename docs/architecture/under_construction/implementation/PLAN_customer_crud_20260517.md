# PLAN_customer_crud_20260517

## Metadata

- Plan ID: `PLAN_customer_crud_20260517`
- Status: `under_construction`
- Owner agent: `Claude Sonnet 4.6`
- Created at (UTC): `2026-05-17T20:00:00Z`
- Last updated at (UTC): `2026-05-17T20:00:00Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/atomic_cmd_costumer.md`

---

## Goal and intent

- **Goal:** Deliver CMD-1 through CMD-4 (customer create, update, delete, find-or-create), QUERY-1 (list customers with `q` filter and pagination), and QUERY-2 (get customer by ID with linked items), plus the customers router and domain serializers.
- **Business/user intent:** Customers are the root entity behind every task. Without atomic customer commands and lookup, task commands cannot link items to a customer in one step. The find-or-create command (CMD-4) is the primary entry point for task flows — it avoids duplicate creation when a customer contacts the workshop more than once.
- **Non-goals:** History record creation (`CustomerHistoryRecord` is nullable — history is a follow-up concern); `CustomerStatusEnum` transitions; merging/redacting/anonymizing customers; customer search by `customer_type`; any migration (no new columns or tables needed).

---

## Scope

- **In scope:**
  - New package: `services/commands/customers/` (with `__init__.py`)
  - New package: `services/commands/customers/requests/` (with `__init__.py` containing all request models and parsers)
  - New command: `create_customer.py` (CMD-1)
  - New command: `update_customer.py` (CMD-2)
  - New command: `delete_customer.py` (CMD-3)
  - New command: `find_or_create_customer.py` (CMD-4)
  - New package: `services/queries/customers/` (with `__init__.py`)
  - New query file: `services/queries/customers/customers.py` (QUERY-1 + QUERY-2)
  - New serializer file: `domain/customers/serializers.py`
  - New router: `routers/api_v1/customers.py`
  - Router registration: `routers/api_v1/__init__.py`

- **Out of scope:** Alembic migration (all required models exist); `CustomerHistoryRecord` writes; customer status transitions; task CRUD; item CRUD (only reads items in QUERY-2).

- **Assumptions:**
  - `Customer` model exists at `beyo_manager.models.tables.customers.customer` with all columns as observed.
  - `Task` model exists at `beyo_manager.models.tables.tasks.task` and has `customer_id` FK to customers and `is_deleted` column.
  - `TaskItem` model exists at `beyo_manager.models.tables.tasks.task_item` and has `task_id`, `item_id`, `removed_at` (null = active).
  - `Item` model exists at `beyo_manager.models.tables.items.item` with `is_deleted`.
  - `maybe_begin` exists at `beyo_manager.services.commands.utils.transaction`.
  - `apply_string_filter` exists at `beyo_manager.services.queries.utils.string_filter` with signature `(stmt, q, string_filters, allowed_columns: dict[str, InstrumentedAttribute]) -> Select`.
  - `serialize_item_list(item, issue_count: int) -> dict` exists at `beyo_manager.domain.items.serializers`.

---

## Clarifications required

None — all design questions resolved during planning.

---

## Acceptance criteria

1. `PUT /api/v1/customers` creates a Customer; returns `{"data": {"client_id": "cus_..."}}`. Requires `display_name` and at least one of `primary_email` or `primary_phone_number` — omitting both raises a `ValidationError` before any DB write.
2. `PATCH /api/v1/customers/{client_id}` updates only fields explicitly present in the payload; absent fields are unchanged; null in payload clears the column; returns `{"data": {"client_id": "cus_..."}}`.
3. `DELETE /api/v1/customers/{client_id}` soft-deletes the customer; returns `{"data": {}}`.
4. `POST /api/v1/customers/find-or-create` returns an existing active customer if one matches the normalized email or phone; creates and returns a new one otherwise; response is `{"data": {"client_id": "cus_...", "was_created": true|false}}`.
5. `GET /api/v1/customers` returns `{"data": {"customers_pagination": {"items": [...], "limit": int, "offset": int, "has_more": bool}}}` where `q` filters across `display_name`, `primary_email`, `primary_phone_number`.
6. `GET /api/v1/customers/{client_id}` returns `{"data": {"customer": {..., "linked_items": [...]}}}` where `linked_items` are distinct items reached via `Task.customer_id → TaskItem.item_id`, each serialized with `serialize_item_list(item, issue_count)`.
7. Import smoke test passes: `.venv/bin/python -c "from beyo_manager import create_app; create_app(); print('OK')"`.

---

## Contracts and skills

### Contracts loaded

**Read order (canonical first, local second):**

- `backend/architecture/01_architecture.md` (baseline): layer rules, folder structure.
- `backend/architecture/04_context.md` (baseline): `ServiceContext` shape — `incoming_data`, `query_params`, `identity`, `session`.
- `backend/architecture/05_errors.md` (baseline): `NotFound`, `ValidationError`, `ConflictError` — import paths.
- `backend/architecture/06_commands.md` (baseline): command skeleton, transaction pattern, request parser pattern.
- `backend/architecture/06_commands_local.md` (local delta): **ALL commands use `maybe_begin` instead of `ctx.session.begin()`**; session call safety table; one `maybe_begin` per function, no manual commit/rollback.
- `backend/architecture/07_queries.md` (baseline): query signature, `select()` pattern, result extraction.
- `backend/architecture/07_queries_local.md` (local delta): **offset-based pagination only** — `limit + 1` trick; completion gate checklist.
- `backend/architecture/09_routers.md` (baseline): handler skeleton, `run_service`, `build_ok`/`build_err`, static routes before wildcard, `body.model_dump(exclude_unset=True)` for PATCH.
- `backend/architecture/21_naming_conventions.md` (baseline): file naming, constant naming, prefix conventions.
- `backend/architecture/08_domain.md` (baseline): serializers in `domain/<domain>/serializers.py`, pure functions.
- `backend/architecture/46_serialization.md` (baseline): serializers are pure functions; services return `dict` for commands.
- `backend/architecture/55_query_filters_local.md` (local-only): `apply_string_filter` signature and usage; `max_length=200` on router `q` param.

### Local extensions loaded

- `06_commands_local.md`: `maybe_begin` replaces `ctx.session.begin()` everywhere; session call safety.
- `07_queries_local.md`: offset pagination; `limit + 1` detection pattern.
- `55_query_filters_local.md`: `apply_string_filter` for same-table columns — QUERY-1 is fully covered (all filtered columns are on `customers`).

### File read intent — pattern vs. relational

**Prohibited (pattern reads):**
- Reading another command file to understand `session.add` / `flush` shape → read `06_commands.md`.
- Reading another router to understand handler shape → read `09_routers.md`.
- Reading another serializer to understand output shape → read `46_serialization.md`.

**Permitted (relational reads):**
- `backend/app/beyo_manager/models/tables/customers/customer.py` — exact column names, types.
- `backend/app/beyo_manager/models/tables/tasks/task.py` — `customer_id`, `is_deleted` columns.
- `backend/app/beyo_manager/models/tables/tasks/task_item.py` — `task_id`, `item_id`, `removed_at` columns.
- `backend/app/beyo_manager/models/tables/items/item.py` — `is_deleted`, `workspace_id` for QUERY-2 join.
- `backend/app/beyo_manager/domain/customers/enums.py` — `CustomerTypeEnum`, `CustomerStatusEnum`.
- `backend/app/beyo_manager/domain/items/serializers.py` — confirm `serialize_item_list(item, issue_count)` signature.
- `backend/app/beyo_manager/services/queries/utils/string_filter.py` — confirm `apply_string_filter` signature before calling.
- `backend/app/beyo_manager/routers/api_v1/__init__.py` — existing registration block to extend.

### Skill selection

- Primary skill: Backend CRUD + domain commands.
- Excluded: worker, background jobs, redis, websockets — none required.

---

## Implementation plan

### Step 0 — Pre-condition verification

```bash
grep -r "def maybe_begin" backend/app/beyo_manager/services/commands/utils/
grep -r "def apply_string_filter" backend/app/beyo_manager/services/queries/utils/
grep -r "def serialize_item_list" backend/app/beyo_manager/domain/items/
```

Expected: one match each. If absent, stop and implement the missing prerequisite first.

---

### Step 1 — Create package directories

Create the following empty files (package init files):

- `backend/app/beyo_manager/services/commands/customers/__init__.py` — empty
- `backend/app/beyo_manager/services/commands/customers/requests/__init__.py` — content in Step 2
- `backend/app/beyo_manager/services/queries/customers/__init__.py` — empty

---

### Step 2 — Create `services/commands/customers/requests/__init__.py`

**File:** `backend/app/beyo_manager/services/commands/customers/requests/__init__.py`

```python
"""Request models for customer commands."""

from decimal import Decimal

from pydantic import BaseModel, field_validator, model_validator

from beyo_manager.domain.customers.enums import CustomerStatusEnum, CustomerTypeEnum
from beyo_manager.errors.validation import ValidationError


# ── Normalization helpers ──────────────────────────────────────────────────────

def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized if normalized else None


def _normalize_phone(phone: str | None) -> str | None:
    if phone is None:
        return None
    normalized = "".join(c for c in phone if c.isdigit() or c == "+").strip()
    return normalized if normalized else None


# ── Request models ─────────────────────────────────────────────────────────────

class CreateCustomerRequest(BaseModel):
    display_name: str
    customer_type: CustomerTypeEnum = CustomerTypeEnum.UNKNOWN
    primary_email: str | None = None
    primary_phone_number: str | None = None
    address: dict | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def strip_display_name(cls, v) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("display_name must not be blank.")
        return v

    @field_validator("primary_email", mode="before")
    @classmethod
    def normalize_email(cls, v) -> str | None:
        return _normalize_email(v)

    @field_validator("primary_phone_number", mode="before")
    @classmethod
    def normalize_phone(cls, v) -> str | None:
        return _normalize_phone(v)

    @model_validator(mode="after")
    def require_at_least_one_contact(self) -> "CreateCustomerRequest":
        if self.primary_email is None and self.primary_phone_number is None:
            raise ValueError(
                "At least one of primary_email or primary_phone_number must be provided."
            )
        return self

    @property
    def primary_email_normalized(self) -> str | None:
        return self.primary_email  # already normalized by validator

    @property
    def primary_phone_number_normalized(self) -> str | None:
        return self.primary_phone_number  # already normalized by validator


class UpdateCustomerRequest(BaseModel):
    client_id: str
    display_name: str | None = None
    customer_type: CustomerTypeEnum | None = None
    status: CustomerStatusEnum | None = None
    primary_email: str | None = None
    primary_phone_number: str | None = None
    address: dict | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def strip_display_name(cls, v) -> str | None:
        if v is None:
            return None
        v = str(v).strip()
        return v if v else None

    @field_validator("primary_email", mode="before")
    @classmethod
    def normalize_email(cls, v) -> str | None:
        return _normalize_email(v)

    @field_validator("primary_phone_number", mode="before")
    @classmethod
    def normalize_phone(cls, v) -> str | None:
        return _normalize_phone(v)


class DeleteCustomerRequest(BaseModel):
    client_id: str


class FindOrCreateCustomerRequest(BaseModel):
    display_name: str
    primary_email: str | None = None
    primary_phone_number: str | None = None
    customer_type: CustomerTypeEnum = CustomerTypeEnum.UNKNOWN
    address: dict | None = None

    @field_validator("display_name", mode="before")
    @classmethod
    def strip_display_name(cls, v) -> str:
        v = str(v).strip()
        if not v:
            raise ValueError("display_name must not be blank.")
        return v

    @field_validator("primary_email", mode="before")
    @classmethod
    def normalize_email(cls, v) -> str | None:
        return _normalize_email(v)

    @field_validator("primary_phone_number", mode="before")
    @classmethod
    def normalize_phone(cls, v) -> str | None:
        return _normalize_phone(v)


# ── Parse functions ────────────────────────────────────────────────────────────

def parse_create_customer_request(data: dict) -> CreateCustomerRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return CreateCustomerRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_update_customer_request(data: dict) -> UpdateCustomerRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return UpdateCustomerRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_delete_customer_request(data: dict) -> DeleteCustomerRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return DeleteCustomerRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_find_or_create_customer_request(data: dict) -> FindOrCreateCustomerRequest:
    from pydantic import ValidationError as PydanticValidationError
    try:
        return FindOrCreateCustomerRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
```

**Normalization rules:**
- `primary_email`: `.strip().lower()` — run through `_normalize_email`; stored in both `primary_email` (as-received after strip) and `primary_email_normalized` (lowercased, stripped).
- `primary_phone_number`: strip all characters except digits and `+` — run through `_normalize_phone`. This produces a consistent lookup key independent of formatting (spaces, dashes, parentheses).
- Both normalizations are applied in validators, so the resulting field values ARE already normalized on the request object.

**Important:** `_normalize_email` and `_normalize_phone` are used in both the request models (via validators) and directly in `find_or_create_customer.py` for the DB lookup. Do not duplicate the logic — import them: `from beyo_manager.services.commands.customers.requests import _normalize_email, _normalize_phone`.

---

### Step 3 — Create `domain/customers/serializers.py`

**File:** `backend/app/beyo_manager/domain/customers/serializers.py`

```python
"""Serializers for the customers domain."""

from beyo_manager.domain.items.serializers import serialize_item_list
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.items.item import Item


def serialize_customer(customer: Customer) -> dict:
    return {
        "client_id": customer.client_id,
        "workspace_id": customer.workspace_id,
        "display_name": customer.display_name,
        "customer_type": customer.customer_type.value,
        "status": customer.status.value,
        "primary_email": customer.primary_email,
        "primary_phone_number": customer.primary_phone_number,
        "primary_email_normalized": customer.primary_email_normalized,
        "primary_phone_number_normalized": customer.primary_phone_number_normalized,
        "address": customer.address,
        "latest_history_record_id": customer.latest_history_record_id,
        "created_at": customer.created_at.isoformat(),
        "created_by_id": customer.created_by_id,
        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
        "updated_by_id": customer.updated_by_id,
    }


def serialize_customer_detail(
    customer: Customer,
    items: list[Item],
    issue_counts: dict[str, int],
) -> dict:
    return {
        **serialize_customer(customer),
        "linked_items": [
            serialize_item_list(item, issue_counts.get(item.client_id, 0))
            for item in items
        ],
    }
```

**Notes:**
- `serialize_customer_detail` is used only by QUERY-2. `issue_counts` is a `dict[item_client_id → count]` batch-loaded before calling this function — never compute counts inside the serializer.
- `serialize_item_list` is imported from the items domain — this is a cross-domain read, which is acceptable here because items are part of the customer detail response.

---

### Step 4 — Create `create_customer.py` (CMD-1)

**File:** `backend/app/beyo_manager/services/commands/customers/create_customer.py`

```python
"""CMD-1: Create a Customer."""

from datetime import datetime, timezone

from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.services.commands.customers.requests import parse_create_customer_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_customer(ctx: ServiceContext) -> dict:
    """Create a new Customer with normalized contact fields."""
    request = parse_create_customer_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        customer = Customer(
            workspace_id=ctx.workspace_id,
            display_name=request.display_name,
            customer_type=request.customer_type,
            primary_email=request.primary_email,
            primary_phone_number=request.primary_phone_number,
            primary_email_normalized=request.primary_email_normalized,
            primary_phone_number_normalized=request.primary_phone_number_normalized,
            address=request.address,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(customer)
        await ctx.session.flush()

    return {"client_id": customer.client_id}
```

**Notes:**
- `primary_email_normalized` and `primary_phone_number_normalized` are set from the validated (already-normalized) properties on the request model.
- No existence check needed — duplicates are allowed at the model level (no unique constraint on contact fields). CMD-4 (find-or-create) is the deduplication entry point.
- `status` defaults to `CustomerStatusEnum.ACTIVE` via the model default — do not pass it here.

---

### Step 5 — Create `update_customer.py` (CMD-2)

**File:** `backend/app/beyo_manager/services/commands/customers/update_customer.py`

```python
"""CMD-2: Update Customer fields — null vs omit via model_fields_set."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.services.commands.customers.requests import parse_update_customer_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


_DIRECT_FIELDS = {
    "display_name",
    "customer_type",
    "status",
    "primary_email",
    "primary_phone_number",
    "address",
}


async def update_customer(ctx: ServiceContext) -> dict:
    """Update Customer — only fields present in the request payload are written."""
    request = parse_update_customer_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Customer).where(
                Customer.workspace_id == ctx.workspace_id,
                Customer.client_id == request.client_id,
                Customer.is_deleted.is_(False),
            )
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise NotFound("Customer not found.")

        for field_name in _DIRECT_FIELDS:
            if field_name in request.model_fields_set:
                setattr(customer, field_name, getattr(request, field_name))

        # Keep normalized columns in sync whenever contact fields are updated
        if "primary_email" in request.model_fields_set:
            customer.primary_email_normalized = request.primary_email  # already normalized by validator
        if "primary_phone_number" in request.model_fields_set:
            customer.primary_phone_number_normalized = request.primary_phone_number  # already normalized

        customer.updated_at = datetime.now(timezone.utc)
        customer.updated_by_id = ctx.user_id

    return {"client_id": customer.client_id}
```

**`model_fields_set` rule:** The router passes `body.model_dump(exclude_unset=True)`. The parser calls `model_validate(data)`. Only explicitly-provided fields appear in `model_fields_set`. Absent fields are not written; explicit nulls clear the column.

**Normalized sync:** When `primary_email` is in `model_fields_set`, the request validator has already normalized it, so `request.primary_email` is the normalized value. Setting `primary_email_normalized = request.primary_email` is correct — both store the same normalized value.

---

### Step 6 — Create `delete_customer.py` (CMD-3)

**File:** `backend/app/beyo_manager/services/commands/customers/delete_customer.py`

```python
"""CMD-3: Soft-delete a Customer."""

from datetime import datetime, timezone

from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.services.commands.customers.requests import parse_delete_customer_request
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def delete_customer(ctx: ServiceContext) -> dict:
    """Soft-delete a Customer. Does not cascade to linked tasks or items."""
    request = parse_delete_customer_request(ctx.incoming_data)

    async with maybe_begin(ctx.session):
        result = await ctx.session.execute(
            select(Customer).where(
                Customer.workspace_id == ctx.workspace_id,
                Customer.client_id == request.client_id,
                Customer.is_deleted.is_(False),
            )
        )
        customer = result.scalar_one_or_none()
        if customer is None:
            raise NotFound("Customer not found.")

        customer.is_deleted = True
        customer.deleted_at = datetime.now(timezone.utc)
        customer.deleted_by_id = ctx.user_id

    return {}
```

---

### Step 7 — Create `find_or_create_customer.py` (CMD-4)

**File:** `backend/app/beyo_manager/services/commands/customers/find_or_create_customer.py`

```python
"""CMD-4: Find existing Customer by normalized email or phone, or create a new one."""

from sqlalchemy import or_, select

from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.services.commands.customers.requests import (
    _normalize_email,
    _normalize_phone,
    parse_find_or_create_customer_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def find_or_create_customer(ctx: ServiceContext) -> dict:
    """Return an existing active Customer matched by email/phone, or create a new one."""
    request = parse_find_or_create_customer_request(ctx.incoming_data)

    normalized_email = _normalize_email(request.primary_email)
    normalized_phone = _normalize_phone(request.primary_phone_number)

    if normalized_email is None and normalized_phone is None:
        raise ValidationError(
            "At least one of primary_email or primary_phone_number must be provided."
        )

    async with maybe_begin(ctx.session):
        # Build lookup conditions — only include non-null normalized values
        lookup_conditions = []
        if normalized_email is not None:
            lookup_conditions.append(
                Customer.primary_email_normalized == normalized_email
            )
        if normalized_phone is not None:
            lookup_conditions.append(
                Customer.primary_phone_number_normalized == normalized_phone
            )

        existing_result = await ctx.session.execute(
            select(Customer).where(
                Customer.workspace_id == ctx.workspace_id,
                Customer.is_deleted.is_(False),
                or_(*lookup_conditions),
            ).limit(1)
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            return {"client_id": existing.client_id, "was_created": False}

        customer = Customer(
            workspace_id=ctx.workspace_id,
            display_name=request.display_name,
            customer_type=request.customer_type,
            primary_email=request.primary_email,
            primary_phone_number=request.primary_phone_number,
            primary_email_normalized=normalized_email,
            primary_phone_number_normalized=normalized_phone,
            address=request.address,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(customer)
        await ctx.session.flush()

    return {"client_id": customer.client_id, "was_created": True}
```

**Design notes:**
- Both lookup conditions are combined with `or_()` — a match on either email OR phone returns the existing customer.
- `.limit(1)` prevents scanning the full result set when multiple matches exist (e.g., phone matches a different customer than email).
- The lookup and the create are inside the same `maybe_begin` block — if the create flushes and then fails (e.g., parent transaction rollback), neither is committed.
- `_normalize_email` and `_normalize_phone` are called again here to derive the values passed to the DB lookup, matching the values stored in `primary_email_normalized` / `primary_phone_number_normalized`. Since the request validators already normalize the fields, calling them again here is idempotent and explicit.

---

### Step 8 — Create `services/queries/customers/customers.py` (QUERY-1 + QUERY-2)

**File:** `backend/app/beyo_manager/services/queries/customers/customers.py`

```python
"""QUERY-1: List Customers | QUERY-2: Get Customer by ID with linked items."""

from sqlalchemy import func, select

from beyo_manager.domain.customers.serializers import serialize_customer, serialize_customer_detail
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_issue import ItemIssue
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.models.tables.tasks.task_item import TaskItem
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.utils.string_filter import apply_string_filter

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50

_ALLOWED_FILTER_COLUMNS = {
    "display_name": Customer.display_name,
    "primary_email": Customer.primary_email,
    "primary_phone_number": Customer.primary_phone_number,
}


async def list_customers(ctx: ServiceContext) -> dict:
    """QUERY-1: List customers with optional q filter and offset pagination."""
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    q = ctx.query_params.get("q")
    string_filters = ctx.query_params.get("string_filters")

    stmt = select(Customer).where(
        Customer.workspace_id == ctx.workspace_id,
        Customer.is_deleted.is_(False),
    )

    stmt = apply_string_filter(stmt, q, string_filters, _ALLOWED_FILTER_COLUMNS)

    stmt = stmt.order_by(Customer.created_at.desc()).offset(offset).limit(limit + 1)
    result = await ctx.session.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "customers_pagination": {
            "items": [serialize_customer(c) for c in page],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }


async def get_customer(ctx: ServiceContext) -> dict:
    """QUERY-2: Get Customer by ID with linked items (via tasks → task_items)."""
    client_id = ctx.incoming_data.get("client_id")

    result = await ctx.session.execute(
        select(Customer).where(
            Customer.workspace_id == ctx.workspace_id,
            Customer.client_id == client_id,
            Customer.is_deleted.is_(False),
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise NotFound("Customer not found.")

    # Load distinct items linked to this customer through active tasks
    # Path: Customer → Task (customer_id) → TaskItem (task_id, removed_at IS NULL) → Item
    items_result = await ctx.session.execute(
        select(Item)
        .join(TaskItem, TaskItem.item_id == Item.client_id)
        .join(Task, Task.client_id == TaskItem.task_id)
        .where(
            Task.customer_id == customer.client_id,
            Task.workspace_id == ctx.workspace_id,
            Task.is_deleted.is_(False),
            TaskItem.removed_at.is_(None),
            Item.workspace_id == ctx.workspace_id,
            Item.is_deleted.is_(False),
        )
        .distinct()
        .order_by(Item.created_at.desc())
    )
    items = items_result.scalars().all()

    # Batch-load issue counts for linked items
    issue_counts: dict[str, int] = {}
    if items:
        item_ids = [item.client_id for item in items]
        count_result = await ctx.session.execute(
            select(ItemIssue.item_id, func.count(ItemIssue.client_id).label("cnt"))
            .where(
                ItemIssue.workspace_id == ctx.workspace_id,
                ItemIssue.item_id.in_(item_ids),
                ItemIssue.is_deleted.is_(False),
            )
            .group_by(ItemIssue.item_id)
        )
        issue_counts = {row.item_id: row.cnt for row in count_result}

    return {"customer": serialize_customer_detail(customer, items, issue_counts)}
```

**QUERY-2 JOIN design:**
- `Task.is_deleted.is_(False)` filters soft-deleted tasks — verify the column name exists on `Task` model before implementation.
- `TaskItem.removed_at.is_(None)` means the link is active (not removed).
- `.distinct()` prevents duplicate `Item` rows when an item appears in more than one task for the same customer.
- No pagination on linked items — the set is bounded by the customer's task history. If this becomes a concern, pagination can be added as a follow-up.

**QUERY-1 apply_string_filter usage:**
- `_ALLOWED_FILTER_COLUMNS` maps string keys to ORM column attributes.
- `string_filters` (optional query param) lets callers narrow to a subset of columns by name (e.g., `?q=john&string_filters=primary_email`).
- If `string_filters` is absent or None, all three columns are searched.

---

### Step 9 — Create `routers/api_v1/customers.py`

**File:** `backend/app/beyo_manager/routers/api_v1/customers.py`

**Route declaration order (static before wildcard — critical for FastAPI):**
1. `PUT ""` — create customer
2. `GET ""` — list customers
3. `POST "/find-or-create"` — CMD-4 — **MUST be declared before `/{client_id}` routes**
4. `GET "/{client_id}"` — get customer
5. `PATCH "/{client_id}"` — update customer
6. `DELETE "/{client_id}"` — delete customer

```python
"""Router: /api/v1/customers"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.customers.enums import CustomerTypeEnum, CustomerStatusEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, WORKER
from beyo_manager.services.commands.customers.create_customer import create_customer
from beyo_manager.services.commands.customers.delete_customer import delete_customer
from beyo_manager.services.commands.customers.find_or_create_customer import find_or_create_customer
from beyo_manager.services.commands.customers.update_customer import update_customer
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.queries.customers.customers import get_customer, list_customers
from beyo_manager.services.run_service import run_service

router = APIRouter()


# ── Request body models ────────────────────────────────────────────────────────

class _CreateCustomerBody(BaseModel):
    display_name: str
    customer_type: CustomerTypeEnum = CustomerTypeEnum.UNKNOWN
    primary_email: str | None = None
    primary_phone_number: str | None = None
    address: dict | None = None


class _UpdateCustomerBody(BaseModel):
    display_name: str | None = None
    customer_type: CustomerTypeEnum | None = None
    status: CustomerStatusEnum | None = None
    primary_email: str | None = None
    primary_phone_number: str | None = None
    address: dict | None = None


class _FindOrCreateCustomerBody(BaseModel):
    display_name: str
    primary_email: str | None = None
    primary_phone_number: str | None = None
    customer_type: CustomerTypeEnum = CustomerTypeEnum.UNKNOWN
    address: dict | None = None


# ── Collection-level routes (declared before wildcard /{client_id}) ────────────

@router.put("")
async def route_create_customer(
    body: _CreateCustomerBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(create_customer, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.get("")
async def route_list_customers(
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None, max_length=200),
    string_filters: str | None = Query(None, max_length=200),
):
    ctx = ServiceContext(
        incoming_data={},
        query_params={"limit": limit, "offset": offset, "q": q, "string_filters": string_filters},
        identity=claims,
        session=session,
    )
    outcome = await run_service(list_customers, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.post("/find-or-create")
async def route_find_or_create_customer(
    body: _FindOrCreateCustomerBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data=body.model_dump(),
        identity=claims,
        session=session,
    )
    outcome = await run_service(find_or_create_customer, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


# ── Wildcard /{client_id} routes ───────────────────────────────────────────────

@router.get("/{client_id}")
async def route_get_customer(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(get_customer, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.patch("/{client_id}")
async def route_update_customer(
    client_id: str,
    body: _UpdateCustomerBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id, **body.model_dump(exclude_unset=True)},
        identity=claims,
        session=session,
    )
    outcome = await run_service(update_customer, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)


@router.delete("/{client_id}")
async def route_delete_customer(
    client_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    ctx = ServiceContext(
        incoming_data={"client_id": client_id},
        identity=claims,
        session=session,
    )
    outcome = await run_service(delete_customer, ctx)
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)
```

**Critical notes:**
- `POST "/find-or-create"` is declared BEFORE `GET "/{client_id}"`. If reversed, FastAPI will attempt to match the string `"find-or-create"` as a `client_id` path parameter, routing incorrectly.
- `PATCH` uses `body.model_dump(exclude_unset=True)` — this is the required form. Not `model_dump()` and not `model_dump(exclude_none=True)`.

---

### Step 10 — Register customers router in `routers/api_v1/__init__.py`

**File:** `backend/app/beyo_manager/routers/api_v1/__init__.py`

Add import alongside existing router imports:
```python
from beyo_manager.routers.api_v1 import customers
```

Add registration inside `register_v1_routers`, before the `# Add domain routers here` comment:
```python
    app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
```

---

## Risks and mitigations

- **Risk:** `Task.is_deleted` column may not exist on the `Task` model (model uses a different deletion flag).
  **Mitigation:** Read `task.py` before implementing QUERY-2. If `is_deleted` is absent, filter on `Task.closed_at.is_(None)` or remove the task deletion filter and note the gap.

- **Risk:** `POST "/find-or-create"` route captured by `/{client_id}` wildcard if declaration order is wrong.
  **Mitigation:** The plan specifies declaration order explicitly. Verify by running the app and hitting `POST /api/v1/customers/find-or-create` — it must NOT return a 404 or a "Customer not found" error from `get_customer`.

- **Risk:** Duplicate customer creation under concurrent `find_or_create_customer` calls (race condition between read and write).
  **Mitigation:** This plan does not add a DB-level unique constraint. If concurrent calls occur, two customers may be created. This is acceptable for the current scope. A future migration can add a unique partial index on `(workspace_id, primary_email_normalized)` and `(workspace_id, primary_phone_number_normalized)` as a follow-up.

- **Risk:** `serialize_item_list` signature changes in a future refactor break QUERY-2.
  **Mitigation:** Confirm the exact signature by reading `domain/items/serializers.py` before implementation.

- **Risk:** `model_fields_set` in CMD-2 is empty if the router uses `body.model_dump()` instead of `body.model_dump(exclude_unset=True)`.
  **Mitigation:** PATCH handler must use `exclude_unset=True`. Verify after implementation.

---

## Validation plan

```bash
# 1. Import smoke test
cd backend/app && .venv/bin/python -c "from beyo_manager import create_app; create_app(); print('OK')"
# Expected: OK

# 2. No ctx.session.begin() in customer commands
grep -rn "ctx.session.begin" backend/app/beyo_manager/services/commands/customers/
# Expected: zero matches

# 3. All new command files exist
ls backend/app/beyo_manager/services/commands/customers/create_customer.py
ls backend/app/beyo_manager/services/commands/customers/update_customer.py
ls backend/app/beyo_manager/services/commands/customers/delete_customer.py
ls backend/app/beyo_manager/services/commands/customers/find_or_create_customer.py
ls backend/app/beyo_manager/services/queries/customers/customers.py
ls backend/app/beyo_manager/domain/customers/serializers.py
ls backend/app/beyo_manager/routers/api_v1/customers.py
# Expected: all exist

# 4. Router registered
grep "customers" backend/app/beyo_manager/routers/api_v1/__init__.py
# Expected: include_router line with /api/v1/customers prefix

# 5. find-or-create route is declared before /{client_id} in router file
grep -n "find-or-create\|client_id" backend/app/beyo_manager/routers/api_v1/customers.py
# Expected: find-or-create line number is LOWER than the first /{client_id} line number
```

---

## Review log

- `2026-05-17` Claude Sonnet 4.6: Plan created from intention notes + Customer/Task/TaskItem model read.

---

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: GitHub Copilot (implementation)
