we will create the router and command for assigning a user to a working section, which involves creating a new `WorkingSectionMembership` row linking the user, working section, and workspace.

so as the unassign router and command for removing that link. 

both accept list of working section IDs to assign/unassign, and the user ID to modify.

the commands will be used by other services like at the user registration ( which is not yet implemented yet plan intention is define at /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/docs/architecture/under_construction/intention/user_registration.md )

this services should push the event to so that the socket can push the update to the frontend and the frontend can update the user profile page with the new working sections. it targets the user that is getting changed, so the event should be pushed to a channel specific to that user, not the whole workspace. ( socket events already have that room functionality, double check that is true )

---

# INTENTION_working_section_membership_20260515

## Metadata

- Intention ID: `INTENTION_working_section_membership_20260515`
- Status: `active`
- Owner: `claude-sonnet-4-6`
- Created at (UTC): `2026-05-15T12:00:00Z`
- Last updated at (UTC): `2026-05-15T12:00:00Z`

## Goal

Enable admins and managers to assign workers to working sections (and remove them) via batch HTTP endpoints, so the system tracks which workers are responsible for each section.

## Why this matters

Task routing, staffing visibility, and capacity planning all depend on knowing which workers belong to which working sections. Without this link, the system has sections defined but no way to know who can perform work in them. The `WorkingSectionMembership` table already exists in the schema — this intention delivers the API surface that makes it usable.

The commands are also designed to be reused by other services (e.g. user registration) so that assigning a new worker to sections on onboarding uses the same logic path as the HTTP endpoint.

## Success criteria

1. `POST /api/v1/users/{user_id}/working-sections` assigns a WORKER to one or more sections in a single atomic call and returns the list of assigned section IDs.
2. `DELETE /api/v1/users/{user_id}/working-sections` removes active assignments for the given section IDs (soft-remove via `removed_at`) and returns the list of unassigned section IDs.
3. `GET /api/v1/working-sections/{id}/members` returns all currently active members of a section with `membership_id`, `user_id`, `username`, and `assigned_at`.
4. After assign or unassign, a `UserEvent` is dispatched to the affected user's socket room (not the workspace room).
5. Assigning a user who is not a WORKER returns `422 ValidationError`.
6. Assigning a user who is not in the workspace returns `404 NotFound`.
7. Assigning the same user to a section they are already actively assigned to returns `409 Conflict`.
8. Unassigning a user from a section with no active membership returns `404 NotFound`.
9. Only ADMIN and MANAGER roles can call all three endpoints.
10. Commands can be called from other services (user registration) via `ServiceContext` without any route dependency.

## Scope boundary

- In scope:
  - `POST` and `DELETE` at `/api/v1/users/{user_id}/working-sections`
  - `GET` at `/api/v1/working-sections/{id}/members`
  - WORKER-only assignment validation via workspace membership and role chain
  - Soft-remove semantics (`removed_at` / `removed_by_id`) — no hard deletes
  - `UserEvent` dispatch to the affected user's room after each command

- Out of scope:
  - User perspective query (listing all sections a user is assigned to) — deferred to future plan
  - Historical membership queries (past assignments where `removed_at IS NOT NULL`)
  - Notifications or push fanout triggered by assignment changes
  - Bulk operations across multiple users in one call

- Non-goals:
  - Changing who can be assigned (always WORKER-only in this plan)
  - Assigning MANAGER or ADMIN to sections as workers

## Linked implementation plans

| Plan ID | Path | Status | Covers |
|---------|------|--------|--------|
| `PLAN_working_section_membership_20260515` | `backend/docs/architecture/archives/implementation/PLAN_working_section_membership_20260515.md` | `completed` | Commands, query, serializer, routers, registration |

## Progress notes

- `2026-05-15`: Intention written. Blocking decisions resolved: user-centric batch routes (`/users/{id}/working-sections`), WORKER-only assignment, `UserEvent` confirmed via `domain_event.py` inspection, `ServiceContext` standard signature for reuse. GET members stays section-centric.
- `2026-05-15`: Implementation completed and validated with live API flow (assign -> list members -> unassign -> list members). Summary and archive record created, implementation plan moved to archives.
