---
role: maintenance
subject: suite-wide dev-DB residue (phase-4 re-review r3, finding N11)
date: 2026-08-13
run: at the owner's choosing — blocks nothing
---

# Session prompt — maintenance: suite-wide database residue

You are a **maintenance agent**. One bounded job; this blocks no phase gate.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` — rules 7 and 11½ bind.

## The finding (measured, phase-4 re-review r3, 2026-08-13)

A single full non-e2e run (`PYTHONPATH=. pytest -m 'not e2e'` against the
configured dev DB) **commits and leaves** roughly: **+116 workspaces**
(`shift-hook-*`, `Workspace <hex>`), **+101 users, +19 tasks, +20 working
sections**. This is suite-wide standing behaviour — the item-economics tests
were measured leaving zero. Charter rule 11½ (tests that commit own their
teardown) is violated broadly, and the dev DB grows on every full run.

## Job

1. **Attribute:** identify which test modules/fixtures commit without teardown
   (the `shift-hook-*` naming is the first lead; a before/after row diff per
   test module or a `-p no:randomly` bisect both work). Do not guess from
   names — measure.
2. **Recommend, don't mass-fix:** deposit a table (module → tables leaked →
   likely fixture) plus a proportionate remedy proposal (shared teardown
   fixture vs per-module fixes vs a documented accepted-residue register).
   Only apply fixes if the owner has authorized them in the message that
   launched you; otherwise this is a diagnosis deposit.
3. Configured DB stays at `head`; no destructive cleanup of existing rows
   without an explicit owner instruction naming the rows.

## Closing protocol

Deposit the handoff at
`docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/maintenance/2026-08-13_suite-db-residue_r1_handoff.md`
(full path): findings table; `⚠ OWNER DECISIONS REQUIRED (n)` for the remedy
choice; full write perimeter.
