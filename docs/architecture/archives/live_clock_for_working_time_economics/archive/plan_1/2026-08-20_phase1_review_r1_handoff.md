---
plan: 1
role: reviewer
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-20
actor: Claude Opus 5 (1M context)
---

# Phase 1 review (round 1) — `live_clock_for_working_time_economics`

**Verdict: CHANGES_REQUESTED.** 2 blocking, 2 should-fix, 7 notes.

The shipped code is, as far as this review could establish, **correct**. Every
arithmetic result I re-derived by hand matched, the loader delegates averaging to
the one shared rule, and it provably cannot write to an ORM attribute. What fails
is the *proof*: two of the loader's defining contracts — the `settled +` term and
the `int(round(·))` output — have no test that can fail on their absence. I
deleted each of them from the production code and ran the whole suite: both times
the result was exactly the baseline **26 failed / 2454 passed / 1 deselected**,
with an **empty** added-ID set. Plan 1's stated goal is the loader "with its full
contract proven at loader level" (§1); the two most load-bearing terms of that
contract are not proven, and phase 2 wires this function into all three
money-bearing surfaces.

The P1 probe resolved in the implementer's favour and then some: the naive-`now`
boundary guard is not an unjustified addition — it is the **only** loud path.
Intention §1A HC-3A's claim that the `TypeError` fires "inside
`concurrency.py:_sweep`" is **false as shipped**, measured three ways below.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Every finding is a coordinator/implementer fold; nothing here needs an
owner answer.

---

## 1. Blocking

### B1 — the loader's defining equation `live = settled + share` has no test that can fail

- **Site.** `live_worked_seconds.py:load_live_worked_seconds` — the returned dict
  comprehension (`settled_seconds + live_by_step.get(step_id, 0)`).
- **Authority.** Intention §3.1 and §3.1A A:
  `live_worked_seconds(s, now) = s.total_working_seconds + int(round(open_share))`.
  `plans/plan_1.md` §1 Goal ("its full contract proven at loader level") and §4
  task 3 bullet 5 ("every input step keyed in the output; steps with no open
  working record map to their settled column as `int`").
- **What is wrong.** Every fixture in
  `test_live_worked_seconds.py` leaves `_add_step_record`'s `settled` parameter at
  its default `0`; the only explicit use in the file is `settled=0`
  (`test_c10_loader_never_persists_live_seconds_on_task_step`). With the settled
  column pinned at addition's identity element, the `+` is invisible to every row.
  There is also **no row at all** for "a step with a non-zero settled column and no
  open working record" — the case plan §4 task 3 names explicitly.
- **Measured.** Reviewer mutation, definition site, whole suite: replace
  `settled_seconds + live_by_step.get(step_id, 0)` with
  `live_by_step.get(step_id, 0)` (delete the settled term entirely) →
  **26 failed / 2454 passed / 1 deselected**, added ID set **∅**. Reverted, loader
  hash `6d11b922…fa82ca`.
- **Correction.** Two rows with `settled != 0`: (a) a step with a non-zero settled
  column **and** an open working record, asserting `settled + share`; (b) a step
  with a non-zero settled column and **no** open record, asserting exactly the
  settled value. Register the named mutation "drop the settled term ⇒ both rows
  redden", both sides computed, site named as definition-site.

### B2 — the `int` output type and the rounding locus have no test that can fail

- **Site.** `live_worked_seconds.py:load_live_worked_seconds` —
  `live_by_step[contribution.step_id] += int(round(contribution.seconds))`.
- **Authority.** §3.1A A (round the **share**, `int(round(·))`, Python half-even —
  "the difference is one second at exact halves, which is precisely the width of
  the §3.3 bound") and §3.1A B (a float output is truncated by `int()` in four
  `budget_division.py` sites and raises `ValidationError` through
  `calculator.py:_require_seconds(..., exact=True)` on the money path — "a payload
  whose rows are truncated and whose headline is a 500"). Plan §4 task 3 bullet 5:
  "output values are `int`".
- **What is wrong.** Two independent reasons the rows cannot bite. First,
  `1800.0 == 1800` is `True` in Python and dict equality compares values with
  `==`, so every `assert result == {...}` row passes unchanged against a
  float-returning loader. Second, no fixture produces a share that lands on an
  exact half-second, so half-even versus half-up versus truncation are
  indistinguishable across all 17 rows.
- **Measured.** Reviewer mutation, definition site, whole suite: replace
  `int(round(contribution.seconds))` with `contribution.seconds` (drops both the
  rounding and the cast) → **26 failed / 2454 passed / 1 deselected**, added ID set
  **∅**. Reverted, hash-verified.
- **Correction.** (a) An explicit type row —
  `assert all(isinstance(v, int) for v in result.values())` — which `==` cannot
  express. (b) One row whose exact share lands on a half-second (a two-way batch
  split of an odd second count, per §3.1A A / §4.1A), asserting the half-even
  result, so the locus is discriminated. Register the mutation "return the raw
  float ⇒ the type row reddens" and "`math.floor(x + 0.5)` ⇒ the half-second row
  reddens", both sides computed.

---

## 2. Should-fix

### S1 — the C9 naive-`now` row asserts a mechanism that cannot fire; HC-3A's failure site is wrong

This is P1, resolved. The guard is **sound, load-bearing, and mutation-covered**;
what is defective is its name and the upstream contract sentence.

- **Sites.** `test_live_worked_seconds.py:test_c9_naive_now_fails_loudly_inside_the_sweep`;
  `live_worked_seconds.py:load_live_worked_seconds` (the opening `TypeError`
  guard).
- **Authority.** Intention §1A HC-3A: "A naive `now` raises `TypeError` inside
  `concurrency.py:_sweep` at `(end - interval.entered_at)`; this is the one
  mechanism in the feature that fails loudly." Plan C9: "raises `TypeError`
  **inside the sweep**".
- **Measured, three ways** (all probes reverted, hash-verified):
  1. **Guard deleted, with an open working record present** — the case the plan
     assumed would raise anyway. `load_live_worked_seconds` returned
     `{step: 0}`. **No raise.** The live term vanished silently.
  2. **Guard deleted, with no open working record** — returns settled silently
     (trivially; the per-user loop never runs).
  3. **Direct probe of the SQL boundary.** Calling
     `averaged_time.py:compute_record_contributions` with a naive `window_end`
     against a fixture whose aware-bind counterpart returns 1 row returned
     **0 rows and no error**: asyncpg/Postgres accepted the naive bind and
     silently shifted the `entered_at < window_end` boundary. So the rows never
     reach `_sweep`, and `(end − interval.entered_at)` never executes.
  4. **Whole-suite mutation "delete the loader's boundary guard"** (definition
     site): **27 failed / 2453 passed / 1 deselected** =
     `B ∪ {test_live_worked_seconds.py::test_c9_naive_now_fails_loudly_inside_the_sweep}`
     — exactly one added ID. The guard **is** covered by its row.
- **Assessment (doctrine rule 6).** The implementer's justification was directionally
  right and understated: they wrote that asyncpg "normalizes a naive bind value at
  the SQL boundary". It does — and the consequence is not that the guard *preserves*
  a contract that would otherwise hold elsewhere, but that **without the guard the
  feature's single loud mechanism becomes silent**, dropping the live term with no
  error, no log and no failing test. That is rule-6 surface behaving exactly as the
  charter warns. The addition should be absorbed, not merely tolerated.
- **Correction (this phase).** Rename to
  `test_c9_naive_now_fails_closed_at_the_loader_boundary` and add a docstring
  recording that the sweep cannot raise because the driver normalizes the naive
  bind first (cite the 0-rows observation). A test name asserting a false property
  is a claim under master plan §5's comment rule.
- **Routed upstream (coordinator, do not edit from here).** Intention §1A HC-3A's
  Type bullet should absorb *"the loader fails closed at its own boundary"* as the
  contract and retire the `concurrency.py:_sweep` failure-site claim; plan C9's
  wording follows. Register the named mutation with the red set measured above.

### S2 — the deleted-record row is missing the docstring its criterion requires

- **Site.** `test_live_worked_seconds.py:test_c4_deleted_record_is_excluded_defensively`.
- **Authority.** Plan C4: "`is_deleted` record ⇒ 0 (**docstring**: no shipped
  writer, defense-in-depth, §3.1A D)". Intention §9A T4: "the row is
  defense-in-depth, which the criterion should say so a reviewer does not go
  looking for the writer."
- **What is wrong.** The test has no docstring at all. The name carries
  "defensively" but not the fact that no shipped command sets the flag, which is
  the half that saves the next reader a search.
- **Correction.** Add the docstring, naming
  `reset/phases/delete_step_state_records.py` (a hard workspace-wide `DELETE`) as
  the only writer, per §3.1A D.

---

## 3. Notes

- **N1 — P5, the zero-cases row's two predicates, both measured.** The row carries
  two steps. *Missing-attribution half:* reviewer mutation removing
  `if user_id is not None:` (definition site) → whole suite
  `B ∪ {test_c4_zero_cases_future_entry_and_missing_attribution_are_skipped}`,
  exactly 1 added ID ⇒ load-bearing. (It bites because
  `func.coalesce(...) == None` renders as `IS NULL`, so the un-attributed record
  *is* fetched and earns 600.) *Future-entry half:* no loader-side mutation
  isolates it — the mechanism lives in the wrapper's strict
  `entered_at < window_end` and `_sweep`'s `duration <= 0`. It reddens only under
  the coordinator's mutation-3 **both-args** shape, and there it is the `future`
  step's assertion that moves (the `missing` step reads 0 under every shape).
  Both halves therefore bite, on different mutations. Recommend the docstring
  record which mutation answers to which half, per charter rule 2's companion.
- **N2 — P4, attribution is Python `or`, and that is the parity-preserving choice.**
  The loader groups by `record.credited_user_id or record.created_by_id`; §3.1 and
  §3.1A specify `COALESCE`. They differ only on `credited_user_id == ""`. Scope of
  the equivalence, verified at source (search term `credited_user_id`, swept across
  `app/beyo_manager/`): the column carries **no FK** by design
  (`step_state_record.py`, the comment above the mapping), so `""` is writable at
  the DB level; but every shipped writer passes `ctx.user_id` or
  `request.credited_user_id or ctx.user_id`
  (`transition_step_state.py:_resolve_transition_credit_user_id`,
  `transition_step_state_batch.py`, `_step_transition_core.py`,
  `force_task_ready.py`, `_case_created_step_pause.py`,
  `finalize_pending_step_completion.py`), and `ServiceContext.user_id` returns
  `""` only when the JWT carries no `user_id` claim — which the `or` in the
  resolver already collapses. **Decisive:** settlement itself uses the identical
  Python `or` — `process_step_transition.py:_recompute_step_time_totals`
  (`uid = r.credited_user_id or r.created_by_id`) — and feeds it into the same SQL
  `COALESCE` filter. Matching settlement is what HC-2 / §3.3 parity requires; a
  literal SQL `COALESCE` in the loader would have *diverged* from settlement on
  exactly that value. **No code change.** Recommend §3.1/§3.1A say "the same
  attribution settlement uses — `credited_user_id or created_by_id`, matching
  `_recompute_step_time_totals`" rather than `COALESCE`.
- **N3 — P2, C7's `90900` re-derived by hand; A9's constraint holds.** Segments
  against `concurrency.py:_sweep`: `[08:30, 09:00)` k=1 (closed record only);
  `[09:00, 09:30]` k=2 ⇒ A +900; `[09:30, 01-02 10:00]` k=1 ⇒ A +88 200;
  `[10:00, 11:00]` k=2 ⇒ A +1800. A = 900 + 88 200 + 1800 = **90 900** ✓.
  A9's separation constraint: the closed record's `exited_at` (2026-01-01 09:30)
  precedes `max(entered_at) − 1 day` (2026-01-02 10:00 − 1 day = 2026-01-01
  10:00) ✓ — so under the `max` anchor the closed record is dropped by the window
  and A = 90 000 + 1800 = **91 800**, which is why the ledger's 1-ID red set is
  right. The row asserts only `first`; asserting `second == 1800` as well would be
  free and would pin the second open record.
- **N4 — P3, the golden composition walked against plan task 1; conforms.** Two
  task keys per file (`idle_no_result`, `frozen_no_drift`) ✓; E-B both faces at
  their own serialization sites (`serialize_task_budget_status` with
  `include_monetary=True` / `False`) ✓; E-A **one single-task call per task**
  (`query_params={"task_ids": [task_id]}` inside the per-task loop — never
  batched) ✓; fixture (c) — both steps hold an open `PENDING` record ✓; both
  required docstring rationales present (typicals invariance; the D9 no-drift note
  on fixture b) ✓. Typicals invariance holds for a **stronger** reason than the
  plan states: besides no `COMPLETED` step and `closed_at` NULL, the fixture's
  `working_section_id` (`wsec_live_clock_golden`) is unique to the flush-only
  fixture, so `get_working_section_typical_times.py:typical_times_statement`'s
  COMPLETED grouping cannot see another test's rows at any run date; the captured
  goldens show `sample_count: 0`, `typical_worker_seconds: null` ✓. Assertion
  liveness confirmed: a one-byte flip in `golden_production_time.json` reddens the
  row (probe reverted). Goldens-first sequencing independently re-verified from
  the checkpoint's own content — `git diff --name-only 08fc141..1081a2b` is
  exactly the three goldens plus their test.
- **N5 — P6, teardown audit: clean, nothing owed.** No test in either phase file
  commits. `tests/conftest.py:db_session` is rollback-scoped and D3's flush-only
  golden fixtures ride it. C5's close path is
  `_step_transition_core.py:_apply_step_transition`, whose docstring says "Does
  not commit and does not dispatch realtime events" — verified at source (two
  `session.flush()` calls, no `commit`); its
  `services/infra/execution/task_factory.py:create_instant_task` contains no
  `commit` either. `_recompute_step_time_totals` (lines 185–260 of
  `process_step_transition.py`) contains no commit; the module's only
  `await session.commit()` sits inside `handle_process_step_transition`, which no
  phase test calls. Charter 11½ has nothing to bind on here.
- **N6 — P7, graph delta verified; one summary carries a count.**
  `archgraph_status`: 188 nodes / 280 edges, **0 diagnostics, 0 stale, 3 pending**,
  revision `9e29e830…` matching the handoff's claim. The three pending items are
  exactly the declared node plus its two edges; both edge targets resolve to
  existing nodes (`table-step-state-record` at line 758,
  `src-compute-record-contributions` at line 2168 of `.archgraph/architecture.yml`).
  Evidence anchors carry `symbol: load_live_worked_seconds` and resolve
  (`staleNodeCount: 0`). The recorded shape matches what shipped (client-id-keyed
  mapping, per-worker grouping, min-entered-at anchor, no ORM mutation). **Nit for
  the owner's adjudication:** the `reads_from` edge summary says "issues **one**
  batched probe" — a count inside a summary. Also verified rather than assumed: no
  `ServiceContext` node exists in the graph, so N-1 owed no delta. No item was
  promoted, rejected, edited or removed by this session.
- **N7 — D1's choice is recorded only in a document that archives.** Plan §6 D1
  grants the implementer the row-3 durations "recorded in the test beside the row".
  `test_c3_row_3_cross_task_open_record_is_in_the_divisor` carries neither comment
  nor docstring; the choice (two overlapping 30-minute cross-task records ⇒ 900) is
  recorded only in the implementer handoff. Master plan §5 — "'record the decision'
  names its post-closeout medium … never only a handoff, which archives" — applies.
  One comment line fixes it.

---

## 4. Verified correct (so the re-review can skip these)

- **C1** — full suite re-run by this reviewer on a clean tree at `76bc58e`:
  **26 failed / 2454 passed / 1 deselected** (127 s); failure IDs extracted and
  `diff`ed against master plan §6's enumerated set — **identical, zero delta**.
  Neither named flaky test appeared, so no repeat was owed.
- **C2** — composition, liveness and sequencing all verified (N4).
- **C3** — row 1: both steps `allows_batch_working=True` (the `_add_step_record`
  default) and credited to two distinct users, so the distinct-users predicate is
  the only reason 1800/1800 holds — the same-user counterfactual is 900/900 per
  A8. Rows 2 and 4 re-derived independently against `_sweep` and match §3.2A's
  1500/300 and 1200. Row 3 matches D1's granted shape.
- **C4** — all five rows present; the step-flag row carries **both** assertions
  (`marked: 0` and the sibling rising 300 → 600, §6A E3). Exclusions otherwise
  sound: a marked-wrong record is fetched by the probe but earns `0.0` through
  `averaged_seconds_by_record`'s flagged-interval drop, so the loader needs no
  second filter.
- **C5** — both rows use the plan's pinned close path,
  `_apply_step_transition(..., now=t)`, with exactly the pinned argument set
  (`new_state=PAUSED`, `credited_user_id` of the fixture worker,
  `pause_reason_id=None`, `transition_reason=None`), then call
  `_recompute_step_time_totals` directly and assert `|live − column| ≤ 1`
  **per step**. The single-open-record row's §9A precondition holds by
  construction: `_seed_workspace` mints a fresh workspace *and* a fresh user per
  test, so that worker holds no other open interval anywhere.
- **C6** — the deleted step's open batch record still halves the live sibling
  (300, not 600), and the deleted step is absent from the output (§3.1A F, T10).
- **C7** — 90 900 re-derived; A9's constraint honoured (N3).
- **C8** — determinism across two identical calls, plus `calls == []` against a
  +5 s advancing stub. The stub is genuinely load-bearing: it reddens under the
  ledger's mutation 3.
- **C9** — three of four rows verified: aware-UTC type, explicit `now=` honoured,
  and the A6 stubbed default-stamp row proving the stamp is evaluated *per
  construction* (`first.now == T0`, `second.now == T0 + 1s`, `calls == [UTC, UTC]`),
  with the pre-patch construction kept out of the call log. Fourth row → S1.
- **C10** — the A7 assertion order is honoured exactly, and the row is **stronger
  than the criterion requires**: an assignment made *before* the probe's
  `session.execute` would be autoflushed (emptying `session.dirty` and defeating
  step 1), but step 3's post-`expire_all` re-read catches that ordering too. Both
  variants covered.
- **HC-1A, structurally** (doctrine rule 3): the loader contains **no assignment
  to any attribute of any ORM object**; `steps` are read for `client_id` and
  `total_working_seconds` only. This is stronger than the passing test.
- **HC-2**: averaging is delegated to `compute_record_contributions`; the file
  contains no second averaging rule and no `now − entered_at` elapsed anywhere.
- **N-1 / N-3 conformance**: `ServiceContext.now` exactly as registered, Rules
  block extended, and nothing else in `context.py` touched; the loader's name,
  home, signature and return type match the registry.
- **The window anchor over *probed* records** (not over all of the user's open
  records, which is what intention §3.1 says) matches plan §4 task 3's own wording
  and is provably sufficient: any record that can alter a probed record's share
  overlaps `[min(probed entered_at), now]`, hence has `exited_at > W_start` or is
  open and fetched unconditionally. Verified by derivation, not assumed.
- **Write perimeter**: `git diff --name-only 08fc141..a7659bc` is the eight
  code/graph items; `plans/plan_1.md` and the handoff arrive in `ecd24e8`. Equals
  the declared ten exactly, nothing outside.

---

## 5. Lessons for the plans (coordinator folds these upstream)

1. **A criterion set that never varies an input cannot test the term that consumes
   it.** Every C3–C10 fixture pins `total_working_seconds = 0` — addition's
   identity element — so the loader's `settled +` term is invisible to all 17
   rows. Plan §4 task 3 enumerated the contract; plan §5 did not mirror it as a
   criterion. **Rule to add: every term of a defining equation gets a criterion
   that varies it away from its identity element** (0 for addition, 1 for
   multiplication, the empty set for a union). A fixture sitting at the identity
   element makes the operator untestable while the row's name says otherwise.
2. **Equality assertions do not test types in Python.** `{k: 1800.0} == {k: 1800}`
   is `True`. A criterion naming an output type (§3.1A B) requires an explicit
   `isinstance` row; a value row can never carry it. Companion to rule 2.
3. **A "fails loudly" claim is a mechanism claim and inherits the mutation rule.**
   HC-3A named the failure site (`concurrency.py:_sweep`) without probing it; on
   the configured driver the rows never reach the sweep, so the named site cannot
   fire and the true behaviour is a silent wrong answer. **Rule: a contract that
   names *where* a failure surfaces must be probed at that site before it ships as
   a contract** — the same discipline charter rule 11 already imposes on named
   mutations. This is the third pipeline in which an unmeasured claim about a
   mechanism's *site* survived a gate.
4. **The P1 extraction worked and should be kept.** The coordinator's consumption
   pass flagged the guard as an unplanned semantic addition rather than waving it
   through; the probe converted "sound but under-justified" into a corrected
   upstream contract plus a measured named mutation. Keep converting semantic
   additions into probes with a fold-back obligation.
5. **Delegation grants need a post-closeout medium.** D1 said "recorded in the test
   beside the row" and the record landed only in the handoff (N7). D-grants should
   say "as a comment in the test", per master plan §5.

---

## 6. Carry-forward dispositions

Not applicable at this verdict — the notes return with the fix cycle rather than
crossing a phase boundary. If the coordinator approves after r2 with N1–N7 still
open, N2 (intention §3.1/§3.1A `COALESCE` wording) and N6 (graph summary count)
are the two that must be routed to **phase 4** (the closeout / graph-delta phase);
the rest are phase-1-local and die with the fix.

---

## 7. Mutation-probe declaration and write perimeter

**Every probe applied by this session, and its revert.** All four production-code
mutations were applied at the definition site in
`app/beyo_manager/services/queries/item_economics/live_worked_seconds.py`, run
against the **whole** non-e2e suite, then reverted with `git checkout --` and the
file's SHA-256 re-verified as
`6d11b922fbec3031be49adf1313b6d1685bef95659caf81f2b6cb7e918fa82ca` — byte-identical
to the implementer's recorded revert hash.

| # | Mutation (all definition site, the loader) | Whole-suite result | Added vs baseline | Reverted |
|---|---|---|---|---|
| R1 | Delete the naive-`now` boundary guard | 27 / 2453 / 1 | `{test_c9_naive_now_fails_loudly_inside_the_sweep}` (1) | ✓ hash verified |
| R2 | Remove `if user_id is not None:` from the attribution grouping | 27 / 2453 / 1 | `{test_c4_zero_cases_future_entry_and_missing_attribution_are_skipped}` (1) | ✓ hash verified |
| R3 | Drop the settled term (`settled_seconds + …` → `…`) | 26 / 2454 / 1 | **∅** | ✓ hash verified |
| R4 | Drop `int(round(·))` (`+= int(round(c.seconds))` → `+= c.seconds`) | 26 / 2454 / 1 | **∅** | ✓ hash verified |

Baseline for the `B ∪ Δ` notation above is master plan §6's enumerated 26-ID set,
re-measured and `diff`ed by this session as identical.

**Fixture probe (focused, not whole-suite).** One byte of
`app/tests/integration/services/queries/item_economics/goldens/golden_production_time.json`
was flipped (`"worked_seconds":600` → `601`) to confirm the golden assertion is
live; it reddened
`test_live_clock_goldens.py::test_prechange_payloads_match_byte_golden_files`.
Run focused rather than whole-suite on the ground that the three golden files are
read by exactly one test (`GOLDEN_DIR` is referenced nowhere else in the tree), so
the mutation's reach is bounded by construction. Restored with `git checkout --`.

**Temporary file, created and deleted.**
`app/tests/integration/services/queries/item_economics/test_zzz_reviewer_probe_p1.py`
— the three P1 diagnostic probes (naive `now` with an open record; naive `now`
without one; a naive `window_end` bind straight into
`compute_record_contributions`). Deleted before the mutation suites were run; it
appears in no commit.

**Database / state side effects.** None beyond the suite's own. Every probe ran
through the rollback-scoped `tests/conftest.py:db_session`; no manual writes, no
migrations, no `archgraph` mutation (status and `list_pending_reviews` are reads).

**Write perimeter of this session** — `git status --porcelain` is **empty** and
`git diff --name-only HEAD` is **empty** at `76bc58e`. The only file this session
adds to the repository is this handoff:

- `docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/handoffs/reviewer/2026-08-20_phase1_review_r1_handoff.md`

No code edit, no plan edit, no master-plan tracker row — per §6 of the review
prompt, those are the coordinator's.
