# INTENTION — Connecteam Clock Actions (Phase 2) (2026-07-20)

> Provided by the product owner on 2026-07-20. Successor to
> `INTENTION_connecteam_time_activity_webhook_20260720.md` (phase 1, foundation).

## Objective

Introduce the user resolver flow end-to-end: given the `connecteam_user_id` carried by an
accepted Connecteam time-activity webhook, obtain the mapped user from the database and
apply the real internal clock action — marking clock-in or clock-out **depending on the
incoming webhook intention** — using the same mechanism as the existing
`toggle_worker_shift` endpoint (`backend/app/beyo_manager/services/commands/users/toggle_worker_shift.py`).

## Context established by phase 1 (already live)

- Webhook intake, verification (`X-Webhook-Secret` static shared secret), normalization,
  Redis dedup, and ExecutionTask queueing are implemented and validated with real
  Connecteam traffic.
- `TaskType.CONNECTEAM_PROCESS_TIME_ACTIVITY` is processed by the shared `tasks-worker`
  on `queue:tasks` (owner decision: no dedicated worker).
- `resolve_connecteam_worker` maps `connecteam_user_id` → `UserWorkProfile`
  (`user_id`, `workspace_id`); unmapped events complete as `connecteam_worker_not_mapped`.
- The three handlers (`clock_in`, `clock_out`, `auto_clock_out`) are logging no-ops with
  stable interfaces — phase 2 replaces their bodies.

## Owner constraints carried forward

- Adapt to what the architecture currently provides; never modify shared architecture
  (worker runtime, shift primitives, logging utilities) for this integration.
- Only the explicit `connecteam_user_id` mapping resolves workers — no fallback matching.
- `manual_break` activity remains ignored; only `clock_in`, `clock_out`, `auto_clock_out`
  with `activity_type == "shift"` act.

## Out of scope

- Connecteam REST API calls; syncing users; admin/edit events; frontend changes;
  new tables or migrations; changes to `toggle_worker_shift`, `_clock_worker_shift.py`,
  or any non-Connecteam code path.

## Lifecycle progress

- Linked implementation plan: `backend/docs/architecture/archives/implementation/PLAN_connecteam_clock_actions_20260720.md` — `archived`.
- Phase-2 automated implementation and validation are complete, including DB-backed parity
  with `toggle_worker_shift` and working-step closure semantics.
- Human-only ngrok validation remains pending: the owner must clock a mapped worker in and out
  in Connecteam to confirm the live delivery, logs, and UI state. This follow-up is documented
  in `backend/docs/architecture/under_construction/implementation/VALIDATION_connecteam_webhook_ngrok.md`.
