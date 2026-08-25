---
plan: plan_2
role: review
round: 2
verdict: APPROVED
date: 2026-08-25
actor: Claude Opus 5
---

# Plan 2 re-review round 1 — delta on the fix checkpoint `8dc3a06`

Delta-scoped re-review of the round-1 fix. **B1 is closed and N2's two vacuity holes are
closed.** The executable perimeter is exactly the one allowed file; the four declared
SHA-256 identities and the declared normal-side app-diff digest all reproduce byte-for-byte
on my tree, so the fix session's fresh 19-mutation ledger is tree-bound evidence I consume by
citation rather than re-run.

The one thing I bought that nobody had measured: the same money-field transposition planted at
the **serializer** site — a site no named mutation covers — and C8(e) is the **only** test in
the file that catches it (1 failed / 28 passed). Before this fix the same probe class measured
28 passed at the service site (review r1, PR-A). The instrument is real, and it is the only
instrument.

**Verdict: `APPROVED`.** Phase 3 is unblocked.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs owner attention. Owner card 1 from review r1 was answered and is discharged
(intention round 12). The pending architecture-graph items remain the owner's standing
adjudication queue — unchanged by this round, no new item added.

## Gate check

| Gate | Source | Result |
|---|---|---|
| Intention header | `planning/intention.md:3-4` | `status: **RATIFIED**` (round 12, 2026-08-25) — **pass** (see N5) |
| Plan 1 `APPROVED`, Plan 2 `IMPLEMENTED` | master plan §4 tracker | **pass** |
| `HEAD` = `8dc3a06`, subject `CHECKPOINT (not approved): task budget signal phase 2 fix round 1` | `git log -1` | **pass** |
| No uncommitted Plan 2 executable/test change | `git status --porcelain` → only `.archgraph/`, `docs/archgraph-anchor-observations.md`, and three untracked doc/prompt trees; nothing under `app/` | **pass** |

## Verified perimeter

`git diff --name-status 8a63402 8dc3a06` returns ten paths. Exactly **one** is executable:

- `app/tests/integration/services/queries/item_economics/test_budget_signals_query.py` — the
  allowed file, +34 lines, no deletions.

The other nine are documents, all declared in the fix handoff's write-and-probe perimeter:
the fix prompt and handoff, the review-r1 prompt and handoff, `master_plan.md`,
`planning/intention.md`, and `plans/plan_1.md` / `plan_2.md` / `plan_3.md`. Provenance
verified rather than assumed:

| Doc delta | Declared as | Provenance check | Result |
|---|---|---|---|
| `intention.md` round 10 → 12 header + new round-12 changelog section + three "eight → seven" cells | coordinator fold of N1/N3 after owner card 1 | The changelog section is **lettered/appended**, renumbers nothing, and records the owner act; §5A.2 and §6A.2 row 1 carry the corrected count | pass |
| `master_plan.md` §6.6 "eight → seven"; intention pointer to round 12; Plan 2 tracker row | coordinator fold + implementer tracker row | Tracker row is the fix session's own row; the §6.6 cell is the N1 fold | pass |
| `plans/plan_1.md`, `plan_3.md` — `state: NOT_STARTED` header removed; `plan_3.md` C4(d) "eight → seven" | coordinator fold of N4 and N1 | N4's destination was "coordinator, project-wide, before the phase-3 prompt"; done early, not misfiled | pass |
| `plans/plan_2.md` — `state:` header removed, C3(a)/C4(b) cells, C8(e) row, MUT-19 row, count 18 → 19, three Review-log entries | coordinator fold + review-r1 entry + fix-r1 entry | All present; see N6 on entry ordering | pass |

**No executable/test file outside the allowed one changed. No finding on perimeter.**

Byte-identity of the handed-over tree (recomputed this session, `shasum -a 256`):

| File | Declared | Recomputed | |
|---|---|---|---|
| `get_task_budget_signals.py` | `41934cd4…aff453` | `41934cd4491ab259edf8f87e232f4ecc91ec3f99eba27065f49b2d5895aff453` | match |
| `division_serializers.py` | `bc1f56cc…6ff577` | `bc1f56cc057317211a1298c2bac9387d754c6530fac29fffb7604cf6ce4ff577` | match |
| `budget_signal.py` | `1c0018ee…5ff070` | `1c0018ee84a4772f7a996eec9f0c2244f10a1ba21653f7fcce24a6e9d65ff070` | match |
| `test_budget_signals_query.py` | `0b4689f0…2693d0` | `0b4689f0a40411bd39b655a78cfccdb1ab9338b4efca4e27e7a5e51d032693d0` | match |
| normal-side app diff vs base | `44a644dc…1a85fb` | `git diff 8a63402 8dc3a06 -- app/ \| shasum -a 256` → `44a644dc73a6225551a7af606f772faaf91eb3bd725ace7801a1ce702a1a85fb` | match |

The last row is the one that matters for reuse: the tree the 19-mutation ledger was executed
against is **byte-identical to the tree under review**, so every ledger row — including the
eighteen re-run after the test-file edit — is valid tree-bound evidence here. Re-running any of
them would be a redundant re-run under the charter's test-evidence section.

## Findings

**None blocking. None should-fix.** Two notes, both coordinator-layer and neither touching
phase-2 executables.

### N5 — note — the intention header's date sentence and its round stamp now disagree

`planning/intention.md:3-4` reads `status: **RATIFIED** (round 12, 2026-08-25) — re-ratified by
the owner (**David**) on 2026-08-24, on the re-ratification surface at §10.6.` The round stamp
and the ratifying-act date now name different days, because rounds 11 and 12 were
wording-preserving amendments that did not re-open the gate while the sentence still describes
the round-10 act. It reads as one act with two dates. **Correction:** split them — the stamp
carries the current round and its date; the sentence names the last *ratifying* act and its own
date ("last full re-ratification: 2026-08-24, §10.6; rounds 11–12 are precision amendments that
preserved RATIFIED"). Owner layer: none — this is wording inside a section the owner already
approved, not a semantic change. Destination: coordinator, before the phase-3 prompt.

### N6 — note — the Plan 2 Review log is no longer chronological

`plans/plan_2.md` §8 is declared append-only. The entry **"Review r1 findings folded
(2026-08-25)"** sits at line 251, *before* "Implementation round 2 blocked at close" and
"Checkpoint closeout" — both of which happened before review r1 existed. A future session
reconstructing the round order from this log will read the fold as preceding the round that
produced it. **Correction:** move the fold entry to sit immediately after the review-r1 entry it
folds, or restate its position with an explicit "(folded after review r1, recorded here for
adjacency)". Destination: coordinator. Not a phase-2 fix-cycle item.

## Verified correct — the changed seam

**W1 — C8(e)'s expected tuple is independently correct.** Re-derived from source with no test
run, on the fixture the plan names (`allowed = Decimal("-12.50")`, rate `Decimal("3.7500")`,
step `a` `working`/section A/60 s, step `b` `pending`/section B/0 s, no open `StepStateRecord`):

- `evaluation.allowed_worker_minutes = -12.50 ≤ 0` → status `INFEASIBLE`, which **is** in
  `_BUDGET_STATUSES` (`get_task_budget_allocations.py:48`), so the row is budget-bearing.
- `_budget_seconds(-12.50) = -750`; `charged_seconds = 0` (no excluded state);
  `distributable_seconds = max(0, -750) = 0` → both section allowances `0`.
- Section A: `worked 60`, `left_seconds = 0 - 60 = -60`, governing state `working` (non-terminal)
  → contributes `max(0, -60) = 0`. Section B: `left_seconds = 0`, `pending` → contributes `0`.
  `remaining_commitment = 0`.
- `load_live_worked_seconds`: no open `WORKING` record → live == settled → `actual = 60`.
- `over_seconds = max(0, 60 - max(0, -750)) = 60`; `over_seconds > 0` → `budget_state = "over"`.
- `remaining_pot = -750 - 60 = -810`; `projected_over_seconds = max(0, 0 - (-810)) = 810`.
- `calculate_consumed_cost_minor(60, 3.75) = 3.75 → ROUND_HALF_EVEN → 4`;
  `calculate_consumed_cost_minor(810, 3.75) = 50.625 → 51`.

`(60, 4, 810, 51, "over")` — exactly the asserted tuple. The fixture is **order-independent**:
because `distributable_seconds` is `0`, both allowances are `0` regardless of typical weights,
so no seeded history, section sort order or governing-step choice can move the result.

**W2 — the money operands are non-zero and unequal, and so is the seconds pair.** `4 ≠ 51`
and `60 ≠ 810`, all four non-zero. Every one of the six pairwise transpositions among
`over_seconds / over_cost_minor / projected_over_seconds / projected_over_cost_minor` now moves
this tuple. This is what B1 asked for and slightly more: C8(a) `9/9`, C8(d) `0/0` and C3(a)
`0/0` are no longer the only paired fixtures.

**W3 — MUT-19 is sited where the plan says and its red reaches the mapping assertion.** Plan 2
§6.1 sites it at `get_task_budget_signals.py`, call site, the per-task row dict — which is
`get_task_budget_signals.py:406-421`, the exact construction B1 named. The ledger records the
observed red as `(60, 51, 810, 4, over)`: positions 2 and 4 swapped, positions 1/3/5 intact.
Charter rule 12's short-circuit hazard does not apply — C8(e) is a **single tuple comparison**,
so every sub-check is evaluated on every run and no assertion returns before the money fields
are read.

**W4 — the closed mutation set is closed and its count is derived.** Plan 2 §6.1 declares 19;
the ledger records `MUT-01`…`MUT-19`, one row per declared mutation, each with an isolated
mutant, a named bite target, observed red evidence and a restore flag. The handoff's own count
line (`C1 2 + C2 3 + C3 2 + C4 2 + C5 5 + C6 1 + C7 1 + C8 3 = 19`) reconciles against the
table by bite target: C1 `01,02`; C2 `03,04,05`; C3 `06,07`; C4 `08,09`; C5 `10,11,12,13,18`;
C6 `14`; C7 `15`; C8 `16,17,19`. Derived, not typed.

**W5 — C4(b)'s guard precedes its per-row loop.** `assert len(rows) == 2` is at line 632,
before the `for row in rows:` at 633. The fixture seeds exactly two tasks (one evaluated, one
not), so the guard is satisfiable and falsifiable. MUT-08 still bites C4(b) through the
integer-type assertion.

**W6 — C4(c)'s guard precedes its flatness walk.** `assert result["budget_signals"]` is at line
650, between the envelope assertion (649) and the `not any(...)` walk (651-655). The walk can no
longer pass on an empty list. MUT-09's recorded red covers C4(a) **and** C4(c), so the walk is
still shown to bite.

**W7 — trace chain intact, no orphan test, no untraced criterion.** 29 criterion rows
(C1 2, C2 5, C3 3, C4 3, C5 6, C6 2, C7 3, C8 5) ↔ 29 `async def test_` functions in the file
(counted this session), bijective, matching the fix handoff's map row for row. C8(e) sits under
C8, whose section trace is §4A.1, §4A.2, §4.1, §3A.5 → **M2** — the same ledger entry review r1
named for it. The four module-level helpers (`_ctx`, `_get`, `_case`, `_evaluated_task`) all
have callers (rule 4).

**W8 — no production delta.** `git diff 8a63402 8dc3a06 -- app/beyo_manager/` is empty; the
three probe-touched production files hash to their declared pre-probe values. The fix changed
test observability only, exactly as claimed.

**W9 — N1 is fully discharged, and further than its site list.** No live artifact still says
"eight numerics": intention §5A.2 and §6A.2 row 1, master plan §6.6, plan 2 C3(a)/C4(b) and —
beyond the list — plan 3 C4(d) all read seven. A repo-wide sweep for `eight numeric|the eight|
eight fields` returns only archived handoffs (immutable history), review-log quotations of the
finding itself, and **correct** unrelated uses: the eight-member `TaskStepStateEnum`, and the
`BudgetSignal` dataclass's genuine eight fields (`budget_state` + 7 ints). The wire row is
ten keys = 3 strings + 7 ints. Internally consistent.

**W10 — N3 and N4 are discharged.** Intention header now reads round 12 (see N5 on its date
sentence); `state:` headers are gone from all three plan files.

**W11 — evidence arithmetic is consistent across the cycle.** L1 28 → 29 (+1 = C8(e)); declared
L2 639 → 640 (+1); L4 2786 → 2787 passed (+1) with the durable 21-ID failing set unchanged in
both directions and 1 skipped throughout. One L4 stamp, taken on the handed-over tree, with a
pre-run authorization line recorded in the fix handoff.

## New evidence bought this session (variation, not reproduction)

**PR-C — serializer-site money transposition.** *Hypothesis:* the money-field mapping is
guarded at the **serializer** projection too, a site the closed 19-mutation set never touches —
`serialize_budget_signal` re-keys all ten fields by hand (`division_serializers.py:74-88`), so a
transposition there is a distinct real defect from MUT-19's service-side one.

- Applied at `division_serializers.py:79,81`: `"over_cost_minor": row["projected_over_cost_minor"]`
  and `"projected_over_cost_minor": row["over_cost_minor"]`.
- Scope **L1**, file: `PYTHONPATH=. pytest tests/integration/services/queries/item_economics/test_budget_signals_query.py -q` from `app/`.
- Result: **1 failed, 28 passed** — the single failure is
  `test_c8_e_money_fields_map_to_distinct_nonzero_operands`. Every other criterion in the file
  is blind to it, which is precisely the review-r1 PR-A measurement (28 passed, all green) now
  inverted by the new row.
- Reverted from a pre-probe copy; `division_serializers.py` re-hashes to
  `bc1f56cc057317211a1298c2bac9387d754c6530fac29fffb7604cf6ce4ff577`, byte-identical.

Two things fall out. First, C8(e) is not merely *a* witness for the field-mapping class, it is
the **only** one in the phase — which is the strongest form of "the guard can fail" this phase
can produce. Second, the 28 green tests in that run are a free, non-redundant confirmation that
the rest of the file is clean on this tree, so **no separate clean L1 run was taken**.

**Structural reads (no execution).** The serializer is a literal ten-key hand projection with
no computation, so C8(e) observes the composition of both mapping sites at once; and
`_BUDGET_STATUSES` includes `INFEASIBLE`, which is what makes a negative allowance
budget-bearing and the C8(e) fixture legal.

## L4 budget

Declared **0**, spent **0**. The current-tree L4 evidence is the fix handoff's single stamp —
`21 failed / 2787 passed / 1 skipped`, additions `∅`, removals `∅` — taken on a tree whose app
diff digest reproduces exactly on mine. No full-suite run was made this session. The one probe
run was L1 file scope and bought a new mutant site, not a reproduction.

## Mutation-probe declaration

| File | Probe | Restored | Verification |
|---|---|---|---|
| `app/beyo_manager/domain/item_economics/division_serializers.py` | PR-C, transpose the two money source keys in `serialize_budget_signal` | yes, from a pre-probe copy | `shasum -a 256` → `bc1f56cc…6ff577`, identical to the declared and pre-probe value |

No other file was written or touched. `git status --porcelain` after the probe is **identical**
to the session-entry status (two modified graph/observation files and three untracked doc
trees, none of them mine, none under `app/`). Database side effects: the probe run used the
suite's standard disposable-DB path (`tests/database_isolation.py`, per-worker databases created
from the migrated template and dropped at session end); no fixture, seed or migration was
altered, and no database was targeted outside that path. I could not independently enumerate
leftover `beyo_test_*` databases — the local `psql` prompts for a password this session does not
hold — so orphan-DB accounting stays with the project's existing standing item, unchanged by
this round.

## Carry-forward dispositions

| Item | Status | Destination | Why there |
|---|---|---|---|
| **B1** (money transposition unobservable) | **CLOSED** | — | C8(e) + MUT-19 shipped; independently re-derived (W1) and independently probed at a second site (PR-C) |
| **N2** (two vacuous assertions) | **CLOSED** | — | W5, W6 |
| **N1** (seven vs eight numerics) | **CLOSED** | — | W9; owner card 1 answered, intention round 12 |
| **N3** (stale round number) | **CLOSED** | — | W10 |
| **N4** (`state:` headers) | **CLOSED** | — | W10 |
| **N5** (header date vs round stamp) | **OPEN** | Coordinator, before the phase-3 prompt | Wording inside an owner-approved section; no semantic change, no owner act needed |
| **N6** (Review-log entry out of order) | **OPEN** | Coordinator, at the phase-2 closeout | The log is the provenance record the next phase reads |
| Architecture-graph pending items (phase-2 projection + six relationships, plus 9 other pending and 6 stale) | **OPEN, owner-only** | Owner adjudication queue | Unchanged this round: 0 nodes, 0 relationships, 0 review decisions, 0 repairs |
| §6A.2 rows 2 and 6 on the service path | **CLOSED** | — | Row 2 arrived with C8(e) as review r1 predicted; row 6 is plan 1's |

## Lessons for the plans

1. **A second mapping site deserves a named mutation of its own.** This phase ships the row
   through *two* hand-written key projections — the service's row dict and
   `serialize_budget_signal` — and the closed set names a transposition at only the first. It
   happens that one criterion covers both, because C8(e) asserts the serialized output. That is
   luck, not design: had the serializer collapsed or renamed a key, the ledger would have read
   19/19 green with a site unmutated. **Rule for the planner: when a value crosses N hand-written
   projections before the wire, the mutation set names the site closest to the wire, not the
   site closest to the computation** — a mutation at the last projection covers the earlier ones
   by composition, and the reverse is not true. (Generalizes review r1's lesson 2.)
2. **Fix rounds that add a criterion row should carry the row's own trace cell, not inherit the
   section's.** Review r1's correction specified C8(e) as "trace §4.3, §5.1, §4A.1 → M2"; the
   plan added the row under C8's section trace (§4A.1, §4A.2, §4.1, §3A.5 → M2). Same ledger
   entry, so nothing is untraced and this is not a finding — but the two §-lists differ, and the
   next reviewer has to decide which is authoritative. Cheap fix: when a review prescribes a
   trace, the fold either uses it verbatim or records why the section trace subsumes it.
3. **Chronology is part of what a Review log is for.** N6 is small and cost nothing this round
   only because the fix handoff independently states its base commit. An append-only log that is
   edited in the middle stops being usable as the round-order record, which is the one thing a
   re-review cannot reconstruct from the tree.

## Write perimeter of this session

1. this handoff;
2. the Plan 2 tracker row in `master_plan.md` (`IMPLEMENTED` → `APPROVED`);
3. one append-only entry at the end of `plans/plan_2.md` §8 Review log;
4. one appended entry in `docs/archgraph-anchor-observations.md` (standing owner observation
   log, outside the project folder).

No code, no test, no plan body, no criteria table, no intention, no prompt, no archive move,
no architecture-graph write.
