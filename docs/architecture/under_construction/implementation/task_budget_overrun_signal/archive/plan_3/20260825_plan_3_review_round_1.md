---
plan: plan_3
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-25
actor: Claude Opus 5 (1M context)
---

# Plan 3 first review — route, HC-2a artifacts, frontend handoff

**Verdict: CHANGES_REQUESTED.** One should-fix, zero blocking. The production route, the four
HC-2a artifacts, the published frontend handoff and the graph delta are all correct as shipped —
verified structurally and, where it mattered, by planted defect. The one fix is **test-only, in one
file, ~8 lines**: `C4(d)`'s criterion enumerates the README field types and per-row `Required`
markers and the shipped test asserts neither, which I demonstrated by mutation.

Everything else in this phase is settled; the fix round is delta-scoped to
`tests/unit/routers/api_v1/test_budget_signals_route.py`.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — the sibling route was moved; keep it, or move it back?

**Question.** Keep the stronger route ordering (both fixed batch routes ahead of *every*
parameterized task route) and record it as an amendment to the ratified intention — or move the
pre-existing `budget-allocations` route back and weaken the plan's ordering rule to match what the
intention actually promised?

**Story.** Every `/tasks/...` URL in the economics API is matched top-to-bottom in one file. Two of
them are fixed words — `budget-allocations`, `budget-signals` — and six are wildcards like
`/tasks/{id}/production-time`. If a wildcard ever gets shortened to just `/tasks/{id}`, it will
swallow the two fixed URLs and managers will silently get the wrong screen's data. Nothing does
that today. To make that impossible in future, this phase lifted the older `budget-allocations`
route up the file so both fixed routes sit above all the wildcards. That is a change to a line of
shipped code your ratified constraints said would only ever be *added to*.

**Branches.**
- **Keep it** — the ordering trap is closed permanently; the intention gains one sentence saying
  one existing route moved, and the record stops matching the tree only after that sentence lands.
- **Move it back** — the intention's "addition only" text stays literally true; the phase's
  ordering rule shrinks to "ahead of every parameterized *GET*", which is what the intention
  actually promised, and the trap stays open for a future route shape.

**Recommendation.** Keep it and amend — I verified the move changes no request's destination today
(no wildcard route can match a two-segment fixed path), so the cost is one sentence of record and
the benefit is a durable guard.

**On silence.** The gate holds: Phase 3 stays CHANGES_REQUESTED for the unrelated test fix and the
relocation ships neither approved nor reverted.

**Trace.** intention §1 HC-2a, §7A.4; plan 3 §6 C1(b); `routers/api_v1/item_economics.py:319-347`.

## Gate check

| Gate | State | Source |
|---|---|---|
| `planning/intention.md` header | **RATIFIED** (round 12, 2026-08-25) | intention header; master plan §2 |
| Master plan Phase 2 | **APPROVED** (2026-08-25, gate `18f774f`) | master plan §4 |
| Master plan Phase 3 | **REVIEWING** (2026-08-25, coordinator) | master plan §4 |
| Projection gate | waived, recorded | plan 3 §9 first entry |

Both prompt gates hold. This is a first full review, not a re-review.

## Evidence identity

- **Review tree:** `032b0d3`; `app/` **clean** (`git status --porcelain -- app/` empty); dirty
  tracked paths are `.archgraph/architecture.yml`, `docs/archgraph-anchor-observations.md`,
  `master_plan.md`, `plans/plan_3.md`; dirty-tree digest
  `974275ab7b7c88686b5b6e6c62da364ad8ec82b654ee5d34ae552a70bc2861f2` (`git diff | shasum -a 256`,
  taken before any probe).
- **`app/` is byte-identical to the checkpoint** `c83c815` (`git diff c83c815..032b0d3 --name-only`
  returns only the implementer handoff).
- **L4 budget: exactly one, spent one.** Authorization taken before the run: *the cited implementer
  stamp identifies checkpoint `c83c815` plus dirty digest `dc386467…`, and the coordinator's
  tracker and Review-log edits have changed the dirty set since, so my tree is not the cited tree*
  (charter L4 case (b)).
- **Closing stamp:** `PYTHONPATH=. pytest -m 'not e2e'` from `app/` →
  **21 failed / 2800 passed / 1 skipped**, 52.76 s. The 21 IDs were compared **member by member**
  against the published durable set in
  `HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7 (not against the implementer's
  prose): **additions ∅ / removals ∅**.
- **C5(a) sibling check:** none of `test_budget_allocations_query.py`,
  `test_production_time_query.py`, `test_price_scenario_query.py`,
  `test_budget_status_filter_spec.py`, `test_live_clock_goldens.py`,
  `test_budget_division_routes.py` appears in the failing set — all green under the stamp.
- Every other probe this session ran at L1 or was a source/structural read. No cited command was
  repeated for independence.

## Findings

### SF1 — should-fix — `C4(d)`'s README type and `Required` assertions were not written

**What is wrong.** C4(d) requires the ten `data.budget_signals[].<field>` rows *"each `Required:
Yes`, with `budget_state` and `currency` typed `string` and the seven numerics `integer`"*.
`test_budget_signals_readme_detail_documents_the_ten_field_contract`
(`tests/unit/routers/api_v1/test_budget_signals_route.py:130-155`) asserts only that each field
name occurs once followed by a pipe, pins the **two** string-typed rows as whole-line literals, and
then checks `section.count("| Yes |") >= 10`. The section contains **17** `| Yes |` occurrences
(the parameter row, `ok`, the array row, `warnings[]` and the three `detail[]` rows on top of the
ten fields), so the count assertion carries seven rows of slack and is not a per-row check. The
seven numeric rows' `integer` type is asserted nowhere.

**Demonstrated, not argued.** Applied to `beyo_manager/routers/README.md`:
`| data.budget_signals[].over_seconds | integer | Yes |  |` →
`| data.budget_signals[].over_seconds | string | No |  |`. Ran the C4(d) test plus the whole
mirror file: **5 passed**. A served integer can be documented to the frontend as an optional
string and every shipped guard stays green. Reverted; `README.md` md5 `5839a70e…` restored.

**Violated authority.** `plans/plan_3.md` §6 C4(d); master plan §6.6 (wire vocabulary); charter
rule 2 (enumerate, and each row's assertion is its own) and rule 15 (a guard ships with proof it
can fail). Note that `routers/README.md` is read by exactly two tests in the repo — this one and
the mirror test, which compares method and path only — so nothing else covers it.

**Suggested correction** (one test, no production change): replace the two whole-line literals and
the `>= 10` count with a per-field loop asserting the exact cell trio, e.g. for each of the seven
numerics `f"| data.budget_signals[].{field} | integer | Yes |" in section`, and for `task_id`,
`budget_state`, `currency` the `string` form. **Named mutations for the fix round** (both in
`beyo_manager/routers/README.md`, applied at the row, reverted after): (a) one numeric row's type
`integer → string` must redden; (b) a different numeric row's `Required` `Yes → No` must redden —
two mutations, because a single one short-circuits the other's sub-check (charter rule 12).

### N1 — note — the relocation of `route_get_task_budget_allocations`

Judgment probe 1. The implementation moved the pre-existing fixed route (previously declared after
`route_list_task_evaluations`) up to sit immediately before the new route, so that both fixed paths
precede every `/tasks/{...}` route. **This is required by plan C1(b) and is not a finding against
the implementer**, who declared it in the handoff and in the plan's Review log. It is recorded
because two ratified sentences no longer describe the tree:

- intention §1 **HC-2a** — *"Exactly four artifacts change, **by addition only**, each reverted by
  one edit"*. Artifact 4 now also carries a relocation; reverting it is two edits, not one.
- intention **§7A.4** — its contract is *"declared immediately after `budget-allocations` … which
  puts it ahead of every parameterized `/tasks/...` **GET**"*. That was already true without moving
  anything: the two routes that sat above the sibling are `POST /tasks/{id}/evaluations/commit` and
  `GET /tasks/{id}/evaluations`, and C1(b) widened the rule from "every parameterized GET" to
  "every path starting `/tasks/{`". The plan is strictly stronger than the authority it traces to.

**Behaviourally inert, verified.** Every `/tasks/{...}` route in the file carries at least one
further path segment, so none can match a two-segment fixed path in either direction; the README
Quick Index order is untouched and both mirror arbiters are set comparisons. I re-derived the
served route table from the module after the move: 27 decorators, matching the README's 27 Quick
Index rows and `_EXPECTED_ROUTES`'s 27 entries. See owner card 1.

### N2 — note — `C4(a)`'s operation-id column is guarded by nothing

C4(a)'s Expected column names the full README row *including*
`route_get_task_budget_signals_api_v1_item_economics_tasks_budget_signals_get`, but its Home test
`test_readme_quick_index_mirrors_every_shipped_route` matches `_README_ROW`, which captures method
and path only. No test in the repo reads an operation id.

**Verified correct anyway, independently, this session:** I generated the router's OpenAPI document
and compared the `operationId` of all 27 item-economics operations against the README's fourth
column — **27 rows checked, 0 mismatches**, and the new route's generated id is exactly the string
the README and master plan §6.5 publish. Lesson only: either widen `_README_ROW` to capture the
operation-id column, or drop it from C4(a)'s Expected so the criterion stops naming what it does
not check.

### N3 — note — `C2(c)` cannot observe a double-listed route

`test_router_route_pairs_match_the_authoritative_route_table` builds `expected` from the **set
union** of `_ROUTES` and `_ALL_ROLE_ROUTES`. Adding the budget-signals row to *both* lists leaves
that set unchanged, so C2(c) alone cannot prove the `_ALL_ROLE_ROUTES` exclusion.

**The exclusion is nevertheless structurally enforced** — by
`test_budget_status_route_is_available_to_all_roles`, whose fallback branch asserts the dispatched
callable is `get_task_budget_status` for ADMIN/MANAGER and expects `200` for WORKER/SELLER; MUT-03
reddened exactly those four parametrizations. Recorded so a later phase does not mistake C2(c) for
the guard.

### N4 — note — MUT-01 short-circuited the half of C1(b) that motivated the move

Charter rule 12. `test_budget_signals_fixed_route_precedes_parameterized_task_routes` has three
sequential assertions. MUT-01 (move the new decorator below `route_get_task_price_scenario`) trips
the **first** — `signal_index == allocation_index + 1` — and returns, so
`signal_index < min(parameterized_indices)` never executed in the round. The precedence sub-check —
the one that required moving pre-existing code — was named by no mutation in the plan's closed set
of nine.

**Gap closed this session by variation, not by re-running MUT-01.** I moved the *pair* of fixed
routes back below `route_commit_item_cost_evaluation` / `route_list_task_evaluations`, preserving
adjacency so assertion 1 stays green, and observed the red: `assert 19 < 16` at
`test_budget_signals_route.py:84`. Reverted; `item_economics.py` md5 `1331bd27…` restored. The
third assertion (`allocation_index < min(...)`) is implied by the first two and can never be the
sole failure — harmless, not a defect. Lesson for the plans: a criterion with N sequential
assertions needs N mutations, enumerated from the code after implementation.

### N5 — note — the frontend handoff's ten-field contract table is guarded only by its header

`test_budget_signals_handoff_records_the_served_contract` pins `"| Field | Type | Meaning |"` and
the two enum vocabularies, but asserts no field row. **Demonstrated:** deleted three of the ten
rows (`over_seconds`, `allowed_seconds`, `cost_per_worker_minute_ten_thousandths`) from the
published handoff and ran the file — **3 passed**. Reverted; handoff md5 `9c62a862…` restored.

**This is a plan defect, not an implementation one** — C6(e) literally asks for *"the literal
ten-field table header row"*, and the test delivers exactly that; filing it against the implementer
would be a finding on a non-defect. Routed as a **candidate criterion** for the coordinator: C6(e)
should require each of the ten `` | `field` | type | `` rows, with the named mutation "delete one
field row from the handoff table" (MUT-09 already covers a correction sentence, not the table).
Same shape, smaller: C6(a) and C6(b) assert the metadata paths and the three correction sentences
*anywhere in the document* rather than under their required headings, which the criteria do name.

### N6 — note — the implementer handoff's baseline enumeration lists 22 IDs for a 21-ID set

`handoffs/implementer/20260825_plan_3_implementation_round_1.md` §Validation evidence names
`test_worker_working_sections_excludes_counts_for_deleted_parent_tasks` as a separate row *and*
counts it inside *"the two `test_batch_working_section_integration` tests"* — those are the same
test. The measured set is correct (I re-measured 21 and matched the published list member by
member); only the prose is one row long. Charter manifest property 3: counts and enumerations are
derived from the artifact they count, never re-typed. No action beyond the record.

## What I verified correct

Structural and source-level checks, so the next round does not repeat them:

- **Route identity and dispatch.** `GET /tasks/budget-signals` is declared immediately after
  `/tasks/budget-allocations` and both precede all six `/tasks/{...}` routes
  (`item_economics.py:319-347`). Dispatch passes the repeatable list **unchanged**: a probe with
  `?task_ids=tsk_b&task_ids=tsk_a&task_ids=tsk_b` reached `get_task_budget_signals` with
  `query_params == {"task_ids": ["tsk_b", "tsk_a", "tsk_b"]}` — order and duplicates preserved,
  no dedup or sort at the boundary. The envelope boundary holds: success responses carry exactly
  `{data, ok, warnings}` via `build_ok`, and the over-cap `ValidationError` arrives as
  `{error, ok}` at 422 via `build_err`/`ValidationError.http_status`.
- **Authorization.** `require_roles([ADMIN, MANAGER])` on the route; the row is in `_ROUTES`
  (24 entries) and absent from `_ALL_ROLE_ROUTES` (3 entries, unchanged). See N3 for where the
  exclusion actually bites.
- **The validation seam is two distinct envelopes**, both covered: `detail[]` 422 with zero service
  entries when `task_ids` is absent, and `error`/`ok` 422 with exactly one service entry over the
  cap — the latter through the **real** Phase 2 service (`_MAX_TASK_IDS = 50`, raised on the raw
  list at `get_task_budget_signals.py:76-79`), with the identity asserted as a prefix per §7A.3.
  The 50/51 adjacent pair is enumerated.
- **HC-2a counts, each derived from its own registry, not read from the plan:** 27 `@router.`
  decorators; 27 README Quick Index rows matching `^\| VERB \| /api/v1/item-economics/`; 27
  `_EXPECTED_ROUTES` entries and 27 distinct `(method, path)` pairs; `_ROUTES` 23 → 24;
  `_ALL_ROLE_ROUTES` 3 → 3. Exactly **four** pre-existing files changed, so HC-2a's "no fifth" holds.
- **The mirror identifier is truthful:** `test_the_registry_ships_twenty_seven_routes`, and the
  module docstring's *"Two arbiters over the same 27 rows"* was updated with it.
- **Quick Index and detail section agree** on method, path, tag and operation id; the detail table
  carries the **actual** ten-key wire contract in the shipped order — I diffed it against
  `serialize_budget_signal` (`division_serializers.py:74-88`) key by key. No timestamp field exists
  on the wire.
- **The frontend handoff.** All three correction sentences present verbatim, with their reasons;
  five `### Open question N` headings each carrying a substantive answer that matches its authority
  (Q1 §5.3/S2, Q2 §7.4, Q3 §3.3, Q4 §2.4A, Q5 §4.1 — Q5 additionally corrects the request's
  assumption that the rate is resolved live rather than snapshotted at commit); the D9/D10 and
  infeasible-production-time sentences; both enum vocabularies exactly as master plan §6.6; the
  role sentence, the ordering sentence and "no server timestamp is served".
  **Its money figures are true, re-derived here rather than trusted:**
  `calculate_consumed_cost_minor` at rate `3.7500` returns `0` for 8 s, `1` for 9 s and `9` for
  136 s — so *"the first eight seconds cost zero minor units"* is exact.
- **Neither published `from_frontend` file was edited**, and no `docs/domains/item_economics`
  surface was touched — confirmed by the perimeter diff below, not by claim.
- **C6(f)'s absence guard can observe a presence** (charter rule 15, and the rule's own worst case
  is an absence row that measures true because nothing ever writes the form). I planted the retired
  identity in the new handoff; `test_retired_inline_refusal_identity_is_absent_from_live_sources`
  reddened naming the file. Reverted.
- **Test authorship traces both ways.** Six new route tests → C1(a), C1(b), C3(a), C3(b), C3(c),
  C4(d); three new handoff tests → C6(a)+(c), C6(b), C6(d)+(e); the two modified pre-existing files
  add rows, not tests. **Zero orphan tests.** Both new files are `phase`-free and marked `unit`
  (`15_testing.md`).

## Judgment-call probes — outcomes

1. **The relocation.** Correct and required by C1(b); behaviourally inert; no finding against the
   implementer. Two ratified sentences now mis-describe the tree — owner card 1, note N1.
2. **Checkpoint perimeter.** `git diff --name-only 18f774f..c83c815` returns exactly ten paths:
   the seven Plan 3 §4 paths plus `master_plan.md` (tracker row), `plans/plan_3.md` (Review log)
   and the implementer handoff. **No out-of-perimeter implementation write.** `c83c815..032b0d3`
   is the implementer handoff alone; `032b0d3..HEAD` is empty. C5(b) holds.
3. **Graph provenance — isolable, yes.** `.archgraph/architecture.yml` is unstaged and carries
   **two disjoint deltas** against HEAD (204 nodes / 312 edges → 206 / 316):
   - Phase 3: `endpoint-item-economics-task-budget-signals` + `accepts` →
     `projection-item-economics-task-budget-signals` + `governed_by` →
     `decision-money-audience-admin-manager-only`, all stamped `2026-08-25T06:35:03.125Z`;
   - unrelated Bootstrap Pause work: `command-bootstrap-pause-reason-seeding` + two `depends_on`
     edges, all stamped `2026-08-24T13:47:21.336Z`.
   The two groups occupy **four non-overlapping diff hunks** (bootstrap node, endpoint node,
   bootstrap edges, endpoint edges), so the phase-3 delta can be staged alone by hunk selection or
   by node id, with no risk to the bootstrap work. The delta matches master plan §8's phase-3
   expectation exactly (one endpoint node, `accepts` to the projection, the governance link) and
   the implementer's stated entry state (205 nodes / 314 edges) reconciles arithmetically with
   HEAD + the bootstrap group. The endpoint node's evidence resolves:
   `route_get_task_budget_signals` is at `item_economics.py:335-346` against a recorded span of
   335–347 (one trailing blank line). **No graph state was read through, written by, or mutated by
   this session; no archgraph tool was called** — the assessment is from the YAML on disk.
4. **The evidence-only commit `032b0d3`.** Its L4 record identifies checkpoint `c83c815` plus dirty
   digest `dc386467…`. That digest **cannot** describe my tree: `master_plan.md` (Phase 3
   `IMPLEMENTED → REVIEWING`) and `plans/plan_3.md` (the review-dispatch entry) both changed after
   it was taken. The record remains valid evidence about the **code** — `app/` is byte-identical
   across `c83c815..032b0d3..HEAD` and clean — but **my closing stamp is the authoritative one for
   this gate**, and it reproduces the same result (21/2800/1, delta ∅/∅) on a differently-identified
   tree, which is corroboration rather than repetition.

## Mutation-probe declaration

Every probe applied and reverted; each file checksummed byte-identical afterwards and confirmed
absent from `git status --porcelain`.

| Probe | File touched | md5 after revert | Result |
|---|---|---|---|
| C1(b) precedence sub-check (rule-12 gap, N4) | `app/beyo_manager/routers/api_v1/item_economics.py` | `1331bd2719ff6bc453a87cad5a8289e6` | red as required |
| README type + `Required` (SF1) | `app/beyo_manager/routers/README.md` | `5839a70e92670bbdcc564c1995e6ea89` | **stayed green — the finding** |
| Handoff contract-table rows (N5) | `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_task_budget_overrun_signal_20260825.md` | `9c62a862b0dbfc2d1f5ede0f29797128` | **stayed green — the note** |
| Retired-identity presence (rule 15) | same handoff | `9c62a862b0dbfc2d1f5ede0f29797128` | red as required |

**State side effects:** none. No test that commits rows was run outside the one L4 stamp, which
owns its own disposable databases (`tests/database_isolation.py`). No file was created or deleted;
the two route/dispatch probes ran as in-process scripts, not as test files. `.archgraph/`,
`docs/archgraph-anchor-observations.md`, `.archgraph/backfill/`, the remaining-production-pressure
project and the worker-time-pressure `from_frontend` handoff were preserved untouched by every
probe.

**Write perimeter of this session:** this handoff; `plans/plan_3.md` §9 (Review log append);
`master_plan.md` §4 (Phase 3 tracker row only); and one append to
`docs/archgraph-anchor-observations.md`, a standing owner-directed observation log unrelated to
Phase 3's findings — declared here for perimeter completeness, per master plan §9 rule 1, which
requires the conflict between a prompt's allowed-files list and a standing external brief to be
reported rather than resolved silently. Nothing else was written.

## Carry-forward dispositions

| Item | Destination | Why |
|---|---|---|
| SF1 | **Phase 3 fix round 1** | Required for approval; one test file, two named mutations supplied |
| N1 / card 1 | **Owner, then intention amendment** (lettered `§7A.4A`, never a renumber) | Ratified text vs tree; coordinator folds after the answer |
| N2 | **Coordinator — plan lesson**, applies to the next route-adding phase | C4(a) names a column its home test cannot see |
| N3 | **Coordinator — record only** | The exclusion holds; the note prevents a future misreading |
| N4 | **Coordinator — planner lesson** | Sequential-assertion criteria need one mutation per sub-check |
| N5 | **Coordinator — candidate criterion for C6(e)**, plus the C6(a)/C6(b) locality tightening | Plan defect; do not charge it to the fix round unless the coordinator folds it in |
| N6 | **Coordinator — record only** | Prose arithmetic; measured set is correct |

## Lessons for the plans

1. **A criterion that enumerates cells must be discharged cell by cell.** C4(d) named types and
   `Required` markers; a `count(...) >= 10` proxy with seven rows of slack replaced them. The
   proxy-count shape is the same family as the occurrence-count allowlist in charter rule 15.
2. **A criterion with N sequential assertions needs N named mutations** (rule 12), enumerated from
   the implemented code, not from the plan's prose. Plan 3's closed set of nine covered C1(b)'s
   adjacency and never its precedence — the half that justified touching pre-existing code.
3. **A plan criterion must not be stronger than the intention section it traces to** without the
   planner routing the widening back. C1(b) widened §7A.4 from "every parameterized GET" to "every
   `/tasks/{` path" and thereby required an edit HC-2a forbids; nobody noticed until the
   implementer had to make it, and the projection gate that would have caught it was waived.
4. **"Contains the header row" is not "contains the table."** C6(e) guards a published external
   contract by one header string. When a criterion's subject is a table, its rows are the criterion.
