# Review prompt — Declared Worker States, Phase 6: kiosk worker flow

You are reviewing an implementation made by another agent (Codex) in the ManagerBeyo backend (`backend/`). Your job is adversarial verification. Do not fix anything — report.

## Inputs

- Master plan (decisions D12–D14): `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
- Phase plan under review: `.../declared_worker_states/PLAN_declared_worker_states_phase6_kiosk_flow_20260729.md`
- Frontend contract: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md`
- The implementation diff: `git log`/`git diff` for the phase's commits.

## Review protocol

1. Read the master decisions, the phase plan, then the diff completely.
2. Map every acceptance criterion to concrete evidence; re-run the validation plan yourself.
3. Record findings in the phase plan's Review log and report them in your reply.

## Phase-specific checklist

- [ ] `clock_in_code` migration: partial unique index `(workspace_id, clock_in_code) WHERE clock_in_code IS NOT NULL` present in the migration (not just the model); duplicate-in-workspace proven at DB level; cross-workspace duplicate allowed; downgrade clean.
- [ ] Code management goes through the ESTABLISHED work-profile write path (not a new parallel command); `updated_by_id` stamped; 4–16 trim validation; friendly `409` on duplicate.
- [ ] NO identify endpoint was created (D13 rev 3) — grep the router diff; a `/identify` route is a blocking finding.
- [ ] Roster exposure is floor-scope-conditional: floor session → items carry `clock_in_code` (+ `email`); EVERY other scope → fields **absent** (not `null`) and response byte-identical — existing list_users tests unmodified and green. Probe with a real manager-scope token, not just unit mocks.
- [ ] Both compact and full list modes carry the fields for floor sessions.
- [ ] Code fetch is ONE batched query for the page (inspect the code; N+1 per user is a blocking finding).
- [ ] Workspace scoping: codes returned belong to the session's workspace only (multi-workspace user test).
- [ ] `analytics: null` present on `/clock-out` AND the `/clock` toggle clock-out branch; all pre-existing response keys unchanged (additive-only proven by unmodified existing assertions).
- [ ] Full-loop kiosk test exists and passes (floor sign-in → roster with codes → GET /current → clock-in → declare → clock-out).
- [ ] Handoff conformance: walk Phase 6's endpoints (§3 roster fields, §5 `analytics: null` placement, code management) against the implementation; status rows for Phase 6 flipped.
- [ ] Connecteam surface untouched (D8) — no diffs under `services/tasks/connecteam/`, `services/infra/connecteam/`, `auto_clock_out_open_shifts.py`.
- [ ] Full suite green; ruff clean.
- [ ] Master plan phase table updated for Phase 6 — but master plan NOT archived (Phase 7 remains; premature archive is a process finding).

## Adversarial probes (attempt at least these)

- Call `GET /users` with a WORKER-role token (regular worker app): no code/email fields leak in any mode.
- Set worker A's code, clear it, re-list from a floor session → `clock_in_code: null` (stale value gone).
- Assign the same code in two different workspaces → both succeed; each floor session sees only its own workspace's codes.
- Duplicate code within one workspace via the management path → friendly `409`, not a raw `IntegrityError` 500.

## Verdict

End your report with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated clause, severity).
