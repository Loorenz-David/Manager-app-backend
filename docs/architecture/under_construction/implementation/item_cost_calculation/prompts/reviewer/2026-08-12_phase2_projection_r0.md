---
plan: phase 2 (schema, models & migration)
role: reviewer
round: 0 (plan-projection)
date: 2026-08-12
---

# Session prompt — plan projection (round 0), phase 2: schema, models & migration

You are the **plan-projection agent** for phase 2 of the item-cost-calculation
pipeline. You implement nothing: you do the implementer's first hour **on paper**,
from the artifacts alone, and record every decision the plan fails to determine.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(branch `fix/idempotent-completion-analytics`). Project folder:
`docs/architecture/under_construction/implementation/item_cost_calculation/`.

## Doctrine (read first, by absolute path, in this order)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md` — shared charter.
2. `/Users/davidloorenz/agent-skills/plan-projection.md` — your session doctrine.

The plan file and its cited authorities are what you project; where this prompt
differs from them, they win.

## Gate check (verify before working; on any failure, stop and report)

- `master_plan.md` §4 tracker shows phase 1 **APPROVED** and phase 2 `NOT_STARTED`
  with a ⚑ projection gate.
- `plans/phase_2_schema_models.md` exists and its Review log is empty.
- No phase-2 implementer handoff exists (you are round 0).

## Read order (after doctrine)

1. `master_plan.md` — §§5, **6 entire** (the naming registry is this phase's
   backbone: tables, prefixes, constraint names, enums with PG-type ownership),
   9 (standing rules, esp. P-B), 10 (environment topology, migration commands,
   DB safety).
2. `plans/phase_2_schema_models.md` — the plan you are projecting.
3. Intention **§4 entire (incl. §4.6 as amended round 6), §4A, §4.7A**; the
   invariants INV-G1/B1/B2/M1/M2/E1/E2/V1/V2; §6A.4's term-nullability table
   (its DB CHECK lands here); §7A.1/§7A.2 (the chains the partial uniques must
   arbitrate); §10.1; §16 rounds 3–6 changelog for what was amended when.
4. Contracts: `03_models`, `30_migrations`, `21_naming_conventions`,
   `25_soft_delete`, `24_multi_tenancy` (+ core per master plan §5).

Line numbers in planning artifacts date to 2026-08-11/12 — verify by symbol name.

## Depth targets (the phase's silent-failure mechanisms — tracker flags rows
1, 3, 8, 11, 12, 15 DDL-side, plus the round-6 schema delta)

1. **Registry ↔ DDL conformance** — every table/prefix/constraint/enum name in
   master plan §6.1–6.3 must be DDL-expressible and collision-free: verify the
   nine prefixes against `client_id_prefix_map.md` in the tree, the constraint
   names against the repo's `uix_`/`ck_` idioms, and the partial-unique
   predicates against the `postgresql_where` migration idiom (`595e7b840926`).
2. **PG enum type ownership** — the three currency PG types (`create_type=True`,
   one per column), the reused `business_task_type_enum` /
   `task_return_source_enum` / `task_state_enum` (`create_type=False`, ownership
   stays on `tasks`): simulate the autogenerate + hand-fix pass on paper — which
   types the migration creates, which it must NOT create, and what `downgrade`
   drops (the R2-1 ownership rule cuts both ways).
3. **Round-6 result columns (§4.6 as amended)** — `task_state_snapshot` NOT NULL
   enum copy; `task_closed_at` nullable; `unique(task_id)`; no soft delete
   (`created_at` only). Verify the plan's tasks and criteria carry them
   decidably.
4. **CHECK totality** — §6A.4's per-type nullability CHECK
   (`ck_cost_model_terms_value_by_type`): is the CHECK expression fully
   determined by the artifacts (all three types × column presence), and does a
   criterion exist per branch? Same for window CHECKs, money CHECKs (A1
   `> 0` vs `≥ 0` distinctions), and the valuation at-least-one-amount CHECK.
5. **Migration reversibility** — the schema migration's `downgrade` (charter
   rule 7; disposable-DB round-trip criterion with its automated in-suite
   proxy): decidable from the plan? Journal table explicitly NOT in this phase
   (it is phase 6's)?
6. **Criteria decidability & first-hour reality** — could two honest
   implementers read any criterion differently? Do the file paths, registration
   points (`models/__init__.py`, prefix map, `models/tables/item_economics/README.md`),
   and alembic environment facts hold against the real tree? Apply master plan
   P-G where criteria rows mirror each other (per-table constraint rows): are
   they separately required with named mutations where warranted?

## Constraints

- **No implementation, no code edits.** Read-only against the tree; running
  collection or read-only commands is permitted per your doctrine; write nothing
  outside your handoff.
- Write perimeter: your handoff file ONLY. Plan defects are ledger entries for
  the coordinator — never fixed in place.
- Archgraph: `archgraph_status` + orient on `table-task-step`, `table-task-item`
  if useful; read-only; never adjudicate pending reviews; no delta.

## Closing protocol

1. Deposit the handoff at
   `handoffs/reviewer/2026-08-12_phase2_projection_r0_handoff.md` with frontmatter
   `plan: phase 2`, `role: reviewer`, `round: 0`, `date`, `state`, `verdict`,
   `actor`.
2. Body, in order: opening summary; **`⚠ OWNER DECISIONS REQUIRED (n)`** (charter
   card format; one line if zero); the **decision ledger** (every decision the
   plan fails to determine: severity + routing recommendation); citation/path/
   criteria-decidability results; the **explicit delegation list**; your full
   write perimeter (expected: this handoff, nothing else). **Deposit the handoff
   before ending the session** — the coordinator's routing is blocked without it.
3. Verdict per your doctrine. The implementer prompt is compiled only after the
   coordinator routes your ledger — do not soften findings to unblock the phase.
