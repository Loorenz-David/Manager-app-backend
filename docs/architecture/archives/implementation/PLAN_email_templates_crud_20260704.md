# PLAN_email_templates_crud_20260704

## Metadata

- Plan ID: `PLAN_email_templates_crud_20260704`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-04T00:00:00Z`
- Last updated at (UTC): `2026-07-04T20:05:46Z`
- Related issue/ticket: —
- Intention plan: `backend/docs/architecture/under_construction/intention/email_implementation.txt`

## Goal and intent

- Goal: Add an `EmailTemplate` model, full CRUD commands, list/get queries, and a dedicated router at `/api/v1/email-templates`. Templates are workspace-scoped, categorized by topic and type (txt/html), and allow users to store reusable email subjects and content bodies. The list endpoint supports filtering by one or more topics passed as a comma-separated query param.
- Business/user intent: Users need to compose recurring emails (coordination updates, customer notifications, etc.) without rewriting subject/body each time. Templates are stored per workspace, tagged with a topic that aligns with the email thread entity context, and typed by rendering format (plain text or HTML).
- Non-goals: Template rendering/variable interpolation, template versioning, associating a template to a specific thread or connection, soft-delete (hard delete is sufficient here), realtime socket events for template changes.

## Scope

- In scope:
  - `domain/emails/enums.py` — add `EmailTemplateTopicEnum` and `EmailTemplateTypeEnum`
  - `models/tables/emails/email_template.py` — new model (`CLIENT_ID_PREFIX = "etpl"`)
  - `models/__init__.py` — register the new model for Alembic detection
  - `models/tables/client_id_prefix_map.md` — add `EmailTemplate | etpl` row
  - `domain/emails/serializers.py` — add `serialize_email_template`
  - `services/commands/emails/requests/create_email_template_request.py` — new request parser
  - `services/commands/emails/requests/update_email_template_request.py` — new request parser
  - `services/commands/emails/create_email_template.py` — new command
  - `services/commands/emails/update_email_template.py` — new command
  - `services/commands/emails/delete_email_template.py` — new command
  - `services/queries/emails/list_email_templates.py` — new query (offset pagination, topic filter)
  - `services/queries/emails/get_email_template.py` — new query
  - `routers/api_v1/email_templates.py` — new router (5 routes)
  - `routers/api_v1/__init__.py` — register the new router
  - Alembic migration — `alembic revision --autogenerate -m "add_email_templates_table"` then `alembic upgrade head`
  - Frontend handoff doc — `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_email_templates_20260704.md`

- Out of scope:
  - Template rendering or variable substitution at send time
  - Template versioning or audit history
  - Realtime events when a template is created/updated/deleted
  - Linking templates to specific connections, threads, or tasks

- Assumptions:
  - All email templates are workspace-scoped via a `workspace_id` FK (consistent with `EmailConnection`, `EmailThread`, `EmailMessage`). The user's intention listed columns do not include `workspace_id` explicitly, but the architecture and context require it.
  - Topics are an enumerated set; the values mirror `EmailThreadEntityTypeEnum` (TASK, TASK_CUSTOMER_COORDINATION, CASE, CUSTOMER) so that templates can be pre-selected in context. A new `EmailTemplateTopicEnum` is created rather than reusing the entity type enum to allow independent evolution.
  - No soft-delete; DELETE is a permanent hard-delete (no `is_deleted` column needed).
  - Roles for all template endpoints: `ADMIN`, `MANAGER` for mutating routes; `ADMIN`, `MANAGER`, `SELLER` for read routes.

## Clarifications required

_None — implementation can proceed._

## Acceptance criteria

1. `PUT /api/v1/email-templates` creates an `EmailTemplate` in the caller's workspace; returns `{"template": serialize_email_template(...)}`.
2. `GET /api/v1/email-templates` returns `{"templates_pagination": {"items": [...], "has_more": bool, "limit": int, "offset": int}}`; supports `limit`, `offset`, and `topic` (comma-separated string e.g. `"task,case"`) query params.
3. `GET /api/v1/email-templates/{client_id}` returns `{"template": serialize_email_template(...)}` or 404 if not found or belongs to a different workspace.
4. `PATCH /api/v1/email-templates/{client_id}` updates `name`, `subject`, `content`, `topic`, and/or `template_type`; raises 404 if not found; returns updated template.
5. `DELETE /api/v1/email-templates/{client_id}` permanently deletes the record; returns `{}`.
6. Serializer output includes: `client_id`, `workspace_id`, `name`, `subject`, `content`, `topic`, `template_type`, `created_at`, `created_by_id`, `updated_at`, `updated_by_id`.
7. All commands follow `06_commands.md`: transaction via `async with ctx.session.begin()`, request parsed via Pydantic parser, no cross-command calls.
8. List query follows `07_queries_local.md`: offset pagination, `_MAX_LIMIT = 200`, `_DEFAULT_LIMIT = 50`, top-level key `templates_pagination`.
9. Migration autogenerates cleanly from the new model and `alembic upgrade head` succeeds.
10. Frontend handoff doc created at `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_email_templates_20260704.md`.

## Contracts and skills

### Contracts loaded

- `backend/architecture/01_architecture.md`: system overview, layering rules
- `backend/architecture/04_context.md`: `ServiceContext` shape (`workspace_id`, `user_id`, `identity`, `incoming_data`, `query_params`, `session`)
- `backend/architecture/05_errors.md`: `NotFound`, `ValidationError`, `ConflictError` error classes and raise patterns
- `backend/architecture/06_commands.md`: command skeleton, `async with ctx.session.begin()`, `session.add`, `session.flush`, request parser contract, no cross-command calls
- `backend/architecture/06_commands_local.md`: `maybe_begin` utility noted; not used here — each template command owns its transaction directly
- `backend/architecture/07_queries.md`: query function signature, `select()` pattern, `scalar_one_or_none()`, serialization at call site
- `backend/architecture/07_queries_local.md`: offset pagination overrides cursor; `_MAX_LIMIT = 200`, `_DEFAULT_LIMIT = 50`; pagination key shape `{"items": [...], "has_more": bool, "limit": int, "offset": int}`
- `backend/architecture/09_routers.md`: router skeleton, `build_ok`/`build_err`, `require_roles`, path param injection, static routes before wildcard
- `backend/architecture/21_naming_conventions.md`: file naming, variable naming, router path conventions
- `backend/architecture/03_models.md`: SQLAlchemy ORM model conventions, `IdentityMixin`, `Base`, `mapped_column`, FK patterns
- `backend/architecture/08_domain.md`: domain enum and serializer conventions
- `backend/architecture/30_migrations.md`: Alembic autogenerate workflow, `alembic revision --autogenerate`, `alembic upgrade head`
- `backend/architecture/40_identity.md`: `IdentityMixin` and `client_id` generation
- `backend/architecture/41_user.md`: user FK reference pattern (`users.client_id`)

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: adds `maybe_begin` and session call safety rules — not used in this plan (commands are self-contained)
- `backend/architecture/07_queries_local.md`: offset pagination replaces cursor pagination for list queries

### File read intent — pattern vs. relational

Permitted relational reads required before coding:
- `models/tables/emails/email_thread.py` — FK reference pattern, `workspace_id`, `created_at`/`updated_at` column shape ✓ (read above)
- `models/tables/emails/email_connection.py` — confirm `workspace_id` FK pattern ✓ (read above)
- `models/base/identity.py` — `IdentityMixin` signature, `CLIENT_ID_PREFIX` usage ✓ (read above)
- `domain/emails/enums.py` — existing enum values to align with ✓ (read above)
- `domain/emails/serializers.py` — existing serializer shape to follow ✓ (read above)
- `routers/api_v1/email_threads.py` — existing email router pattern ✓ (read above)
- `routers/api_v1/__init__.py` — where to insert new router registration ✓ (read above)
- `models/__init__.py` — where to insert new model import ✓ (read above)
- `models/tables/client_id_prefix_map.md` — confirm `etpl` is not taken ✓ (read above)

Prohibited reads (contracts already cover these):
- Any other command file to understand `session.begin()` / flush shape → `06_commands.md`
- Any other router to understand handler wiring → `09_routers.md`
- Any other serializer to understand output shape → `08_domain.md` + `46_serialization.md`

### Skill selection

- Primary skill: CRUD goal bundle from `backend_contract_goal_mapping_guide.md`
- Excluded alternatives:
  - `11_infra_events.md` — no realtime broadcast needed for template CRUD
  - `13_sockets.md` — no socket events
  - `15_testing.md` — no test scaffolding in scope
  - Worker-driven, replayable async, CI-validated bundles — not triggered

## Implementation plan

### Step 1 — Add enums to `domain/emails/enums.py`

**File:** `app/beyo_manager/domain/emails/enums.py` (append to existing file)

```python
class EmailTemplateTopicEnum(str, enum.Enum):
    TASK = "task"
    TASK_CUSTOMER_COORDINATION = "task_customer_coordination"
    CASE = "case"
    CUSTOMER = "customer"


class EmailTemplateTypeEnum(str, enum.Enum):
    TXT = "txt"
    HTML = "html"
```

`EmailTemplateTopicEnum` mirrors `EmailThreadEntityTypeEnum` values so templates can be matched to thread context. Defined separately to allow independent evolution.

---

### Step 2 — Create model `models/tables/emails/email_template.py`

**File:** `app/beyo_manager/models/tables/emails/email_template.py` (new file)

```python
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from beyo_manager.models.base.base import Base
from beyo_manager.models.base.identity import IdentityMixin


class EmailTemplate(IdentityMixin, Base):
    CLIENT_ID_PREFIX = "etpl"
    __tablename__ = "email_templates"

    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.client_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    template_type: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.client_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_by_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.client_id"), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc), nullable=True
    )
```

Notes:
- `topic` and `template_type` are stored as `String` (consistent with how `EmailThread.topic`, `EmailThread.entity_type` are stored — no native Postgres enum type). Enum validation is enforced at the command layer via Pydantic.
- `index=True` on `topic` to support the filtered list query efficiently.
- No `is_deleted` — hard delete is sufficient for templates.

---

### Step 3 — Register model in `models/__init__.py`

**File:** `app/beyo_manager/models/__init__.py`

Append inside the `# --- Emails ---` section (after `email_thread_user_state`):

```python
from beyo_manager.models.tables.emails import email_template  # noqa: F401
```

---

### Step 4 — Update `client_id_prefix_map.md`

**File:** `app/beyo_manager/models/tables/client_id_prefix_map.md`

Add row (alphabetically by class name, near `EmailConnection`):

```
| EmailTemplate | etpl | etpl_xxxxxxx |
```

---

### Step 5 — Add `serialize_email_template` to `domain/emails/serializers.py`

**File:** `app/beyo_manager/domain/emails/serializers.py` (append)

Add to `TYPE_CHECKING` block:
```python
from beyo_manager.models.tables.emails.email_template import EmailTemplate
```

Add serializer function:
```python
def serialize_email_template(template: "EmailTemplate") -> dict:
    return {
        "client_id": template.client_id,
        "workspace_id": template.workspace_id,
        "name": template.name,
        "subject": template.subject,
        "content": template.content,
        "topic": template.topic,
        "template_type": template.template_type,
        "created_by_id": template.created_by_id,
        "created_at": template.created_at.isoformat(),
        "updated_by_id": template.updated_by_id,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }
```

---

### Step 6 — Request parsers

#### Step 6a — `create_email_template_request.py`

**File:** `app/beyo_manager/services/commands/emails/requests/create_email_template_request.py` (new)

```python
from pydantic import BaseModel, field_validator, ValidationError as PydanticValidationError

from beyo_manager.domain.emails.enums import EmailTemplateTopicEnum, EmailTemplateTypeEnum
from beyo_manager.errors.validation import ValidationError


class CreateEmailTemplateRequest(BaseModel):
    name: str
    subject: str
    content: str
    topic: EmailTemplateTopicEnum
    template_type: EmailTemplateTypeEnum

    @field_validator("name", "subject", "content", mode="before")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


def parse_create_email_template_request(data: dict) -> CreateEmailTemplateRequest:
    try:
        return CreateEmailTemplateRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}")
```

#### Step 6b — `update_email_template_request.py`

**File:** `app/beyo_manager/services/commands/emails/requests/update_email_template_request.py` (new)

```python
from pydantic import BaseModel, field_validator, ValidationError as PydanticValidationError

from beyo_manager.domain.emails.enums import EmailTemplateTopicEnum, EmailTemplateTypeEnum
from beyo_manager.errors.validation import ValidationError


class UpdateEmailTemplateRequest(BaseModel):
    client_id: str
    name: str | None = None
    subject: str | None = None
    content: str | None = None
    topic: EmailTemplateTopicEnum | None = None
    template_type: EmailTemplateTypeEnum | None = None

    @field_validator("name", "subject", "content", mode="before")
    @classmethod
    def strip_and_require_if_provided(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("must not be blank when provided")
        return v


def parse_update_email_template_request(data: dict) -> UpdateEmailTemplateRequest:
    try:
        return UpdateEmailTemplateRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}")
```

---

### Step 7 — Command: `create_email_template.py`

**File:** `app/beyo_manager/services/commands/emails/create_email_template.py` (new)

```python
from beyo_manager.domain.emails.serializers import serialize_email_template
from beyo_manager.models.tables.emails.email_template import EmailTemplate
from beyo_manager.services.commands.emails.requests.create_email_template_request import (
    parse_create_email_template_request,
)
from beyo_manager.services.context import ServiceContext


async def create_email_template(ctx: ServiceContext) -> dict:
    request = parse_create_email_template_request(ctx.incoming_data)

    async with ctx.session.begin():
        template = EmailTemplate(
            workspace_id=ctx.workspace_id,
            name=request.name,
            subject=request.subject,
            content=request.content,
            topic=request.topic.value,
            template_type=request.template_type.value,
            created_by_id=ctx.user_id,
        )
        ctx.session.add(template)

    return {"template": serialize_email_template(template)}
```

---

### Step 8 — Command: `update_email_template.py`

**File:** `app/beyo_manager/services/commands/emails/update_email_template.py` (new)

```python
from sqlalchemy import select

from beyo_manager.domain.emails.serializers import serialize_email_template
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_template import EmailTemplate
from beyo_manager.services.commands.emails.requests.update_email_template_request import (
    parse_update_email_template_request,
)
from beyo_manager.services.context import ServiceContext


async def update_email_template(ctx: ServiceContext) -> dict:
    request = parse_update_email_template_request(ctx.incoming_data)

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(EmailTemplate).where(
                EmailTemplate.workspace_id == ctx.workspace_id,
                EmailTemplate.client_id == request.client_id,
            )
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise NotFound("Email template not found.")

        if request.name is not None:
            template.name = request.name
        if request.subject is not None:
            template.subject = request.subject
        if request.content is not None:
            template.content = request.content
        if request.topic is not None:
            template.topic = request.topic.value
        if request.template_type is not None:
            template.template_type = request.template_type.value
        template.updated_by_id = ctx.user_id

    return {"template": serialize_email_template(template)}
```

---

### Step 9 — Command: `delete_email_template.py`

**File:** `app/beyo_manager/services/commands/emails/delete_email_template.py` (new)

```python
from sqlalchemy import select

from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_template import EmailTemplate
from beyo_manager.services.context import ServiceContext


async def delete_email_template(ctx: ServiceContext) -> dict:
    client_id: str = ctx.incoming_data["client_id"]

    async with ctx.session.begin():
        result = await ctx.session.execute(
            select(EmailTemplate).where(
                EmailTemplate.workspace_id == ctx.workspace_id,
                EmailTemplate.client_id == client_id,
            )
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise NotFound("Email template not found.")

        await ctx.session.delete(template)

    return {}
```

---

### Step 10 — Query: `list_email_templates.py`

**File:** `app/beyo_manager/services/queries/emails/list_email_templates.py` (new)

```python
from sqlalchemy import select, func

from beyo_manager.domain.emails.serializers import serialize_email_template
from beyo_manager.models.tables.emails.email_template import EmailTemplate
from beyo_manager.services.context import ServiceContext

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


async def list_email_templates(ctx: ServiceContext) -> dict:
    limit = min(int(ctx.query_params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(ctx.query_params.get("offset", 0))
    topic_raw: str | None = ctx.query_params.get("topic")

    stmt = select(EmailTemplate).where(
        EmailTemplate.workspace_id == ctx.workspace_id
    )

    if topic_raw:
        topics = [t.strip() for t in topic_raw.split(",") if t.strip()]
        if topics:
            stmt = stmt.where(EmailTemplate.topic.in_(topics))

    stmt = stmt.order_by(EmailTemplate.created_at.desc())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await ctx.session.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.limit(limit).offset(offset)
    result = await ctx.session.execute(stmt)
    templates = result.scalars().all()

    return {
        "templates_pagination": {
            "items": [serialize_email_template(t) for t in templates],
            "has_more": (offset + limit) < total,
            "limit": limit,
            "offset": offset,
        }
    }
```

---

### Step 11 — Query: `get_email_template.py`

**File:** `app/beyo_manager/services/queries/emails/get_email_template.py` (new)

```python
from sqlalchemy import select

from beyo_manager.domain.emails.serializers import serialize_email_template
from beyo_manager.errors.not_found import NotFound
from beyo_manager.models.tables.emails.email_template import EmailTemplate
from beyo_manager.services.context import ServiceContext


async def get_email_template(ctx: ServiceContext) -> dict:
    client_id: str = ctx.incoming_data["client_id"]

    result = await ctx.session.execute(
        select(EmailTemplate).where(
            EmailTemplate.workspace_id == ctx.workspace_id,
            EmailTemplate.client_id == client_id,
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise NotFound("Email template not found.")

    return {"template": serialize_email_template(template)}
```

---

### Step 12 — Router: `routers/api_v1/email_templates.py`

**File:** `app/beyo_manager/routers/api_v1/email_templates.py` (new)

```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.emails.enums import EmailTemplateTopicEnum, EmailTemplateTypeEnum
from beyo_manager.models.database import get_db
from beyo_manager.routers.http.response import build_err, build_ok
from beyo_manager.routers.utils.jwt_dep import require_roles
from beyo_manager.routers.utils.roles import ADMIN, MANAGER, SELLER
from beyo_manager.services.commands.emails.create_email_template import create_email_template
from beyo_manager.services.commands.emails.update_email_template import update_email_template
from beyo_manager.services.commands.emails.delete_email_template import delete_email_template
from beyo_manager.services.queries.emails.list_email_templates import list_email_templates
from beyo_manager.services.queries.emails.get_email_template import get_email_template
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.run_service import run_service

router = APIRouter()


class _CreateBody(BaseModel):
    name: str
    subject: str
    content: str
    topic: EmailTemplateTopicEnum
    template_type: EmailTemplateTypeEnum


class _UpdateBody(BaseModel):
    name: str | None = None
    subject: str | None = None
    content: str | None = None
    topic: EmailTemplateTopicEnum | None = None
    template_type: EmailTemplateTypeEnum | None = None


async def _run(command, incoming_data: dict, claims: dict, session: AsyncSession, query_params: dict | None = None):
    outcome = await run_service(
        command,
        ServiceContext(
            identity=claims,
            incoming_data=incoming_data,
            query_params=query_params or {},
            session=session,
        ),
    )
    return build_ok(outcome.data) if outcome.success else build_err(outcome.error)


@router.get("")
async def list_email_templates_route(
    topic: str | None = Query(None, description="Comma-separated topic values, e.g. 'task,case'"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        list_email_templates,
        {},
        claims,
        session,
        query_params={"topic": topic, "limit": limit, "offset": offset},
    )


@router.put("")
async def create_email_template_route(
    body: _CreateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(create_email_template, body.model_dump(), claims, session)


@router.get("/{template_id}")
async def get_email_template_route(
    template_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(get_email_template, {"client_id": template_id}, claims, session)


@router.patch("/{template_id}")
async def update_email_template_route(
    template_id: str,
    body: _UpdateBody,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(
        update_email_template,
        {"client_id": template_id, **body.model_dump(exclude_none=True)},
        claims,
        session,
    )


@router.delete("/{template_id}")
async def delete_email_template_route(
    template_id: str,
    claims: dict = Depends(require_roles([ADMIN, MANAGER])),
    session: AsyncSession = Depends(get_db),
):
    return await _run(delete_email_template, {"client_id": template_id}, claims, session)
```

Route declaration order (all static before wildcard ✓):
```
GET    ""               → list_email_templates    ADMIN, MANAGER, SELLER
PUT    ""               → create_email_template   ADMIN, MANAGER
GET    "/{template_id}" → get_email_template      ADMIN, MANAGER, SELLER
PATCH  "/{template_id}" → update_email_template   ADMIN, MANAGER
DELETE "/{template_id}" → delete_email_template   ADMIN, MANAGER
```

---

### Step 13 — Register router in `routers/api_v1/__init__.py`

**File:** `app/beyo_manager/routers/api_v1/__init__.py`

Add import (alongside other email imports):
```python
from beyo_manager.routers.api_v1 import (
    ...
    email_templates,
    ...
)
```

Add registration inside `register_v1_routers` (after email_threads registration):
```python
app.include_router(
    email_templates.router,
    prefix="/api/v1/email-templates",
    tags=["email-templates"],
)
```

---

### Step 14 — Alembic migration

```bash
cd app
alembic revision --autogenerate -m "add_email_templates_table"
alembic upgrade head
```

Expected: migration file creates table `email_templates` with columns `client_id` (PK), `workspace_id` (FK + index), `name`, `subject`, `content`, `topic` (indexed), `template_type`, `created_by_id` (FK), `created_at`, `updated_by_id` (FK, nullable), `updated_at` (nullable).

Verify after upgrade: `alembic current` shows the new head revision.

---

### Step 15 — Frontend handoff doc

**File:** `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_email_templates_20260704.md`

Create following the `TEMPLATE_HANDOFF_TO_FRONTEND.md` format. Include:
- All 5 endpoint signatures with HTTP method, path, roles, request body, and response shape
- Enum value tables for `topic` and `template_type`
- `topic` query param behavior: comma-separated string, optional, no topic filter returns all
- Serializer field table
- Error cases: 404 on unknown `client_id`, 422 on invalid enum value or blank required field

## Risks and mitigations

- Risk: `topic` is stored as `String` and validated only at the command layer; invalid values could theoretically be inserted by direct DB access.
  Mitigation: Acceptable — consistent with the rest of the codebase's approach (`EmailThread.topic`, `EmailThread.entity_type`). Add a DB-level `CHECK` constraint to the migration if stricter enforcement is needed later.

- Risk: `alembic revision --autogenerate` requires `email_template` to be registered in `models/__init__.py` before the command runs.
  Mitigation: Step 3 (register model) must be completed before Step 14 (migration). Plan steps are ordered correctly.

- Risk: The `updated_at` column uses `onupdate` lambda; SQLAlchemy only fires `onupdate` when the ORM detects a dirty column. If `update_email_template` sets `updated_by_id` only, `updated_at` will still fire because `updated_by_id` is a tracked mapped column on the same instance.
  Mitigation: No special handling needed — any attribute change on the instance triggers `onupdate` for `updated_at`.

## Validation plan

- `python -c "from beyo_manager.routers.api_v1 import email_templates"` — import succeeds without error
- `python -c "from beyo_manager.models.tables.emails.email_template import EmailTemplate"` — import succeeds
- `alembic check` — no pending migrations after `upgrade head`
- `PUT /api/v1/email-templates` with `{"name": "Intro", "subject": "Hi {{name}}", "content": "Body text", "topic": "task", "template_type": "txt"}` → returns `{"template": {...}}` with `client_id` starting with `etpl_`
- `GET /api/v1/email-templates` → returns `{"templates_pagination": {"items": [...], "has_more": false, "limit": 50, "offset": 0}}`
- `GET /api/v1/email-templates?topic=task` → only templates with `topic == "task"`
- `GET /api/v1/email-templates?topic=task,case` → templates with `topic` in `["task", "case"]`
- `GET /api/v1/email-templates/{client_id}` → single template or 404
- `PATCH /api/v1/email-templates/{client_id}` with `{"name": "Updated Name"}` → name changed, `updated_at` set
- `DELETE /api/v1/email-templates/{client_id}` → `{}`, subsequent GET returns 404
- `PUT /api/v1/email-templates` with `{"topic": "invalid_topic"}` → 422 validation error
- `PUT /api/v1/email-templates` with `{"name": "  "}` → 422 validation error (blank after strip)

## Review log

_empty_

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved`
- Transition owner: `claude-sonnet-4-6`
