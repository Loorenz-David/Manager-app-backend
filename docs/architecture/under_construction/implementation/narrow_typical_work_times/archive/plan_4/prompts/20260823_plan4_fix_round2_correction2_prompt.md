---
plan: plan_4
role: implementer
round: 2
correction: 2
supersedes_scope_of: prompts/implementer/20260823_plan4_fix_round2_prompt.md
date: 2026-08-23
---

# Fix round 2 — correction 2: you were right, the fence is lifted

**This supersedes the *scope* of the round-2 prompt and of correction 1. Everything else in
the round-2 prompt still stands and still wins over this document where they overlap.**
The round-2 prompt itself is **not edited** — it has been reported against twice.

## You were right and I was wrong

You halted on C10(d) saying production returns `insufficient_sample` for category-less tasks
and that fixing it needed production changes. I ruled that a fixture defect and told you to
seed more section-wide history. **You refuted that by measurement** — 27 → 32 completed section
totals, C10 failed identically — then found the real cause and reverted your own ineffective
change, leaving the tree clean. That is exactly what the instruction to re-open rather than
comply was for. **Do not treat my rulings as settled when your measurement disagrees.**

I verified your diagnosis independently at source:

- `get_task_budget_allocations.py:150-151` keys statement rows
  `(row.client_id, int(row.spec_index) if specs else None)` — so with `K ≥ 1` every key is
  `(section_id, 0..K-1)`.
- `:254` looks up `(section_id, task_spec_index if specs else None)`, which for a category-less
  task in a mixed batch is **`(section_id, None)`** — a key that never exists.
- `:255-256` therefore constructs `SectionTypicalEvidence(section_id, None, 0, None, 0)`, and
  the task publishes `insufficient_sample`.

That **contradicts task 8 and §3B B1**, which require `spec_index = None` to take
`narrowed_* := section_*` with a **section-wide** basis.

**Why C9 stayed green:** C9's fixture is a single no-category task, so `K == 0`, `specs` is
empty, and rows are keyed `(section_id, None)` — the lookup matches. **C9 is the `K == 0`
path; C10 is the `K ≥ 1` mixed path.** My inference from one to the other is the whole of my
error, and it is now recorded in master plan §9.

## Scope change — the one thing this document authorizes

**`app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` is added to
your round-2 perimeter**, for this defect only. It was always inside plan §4; my round-2 prompt
narrowed it out and that narrowing was wrong.

**Nothing else in production is in scope.** If any other production file appears necessary,
**stop and report** — that instruction has now paid for itself once.

## The fix

A task whose `spec_index is None` must resolve against **any** row for its section and read
**only the section-wide columns**, with `narrowed_* := section_*`.

**Why that is safe, verified at source:** the section-wide columns are **spec-independent** —
`section_count` and `section_percentile` are filtered by `qualifying` only, never by
`narrowed_qualifying` (`get_working_section_typical_times.py:95-96`) — so they are byte-identical
on every `spec_index` row for a given section. And the statement emits **one row per live
non-deleted working section × spec_index** (§4A K2), so `(section_id, 0)` exists whenever
`K ≥ 1`.

**Constraints on how you write it:**
- Do **not** make the `K == 0` path conditional on anything new. It works; leave it alone.
- Do **not** synthesize a `(section_id, None)` entry into `typical_rows` as a shortcut — that
  puts a fabricated key in a dict whose keys are otherwise a faithful image of the result set,
  and the next reader cannot tell them apart.
- Keep `narrowed_typical_worker_seconds` / `narrowed_sample_count` derivation for
  `task_spec_index is not None` **exactly** as it is (`:260-261`).

## What C10(d) now proves

**C10(d) is not a defective criterion and is not being reworded.** It is the criterion that
caught this phase's first production defect, on precisely the shape it was written for —
Critical rank 2/3, a mis-keyed row attributing the wrong history to a task. When it goes green,
it will be green for the right reason. **Say so in your ledger**: this row moved from red to
green by a production fix, not by a fixture change.

## Also still owed from round 2

Unchanged: **B1** (the snapshot must fail when absent — delete it, record the red, restore),
**B2** (C8/C11 done; C10 finishes with this fix), **B3** (one ledger row per mutation, 21 named,
**C10(i) and C10(ii) have still never been run**), **B4**, **S1** (21-ID diff, not a count),
**S2**.

**One addition to B3, and it is not optional.** After this fix, add a mutation that would have
caught it: **revert the `spec_index is None` fallback to the `(section_id, None)` lookup** →
C10(d) must go red with `insufficient_sample`. A production defect that no named mutation
reproduces is a defect the suite can silently reacquire.

## Evidence budget

Unchanged: **exactly 1 L4 run**, the closing stamp on the tree you hand over, with S1's id diff
computed from it. Everything else at L1/L2.

## Report back

As per the round-2 prompt, plus:
- The failing → passing transition for C10(d), with observed ids on both sides.
- The new anti-regression mutation and its observed red.
- Confirmation that the `K == 0` path is untouched.
