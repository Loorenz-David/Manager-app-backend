---
plan: phase 5 (valuation surface)
role: reviewer (projection)
round: 0 (pre-implementation projection gate)
date: 2026-08-13
---

# Session prompt — phase 5 projection, round 0

You are the **projectionist** for phase 5. The plan was written on 2026-08-11,
BEFORE owner round 12 (§7C) and before phases 4/4B shipped — your job is to
find where it no longer survives contact with the code and semantics as they
exist NOW, and to deposit an amendment ledger, not to implement anything.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

## Ground

- Plan under projection: `plans/phase_5_valuation_surface.md` (incl. its Notes
  forward items — the N7-consumption persisted-rate arbiter, the N-d live-data
  note, and the phase-4 forward-notes block N4/N5/N8/N9).
- Semantic authority: intention §§4A, 6A (esp. §6A.9 valuation-currency), §7C
  ENTIRE (round 12 — the plan predates it), §8B, §11A.4 (12 ordered values);
  owner pins R12-1 1–2 in `planning/owner_decisions.md`.
- Registry: master plan §6 (identities incl. the two 4B additions; §6.5 files);
  §9 rules P-A…P-Z ALL bind (P-V ids name authority rows; P-W filter rows
  compete; P-X name what a harness can see; P-Y assertion shape per row; P-Q
  implication fixtures; P-R router harness named).
- Shipped reality to project against (phases 4+4B, both APPROVED):
  - `resolve_economics_configuration(major_category, groups, basis_versions,
    cost_model_versions, on_date)` — category-aware, §7C.2 total order,
    `item_missing_major_category` FIRST (`domain/item_economics/configuration.py:44-82`).
  - `resolve_major_category(snapshot)` (`configuration.py`) — the per-item
    entry point whose FIRST production caller lands in THIS phase (plan Notes:
    "preview calls `resolve_major_category`, never reads the snapshot
    directly"; `item_missing_major_category` payload rows carry null numerics
    per P-B).
  - Per-category status shape (categories.{wood,seat} + shared model flag);
    INV-G3 (one active group per workspace+category);
    `ITEM_COST_GROUP_CATEGORY_TAKEN` / `…_IMMUTABLE` registered.
  - Calculator (phase 3): 19-name `__all__`, Q1–Q5, rederive totality.

## Environment facts (verified at prompt time)

- Migration head `5caae620088c` (4B's category migration). Suite baseline:
  **1927 passed / 23 known failures (byte-identical phase-1 list) / 1
  deselected**; collection 1950 total. Focused economics selector precedent in
  `archive/plan_4b/2026-08-13_phase4b_fix_r1_handoff.md`.
- Dev DB at head; economics tables at ZERO rows (post-closeout). The N-d
  live-data claim ("37 items with NULL `item_major_category_snapshot`, 225
  wood / 193 seat") predates recent suite runs — RE-MEASURE it live; the
  wider suite is known to commit non-economics residue per run (§10), so item
  counts may have drifted.

## Projection axes (minimum — the ledger is yours)

1. **Round-12 drift:** every plan criterion that names the classifier, group
   selection, or status payload — does it still match the §7C signatures and
   shapes that actually shipped? (The plan predates them.)
2. **Dependencies greps re-run** against the final tree (the 4B N-f lesson):
   the plan's file list and "shipped tests that change" claims; include
   `resolve_major_category`, `ItemValuation`, the valuation
   serializer/routes, and any payload keys the preview shape touches (P
   practice: grep payload KEYS across the test tree, not only callers).
3. **Criteria quality against §9 as it stands now:** P-V table mappings, P-W
   competing fixtures, P-Q implication pins (the N7-consumption arbiter is
   exactly one — a fixture from the Q2-tie family where persisted ≠
   re-divided), P-X harness visibility, P-Y shapes per row, P-R router
   harness naming.
4. **Unvalued-item semantics:** R-9 (never zero, explicit state) — the plan's
   preview rows for unvalued and category-less items; `null` numerics (P-B).
5. **Ledger-recorded environment facts:** disposable-DB needs (likely none —
   valuation is service-layer), teardown scope statements (rule-11½ record).

## Closing protocol

1. Deposit an amendment LEDGER (numbered rows, each with severity
   blocking/should-fix/note, the plan section it amends, and the verified
   correction) — AMENDMENTS_REQUIRED expected if any row is blocking.
   `⚠ OWNER DECISIONS REQUIRED (n)` for anything semantic (cards verbatim,
   story-shaped, with branches + recommendation + on-silence).
2. No code, no plan edits (the coordinator routes), archgraph READ-ONLY
   (state revision `88e185f7…`, 148 nodes / 188 edges, 0 pending — zero
   delta).
3. Deposit at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-13_phase5_projection_r0_handoff.md`
   (full path, AFTER your writes): ledger; live N-d re-measurement; full
   write perimeter.
