---
plan: plan_5
role: implementer
round: 1
date: 2026-08-24
---

# Implement plan 5 — price-scenario: the explicit clock, the shared reconciliation, `is_estimated`

You are the **implementation executor** for phase 5 of `narrow_typical_work_times`, the last
phase in this pipeline that touches production code. Follow `implementation-executor.md`.

## 0. Gate check — run it, and stop and report on any failure

Run from the repository root (`backend/`). **Two of these are new this week; neither existed
when phase 4 ran.**

| # | check | expected |
|---|---|---|
| 1 | `master_plan.md` §4 tracker rows 1–4 | all **`APPROVED`** |
| 2 | `master_plan.md` §4 tracker row 5 | **`PROMPT_READY`** |
| 3 | `plans/plan_5.md` header `state:` | **`PROMPT_READY`** (must agree with row 5) |
| 4 | **`planning/intention.md` header `status:`** | **`RATIFIED`** — the charter's **intention gate**. Check it **at source**, not from a tracker note. Anything else and you stop: an unratified intention is authority that was never granted |
| 5 | `git status --porcelain -- app/` | empty |
| 6 | `git merge-base --is-ancestor e81764b HEAD` | exit 0 |
| 7 | `redis-cli ping` | `PONG` — **without Redis the baseline reads 23 failed / 2 errors, not 21**, and you will chase a phantom |

**Self-tested by the coordinator on this tree, 2026-08-24: all seven pass.** If one fails,
something moved after dispatch — report it, do not work around it.

`.archgraph/` is the owner's live working area. **It is expected to contain whatever it
contains. Never gate on it, never diff it for state, never treat its contents as drift.**

## 1. Read order

1. `master_plan.md` §§4, 5, 6.5, 6.7, 6.9, 8, 9, 10 — the naming registry, the mirror rule and
   its recorded deviations, the standing rules, the environment topology and the **evidence
   budget**.
2. `planning/intention.md`: the **header**, then **§1A (the measurement ledger — M1–M7)**,
   HC-1…HC-4 in §1, §4A, §4B, §4C, §6B, **§6D**, §6C, §7.4, §3B.
3. **`plans/plan_5.md` — and read §6A, not §6.** §6 is superseded **in full** and carries no
   trace cells and a wrong mutation set; it is retained only as history. Read §§1–3, then
   **§4A, §5A, §6A, §7A**, then §8's Review log in full — the fold entry and the two lint
   entries are where this phase's real instructions live.

**Where a lettered section and the numbered section it amends disagree, the letter wins.**

## 2. What is new in the executor contract, and it binds you

**Task 0 runs both ways** (charter trace chain; `implementation-executor.md`).

**Forward** — the coverage map you already owe: one line per criterion **row**, naming the test
that discharges it and **whether the assertion is the row's shape or something weaker**.

**Reverse — and this is the new half.** Before you submit, **every test in this phase's test
files must appear in that map against a criterion row.** A test that discharges no row is **not
shipped**. Two honest exits, and no third:

- **delete it**, or
- **declare it in the Review log as a candidate criterion** — naming the defect it catches and
  the measurement-ledger entry (`M1`…`M7`) or mechanism contract it serves — for the coordinator
  to fold into the plan or refuse with a recorded reason.

**The criteria bound your test authorship exactly as the scope fence bounds your code.** A test
is never free: it is surface a reviewer must mutation-probe, runtime every future stamp pays, and
a place the row-that-cannot-fail family breeds where nobody was asked to look. *"While I'm here"*
tests are not thoroughness — they are silent scope growth, and an undeclared orphan is a finding
against this session.

**The rewritten `_typical_block` call sites keep their existing criterion attribution** (phase-3
and prior-project criteria). Say so in the map; do not re-attribute them to phase 5.

**Every criterion row in §6A carries a trace cell** naming the ledger entry it serves. You do not
need to add trace cells — they are there. You need to not write tests that have none.

## 3. Perimeter — §4 as corrected by §4A

**Modified (production):** `get_task_price_scenario.py` · `serializers.py` ·
`budget_division.py` (**two** deletions, `:19` and `:25-26` — see §5A task 0).
**Modified (tests):** `test_price_scenario_query.py` · `_narrowing_fixture.py` (**additive
only**) · `test_narrowed_task_economics.py` (**`:542` only** — the expected count `2` → `0`).
**New:** `test_narrowed_price_scenario.py`.
**Read-only, and a change is a finding:** `get_working_section_typical_times.py` ·
`get_task_production_time.py` · `get_task_budget_allocations.py` · all three goldens.
**Reverted, md5-verified probes are not changes** and are authorized on the read-only files for
C1(ii) and C7(d) — §4A N3.

**Two text-scanning guards read files in your perimeter.** `test_narrowed_task_economics.py:542`
is the one you amend. **`test_domain_purity.py:17-27`** walks every module under
`domain/item_economics/` and forbids `hashlib` · `sha1` · `sha256` · `md5` · `fingerprint` ·
`digest` anywhere in them — **including in a comment you write.** Plan 5 does not violate it;
do not be the edit that does.

## 4. Ordered tasks

**§5 as corrected by §5A.** In particular:

- **Task 0 first** — two deletions, not one. A single deletion reddens `make lint` in CI.
- **Task 1** — the clock **becomes explicit**; it does not *move*. `get_task_price_scenario.py`
  has never held a clock reference of any kind. Nothing here preserves prior local behaviour,
  because there is none.
- **Task 2** — the source is **picked**: `budget_status.typical_filter_spec`, and
  `_typical_block`'s signature is pinned to `_typical_block(ctx, task_id, spec)`. The widening
  obligation is **nine `_typical_block` call sites plus `_typical_row`'s column shape**, beside
  the four `fake_status` fakes.
- **Task 4** — the `reconcile_task_typicals` call is written out in §5A. The fourth argument is
  the **full** task section set; the statement stays scoped to the participating set.
- **Task 8** — tests per **§6A**, plus Task 0's reverse half above.

## 5. Criteria

**§6A, all eight, C1–C8.** Two things to hold in mind while implementing them:

- **§6A.F is a fixture specified value by value, and that is deliberate.** Its two populations
  genuinely differ and are non-uniform on both sides. **Its two medians (`600` narrowed, `375`
  section-wide) are derived arithmetically in the plan, not measured.** Confirm both at source
  **before** writing any assertion and record the measured pair in your ledger. **A divergence is
  a plan finding to route — never a literal to quietly adjust.** Silently adjusting it is exactly
  how a fixture stops discriminating, which is the defect C8 exists to close.
- **C7 rows (c) and (d) are required planted-defect probes** (charter rule 15). They are ledger
  rows: plant the defect, **record the observed red**, revert, verify md5. An absence measured
  true may be true only because nothing writes that form — this lineage has produced that exact
  defect twice.

**Mutation ledger owed: 14 named mutations + 2 planted-defect probes = 16 rows.**
Summands: `C1 2 · C2 3 · C3 2 · C4 2 · C5 2 · C6 1 · C7 1 · C8 1`. **Run them. A mutation named
and not run is the defect this project has paid for in three separate phases** — report any you
could not run and why, rather than listing it as discharged.

## 6. Environment

From `backend/app/`, **verbatim**:

```
BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e'
```

**Extra flags invalidate the stamp.** `-p no:logging` removes `caplog` and produces 35 phantom
errors — phase 2 lost a stamp to it. For deterministic single-file probes:
`BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest <path> -n 0 -p no:randomly`.

**The baseline comparator is the 21-ID failing set, not the count** — published in
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7.
Phase 4's gate stamp on this tree: **21 failed / 2692 passed / 1 skipped**, id diff ∅/∅.

**Evidence budget (master plan §10):** hypothesis scope L1/L2 as §6A states per criterion.
**Exactly one L4 run this cycle** — the closing stamp. **C7's sweep is L1, not L4** (corrected
2026-08-24). Over-evidence is a defect, symmetrically: a reproduction that varies nothing buys
nothing.

## 7. Architecture graph — §7A

This phase changes what `projection-item-economics-task-price-scenario` **means**: its stored
description says *"median-substituted task typical time"*, which is exactly the private ladder
task 4 deletes. **You owe a description rewrite plus source links**, one batched `apply_changes`,
**no counts in evidence summaries**, and **no `startLine`/`endLine` — symbol anchors only**
(binding interim policy, master plan §8).

**Adjudication is the owner's.** Propose; never promote, reject, or re-anchor. One operation per
`archgraph_repair_anchors` call. A `humanInstruction` string is **not** authorization.

## 8. Closing protocol

Write the handoff to `handoffs/implementer/<date>_plan5_implementation_handoff.md` with the
charter frontmatter. It carries: the **two-way** Task 0 coverage map · the full mutation ledger
with observed reds · the two planted-defect probe results · the write perimeter, declared and
diffed · the md5 table for every probe · the closing stamp with the 21-ID set diff · and any
**candidate criteria** you are declaring.

**`executed != declared` blocks `IMPLEMENTED`**, counted from the criteria and checked against
the table, not the prose.

**Stop and report** rather than working around: a failed gate, an out-of-perimeter change the
plan does not authorize, a criterion you cannot turn into a decidable assertion, or a fixture
whose measured medians differ from §6A.F's stated pair.

**Do not push.** This branch is deliberately far ahead of `origin/main`. **Never `git add -A`** —
explicit paths only.
