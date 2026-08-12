---
plan: maintenance (migration-chain stall — outside the item-cost pipeline)
role: maintenance
round: 1
date: 2026-08-12
---

# Session prompt — root-cause the from-scratch migration-chain stall

You are a **maintenance agent**. This item is owner-commissioned (phase-2 review
card 1, answered 2026-08-12) and is **independent of the item-cost pipeline** — do
not touch its artifacts or its in-flight phase work.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.

## The defect (reviewer-verified 2026-08-12)

A from-scratch `alembic upgrade` against an **empty** database hangs at the very
first statement (`CREATE TABLE alembic_version`) and never returns —
`pg_stat_activity` shows the session `idle in transaction` / `Client:ClientRead`,
zero tables created. Reproduced targeting revision `7758ea23764e` (so it predates the
item-cost work entirely). Forward migration from an existing database works fine —
the defect only blocks clean builds: new developers, CI database steps, disaster
recovery. 114 revisions, linear chain; `transaction_per_migration=True`
(`migrations/env.py:72`); `settings.database_url` is the target (a real
`DATABASE_URL` env var overrides `.env`).

## Task

1. **Reproduce** on a disposable database (create
   `beyo_manager_stall_probe` via `PYTHONPATH=. APP_ENV=development
   DATABASE_URL=… python3 -m scripts.create_db`; drop it when done). Never touch the
   configured `beyo_manager` DB destructively (it stays at head).
2. **Root-cause.** Likely suspects to check first: `migrations/env.py`'s async/engine
   handling on a cold database (the `idle in transaction` + `ClientRead` signature
   suggests a second connection waiting on a lock the first holds, or an
   un-awaited/un-committed setup path), `scripts/create_db` vs alembic interplay, or
   an early revision acquiring something it never releases when `alembic_version`
   does not yet exist.
3. **Fix minimally.** Charter rule 7 binds: **never rewrite an applied migration** —
   if the cause is inside a historical revision, the fix is env-level or a follow-up
   mechanism, not an edit to the applied file (escalate to the owner if only a
   rewrite would work). If the cause is in `env.py`/scripts, fix there.
4. **Prove it:** a full from-scratch `alembic upgrade head` completes on the
   disposable DB; then `make db-migrate` against the configured DB still succeeds
   (no-op at head). Record timings.
5. Update master plan §10's caveat in
   `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
   (the item-cost pipeline consumes the recipe): replace the clone-workaround caveat
   with the fixed from-scratch recipe, marked verified.

## Constraints

- Write perimeter: the fix (env/scripts level), the §10 caveat update, and your
  handoff. No test-suite changes, no model changes, no item-cost pipeline files
  beyond §10.
- Full non-e2e suite must stay at the recorded baseline (23 known failures, no new).
- Commit as `fix(migrations): <summary>` when proven (standing checkpoint
  authorization does not apply here — this is not a pipeline phase; commit once,
  when done and verified).

## Closing protocol

Deposit the handoff at
`handoffs/maintenance/2026-08-12_migration-chain-stall_r1_handoff.md` (frontmatter
`plan`, `role`, `round`, `date`, `state`, `verdict`, `actor`): root cause with
evidence; the fix and why it is minimal; proof of the from-scratch build; full write
perimeter incl. the commit hash; `⚠ OWNER DECISIONS REQUIRED (n)` (one line if
zero — escalate here if the only viable fix rewrites an applied migration).
