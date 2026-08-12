---
plan: phase 2 (schema, models & migration)
role: review
round: 3 (re-review, delta-scoped — single finding)
verdict: APPROVED
date: 2026-08-12
actor: Claude (plan-reviewer)
---

# Phase 2 re-review r3 handoff

**Verdict: APPROVED.** B5 — the single finding left open by r2 — is resolved and
independently mutation-verified. Phase 2 is complete: the schema was settled on the
merits at r1, the test layer at r2 bar one row, and that row now arbitrates the
invariant it names. One new note (N14), pre-existing and outside this phase.

Fix r3 did exactly what the correction clause asked and nothing more. The optional
notes N12 and N13 were deliberately not taken — compliant, not a finding.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner this round. The 14 promote / 1 edit archgraph
recommendations from r1 remain held for post-approval adjudication, which is now due.

## Step 1 — verified perimeter

`git show e9d6ac6` contains exactly three files:

| File | Change |
|---|---|
| `app/tests/integration/models/item_economics/test_item_economics_schema.py` | +5 / −2 |
| `docs/…/plans/phase_2_schema_models.md` | +22 / −0 (Review log) |
| `docs/…/master_plan.md` | +1 / −1 (tracker row) |

Nothing outside the perimeter. Checkpoint not amended (`e9d6ac6` is final). No
production code, no model, no migration, no schema change. Working tree clean at close.

**Discrepancy, coordinator-side:** the prompt specified the test module as **+7/−2**;
it is **+5/−2**. The change itself is exactly the correction clause, so this is a
transcription slip in the prompt, not a fix-cycle defect.

## Step 2 — B5 verification (the whole scope)

### 2.1 Fixture read — correct

The `sections_conflict` / `sections_removed` branch now builds:

```
second_group = ProductionCostGroup(workspace_id=workspace.client_id,
                                   name=f"group {uuid4().hex}", created_by_id=user.client_id)
first  = ProductionCostGroupSection(… production_cost_group_id=group.client_id,
                                    working_section_id=section.client_id …)
second = ProductionCostGroupSection(… production_cost_group_id=second_group.client_id,
                                    working_section_id=section.client_id,
                                    removed_at=now if case == "sections_removed" else None)
```

- The two memberships share exactly `(workspace_id, working_section_id)` and **differ
  in group** — the C2 cell's "section active in two groups".
- `sections_removed` differs from the (a) row **only** in `removed_at`, and stays on
  the second group.
- The second group's name is a fresh uuid, so `uix_production_cost_groups_name_active`
  cannot become a second sufficient cause.

### 2.2 Named mutation, re-run by the reviewer — bites, exactly

Disposable database `beyo_manager_rereview_r3` built from empty with the §10
from-scratch recipe (empty → `90cdd23a828e` in **1.63s**); baseline on it 79 passed.

| Mutation (name preserved, DDL site) | Expected | Result |
|---|---|---|
| key widened to `(workspace_id, production_cost_group_id, working_section_id)` — destroys INV-G1 | exactly `sections_conflict` red | **1 failed / 78 passed**, the failure being exactly `…[sections_conflict]`. Zero collateral. |
| `removed_at IS NULL` clause dropped — reviewer addition, closes INV-G1's pair | exactly `sections_removed` red | **1 failed / 78 passed**, the failure being exactly `…[sections_removed]`. Zero collateral. |

DDL verified before and after from `pg_indexes`, byte-identical:
`CREATE UNIQUE INDEX uix_production_cost_group_sections_active ON
public.production_cost_group_sections USING btree (workspace_id, working_section_id)
WHERE (removed_at IS NULL)`. Module back to **79 passed** after restoration.

r2's proof — that the widening mutation left all 79 green — is closed by construction.
The second mutation additionally converts one of the seven clause mutations r2 left
standing on the fixer's declaration into a re-derived result: **INV-G1 now has both
arbiters live**, the (a) row biting on key width and the (b) row on the predicate
clause.

### 2.3 Full suite — 1684 / 23 / 1, baseline-identical

Clean run on HEAD: **1684 passed / 23 failed / 1 deselected**, failure set
**byte-identical** to the phase-1 recorded 23-item baseline (sorted set-diff empty),
zero connection noise.

**Disclosure of a confound this session created.** The reviewer's *first* suite run was
launched in the background and overlapped this session's own disposable-database
probes in the same postgres container. It reported **24 failed / 1683 passed** — one
extra failure, `test_process_shopify_products_fans_out_to_all_active_workspace_shops_
and_enqueues_one_task`, unrelated to phase 2. The disposable database was dropped and
the suite re-run with nothing else touching the container: **1684 / 23 / 1**, set
byte-identical. The recorded result is the clean run. The extra failure's cause is
structural and pre-existing — see N14 — not attributable to phase 2, whose entire diff
this cycle is one fixture in the item_economics module.

## Findings

### N14 (note, passing-glance — pre-existing, outside phase 2)

`tests/integration/services/commands/shopify/test_process_shopify_products_integration.py`
compares an unordered query result as an ordered list:

- `rows` is `select(ShopifyProductSyncItem).where(workspace_id == …)` — **no
  `ORDER BY`**;
- line 176 asserts `"sync_item_client_ids": [row.client_id for row in rows]` inside an
  ordered-list equality against the command's return value.

The test's own comment two lines above documents this exact hazard for
`event_client_ids` and compares *those* as a set — the same latent defect, half-fixed.
Observed failing once under container load with the two ids transposed and contents
identical.

*Why it is worth filing:* this project gates every phase on a **byte-identical**
comparison against the 23-item baseline. A randomly flaky member of that set costs a
future round a false regression hunt — which is precisely what it cost this one.

*Correction (whenever that file is next touched):* compare `sync_item_client_ids` as a
set, or add an `ORDER BY` to the query. Not phase-2 work; do not open a fix cycle for it.

### Minor, recorded not filed

The fix-r3 handoff transcribes the archgraph revision as
`9476e89ab7d263e43bf8eb055ccc6d0f8186ba34c861787c4d1422c4890019e` — 63 hex characters,
one short of the real 64-character digest (`…019e6`). Harmless here, but a "revision
unchanged" check compares strings.

## Carry-forward dispositions (final for phase 2)

| Item | Origin | Destination |
|---|---|---|
| N3 — `EconomicsStatusEnum` declaration order ≠ §11A.4 evaluation order | r1 | phase 4 (the ordered classifier must not derive precedence by iterating the enum) |
| N4 — `checkfirst=True` on the five new types | r1 | phase 9 drift batch |
| N5 — `client_id_prefix_map.md` row ordering | r1 | phase 9 drift batch |
| N8 — B2 proxy regex misses a raw-SQL `DROP TYPE` | r2 | next touch of the migration / phase 9 |
| N9 — maintenance handoff commit hash wrong | r2 | coordinator (recorded) |
| N10 — cold-build workspace row written into every cold DB | r2 | maintenance ledger |
| N11 — private-Alembic-internals graph shim | r2 | maintenance ledger |
| N12 — C2 (a) rows lack `match=` | r2 | next touch (optional; correctly not taken in r3) |
| N13 — `DBAPIError` too broad on the numeric-bound row | r2 | next touch (optional; correctly not taken in r3) |
| N14 — Shopify order-dependent assertion | r3 | next touch of that file / phase 9 |
| N1, N2, N6, N7 | r1 | closed |
| B1–B5, S1–S3 | r1, r2 | **closed** |

Nothing evaporates: every open note has a named destination phase.

## Lessons for the plans

None new this round. r2's L1–L3 stand and are already folded upstream; L2 in particular
("an (a) conflict row must name the key columns it discriminates, not only the predicate
clauses") is what this round confirmed to be worth the cost — the corrected row is now
the only reason INV-G1 has a live arbiter.

## Archgraph

Read-only this session (`archgraph_status` only). **Zero delta** — revision
`9476e89ab7d263e43bf8eb055ccc6d0f8186ba34c861787c4d1422c4890019e6`, 125 nodes,
161 edges, **15 pending reviews**, 0 stale nodes, 0 diagnostics, permission mode
`review`. Unchanged since r1. No promotion, rejection or edit was performed. With the
phase now APPROVED, the 14 promote / 1 edit recommendations from r1 are due for the
owner's adjudication via the coordinator's standing §8 flow.

## Full write perimeter (this session)

**Documents written (3):**
- `docs/…/plans/phase_2_schema_models.md` — Review log entry "2026-08-12 — reviewer r3" appended (append-only; no prior entry edited).
- `docs/…/master_plan.md` — phase-2 tracker row only: state IMPLEMENTED → **APPROVED**, actor list extended with "reviewer r3 (Claude)", Note appended. Prior actor stamps preserved; no other row touched.
- `docs/…/handoffs/reviewer/2026-08-12_phase2_rereview_r3_handoff.md` — this file.

**Production code / tests changed: none.**

**Mutation-probe declaration.**
- *Repository files applied-and-reverted:* **none.** This session's probes were DDL-only;
  no source file was mutated. Working tree clean at close (`git status --short` shows
  only the three documents above).
- *Database side effects:* both DDL mutations were applied **only** to the disposable
  database `beyo_manager_rereview_r3`, built from empty via the §10 from-scratch recipe
  — (i) key widening of `uix_production_cost_group_sections_active`, (ii) dropping its
  `removed_at IS NULL` clause. Each applied, exercised, and reverted individually; the
  index definition was re-read from `pg_indexes` and confirmed identical to the original,
  and the module returned to 79 passed. The database was **dropped** at close;
  `pg_database` lists only `beyo_manager`. No disposable database remains.
- *Configured development database:* never downgraded, never mutated. At head
  `90cdd23a828e` at open and at close. The only operations against it were the two
  read-only full-suite runs.
- *Tool-recorded state:* archgraph read-only, delta zero (above).
- *Scratch:* suite output captured under the session scratchpad only; nothing written
  into the repository outside the three documents listed.
