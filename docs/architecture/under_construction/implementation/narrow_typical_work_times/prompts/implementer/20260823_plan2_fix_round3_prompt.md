---
plan: plan_2
role: implementer
round: 3
date: 2026-08-23
---

# Session prompt — implementation-executor, phase 2 **fix round 3** (post-review)

## Role and workspace

You are the **implementer** closing the phase-2 review. The reviewer's verdict was
`CHANGES_REQUESTED` with **0 blocking findings and no defect in the production code** — it
audited the statement against §4A K4 line by line and found it correct. **This round changes
no production code.** Every item is a test fixture, an assertion, a `match=` string, or a
paragraph of prose.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. **Never push.** **Never `git add -A`** — explicit paths only.
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below `<project>/`).

Doctrine first, by absolute path — it wins over this prompt wherever they differ:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## Gate check (stop-and-report if any fails)

1. `<project>/plans/plan_2.md` header reads `state: CHANGES_REQUESTED`, and its §8 Review
   log carries the **2026-08-23 review round 1** entry.
2. The fix-round-2 checkpoint `a371e8e` is an **ancestor of `HEAD`**
   (`git merge-base --is-ancestor a371e8e HEAD`). **Do not pin `HEAD` to a SHA.**
3. `git status` clean at start (only `?? .archgraph/contexts/` is expected).

## Read first

- `<project>/handoffs/reviewer/20260823_plan2_review_handoff.md` **in full** — it carries
  the measured both-sides for every item below, and its "What I verified correct" section
  tells you what not to re-audit.
- `<project>/plans/plan_2.md` §6 **as corrected by §6A**, and §8's Review log.
- `<project>/master_plan.md` §9 — four new rules were earned from this review and they are
  what these fixes are *for*.

## The through-line: three guards that cannot fail

S1, S2 and S3 are one defect at three layers, and it is worth seeing before you fix them
individually. In each case **a row exists, the assertion looks right, and nothing can move
it** — because the fixture contains no row the mutation touches, or the assertion matches
too loosely to discriminate. The rule master plan §9 now carries: *after naming the
mutation and the column, confirm the fixture contains a row the mutation moves.*

Round 2 fixed three instances of this class. This review found three more. Expect to be
asked "what makes this row fail?" for every row you touch.

---

## S1 — the `K ≥ 1` branch's population definition is guarded by nothing

`typical_times_statement` and `_no_spec_typical_times_statement` each declare their **own**
`grouped_steps`, restating the same four filters and the same 90-day cutoff. C1 freezes the
**no-spec** branch's SQL shape. Nothing constrains the `K ≥ 1` copy.

C5 looks like the guard — it asserts `section_sample_count == 20` at every `spec_index`
*and* against the `K == 0` call — but every fixture in the file seeds only steps that are
`COMPLETED`, not deleted, not marked wrong, and closed one day ago. **There is nothing for
the equality to discriminate.**

**Measured by the reviewer** (L2, `tests/unit/services/queries/working_sections/` +
`tests/integration/services/queries/working_sections/`, contract side 62 passed / 1
skipped). Each deletion is in the `K ≥ 1` branch only:

| mutation | result |
|---|---|
| delete `TaskStep.recorded_time_marked_wrong.is_(False)` | **62 passed — no bite** |
| delete `TaskStep.state == TaskStepStateEnum.COMPLETED` | **62 passed — no bite** |
| delete `TaskStep.is_deleted.is_(False)` | **62 passed — no bite** |
| `qualifying = latest_closed_at >= cutoff` → `true()` | **62 passed — no bite** |

**Fix.** Add four discriminating rows to C5's fixture — one step
`recorded_time_marked_wrong=True`, one `is_deleted=True`, one non-`COMPLETED`, and one
`closed_at` outside the 90-day window — so that `section_sample_count == 20` at every index
*and* `== base.sample_count` becomes a real divergence assertion between the two branches.
**Keep the literals**: the count and the median (`76`) must both stay pinned to literals,
and adding non-qualifying rows must not change either. Then **run all four mutations above**
and record each one's failing test id.

**Note what you are actually building**: the first criterion in this project that asserts
the two duplicated builders *agree*. Say so in the ledger.

## S2 — `narrowed_typical_worker_seconds` is never asserted at any `spec_index ≥ 1`

For `K ≥ 2` both narrowed columns are `coalesce(case(index == 0, …), case(index == 1, …),
…)`. The **count** column is pinned per index; the **value** column is not — across the
whole file it is asserted non-`None` only at `spec_index == 0` and on `K == 1` paths.

**Measured by the reviewer**, the contrasting pair, same scope and command:

| mutation | result |
|---|---|
| `case((index == position, typical))` → `case((index == 0, typical))` on the **typical** coalesce | **62 passed — no bite** |
| the same mutation on the **count** coalesce | **3 failed** |

Under the mutant, a section's narrowed median at `spec_index ≥ 1` returns `NULL` (the task
silently falls back to the section-wide typical) **and** `spec_index 0` inherits a *later*
spec's median whenever its own count is below `TYPICAL_MIN_SAMPLE_SIZE`. That is plan §6
C4's stated *Defect caught* — "one item category's history attributed to another task",
Critical rank 2 — live on the value column.

**Fix.** One `K = 2` row where **both** indices clear `TYPICAL_MIN_SAMPLE_SIZE` with
**different** medians, asserting each index's **literal** `narrowed_typical_worker_seconds`.
**The existing C4 fixture cannot be reused as-is** — its index 1 has 2 groups by contract,
so it can never produce a typical. Then run the typical-coalesce mutation and record the id.

## S3 — C0's bare-string enum row cannot tell an explicit rejection from an accidental one

C0's *Contract* is explicit: *"the enum family rejects a bare `str` **explicitly**, never by
accident of member length."* The row asserts
`pytest.raises(ValidationError, match="major_categories")` — and **both** messages contain
the family name: the explicit guard's `"major_categories must be a sequence of values."`
and the accidental path's `"major_categories contains an unknown value."`

**Measured by the reviewer** (L1, `tests/unit/domain/item_economics/test_typical_filters.py`):
removing `str` from `_optional_categories`'s
`isinstance(raw, (str, bytes, bytearray, memoryview, Mapping))` guard → **43 passed, no
bite.** `"wood"` iterates character-wise, `ItemMajorCategoryEnum("w")` raises `ValueError`,
and the `except` arm raises the *other* `ValidationError`, which `match=` still accepts.

**Fix.** Pin the message, not the family: `match="must be a sequence of values"`. The
accidental path does not produce it. The same change arms the
`{"major_categories": {"wood": 1}}` row, which currently bites only by luck of ordering.
Then run the guard-deletion mutation and record the id.

**Also run C0's second named mutation.** §6 C0 names two; round 1 ran one and round 2
declined the second as "justified by round-1 tree-bound ledger row" — **the round-1 row does
not cover it**, so the stated reason does not hold (charter rule 14). The mutation is:
shorten a test enum member to one character in the `major_categories` row's fixture, and
confirm the bare-`str` row still rejects **explicitly** rather than by accident of length.

## S4 — decided for you; do not re-litigate, but do transcribe

The shipped `K ≥ 1` column order is the reverse of intention §4A K2's prose. **The shipped
order stands** — the coordinator amended the intention as **§4A K2-a**: the column *set*
and *names* are contractual, the *order* is not, and results are read by name, never by
position. Plans 3 and 6 now read it.

**Nothing to change in code or in C2** (C2 already pins the shipped tuple, which is the
accurate one). Your only task: **do not "fix" the order**, and note in the ledger that C2's
tuple was confirmed against §4A K2-a rather than K2's superseded prose.

## S5 — the measurement document, one paragraph

`collect_measurement_matrix` loops all eleven cases on **one** `db_session` with no cleanup,
so each row is measured against a table holding every previous row's seed — by the last row
`task_steps` carries ~232 seeded rows across eleven workspaces. The document's *"Seed
cardinalities are exact for every row"* is true of each **workspace's** seed, not of the
**table**. It shows in the document's own numbers: the same query costs **0.060 ms** at
position 5 and **0.087 ms** at position 10.

**Do NOT re-measure** — D26 sets no threshold and §12's conditional acceptance is met in
full. Add **one paragraph** to `planning/query_cost_measurements.md` recording:
- the seeding is **cumulative**, and each row's **position** in the sequence;
- **no `ANALYZE`** was run, so the `cost` column is a default-estimate — which is why it
  reads `16.42` for both the 1-task and the 20-task seed of the identical query — and say
  what the column means;
- the harness requests `BUFFERS` and records none.

State plainly that whether the 50×20 row's 1.9× is spec fan-out or table growth is
**undecidable from this document**. An honest limitation beats a clean-looking table.

## N4 — one missing enumerated value

C10 row (c) lists three out-values for `width_cm=(60,80)`: **59, 81 and `NULL`**. The test
seeds 59 and 81 only. The mutation is covered elsewhere (it bites on rows (d), (e), (h)) —
the row's own enumeration is not. Seed the `NULL` width. Charter rule 2.

## Also fold in: C8's decorative median line

The reviewer accepted C8's option (b) for this phase and recommended that **whichever phase
next edits this file** either arm the median line or delete it. **That is this round** —
you are editing the file. Six identical `100`s is the inert fixture master plan §9 warns
about, sitting inside an otherwise armed criterion. **Arm it** (five distinct group values
so a fan-out moves the median) **or delete the line** and keep the count assertion, which
bites hard (6 → 17 rows). Say which you chose and why.

## Not in scope — do not do these

- **No production code changes.** The reviewer found no defect in it. If you believe a fix
  requires one, **stop and report** rather than making it.
- **The one-active-primary rows are plan 3's**, by owner ruling **D27**. Do not add them here.
- **The architecture-graph queue is a separate authorized maintenance session** (**D28**).
  Do not adjudicate, promote, reject or edit any review item. The stale evidence span (N5)
  is re-recorded there, not here.
- **The clock-in-code trio** is out of perimeter and now better understood: the reviewer's
  serial `-n 0` L4 returned the **identical 21-ID set**, so the baseline is stable across
  worker topologies on this tree. Those three fail only when run **alone**. Expect 21.

## Evidence budget

- Mutations at **L1 hypothesis scope** — whole files, **never `-k`**. S1/S2 run at L2
  (`tests/unit/services/queries/working_sections/` +
  `tests/integration/services/queries/working_sections/`); S3 at L1.
- **State, per mutation, which test id failed** — the id, not "the file reddened".
- The reviewer's probes are **tree-bound evidence on your SHA**: cite the contract-side
  baselines (62 passed / 1 skipped at L2; 23 passed / 1 skipped focused) rather than
  re-deriving them. Spend your budget on the **post-fix** side — every mutation above must
  now **bite**, and that is the whole point of the round.
- **Exactly one L4 stamp** closes the cycle, with the delta against the 21-ID set in both
  directions. Check Redis first (`redis-cli ping`); use the documented default
  `BEYO_TEST_SLOT=main`.

## Closing protocol

1. Perimeter green; every mutation above run **post-fix** with both sides and its failing id.
2. Update `<project>/plans/plan_2.md` §8 (append) and `master_plan.md` §4 row 2's note.
   The state moves to `IMPLEMENTED` for re-review.
3. **Checkpoint commit**, subject prefixed `CHECKPOINT (not approved): `, explicit paths.
4. Handoff at
   `<project>/handoffs/implementer/20260823_plan2_fix_round3_handoff.md`, frontmatter
   `plan: plan_2`, `role: implementer`, `round: 3`, `date`, `actor`. Body: owner-readable
   opening; one row per item in this prompt with its disposition; the mutation ledger with
   both sides and failing ids; the L4 stamp; the write perimeter from `git status`; the
   checkpoint SHA. **If your production diff is not empty, say so in the opening sentence.**
5. Final chat message is the charter's **owner layer**: what you did → what it means → what
   happens next → what needs the owner; one pointer line naming the handoff.
