---
role: maintenance (light research — diagnosis only, no fixes)
subject: which tests leave rows in the dev DB (phase-4 re-review r3, finding N11)
date: 2026-08-13
run: at the owner's choosing — blocks nothing
---

# Session prompt — light research: suite-wide dev-DB residue

You are a **research agent**. Measure and attribute; **change no code, delete
no rows**. Time-box yourself to roughly one focused session.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`; `PYTHONPATH=. pytest -m 'not e2e'`; dev DB
postgres `127.0.0.1:5433` / `beyo_manager`).

## What was measured (re-review r3, 2026-08-13 — take as given)

One full non-e2e run against the configured dev DB **commits and leaves**
approximately: **+116 workspaces** (names like `shift-hook-*` and
`Workspace <hex>`), **+101 users, +19 tasks, +20 working sections**. The
item-economics tests were measured leaving **zero** — this residue is
pre-existing behaviour of OTHER test modules, which is exactly the working
hypothesis to confirm: the rows are pre-rows of older suites, not the
item-cost implementation.

## Job — answer three questions

1. **Who writes them?** Attribute the residue to test files. Cheap route
   first: grep the giveaway names (`shift-hook`, `"Workspace "` + hex
   construction) across `tests/` — the fixtures that build those names are
   the writers. Confirm by row-count snapshots (workspaces/users/tasks/
   working_sections) before and after running JUST the suspect directories,
   not the whole suite per file.
2. **Why do they survive?** For the top offenders only: do they commit and
   lack teardown, or does teardown exist but not cover these tables?
   (Sessions on the rolled-back `db_session` fixture cannot leak — anything
   leaking uses commits or a second session.)
3. **How big is the existing pile?** Count the accumulated residue currently
   in the dev DB matching those name patterns (count + oldest/newest
   `created_at` — do NOT delete anything).

## Deliverable

A short handoff at
`docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/maintenance/2026-08-13_suite-db-residue_r1_handoff.md`
(full path) with:

- a table: test file → tables leaked → rows per full run → why (commit
  without teardown / partial teardown / other);
- the current accumulated totals in the dev DB per pattern;
- a proportionate remedy recommendation (shared teardown fixture vs
  per-module fixes vs a one-time purge + accepted-residue register) as an
  `⚠ OWNER DECISIONS REQUIRED (1)` card — the owner picks; you fix nothing;
- your write perimeter (should be: the handoff file only).

Rules: configured DB stays at `head`; no row deletion, no code change, no
migration. If attribution is turning into an excavation, deposit what you
have with the top 2–3 offenders named and stop — this is a light pass.
