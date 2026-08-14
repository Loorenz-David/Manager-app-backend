---
plan: phase 6 (legacy money migration & API bridge)
role: reviewer
round: 1
date: 2026-08-14
---

# Session prompt — review phase 6 implementation r1

You are the **reviewing agent** for phase 6 — the DESTRUCTIVE phase. Re-derive
independently; never accept a declaration you can re-run. The live database
was measured empty of legacy money at projection time, so the real evidence
lives on seeded disposables — vacuous green is the enemy here.
Workspace: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
(commands from `backend/app/`, per master plan §10).

## Doctrine (read by absolute path)

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Ground

- Plan: `plans/phase_6_legacy_migration_api_bridge.md` — base + forward note +
  the GOVERNING "Round-0 projection amendments" (D1–D23). Intention **round 14
  as folded**: §10A.1(a)–(c), §10A.2 incl. P3, §10A.3 as corrected; §6.4's
  corrected ITEM_MONEY_MOVED row. §9 P-A…P-AA and all extensions bind.
- Checkpoint `b940309` (final; deposit `0f43071` handoff-only):
  `handoffs/implementer/2026-08-14_phase6_implement_r1_handoff.md`. The
  mutation ledger's hashes live in the PLAN's Review log (a deviation from the
  handoff-carries-ledger norm — verify completeness there first).
- Projection evidence to reuse (the r0 handoff): the census pre-counts (479
  items, all zeros), the D1 executed error-translation table, the D4
  nine-endpoint census, the six-site write census.

## Coordinator consumption findings (route into your probes)

- **P6-A (undeclared perimeter deviation):** the checkpoint touches
  `models/tables/items/item_upholstery_requirement.py` (2 lines) — absent
  from the handoff's record and from the prompt's fence. Expected legitimacy:
  the R2-1 enum-ownership flip (`create_type` moving off the dropped
  `items.item_currency`). VERIFY: the diff is exactly that flip; the
  migration-site flags are what count (phase-2/4B lesson) — check the drop
  migration's downgrade uses `create_type=False`, and prove the cold-build
  end state (disposable, empty → head): `item_currency_enum` exists with
  exactly ONE column user. Also note the five write-path command files in the
  checkpoint (`_create_item_in_session`, `create_item`, `find_or_create_item`,
  `update_item`, `create_task`) — required by §10.2 step 2 but unlisted in
  the prompt's fence (coordinator gap, recorded; verify their diffs remove
  ONLY the three-key writes).
- **P6-B (ledger location + completeness):** the handoff summarizes five
  probes; the plan Review log must carry per-row hashes + full observed red
  sets (P-I sixth/seventh ext). The five named in the amendments: D5's PAIR
  (task-validator deletion; item-validators deletion), D4's TWO serializer
  mutations (each with its full red set — the base-serializer one should
  redden the three item rows incl. customer-detail), D6's router-retention
  row. Re-run at least three, hash-verified.
- **P6-C (arithmetic):** suite 1997/23/1 = 2020 selected (coordinator
  re-collected: exact; +29 over 1991). Reconcile the focused split (29
  phase-6 + 1 tie-breaker vs +29 collection). `items` 479 → 480 since the
  projection census — attribute (expected: the known suite-wide residue
  class, not phase-6 tests; state the scope).

## Step 2 — the criteria, re-derived (seeded disposables throughout)

- **C1/C2 (data migration):** seed a disposable at the PRE-data-migration
  revision with the full §10A.2 case table (eligible rows, currency-only,
  soft-deleted-with-amount, the collision row per §10A.1(a), a
  soft-deleted-valuation item per (c)) and run `upgrade`: journal rows,
  created valuations, attribution (= item's `created_by_id`), the mapping
  byte-equality (all three pairs individually, P-O), post-conditions per the
  RESTATED pc2 — all by STATE QUERIES. Run the copy TWICE — second pass a
  no-op without aborting. Then the three REFUSALS (P1 amount+NULL currency;
  P2 negative; P3 amount+NULL creator): each aborts with a row report and
  persists NOTHING (state-queried). Non-vacuity: assert the seeded eligible
  set was non-empty before every green.
- **C3 (reversibility):** the exact revision pair — downgrade the drop
  (columns return NULL), downgrade the data migration (journal repopulates
  all three columns byte-identically, created valuations deleted by
  `valuation_client_id` only — a manually created valuation SURVIVES), then
  upgrade again. End states by state queries.
- **C4 (bridge):** through the TestClient harness (P-R): per schema —
  absent → 200, present-null → 200, present-non-null → 422 with the EXACT
  full message and the `{"error", "ok": false}` envelope (the D1 executed
  table is your oracle — a mangled leading token is a regression to the
  broken design); D6's survival row (a non-NULL value reaches the command
  validator through the router body); D16's collapse honored on create-item;
  D5's fixture branches both covered.
- **C5 (the nine-row census, P-V):** ids map one-for-one onto D4's table —
  no omissions (customer-detail `linked_items[]` is the row history
  forgets); key-set assertions on production serializer output; both
  serializer mutations re-run with full red sets.
- **C6 (drop):** live-schema rows at head; the pg_type/pg_attribute
  structural row (exactly one remaining enum user); FILTERED
  `compare_metadata` (P-X caveat); the journal survives at head (0 rows,
  table present — protected from autogenerate by the `_journal` suffix; one
  line confirms the name matches).
- **The tie-breaker row (D14):** synthetic two-row identical-`created_at`
  fixture asserting `client_id DESC` — verify it's labeled synthetic and
  actually ties.
- **Suite:** 1997/23/1 re-run yourself, failure set byte-identical to the
  phase-1 baseline; ruff; configured DB at head `be9dfe42a035`; zero
  `beyo_manager_phase6_*` disposables remain (catalog query).

## Step 3 — architecture graph (read-only + service)

Expect: 1 new pending node (`table-item-valuation-migration-journal`) + the 6
prior pending items (the phase-5 read-surface delta) = 7 pending. Do NOT
adjudicate. Verify the journal node's claims against both migration
directions, spot-check the 6 prior items' spans still hold after this phase's
diffs (`set_item_valuation.py` untouched this phase — confirm), and deliver
the anchor-spans service for all 7 for the coordinator's post-approval pass.
Also confirm the `node:table-item` description edit is correctly LEFT to the
coordinator (its "until phase 6's migration" sentence is now stale — a
maintenance edit under §8, not the implementer's).

## Closing protocol

1. Review log entry; tracker verdict (stamps preserved); per-finding verified
   corrections if CHANGES_REQUESTED.
2. Deposit the handoff at
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase6_review_r1_handoff.md`
   (full path, AFTER your writes): summary; `⚠ OWNER DECISIONS REQUIRED (n)`;
   P6-A/B/C outcomes stated; probe declaration with copy-pasted sha256 pairs;
   disposables listed and dropped; full write perimeter.
