# INTENTION_working_section_crud_20260515

## Metadata

- Intention ID: `INTENTION_working_section_crud_20260515`
- Status: `active`
- Owner: `claude-sonnet-4-6`
- Created at (UTC): `2026-05-15T00:00:00Z`
- Last updated at (UTC): `2026-05-15T00:00:00Z`

## Goal

Establish the first operational CRUD layer for working sections so the workspace capability topology can be created, read, updated, and deleted through authenticated API endpoints.

## Why this matters

Working sections are the foundational registry that defines what areas of the workspace exist, what item categories they can handle, what issue types they support, and which sections must complete before others begin. Without working sections, no task assignment, staffing, or operational routing logic can be built. This is the first domain-specific command/query layer in the beyo_manager app.

## Success criteria

1. `PUT /api/v1/working-sections` creates a working section (with optional dependency, category, and issue type links) and returns the new section's `client_id`. Protected by `require_roles([ADMIN])`.
2. `PATCH /api/v1/working-sections/{id}` edits name, image, and/or replaces dependency/category/issue-type links. At least one field required. Protected by `require_roles([ADMIN])`.
3. `DELETE /api/v1/working-sections/{id}` soft-deletes a working section. Protected by `require_roles([ADMIN])`.
4. `GET /api/v1/working-sections/{id}` returns full section shape including dependency list (`client_id` + `name`), item category list (`client_id` + `name`), and supported issue type list (`client_id` + `name`). Protected by `require_roles([ADMIN, MEMBER])`.
5. `GET /api/v1/working-sections` returns all non-deleted sections for the workspace with the same shape as the get-by-id response. Protected by `require_roles([ADMIN, MEMBER])`.
6. All five endpoints follow the architecture contracts: commands own transactions, serializers own presentation, routers own nothing but wiring.
7. Edit command implements a cycle-detection guard for dependency edges.

## Scope boundary

- In scope:
  - Router (5 routes) + commands (create, edit, delete) + queries (get, list) + domain serializer
  - Dependency, item category, and issue type link management within each write command
  - Cycle detection guard for dependency edges in the edit command
  - Workspace event emission (`working_section:created`, `working_section:updated`, `working_section:deleted`) after each write

- Out of scope:
  - Membership management (adding/removing workers from sections) — separate future command
  - Analytics or runtime counters (`active_task_count`, `busy_workers`)
  - Soft-deleted section recovery endpoint
  - Section dependency graph visualization or traversal APIs
  - Websocket/realtime events for working section changes (event bus covers the async path)

- Non-goals:
  - Pagination beyond simple limit/offset for the list endpoint in this phase (registry is small)
  - Permission system changes or new role definitions

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_working_section_crud_20260515` | `backend/docs/architecture/under_construction/implementation/PLAN_working_section_crud_20260515.md` | `under_construction` | All 5 CRUD endpoints: router, commands, queries, serializer |

## Progress notes

- `2026-05-15`: Intention created. Blocking question on role permissions resolved: ADMIN for writes, ADMIN+MEMBER for reads. Implementation plan drafted and ready for Copilot.

## Open questions

- None blocking at this time.

## Lifecycle transition

- Current status: `active`
- Next status: `achieved`
- Transition trigger: All 7 success criteria are verifiable against the running API.
