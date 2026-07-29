# Review prompt — Declared Worker States, Phase 3: declare/close commands + retirement

You are reviewing an implementation made by another agent (Codex) in the ManagerBeyo backend (`backend/`). Your job is adversarial verification: try to find where the implementation deviates from the plan or breaks an invariant. Do not fix anything — report.

## Inputs

- Master plan (decisions D2, D5, D7, D9, D10 govern this phase): `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
- Phase plan under review: `.../declared_worker_states/PLAN_declared_worker_states_phase3_commands_20260729.md`
- The implementation diff: `git log`/`git diff` for the phase's commits.

## Review protocol

1. Read the master decisions, then the phase plan in full.
2. Read the diff completely; map every acceptance criterion to concrete evidence. Missing evidence = finding.
3. Re-run the plan's Validation plan commands yourself, including the retirement `grep`.
4. Record findings in the phase plan's Review log and report them in your reply.

## Phase-specific checklist

- [ ] Declare validation order and codes match the plan: no open shift → `409`; foreign/deleted reason → `404`; BLOCKER reason → validation error; missing required description → validation error. Each has a test.
- [ ] On-behalf matrix (D10 rev 2) tested for BOTH declare and close: worker self OK; worker + foreign `user_id` → `403`; admin/manager + `user_id` → OK with `created_by_id`/`closed_by_id` = acting account; admin/manager without `user_id` → `403`; non-worker target → `404`. Resolution goes through `resolve_worker_shift_target` — a parallel reimplementation is a finding.
- [ ] Request/response shapes match `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` field-for-field (the frontend builds against it). Any deviation is a blocking finding unless the handoff was updated by the operator first.
- [ ] Reason validation enforces ALL of: same workspace, `is_deleted IS FALSE`, `pause_type = PERSONAL` (D2). Probe: a BLOCKER reason from the same workspace must be rejected.
- [ ] Switch semantics: old declared row closed with `closed_by_id = actor` in the same transaction the new row opens; test proves no window with two open rows and no surfaced `IntegrityError`.
- [ ] Auto-pause reuses `_load_open_working_step_rows` + `_apply_step_transition` with `new_state=PAUSED` and `pause_reason_id = declared reason` (D5) — no parallel transition implementation. Paused records' state AND reason asserted in tests.
- [ ] Closing a declaration does NOT resume paused steps (explicit clarification in the plan); test proves steps stay `PAUSED`.
- [ ] Both commands end with a synchronous same-session `reconcile_worker_shift_state` call; the live derived record is asserted **within the same test transaction** (not via the analytics worker).
- [ ] Lock order preserved: shift row (`load_open_worker_shift_for_update`) acquired BEFORE the declared row lock.
- [ ] No auto-clock-in path reachable from declare (D9).
- [ ] Retirement is total: `grep -rn "pause_worker_shift\|resume_worker_shift" app/beyo_manager/` → zero hits; `/pause` + `/resume` absent from the router; reconcile carve-out (`manually_recorded` current-row check vs `IDLE` target) removed; old tests converted to declared-precedence coverage, not just deleted.
- [ ] NO data migration touching legacy `manually_recorded` rows (D7) — any Alembic data migration here is a blocking finding.
- [ ] The full-loop test (declare → work step auto-closes declaration → complete → declare again → clock out → rebuilt timeline shows both declared segments, correct reasons, `manually_recorded=true`) exists and passes.
- [ ] `models/tables/users/README.md` state-machine section rewritten (includes `IDLE`, declared states, `manually_recorded` redefinition).
- [ ] Routes are thin (parse → ctx → `run_service` → `build_ok`/`build_err`); worker-only gating via `require_roles([WORKER])`.
- [ ] Deploy note about deploy-time manual-pause workers present in the implemented summary.
- [ ] Full suite green; ruff clean.

## Adversarial probes (attempt at least these)

- Declare twice concurrently (two sessions): partial unique index must hold; one request wins, the other errors or switches cleanly.
- Declare while a BLOCKER step-pause is open and no working steps: shift shows declared reason (D4), steps untouched.
- Declare with a working step, then close the declaration WITHOUT touching the step: what state results? (Step is paused, so `IN_PAUSE` step-sourced — verify reason flips from declared to step reason.)

## Verdict

End your report with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated clause, severity).
