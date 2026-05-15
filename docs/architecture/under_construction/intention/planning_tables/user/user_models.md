# User Models Plan

Status: LOCKED - Model Contract
Domain: user
Contracts: 01, 03, 21, 24, 40, 41
Created: 2026-05-12
Updated: 2026-05-12

---

## Objective

Formalize user-adjacent model structure so new worker-operational data is introduced through
independent tables instead of expanding the core users table.

## 1) Locked boundary decisions

The users table remains global identity only.

The users table intentionally contains only authentication identity, user preferences, and
low-frequency profile data. Operational runtime concerns are externalized into dedicated systems.
This separation is foundational and must not be eroded.

Keep on users:
- username
- email (globally unique)
- password hash
- phone_number
- languages — stored as JSONB array of language codes (see Section 7)
- language_preference
- profile_picture

Do not add to users:
- role assignment (lives on workspace_memberships.workspace_role_id)
- working section assignment (lives on working_section_memberships)
- salary (lives on user_work_profiles)
- shift runtime state (lives on user_shift_state_records)
- websocket presence state or runtime online tracking (belongs to future realtime presence systems)
- operational runtime counters
- task-system relationships (future task domain)

---

## 2) Formal table definitions

### 2.1 user_work_profiles

Purpose:
- Per-user, per-workspace work profile and compensation data.

Identity:
- client_id: String(64), PK, prefix uwp

Columns:
- user_id: String(64), FK users.client_id, not null
- workspace_id: String(64), FK workspaces.client_id, not null
- salary_per_hour_before_tax: Numeric(12,4), nullable
- salary_per_hour_after_tax: Numeric(12,4), nullable
- created_at: DateTime(timezone=True), not null — persisted in UTC
- updated_at: DateTime(timezone=True), nullable — persisted in UTC
- created_by_id: String(64), FK users.client_id, not null
- updated_by_id: String(64), FK users.client_id, nullable

Constraints:
- UNIQUE(user_id, workspace_id)
- CHECK(salary_per_hour_before_tax IS NULL OR salary_per_hour_before_tax >= 0)
- CHECK(salary_per_hour_after_tax IS NULL OR salary_per_hour_after_tax >= 0)

Indexes:
- INDEX(user_id)
- INDEX(workspace_id)
- INDEX(workspace_id, user_id)

Cascade behavior:
- No cascade-delete from users or workspaces.
- FK delete behavior: RESTRICT (or equivalent NO ACTION) on all FKs referencing users and workspaces.
  Attempting to delete a referenced user or workspace while profile rows exist must raise a DB error.
- FK update behavior: RESTRICT. client_id values are immutable after creation.
- Profile rows must remain durable for historical auditability.

Currency ownership:
- Currency is workspace-scoped, not profile-scoped.
- Compensation values on user_work_profiles implicitly inherit the workspace's operational currency.
- Cross-currency compensation within the same workspace is out of scope for this phase.
- Do not add currency columns, currency overrides, or user-level currency ownership to this table.

Lifecycle assumption:
- user_work_profiles represents the current operational compensation profile for a user within
  a workspace. There is exactly one active row per (user_id, workspace_id) at any time.
- Historical compensation changes are tracked through snapshot and event systems, not through
  multiple profile rows. The UNIQUE(user_id, workspace_id) constraint is intentional and permanent.
- If a user leaves and is rehired, the existing profile row is updated in place. The command layer
  must snapshot compensation values before overwriting. A future rehire event log is out of scope
  for this phase but must not be modeled by inserting a second profile row.

Notes:
- Numeric is mandatory for financial values. Float is forbidden.
- created_by_id is not nullable. All profile creation must be attributed to an actor.
- updated_by_id is nullable on creation; required on every subsequent update command.
- If only one salary field is populated initially, the other can remain nullable.
- When salary values change, the command layer must snapshot the previous values before overwriting.
  Future payroll and analytics systems must not retroactively derive historical compensation
  from the current mutable profile row.

---

### 2.2 user_shift_state_records

Purpose:
- Store the full history of worker shift state transitions per user per workspace.
- Provide O(1) active-state lookup through a partial unique index on the open row.
- Table name reflects append-oriented historical records, not a single mutable runtime state column.

Identity:
- client_id: String(64), PK, prefix uss

Columns:
- user_id: String(64), FK users.client_id, not null
- workspace_id: String(64), FK workspaces.client_id, not null
- state: Enum(UserShiftStateEnum), not null
- entered_at: DateTime(timezone=True), not null — persisted in UTC
- exited_at: DateTime(timezone=True), nullable — persisted in UTC
- changed_by_id: String(64), FK users.client_id, nullable
  — Nullable only for: bootstrap-generated rows, system-generated transitions,
    and migration-generated historical imports.
  — All normal operational transitions must attribute an actor. Null on an
    operational row is a command-layer violation.

State enum — UserShiftStateEnum:
- STARTED_SHIFT  — initial transition into an active shift lifecycle. Represents the moment a
                   worker opens a shift. Not synonymous with productive work.
- WORKING        — active productive work during an open shift. Sustained working state.
- IN_PAUSE       — shift is open but worker is not actively working.
- ENDED_SHIFT    — terminal state. Shift lifecycle is closed. No further transitions permitted.

Valid transitions (domain layer enforces; model layer does not):
- STARTED_SHIFT -> WORKING
- WORKING       -> IN_PAUSE
- IN_PAUSE      -> WORKING
- WORKING       -> ENDED_SHIFT

All other transitions are illegal (e.g. IN_PAUSE -> STARTED_SHIFT, ENDED_SHIFT -> any state).
Transition legality is enforced exclusively in the domain layer. See "State transition rules ownership" below.

Constraints:
- CHECK(exited_at IS NULL OR exited_at >= entered_at)

Indexes:
- INDEX(user_id)
- INDEX(workspace_id)
- INDEX(user_id, workspace_id, entered_at DESC)
- INDEX(user_id, workspace_id, exited_at)
- Partial unique index: UNIQUE(user_id, workspace_id) WHERE exited_at IS NULL

Active-state derivation:
- Current shift state is the row where exited_at IS NULL.
- Do not cache, denormalize, or duplicate current shift state into:
  - users table
  - any identity field
  - any operational summary column
- All active-state reads resolve through a direct query on user_shift_state_records.

Cascade behavior:
- No cascade-delete from users or workspaces.
- FK delete behavior: RESTRICT (or equivalent NO ACTION) on all FKs referencing users and workspaces.
  Attempting to delete a referenced user or workspace while shift records exist must raise a DB error.
- FK update behavior: RESTRICT. client_id values are immutable after creation.
- Transition history must remain durable for analytics and future task attribution.

Shift-transition authority:
- State transitions are exclusively performed through dedicated command-layer transition services.
- Direct ORM mutation of shift-state rows outside command flows is forbidden.
- This preserves lifecycle consistency, auditability, and future event-sourcing compatibility.

State transition rules ownership:
- The model layer defines the enum values only. It does not enforce transition legality.
- The domain layer owns:
  - allowed transitions (e.g. STARTED_SHIFT -> WORKING is valid; IN_PAUSE -> STARTED_SHIFT is not)
  - illegal state guards (e.g. cannot start a shift while one is already active)
  - transition invariants (e.g. exited_at must be set before a new row is inserted)
- No database CHECK constraints, triggers, or ORM validators are used to enforce transition rules.
- This boundary ensures the state machine can evolve without schema migrations.

---

## 3) Relationship contract

Cardinality:
- users (1) to (*) user_work_profiles
- workspaces (1) to (*) user_work_profiles
- users (1) to (*) user_shift_state_records
- workspaces (1) to (*) user_shift_state_records
- users (1) to (*) workspace_memberships

Cross-domain boundary:
- users does not carry direct working section assignment fields.
- Section assignment is queried through working_section_memberships.

ORM relationship direction rules:
- Keep relationship definitions local to owning domain modules.
- Avoid adding broad reverse relationships on users that force heavy eager loading.
- Use explicit query paths for operational reads (profiles, shifts, memberships).

---

## 4) Column ownership map

- salary_per_hour_before_tax -> user_work_profiles.salary_per_hour_before_tax
- salary_per_hour_after_tax -> user_work_profiles.salary_per_hour_after_tax
- currency -> workspace domain (not user_work_profiles)
- shift state -> user_shift_state_records.state
- shift entered/exited times -> user_shift_state_records.entered_at / exited_at
- languages -> users.languages (JSONB array of language codes)
- language_preference -> users.language_preference

---

## 5) Timestamp contract

All DateTime columns are persisted in UTC throughout the system.

Frontend and UI layers are responsible for:
- timezone localization (e.g. Europe/Stockholm)
- human-readable rendering

Analytics and duration calculations always operate on UTC values.
No timezone-offset columns are stored in the database.

---

## 6) Read and write behavior contract

Write paths:
- Update compensation through dedicated user work profile commands.
- Update shift state through dedicated shift-transition commands only.
- Never mutate the users row for compensation or shift transitions.

Read paths:
- Identity screen reads users only.
- Operational worker query flows read users + user_work_profiles + active user_shift_state_records row.
- Active shift row resolved by: SELECT ... WHERE user_id = ? AND workspace_id = ? AND exited_at IS NULL.

Consistency rules:
- All writes are transactional through command layer.
- No background worker dependency required for this model phase.

---

## 7) languages field contract

- Column type: JSONB on PostgreSQL. JSON is forbidden. ARRAY(String) is forbidden.
- Stored as a JSONB array of language code strings (e.g. ["sv", "en"]).
- Comma-separated storage is forbidden.
- Not normalized in this phase. No reference table.
- language_preference is a single String column (e.g. "sv").
- These are UI/preference metadata fields, not operational query entities.

---

## 8) Soft-delete and historical durability contract

Users are operationally deactivated, not hard-deleted.

Rationale:
- Shift history, analytics, and future task history all reference users by FK.
- Deleting a user row would orphan all historical operational records.

Rules:
- users carries is_active or equivalent deactivation mechanism (per contract 41).
- user_work_profiles and user_shift_state_records must never cascade-delete from users or workspaces.
- Historical records remain durable even when the referenced user is deactivated.

Operational snapshot rule:
- Any system that stores historical compensation, role, or assignment data must snapshot
  the value at the time of the event.
- Future analytics, payroll, and task attribution systems must not retroactively derive
  historical values from mutable current rows (e.g. current salary on user_work_profiles,
  current role on workspace_memberships, current section on working_section_memberships).

---

## 9) Anti-patterns explicitly rejected

On users:
- role FK directly on users
- working section assignment directly on users
- salary directly on users
- shift state column directly on users
- websocket presence state on users
- runtime online tracking on users
- operational runtime counters on users
- users must not become an operational runtime table

On user_work_profiles:
- currency column on user_work_profiles
- per-user currency override
- compensation-level currency ownership

General:
- comma-separated fields (operational or preference)
- Float for money/cost fields
- caching or denormalizing current shift state outside user_shift_state_records
- cascade-deleting operational history from users or workspaces

---

## 10) Delivery phases

Phase 1:
- Create user_work_profiles
- created_by_id not null from day one
- Wire admin-managed compensation creation and update commands

Phase 2:
- Create user_shift_state_records
- Enforce partial unique index for active-row rule
- Wire shift-transition command flow

Phase 3:
- Evaluate language normalization if operational query patterns emerge

Note: websocket presence and runtime online-state architecture are out of scope for this plan.
Those concerns belong to future realtime presence system planning.

---

## 11) Locked clarifications

Q1: Is user_work_profiles required in Phase 1?
Confirmed. Compensation and operational worker profile concerns are foundational worker architecture.
user_work_profiles is Phase 1, not deferrable.

Q2: Single-active-row rule for user_shift_state_records with partial unique index?
Confirmed. Enforce one active shift-state row per (user_id, workspace_id) using a PostgreSQL
partial unique index WHERE exited_at IS NULL.

Q3: Are created_by_id and updated_by_id required from day one on user_work_profiles?
Confirmed. created_by_id is not null from Phase 1. Compensation changes are operationally
sensitive and must be attributable from the start. updated_by_id is nullable on creation,
required on every subsequent update command.

Q4: Should languages stay as user-level preference fields with no normalization?
Confirmed. languages and language_preference remain user-level preference fields in this phase.
languages stored as JSONB array of language codes. JSON type and ARRAY(String) are forbidden. Comma-separated storage is forbidden.
