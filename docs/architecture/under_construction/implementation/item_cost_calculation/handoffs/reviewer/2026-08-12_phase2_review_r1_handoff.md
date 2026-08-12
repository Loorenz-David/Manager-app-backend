---
plan: phase 2 (schema, models & migration)
role: review
round: 1
date: 2026-08-12
state: REVIEWED
verdict: CHANGES_REQUESTED
actor: Claude (plan-reviewer)
---

# Phase 2 reviewer handoff — round 1 (first review, full checklist)

**Verdict: CHANGES_REQUESTED.**

The schema shipped in `8b3f9f7` is **correct**. I re-derived it rather than inheriting
it: the DDL on the migrated database matches master plan §6.2 exactly in both
directions, `compare_metadata` with `compare_type=True` reports **zero** diffs between
the ORM models and the migrated schema across all nine tables, the migration's
`downgrade → upgrade` round-trip preserves the three reused enum types with unchanged
oids, and both C5 mutations bite when re-run independently. The suite is 1628 / 23 / 1
with a failure set byte-identical to the phase-1 baseline — zero regressions.

The **tests do not hold that schema**. Four blocking findings, every one
mutation-proven, and three of them are the same species of defect: a test that survives
the exact failure it exists to catch. The declared gap (C2's mutations not run) turned
out to understate the position — the entire C2 row set is absent, not merely unmutated.
None of this is a schema fix; it is a test-coverage cycle against a correct schema.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — Who owns the from-scratch migration stall, and when?

**Question:** Root-cause the migration-chain stall now as its own maintenance item, or
defer it to phase 9's drift batch?

**Story:** Today a brand-new database cannot be built. `alembic upgrade` on an empty
database hangs at the very first statement and never returns — so a new developer
joining, a CI job that builds a clean database, or a restore into a fresh environment
all stop dead. Your existing database is fine and every phase of this project keeps
working, because they all migrate forward from a database that already exists. The
defect is invisible right up to the day someone needs a clean one, and that day is
usually a bad day to discover it.

**Branches:**
- *Own it now (separate maintenance item):* costs a session soon; clean-build works again
  before the schema grows another seven phases of revisions.
- *Defer to phase 9:* costs nothing today; the project ships on the assumption that
  nobody needs a fresh database for several weeks.

**Recommendation:** own it now as a separate maintenance item — it is unrelated to this
project, it blocks disaster recovery and any future CI database step, and it gets harder
to bisect with every revision added on top.

**On silence:** the gate holds on nothing — phase 2 proceeds either way; the item stays
recorded in master plan §10 and unfiled, which is the state that lets it evaporate.

**Trace:** master plan §10 (disposable-database recipe caveat); §8 reporter discipline;
phase 9 plan; maintenance ledger `open/` (currently empty).

## Findings by severity

Full technical entries — including proofs, violated authorities and verbatim correction
clauses — are in `plans/phase_2_schema_models.md`, Review log, entry
"2026-08-12 — reviewer r1". Summary:

| id | sev | finding |
|---|---|---|
| **B1** | blocking | C2 entirely unimplemented — 0 of 22 rows. No partial-unique conflict test exists anywhere. Stripping one clause from each of the three multi-clause index predicates leaves **23 passed**. |
| **B2** | blocking | C1(b)'s downgrade static proxy never reads `downgrade`; it survives all three defects it names, including the literal M-b (`_task_state_enum.drop()` added to `downgrade` → still green). |
| **B3** | blocking | The five `test_basis_positive_boundaries` rows pass on `uix_production_cost_basis_versions_open`, not on their CHECKs. Deleting all five `ck_pcbv_*` CHECKs leaves **5 passed**. A1 and A2 have no live test. |
| **B4** | blocking | 9 of the 16 registered CHECKs have no behavioral test (dropping all nine reddens only the existence assertion); the enumerated accept-rows and both `_effective_window` chains' 8 rows are absent. |
| **S1** | should-fix | `item_cost_evaluations.currency` — an unregistered **fourth** currency column — silently reuses `item_valuation_currency_enum`. §6.3 registers three types for "3 columns". The new README's "The three currency columns own their per-table PostgreSQL enum types" is now false. |
| **S2** | should-fix | C1(a)'s "the five new PG enum types exist" is asserted nowhere — no test queries `pg_type`. |
| **S3** | should-fix | `test_item_valuation_requires_an_amount_and_accepts_each_single_amount` never inserts a cost-only row (P-G(b)). |
| **N1–N7** | note | C5 oid evidence unrecorded (verified by me, now recorded); `percent_value` bound not pinned to the column; `EconomicsStatusEnum` declaration order ≠ §11A.4 evaluation order; `checkfirst=True` on new-type creation; prefix-map row ordering; the stall recorded-not-filed (card 1); archgraph delta verified. |

**Routing note for the fix prompt (B1).** The tests run against the **migrated**
database, so mutating `postgresql_where` in an ORM model does **not** change the index
the test meets. C2's per-clause mutations must be applied in the migration (or as direct
DDL) against a **disposable** database. A model-side mutation reported green is a false
negative — this is why P-G(a)'s mutation site needs to be named, not just its target.

## Probe results

### P2-1 — C2 multi-clause predicate mutations: **cannot bite; the rows do not exist**
The probe as specified presupposes (b) rows to redden. There are none. I ran the
mutation anyway as an existence proof: on a disposable database, one clause stripped
from each of `uix_production_cost_basis_versions_open` (lost `effective_to IS NULL`),
`uix_item_cost_evaluations_current` (lost `kind = 'committed'`) and
`uix_item_valuations_current` (lost `superseded_at IS NULL`), index names preserved so
the inventory assertion stayed satisfied → **23 passed**. → **B1**.

### P2-2 — closed-list conformance: **exact, both directions**
Against `pg_constraint` / `pg_indexes` on the migrated dev DB: 16 CHECKs, set-equal to
§6.2's closed list (nothing missing, nothing extra); the nine `uix_`/`uq_` names present
with predicates matching §4/§4A clause for clause; the three named `use_alter` FKs
present. No truncation — longest stored name 57 bytes. The in-suite inventory test
asserts the CHECK list in **both** directions, which is stronger than C1(a) required.
Additionally: `compare_metadata(compare_type=True)` → **0 diffs** on all nine tables.

### P2-3 — enum ownership: **verified independently; both mutations bite**
Reused-type oids before / after the full `downgrade → upgrade`:
`business_task_type_enum` 175330 → 175330, `task_return_source_enum` 175954 → 175954,
`task_state_enum` 175962 → 175962 — unchanged, and `tasks.{state,task_type,
return_source}` remain bound to them. `downgrade` drops exactly the five new types and
all nine tables. **M-a** (`create_type=True` on `business_task_type_enum`) →
`asyncpg.exceptions.DuplicateObjectError: type "business_task_type_enum" already
exists`. **M-b** (`_task_state_enum.drop()` in `downgrade`) →
`DependentObjectsStillExistError: column state of table tasks depends on type
task_state_enum`. C5 holds on the decidable site. C1(b)'s *static proxy*, however, is a
separate matter — see B2.

### P2-4 — lifecycle workaround: **adequate; stall genuinely pre-existing**
A from-scratch `alembic upgrade` on an empty database stalls at
`CREATE TABLE alembic_version` (`pg_stat_activity`: `idle in transaction` /
`Client:ClientRead`, zero tables created) when targeting **`7758ea23764e`** — this
revision's own `down_revision`, which predates the phase entirely. The stall is
therefore not attributable to `90cdd23a828e`. The clone-and-round-trip substitute is
sound: exercising one revision's `downgrade → upgrade` needs only the pre-state schema,
which a schema clone supplies exactly; I reproduced C1's round-trip that way and it
passes. **Out of scope, correctly not fixed — but recorded, not filed:** master plan
§10 names two candidate destinations and the maintenance ledger's `open/` is empty. See
card 1.

### P2-5 — per-table shapes: **all correct**
`production_cost_group_sections`: `added_at/by` + `removed_at/by`, no soft-delete trio,
no `updated_*`; INV-G1's predicate is `removed_at IS NULL` alone. `item_valuations`: no
`updated_*`. `item_cost_evaluation_terms`: matches the §4.5 round-7 pin exactly —
`workspace_id` present, no `value` column, `percent_value` + `fixed_amount_minor` +
`amount_minor`, `created_at` only, no `created_by_id`, no soft delete.
`item_cost_results`: `task_state_snapshot` NOT NULL of PG type `task_state_enum`,
`task_closed_at` nullable, `calculation_version` present, no `updated_at` / `is_deleted`.
Deliberate absences all absent: no CHECK on `production_budget_minor`,
`allowed_worker_minutes` or `task_state_snapshot`; no `percent_value` upper bound.

### P2-6 — archgraph delta: 15 items, **all anchors exact**
Method per the archgraph-discrepancies anti-pattern rule: each model file was read and
characterised before its stored claim was opened. All nine node evidence spans are
precisely `class` first line → EOF of the cited file. All six edge spans contain their
FK declaration. **No adjudication performed** — recommendations only.

| # | item | claim | anchor | recommendation |
|---|---|---|---|---|
| 1 | `node:table-production-cost-group` | claim **imprecise** — "preserves one current name per workspace" reads as *one group* per workspace; the index is `(workspace_id, name)` unique among non-deleted, i.e. many groups, distinct names | exact (`production_cost_group.py:10–24`) | **edit** — reword to "name unique per workspace among non-deleted rows" |
| 2 | `node:table-production-cost-group-section` | exact — interval membership, no soft-delete state, one active group per section | exact (`:10–22`) | promote |
| 3 | `node:table-production-cost-basis-version` | exact — effective-dated basis, positive facts, open-version index. (Nit: the persisted rate is derived-persisted, not a "snapshot input"; it is the value the evaluation snapshots. Not worth an edit.) | exact (`:14–43`) | promote |
| 4 | `node:table-cost-model-version` | exact — effective-dated, owns currency (A4) and its terms, one open version per workspace | exact (`:14–33`) | promote |
| 5 | `node:table-cost-model-term` | exact — immutable rule (A6), one valid typed shape per calculation type, name + purchase-cost uniqueness (A5) | exact (`:14–38`) | promote |
| 6 | `node:table-item-cost-evaluation` | exact — projection/committed, frozen snapshots for HC-7 reproducibility, current-committed index + self references | exact (`:16–56`) | promote |
| 7 | `node:table-item-cost-evaluation-term` | exact — immutable applied-term snapshot, reachable only via its evaluation | exact (`:14–25`) | promote |
| 8 | `node:table-item-cost-result` | exact — recomputable per episode, one result per task, linked to evaluation and triggering task state | exact (`:14–36`) | promote |
| 9 | `node:table-item-valuation` | exact — immutable price/cost history, required currency, ≥1 amount, supersession chain, current-row index | exact (`:14–36`) | promote |
| 10 | `edge:table-task--owns-->table-item-cost-evaluation` | exact — `item_cost_evaluations.task_id` FK RESTRICT. Contradiction is a **false positive** (see below) | contains the FK (`:20–55`, broad) | promote |
| 11 | `edge:table-task--owns-->table-item-cost-result` | exact — `item_cost_results.task_id` FK RESTRICT. Contradiction false positive | contains the FK (`:18–35`) | promote |
| 12 | `edge:table-production-cost-group--owns-->table-production-cost-group-section` | exact. Contradiction false positive | contains the FK (`:14–22`) | promote |
| 13 | `edge:table-production-cost-group--owns-->table-production-cost-basis-version` | exact. Contradiction false positive | contains the FK (`:18–42`) | promote |
| 14 | `edge:table-cost-model-version--owns-->table-cost-model-term` | exact | contains the FK (`:18–37`) | promote |
| 15 | `edge:table-item-cost-evaluation--owns-->table-item-cost-evaluation-term` | exact | contains the FK (`:18–25`) | promote |

**On the four `conflicting-canonical-relationship` contradictions:** they are artifacts
of the engine's heuristic that a source node has one canonical `owns` target. `tasks`
genuinely owns `task_steps`, `item_cost_evaluations` *and* `item_cost_results`;
`production_cost_groups` genuinely owns both its sections and its basis versions. The
code says so; the contradictions should not block promotion.

**Edge count reconciled.** The handoff's "6 ownership edges" is correct — the graph
holds exactly 6 pending edges, all stamped `2026-08-12T10:54:05.436Z` (one batch),
alongside the 9 nodes = the 15 pending items. The coordinator's observed "+4 net" is a
net-count artifact of the owner's concurrent backlog adjudication (243 → 15) running in
the same window; nothing is missing from the delta.

**One coverage gap, not a defect in the delta:** `table-item-valuation` carries no
ownership edge from the item, because **no `table-item` node exists** in the graph
(`table-item-issue` and `table-task-item` do). Worth noting for a later mapping pass;
nothing for this phase to fix.

## Scope-fence verification

Confirmed: no existing table's model changed; no command, query, router or calculator;
the three reused PG enum types are neither created nor dropped by the migration
(hand-fixed to `create_type=False`, verified on the live DB by oid); the configured dev
database is at head `90cdd23a828e` and was never downgraded. The checkpoint's perimeter
is exactly the implementer's declared file list plus the coordinator's tracker line.

## Lessons for the plans

1. **Name the mutation's *site*, not only its target — for DDL too.** P-G(a) says
   "dropping any single clause from an index's `postgresql_where`" without saying where.
   In a repo with no test-schema harness, the model and the database disagree about what
   an index is, and the model-side mutation is inert against tests that run on the
   migrated schema. This is charter rule 11's "definition-vs-call-site" clause
   generalised to schema: **the plan should state that DDL mutations are applied in the
   migration or by direct DDL on a disposable database.** Fold into §9 (P-G(a)) and into
   any future phase whose criteria mutate schema objects.
2. **A "static proxy" criterion must name what the test parses.** C1(b) said the test
   should assert what `downgrade` drops; it was satisfiable — and was satisfied — by a
   test that only reads module constants. When a criterion substitutes a static check for
   a runtime one, it should name the *source* being inspected
   (`inspect.getsource(downgrade)`) and carry its own named mutation. Fold into §9.
3. **Charter rule 2's companion needs to reach fixture *helpers*, not just rows.** B3's
   five rows were written correctly; the defect entered through `_foundation()`, a shared
   helper that leaves an open basis version behind. A criterion that says "each row's
   fixture makes its own predicate the only reason" should add: *and shared fixtures are
   audited for constraints they pre-satisfy or pre-violate.* Fold into §9.
4. **A registry that enumerates by count invites silent invention.** §6.3's "currencies
   (3 columns)" was wrong — there are four currency columns — and the implementer closed
   the gap without routing it. Registries should list the *columns*, not a count, so a
   missing row is visible as a missing row. Fold into §6.3's format.
5. **An implementer's declared gap is a floor, not a measurement.** The handoff declared
   "C2's mutations were not run"; the reality was that C2 had no rows. A declared gap
   should state what *was* built for the criterion, not only what was skipped — otherwise
   the coordinator sizes the next cycle from an optimistic reading. Fold into the
   executor's closing protocol.

## Carry-forward dispositions

| item | destination |
|---|---|
| N2 (`percent_value` bound not pinned to the column) | next touch of `test_item_economics_schema.py` — fix cycle r2 if cheap |
| N3 (`EconomicsStatusEnum` declaration order ≠ §11A.4 evaluation order) | **phase 4** (ordered classifier) |
| N4 (`checkfirst=True` on new-type creation) | phase 9 drift batch |
| N5 (prefix-map row ordering) | phase 9 drift batch |
| N6 (stall recorded-not-filed) | owner card 1; if deferred → phase 9 drift batch, as a named row |
| P2-6 15 graph items (14 promote / 1 edit) | coordinator, after phase 2 is APPROVED, per §8 standing authorization |
| `table-item` node absent from the graph | later mapping pass — not this project |

## Full write perimeter

- **Documents:** `plans/phase_2_schema_models.md` (Review log — appended only);
  `master_plan.md` (phase-2 tracker row — state and Note appended, prior actors' stamps
  preserved); this handoff.
- **Code:** none. No production file, test file or migration was modified in the main
  working tree — verified clean at close.
- **Tool-recorded state:** none. `archgraph_status` and read-only review queries only;
  **no `apply_changes`, no adjudication**. Graph unchanged at revision
  `9476e89a…`, 125 nodes / 161 edges, 15 pending.
- **Mutation probes:** disposable git worktree at `8b3f9f7`
  (`scratchpad/probe-wt`, removed at close) and disposable database
  `beyo_manager_disposable` (cloned from a `pg_dump --schema-only` of the dev schema,
  dropped at close). Files applied-and-reverted inside the worktree, each verified
  byte-identical by sha256 — migration `3fc5cd88…48d0`,
  `models/tables/item_economics/cost_model_term.py`. All DDL mutations (index
  predicates, CHECK drops and adds, column type and nullability changes) were applied
  **only** to the disposable database. Verified at close: main tree clean, configured
  development database at head `90cdd23a828e` with all 16 CHECKs intact, no
  `beyo_manager_*` database left behind.
