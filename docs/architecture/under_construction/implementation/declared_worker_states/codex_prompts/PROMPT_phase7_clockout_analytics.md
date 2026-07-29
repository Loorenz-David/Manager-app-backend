# Codex prompt — Declared Worker States, Phase 7: clock-out analytics envelope

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`. Process this work as a full plan lifecycle: implement → validate → review-log entry → implemented summary → archive.
2. Read the master plan first: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`. Decision D14 (rev 2) is the spine of this phase.
3. Your implementation plan is: `backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase7_clockout_analytics_20260729.md`. Read it fully before touching code.
4. Prerequisite check: the master plan's phase table must show **Phases 2, 4 and 6 archived**. If not, STOP and report.
5. Clarification-first: ambiguity the plan does not resolve → STOP and ask. Do not invent requirements.
6. Respect the plan's "File read intent" — the breakdown service must be read in full before extracting the seam.

## Hard constraints for this phase

- COMPOSE, don't rebuild: `analytics` is assembled from the existing machinery — the breakdown seam (timeline + segments + pause_reasons) and `compute_worker_insights` + existing serializers. Any new metric computation or duplicated timeline math is out of scope.
- The analytics composition runs AFTER the clock-out write transaction, in the route/service wiring — `clock_out_shift_for_user` itself must remain untouched (safeguard + Connecteam never compute analytics).
- Graceful degradation is a hard rule: any exception in the composition → `analytics: null` + structured error log; the clock-out response is still `200` with the shift closed. Prove it with the monkeypatched test.
- The manager breakdown endpoint must stay byte-identical (its existing tests unmodified) — the seam extraction is a parameter lift, not a rewrite.
- The equivalence contract test (analytics ≡ manager breakdown for the same user/day) is the flagship — write it first.
- Shapes must match `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §5 field-for-field. Conflicts → STOP and ask.
- Measure the composite's latency on a realistic seeded day and record it in the plan's Review log.

## Definition of done

- Every acceptance criterion verified with evidence.
- Full validation plan green; `ruff check` clean.
- Handoff §5 status flipped (analytics live).
- Plan's Review log updated (incl. latency measurement); plan archived (preserve subfolder); implemented summary written; master plan phase table updated — and since this is now the FINAL phase, set the master plan to `archived` and move the whole `declared_worker_states/` folder to `archives/implementation/`.
