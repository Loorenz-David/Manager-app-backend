# Review prompt — Declared Worker States, Phase 4: clock surface + current-state endpoint + handoff

You are reviewing an implementation made by another agent (Codex) in the ManagerBeyo backend (`backend/`). Your job is adversarial verification: try to find where the implementation deviates from the plan or breaks an invariant. Do not fix anything — report.

## Inputs

- Master plan (decisions D8, D10 govern this phase): `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
- Phase plan under review: `.../declared_worker_states/PLAN_declared_worker_states_phase4_clock_surface_20260729.md`
- The implementation diff: `git log`/`git diff` for the phase's commits.

## Review protocol

1. Read the master decisions, then the phase plan in full.
2. Read the diff completely; map every acceptance criterion to concrete evidence. Missing evidence = finding.
3. Re-run the plan's Validation plan commands yourself.
4. Record findings in the phase plan's Review log and report them in your reply.

## Phase-specific checklist

- [ ] `/clock-in` and `/clock-out` wire the EXISTING commands unmodified (diff must not touch `clock_in_worker_shift.py` / `clock_out_worker_shift.py` logic beyond, at most, import surface).
- [ ] **`clock_out_at` is not reachable from HTTP**: the route's request model must not include it; probe the endpoint with an extra `clock_out_at` field and confirm it is ignored/rejected, never forwarded.
- [ ] `/clock` toggle untouched and covered by a passing regression test.
- [ ] `GET /current`: read-only (no `with_for_update` anywhere in the query service); access matrix tested (worker self; worker + foreign `user_id` → `403`; manager must name a worker); all five state scenarios tested (clocked out / idle / working / step-paused / declared).
- [ ] Legacy free-text `reason` serializes as `pause_reason: null` + `reason_text` — test exists; no 500 path.
- [ ] `shift_started_at` sourced from the latest `STARTED_SHIFT` marker `<= now`, not from the open row's `entered_at`.
- [ ] Reasons listing: if a filter was added, it is additive (default behavior byte-identical — existing listing tests unmodified); if pre-existing, the plan's verify-first note is recorded in the Review log.
- [ ] Connecteam surface untouched: `git diff` shows NO changes under `services/tasks/connecteam/`, `services/infra/connecteam/`, or `services/tasks/users/auto_clock_out_open_shifts.py` (D8). Any change there is blocking.
- [ ] Implemented `GET /current` + clock routes match `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` field-for-field — diff the response shapes yourself against the handoff; any silent deviation is a blocking finding. Handoff status line updated (Phases 1–4 live).
- [ ] Full suite green; ruff clean.
- [ ] Master plan phase table updated for Phase 4 — but master plan NOT archived (Phases 5–6 remain; premature archive is a process finding).

## Adversarial probes (attempt at least these)

- Manager calls `GET /current` on a user who is not a worker in the workspace → `404` (mirrors `resolve_worker_shift_target` semantics).
- `GET /current` immediately after declare (same second): declared_state present and consistent with `state`.
- Double `POST /clock-in` → second returns `409` and writes nothing.

## Verdict

End your report with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated clause, severity).
