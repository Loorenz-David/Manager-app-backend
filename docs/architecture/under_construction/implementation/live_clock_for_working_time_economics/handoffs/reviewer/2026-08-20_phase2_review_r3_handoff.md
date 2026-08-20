---
plan: 2
role: reviewer
round: 3
verdict: CHANGES_REQUESTED
date: 2026-08-20
actor: Opus 5
project: live_clock_for_working_time_economics
---

# Review r3 — plan 2, first full review

The three surfaces are live and the production code is right. I re-derived the fold, the
composition and the batch path against the plan file by file, walked all four payloads of
one fixture side by side, and every worked-derived field agrees on one number — which is
the whole point of the phase. The proof is where the work is still short: two of the four
frontend criteria this pipeline adopted verbatim as contract are not actually
discriminated by any test, and four criteria shipped their headline assertion while
dropping the subordinate clauses the plan spelled out. One delivered test will begin
failing on its own in November, with no code change, and it would land in the very
baseline this pipeline publishes as the next pipeline's reference point.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Nothing in this round needs an owner answer; every finding routes through the
coordinator to a fix cycle. (The three `ai_inferred` graph items remain pending owner
adjudication under `plans/plan_4.md` C6 — untouched by this session, as instructed.)

---

## 1. Perimeter check (step 1)

`git status` clean at `26ef905`, past the fix checkpoint `a28e9e5`.

| Commit | Files | Verdict |
|---|---|---|
| `e7d65b9` implement r1 | 12 — 6 production, 2 test, 3 pipeline records, 1 archgraph | exactly the declared set ✓ |
| `a28e9e5` fix r2 | `test_phase2_live_surfaces.py` + 3 pipeline records; **zero** files under `app/beyo_manager/` | test-only, as prescribed ✓ |
| `bb6cc43` production budget cap | `calculator.py`, `price_scenario.py`, `serializers.py`, `get_task_price_scenario.py`, 5 test files, 1 frontend handoff, `.archgraph/architecture.yml` | foreign-but-expected per master §7 ✓ |

**No golden JSON was moved by any commit in this range** — no escalation is owed. No cap
commit touched any of the six production files in our perimeter. Nothing outside the two
declared perimeters and the recognized cap stream appears in `git diff 487b98a..HEAD`.

One observation, recorded not raised: `bb6cc43` also modified
`test_phase4_fix_coverage.py`, which owns one of the two named flaky tests (master §6).
Foreign-but-expected under "those files' test files", and it did not disturb the ID set.

## 2. Baseline, measured by me on the tree I ran on

`PYTHONPATH=. pytest -m 'not e2e'` at `26ef905`: **26 failed / 2476 passed / 1 deselected**
in 137.25 s. Failing-ID set `comm`-diffed against master §6's enumeration: **added ∅,
removed ∅**. Phase file: **15 tests**, all green. No count was carried from any prior
round.

## 3. F-L4 — the sampled ledger re-measurement (lead probe)

Three rows re-measured by me, each whole-suite on the post-cap tree, both-direction ID
diff against my own clean run, reverted, revert hash-verified byte-identical to `HEAD`.

| Ledger row | Site | Ledger claim | I observed | Reproduces? |
|---|---|---|---|---|
| **3 — C5 ORM assignment** | `get_task_production_time.py`, live figure assigned onto `TaskStep.total_working_seconds` | 5 IDs | **5, the same 5**, removed ∅ | **yes, ID-for-ID** |
| **6 — C6 E-A eager load** | `get_task_budget_allocations.py` step-load site, `+ selectinload(TaskStep.latest_state_record)` | 4 IDs | **4, the same 4**, removed ∅ | **yes, ID-for-ID** |
| **11 — C11 shim default** | `get_working_section_typical_times.py:typical_times_statement`, defaulted branch → `datetime(2099,1,1)` | 1 phase ID + 8 typicals dependents | **9, the same 9**, removed ∅ | **yes, ID-for-ID** |

Observed IDs, row 3: `test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free`,
`test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds`,
`test_c6_allowances_are_byte_identical_after_settlement_recompute`,
`test_c6_created_at_is_carried_into_the_production_division_row`,
`test_c9_settlement_window_drop_is_visible_until_recompute` (all in the phase file).
Row 6: `test_c6_all_completed_e_a_section_keeps_allowances_without_eager_state_load`,
`test_c8_allocations_batch_has_one_open_record_probe`,
`test_c8_three_task_batch_shares_one_probe_and_one_worker_sweep`,
`test_c8_three_task_batch_runs_one_sweep_per_active_worker`.
Row 11: `test_c11_typicals_compatibility_shim_keeps_five_sample_median`,
`test_price_scenario_query.py::test_phase5_c3_typical_counts_only_the_requested_tasks_steps`,
and six `test_typical_times_query.py` rows
(`…uses_group_median_and_returns_empty_sections`, `…aggregates_same_task_section_steps_before_sampling`,
`…admits_old_first_pass_when_recent_rework_closes_group`,
`…uses_continuous_median_and_half_even_rounding[continuous-interpolation]`,
`…[half-even-rounding]`, `…excludes_non_completed_and_marked_wrong_steps_independently`,
`…requires_five_qualifying_groups`).

**Verdict on F-L4: the corruption is isolated to row 4. The ledger otherwise reproduces.**

I also confirmed the coordinator's structural argument independently at source, and it is
exactly right: `created_at` is read at **one** place in the whole domain module —
`budget_division.py:_governing_step`'s sort key — and reaches no payload field, so on a
section with a single candidate (which is what both golden tasks hold, verified at
`test_live_clock_goldens.py`) omitting it cannot move one byte. `latest_state_record` is
read at **two** places — the same sort *and* `budget_division.py:group_steps_by_section`,
which feeds `group["state_entered_at"]` → the serialized `state_entered_at` — so its
omission blanks a payload field on every section regardless of candidate count. Row 4's
golden attribution is therefore structurally impossible; row 5's is structurally
necessary. See S5 for the systemic cause.

## 4. Findings

### BLOCKING

**B1 — §5.2 criteria 1 and 2 are adopted verbatim as contract, and neither is
discriminated by any test.** Authority: `planning/intention.md` §5.2; `plans/plan_2.md`
§5 C2 and C4.

*Criterion 1 (`share_state` consistent with the figures beside it).* The only assertion
on a served payload's `share_state` in this phase is
`test_phase2_live_surfaces.py:test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free`
(`assert section["share_state"] == "over_share"`). On that fixture the section's
`allowance_seconds` is **0** — the excluded steps charge 1440 s against a 1200 s budget,
so `distributable_seconds` is `max(0, -240) = 0`. Under the live basis the section works
2040 s; under the pre-phase settled basis it works 1440 s. **Both exceed 0, so both yield
`over_share`.** The row returns the same verdict with the phase's entire change reverted.
This is the identity-element class again — the degenerate value is the allowance, not the
addend. Plan §5 C2 called for "a section 25 minutes into a 3 m 6 s allowance" with "exact
expected integers in the test"; what shipped is a section with no allowance at all.

The companion assertion in the same row,
`section["left_seconds"] == section["allowance_seconds"] - section["worked_seconds"]`, is
a tautology against the implementation: `budget_division.py:divide_production_budget`
emits `allowance_seconds`, `left_seconds` and `share_state` in **one dict literal** from
the same `worked` and `allowance` locals. No single-site production mutation can make it
false. Verified structurally, no run needed.

*Criterion 2 (two calls a few seconds apart differ only in time-dependent fields).* Plan
§5 C4 states two contracts — "serving each endpoint twice yields byte-identical payloads"
**and** "loader invocations == 1 per request". Only the second shipped:
`test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds` serves
each endpoint exactly **once** and never compares two payloads. There is no byte-identity
row anywhere for the open-record case; C1's goldens cover only the idle case (§5.2
criterion 4).

**The property itself holds** — I constructed and measured it: on `_make_live_fixture`
with `ctx.now` frozen and an open working record, serving E-P twice and E-A twice yields
byte-identical payloads (both `True`). So this is unwritten, not unwritable, exactly as
B1 at implement r1 was. It matters downstream: plan 3 edits
`division_serializers.py:serialize_task_production_time` and
`serializers.py:serialize_task_budget_status` — the two payload builders — and the
open-record determinism guard is what would catch a regression there that the goldens
cannot see.

*Required correction.* (a) Give C2 a fixture with a **positive** section allowance where
the settled basis is at or under it and the live basis is over it, and assert the exact
integers for `allowance_seconds`, `worked_seconds`, `left_seconds` and `share_state`;
**named mutation, definition site,
`get_task_production_time.py:get_task_production_time` substitution site** — build
`DivisionStep(total_working_seconds=step.total_working_seconds)` instead of
`live_seconds[step.client_id]`. Both sides: contract `share_state == "over_share"`;
mutation `== "on_track"` ⇒ red. On today's fixture that mutation leaves `over_share` on
both sides. (b) Add C4's byte-identity row per endpoint at a frozen `ctx.now` with an open
record; keep E-A's call single-task, since its task `SELECT` carries no `ORDER BY`
(the order-luck hazard already recorded for phase 1's E-A golden).

### SHOULD-FIX

**S1 — C6 row 1 ships its headline and drops all three of its honest-form clauses.**
Authority: `plans/plan_2.md` §5 C6; intention §9A T12, §4.3A.
`test_c6_allowances_are_byte_identical_after_settlement_recompute` asserts the
allowance/left byte-identity across the settlement close, and nothing else. Absent:
(i) the assert that **no excluded step in the fixture has an open working record**;
(ii) the assert that `charged_seconds` is computed from settled values, on the division
input; (iii) the assert that the `typical` blocks are byte-identical (path 3, §4.3A —
the plan's own "expensive mistake").

Clause (i) is load-bearing and its absence leaves a §4.1A C invariant unguarded:
`divide_production_budget` computes `charged_seconds` as the sum of
`total_working_seconds` over **excluded** steps, which on the substituted rows is now the
**live** figure. An excluded step holding an open record would make every
`allowance_seconds` in its section tick downward second by second — precisely the
"non-worked-derived" claim §4.1A C makes for `allowance_seconds`. I checked reachability:
`_step_transition_core.py:_apply_step_transition` sets `closing_record.exited_at = now`
unconditionally on every transition, so the state is not reachable through the sanctioned
path and **there is no live defect here**. The assertion's job is to pin that, and it is
the assertion the plan asked for.

Clause (iii) has no substitute: nothing in the phase guards path 3. C6 row 1 cannot cover
it by accident either, because after `_recompute_step_time_totals` the settled total
equals the live one, so a live-fed typical would be identical on both reads.

**S2 — C7's non-vacuity clause is absent and its token walk is narrowed from the pattern
it cites.** Authority: `plans/plan_2.md` §5 C7.
(a) The plan requires the worker face's five fields to equal the manager face's **and to
be greater than the same task's settled-basis values** — "the row is non-vacuous only
because the live term is non-zero". Only the equality shipped. As written, both faces
silently returning the settled basis together satisfies the row. (The suite catches that
elsewhere — `test_c3_population_fold_counts_nonzero_skipped_consumption_on_manager_face`
pins the manager face absolutely at `840` — but C7's own row does not.)
(b) The plan requires "walking **every key** of `serialize_task_budget_status(...)`" and
names `test_production_time_query.py:test_c14_c16_flat_time_only_degradation_and_tenant_boundary`
as the pattern. That pattern uses a **recursive** `walk()` over the whole body. What
shipped iterates one flat sub-dict, `worker_payload["result"]`, non-recursively. The
top-level keys are unguarded, including the `include_monetary=False` branch's own
`payload["allowed_worker_minutes"]` assignment at
`serializers.py:serialize_task_budget_status`. I dumped the worker payload and confirmed
no money token appears anywhere in it today, so the narrowing hides nothing at present —
it just moves the guard off the surface a regression would land on.

**S3 — `test_c11_typicals_compatibility_shim_keeps_five_sample_median` expires on
2026-11-17 and will silently join the published baseline.** Authority: master plan §5
("an observation that depends on the host's timezone, locale or clock is an environment
fact"); §7 closeout obligation 7.
The fixture seeds its five historical steps at
`closed_at = now - timedelta(days=1)` where `now` is the **hard-coded**
`datetime(2026, 8, 20, 12, 0, tzinfo=UTC)` from `_make_live_fixture` — i.e. an absolute
`2026-08-19T12:00Z`. It then calls `typical_times_statement(workspace_id)` **without**
`now`, which is the point of the row: the shim reads the real wall clock, so the cutoff is
`real_now - 90 days` and the filter is `latest_closed_at >= cutoff`
(`get_working_section_typical_times.py:typical_times_statement`, verified at source). The
row therefore qualifies only while `real_now <= 2026-11-17T12:00Z`. After that instant
`sample_count` becomes `0`, `typical_worker_seconds` becomes `None`, and the test fails
with nothing in the repository having changed.

The house form is two files away and correct:
`test_budget_allocations_query.py:_seed_two_section_allocation` seeds its historical steps
at `datetime.now(timezone.utc) - timedelta(days=1)`. Correction: derive this fixture's
`closed_at` from the wall clock, since the assertion is deliberately made against the
wall-clock branch. Consequence if left: master §7 obligation 7 publishes this tree's
enumerated failure-ID set as `narrow_typical_work_times`' reference point, and that
enumeration would acquire a 27th member on a date unrelated to any commit.

**S4 — D7's recording obligation is unmet at both substitution sites.** Authority:
`plans/plan_2.md` §6 D7; master plan §5 ("a delegation grant names its post-closeout
medium").
D7 grants strict indexing and requires it recorded **as a comment at the substitution
site**. The strict indexing shipped correctly — `live_seconds[step.client_id]` at
`get_task_production_time.py:get_task_production_time` and
`get_task_budget_allocations.py:get_task_budget_allocations` — but **neither site carries
a comment**. The handoff records it, and the handoff archives. This is the exact failure
N7 earned the rule for. It has a named consequence: strict indexing is a deliberate
fail-loud choice, and the obvious "fix" for a future `KeyError` is
`live_seconds.get(step.client_id, step.total_working_seconds)`, which silently restores
the settled column and masks C3's population row. D4, D5 (the unit row), D6, D8 and D9
were all honoured.

**S5 — the fourteen-row ledger was measured against a tree that no longer exists, and the
record does not say so where it will be read.** Authority: master plan §5 ("never carry a
pass count between rounds"), §7 (the cap stream's baseline clause).
The fix-r2 handoff states plainly that "the mutation runs were captured against the clean
pre-probe tree at **26 failed / 2474 passed / 1 deselected**", while the delivered tree is
**2476** — the two cap tests landed underneath the sweep. Every one of the fourteen rows
is therefore an observation on a superseded tree; row 4 is the row where that became
visible, not the only row it applies to. My three-row sample reproduces ID-for-ID on the
delivered tree, so the ledger is credible and I am not asking for a re-sweep. What is
owed is the record: `plans/plan_2.md` §7's fix-r2 entry should state the tree each
measurement was taken on, and row 4's added-ID set should be struck and replaced with the
coordinator's measured single ID rather than left in the artifact for someone to cite.

### NOTES

- **N1 — C5's three per-endpoint rows were collapsed into one combined row.** Plan §5 C5
  specifies three rows, one per endpoint, each doing dirty-check → `expire_all()` →
  re-read. What shipped serves all four endpoints and then does the sequence once. I
  traced every case: an assignment at E-P, E-B or E-B-worker is autoflushed by the next
  endpoint's `session.execute()` and caught by the re-read; an assignment at E-A (the last
  served, with no execute after it) is caught by the dirty check. No hole — the ledger's
  5-ID result, which I reproduced, confirms it bites. Diagnosis only: a single failure
  will not say which surface persisted.
- **N2 — C12's E-P and E-A halves are vacuous by construction.** C12 claims zero
  `_common` clock reads on "E-B (both faces), E-P and E-A". E-A no longer imports
  `today_utc` at all, and E-P is served on a task holding a committed evaluation, so
  `get_task_budget_status` returns through `_build_evaluated_status` and never reaches
  `_load_preview_inputs`. The two real call sites (`get_task_budget_status`,
  `get_task_budget_status_worker`) are both genuinely covered on the `unevaluated_task`
  branch, so the criterion is satisfied where it can be — the plan's four-surface phrasing
  just over-claims what is provable.
- **N3 — D5's stub comment is beside the wrong stub.** The comment naming the
  module-bound `datetime` choice sits in
  `test_c11_typicals_statement_uses_the_request_clock_when_supplied`; the actual
  `monkeypatch.setattr(typicals_module, "datetime", NoClock)` is in
  `test_c11_c12_surface_call_sites_do_not_fall_back_to_module_clocks` and carries none.
- **N4 — `typical_times_statement` branches on truthiness where its twin branches on
  `is None`.** `cutoff = (now or datetime.now(timezone.utc)) - …` versus
  `_common.py:_load_preview_inputs`'s `now.date() if now is not None else today_utc()`.
  Inert (`datetime` instances are always truthy) and I am not asking for a change on
  behavioural grounds — but D4 granted **one form for both shims** so the codebase would
  not grow two conventions for one construct, and it now has two.
- **N5 — the price-scenario cost regression landed as intention §4.1A D predicted.**
  `get_task_price_scenario.py:get_task_price_scenario` calls `get_task_budget_status(ctx)`
  with no map, so the shipped valuation endpoint now pays a step load plus the loader's
  probe per request. I confirmed at source and on the payload that it consumes only
  `budget_status.status` and `budget_status.item_binding` — **no worked-derived key
  reaches the price-scenario payload**, so §2.6's claim holds. Plan §6's cost note lists
  E-B standalone and the worker face but not this fourth caller; worth adding at closeout.
- **N6 — `test_c11_typicals_statement_uses_the_request_clock_when_supplied` is marked
  `@pytest.mark.unit`** while living in `tests/integration/…`.

## 5. What I verified correct (settled ground for the next round)

- **Production code matches plan §3/§4 file by file.** The `func.sum` aggregate is deleted,
  not kept; `_build_evaluated_status` branches on `live_seconds is None` (D9); E-P loads
  steps first then threads one map (D8); E-A makes one batch loader call before its task
  loop and resolves `selection_date = ctx.now.date()` once above it; E-A gained **no**
  `selectinload`; both substitution sites use
  `budget_division._loaded_latest_state_record(step)`.
- **Population equality across all four surfaces.** E-P, E-A and `_build_evaluated_status`
  each select `workspace_id + task_id + is_deleted.is_(False)` with **no state filter** —
  the three step sets coincide, so §4.1A A's headline-equals-rows property holds by
  construction and not by luck.
- **HC-5 on the payloads, not the fold.** I served E-P, E-B manager, E-B worker and E-A
  against one fixture and compared field by field. All four report
  `actual_worker_seconds = 2040`; `actual_worker_minutes = "34.00"`,
  `remaining_worker_minutes = "-14.00"` and `percent_consumed = "170.00"` agree wherever
  they appear; E-P's `Σ sections[].worked_seconds` and E-A's `Σ steps[].worked_seconds`
  both equal the headline. **No derived field disagrees.** The two known D9 sites behave
  exactly as disclosed — E-P's `final.percent_consumed` and the worker face's
  `result.percent_consumed` both read `"170.00"` (live) inside blocks whose other members
  are frozen at `"20.00"` / `"0.00"`; that is plan 3's work and is not a finding here.
- **HC-1A on the E-A path, structurally.** `DivisionStep` is a `frozen=True` dataclass;
  E-A constructs it purely from reads, `_loaded_latest_state_record` inspects
  `step.__dict__` without emitting SQL or writing, and nothing between the step load and
  `serialize_budget_allocations` assigns any `TaskStep` attribute. Nothing in the batch
  path can write a step attribute, including through `DivisionStep` construction.
- **Charter 11½ on the C9 fixture — no teardown is owed.** `_apply_step_transition` does
  add a `PROCESS_STEP_TRANSITION` outbox row, but its docstring's claim is accurate and I
  confirmed it: it "does not commit". The phase file contains **zero** `commit()` calls;
  every fixture is flush-only, and `tests/conftest.py:db_session` is rollback-scoped. The
  outbox row, the closed record and the recomputed totals all roll back with the session.
- **C9's three-point contract is not satisfiable wrongly by any phase-2 change.** Working
  through it: a fold that read the settled column would give `1440` at point 1; a fold that
  skipped the recompute would miss point 3; a loader call at the wall clock instead of
  `ctx.now` moves point 1 by hours. The one substitution that satisfies all three is
  replacing the concurrency-averaged share with a naive `now − entered_at` elapsed — the
  fixture has one credited user and one open record, where the two coincide. That is HC-2,
  proven at loader level in phase 1 with multi-user fixtures (T3/T4), so it is not this
  phase's row to carry. **N5's judgment stands: C9 correctly names no production mutant.**
- **C1's goldens are read-only in this phase's diff** and green; both golden tasks hold one
  step in one section, confirmed at source.
- **C10's seven-suite perimeter** is green on my run, including `test_price_scenario_query.py`
  and the phase-9 structural test whose `_SITES` line-number ids are stale-but-inert as the
  plan predicted.
- **C3's population row is absolute and live-discriminating** (`840` contract; settled-only
  would read `240`, the excluded-filter mutant `600`).
- **C8's batching is proven at three tasks**, and its two rows are the ones row 6's mutation
  reddens — the identity-element defect from implement r1 is genuinely closed.

## 6. Lessons for the plans

- **Intention (`planning/intention.md` §4.1A C).** The claim that `allowance_seconds` is
  non-worked-derived is true only while no *excluded* step holds an open working record —
  `charged_seconds` sums `total_working_seconds` over excluded steps, which is now a live
  figure. It holds today because `_apply_step_transition` always closes the open record.
  Add the precondition to §4.1A C as a lettered clause rather than leaving it implicit in
  plan 2's C6 prose, because §4.1A C is what phases 3–4 will cite.
- **Master plan §5 — a new rule to earn.** *A criterion that pins an outcome must be placed
  where the outcome's controlling term is non-degenerate, and the degenerate value is not
  always the addend.* Eight prior instances of this class were about identity elements of
  the arithmetic (`settled = 0`, `∅` for a union). B1 is the ninth and it is a new shape:
  the fixture's arithmetic is fine and the **allowance** is degenerate at 0, so a
  comparison-based verdict (`worked > allowance`) returns the same answer on both sides.
  Compute the *verdict* under both bases before writing the row, not just the values.
- **Master plan §5 / §7 — the external-stream clause needs one more sentence.** §7 already
  says every round re-measures its baseline. What bit here is narrower: a **multi-hour
  mutation sweep** is not a round, and a foreign commit can land inside it. Ledger rows
  must record the tree they were measured at, and a sweep that spans a foreign commit is
  re-based, not annotated. This is the concrete form of the hazard §7 anticipated.
- **This plan (`plans/plan_2.md` §5).** Four criteria — C2, C4, C6 row 1, C7 — are written
  as a headline sentence followed by subordinate clauses, and in all four the headline
  shipped and the clauses did not. The criteria are not at fault; the shape is. Where a
  criterion carries more than one contract, give each its own lettered row with its own
  named mutation, the way C6's rows 2–4 are written — those three shipped completely.
- **Next phase (`plans/plan_3.md`).** Phase 3 edits both payload builders. B1(b)'s
  byte-identity row should exist before that work starts, since it is the only guard that
  would see an open-record determinism regression in a serializer; the goldens cannot.
  Also carry N2's observation: when plan 3 writes T13, name the branch each surface
  actually reaches rather than listing surfaces.

## 7. Mutation-probe declaration

Every probe applied and reverted; all reverts verified byte-identical against `HEAD` by
`sha256`, and `git status` is empty.

| File | sha256 (worktree == `HEAD`) |
|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_production_time.py` | `091cd1f55fbac1249336cd22aae25cc75868c8fda31b6387c55ae0b4dd2fd236` |
| `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` | `fbbe9c9eb1efcc3847cab05ffee2ad7aed5b7ee9b8c2de5f5d73e56c4fb6612d` |
| `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` | `ce483a7913ca9c6814bf3cf8335c8720b68db797ba25f3b4671bd760f91e325d` |

One temporary probe file was created and **deleted**:
`app/tests/integration/services/queries/item_economics/test_zz_reviewer_r3_probe.py`
(the HC-5 payload dump and the two-serve determinism measurement). It asserted nothing,
committed nothing, and its `__pycache__` artefact was removed.

**Database/state side effects: none.** Every probe ran through the suite's rollback-scoped
`db_session`; no probe committed a row, and no fixture was left behind. Four whole-suite
runs total (1 clean + 3 mutants) plus one single-file probe run.

**No archgraph review item was promoted, rejected or edited.**

## 8. Write perimeter

`git status` / `git diff --name-only` after this session: **exactly one file**, this
handoff —
`docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/handoffs/reviewer/2026-08-20_phase2_review_r3_handoff.md`.

No code, no plan edit, no tracker row, no graph write.
