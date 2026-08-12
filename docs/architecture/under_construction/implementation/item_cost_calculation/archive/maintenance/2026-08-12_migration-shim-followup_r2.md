---
plan: maintenance (migration-environment shim follow-up — outside the item-cost pipeline)
role: maintenance
round: 2
date: 2026-08-12
---

# Session prompt — shim follow-up r2: execute the owner-authorized correction

Round 1 (handoff:
`handoffs/maintenance/2026-08-12_migration-shim-followup_r1_handoff.md`) escalated;
the owner has now decided. **Both authorizations are explicit and recorded**
(`planning/owner_decisions.md`, maintenance card 1, 2026-08-12):

1. **Rule-7 exception, one time, this file only:** edit
   `app/migrations/versions/8cf57fa23110_improve_task_notes_and_image_links.py`
   changing `down_revision` from `'a3b5c7d9e1f2'` to `'183fb6115bd3'` — nothing
   else in that file. Add a short comment above the line: owner-authorized
   metadata correction 2026-08-12, breaking the historical revision-graph cycle;
   no DDL changed.
2. **Anchor form: transient.** The cold-build workspace anchor is inserted only
   during a genuinely cold build and **deleted before `upgrade head` returns** —
   a fresh database ends with zero synthetic rows. Documented in env.py.

Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`.
Read r1's handoff first — its findings (the cycle, the two revisions that consume
the anchor mid-chain: `49bd666da846`, `fb10ac7fd439`) are your map.

## Task

1. Apply the authorized one-line metadata edit.
2. Remove the private-internals graph repair from `app/migrations/env.py`
   entirely (the reparenting + `RevisionMap` rebuild); convert the workspace
   anchor to the transient form (insert on cold build only; delete before
   completion; no residue).
3. **Prove, in order, on disposable databases** (create/drop per master plan §10;
   the configured `beyo_manager` DB is never touched destructively):
   a. from-scratch `alembic upgrade head` completes;
   b. the fresh database contains **zero** `mig_cold_build_workspace` rows (and no
      other synthetic residue);
   c. `alembic upgrade head` on the configured DB is a no-op at `90cdd23a828e`;
   d. full non-e2e suite at the recorded baseline (currently 1684 passed /
      23 failed / 1 deselected — no new failures; note N14: one Shopify test is
      known order-flaky under container load — if it alone fails, re-run clean
      before concluding);
   e. `env.py` contains no reference to `_revision_map`, `nextrev`,
      `_all_nextrev`, or any private Alembic attribute (grep-clean audit).
4. Commit once, when proven: `fix(migrations): make the revision graph acyclic
   (owner-authorized metadata correction) and remove the env shim`. **The handoff
   cites the FINAL commit hash** (do not amend after citing).
5. Update master plan §10's recipe caveat block
   (`docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`)
   to the final state: from-scratch verified, shim removed, anchor transient.

## Constraints

- Perimeter: the one migration file (metadata line + comment ONLY), `env.py`,
  master plan §10 block, your handoff. Nothing else — no other migration, no
  model, no test file, no item-cost pipeline artifact.
- If anything forces a second file's edit or a DDL change, STOP and escalate —
  the authorization covers exactly what is written above.
- The phase-3 pipeline work (pure calculator) may be running concurrently — it
  touches no migrations and no DB; do not touch its files.

## Closing protocol

Deposit the handoff at
`docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/maintenance/2026-08-12_migration-shim-followup_r2_handoff.md`
(full path): frontmatter complete; `⚠ OWNER DECISIONS REQUIRED (n)` (one line if
zero); proof of 3a–3e with numbers; full write perimeter incl. the final commit
hash. **Deposit before ending the session.**
