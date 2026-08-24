---
plan: plan_1
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-24
actor: Codex
---

# Phase 1 review round 1

Phase 1's production rule is semantically correct and its full-suite result matches the
published baseline. The phase is not approved because one test does not enforce the fixture
shape it names and the mutation ledger overstates assertion-level reach. Both defects are
contained to phase-1 tests/evidence; no product decision is needed.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs an owner decision. The gate holds while the implementer repairs the two
contained review findings below.

## Verdict

`CHANGES_REQUESTED` — zero blocking findings, two should-fix findings, zero notes.

## Findings

### REV-01 — should-fix — C4(e) does not prove its excluded-row fixture

**What is wrong.** `test_c4e_excluded_allocator_rows_have_no_commitment_or_work_ahead`
constructs the intended allocator fixture, but asserts only the two aggregate predicates
(`test_budget_signal.py:339-349`). The clean fixture currently emits two real rows —
`A/excluded/None` and `B/excluded/None` — yet the test remains green after either of two
review mutations: clearing `division["sections"]`, or replacing both excluded step states
with `completed`. The assertions therefore do not prove that excluded allocator rows are the
reason the result is `(0, False)`.

**Authority.** `plans/plan_1.md` C4(e) and task 0; `planning/intention.md` §12A P3;
pipeline charter standing rules 2 and 15.

**Correction.** Make C4(e) assert the allocator precondition before the aggregate result:
the exact non-empty `A`/`B` row set, `share_state == "excluded"`, and `left_seconds is None`.
Add a named mutation that changes/removes that shape and must redden at the precondition
assertion; record its exact node ID and assertion line.

### REV-02 — should-fix — the mutation ledger is ID-complete but not assertion-complete

**What is wrong.** The plan and implementer handoff each contain all 35 distinct mutation
IDs, but the handoff table records criterion labels rather than the required exact pytest
node IDs and first failing assertion lines (`implementer handoff:143-184`). This masks two
concrete overclaims:

- MUT-14 is reported as reaching C5(e)'s seconds and cost checks. Under a negative incurred
  pair, pytest stops at `over_seconds == 0` (`test_budget_signal.py:407`); neither cost
  assertion executes. Review variations separately planted a negative seconds/cost pair
  (first failure line 407) and a negative cost alone (first failure line 408). The final
  `over_cost_minor >= 0` at line 409 can never fail independently after the preceding
  `over_cost_minor == 0` succeeds.
- MUT-30 is reported as reaching C8(d)'s assignment and frozen-metadata assertions. Removing
  the frozen decorator fails the `pytest.raises(FrozenInstanceError)` block first
  (`test_budget_signal.py:725-726`), so line 727 is not reached.

**Authority.** `plans/plan_1.md` ordered task 3 and §6.1 rule-12 sentence; pipeline charter
standing rule 12.

**Correction.** Split the independent sub-checks and give each a mutation that reaches its
own assertion. Remove or reshape the redundant C5(e) non-negative assertion so it can fail
for its own reason. Rebuild the ledger with exact pytest node IDs and first failing assertion
locations; report only observed reach.

## Verified-correct ground

- Gate inputs passed: master tracker `REVIEWING`; phases 2–3 `NOT_STARTED`; intention
  `RATIFIED`, round 10, no open owner decision; three projection folds, owner waiver and
  implementation entry present; checkpoint `6b84ef0f19f545b54fbd24157eea3964582ba1bf` exists.
- `git diff --name-status f376928 6b84ef0` is exactly the two new phase files plus master
  plan, phase plan and implementer handoff. `6b84ef0..248f8f0` changes only that handoff.
- Production and test modules match the checkpoint/implementer hashes exactly:
  `c94fec7247673c0891769246b5dadf02` and `25a11b845ae4dd071ef886fe7491645e`.
- The production module is pure and uses the fixed public API: terminal values derive from
  `TERMINAL_STEP_STATES`; the clamp is inside the commitment sum; D9's incurred and served
  clamps remain separate from D1's unclamped forecast pot; D10 is a contributing-set test;
  `over` precedes `projected_over`; all eight numeric fields are produced as exact ints;
  the sentinel/vocabulary are derived without modifying `ItemCurrencyEnum`; the dataclass is
  frozen with eight fields; and `__all__` contains only the fixed public surface.
- Both production money calls invoke the module-local `calculate_consumed_cost_minor` in
  incurred-then-projected order. A review variation reversed the calls while preserving
  returned values; C5(g) reddened on the exact ordered-call assertion. Its exact type and
  non-negative assertions execute before delegation, and bypassing the patched module-local
  callable would fail the exact two-call list.
- MUT-07 was independently applied at the task-pot operand. C3(c) observed
  `(200, projected_over)` instead of `(0, within_budget)`, proving the final probe changes
  `remaining_pot_seconds` rather than an unrelated convenient site.
- The declared mutation ID set is numerically closed (`MUT-01` through `MUT-35`) and the
  other reported bites structurally reach their named criterion tests. REV-02 is the bounded
  assertion-level exception.
- All 39 test functions trace by name and coverage map to C1–C8; no orphan test was found.

## Evidence records

### Tree identity

- `HEAD`: `248f8f0f10eff6c406c6c178930b652d7ade1396`.
- Review-entry dirty tracked-diff SHA-256 after probe restoration and immediately before L4:
  `adf87a375b496dcf468eaf7787b44a349c0cb54e9cc9f0c629676f0e0364aad5`.
- The pre-existing unrelated tracked/untracked worktree inventory was recorded before review;
  neither phase code nor phase test had a worktree delta at entry or after probe restoration.
- Implementer L1/L2 results were consumed as targeting context, not reused as tree-bound
  proof, because the review tree's document digest differs. The matching module hashes do
  establish that the implementation artifacts themselves are identical.

### Review variation probes (L1)

| Hypothesis | Command | Result |
|---|---|---|
| C4(e) rejects an empty allocator result | `PYTHONPATH=. .venv/bin/pytest -q -n 0 tests/unit/domain/item_economics/test_budget_signal.py::test_c4e_excluded_allocator_rows_have_no_commitment_or_work_ahead` after clearing `division["sections"]` | **unexpected green: 1 passed** → REV-01 |
| C4(e) rejects non-excluded terminal rows | same targeted command after changing both fixture states to `completed` | **unexpected green: 1 passed** → REV-01 |
| C5(e) distinguishes negative seconds from negative cost | targeted C5(e) command under (a) `seconds=-1,cost=-1`, then (b) `seconds=0,cost=-1` | red at line 407, then red at line 408; proves MUT-14 cannot reach both in one run → REV-02 |
| MUT-07 changes the task-pot operand | targeted C3(c) command with section-left sum assigned to `remaining_pot_seconds` | red at line 239 with `(200, projected_over)` |
| C5(g) observes production call order | targeted C5(g) command with the two money calls reversed | red at line 452; calls observed projected then incurred |

Every probe was applied one at a time and reverted before the next. Exact restored md5 values
are recorded above.

### L4 — the one authorized review-entry stamp

- Command: `PYTHONPATH=. .venv/bin/pytest -m 'not e2e'` from `app/`.
- Result: **21 failed / 2758 passed / 1 skipped** in 52.61s.
- Failing-ID additions against the documented 21-ID baseline: `∅`.
- Failing-ID removals against the documented 21-ID baseline: `∅`.
- Redis diagnostic before the run: `PONG`.
- The phase test file and domain purity guards passed inside this stamp.

## Mutation-probe declaration

Temporary review probes touched only:

- `app/beyo_manager/domain/item_economics/budget_signal.py`
- `app/tests/unit/domain/item_economics/test_budget_signal.py`

Both were restored byte-identically to the checkpoint and implementer handoff hashes. The L4
harness used its configured disposable pytest databases and completed its own teardown; no
development database, external service data, or graph state was mutated.

## Perimeter result

The implementation perimeter is clean and matches the prompt's two commit comparisons. This
review's durable write perimeter is exactly:

1. the phase-1 tracker row in `master_plan.md`;
2. one append-only entry in `plans/plan_1.md`;
3. this reviewer handoff.

All unrelated pre-existing worktree changes were preserved. No production/test mutation is
left behind.

## Architecture assessment

`archgraph_status` reported a valid initialized graph in `review` mode: 204 nodes, 308 edges,
6 stale nodes, 3 pending reviews, and no diagnostics. The review searched `budget` and
inspected the settled allocation source, task-budget allocation projection, allocation
endpoint and ADMIN/MANAGER money-audience decision. The implementer's zero-delta assessment
is correct: phase 1 adds a pure leaf with no mapped endpoint/service reach and changes no
existing architectural meaning or boundary. No graph mutation, context read/write, pending
review inspection, preview or adjudication was attempted.

Graph exploration budget: exact-node depth 0; four nodes inspected; zero nodes/relationships/
source links created; no unresolved phase-1 architecture boundary. The six stale nodes and
three pending items are pre-existing observations outside this review.

## Lessons for plans

1. A criterion whose identity depends on a fixture shape must assert that shape before its
   aggregate result and name a mutation that destroys the precondition.
2. Mutation ledgers should capture exact node IDs and first failing assertions mechanically;
   criterion-level prose invites sequential-assertion overclaims.
3. A non-negative assertion immediately after equality to zero is not an independent guard;
   either give it a fixture where sign is the only predicate or remove the redundant surface.

## Carry-forward dispositions

None. This phase is not approving with notes; REV-01 and REV-02 return to the phase-1 fix
cycle and must be closed before phase 2 starts.
