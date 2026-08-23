---
plan: plan_2
role: reviewer
round: 1
date: 2026-08-23
model: Opus 5
---

# Session prompt — plan-reviewer, phase 2 of `narrow_typical_work_times`

## Role and workspace

You are the **reviewer** for phase 2: `typical_times_statement` extended to compute both
populations in one pass for K specs, a new query-layer module translating a spec into an
item-match predicate, the no-spec form kept byte-identical, and the §12 query-cost matrix
measured and recorded. Two implementation rounds are behind you: round 1 built it, and a
coordinator consumption round sent it back for evidence before it reached you.

**Full two-round review.** You are the only reviewer; Sonnet is not a substitute here.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. **Never push.** **Never `git add -A`.**
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below `<project>/`).
- **Do not read `<project>/prompts/coordinator/`.**

Doctrine first, by absolute path — it wins over this prompt wherever they differ:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Gate check (stop-and-report if any fails)

1. `<project>/plans/plan_2.md` header reads `state: REVIEWING`, and its §8 Review log
   carries the **2026-08-23 fix round 2** consumption entry.
2. The fix-round checkpoint `a371e8e` is an **ancestor of `HEAD`**
   (`git merge-base --is-ancestor a371e8e HEAD`). **Do not pin `HEAD` to a SHA** — the
   coordinator commits the fold and this prompt after the round being consumed, so any
   tip-position check is stale before you read it.
3. `git status` clean at start (only `?? .archgraph/contexts/` is expected).

## Read first

- `<project>/master_plan.md` §§2, 3, 4, 6.1, 6.3, 6.6, 7, **9**, 10.
- `<project>/plans/plan_2.md` in full — **§6 for intent, then §6A, which wins wherever
  they differ.** Six criteria are untouched by §6A (C2, C4, C5, C6, C7, C11); the rest
  carry corrections. §8's Review log is the phase's history.
- `<project>/planning/intention.md` header (the section-letter precedence rule), then
  **§3A**, **§4A** K1–K5, §4B, **§3D**, **§12A**.
- `<project>/planning/owner_decisions.md` — **D26** (no performance threshold).
- The three implementer handoffs in `<project>/handoffs/implementer/`
  (`…plan2_implementation_handoff`, `…plan2_fix_round2_handoff`) and the projection
  handoff in `<project>/handoffs/reviewer/`.

## What has already been verified — do not re-derive it

Stated so your budget goes to what is genuinely open. All of this was measured, not read
off a ledger; **if you doubt any of it, re-measure it and say so** — but do not spend the
round reproducing it by default.

- **The production diff across the entire fix cycle is empty.**
  `git diff d5731c3 HEAD -- app/beyo_manager/` returns nothing: round 2 changed tests, a
  harness label and docs only.
- **K1's repair is armed, confirmed with a mutant shape the implementer did not run.**
  Round 1's C5 test asserted counts only, and a group-seconds `* 2` probe left it green
  while reddening three neighbours. After the repair, `percentile_cont(0.5) → 0.9` in the
  `K ≥ 1` section aggregate — which moves the section median and leaves **every** count
  untouched — reddens
  `test_spec_index_preserves_input_order_and_section_population_is_constant`.
- **The seven previously-unrun named mutations were run in round 2** with both sides and
  failing test ids, on stated dirty-tree SHAs, applied-and-reverted.
- **The §12 conditional acceptance is met**: eleven rows, five copies disclosed as
  constant-by-construction, exact seed cardinalities, no threshold claimed (D26).

## Depth areas — where this phase is most likely to be wrong

Ranked. These are the mechanisms, **not** predicted conclusions; confirm or refute each.

1. **The two branches each declare their own `grouped_steps`.**
   `_no_spec_typical_times_statement` re-states the workspace / `COMPLETED` /
   `is_deleted` / `recorded_time_marked_wrong` filters and the group-by that the `K ≥ 1`
   builder states independently. **C1 freezes the no-spec branch's SQL *shape* only** — and
   the boxed limitation in §6 C1 spells out that no bound value is visible to it. Ask what
   fails if a later phase changes the `K ≥ 1` population filters and not the other. Is
   anything guarding the two against divergence?
2. **`uix_task_items_primary_active` is untested repo-wide, and C8's fan-out-freedom rests
   on it.** §6A recorded this (L33/R10) as "recorded, not fixed here"; round 2 declined it
   again, citing budget. It appears in the model, two migrations and docs — no test. Judge
   the deferral: is it acceptable for the phase whose central join depends on it, or is one
   criterion row owed here rather than later?
3. **The `K ≥ 2` column construction and its `K == 1` bypass.**
   `narrowed_sample_count` / `narrowed_typical_worker_seconds` are built as
   `coalesce(case(index == 0, …), case(index == 1, …), …)` for `K ≥ 2`, but the `K == 1`
   path returns the bare aggregate and never enters the coalesce. Two code paths, one
   contract. Check the count-0 vs NULL boundary, and check how much of the fixture set
   actually exercises `K ≥ 2`.
4. **C11 is a string-containment assertion** (`"coalesce" in compiled`) that the plan
   itself labels an interim instrument with a named conversion trigger. Judge whether the
   trigger is stated well enough to fire.
5. **C8 took option (b), authorised.** The fixture seeds six identical `100`s, so the
   median assertion cannot move; the count assertion bites under the shipped outer
   attachment, and the median is documented as a control. §6A required the disclosure and
   it was made. Judge whether a documented control is the right call or whether the
   fixture should vary.
6. **C13(b)'s coverage claim is loosely stated.** The handoff says the six consumer suites
   were "covered by the L2 run or round-1 green evidence". Measured: the L2 run was
   `tests/…/working_sections/`, which holds **one** of the six
   (`test_typical_times_query.py`); the other five are under
   `tests/integration/services/queries/item_economics/` and rest on the L4 stamp, which is
   green. True via L4, imprecise as written. Confirm and rank it.
7. **`ItemCategory`'s join carries neither `workspace_id` nor `is_deleted IS FALSE`** while
   the `Item` join carries both — so a soft-deleted category still satisfies
   `major_categories`. This is **recorded upstream as intention §3D with a conversion
   trigger, deliberately unchanged** because `major_categories` has no V1 producer. Confirm
   the code matches what was recorded; do not re-litigate the decision.
8. **The measurement doc's honesty, not its numbers.** D26 sets no threshold, so no value
   blocks the phase. The tables are 20 and 50 rows — small enough that the timings are
   mostly planning overhead. Judge whether the document says what it actually measured.

## ⚠ The full-suite baseline is nondeterministic — measured, and it changes how you read a stamp

Do not treat either L4 stamp as a stable comparator.

- Round 1 stamped **24 failed**, including three ids in
  `tests/integration/models/users/test_user_work_profile_clock_in_code.py`.
- Round 2 stamped **21 failed** with a **∅/∅** delta against the approved 21-ID set, and
  those three absent.
- At `HEAD` those same three still fail **3/3 when run alone**.

Same tree, different scheduling. The cause is diagnosed and **out of this phase's
perimeter**: that file predates the phase (`b0f35b1`), and its `_two_workspaces` helper
does `SELECT … FROM workspaces LIMIT 2` and asserts two rows exist — it consumes whatever
state leaked into its xdist worker. Under `--dist loadfile` the partition is decided by
worker availability, so which neighbours a file gets varies run to run.

**Consequence for your review: round 2's clean ∅/∅ delta is partly scheduling luck, and an
unexplained delta is not automatically a regression.** Routed to the `test_isolation_xdist`
project; **do not repair it here** and do not rank it as a phase-2 finding.

## Evidence budget

**Your tree's code content matches the implementer's L4 stamp** (checkpoint `a371e8e`;
everything after it is docs-only). Re-running `pytest -m 'not e2e'` in the same
configuration would be **over-evidence on a matching SHA** — consume the round-2 stamp by
citation and corroborate it arithmetically instead.

**Spend your one L4 on variation that answers an open question: run it serially, `-n 0`.**
That is the comparator the environment section names, it has not been run on this tree, and
it directly probes the nondeterminism above — a serial failing set that differs from the
parallel one is a measured finding worth more than a repeated parallel run. Expect it to be
slower than the ~52 s parallel run. Check Redis first (`redis-cli ping`); without it the
baseline reads 23 failed / 2 errors instead of 21.

Otherwise: mutations at **L1 hypothesis scope** — whole files, **never `-k`**. Where you
challenge a criterion, prefer a **mutant shape nobody has run** over repeating one from a
ledger; that is what turned K1 from a re-worded claim into a confirmed repair.

## Environment (master plan §10 is authoritative)

From `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`; xdist 6 workers is in `addopts`,
`-n 0` is the serial comparator. Databases: server `localhost:5433`, per-process disposable
templates — **never run two suite sessions concurrently in this checkout**, they share the
DB slot and destroy each other's databases. The documented default is
`BEYO_TEST_SLOT=main`; round 2 discarded a non-default-slot run as non-authoritative and
disclosed it.

Orient the graph read-only at start (`archgraph_status` +
`.archgraph/contexts/current-task.md`, untracked, never rebuilt or committed). **Never
promote, reject or edit a review item** — architecture-graph adjudication is the owner's
alone.

## Output

Handoff at `<project>/handoffs/reviewer/20260823_plan2_review_handoff.md`, frontmatter
`plan: plan_2`, `role: reviewer`, `round: 1`, `date`, `actor`, `verdict`.

- **Verdict**: `APPROVED` or `CHANGES_REQUESTED`. Approving a phase that later ships a
  defect is worse than one more round; so is a round manufactured out of a finding that
  cannot name what breaks on the wire.
- **An owner card** for anything only the owner can decide — a product-semantic question, a
  scope trade, a cost the owner should accept or refuse. Zero is a fine answer.
- Ledger rows ranked **blocking / should-fix / recorded**, each naming the criterion or
  contract it attaches to, what breaks observably, and the evidence you took.
- **Say which of the depth areas above you confirmed and which you refuted** — a refuted
  hypothesis is a result, and phase 1's review earned its value partly by refuting two.
- Final chat message is the charter's **owner layer**: what you did → what it means → what
  happens next → what needs the owner; one pointer line naming the handoff.
