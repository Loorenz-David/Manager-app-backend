---
plan: phase 4B (category-driven group selection, §7C)
role: review
round: 2
verdict: APPROVED
date: 2026-08-13
actor: Claude Opus 5
---

# Phase 4B re-reviewer handoff — r2

**APPROVED.** All three review-r1 findings are closed, each verified by the
mutation that was green in r1 and now reddens. Zero new findings. The delta is
one production line (`connection.commit()`) plus two test rows, and I took it
apart from both sides: the fix does what it claims on the success path, and —
a seam the prompt did not name — it does *not* misbehave on the failure path,
where a `finally`-block commit could plausibly have published half-applied DDL.
It does not. Phase 4B is ready for its approval gate.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Card 1 from review r1 was answered (OPTION ONE) and
the authorized edit is exactly the one line that shipped.

## Review history (what this round did NOT re-verify)

Review r1's "Verified correct" list is settled ground: C1(a)–(d), C2, C3, C4,
C5, C6(a)/(d), C7, C8, the 17-row implement-r1 ledger sample, the perimeter and
hygiene of `cfec9df`. This round covered the changed seam only, plus the
bounded regression the protocol requires (full suite twice, dependents
spot-checked).

## Step 1 — perimeter (verified)

- `git show 8285cf1 --stat` = exactly `app/migrations/env.py`,
  `tests/integration/models/item_economics/test_phase4b_category_schema.py`,
  `tests/integration/services/commands/item_economics/test_phase4b_category_selection.py`,
  `master_plan.md`, `plans/phase_4b_category_selection.md`. Nothing outside the
  fix prompt's allowed files.
- `git diff 8285cf1..HEAD -- app/` **empty** — the only later commits are the
  coordinator's `5d8b6a6` (`.archgraph`) and `74ac5eb` (docs).
- `git status --porcelain` clean at session start and end.
- Production diff is one line: `connection.commit()` as the last statement of
  `_do_run_migrations()`'s `finally`.

## Step 2 — delta probes

### R2-P1 (B1 / C9) — PASS, both directions

From-scratch recipe on my own disposable `beyo_manager_4b_r2_a`, end state
asserted by **queries**, not exit code (review L5):

```
head=5caae620088c  tables=106  workspaces=0  pause_reasons=0
coldbuild=0  major_category_col=1          (1.77s)
```

Named mutation on a second disposable `beyo_manager_4b_r2_b` — the one commit
line reverted:

```
head=5caae620088c  workspaces=1  pause_reasons=7  coldbuild=1
```

The ghost returns exactly as review r1 described it. The mutant hash is
`db98e1ee8c215861f346bbc69a4b29643f997dbc6721a7a028108a44280beae5` — **byte-identical
to the `env.py` hash review r1 recorded before the fix**, which independently
proves the delta is that single line and nothing else. Restored to
`09261d91c7813483193fc93dd62e422719a956bb0694fda2af6eb586af4b4e13`. Both
databases dropped.

### Failure-path depth on the changed seam (re-reviewer-authored, not prompted)

`connection.commit()` sits in a `finally`, so it also runs when
`context.run_migrations()` raises. The obvious hazard is that it could commit
work from a migration that failed halfway. C1(b) was verified in r1 under the
*old* transaction handling, so it needed re-deriving under the new one:

- Seeded one `production_cost_groups` row on the disposable at
  `90cdd23a828e`, then `alembic upgrade head`: `RuntimeError` naming the
  `client_id` and all three dependent counts, **exit 1**, and afterwards
  `alembic_version = 90cdd23a828e`, no `major_category` column, no INV-G3
  index, seeded row intact. No partial DDL published — Alembic's per-migration
  transaction rolls back before the `finally` executes.
- Deleting the row and re-running: upgrade succeeds and persists
  (`5caae620088c`, column present).
- Downgrade still persists correctly (`5caae620088c` → `90cdd23a828e`, column
  dropped).

So C1(b) and C1(c) survive the B1 fix intact.

### R2-P2 (S1) — PASS

Both probes that left 7/7 green in review r1 now redden exactly
`test_phase4b_model_index_predicate_is_soft_delete_partial_unique`, and both
mutant hashes reproduce the ledger:

| Mutation | Mutant sha256 | Ledger | Observed |
|---|---|---|---|
| delete `postgresql_where` | `4f2076e1a7405a94f88c3515fad8370d706a53c95a6febe2c5597755eb439afa` | matches | 1 failed / 256 passed |
| flip to `is_deleted = true` | `ceb5248a80d8fa6f9a9c9a1457ce7a93cdf7854e3938e97c04e007fc47d99b52` | matches | 1 failed / 256 passed |

Restored hash **recomputed** (the ledger's S1 "Restored SHA" strings are the
recorded transcription defect — not re-filed):
`27d99ecb8b3a0e5ea5a84b4f214d60a94029308e4b2cb48d33875dea99e17b5f`, byte-identical
to the main.

The predicate now has three independent arbiters at three layers: live schema
(C1(a)), model (C1(e)), DDL site (C2(b)'s disposable mutation, settled in r1).
Changing the index *name* in the model also reddens the new row (the `next(...)`
lookup raises), so it is not silently skippable.

### R2-P3 (S2) — PASS

`test_status_shared_model_failure_is_repeated_in_each_category_block` is now a
whole-payload exact-dict assertion carrying `has_open_basis_version: True`
inside a non-evaluable wood block — precisely the cell C6(c) named. Review r1's
Probe B (`has_open_basis and evaluable`, mutant
`a09aa514df16d8536a1f5545bf526d31e560eaecd9f4b7ab96de6bfa16e68bc0`, matching
the ledger) now reddens exactly that node, where it left 256 green in r1. No
production change shipped; the query was already correct.

C6(b)'s collapse is stated in the plan's fix-r1 amendments block (line 656,
P-G): discharged by C6(a)'s exact-dict seat block plus the shared-model row's
`has_open_cost_model_version: false` pin.

### R2-P4 (N5) — PASS

`domain-item-economics`'s `configuration.py` source link now reads symbol
`resolve_economics_configuration`, span **44–82**. Re-read in code: `:44` is
`def resolve_economics_configuration(`, `:82` is `return EconomicsStatusEnum.OK`
and the file is 82 lines — exact on both boundaries. `contentHash` unchanged
(`e41ab910…`), so no code drift sits under the link. Graph revision
`5c60534df7a47584ed22a845b091b3ae1f2ce377c2a5380d16bb795ebfb3f9ff`,
148 nodes / 188 edges, 0 diagnostics, 0 stale, **2 pending** (the N7
cost-model-term edges) — not adjudicated by me, zero graph delta of my own.

### §10 history correction — verified

The corrected paragraph names the mechanism, marks the maintenance-r2 claim as
never true as stated, records review L5 ("environment facts recorded from a
command's exit code need a state assertion behind them"), carries fix-r1's
verified end-state, and lists N6 as a named open defect for the
migration-infrastructure owner. Accurate against what I reproduced in r1.

## Suite, arithmetic, hygiene

- Full non-e2e, **twice**: 1927 passed / 23 failed / 1 deselected. Failure sets
  byte-identical to each other **and** to the phase-1 baseline list. Zero
  connection-refused / `OperationalError` noise, so both runs are valid evidence
  per §10.
- Arithmetic reconciles: 1926 → 1927 = C1(e)'s single new row. The handoff's
  7-file selector: **200 passed twice**. Review r1's broader 9-file selector
  (adds `test_configuration.py` and the router test): 256 → **257**, same +1.
- Ruff clean on the three changed `.py` files.
- Dev DB at head `5caae620088c`.

## Note (housekeeping — no action owed by the implementer)

The 4B tracker row's closing clause read "graph N5 anchor correction pending
authorization". N5 was in fact completed by the coordinator at `5d8b6a6`
(revision `5c60534d…`) *before* the fix session — which the fix handoff states
correctly, so this was a tracker-prose slip only. Corrected in the same stamp
as this verdict.

## Carry-forward dispositions (unchanged from r1, none blocking)

| Item | Destination |
|---|---|
| N1 — `CONFIGURATION_FAILURE_PRECEDENCE` is a positional branch→identity map, not an independent precedence declaration | whoever next touches that tuple |
| N3 — status query's redundant deleted-basis clause (correct; defence in depth) | phase 8 status rework |
| N4 — `status.value == "ok"` → `status is EconomicsStatusEnum.OK` | phase 8 status rework |
| N6 — partial-target cold build crashes in cleanup (`UndefinedTableError: pause_reasons`), pre-existing | migration-infrastructure owner |

## Full write perimeter

- `plans/phase_4b_category_selection.md` — re-review r2 entry appended to the
  Review log; frontmatter `state` IMPLEMENTED → **APPROVED**.
- `master_plan.md` — tracker row 4B: state → **APPROVED**, actor extended,
  verdict note appended, and the stale N5 clause corrected (stamps preserved).
- `handoffs/reviewer/2026-08-13_phase4b_rereview_r2_handoff.md` — this file.
- No production, migration or test file left modified (`git diff -- app/`
  empty). No architecture-graph mutation (reads only: `archgraph_status`,
  `archgraph_get_node`).

## Mutation-probe declaration

Every probe applied, executed, reverted with `git checkout`; each restored
sha256 byte-identical to its pre-probe value.

| File | Probe | Observed | Mutant sha256 | Restored sha256 |
|---|---|---|---|---|
| `app/migrations/env.py` | revert the `connection.commit()` line; cold build on `beyo_manager_4b_r2_b` | ghost returns: workspaces 1 / pause_reasons 7 / coldbuild 1 | `db98e1ee8c215861f346bbc69a4b29643f997dbc6721a7a028108a44280beae5` | `09261d91c7813483193fc93dd62e422719a956bb0694fda2af6eb586af4b4e13` |
| `…/models/tables/item_economics/production_cost_group.py` | S1(i) delete `postgresql_where` | `…::test_phase4b_model_index_predicate_is_soft_delete_partial_unique` | `4f2076e1a7405a94f88c3515fad8370d706a53c95a6febe2c5597755eb439afa` | `27d99ecb8b3a0e5ea5a84b4f214d60a94029308e4b2cb48d33875dea99e17b5f` |
| same | S1(ii) flip predicate to `is_deleted = true` | same node | `ceb5248a80d8fa6f9a9c9a1457ce7a93cdf7854e3938e97c04e007fc47d99b52` | same as above |
| `…/queries/…/get_economics_configuration_status.py` | S2 collapse to `has_open_basis and evaluable` | `…::test_status_shared_model_failure_is_repeated_in_each_category_block` | `a09aa514df16d8536a1f5545bf526d31e560eaecd9f4b7ab96de6bfa16e68bc0` | `ce43ca5f132667b3bba598d8b97aa3bd4f51bc60f6ae7a5e9c38e1cd65144a62` |

## Database and state side effects

- **Configured `beyo_manager`** — left exactly as found: head `5caae620088c`;
  economics residue zero before the first full run and after the second, same
  scope as review r1's record (`production_cost_groups`,
  `production_cost_group_sections`, `production_cost_basis_versions`,
  `item_cost_evaluations`, `cost_model_versions`, `cost_model_terms`, plus
  `audit_logs` rows matching `production_cost%` / `cost_model%` /
  `item_cost%`; the wider suite's known non-economics residue is out of this
  scope per §10).
- **Disposable databases** — `beyo_manager_4b_r2_a`, `beyo_manager_4b_r2_b`,
  `beyo_manager_4b_r2_sanity`; **all dropped**
  (`SELECT count(*) FROM pg_database WHERE datname LIKE 'beyo_manager_4b%'`
  returns 0).
- **Operator incident, disclosed and repaired.** One malformed re-reviewer
  command lost its `DATABASE_URL` database name, so a cold build landed in the
  PostgreSQL **maintenance database** `postgres` (106 tables + enum types).
  Repaired the same minute with `DROP SCHEMA public CASCADE; CREATE SCHEMA
  public;` plus the standard grants; verified afterwards at 0 tables, 0 public
  types, owner `postgres`, and a `scripts.create_db` create/drop cycle proves
  the maintenance database still functions. Nothing else was touched, and no
  finding in this handoff rests on that run. Incidental corroboration only: it
  ended with `workspaces=0 / pause_reasons=0 / coldbuild=0`, the same C9 end
  state R2-P1 asserts on a properly named disposable.
- **Architecture graph** — read-only; revision unchanged at `5c60534d…`.

## Next session

Phase 4B closeout: archive the 4B prompts and handoffs to `archive/plan_4b/`,
commit the approval gate, and compile the phase-5 prompt (the §7C classifier,
the N-d 37-NULL-category-item note, and the forward-notes block in
`plans/phase_5_valuation_surface.md`). The two pending N7 graph items remain
for the owner; `.archgraph` needs no 4B delta — the six source links and the N5
correction are already recorded.
