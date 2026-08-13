---
plan: phase 4B (category-driven group selection)
role: planner
round: 1
date: 2026-08-12
---

# Session prompt — plan phase 4B: category-driven group selection (§7C)

You are the **implementation-planner** for a single inserted phase of the
item-cost-calculation pipeline. You produce ONE phase plan file; the master plan
already carries the sequencing, tracker row, and registry deltas.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-planner.md` — you are producing
   one phase plan, not a plan set; every other master-plan duty is already done.

## Gate check

- `master_plan.md` §4 carries the 4B tracker row (NOT_STARTED); §7's sequencing
  inserts 4B between 4 and 5; §6.2/§6.3 carry the INV-G3 index name and the
  major-category enum-reuse row.
- `plans/phase_4b_category_selection.md` does not exist yet.
- Phase 4 may still be under review — that is fine; your plan's dependency line is
  "phase 4 APPROVED".

## Read order (after doctrine)

1. Intention **§7C entire** (round 12 — the semantic authority for this phase),
   §11A.4 as amended (12 ordered values; `item_missing_major_category` first among
   group-2 reasons), §7A.5 (the superseded rows — your criteria must show the
   classifier's total order over the NEW rule set), §4.1/§4A, §7.5/§7A.6 (the
   guards your category-immutability rule composes with), R12-1 in
   `planning/owner_decisions.md`.
2. `master_plan.md` §§5, 6 entire (registry as amended — you PIN the exact
   Python class and PG type name for the major-category enum after verifying the
   items-domain owner in-tree, and you pin the INV-G3 conflict identity in §6.4
   style: propose it in your handoff for the coordinator to register), 9 (P-B…P-Q
   all bind), 10.
3. In-tree, verify rather than assume: the items-domain major-category enum (its
   Python class, PG type name, and `create_type` owner — research_context cites
   `item_categories.major_category` and the denormalized
   `items.item_major_category_snapshot`); phase 4's shipped
   `configuration.py`/status query/group commands (the code your phase reworks —
   phase 4 is IMPLEMENTED, under review); the phase-2 migration idiom for adding a
   NOT NULL column with a pre-flight (journal exemplar `97b60e06d42a`,
   `677ed7131bb2` enum handling).

## The phase must cover (from §7C — enumerate, never sample)

- Schema delta: `major_category` NOT NULL (enum reuse, `create_type=False` in the
  migration — the model-layer flag is inert, phase-2 lesson), INV-G3 partial
  unique, migration + downgrade with the §7C.1 pre-flight (report-never-guess on
  uncategorizable rows), the C1(b)-style static downgrade proxy (P-J).
- Group commands: `major_category` required at creation; **immutable once any
  basis version exists** (§7C.4 — exact predicate pinned); INV-G3 dual-path
  conflict identity; update/list/serializer surfaces gain the field.
- Classifier rework: the §7C.2 total ordered rule (category → group-for-category →
  open basis), `item_missing_major_category` first among group-2 reasons,
  precedence still an explicit sequence (never enum iteration — the B6 structural
  guard extends to the new value); `EconomicsStatusEnum` gains the member.
- Status query: per-category evaluability blocks + shared cost-model fields
  (§7C.3) — a breaking shape change to phase 4's payload; the plan states the
  new shape exactly and updates phase 4's shipped tests deliberately (named, per
  the phase-1 D8 lesson — which tests change and on whose authority).
- Criteria discipline: P-G…P-Q all apply — per-clause (b) rows for INV-G3, named
  mutations with observed-node-id declarations (P-I), implication pins with
  sole-cause fixtures (P-Q), harness/database stated per criterion (the phase-4
  harness block is your precedent), role gates + audit rows for changed commands
  (C11 pattern; the audit vocabulary gains `production_cost_group.*` variants only
  if the events change — verify).

## Constraints

- Write perimeter: `plans/phase_4b_category_selection.md` + your handoff. No
  master-plan edits (propose registry additions in the handoff; the coordinator
  applies them), no intention edits, no code.
- Anything §7C fails to determine → decision ledger rows in your handoff (owner
  cards only if a product semantic is genuinely open).

## Closing protocol

Deposit the handoff at
`docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/planner/2026-08-12_phase4b_planner_r1_handoff.md`
(full path): frontmatter complete; `⚠ OWNER DECISIONS REQUIRED (n)` (one line if
zero); proposed registry additions (enum class/type name verified in-tree; INV-G3
identity; any new audit events); the phase table row (goal, projection-gate flag —
it is ⚑ MANDATORY); anything you could not plan; full write perimeter. **Deposit
before ending the session.**
