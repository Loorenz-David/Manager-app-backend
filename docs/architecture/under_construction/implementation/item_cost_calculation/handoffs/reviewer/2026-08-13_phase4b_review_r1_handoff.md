---
plan: phase 4B (category-driven group selection, §7C)
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-13
actor: Claude Opus 5
---

# Phase 4B reviewer handoff — r1

Phase 4B's category contract is, on the evidence, **built correctly**: the
migration, the INV-G3 index, both command paths, the §7C.2 classifier, the
§7C.3 status shape and the HTTP surfaces all re-derived green, and every named
mutation I re-ran bit exactly where the plan said it would. The phase is held
by **one blocking finding that lives entirely in the declared `env.py` scope
exception**: the rollback OD-1 retained is genuinely required for the migration
to persist (P4B-0a reproduced), but it also broke the cold-build cleanup that
§10 verified (P4B-0b failed) — a freshly built database now ships a synthetic
workspace and seven pause reasons. Two should-fix coverage gaps accompany it.

## ⚠ OWNER DECISIONS REQUIRED (1)

**1. A second edit to `app/migrations/env.py`.**

**Question** — Authorize 4B's fix cycle to make one more edit to
`app/migrations/env.py`, or route the whole migration transaction-boundary
repair to the migration-infrastructure owner?

**Story** — You stand up a database for a new workshop. The build reports
success, but the fresh database already holds a workspace called "Migration
workspace" and seven pause reasons under it — "Lunch break", "Coffee break",
"Meeting", "Waiting for upholstery". Your first admin opens the app and sees
two workspaces on day one, with nothing to say which is real. Every future
fresh build ships the same ghost, and nobody notices until someone clocks a
pause against it.

**Branches**
- Authorize the second edit — 4B's fix cycle adds one commit call plus a
  from-scratch criterion; the gate closes inside this phase.
- Route it out — 4B stays CHANGES_REQUESTED until the infrastructure owner
  lands the repair, and phase 5 waits behind it.

**Recommendation** — Authorize the second edit: the defect is one line away
from the line you already agreed to retain, and splitting it leaves the ghost
live in the interval.

**On silence** — The gate holds at CHANGES_REQUESTED; nothing is edited.

**Trace** — master plan §10 (from-scratch recipe), OD-1, finding B1,
`app/migrations/env.py:163-179`.

## OD-1 probe outcomes (stated explicitly)

**P4B-0a — REPRODUCED.** On a disposable database at `90cdd23a828e`, with the
four `env.py` lines reverted, `alembic upgrade head` logs
`Running upgrade 90cdd23a828e -> 5caae620088c`, exits **0**, and persists
**neither** the revision (`alembic_version` remains `90cdd23a828e`) **nor** the
DDL (`major_category` absent from `information_schema.columns`). The
implementer's rationale is correct and RETAIN is the right call for the
migration path.

Mechanism, and the answer to "what changed": `_cold_build_workspace_callbacks`
runs its preflight `SELECT`, which autobegins a SQLAlchemy transaction.
`context.configure()` therefore constructs a `MigrationContext` with
`_in_external_transaction = True`, and from that point **every**
`begin_transaction()` — outer and per-migration — returns `nullcontext()`;
Alembic assumes the caller owns the transaction and never commits, while
`_run_async_migrations`'s `async with connectable.connect()` closes (rolls
back) at the end. The maintenance session's from-scratch runs were not
protected by anything in `env.py` — they survived because two historical
revisions (`6787eabf4c32`, `7a3e91c4b2d8`) issue a raw `op.execute("COMMIT")`
to build indexes `CONCURRENTLY`, which commits the accumulated work out from
under Alembic. Confirmed directly: adding one `op.execute("COMMIT")` to
`5caae620088c` made the identical warm upgrade persist. A single-step warm
upgrade never reaches those revisions, which is why 4B was the first migration
to expose the defect.

**P4B-0b — FAILED.** See B1 below. With the rollback in place, §10's
from-scratch recipe (empty disposable DB → `5caae620088c`) reaches head with
the correct schema, but ends with `workspaces = 1` and `pause_reasons = 7`.

## Verdict

**CHANGES_REQUESTED** — 1 blocking, 2 should-fix, 6 notes.

### Blocking

**B1 — the retained `env.py` rollback leaves cold-build residue in every
freshly built database.**
Observed: `beyo_manager_4b_p0b`, empty → `5caae620088c` via §10's recipe →
`alembic_version = 5caae620088c`, 106 tables, `major_category` present and
NOT NULL — and `workspaces = 1` (`mig_cold_build_workspace`, "Migration
workspace") with 7 `pause_reasons` rows owned by it. With the four lines
reverted, the same cold build ends at `workspaces = 0`, `pause_reasons = 0`.
Cause: `cleanup_cold_build_workspace()` runs in the `finally` block *after* the
per-migration transactions have committed; its two `DELETE`s autobegin a fresh
implicit transaction that nothing ever commits, so they are discarded at
connection close. Before the change nothing persisted at all, so cleanup was
vacuously satisfied — which is why this was invisible until the rollback made
migrations real.
Authority: master plan §10 ("During a genuinely cold build it creates a
transient migration workspace ... then deletes that workspace and its
anchor-owned rows before the command returns"); charter rule 7.
Correction: commit the cleanup — `connection.commit()` as the last statement of
the `finally`, or wrap the two `DELETE`s in `with connection.begin():` — and
add a criterion that re-runs §10's from-scratch recipe asserting zero
`workspaces`, zero `pause_reasons` and zero `mig_cold_build_workspace` rows.
§10's verified-2026-08-12 paragraph should be corrected in the same cycle: its
"verified twice" claim describes a run that persisted nothing.

### Should-fix

**S1 — C1(a)'s `compare_metadata` clause is blind to partial-index predicate
drift.** Deleting `postgresql_where=text("is_deleted = false")` from
`ProductionCostGroup.__table_args__`, and separately flipping it to
`is_deleted = true`, each leave all 7 rows of `test_phase4b_category_schema.py`
green — the `compare_metadata(compare_type=True)` row included. Removing the
whole `Index(...)` *is* caught. So task 2's parenthetical ("mirroring the
migration exactly — autogenerate-drift is caught by C1's `compare_metadata`
row") is false for the predicate clause, which is precisely what INV-G3's
soft-delete escape hatch rests on. No live defect: the migration owns the live
schema and it is correct. Authority: task 2 + C1(a); P-J.
Correction: a model-side structural row asserting the named index in
`ProductionCostGroup.__table__.indexes` carries
`dialect_options["postgresql"]["where"]` equal to `is_deleted = false`, with
the named mutation "changing the model predicate must redden this row".

**S2 — C6(c) has no arbiter.** Rewriting the payload cell to
`"has_open_basis_version": has_open_basis and evaluable` leaves the entire
256-test focused suite green. C6(c) names `has_open_basis_version: true` inside
a block with `evaluable: false, first_failure:
not_configured_no_cost_model_version`;
`test_status_shared_model_failure_is_repeated_in_each_category_block` asserts
only the two `first_failure`s and `has_open_cost_model_version`, and is not an
exact-dict-equality row as C6's preamble mandates. Authority: C6 preamble +
C6(c).
Correction: make that test an exact-dict-equality assertion over the whole
payload, as C6(a)/(d) already are. C6(b)'s content is in fact discharged —
C6(a)'s exact-dict seat block is the "nothing configured" block shape and the
shared-model row pins `has_open_cost_model_version: false` — but the collapse
should be stated explicitly per P-G rather than left implicit.

### Notes

- **N1 — M2 declared 1 reddened node, 7 observed.** The precedence-demotion
  mutant (SHA `22cc4294…`, reproduced exactly) reddens V1, V2, V2b, P1,
  `test_configuration.py`'s classifier row,
  `test_configuration_commands_canonicalize_chain_and_status` and
  `test_c8_status_query_enumerates_each_first_failure_and_success` — not "P1
  and no value row" as C5's M2 predicted. Cause:
  `resolve_economics_configuration` returns
  `CONFIGURATION_FAILURE_PRECEDENCE[i]` positionally, making the tuple a
  branch→identity map rather than an independent precedence declaration, so
  permuting it changes returned identities, not order. No live defect —
  P1/P3/P4 still arbitrate the order, and M3 (re-run across all 256 focused
  tests, not the 13 declared) confirms enum declaration order is irrelevant.
  P-I's per-row declaration is under-stated and C5's M2 wording is
  unsatisfiable by this construction.
- **N2 — the 63-char mutant SHA is a transcription error, not a different
  mutation.** Recomputed: original
  `8ad093a30d7f564c89221d888f2b66fb143572c7686ead57e85f0577e9ae9aee` (exact
  match); mutant
  `56a99ea50ab28480700e1dcde252b88f1f68044335df283e058e60ea5bee123c`. The
  ledger transposes `ea`→`ae` near offset 54 and drops the trailing `c`. The
  mutation reproduces and reddens the declared node.
- **N3 — the reported vacuous mutation is correctly reported; no criterion row
  is owed.** Verified at the loader: the status query selects basis versions
  with `is_deleted.is_(False)`, so the comprehension's `and not
  version.is_deleted` is redundant; removing it leaves 256 green. Two
  independent sufficient causes, both correct — defence in depth, not a gap.
  C6(d)'s per-category-scope mutation covers the clause it was written for.
  Carry forward to phase 8's status rework.
- **N4** — `evaluable = status.value == "ok"` compares a string literal rather
  than `status is EconomicsStatusEnum.OK`. Correct today; brittle to any
  enum-value edit.
- **N5** — archgraph span imprecision: the `domain-item-economics` link is
  labelled `symbol: resolve_economics_configuration` but spans
  `configuration.py:12-82` (the precedence tuple, `resolve_major_category`,
  `is_applicable` and the function). The second spot-check
  (`5caae620088c…py:25-58`, `upgrade`) is exact. Nothing in the graph
  contradicts the code, so no `archgraph-discrepancies` filing.
- **N6 (passing glance, pre-existing, outside 4B)** — a cold build targeting a
  revision below the pause-reason migrations crashes in cleanup:
  `alembic upgrade a1312183fdfb` on an empty database raises
  `UndefinedTableError: relation "pause_reasons" does not exist` from
  `cleanup_cold_build_workspace()` (the anchor is created at `a1312183fdfb`,
  `pause_reasons` arrives later). Route to the migration-infrastructure owner
  together with B1.

## Verified correct (settled ground for the re-review)

- **C1(a)** — dev DB at head: `major_category` NOT NULL, `atttypid` resolving
  to `item_major_category_enum`, exactly one `pg_type` row of that name, the
  index unique on `(workspace_id, major_category)` with predicate
  `(is_deleted = false)`, filtered `compare_metadata` clean (subject to S1).
- **C1(b)** — reviewer-run disposable seeded-row refusal: two seeded groups
  (one soft-deleted) → `RuntimeError` naming both `client_id`s and all three
  dependent counts, `alembic` exit 1, `alembic_version` unchanged, no column,
  no index; after `DELETE` the upgrade succeeds. Confirms the pre-flight counts
  deleted rows too.
- **C1(c)/(d)** — reviewer-run disposable round-trip upgrade → downgrade →
  upgrade: the column is dropped, the enum type survives at exactly one
  `pg_type` row, `create_type=False` at the migration site.
- **C2** — both DDL-site mutations re-run on disposable state; mutant SHAs
  match the ledger exactly (`0bb4461c…` widen-with-`name`, `10857fee…`
  drop-predicate), each reddening exactly its own row (plus C1(a)'s
  corresponding key/predicate assertion, correctly). Rows (c)/(d) hold.
- **C3** — pre-check rows on both commands; the `INDEX_IDENTITIES` mutation
  reproduces `3b594c36…` and reddens the parametrized identity row; the L-4
  reachability judgment is recorded in the plan's amendments (P-S — harness not
  demanded); the update command routes its flush through
  `translate_integrity_error`, so C3(d)'s collapse stands.
- **C4** — guard deletion reddens exactly (a)+(b) with (c)/(d)/(e) green;
  breadth-narrowing with `is_deleted.is_(False)` reddens exactly (b);
  the inequality drop (`dccb142c…`) reddens exactly (d); C4(a) asserts the
  leading token and both message substrings individually (P-O); the L-5
  router-level row exists and pins `major_category: None` on a name-only PATCH,
  with the command-level absent-field row in
  `test_configuration_commands_canonicalize_chain_and_status` (a rename of a
  versioned group).
- **C5** — V0–V6 + V2b + P1/P3/P4/P5 present, on unsaved ORM instances with
  explicit distinct `client_id`s and explicit `is_deleted` (L-6);
  parametrize ids name their authority rows (P-V extension); M1 reproduces
  `c193c89f…` and reddens V2+V4 as declared; M3 re-run across all 256 focused
  tests.
- **C6(a)/(d)** — true exact-dict-equality rows pinning top-level keys exactly
  `{categories, has_open_cost_model_version}`, block keys exactly the five, and
  `categories` keys exactly `{wood, seat}`; the per-category-scope mutation
  reddens (d).
- **C7** — (a) parse rows including wrong-case `"WOOD"`; (c) the body-model
  structural row with its mutation re-run; (d) lowercase coercion and explicit
  `null` acceptance. The create-response cell of C7(a) and the list row C7(b)
  are discharged through the shared serializer's update-response rows — same
  function, same field; acceptable, but not the collapse the plan wrote.
- **C8** — `audit(` in both reworked commands emits only the registered
  `production_cost_group.created` / `.updated`; no new event string appears
  anywhere in the phase's production diff; the ADMIN-retention row still bites
  over the reworked create route (removing ADMIN reddens
  `…[post-cost-groups-admin]`), confirming T8-10 restored the gate test rather
  than masking a 422.
- **Suite** — 1926 passed / 23 failed / 1 deselected on two reviewer runs;
  failure sets byte-identical to each other and to the phase-1 baseline list;
  zero connection-refused / `OperationalError` noise, so both runs are valid
  evidence per §10.
- **Ruff** — clean on all 21 changed `.py` files. (The tree-wide `ruff check`
  reports 128 pre-existing errors outside this phase's perimeter; not measured
  as a delta.)
- **Graph** — 148 nodes / 188 edges / 0 diagnostics / 0 stale / revision
  `5e4f368d…`, 2 pending (the N7 cost-model-term edges) not adjudicated.
- **Hygiene** — `git status --porcelain` clean at session start and end;
  `cfec9df` perimeter as the coordinator recorded; `a22cd25` is a docs-only
  deposit; all eleven production/migration file hashes matched the ledger's
  "Original SHA" column before any probe and after every revert.

## Lessons for the plans

1. **`compare_metadata` is not an arbiter for dialect-specific index
   predicates** (S1). L-13 named the harness precisely and it still could not
   see the clause it was invoked to protect. A criterion that delegates
   model/migration agreement to autogenerate must say *which* differences
   autogenerate can see; partial-index predicates, `server_default` expressions
   and comments are outside it. This is P-J applied to a harness rather than a
   static proxy — a new standing rule candidate.
2. **A criterion row that names several cells needs its assertion shaped to
   test all of them** (S2). C6's preamble said "exact-dict equality"; two of
   four rows shipped as partial assertions, and the cell that lost its arbiter
   was the one C6(c) existed to pin. When a criterion states an assertion
   *shape*, the implementer prompt should restate it per row.
3. **A named mutation's predicted blast radius is part of the criterion** (N1).
   C5's M2 predicted "P1 and no value row"; the shipped construction makes that
   impossible. When the observed radius contradicts the plan's prediction, the
   implementer owes the discrepancy as a finding rather than a narrowed
   declaration — extend P-I to require the declaration to state the *full*
   observed set and flag any divergence from the plan's prediction.
4. **An infrastructure workaround adopted mid-phase needs its own
   before/after property test** (B1). OD-1 was answered "retain, you verify",
   and verification was only commissioned because the coordinator wrote the
   probe by hand. A scope exception touching shared machinery should carry a
   standing requirement: name the property the machinery had before the change
   and re-assert it after.
5. **§10's environment topology carries a claim that was never true** — the
   "verified twice" from-scratch paragraph describes a run that persisted
   nothing. Environment facts recorded from a command's exit code need a state
   assertion behind them.

## Carry-forward dispositions

| Item | Destination |
|---|---|
| N3 (status query's redundant deleted-basis clause) | phase 8 — status/results rework |
| N4 (`status.value == "ok"` → `status is EconomicsStatusEnum.OK`) | phase 8, or 4B fix r1 if the query is touched anyway |
| N5 (archgraph span/symbol mismatch on `domain-item-economics`) | 4B fix r1 graph delta |
| N6 (partial-target cold build crashes in cleanup) | migration-infrastructure owner, with B1 |
| §10 correction (from-scratch paragraph) | 4B fix r1, alongside B1 |

## Full write perimeter

- `plans/phase_4b_category_selection.md` — Review log entry appended; the
  frontmatter `state` block IMPLEMENTED → CHANGES_REQUESTED.
- `master_plan.md` — tracker row 4B: state → **CHANGES_REQUESTED**, actor
  extended, one-line note appended (stamps preserved).
- `handoffs/reviewer/2026-08-13_phase4b_review_r1_handoff.md` — this file.
- No production, migration or test file was left modified. No architecture
  graph mutation of any kind (reads only: `archgraph_status`).

## Mutation-probe declaration

Every probe below was applied, executed, and reverted with `git checkout`;
each file's restored sha256 is byte-identical to its pre-probe value, which is
also the ledger's "Original SHA".

| File | Probe | Observed | Mutant sha256 | Restored sha256 |
|---|---|---|---|---|
| `app/migrations/env.py` | P4B-0a: the four retained lines removed | warm upgrade exits 0, persists neither revision nor DDL | (not recorded — deletion) | `db98e1ee8c215861f346bbc69a4b29643f997dbc6721a7a028108a44280beae5` |
| `…/5caae620088c_add_major_category….py` | `op.execute("COMMIT")` added (mechanism proof) | warm upgrade then persisted | (transient) | `312db2741d06afd6efb281deb389c7f9efae1fbd89dc71a8947d46ba5ea2f18e` |
| same migration | C2(a): index key widened with `name` (disposable DDL) | `…::test_phase4b_index_conflict_row_shares_only_workspace_and_category` + `…::test_phase4b_live_schema_reuses_enum_and_matches_model` | `0bb4461c590e7f996b384674c636809e198911dce09061e2d9d234a4c7d0049a` | same as above |
| same migration | C2(b): `WHERE is_deleted = false` dropped (disposable DDL) | `…::test_phase4b_index_predicate_allows_deleted_row` + the live-schema row | `10857fee2d5e8ddc83151849acbcc818c59a47a77cffa7b1a8b86c068c2397e0` | same as above |
| `…/update_production_cost_group.py` | C4: immutability guard block deleted | `…::test_category_flip_with_live_basis_is_immutable_and_reports_both_values`, `…::test_category_flip_remains_immutable_when_the_only_basis_is_deleted` (2 failed / 254 passed) | `aae2167ef9779cd09548182095f49178e93651295437f0b31af13c7ad5f525a6` | `8763888f77ea8af1f2c0ddce3f31773bf805aae6c50db7dbabf227b4ce1a02e0` |
| same | C4(b): basis query narrowed with `is_deleted.is_(False)` | `…::test_category_flip_remains_immutable_when_the_only_basis_is_deleted` | `649e1a971f1f70efdf2588abf8618879646158f0b24fb156ef3d089d00f24db6` | same as above |
| same | C4(d): `!= group.major_category` dropped | `…::test_equal_category_is_an_accepted_noop_for_a_versioned_group` | `dccb142c2d54a7e360489028c2d9c161598d10a0a39627df0c4e04b3283e1b9f` | same as above |
| `…/domain/item_economics/configuration.py` | M1: category filter removed from the group scan | `…test_phase4b_category_classifier.py::…[V2-wrong-category-group-…]`, `…[V4-basis-hangs-on-other-category-group-…]` | `c193c89f46af8c552dde0e19111beffdf42717ea8d12ac0d680282f96558d4ec` | `e41ab910a3935d58ebadd8531a4bdefe5764d1e80d3cea77fe0659de8d57239e` |
| same | M2: first two precedence members swapped | 7 nodes (V1, V2, V2b, P1, `test_configuration.py::…`, `…::test_configuration_commands_canonicalize_chain_and_status`, `…::test_c8_status_query_enumerates_each_first_failure_and_success`) | `22cc4294a3caca6d84263f0cb782943aba73333e9336c59fb51ca061a096b2cf` | same as above |
| `…/domain/item_economics/enums.py` | M3: `ITEM_MISSING_MAJOR_CATEGORY` moved to the end | 256 passed — precedence independent of declaration order | `889110468fb299151948135c24fbd4d2182482d5ecbad4e58a3b3af66860ccc1` | `9490d6195acb0fe58a39c985c7ce175c1e02c19ba0ac1d4897884b08f50376bd` |
| `…/commands/item_economics/_common.py` | C3(b): new `INDEX_IDENTITIES` entry removed | `…::test_integrity_translation_preserves_each_registered_index_identity[uix_production_cost_groups_major_category_active-ITEM_COST_GROUP_CATEGORY_TAKEN]` | `3b594c367b535a0b74766f9435b390b85d928a561bc9bc14316cdaa94b018b0d` | `64bb3b3970f56d9d7c41c43846b681bcb919f5f043de277ec6b0dd6ee9467263` |
| `…/queries/…/get_economics_configuration_status.py` | C6(d): per-category basis-group scope removed | `…::test_status_has_exact_per_category_shape_and_scopes_basis_to_each_group`, `…::test_configuration_commands_canonicalize_chain_and_status` | `2359e773f62604206cb44d4f5b75f80f3d2a188ccb64c70191cbef4cbdb2cda4` | `ce43ca5f132667b3bba598d8b97aa3bd4f51bc60f6ae7a5e9c38e1cd65144a62` |
| same | Probe A: reported-vacuous `and not version.is_deleted` removed | 256 passed — vacuity confirmed | (transient) | same as above |
| same | Probe B: `has_open_basis_version` collapsed to `has_open_basis and evaluable` | **256 passed — S2** | (transient) | same as above |
| `…/routers/api_v1/item_economics.py` | C7(c): `major_category` removed from `_CreateGroupBody` | `…::test_group_router_body_models_keep_category_fields_at_the_http_boundary` | `56a99ea50ab28480700e1dcde252b88f1f68044335df283e058e60ea5bee123c` | `8ad093a30d7f564c89221d888f2b66fb143572c7686ead57e85f0577e9ae9aee` |
| same | C8: ADMIN dropped from the create-group route | `…::test_every_configuration_route_retains_admin_and_manager_access[post-cost-groups-admin]` | (transient) | same as above |
| `…/models/tables/item_economics/production_cost_group.py` | Probe C: model index predicate deleted | **7 passed — S1** | (transient) | `27d99ecb8b3a0e5ea5a84b4f214d60a94029308e4b2cb48d33875dea99e17b5f` |
| same | Probe C2: model index removed entirely | `…::test_phase4b_live_schema_reuses_enum_and_matches_model` (caught) | (transient) | same as above |
| same | Probe C3: model predicate flipped to `is_deleted = true` | **7 passed — S1** | (transient) | same as above |
| same | Probe D: column type changed to `String(32)` | 5 failed (caught) | (transient) | same as above |

## Database and state side effects

- **Configured development database (`beyo_manager`)** — left exactly as found:
  at head `5caae620088c`; economics tables at zero rows before and after
  (`production_cost_groups`, `production_cost_group_sections`,
  `production_cost_basis_versions`, `item_cost_evaluations`,
  `cost_model_versions`, `cost_model_terms`) and zero `audit_logs` rows
  matching `production_cost%` / `cost_model%` / `item_cost%` — measured before
  the first full-suite run and after the second (§9 rule-11½ record: this scope
  is economics-only; the wider suite is known to commit non-economics residue
  per full run, §10).
- **Disposable databases** — `beyo_manager_4b_p0a1`, `…p0a2`, `…p0a3`,
  `…p0a4`, `…p0a5`, `…p0b` created for P4B-0a/0b, the C1 round-trip, the
  seeded-row refusal and the C2 DDL-site mutations; **all six dropped**
  (`SELECT datname FROM pg_database WHERE datname LIKE 'beyo_manager_4b%'`
  returns nothing).
- **Architecture graph** — read-only (`archgraph_status`); revision unchanged
  at `5e4f368df1e17bdbad477428f691e91ad15ece9bd9455b668ebe7bf95b4e76f0`.

## Next session

A fix cycle scoped to: **B1** (commit the cold-build cleanup + a from-scratch
criterion + the §10 correction), **S1** (model-side predicate structural row
with its named mutation), **S2** (C6(c) as an exact-dict row). B1 needs owner
card 1 answered first. N1's declaration lesson and N5's graph span can ride
along. Everything else in the "Verified correct" list is settled — the
re-review is delta-scoped to the changed seam plus a verified perimeter.
