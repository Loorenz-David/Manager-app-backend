---
plan: phase 4B (category-driven group selection)
role: planner
round: 1
date: 2026-08-12
state: PLANNED
actor: planner (Claude)
---

# Planner handoff — phase 4B plan authored

`plans/phase_4b_category_selection.md` is written and executable from its
Read-first list. Gate check passed before writing: the §4 tracker row, §7
sequencing insert, §6.2 INV-G3 name and §6.3 enum-reuse row were all present;
the plan file did not exist. All §7C-cited in-tree facts were verified, not
assumed (section "Verified in-tree facts" in the plan); the §7C.3 breaking
payload shape is stated exactly; the four phase-4/phase-2 test nodes the phase
deliberately changes are named with their authorities (D8 discipline).

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner — round 12's pins 1–2 determined every product
semantic; the four interpretation pins below are technical and go to the
coordinator (ledger).

## Proposed registry additions (coordinator applies; no master-plan edits made)

1. **§6.3 major-category row — complete the pin (verified in-tree
   2026-08-12):** Python class `ItemMajorCategoryEnum`
   (`app/beyo_manager/domain/items/enums.py:17`; members `WOOD = "wood"`,
   `SEAT = "seat"`). PG type **`item_major_category_enum`**; type-creation
   ownership `item_categories.major_category`
   (`models/tables/items/item_category.py:24-28`, `create_type=True` there);
   4B's column and migration reference it with `create_type=False`
   (migration-site per the phase-2 lesson). PG labels verified live in the
   dev DB: `wood`, `seat`.
2. **§6.3 `EconomicsStatusEnum` row:** the members are now the **12 ordered
   values of §11A.4 as amended by §7C.3** — recommend replacing the stale
   "the 11 members" prose with the item list or "12" derived from §11A.4
   (P-L: items, never counts). New member
   `ITEM_MISSING_MAJOR_CATEGORY = "item_missing_major_category"`.
3. **§6.4 error identities (registry-authored, dual-path sibling format):**
   - `ITEM_COST_GROUP_CATEGORY_TAKEN` —
     `uix_production_cost_groups_major_category_active`; `ValidationError` on
     the pre-check (create AND update-flip), `ConflictError` on the DB
     conflict path via `INDEX_IDENTITIES`; message names the category value.
   - `ITEM_COST_GROUP_CATEGORY_IMMUTABLE` — `ValidationError`; §7C.4's
     immutability refusal; message names the group and its current category.
4. **§6.4 audit vocabulary: NO additions** — verified: 4B changes what
   `production_cost_group.created` / `.updated` carry, never the event names;
   the registered set stands.
5. **§6.5 `configuration.py` public surface +=** `resolve_major_category`
   (pure snapshot-string → `ItemMajorCategoryEnum | None` canonicalizer;
   phases 5/7/8 call it — they never read the snapshot column directly).
6. **§6.5 serializers note:** `serialize_production_cost_group` carries
   `major_category` from 4B on.
7. **Migration filename slug (naming registry):**
   `add_major_category_to_production_cost_groups`.

## Phase table row (for §4; also mirrors the plan)

| # | Phase | Plan file | Gate | State |
|---|---|---|---|---|
| 4B | Category-driven group selection (§7C): NOT NULL enum column + INV-G3 + §7C.2 classifier + per-category status payload | `plans/phase_4b_category_selection.md` | **⚑ MANDATORY** (selection is the S1 mechanism; inventory row 19 superseded by §7C; breaking payload reshape) | NOT_STARTED (plan authored 2026-08-12) |

## Decision ledger — pinned interpretations (coordinator ratifies or reroutes)

| # | §7C left undetermined | Pin in the plan | Basis |
|---|---|---|---|
| L1 | "once **any** basis version exists" — deleted rows included? | ALL rows, `is_deleted` irrelevant (plan task 3, C4(b) has the arbiter) | plain reading; phase-4 N3 precedent (history existed); escape hatch verified — group delete counts only non-deleted versions, so delete-and-recreate stays open |
| L2 | snapshot string outside the wood/seat vocabulary (column is `String(64)`, unenforced) | treated as missing → `item_missing_major_category` (C5 V0 row) | R-9 never-guess; `not_configured_no_cost_group` would prescribe the wrong repair (config fix vs item fix) |
| L3 | update carrying the CURRENT category while immutable | accepted no-op (C4(d) has the arbiter) | idempotent PATCH; refusal would break benign full-object updates |
| L4 | §7C.3 payload shape beyond "blocks + shared fields" | exact shape pinned in plan task 6; old top-level keys removed; `categories` keyed by enum value, both members always present | prompt grants the planner the shape ("the plan states the new shape exactly"); minimal §7C.3 surface — "(group? open basis?)" |

## Could not plan (forwarded, not gaps)

- **Phase-5/8 consumption rows** of `resolve_major_category` and the
  `item_missing_major_category` null-numerics payload (P-B) — forwarded in the
  plan's Notes; phase 5's plan predates round 12, so the coordinator folds
  §7C into its prompt at prompt time.
- **Breaking-test list freshness:** phase 4 is still in review; its fix cycles
  may add test nodes touching the old shapes. The plan's Dependencies section
  carries the exact re-verification greps for the coordinator at prompt time.
- **Migration revision id** — resolvable only at implementation time (chain
  head moves); the slug is registered above.

## Write perimeter (this session, complete)

- `plans/phase_4b_category_selection.md` (new)
- `handoffs/planner/2026-08-12_phase4b_planner_r1_handoff.md` (this file)
- No code, no master-plan edit, no intention edit, no archgraph mutation
  (archgraph not consulted — all orientation was file-based; zero graph
  delta).
