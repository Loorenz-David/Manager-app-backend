# Review prompt — Declared Worker States, Phase 1: model + migration

You are reviewing an implementation made by another agent (Codex) in the ManagerBeyo backend (`backend/`). Your job is adversarial verification: try to find where the implementation deviates from the plan or breaks an invariant. Do not fix anything — report.

## Inputs

- Master plan (binding decisions D1–D10): `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`
- Phase plan under review: `.../declared_worker_states/PLAN_declared_worker_states_phase1_model_20260729.md`
- The implementation diff: inspect `git log`/`git diff` for the phase's commits (or the working tree if uncommitted).

## Review protocol

1. Read the master plan's decisions table, then the phase plan in full (goal, scope, assumptions, acceptance criteria).
2. Read the diff completely. For each acceptance criterion in the plan, find the concrete evidence (code + test) that satisfies it. Missing evidence = finding.
3. Re-run the plan's Validation plan commands yourself; do not trust reported output.
4. Record findings in the phase plan's Review log (date, reviewer, findings) and report them in your reply.

## Phase-specific checklist

- [ ] Model matches the plan's column spec exactly (types, nullability, FK targets, `ondelete="RESTRICT"`); no extra columns invented, none dropped.
- [ ] Partial unique index `uix_user_declared_state_records_active` exists **in the migration** with `postgresql_where` (autogenerate often drops it) and is proven by a DB-level test (`IntegrityError` on second open row).
- [ ] Check constraint `exited_at >= entered_at` present in model AND migration; tested.
- [ ] Same-user-different-workspace open rows allowed (test exists).
- [ ] `uds` prefix: verified free, claimed in `client_id_prefix_map.md`.
- [ ] `models/tables/users/README.md` documents the table incl. source-table/never-rebuilt/one-open-row/close-don't-delete rules.
- [ ] **Inertness**: `grep -rn "UserDeclaredStateRecord\|user_declared_state_records" app/beyo_manager/` hits ONLY the model file, `models/__init__.py`, the migration, and tests. Any service/router/worker hit = blocking finding.
- [ ] Migration downgrade drops the table cleanly; upgrade→downgrade→upgrade cycle verified.
- [ ] No soft-delete columns, no `state` enum column (plan explicitly excludes both).
- [ ] Full suite green (proves nothing else changed behavior); ruff clean.

## Verdict

End your report with exactly one of:
- `APPROVED` — all criteria evidenced, checklist clean. The operator will let Codex proceed to summary/archive.
- `NEEDS_CHANGES` — enumerate findings, each with file:line, the plan/master clause it violates, and severity (blocking / minor).
