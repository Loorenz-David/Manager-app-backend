---
plan: plan_5
role: implementer
round: 3
date: 2026-08-24
---

# Plan 5 — fix round 3 (review round 1: 2 blocking, 1 should-fix, 5 notes)

An Opus 5 review returned `CHANGES_REQUESTED`. **Your production code is right** — the reviewer
verified §6B implemented verbatim, the price terminal, and no behavioural regression on the
pre-existing path, by reading the old and new bodies side by side. **Both blocking findings are
about what is watching it.**

Read `plans/plan_5.md` §8's newest entry — *"review round 1 consumed"* — and the review handoff
itself before starting. **Two of the three non-note findings are the plan's defects, not yours,
and are already corrected in §6A.**

## Gate check

`plans/plan_5.md` header `state: CHANGES_REQUESTED` · master plan §4 row 5 `CHANGES_REQUESTED` ·
`planning/intention.md` header **`RATIFIED`** · `git status --porcelain -- app/` empty from
`backend/` · `redis-cli ping` → `PONG`. **`.archgraph/` is the owner's and is closed for this
phase (D31) — do not read it for state, do not gate on it, do not touch it.**

## B1 — BLOCKING. Implement §6A **C8(c)**: the edge that feeds the function

**The finding, measured by the reviewer.** Replace the third argument at
`get_task_price_scenario.py:234-238` with `None` and the **entire repository stays green** — L2
item-economics 366 passed, full suite 21 failed / 2707 passed / 1 skipped, the exact 21-ID
baseline, **no failure-ID delta in either direction**.

**Narrowing can be switched off for this consumer and nothing anywhere reddens.** Every row that
exercises narrowing calls `module._typical_block(...)` directly and hands it a spec the test
derived itself; the four `_run_scenario`-family tests that call the service monkeypatch
`_typical_block` away, and their `fake_status` returns `typical_filter_spec=None`.

**§6A C8(c) is written.** Two acceptable forms, and **(ii) is preferred**:

- **(ii)** drive `get_task_price_scenario(ctx)` **end to end** on `seed_divergent_category_task`
  and assert `typical["total_seconds"] == 600` on the **served payload**. This also closes the
  standing note that C8 reads `_typical_block`'s dict rather than the wire.
- **(i)** a spy on `module._typical_block` asserting it receives the spec derived from the task's
  own PRIMARY item.

**Mutation:** `get_task_price_scenario.py:237` (call site) — pass `None`. **Row (c) alone must
redden.** Note carefully: **this mutation is known to leave the whole suite green today.** A
ledger reporting it as red without a new test has not run it.

## B2 — BLOCKING. Implement §6A **C1(b)** as prescribed, and declare it element by element

**What shipped:** two calls against two `_TypicalSession` instances built from **identical
hand-supplied rows**. That fake discards the statement, so the two results are `f(x)` and `f(x)`
over the same `x` — the byte-identity assertion is a tautology. **Measured:** under this row's own
mutation C1(i) the red lands at `:139`, the spy's kwarg list — **the same observable `test_c1a`
already asserts at `:92`** — while the byte-identity assertion at `:136-138` **executed and passed
under total loss of the injected clock**.

**Charter rule 12:** a named mutation must reach **every** sub-check. This one reaches the
sub-check already covered and misses the row's entire distinguishing content — M7's stated
observable, *the same task over identical data serving byte-identical typicals at two different
wall-clock instants*.

**Also: the instrument was substituted without declaration**, and the round-1 coverage map claimed
C1(b) covers *"boundary inclusion"* — `closed_at`, `timedelta`, `90` and a fake `datetime` appear
**nowhere** in that file's C1 block. Charter rule 14: **a divergence from a prescribed instrument
is declared, in the round that makes it.**

**Do one of these:**
- implement §6A C1(b) **as written** — it is specified to the line: fake `datetime` on
  `…get_working_section_typical_times.datetime`, `now()` returning `ctx.now - 1s` then
  `ctx.now + 1s`, one group pinned at `max(closed_at) == ctx.now - 90 days`; or
- if that route is genuinely unworkable, a **DB-backed** row on `seed_divergent_category_task`
  seeded with one group at `now - 90 days` and one at `now - 91 days`, asserting two exact
  `total_seconds` literals at two `ctx.now` values one day apart.

**Either way the row reddens on a number, not on a kwarg list**, and C1(i) is re-derived from the
shipped code afterwards.

**Ledger requirement for this row, binding:** state **which prescribed element you implemented**,
one cell each — the fake `datetime`, the boundary group, the two exact literals. *"Implemented
C1(b)"* is not a ledger entry for a row specified this precisely.

## S1 — plan defect, already corrected. No code.

§6A C5(b) claimed to guard §2B S-7's SQL scoping. It does not, and **nothing does**: deleting
`.where(WorkingSection.client_id.in_(participating_ids))` leaves L2 at 366 passed, because
`reconcile_task_typicals` iterates `section_ids` and ignores foreign rows. **§2B S-7 is a
query-cost property with no wire observable, recorded as having no owner.**

**Do not build a test for it.** Inventing a criterion for a mechanism with no observable is how
this project's fifth-generation cannot-fail row gets built. Nothing is asked of you here; it is
listed so you do not close it on your own initiative.

## Notes — four one-line items, none of them new coverage

- **N1 — done in the plan, do it in the test.** §6A C4(a) states two observables; the test asserts
  `total_seconds` only (`:239`). Add the `is_estimated` assertion.
- **N2 — C6 runs on a hand-built `TaskTypicalSelection` and re-imports `"icat_chair"`**, the exact
  literal §6A **S1** deleted because no seed in this repository produces it. Either point row (c)
  at `seed_categorized_two_section_task` and assert what it produces, or **declare in the Review
  log** that row (c) reads back constants the test supplied. Rows (a)/(b) are sound; the shared-import
  mutation does bite there. **Do not add coverage** — the `len(participating_section_ids)` vs
  `len(selected)` class is already caught by phase 4's approved
  `test_c5_c6_serializers_disclose_basis_and_count_only_for_participating_sections:124`.
- **N3 — C8(b) reads `_typical_block`'s dict where the row names production-time's
  `sections[].typical` triple**, and passes `None` rather than a spec derived from `plain_task`'s
  category-less item. If B1's form (ii) is implemented this largely resolves; otherwise **declare
  the divergence**.
- **N4 — `test_c1c`'s `assert "now" not in captured` is equally true if the spy is never called**
  (`captured` is `{}` on the contract path, since `:192` passes no keywords). One line: assert the
  spy was invoked.
- **N5 — `section_ids` is built from `groups`, not `steps`** as §5A task 4 pins. **Behaviourally
  identical and strictly better** against fake sessions. No code change — **declare it**, so the
  next reviewer does not file a finding on correct work.

## Evidence

**One L4 at the end.** Everything else L1/L2. The tree is unchanged since your fix-round-2 stamp,
so **cite it for anything you do not touch**. Every probe: apply, observe, revert, verify md5,
declare.

**Re-derive the mutation ledger from §6A after your edits** — it is now
`C1 2 · C2 3 · C3 2 · C4 2 · C5 2 · C6 1 · C7 1 · C8 2` = **15 named mutations**, plus the 2
planted-defect probes = **17 rows**. Print the summands.

## Closing

Handoff to `handoffs/implementer/<date>_plan5_fix_round3_handoff.md`. Carry: B1 and B2 with their
**observed** reds · C1(b)'s per-element declaration · the four note dispositions · the re-derived
ledger with summands · write perimeter diffed · md5 table · the closing stamp with the 21-ID diff ·
**and Task 0 both ways**, since you are adding tests.

**Stop and report** rather than working around a failed gate, an unauthorized perimeter change, or
a criterion you cannot turn into a decidable assertion. **Do not push. Never `git add -A`.**
