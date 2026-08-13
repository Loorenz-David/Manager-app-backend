---
plan: phase 4 (configuration services)
role: review
round: 2 (re-review, delta-scoped)
verdict: CHANGES_REQUESTED
state: REVIEWING → CHANGES_REQUESTED
date: 2026-08-13
actor: Claude
---

# Phase 4 re-review r2 handoff

**Verdict: CHANGES_REQUESTED** — 2 blocking, 4 should-fix, 6 notes.

The fix cycle did the big thing right: 7 test nodes became 126, the coverage
collapse that produced r1's B1 is substantially closed, B2's eight 500s are all
422s naming their field, and every trim landed. The perimeter is exact and the
disposable-CLONE deviation is resolved as procedural only. What holds the gate is
that three criteria families still ship rows that cannot fail: §7A.4's entire
`effective_from IS NULL` open-row column is unenumerated, four of C10's six
filter rows plus both `ITEM_COST_GROUP_NAME_TAKEN` rows have no arbiter, and C3
asserts the conflict's *class* but never its registered *identity*. All of it is
test-side; no production defect was found this round.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Every finding is implementer work inside the existing
plan criteria; the 47 graph items remain held for the coordinator's single
post-approval adjudication under §8's standing authorization.

## Step 1 — verified perimeter

- `git show 4e19506` = 5 production + 3 test files + tracker row + Review log =
  **10 files, 923 insertions**, exactly the fix prompt's allowance. `187efb9`
  carries only the handoff. `git diff 4e19506..HEAD -- app/` is **empty**; the
  working tree is clean. Nothing outside the perimeter changed.
- **Deviation (disposable local clones, not worktrees) — procedural only.** All
  six declared "main" sha256 values equal both the current working-tree files and
  the blobs as committed in `4e19506`:

| File | sha256 (worktree == `4e19506` blob == declared) |
|---|---|
| `create_production_cost_basis_version.py` | `acd64c36…dad4b5cb` |
| `_common.py` | `3b594c36…4b018b0d` |
| `requests/__init__.py` | `904b635f…f5424860` |
| `delete_production_cost_basis_version.py` | `196fa870…e50d4104c` |
| `configuration.py` | `3e4412f0…7e3d08b195` |
| `routers/api_v1/item_economics.py` | `891f9a18…ba5474b792` |

  Zero probe residue. Note it in the record; do not file it.

## Step 2 — delta probes

**R2-P1 (coverage closure).** Criterion-by-criterion against the amended C1–C11:

| Criterion | Shipped | Verdict |
|---|---|---|
| C1 (20 admission rows) | 10 cases × 2 chains | **GAP → B1.** Count matches; the *table* does not. Cases duplicate §7A.4 rows 2 and 8 and omit rows 4, 5, 6. |
| C2 (adjacency, both chains) | 3 boundaries × 2 chains through `is_applicable` on command-built ORM rows | met; theorem row → N1 |
| C3 (real two-session race) | 2 chains, genuine `_session_factory()` sessions | race met; **identity → S1** |
| C4 (rate rows) | underflow ×2 paths, canonicalize-then-derive, persisted-rate/rederive, smuggled-field | 4 of 5; **S4-forward row → S2** |
| C5 (12 cells) | 12 parametrized ids + both duplicate pre-checks + router term-route absence | met (reachability note per amended N6/L2 stands) |
| C6 (guard race) | serial ×2 chains + interleaved `reference_blocked_while_locked` | met; harness timeout → S4 |
| C7 (INV-G1 + group guards) | membership identity, in-use, clean, non-deleted-version | met |
| C8 (six via the STATUS QUERY) | all six, through `get_economics_configuration_status` | met; shape → N5 |
| C9 (router percent docs) | router body-model field metadata, case-insensitive | met |
| C10 (3 queries × 4 rows + update) | one node, all three lists | **GAP → B2** |
| C11 (per-route roles + audit) | 13 routes × {worker, seller, admin, manager} + 9 audit events | met |

**C11's harness (P-R):** `TestClient` over a `FastAPI()` app including
`item_economics.router`, with `get_db` / `get_jwt_claims` dependency overrides and
`run_service` monkeypatched to a recording double, plus `router.routes`
introspection for the surface assertions. That is a named harness and it is the
right one.

**R2-P2 (mutations, re-run).** All applied in the main worktree, reverted,
sha256-verified byte-identical afterwards.

| Mutation | Observed result |
|---|---|
| C6(b) `for_update=True → False` | reddens exactly `test_c6_interleaved_fk_insert_is_blocked_by_the_delete_row_lock_then_proceeds` (the FK insert completes, so the delete then raises `…_IN_USE`) |
| C8 swap first two precedence entries (mutated `a5de2350…` = **declared value**) | reddens `test_c8_status_query_enumerates_each_first_failure_and_success` **and** `test_configuration_classifier_uses_explicit_failure_order_and_same_basis_identity_for_gap` — one more than declared |
| C11 remove MANAGER from **all 13** allow-lists | reddens **exactly** the 13 `test_every_configuration_route_retains_admin_and_manager_access[…-manager]` ids, zero collateral — P-G's "every MANAGER row" fully satisfied (the ledger only declared the single-route version, which reddens 1) |
| B2 drop `gt=0` (mutated `22ea0125…` = **declared value**) | reddens exactly `test_basis_request_rejects_each_out_of_range_numeric_field[fixed-negative]` |
| C3 basis index → model identity (mutated `71249f1a…` = **declared value**) | reddens **only** the hand-built translation row; both real race rows stay green → **S1** |
| Plan C8 structural (B6): reverse `EconomicsStatusEnum` declaration order | **126/126 unchanged** — precedence is genuinely independent of the enum |

**R2-P3 (the races are genuine).** `db_session` is a real `get_db()` session with a
teardown rollback — not a nested-transaction wrapper — so C3/C6's
`_session_factory()` sessions and their `commit()`s are real cross-connection work;
the C6(b) lock flip is only observable that way. Neither test monkeypatches `flush`
to raise. **Teardown leaves no residue:** C3+C6 run twice consecutively → row counts
flat; two consecutive full-suite runs → flat (economics workspace id sets identical
before and after). Rule 11½ holds. C3's seam has no timeout → **S4**.

**R2-P4 (B2 totality).** All eight r1-proven 500 cases now raise `ValidationError`
→ **HTTP 422** naming the field: `_parse` converts the pydantic error to
`"<field>: <msg>"` and `ValidationError.http_status = 422`. Bounds mirror §6.2's
CHECK list exactly, in direction and strictness. R11-1's canonicalization rows are
green and independent of the bound rows (P-U's two criteria kept separate — the
before-validator quantizes, then the constraint runs, so `hours = 0.004 → 0.00` is
also rejected rather than reaching `DivisionByZero`). **Adjacent-pair rows are
absent for every bound → S3.**

**R2-P5 (production trims).** `cost_per_worker_minute_minor` is not in
`_BasisVersionBody.model_fields`, so it is gone from the published OpenAPI schema
(N4's `extra="ignore"` pin still carries the smuggling row). `_common.reference_exists`
and `get_group(..., for_update=)` are gone with no callers left behind.
`create_cost_model_version` compares enum **members** with `is`. The vestigial
`version = None` is gone. Ruff clean on every changed phase file.

**Suite.** 1875 passed / 23 failed / 1 deselected, run **twice**; failure set
byte-identical to the phase-1 baseline list (23/23, `diff` clean — N14's flaky
candidate did not fire). Focused phase set **126 passed**. Dev DB at head
(`90cdd23a828e`).

## Findings

### B1 (blocking) — §7A.4's `effective_from IS NULL` open-row column is unenumerated

C1 requires "all 10 rows × 2 chains = 20 rows … No sampling." The shipped 20 rows
are 10 parametrized cases × 2 chains, but the cases are not the table's rows: they
duplicate row 2 (`none-open-today` and `none-open-past`) and row 8
(`open-equal-rejected` and `open-before-rejected`), and **omit rows 4, 5 and 6** —
the whole "open version whose `effective_from IS NULL`" column. The only `open_from`
fixtures are `None`, a *dated* open row, and a *soft-deleted* one; no live open row
with a NULL `effective_from` is ever built, even though `_basis()`/`_model()` create
exactly that shape as the first version of a chain.

Row 5 (`NULL`-open + `≤ today` → accept, closing the predecessor at that date) is the
ordinary "second version supersedes the unbounded-past first version" path.

Verified: deleting the `open_from is not None` guard at `_common.py:52` leaves the
entire C1 matrix and C2 green (124 passed, C3 deselected). The production code is
correct; nothing tests it.

Correction: three rows per chain with a live `effective_from IS NULL` open row —
row 4 (`NULL` requested → `…_EFFECTIVE_FROM_REQUIRED`), row 5 (`≤ today` → accept,
and assert the predecessor's `effective_to == d`), row 6 (`> today` →
`…_EFFECTIVE_FROM_FUTURE`). Named mutation: **drop `open_from is not None` from the
comparison at its definition site in `_common.admission_error` — row 5 must redden.**
Authority: plan C1; intention §7A.4 rows 4–6; charter rule 2.

### B2 (blocking) — C10's rows are satisfied regardless of the behaviour they name

C10 requires, per each of the three list queries, a workspace-scoping row, an
`is_deleted` row, an ordering row and a `limit + 1` row, plus
`update_production_cost_group` happy path and `ITEM_COST_GROUP_NAME_TAKEN` on rename
collision **on both paths**. All three lists are folded into one node whose
assertions hold with or without the filters: `limit = 1` plus name/`effective_from`
ordering keeps the foreign and soft-deleted rows outside the asserted slice, and
`has_more` is already `True` for other reasons.

Verified by mutation — each of these leaves **126/126 green**:

| Mutation | Result |
|---|---|
| drop `workspace_id` from `list_production_cost_groups` | 126 passed |
| drop `is_deleted` from `list_production_cost_groups` | 126 passed |
| drop `is_deleted` from `list_cost_model_versions` | 126 passed |
| drop `workspace_id` from `list_production_cost_basis_versions` | 126 passed |
| delete the whole `ITEM_COST_GROUP_NAME_TAKEN` pre-check (`update_production_cost_group.py:24-25`) | 126 passed |

Only 2 of the 6 filter rows have an arbiter (basis `is_deleted`, model
`workspace_id` — both do redden, confirming the fixture is one tweak away from
working). Note the second-order effect of the last row: with the pre-check gone a
rename collision surfaces as `ConflictError`/409 from the index rather than
`ValidationError`/422, so the registered dual-path contract silently changes class.

Correction: per filter row, a fixture in which the filtered-out row would otherwise
land **inside** the asserted slice (sort it first, or raise `limit`), so the filter
is the sole reason the expected output holds; and two rename-collision rows
(pre-check + DB path). Authority: plan C10; charter rule 2's sole-cause companion;
P-K, P-M.

### S1 (should-fix) — C3 asserts the conflict's class, never its registered identity

`test_c3_real_concurrent_open_insert_translates_the_loser` asserts
`sum(isinstance(outcome, ConflictError)) == 1` and nothing about the message. C3
requires "the loser's exact `ConflictError` identity
(`ITEM_COST_CONCURRENT_BASIS_VERSION` / `_MODEL_VERSION`)", and the criteria header
requires identities asserted as exact leading tokens **plus** class. Verified:
mapping `uix_production_cost_basis_versions_open` to
`ITEM_COST_CONCURRENT_MODEL_VERSION` reddens only
`test_integrity_translation_preserves_each_registered_index_identity[…]` — the
hand-built `IntegrityError` proxy that C3's harness block explicitly excludes —
while both real race rows stay green. The fix's own ledger records this outcome
("the clean real two-session race passes for both chains"); it is the gap, not the
proof. Correction: assert the loser's message starts with the chain-qualified token.
Authority: plan C3; intention §7A.2's criterion.

### S2 (should-fix) — C4's S4-forward row is still absent

The criterion needs `Decimal(str(v))` proven on a value where `Decimal(v)` would
differ, **distinct from** the B1 canonicalization fixture. Both shipped fixtures
(`173.456 → 173.46`, `12.01056 → 12.011`) quantize identically under either parse,
so neither can see the defect. Verified: replacing `Decimal(str(value))` with
`Decimal(value)` at `requests/__init__.py:19` leaves **126/126 green**. Correction:
a fixture straddling the rounding boundary — e.g. `monthly_paid_hours = 2.675`, which
gives `2.68` via `Decimal(str(v))` and `2.67` via `Decimal(v)`. Authority: §6A.1;
phase-3 projection S4 forwarded into this phase; plan C4's S4-forward row.

### S3 (should-fix) — bound strictness and the accept side of every bound are unarbitrated

Each of the five bounds carries only reject rows, all inherited from r1's eight 500
cases; no bound has an adjacent-pair row. Verified: `Field(gt=0)` → `Field(ge=0)` on
`fixed_monthly_cost_minor` leaves **126/126 green** — yet under `ge=0` a
`fixed_monthly_cost_minor = 0` request is admitted, violates
`ck_pcbv_fixed_monthly_cost_minor_positive`, is re-raised by
`translate_integrity_error` and reaches the client as HTTP 500: precisely the defect
B2 exists to close, reintroduced invisibly. Symmetrically, nothing pins that
`planning_utilization_percent = 100`, `percent_value = 0` and `percent_value = 999.999`
are *accepted*, so tightening any bound would 422 legal input with the suite green.
Correction: one adjacent pair per bound — reject at the excluded value, accept at the
included one (`0`/`1` for `gt=0`; `100`/`100.01`; `0` and `999.999`/`1000`; `0`/`-1`).
Authority: charter rule 2; §6.2's CHECK list; R2-P4.

### S4 (should-fix) — C3's synchronization seam can hang the suite indefinitely

The C3/C6 harness block requires "a hard timeout on the blocked statement
(`SET LOCAL lock_timeout` or asyncio timeout) so a deadlock cannot hang the suite."
C6 has one (`asyncio.wait_for(…, timeout=0.3)`). C3 has none: `await
flush_complete.wait()` and `await release.wait()` are unbounded, so any failure in the
winner *before* it reaches the monkeypatched `audit` blocks forever rather than
failing. Not hypothetical — the B1 probe made the winner raise inside
`admission_error` and the focused suite hung until killed at 120 s (that hang is also
how the run left committed rows behind; see N3). Correction: wrap both waits in
`asyncio.wait_for` with an explicit timeout. Authority: plan C1–C11 harness block.

### Notes

- **N1** — C2 omits §7A.3's theorem row as worded ("the open row is the resolution
  for **today**"): the three boundaries are asserted at `second_day` (2026-08-12),
  not at `today`. The property is covered transitively by C8's all-present fixture
  (`effective_from = today − 1`, open, → `evaluable`). Recorded, not filed.
- **N2** — two of the four command anchors r1 verified "exact" are now **stale**
  because this fix touched their files: `create_cost_model_version` 14-74 → **15-75**
  (one added import) and `delete_cost_model_version` 14-37 → **14-36** (the removed
  `version = None`). Corrected spans below.
- **N3** — the configured development database carries phase-4 residue from
  **interrupted** runs: 3 workspaces created 2026-08-12 21:59/22:08 (the fix-r2
  session) — `ws_c73d3e66…` and `ws_f5002ad7…` (the C3 chain pair, each with a closed
  v1 and an open v2) and `ws_2739154…` (the C6 fixture, with its evaluation) — plus
  their groups, versions and audit rows. **Not a teardown defect** (proven above: two
  full-suite runs and two C3/C6-only runs each add zero rows); a killed process simply
  skips the `finally`, which is what S4 makes easy. Left in place — not this session's
  rows to delete. Suggested disposition: a one-line purge in the phase-4 closeout, or
  a maintenance follow-up.
- **N4** — C4's "exactly 4 dp" is asserted with `Decimal.__eq__`, which ignores the
  exponent, so the persisted *scale* has no arbiter. The column pins it; low value,
  next touch.
- **N5** — C8's six fixtures are a `for` loop inside one node rather than parametrized
  rows: an early failure aborts the remaining cases and the node id does not name the
  case, so a per-row mutation cannot be declared against it (P-I's observed-node-id
  discipline, P-G(b)'s naming rule). Next touch.
- **N6** — C3's seam is a monkeypatched `audit`. It is a genuine pause seam, not the
  excluded hand-built `IntegrityError`, and it satisfies the harness block's intent;
  but unlike C6's `after_lock` it is not declared in the plan as a designed test seam.
  Recorded so a future reader does not read it as smuggled.
- **N7 (graph, passing glance)** — two edges are **missing** from the pending delta,
  not wrong: `create_cost_model_version` writes `cost_model_terms`
  (`create_cost_model_version.py:68-69`) and `list_cost_model_versions` reads it
  (`list_cost_model_versions.py:32`), but no `…--writes_to--> table-cost-model-term`
  or `…--reads_from--> table-cost-model-term` edge exists among the 47. For the
  coordinator's post-approval batch; not adjudicated here.

## Step 3 — anchor-spans service for the 47 held items

Not adjudicated — no item was promoted, rejected, edited or removed. These are the
**current** spans so the coordinator's single post-approval pass uses final line
numbers. All verified against the working tree at `4e19506`.

**13 endpoint nodes** (r1 verified these exact; every one shifted **−1** because the
fix deleted `_BasisVersionBody.cost_per_worker_minute_minor`), file
`app/beyo_manager/routers/api_v1/item_economics.py`:

| Node | r1 span | **current span** |
|---|---|---|
| `endpoint-item-economics-post-cost-groups` | 93-99 | **92-98** |
| `endpoint-item-economics-get-cost-groups` | 102-109 | **101-108** |
| `endpoint-item-economics-patch-cost-group` | 112-119 | **111-118** |
| `endpoint-item-economics-delete-cost-group` | 122-128 | **121-127** |
| `endpoint-item-economics-post-section` | 131-138 | **130-137** |
| `endpoint-item-economics-delete-section` | 141-148 | **140-147** |
| `endpoint-item-economics-post-basis` | 151-159 | **150-158** |
| `endpoint-item-economics-get-basis` | 162-170 | **161-169** |
| `endpoint-item-economics-delete-basis` | 173-179 | **172-178** |
| `endpoint-item-economics-post-model` | 182-188 | **181-187** |
| `endpoint-item-economics-get-model` | 191-198 | **190-197** |
| `endpoint-item-economics-delete-model` | 201-207 | **200-206** |
| `endpoint-item-economics-status` | 210-215 | **209-214** |

**9 command nodes** (spans are decorator/`async def` → last line of the function),
files under `app/beyo_manager/services/commands/item_economics/`:

| Node | r1 verdict | **current span** |
|---|---|---|
| `command-…-create-production-cost-group` | exact (13-36) | **13-36** (unchanged) |
| `command-…-create-production-cost-basis-version` | exact (13-51) | **13-51** (unchanged) |
| `command-…-create-cost-model-version` | exact (14-74) | **15-75** ← stale, this fix added an import |
| `command-…-delete-cost-model-version` | exact (14-37) | **14-36** ← stale, this fix removed a line |
| `command-…-update-production-cost-group` | imprecise (stored 12-30) | **13-34** |
| `command-…-delete-production-cost-group` | imprecise (stored 12-38) | **15-41** |
| `command-…-add-section-to-cost-group` | imprecise (stored 12-48) | **15-49** |
| `command-…-remove-section-from-cost-group` | imprecise (stored 12-33) | **14-32** |
| `command-…-delete-production-cost-basis-version` | imprecise (stored 13-38) | **14-37** |

**25 edges** — all currently carry the single blanket anchor
`routers/api_v1/item_economics.py:88-215`, which is both stale (the file is now 215
lines) and, for the writes and reads, the wrong file. Per-edge anchors:

*9 `writes_to` (command → table): the `add`/mutation + `flush` site in the command.*

| Edge | **current anchor** |
|---|---|
| `create-production-cost-group --writes_to--> table-production-cost-group` | `create_production_cost_group.py:30-32` |
| `update-production-cost-group --writes_to--> table-production-cost-group` | `update_production_cost_group.py:27-30` |
| `delete-production-cost-group --writes_to--> table-production-cost-group` | `delete_production_cost_group.py:36-39` |
| `add-section-to-cost-group --writes_to--> table-production-cost-group-section` | `add_section_to_cost_group.py:43-45` |
| `remove-section-from-cost-group --writes_to--> table-production-cost-group-section` | `remove_section_from_cost_group.py:28-30` |
| `create-production-cost-basis-version --writes_to--> table-production-cost-basis-version` | `create_production_cost_basis_version.py:45-47` (chain closure at `:33`) |
| `delete-production-cost-basis-version --writes_to--> table-production-cost-basis-version` | `delete_production_cost_basis_version.py:32-35` |
| `create-cost-model-version --writes_to--> table-cost-model-version` | `create_cost_model_version.py:53-55` |
| `delete-cost-model-version --writes_to--> table-cost-model-version` | `delete_cost_model_version.py:31-34` |

*9 `accepts` (endpoint → command): the route's `_run(...)` dispatch line, file
`routers/api_v1/item_economics.py`.*

| Edge | **current anchor** |
|---|---|
| `post-cost-groups --accepts--> create-production-cost-group` | `:98` |
| `patch-cost-group --accepts--> update-production-cost-group` | `:118` |
| `delete-cost-group --accepts--> delete-production-cost-group` | `:127` |
| `post-section --accepts--> add-section-to-cost-group` | `:137` |
| `delete-section --accepts--> remove-section-from-cost-group` | `:147` |
| `post-basis --accepts--> create-production-cost-basis-version` | `:157-158` |
| `delete-basis --accepts--> delete-production-cost-basis-version` | `:178` |
| `post-model --accepts--> create-cost-model-version` | `:187` |
| `delete-model --accepts--> delete-cost-model-version` | `:206` |

*6 `reads_from` (endpoint → table): the SELECT in the query module, files under
`app/beyo_manager/services/queries/item_economics/`.*

| Edge | **current anchor** |
|---|---|
| `get-cost-groups --reads_from--> table-production-cost-group` | `list_production_cost_groups.py:15-23` |
| `get-basis --reads_from--> table-production-cost-basis-version` | `list_production_cost_basis_versions.py:15-27` |
| `get-model --reads_from--> table-cost-model-version` | `list_cost_model_versions.py:16-28` |
| `status --reads_from--> table-production-cost-group` | `get_economics_configuration_status.py:12-19` |
| `status --reads_from--> table-production-cost-basis-version` | `get_economics_configuration_status.py:20-27` |
| `status --reads_from--> table-cost-model-version` | `get_economics_configuration_status.py:28-35` |

*1 `configured_by`.*

| Edge | **current anchor** |
|---|---|
| `domain-item-economics --configured_by--> endpoint-item-economics-status` | `routers/api_v1/item_economics.py:209-214` |

## Lessons for the plans

- **L1 (extends P-M / charter rule 2).** A criterion stating a row **count** must
  state the *table* the rows enumerate, and the implementer's rows must be mapped
  back to it one-for-one. C1's "20 rows" was met numerically by 10 cases × 2 chains
  while three of §7A.4's ten rows had no fixture — the arithmetic is what made the
  gap invisible to two rounds. Companion to P-L's "registries list items, never
  counts".
- **L2 (extends P-K / P-M).** A criterion demanding a **filter** row (workspace
  scoping, `is_deleted`) must name the fixture property that makes the filtered row
  *compete for the asserted slice* — with `limit = 1` and an ordering key, foreign
  and deleted rows sort out of view and every filter row passes vacuously. Four of
  C10's six filter rows failed exactly this way.
- **L3 (extends P-T).** A concurrency criterion naming a synchronization seam must
  also require **every wait in that seam to be bounded**, not only the blocked
  statement: C3's unbounded `Event.wait()` converts any upstream failure into an
  infinite hang, which is strictly worse than a red test and is how a killed run
  leaves committed rows behind.
- **L4 (extends P-I).** When a fix cycle's own ledger records that a mutation
  reddened a proxy row *and* explicitly notes the integrated row stayed green, that
  sentence is a **finding the implementer already found** — the fix prompt should
  require it to be closed, not merely reported (S1's identity gap was written down
  in the ledger and shipped anyway).

## Human-authorization backlog

- 47 architecture-graph items still pending (17 promote / 30 edit-then-promote per
  r1). **No item was promoted, rejected, edited or removed by this session.**
  Corrected spans supplied above; N7 adds two missing `table-cost-model-term` edges
  for the same batch. Adjudication remains the coordinator's single post-approval
  pass under master plan §8's standing authorization.

## Write perimeter (this session)

Documents written — exactly three, all after the probes:

- `docs/architecture/under_construction/implementation/item_cost_calculation/plans/phase_4_configuration_services.md`
  (Review log append only — "Re-review r2" section; no other section touched)
- `docs/architecture/under_construction/implementation/item_cost_calculation/master_plan.md`
  (phase-4 tracker row only: state `IMPLEMENTED` → `CHANGES_REQUESTED`, date, actor, note)
- this handoff

**No code, test, migration or `.archgraph` file was written.** Architecture Graph
touched read-only (`archgraph_status`, `archgraph_list_pending_reviews`): revision
`bf6dad5b9264937b5950366affe9910dcaacf7abd68a42114bb52fa327e68262`, 148 nodes /
186 edges, valid, 0 diagnostics, 0 stale, **47 pending, zero delta** — unchanged from
the fix-r2 declaration.

## Mutation-probe declaration

Probes ran in the **main worktree** (the same `.git` limitation the implementer hit).
Every mutation was applied, exercised, reverted with `git checkout --`, and the file's
sha256 re-verified byte-identical to its pre-probe value; `git status --porcelain` is
empty at close and `git diff 4e19506..HEAD -- app/` is empty.

Files touched by probes (all restored):
`_common.py`, `configuration.py`, `enums.py`, `requests/__init__.py`,
`delete_production_cost_basis_version.py`, `update_production_cost_group.py`,
`routers/api_v1/item_economics.py`, `list_production_cost_groups.py`,
`list_production_cost_basis_versions.py`, `list_cost_model_versions.py`.

**Database side effects.** The economics-workspace id set is identical before and
after the probe sequence — the probes themselves left nothing. Two workspaces created
by this session's first full-suite run (`ws_88b1960b…` 07:40:05Z, `ws_ff19f3b0…`
07:40:53Z) and their 15 dependent rows were **deleted** at close, restoring the
database to as-found. The three 2026-08-12 workspaces described in N3 predate this
session and were deliberately **left untouched**. Configured DB left at head
(`90cdd23a828e`); no migration was run; no disposable database was created.

## Coordinator fold-ins

- Compile a fix-r3 prompt: B1 (six §7A.4 rows + the named guard mutation), B2 (six
  filter fixtures made sole-cause + two rename-collision rows), S1 (identity token on
  the real race, both chains), S2 (a straddling fixture for the `Decimal(str(v))`
  parse), S3 (one adjacent pair per bound), S4 (bound both C3 waits).
- Fold L1–L4 into §9's standing rules (L1 → P-L/P-M, L2 → P-K/P-M, L3 → P-T,
  L4 → P-I).
- N3 → phase-4 closeout or a maintenance row; N4/N5/N6 → next touch; N1 recorded,
  not actionable.
- Graph: corrected spans above + N7's two missing edges feed the single
  post-approval adjudication.
