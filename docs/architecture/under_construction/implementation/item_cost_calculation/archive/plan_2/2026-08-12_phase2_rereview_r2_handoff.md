---
plan: phase 2 (schema, models & migration)
role: review
round: 2 (re-review, delta-scoped)
verdict: CHANGES_REQUESTED
date: 2026-08-12
actor: Claude (plan-reviewer)
---

# Phase 2 re-review r2 handoff

**Verdict: CHANGES_REQUESTED — one blocking finding (B5), six notes.**

Seven of the eight r1 items are genuinely closed. B1–B4 and S1–S3 were re-derived
independently rather than inherited, and two of them were verified harder than the fix
declared: a full 16-CHECK drop sweep (every closed-list CHECK reddens a *behavioural*
row, not merely the inventory existence assertion) and a two-sided drop-simulation of
S2's `pg_type` assertions. The remaining defect is narrow: one of C2's 25 rows —
INV-G1's (a) conflict row — puts both memberships in the same production cost group
instead of the two the plan's cell specifies, so the invariant "a working section
belongs to at most one production cost group at a time" has no live arbiter. Proven by
mutation: widening the index key destroys INV-G1 and all 79 tests stay green. The fix
is one fixture change.

The schema itself remains correct and untouched by this cycle; the maintenance
commit's central claim (from-scratch `alembic upgrade head` completes) is verified.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner this round. N10 and N11 describe durable properties of the
migration-environment shim that the coordinator should file in the maintenance ledger;
neither is a decision only the owner can make.

## Step 1 — verified perimeter

| Commit | Expected | Actual | Verdict |
|---|---|---|---|
| `39e6fbe` (fix r2, Codex) | schema test module, item_economics README, phase-2 plan, master-plan tracker row | exactly those four (`README.md`, `test_item_economics_schema.py`, `master_plan.md` — tracker row only, `phase_2_schema_models.md`) | **exact** |
| `7e1b11d` (maintenance r1, Codex) | `app/migrations/env.py`, master plan §10, its handoff | exactly those three; handoff added as `handoffs/maintenance/…` at **repo root**, relocated to the project folder by the coordinator in `2985165` (R100, content-identical) | **exact** (misfiling already remediated) |

Working tree clean at close. Migration source sha256
`3fc5cd88367b8a7ba2c0dadc34a00ae878a4b586db0b913a055ca6816fda48d0` — byte-identical
before and after this session's source probes.

## Step 2 — probe results

### R2-P1 — row count and mapping: **PASS (25 confirmed, r1's prose was wrong)**

Per-index case counts in the test module map one-to-one onto the C2 table:

| Index | (a) | clause (b) rows | key (b) rows | total |
|---|---|---|---|---|
| `uix_production_cost_groups_name_active` | 1 | 1 | — | 2 |
| `uix_production_cost_group_sections_active` | 1 | 1 | — | 2 |
| `uix_production_cost_basis_versions_open` | 1 | 2 | — | 3 |
| `uix_cost_model_versions_open` | 1 | 2 | — | 3 |
| `uix_cost_model_terms_purchase_cost` | 1 | 2 | — | 3 |
| `uix_cost_model_terms_name_active` | 1 | 1 | 1 | 3 |
| `uix_item_cost_evaluations_current` | 1 | 3 | — | 4 |
| `uix_item_valuations_current` | 1 | 2 | — | 3 |
| `uq_item_cost_results_task_id` | 1 | — | 1 | 2 |
| **total** | **9** | **14** | **2** | **25** |

The 14 clause rows equal the 14 `postgresql_where` clauses counted off the live DDL
(1,1,2,2,2,1,3,2). None missing, none invented. **r1's "22 rows (9 + 13)" was the
arithmetic error** — the fixer correctly followed the table. See lesson L1.

### R2-P2 — mutations, sampled independently: **PASS**

*Index predicate clauses — 7 of 14 re-run by the reviewer at the DDL site* (drop +
recreate under the same name on a from-scratch disposable DB; the other 7 stand on the
fixer's declaration, not re-derived):

| Clause dropped from | Row expected red | Result |
|---|---|---|
| INV-B1 `effective_to IS NULL` | `basis_closed` | RED, siblings green |
| INV-B1 `is_deleted = false` | `basis_soft_deleted` | RED, siblings green |
| INV-E1 `kind = 'committed'` | `evaluations_projection` | RED, siblings green |
| INV-E1 `superseded_at IS NULL` | `evaluations_superseded` | RED, siblings green |
| INV-E1 `is_deleted = false` | `evaluations_soft_deleted` | RED, siblings green |
| INV-V1 `superseded_at IS NULL` | `valuations_superseded` | RED, siblings green |
| INV-V1 `is_deleted = false` | `valuations_soft_deleted` | RED, siblings green |

*B2 downgrade-source mutations — all three re-run and reverted:* adding
`_task_state_enum.drop(...)` to `downgrade` (the literal M-b defect) → RED; deleting
`_item_valuation_currency_enum.drop(...)` → RED; deleting
`op.drop_table('item_cost_results')` → RED. C1(b) now bites on the defect it names.

*B3 / A1 / A2 and the full CHECK sweep:* the B3 fixture closes its basis version
(`_foundation(basis_open=False)` → `effective_to = 2099-01-01`), so
`uix_production_cost_basis_versions_open` cannot be the second sufficient cause, and
every reject row asserts its constraint name via `match=`. Rather than the two required
drops, **all 16 closed-list CHECKs were dropped one at a time**; every one reddens a
behavioural test, each exactly its own named row(s):

- `ck_pcbv_fixed_monthly_cost_minor_positive` → both the −1 and 0 rows (A1 live);
- `ck_pcbv_cost_per_worker_minute_minor_positive` → the 0 row (A2 live);
- `ck_cost_model_terms_value_by_type` → all 9 reject rows of the 12-row matrix;
- the other 13 → exactly 1 behavioural row each.

Constraint count restored to 16; module green afterwards.

### R2-P3 — combined tree: **PASS**

Full non-e2e suite on HEAD (fix + maintenance): **1684 passed / 23 failed /
1 deselected**, matching the declaration. The 23-item failure set is **byte-identical**
to the phase-1 recorded baseline (sorted set-diff empty). Zero connection noise. The
transient collection error the maintenance session saw in
`test_item_economics_schema.py` is **gone** — 79 tests collect and pass.

### R2-P4 — maintenance verification: **PASS, with two notes**

- §10's from-scratch recipe: empty database → `alembic upgrade head` →
  `90cdd23a828e` in **1.52s**, 106 public tables. The stall fix's central claim holds;
  that database served the DDL probes above and was dropped at close.
- Configured dev DB at head `90cdd23a828e`, untouched; `alembic upgrade head` on it is
  a **0.49s no-op** with zero cold-build anchor rows written.
- `env.py`'s repair block: guards are conditioned on the exact legacy graph — three
  shape conditions on `8cf57fa23110.down_revision`, `a3b5c7d9e1f2.down_revision` and
  `6f4d2c1b9a7e.down_revision` — and the two cold-build hooks are gated on
  `step.up_revision_id == 'a1312183fdfb'`, so they are genuinely inert at or past head.
  **No historical migration file was rewritten (rule 7 holds)** — the commit touches
  only `env.py`.
- Broader than guarded-and-inert, filed not fixed: **N10** (a permanent workspace row
  written into every cold database) and **N11** (private-Alembic-internals mutation
  running on every invocation). Neither affects phase 2's verdict.

### R2-P5 — S1/S2/S3: **PASS**

- **S1:** the README's "four currency columns use three PostgreSQL enum types …
  `item_valuations.currency` and `item_cost_evaluations.currency` share
  `item_valuation_currency_enum`, owned by `item_valuations`" matches §6.3's ratified
  reuse row exactly (registry decision 2026-08-12).
- **S2:** both halves bite, drop-simulated on the disposable DB. Renaming
  `item_cost_evaluation_kind_enum` → the five-new-types assertion reddens. Rebinding
  `tasks.return_source` to a decoy type of the same name (so all eight names still
  exist, isolating the second assertion) → the `tasks` binding assertion reddens.
  Both reverted; test green.
- **S3:** `test_item_valuation_amount_and_currency_boundaries` covers every case its
  name claims — negative-sale, negative-purchase, both-null, price-only, **cost-only**,
  null-currency. N2 taken: the inventory pins reflected `percent_value` to
  `numeric(6,3)`.

## Findings

### B5 (blocking) — INV-G1's C2 (a) row uses one group, not two; the invariant has no live arbiter

C2's cell reads "(a) conflict → `IntegrityError`: **section active in two groups**".
`test_partial_unique_indexes_enforce_conflicts_and_exclusions[sections_conflict]`
builds both `ProductionCostGroupSection` rows against the same `group.client_id` from
`_foundation`, so the row conflicts on the duplicated
`(workspace_id, working_section_id)` pair *and* on a duplicated group — it cannot
distinguish the shipped key from a group-scoped one. This is the last of the 25 rows
still passing for a reason other than the one its cell states (r1's B3 rule, applied to
C2 rather than C3).

**Proof** (applied and reverted on a from-scratch disposable DB, index name preserved):
recreating `uix_production_cost_group_sections_active` as
`(workspace_id, production_cost_group_id, working_section_id) WHERE removed_at IS NULL`
— which permits one working section in unlimited groups simultaneously, destroying
INV-G1 — leaves the **entire phase-2 module at 79 passed**, with `sections_conflict`
and `sections_removed` both green. Restored; 79 passed.

**Violated authority:** plan C2, the `uix_production_cost_group_sections_active` (a)
cell; intention §7A.2 ("the index is the only arbiter") and §4.2; charter rule 2
companion.

**Correction clause (verbatim):** in the `sections_conflict` / `sections_removed`
branch, create a **second `ProductionCostGroup`** in the same workspace and attach the
second `ProductionCostGroupSection` to *that* group (same `working_section_id`), so the
shared key is `(workspace_id, working_section_id)` alone and the group differs —
exactly the "section active in two groups" the cell specifies. Re-run the reviewer's
named mutation (widen the index key to include `production_cost_group_id` at the DDL
site on a disposable DB) and declare that `sections_conflict` turns red. Leave
`sections_removed`'s `removed_at` clause row as it is, but move it onto the second
group too so it stays a one-clause delta from the corrected (a) row.

### Notes

- **N8** — the B2 proxy recognises only the `_<name>_enum.drop(` idiom. Probed: adding
  `op.execute('DROP TYPE task_state_enum')` to `downgrade` leaves the test **green**.
  C1(b)'s three named mutations all bite, so the criterion is met; a textual `DROP TYPE`
  scan would close the residue. → next touch of the migration / phase 9.
- **N9** — the maintenance handoff declares `Commit hash: 2875320`; the commit is
  `7e1b11d`. The perimeter had to be verified by content rather than by the declared
  hash. → coordinator, provenance hygiene.
- **N10** — `_ensure_cold_build_workspace` writes a permanent row into every cold
  database. Verified: the from-scratch DB carries
  `workspaces('mig_cold_build_workspace', 'Migration workspace', created_by_id NULL)`;
  the configured dev DB carries none. It is a data insert performed by the migration
  *environment*, not by any revision — it appears in no `alembic history`, no downgrade
  removes it, and every future staging/production database built cold inherits it.
  → maintenance ledger.
- **N11** — the graph repair mutates Alembic private internals
  (`script.revision_map._revision_map`, `revision.nextrev`, `revision._all_nextrev`)
  and, being guarded on the on-disk graph shape rather than on database state, runs on
  every alembic invocation (effectively inert at head — verified).
  `_restore_cold_build_role_enum` additionally executes
  `UPDATE workspace_roles SET name = NULL`, destructive but double-guarded (revision id
  + both role enum types absent). This is a durable compatibility shim standing in for
  the real fix — a merge/branch revision making the on-disk graph acyclic. An Alembic
  upgrade renaming those internals breaks every migration run. → maintenance ledger.
- **N12** — C2's nine (a) rows assert bare `IntegrityError` with no `match=` on the
  index name, unlike the C3 rows which now do. Every fixture is otherwise sole-cause
  (verified), so no row is currently decoration. → next touch.
- **N13** — `test_percent_boundaries_use_check_and_numeric_type[numeric-bound-reject]`
  expects `DBAPIError`, of which `IntegrityError` is a subclass, so a later
  `CHECK percent_value < 1000` would leave it green. It conforms to D12 as written, and
  N2-taken now pins the reflected precision structurally, so **r1's N2 is closed**.
  → next touch, optional.

## Carry-forward dispositions

| Item | Origin | Destination |
|---|---|---|
| N3 — `EconomicsStatusEnum` declaration order ≠ §11A.4 evaluation order | r1 | phase 4 (ordered classifier must not iterate the enum) |
| N4 — `checkfirst=True` on the five new types | r1 | phase 9 drift batch |
| N5 — `client_id_prefix_map.md` row ordering | r1 | phase 9 drift batch |
| N8 — B2 proxy regex residue | r2 | next touch of the migration / phase 9 |
| N9 — maintenance handoff commit hash wrong | r2 | coordinator (record only) |
| N10 — cold-build workspace row | r2 | maintenance ledger |
| N11 — private-internals graph shim | r2 | maintenance ledger |
| N12 — C2 (a) rows lack `match=` | r2 | next touch |
| N13 — `DBAPIError` too broad on the numeric-bound row | r2 | next touch, optional |
| N1, N2, N6, N7 | r1 | **closed** (evidenced / assertion added / stall owned and fixed / graph items held for post-approval) |

## Lessons for the plans

- **L1 — C2's prose count contradicted its own table.** "9 (a) + 13 (b) = 22" against
  the 25 rows the table enumerates and the 14 clauses in the DDL. Two sessions spent
  effort reconciling it, and r1 filed a finding using the wrong number. A criterion
  stating a count must derive it from the table, or omit the count.
- **L2 — an (a) conflict row must name the key columns it discriminates, not only the
  predicate clauses.** C2's per-clause discipline (projection D8) covered predicates
  exhaustively and left key columns to prose ("two groups") — exactly where B5 slipped
  through. Criteria for a partial-unique index should enumerate one accept row per
  *key column* as well as one per predicate clause.
- **L3 — shared `_foundation`-style fixtures are where second sufficient causes are
  born** (r1's B3, now B5). When a phase's tests hang off one factory, each criterion
  cell should state which field of the shared fixture that row varies.

## Archgraph

Read-only this session (`archgraph_status` only). Zero delta from both the fix and the
maintenance session, as expected: revision
`9476e89ab7d263e43bf8eb055ccc6d0f8186ba34c861787c4d1422c4890019e6`, **125 nodes,
161 edges, 15 pending reviews**, 0 stale nodes, 0 diagnostics, permission mode
`review`. Unchanged from r1. No promotion, rejection or edit was performed; the 14
promote / 1 edit recommendations from r1 remain held for post-approval adjudication by
the owner.

## Full write perimeter (this session)

**Documents written (3):**
- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_2_schema_models.md` — Review log entry "2026-08-12 — reviewer r2" appended (append-only; no prior entry edited).
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md` — phase-2 tracker row only: state IMPLEMENTED → **CHANGES_REQUESTED**, actor list extended with "reviewer r2 (Claude)", Note appended. Prior actor stamps preserved; no other row touched.
- `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase2_rereview_r2_handoff.md` — this file.

**Production code / tests changed: none.**

**Mutation-probe declaration.**
- *Repository files applied-and-reverted:*
  `app/migrations/versions/90cdd23a828e_item_economics_schema.py` — four source
  mutations (the three B2 defects plus one raw-SQL `DROP TYPE` variant for N8), each
  applied and reverted individually. sha256 verified byte-identical before and after:
  `3fc5cd88367b8a7ba2c0dadc34a00ae878a4b586db0b913a055ca6816fda48d0`. Working tree
  clean at close (`git status --short` empty).
- *Database side effects:* all DDL mutations were applied **only** to the disposable
  database `beyo_manager_rereview_r2`, built from empty via the §10 from-scratch
  recipe. Mutations: 7 index predicate-clause variants across
  `uix_production_cost_basis_versions_open` / `uix_item_cost_evaluations_current` /
  `uix_item_valuations_current`; 1 key-column widening of
  `uix_production_cost_group_sections_active` (B5's proof); 16 CHECK-constraint drops
  (one at a time, the full closed list); 2 enum-type renames plus 1 decoy type
  (`item_cost_evaluation_kind_enum`, `task_return_source_enum`) for the S2 probes. All
  reverted and verified restored (index definitions re-read, constraint count back to
  16, module 79 passed) before the database was **dropped** at close. No disposable
  database remains — `pg_database` lists only `beyo_manager`.
- *Configured development database:* never downgraded, never mutated. At head
  `90cdd23a828e` at open and at close; zero `mig_cold_build_workspace` rows; the only
  operations against it were the full read-only test suite and a no-op
  `alembic upgrade head`.
- *Tool-recorded state:* archgraph read-only, delta zero (see above).
- *Scratch:* probe scripts under the session scratchpad only; nothing written into the
  repository outside the three documents listed above.
