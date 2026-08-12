---
plan: phase 2 (schema, models & migration)
role: reviewer
round: 2 (re-review, delta-scoped)
date: 2026-08-12
---

# Session prompt — re-review phase 2 after fix cycle r2

You are the **re-reviewing agent** for phase 2. Delta-scoped per the charter
protocol — settled ground is not re-derived.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` (re-review protocol).
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md` — re-review variant.

## Review history (what is settled, and by whom)

- **Review r1 (Claude, CHANGES_REQUESTED):** the SCHEMA was approved on the merits —
  settled ground is enumerated under "Verified correct" in the phase-2 Review log
  (closed-list DDL conformance both directions, 0 metadata diffs, enum-ownership
  round-trip with unchanged oids, per-table shapes, scope fences). Do not re-derive
  it; report anything seen wrong in passing.
- **Open items resolved by fix r2 (Codex, checkpoint `39e6fbe`):** B1 (C2 0→25
  rows), B2 (downgrade proxy now reads `inspect.getsource`), B3 (basis rows
  sole-cause), B4 (remaining CHECK coverage), S1 (README: four columns / three
  types), S2 (`pg_type` assertions), S3 (valuation test renamed + cost-only row),
  N2 taken (`numeric(6,3)` reflected assertion).
- **Concurrent, outside phase scope but on the same tree:** maintenance commit
  `7e1b11d` fixed the from-scratch migration stall (a CYCLE in the historical
  revision graph; guarded in-memory repair in `migrations/env.py`; §10 recipe now
  claims from-scratch verified). Its handoff:
  `handoffs/maintenance/2026-08-12_migration-chain-stall_r1_handoff.md`.
- Fix handoff: `handoffs/implementer/2026-08-12_phase2_fix_r2_handoff.md`.

## Step 1 — verified perimeter (mandatory first step)

`git show 39e6fbe` must contain only: the schema test module, the item_economics
README, the phase-2 plan (Review log), the master-plan tracker row. The maintenance
commit `7e1b11d` must contain only: `app/migrations/env.py`, master plan §10, its
handoff (originally misfiled at repo root — since relocated by the coordinator).
Anything else in either is a finding, attributed to its session.

## Step 2 — full adversarial depth on the changed seam (probes)

- **R2-P1 (row count + mapping):** the fix implemented **25** C2 cases where r1's
  prose said 22 — the fixer followed the plan's table and documented the
  discrepancy. Verify the 25 map one-to-one onto the C2 table's enumerated rows
  (9 (a) + the (b) set + key-column rows), none missing, none invented.
- **R2-P2 (mutations, sampled independently):** the fixer declared 14 predicate-
  clause mutations + 3 downgrade-source mutations + 14 CHECK-drop mutations, all
  reddening named rows. Re-run at least: one clause per multi-clause index (INV-B1,
  INV-E1, INV-V1) **at the DDL site on a disposable DB** (P-G(a) extension binds),
  all three B2 source mutations, and the A1/A2 CHECK drops (B3's sole-cause fix —
  also verify the fixture's basis version is closed so the index cannot fire, and
  the asserted constraint NAME matches). Revert, sha256-verify
  (migration sha `3fc5cd88…48d0`), declare.
- **R2-P3 (combined tree):** full suite on the current HEAD (fix + maintenance
  together): expect 1684 passed / 23 failed / 1 deselected with the failure set
  byte-identical to the §10 baseline. The maintenance session saw a transient
  collection error in the fix's file mid-flight — confirm it is gone.
- **R2-P4 (maintenance verification, light):** using the §10 recipe (now
  from-scratch), build a disposable DB with `alembic upgrade head` from empty —
  it must complete (the stall fix's central claim) — then use that DB for your
  R2-P2 DDL probes and drop it. Confirm the configured dev DB is at head
  `90cdd23a828e`, untouched. Read `migrations/env.py`'s repair block once: confirm
  the guards are conditioned on the exact legacy graph (it must be inert for
  databases at or past head) and that no historical migration file was rewritten
  (rule 7). If anything there looks broader than guarded-and-inert, file it as a
  finding — do not fix.
- **R2-P5 (S1/S2/S3 verification):** README sentence matches §6.3's registered
  reuse; the inventory's `pg_type` assertions exist and bite (drop-simulate one on
  the disposable DB); the renamed valuation test covers what its name claims.

## Step 3 — Review log + tracker + handoff

1. Review log entry (append-only); tracker row (yours only): verdict
   **APPROVED** / **CHANGES_REQUESTED**, Note appended, actor stamps preserved.
2. Archgraph: read-only; zero delta expected from both sessions — verify revision
   still `9476e89a…` / 15 pending, and state it.
3. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase2_rereview_r2_handoff.md`
   (NOTE: full path — a prior session misfiled its handoff by resolving a relative
   path against the repo root): summary; `⚠ OWNER DECISIONS REQUIRED (n)`; probe
   results R2-P1…P5; findings with verbatim correction clauses if any; lessons;
   full write perimeter incl. probe declaration. **Deposit before ending the
   session.**
