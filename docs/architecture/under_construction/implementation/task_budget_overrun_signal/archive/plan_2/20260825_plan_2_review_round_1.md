---
plan: plan_2
role: review
round: 1
verdict: CHANGES_REQUESTED
date: 2026-08-25
actor: Claude Opus 5
---

# Plan 2 review round 1 — the batched service and its serializer

First review, full checklist. The production code is correct and, on the loading half, provably
so: the new service is **token-identical** to `get_task_budget_allocations` from the cap through
the allocator call, so §3A.1's element-for-element section invariant holds by construction
rather than by fixture. Every criterion row has a test, every test has a row, all 18 named
mutations are recorded red on a tree whose hashes reproduce, and my own L4 returns the durable
21-ID set with an empty delta in both directions.

One should-fix blocks approval: **the two money fields of the ten-key row can be transposed and
the entire phase suite stays green** — measured this session, not inferred. That is the one
field-mapping class the row contract leaves unguarded, and the row contract is what this phase
exists to ship.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — correct a wrong count inside the ratified intention?

**Question:** May the coordinator correct "**eight** numeric fields" to "seven" in the ratified
intention, as a precision amendment that does not re-open the gate?

**Story:** The row you are shipping carries ten fields: three are text (the task id, the verdict,
the currency) and seven are numbers. Three places in the ratified text say there are eight
numbers, because the count quietly treats the task id as a number. Nothing built is wrong — the
code and the tests both use seven — but the next person to write a criterion from that sentence
will look for a field that does not exist, and spend a round finding out.

**Branches:** *Precision amendment* — one lettered section, gate stays RATIFIED, work continues.
*Material change* — status returns to COLLABORATING and phase 3 waits for re-ratification.

**Recommendation:** Precision amendment — it changes no meaning, and it is the same class as the
§6A.2A and round-11 corrections you already approved.

**On silence:** the gate holds; the wording stays wrong and the fix cycle proceeds without it.

**Trace:** intention §5A.2, §6A.2 row 1; master plan §6.6; plan 2 §6 C3(a), C4(b).

## Gate check

| Gate | Source | Result |
|---|---|---|
| Intention header | `planning/intention.md:3-4` | `status: **RATIFIED**` — **pass** (see N3 on the round number) |
| Plan 1 `APPROVED`, Plan 2 `IMPLEMENTED` | master plan §4 | **pass** |
| `HEAD` = `8a63402`, subject `CHECKPOINT (not approved): task budget signal phase 2` | `git log -1` | **pass** |
| No uncommitted change touches a Plan 2 executable/test file | `git status --porcelain -- app/` → empty | **pass** |

## Findings

### B1 — should-fix — no criterion can observe a transposition of the two money fields

**What is wrong.** `get_task_budget_signals.py:406-421` builds the ten-key row by copying eight
values off `BudgetSignal`. Three of the four transposition classes available in that dict are
guarded; the money pair is not. Measured on the checkpoint tree:

| Mutant (row dict, call site `get_task_budget_signals.py:406-421`) | Phase file result |
|---|---|
| `over_cost_minor` ⇄ `projected_over_cost_minor` | **28 passed — no test bites** |
| `allowed_seconds` ⇄ `actual_worked_seconds` (control) | 1 failed (`test_c7_b_open_record_moves_only_live_time_fields`) |
| `over_seconds` ⇄ `projected_over_seconds` (by inspection) | C2(b) bites — it pins `0` against `750` |

**Why every money row misses it.** The suite's three cost-bearing fixtures each make
`over_cost_minor` and `projected_over_cost_minor` *numerically equal*, so the mapping is not the
reason the expected value holds:

- C8(a) settles 3736 s ⇒ `over 136 / projected 136` ⇒ `9 / 9`;
- C8(d) settles 3608 s ⇒ `over 8 / projected 8` ⇒ `0 / 0`;
- C3(a) is the all-zero constructed row.

C2(b) is the one fixture where the two differ (`0` vs `47`) and it asserts neither cost field.

**Violated authority.** Intention §4.3 and §5.1 (`over_cost_minor` = §4.2 over `over_seconds`;
`projected_over_cost_minor` = §4.2 over `projected_over_seconds`), §5A.1 (per-field production
types and ownership — plan 2's C4 trace target), ledger **M2**. Charter rule 2's companion:
*each row's fixture makes its own predicate the ONLY reason the expected outcome holds.* This is
the seventh instance of the project's own §9 rule 7 family, in the one pair the six listed traps
do not name.

**Suggested correction.** One new criterion row and one new named mutation; the closed set
becomes **19**.

- **C8(e)** — trace **§4.3, §5.1, §4A.1 → M2**. Fixture: evaluated task, `allowed =
  Decimal("-12.50")` (raw `−750`), rate `Decimal("3.7500")`, two steps — `a` (`working`,
  section A, `total_working_seconds = 60`), `b` (`pending`, section B, `0`); no open record.
  Assert `over_seconds, over_cost_minor, projected_over_seconds, projected_over_cost_minor,
  budget_state`. Expected `60, 4, 810, 51, over` — re-derived this session through the shipped
  `calculate_consumed_cost_minor` at rate `3.7500` (`60 → 4`, `810 → 51`), not copied; the
  implementer re-derives it in Task 0 per §9 rule 3.
- **MUT-19** — `get_task_budget_signals.py`, **call site**, the row dict in the per-task loop:
  transpose `over_cost_minor` and `projected_over_cost_minor`. C8(e) must redden.

Extending C2(b) instead is **not** sufficient on its own: with `over_cost_minor == 0` the row
cannot separate "the cost of `over_seconds`" from "a constant zero" — the same weakness that
makes C8(a) blind. The fixture above is the cheapest one where both figures are non-zero and
unequal. It also lands §6A.2's "60 s logged, work still ahead" infeasible row (row 2), which no
plan-2 criterion currently reaches on the production path.

### N1 — note — "the eight numerics" is a typed count and it is wrong; there are seven

The row is three strings (`task_id`, `budget_state`, `currency`) and **seven** integers. The
count omits `task_id` from the string set. Sites: intention §5A.2 ("all eight numeric fields
`0`" — immediately above a literal carrying seven zeros) and §6A.2 row 1; master plan §6.6 ("the
eight numerics"); plan 2 §6 C3(a) ("all eight numerics `== 0`") and C4(b) (which lists three
strings *and* eight numerics — eleven fields in a ten-field row). Charter manifest property 3.

The implementation and both tests use seven and are correct; `NUMERIC_KEYS`
(`test_budget_signals_query.py:53-61`) has seven entries and C4(b) covers all of them. Note that
the implementer resolved the contradiction silently rather than declaring it (charter rule 14's
spirit) — no product consequence, recorded because an undeclared divergence costs the next
reviewer a finding on a non-defect. Correction: owner card 1, then master plan §6.6 and the two
plan-2 cells. **No criterion changes.**

### N2 — note — two assertions pass vacuously on an empty row list

`test_c4_b_row_values_have_closed_types_and_vocabularies` iterates `for row in rows` with no
cardinality assertion, and `test_c4_c_envelope_is_exact_and_rows_are_flat`'s flatness half is
`not any(... for row in result["budget_signals"] ...)`. Both are true of an empty list. Contained
— C4(a), C5(a), C5(f) pin cardinality on the same fixtures, so no single mutant escapes the file
— but each row should arm itself. Correction: add `assert len(rows) == 2` to C4(b) and
`assert result["budget_signals"]` to C4(c). Fold into the B1 fix cycle; do not spend a round on
it alone.

Related, no action: plan 2 C4(c) says "a recursive walk"; the test scans one level. Equivalent in
effect — any nested container must sit inside a depth-1 container — so no coverage is lost.
Recorded so a later reader does not file it.

### N3 — note — the intention header's round number is stale

The header reads `RATIFIED (round 10, 2026-08-24)` while §11 now carries a **round 11** ratified
amendment (the owner-approved M6 perimeter clarification) and master plan §2 cites round 11. The
gate passes on `RATIFIED`; only the round number lies. Correction: one-line header update in the
same edit as owner card 1.

### N4 — note — every plan file's `state:` header says `NOT_STARTED`, including approved Plan 1

`plans/plan_1.md:6`, `plan_2.md:6`, `plan_3.md:6` all carry `state: NOT_STARTED`. Plan 1 is
`APPROVED` and Plan 2 is `IMPLEMENTED`. Charter: state is positional and the master plan §4
tracker is the single home; a second, unmaintained copy in the plan header is a gate a future
session can read wrong — this review's own prompt sidesteps it by pointing the gate at the
tracker. Correction: delete the `state:` line from all three plan headers (the `projection_gate:`
line stays). Project-wide, not phase-2-specific; route to the coordinator, not to the fix cycle.

## Verified correct

Recorded specifically so the re-review is delta-scoped to B1's fixture and nothing else.

**V1 — the loading half is proven structurally, not by fixture.** An AST-normalized comparison of
`get_task_budget_signals` against `get_task_budget_allocations` yields exactly **four** deltas:
the function name, the error identity string, the added `.order_by(Task.client_id.asc())`, and
the tail from `if status in _BUDGET_STATUSES …` onward. Everything between — the raw-list cap,
the three-clause visibility predicate, all eleven batch loads, the status resolution *including
the no-evaluation branch* (§6A.1A, structurally held ✓), the `(sequence_order is None,
sequence_order, client_id)` step sort, `DivisionStep` construction with **strict**
`live_seconds[step.client_id]`, the whole narrowing/typicals evidence block,
`reconcile_task_typicals(...).selected`, and `divide_production_budget(allowed, division_steps,
selection.selected)` with `section_attributes` omitted — is token-identical.

This settles three things at once: §3A.1's "element-for-element equal to the sibling's list"
invariant holds by construction; HC-2's "copied, never extracted into a shared helper" is
satisfied; and the fact that plan 2's fixtures never exercise the item-narrowing branch (all
fixture items carry `item_major_category_snapshot="wood"` with no category, so `specs` is always
empty) costs nothing — that branch is byte-equal code the sibling's own C10 covers.

**V2 — ordering.** `.order_by(Task.client_id.asc())` on the visibility query is the *only*
ordering site; there is no `sorted(...)` over `output` (§7A.2's "exactly one place, never both",
verified structurally rather than behaviorally, since no test can distinguish two sites).
C6(b) reverses the request order on `client_id`s that are not in insertion order, so the
two-call-that-does-not-reverse trap is escaped; MUT-14 reddened both rows, so the five-id
contingency was not needed.

**V3 — the cap.** `len(task_ids) > _MAX_TASK_IDS` on the raw list at `:76`, before the first
`execute`. Adjacent pair 50 (C5(c)) / 51 (C5(d)) both present; identity asserted as a prefix
(§9 rule 8); C5(d) pins statement count `0` and MUT-18 arms that absence claim with a planted
presence (charter rule 15).

**V4 — the `no_budget` construction.** `NO_BUDGET_SIGNAL` short-circuits before any arithmetic
(§5A.2); it is a `frozen=True` dataclass, so the shared module constant cannot be mutated by a
caller. C3(a) asserts the whole row against a ten-key literal on a task carrying 1200 logged
seconds, and MUT-06 reddened it on `actual_worked_seconds` — the "`no_budget` fixture with no
logged time" trap is escaped.

**V5 — money is a call.** No seconds×rate arithmetic exists in the service; the only money is
`compute_budget_signal`, and `budget_signal.py` is byte-identical to its phase-1 approved content
(`sha256 1c0018ee84a4…`; absent from `git diff --numstat bd83950 8a63402`). MUT-16's minute-domain
mutant reddened C8(b) at `3602 → 2` (the minute domain gives `1`), so §3A.5's second-domain
contract is witnessed on the production path.

**V6 — snapshot, not live basis.** `evaluation.cost_per_worker_minute_minor_snapshot` at `:398`;
`basis_versions` is loaded for status resolution and never read for a rate. MUT-17 reddened C8(c)
at `99999` vs `37500`. §6A.1's "guaranteed present" is structurally true, not hopeful:
`currency`, `cost_per_worker_minute_minor_snapshot` and `allowed_worker_minutes` are all
`nullable=False` (`item_cost_evaluation.py:30,37,39`) and `uix_item_cost_evaluations_current`
(`:56`) makes the `{task_id: evaluation}` map single-valued.

**V7 — `ctx.now` is the only clock in the tail.** `load_live_worked_seconds(..., ctx.now)` at
`:163-168`; no `datetime.now` anywhere in the module. MUT-15 reddened C7(b) under both `TZ=UTC`
and the host zone. (`typical_times_statement(now=ctx.now)` and `selection_date = ctx.now.date()`
are inside the token-identical copy of V1.)

**V8 — serializer.** Additive only: `git show --numstat` gives **23 insertions, 0 deletions** on
`division_serializers.py`; two functions plus two `__all__` entries, ten keys copied through with
no `_decimal`, no `str()`, no `.get()` default. MUT-08 and MUT-09 reddened C4(b) and C4(a)/C4(c).

**V9 — perimeter.** Six executable/test files in the checkpoint: the four of plan 2 §4 (as
amended for C19) plus the two separately authorized maintenance files. Untouched:
`get_task_budget_allocations.py`, `budget_division.py`, `calculator.py`, the sibling test files,
`docs/domains/item_economics/*`, `routers/README.md`, both route-mirror tests, `Application_contracts`.
A repo-wide sweep for `budget_signal|budget-signals|budget_signals` returns exactly the six
expected files — no route is mounted, so phase 3's tripwires stay at 26 and green.

**V10 — trace chain, both directions.** 28 criterion rows ↔ 28 test functions, bijective; the
implementer's map at round 1 §"Criterion trace map" reproduces against the file. **No orphan
test.** Every criterion group carries a trace cell to a ledger ID or contract.

**V11 — the six invited rows-that-cannot-fail (master plan §9 rule 7) are all escaped**, each by
a named fixture: equal typicals → C1(a) seeds medians 3600/1800 and the unequal split is the only
reason `(0, within_budget)` holds (MUT-01 gives `(600, projected_over)`); no completed section →
C1(a)'s section A is `completed`; unreversed two-call ordering → C6(b); infeasible-that-always-
logs-work → C2(b) logs zero; `no_budget` with no logged time → C3(a) logs 1200; both-pairs kept
exclusive → C8(a) serves `over` with a non-zero projected pair. B1 is a *seventh* shape the rule
does not list.

**V12 — evidence identity.** All seven SHA-256 hashes declared in the checkpoint closeout
reproduce byte-for-byte on this tree, including the two maintenance files. The closeout's L4
budget of `0` is correct, not a skipped stamp: the maintenance stamp was taken on an executable
tree whose hashes are these, so it *is* the handed-over tree's stamp (charter: the stamp is
defined by the tree, not by the count).

**V13 — my L4.** `PYTHONPATH=. pytest -m 'not e2e'` → **21 failed / 2786 passed / 1 skipped** in
51.59 s. Failing-ID delta against the enumerated durable 21-ID comparator
(`HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7): additions `∅`, removals `∅`.
Redis `PING` → `True` immediately before. This is the third independent observation of that set
after a cycle in which it read 22, then 24 — the set is stable again.

**V14 — the maintenance repair strengthens; it does not weaken.** C10: the tuple equality on
`captured_specs[0]` asserted an order the production code does not promise (the sibling loads
tasks off an unordered `select(Task)`), so it was replaced by exact set equality — *and* the
category-to-result check was widened from one representative task to three, at tasks 0/20/35 with
**distinct** sample counts 7/9/11 (`_narrowing_fixture.py:147` seeds chair/table/stool at
7/9/11 samples). A mis-assigned spec index therefore still reddens, at the observable result
boundary rather than through a non-contractual SQL order. The dedupe claim (`len(captured_specs)
== 1`, three specs) is intact. Clock-code: `_two_workspaces`'s ambient `select(Workspace).limit(2)`
is replaced by an owned uuid-suffixed seed with per-test teardown, and the expected duplicate
insert now runs inside `db_session.begin_nested()` so the aborted transaction cannot poison the
`finally` cleanup — the correct fix, not a suppression.

## Mutation-probe declaration

Two probes, applied one at a time to the checkpoint tree, each reverted and verified before the
next.

| Probe | File | Site | Result | Restored |
|---|---|---|---|---|
| PR-A | `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py` | call site, row dict `:406-421` — `over_cost_minor` ⇄ `projected_over_cost_minor` | L1 phase file **28 passed** (the B1 gap) | ✔ |
| PR-B | same file | call site, row dict `:406-421` — `allowed_seconds` ⇄ `actual_worked_seconds` | L1 phase file **1 failed** (`test_c7_b_…`), 27 passed | ✔ |

Restored identity, verified after the last revert: `md5 f3cc04163839ebc2de639ef0283f0cb8`,
`sha256 41934cd4491ab259edf8f87e232f4ecc91ec3f99eba27065f49b2d5895aff453` — equal to the
implementation-round-2 declaration — and `git status --porcelain -- app/` is empty.
No other file was touched. **State side effects: none.** Both probe runs used the disposable-DB
fixture backbone (`db_session` rolls back; each test owns a `finally` cleanup) and every pytest
process drops its own `beyo_test_<slot>_gwN` database at session end. No architecture-graph write,
no review-item promotion/rejection/edit, no `archgraph_build_context` call — graph access was
`archgraph_status` and one `archgraph_get_node` on the new projection, read-only.

## Evidence identity

- Tree: `8a63402`, `git status --porcelain -- app/` empty (the dirty entries are `.archgraph/`
  and `docs/` only, none inside a Plan 2 executable/test file).
- L4 budget: **1**, spent, authorized before the run. Authorization line, recorded pre-run:
  *narrower evidence insufficient because this review is the phase's approval gate (charter L4
  clause (c)), and because this cycle observed three different failing sets (22 / 24 / 21) on an
  effectively identical executable tree, so an independent stamp on the committed tree is new
  evidence about that set's stability, not a reproduction.*
- Reused without re-execution (tree identity matched by hash): the 18/18 named-mutation ledger
  and both exception probes (round 1), the C19 red/green pair and L2 **639 passed** (round 2), the
  maintenance serial-order pair (**19 passed** in each file order).
- New evidence bought this session: the AST-normalized structural comparison (V1), the two
  transposition probes, the derivation of `60 → 4` / `810 → 51`, the column-nullability and
  unique-index reads (V6), the repo-wide reference sweep (V9), and the L4 stamp.

## Carry-forward dispositions

| Item | Destination | Why there |
|---|---|---|
| **B1** + N2's two assertions | **Plan 2 fix cycle** (this phase) | The row dict and its test file are phase-2 files; phase 3 cannot touch them without a §9 rule 6 breach |
| **N1** (the seven/eight count) | Intention lettered amendment + master plan §6.6 + plan 2 cells, after owner card 1 | Semantics live in the intention; the plan cells flow down |
| **N3** (stale round number) | Same edit as N1 | One-line header |
| **N4** (`state:` in plan headers) | Coordinator, project-wide, before the phase-3 prompt | Not phase-2 scope; a gate a future session can read wrong |
| §6A.2 rows 2 and 6 on the **service** path | Nothing owed — row 2 arrives free with C8(e); row 6 is plan 1's, already discharged there | Recorded so no one re-opens it |

## Lessons for the plans

1. **A criterion that pins two derived figures whose fixture makes them equal has proven one of
   them.** C8(a)'s `136/136` and C8(d)'s `8/8` read as two independent assertions and are one.
   When a plan's criteria table names a *pair* of derived fields, at least one row must give the
   pair distinct non-zero values — otherwise the mapping between them is decoration. This is the
   seventh shape of the §9 rule 7 family in this project; it is worth adding to that list as
   "a paired-figure fixture that keeps the pair numerically equal".
2. **The field-mapping class deserves its own mutation family.** A row contract of *N* keys
   admits *N choose 2* transpositions; a plan that names mutations only for *behaviour* leaves
   them all unnamed. Cheap rule for the planner: for a phase whose deliverable is a flat row,
   name one transposition mutation per pair of same-typed fields that any fixture leaves equal.
3. **Structural equivalence retires whole classes of fixture work.** An AST-normalized diff
   against the sibling proved §3A.1's invariant and HC-2's copy rule outright, and answered "the
   narrowing branch is never exercised by this phase's fixtures" without a single new test. Where
   a plan says "copy the sibling's blocks", it should say so as a *checkable* obligation —
   "`ast.unparse` of the two functions differs only in the enumerated deltas" — rather than as
   prose the reviewer must re-establish by eye.
4. **A count typed in a semantic authority survives every gate below it.** "Eight numerics"
   passed the inventory, the planner, the projection round, two implementation rounds and a
   closeout, contradicting a literal printed two lines above it. Manifest property 3 catches
   counts a tool can derive; this one needs the authority to *show its arithmetic* — write
   "seven numerics (ten fields − `task_id`, `budget_state`, `currency`)".

## Human-authorization backlog

- **Owner card 1** — the intention amendment (above). Nothing else needs the owner.
- The architecture graph carries the phase-2 projection node and its six relationships in
  `reviewState: pending`, alongside 9 other pending items and 6 stale nodes. **The owner
  adjudicates**; this review neither promoted, rejected nor edited any item. The recorded delta
  matches master plan §8's phase-2 expectation exactly — one `projection` under
  `domain-item-economics`, four `reads_from` edges mirroring the sibling's, and the `implements`
  edge from `source-file-item-economics-budget-division`, which the tree does prove.

## Write perimeter of this session

1. this handoff;
2. the Plan 2 tracker row in `master_plan.md` (`IMPLEMENTED` → `CHANGES_REQUESTED`);
3. one append-only entry in `plans/plan_2.md` §8 Review log.

No code, no test, no plan body, no intention, no prompt, no archive move, no graph write.
Probe-only files, fully restored: `app/beyo_manager/services/queries/item_economics/get_task_budget_signals.py`.
