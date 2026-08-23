---
plan: plan_2
role: implementer
round: 2
date: 2026-08-23
---

# Session prompt — implementation-executor, phase 2 **fix round 2**

## Role and workspace

You are the **implementer** closing a coordinator-consumption round on phase 2 of
`narrow_typical_work_times`. **Round 1's production code is accepted as-is** — do not
redesign the statement, the predicate module or the measurement harness. This round is
almost entirely about **evidence**: mutations the plan named that were never run, and two
fixtures that cannot fail.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. **Never push.** Commits use **explicit paths only, never `git add -A`**.
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below `<project>/`).

Doctrine first, by absolute path — it wins over this prompt wherever they differ:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

## Gate check (stop-and-report if any fails)

1. `<project>/plans/plan_2.md` header reads `state: IMPLEMENTED`, and its §8 Review log
   carries the **2026-08-23 coordinator consumption** entry.
2. `git status` clean at start (only `?? .archgraph/contexts/` is expected).
3. Round 1's checkpoint `d07028b` and handoff `406b097` are **ancestors of `HEAD`**
   (`git merge-base --is-ancestor 406b097 HEAD`), and the coordinator's consumption fold
   `a4e41f6` is present. **Do not pin `HEAD` to a particular SHA** — the coordinator commits
   the fold and this prompt *after* the round it is consuming, so anything that pins the tip
   is stale before you read it. `HEAD` at your start is expected to be `a4e41f6` or a later
   docs-only commit.

*(Corrected 2026-08-23 after this prompt's round 1 stopped here: the gate named
`406b097, d07028b` as the two latest commits, which was true while I drafted it and false
the moment I committed the fold at `a4e41f6`. **Second instance of a coordinator gate
describing a state its own commit invalidates** — see master plan §3. Stopping was correct
both times; nothing below the gate changed.)*

## What round 1 got right — do not touch it

Stated so you spend the round on the gaps and not re-auditing settled work:

- The `K ≥ 1` shape is **exactly** §6A's mandated form — outer `VALUES` cross join on
  `spec_index`, added to the outer `GROUP BY`. The K-multiplication hazard is **not**
  present in the code.
- C1's three parametrized rows, the corrected `delete the len(specs) == 0 branch`
  mutation, and the untouched snapshot file: all correct.
- C0's five parser rows (bytearray, memoryview, dict, major-dict, bare `str`) all landed.
- C12's corrected instrument (`count("LEFT OUTER JOIN item_categories")`, both specs
  narrowing on another field) landed.
- C9 is built as specified, with the `specs=()` half correctly labelled a control.
- `query_cost_measurements.md` carries all eleven rows, the five copies are disclosed,
  and no threshold is claimed. **The plan header's conditional acceptance is met.**
- The outer-attachment choice and the bound-`workspace_id` decision are accepted and
  were correctly disclosed in the handoff.

## ⚠ K1 — BLOCKING, and this one is measured

**C5's closing clause was not transcribed, and the consequence is that the criterion
§6A named as the owner of the phase's sharpest hazard does not guard it.**

Plan §6 C5 ends: *"Assert `section_sample_count == 20` at **every** `spec_index`, and equal
to the `K == 0` call's `sample_count` for the same section; **likewise
`section_typical_worker_seconds`**."* §6A lists C5 among the six criteria transcribable
**as written**, and §6A's "Where the K-multiplication hazard actually lives" section names
**C5 as the guard**.

`test_spec_index_preserves_input_order_and_section_population_is_constant` asserts only
counts, and asserts them as `{row.section_sample_count for row in rows} == {base.sample_count}`
— computed against computed, with no literal anywhere.

**Measured on your tree (2026-08-23):** mutating the `K ≥ 1` `grouped_steps`
`func.sum(TaskStep.total_working_seconds)` to `* 2` — the observable signature of the
K-multiplication — reddens **three** tests in
`test_typical_times_narrowing.py`, and **that test is not one of them**. A group-seconds
multiplication changes the median and leaves `count(task_id)` untouched, so a
counts-only criterion cannot see it. The hazard is covered today only **accidentally**, by
C8's and C9's `== 100` assertions.

**Required:**
- Assert `section_typical_worker_seconds` at every `spec_index` **and** against the
  `K == 0` call's `typical_worker_seconds`.
- Assert both columns against **literals**, not only against `base` (§6A/L32's rule for
  C2 row (d) is the same rule; C5 has the same shape).
- Give the fixture a **median that a multiplication moves and that is not the mean** —
  round 1's fixture seeds every task at the default `seconds=100`, so several mutations
  are invisible in it. Clear `TYPICAL_MIN_SAMPLE_SIZE` on both populations.
- **Run the `* 2` mutation yourself** and record that this test is now among the reddened
  ids. That is the row's whole point.

The plan's fixture is "narrowed 6, section 20"; round 1 shipped 6 + 2 = 8. Either seed the
plan's numbers or state in the handoff why the smaller one is sufficient — but the
**literals must appear in the assertions either way**.

## ⚠ K2, K3, K4 — BLOCKING: seven named mutations were never run

The plan names mutations **one per sub-check**. Round 1's ledger reports one per criterion.
Run the missing ones and record, for each, **both sides and the failing test id**.

| criterion | named mutation | status |
|---|---|---|
| **C6** (ii) | `>=` → `>` in the **narrowed** `CASE` | **not run** — row (b) (`narrowed_count == TYPICAL_MIN_SAMPLE_SIZE`) flips non-`None` → `None`; row (c) does not bite |
| **C7** (ii) | move `role == PRIMARY` from the `ON` clause into the statement's `WHERE` | **not run** — the plan calls (ii) and (iii) *"the likelier slips"* |
| **C7** (iii) | move `removed_at IS NULL` from the `ON` clause into the `WHERE`, on a fixture whose one primary-less task instead has a **removed** primary | **not run** — note this needs a *fixture variant*, not only a code edit |
| **C10** (ii) | emit `TRUE` for `(None, None)` instead of `IS NOT NULL` | **not run** — row (h)'s `narrowed_sample_count` doubles |
| **C10** (iii) | join the fields with `or_` instead of `and_` | **not run** — row (i)'s `sofa, width 70` flips out → in |
| **C10** (iv) | `IN` → `NOT IN` on `item_category_ids` | **not run** — row (a) flips both directions |
| **C1** control | delete `WorkingSection.is_deleted.is_(False)` (plan 1's C15 mutation, kept as C1's structural control) | **not run** |

**C10 additionally reported the wrong instrument.** The ledger attributes C10 to
`test_recorded_dimension_range_requires_a_non_null_dimension` — a **unit** test asserting
the substring `"width_in_cm IS NOT NULL"` in a compiled predicate. Plan §6 C10 says
*"**Both sides** are exact-literal `narrowed_sample_count` values per row"*: C10 is an
**integration** criterion (§6A/L14 assigns it explicitly). Keep the unit row if you like,
but C10's recorded both-sides must be integration counts.

## N1, N2 — two rows that cannot fail

**N1 — C2 row (d).** `test_k_shape_is_keyed_by_spec_count_and_non_narrowing_k1_is_seven_columns`
seeds **one** task, so `narrowed_typical_worker_seconds == section_typical_worker_seconds`
compares `None` to `None`. This is the fixture-below-the-floor defect §6A **opens with**,
landing inside a criterion §6A called transcribable as written. §6A/L32 already required
both asserted **against the literal count**; do the same for the typicals. Clear the floor.

**N2 — C8's median half is inert, and the disclosure is missing.** Every group in
`test_primary_join_is_fanout_free_and_secondary_items_do_not_define_membership` seeds
`seconds=100`, so `median == 100` survives any fan-out multiplicity. §6A predicted exactly
this for outer attachment and required you to **"say which assertion bites on which
strategy."** Two acceptable closes, and you may pick either — **but say which you picked**:
(a) vary the seeded seconds so the median moves under the mutation, or (b) keep the fixture
and record in the ledger that under the shipped outer attachment the **count** assertion is
the biting one and the median is a documented control.

## Smaller, non-blocking — fix or justify in the handoff

- **C3's fixture is smaller than the plan enumerates.** Plan: 3 live + 1 soft-deleted,
  `K = 2`, **6 rows**. Shipped: 2 live + 1 soft-deleted, **4 rows**. All three section
  roles are present so the substance holds — but the reduction is undisclosed. Restore the
  enumerated fixture or state why 4 rows prove what 6 would.
- **C10 row (f) was replaced, not added.** §6A said *add* a `can_have_upholstery=False`
  row; the plan's row (f) (`can_have_upholstery=True`, in `True` / out `False`) is gone.
  Keep both — the `False` row catches the falsy-drop bug, the `True` row is the ordinary case.
- **C10 row (c)'s upper boundary is untested.** The plan enumerates in-values **60 and 80**;
  the fixture seeds 60–64. Seed 80.
- **C13(b) has no ledger row.** Five suites in §6 plus `test_phase2_live_surfaces.py`
  (§6A/L18) must be green **with no edits**. The perimeter shows no edits and the L4 stamp
  covers greenness — name them in one row so the claim is recorded rather than inferred.
- **C0's per-row mutations.** §6A/L3 asked for a named mutation for rows 1, 2 and 4; one is
  reported. The tests themselves are all present and correct.
- **`_narrowing_seed.py` stamps a false column.** Every step is seeded at
  `MEASUREMENT_NOW - timedelta(days=1)` (`:116`), and each result row records
  `"history_span_days": HISTORY_SPAN_DAYS` = **90**. The *document* is honest ("all closed
  one day ago inside the 90-day window") — the **harness label** is not, and the harness is
  committed for reproducibility. Rename it to what it measures (e.g. `history_age_days: 1`,
  or `window_days: 90` alongside it). **Do not re-run the matrix** — the numbers stand;
  this is a label fix. If you do re-run, say so and replace the table wholesale.

## Not yours — do not act on it

The L4 stamp's three extra failing ids
(`tests/integration/models/users/test_user_work_profile_clock_in_code.py`) are **not a
phase-2 regression** and are **not in your perimeter**. Diagnosed on your tree: that file
predates this phase (`b0f35b1`), and its `_two_workspaces` helper (`:33-38`) does
`SELECT ... FROM workspaces LIMIT 2` and asserts two rows exist — it consumes whatever
workspaces leaked from earlier tests in its xdist worker. Run alone it fails 3/3 with
`assert 0 == 2`. Phase 2 touched no fixture and no conftest; adding one integration **file**
re-partitioned `--dist loadfile` and changed that file's neighbours.

**Your obligation is reporting, not repair.** Expect the same three ids in your L4 stamp
and record them as *known, diagnosed, out of perimeter*. Routed to the
`test_isolation_xdist` project.

## Evidence budget

- Every mutation runs at **L1 hypothesis scope** — whole files, **never `-k`**. C7, C8 and
  C9 name cross-file bite sets and run at L2.
- **Exactly one L4 stamp** closes the cycle, on the tree you hand over, with the
  failing-ID delta against the 21-ID set **in both directions**, plus the three diagnosed
  ids above named as known. Check Redis first — without it the baseline reads 23 failed /
  2 errors instead of 21.
- **State, per mutation, which test id failed** — the id, not "the file reddened".
- Round 1's already-run mutations are **tree-bound evidence on a matching SHA**: cite them
  by their round-1 ledger row, do not re-run them. Spend the budget on the seven that were
  never run.

## Closing protocol

1. Perimeter green; every mutation in this prompt run with both sides and its failing id.
2. Update `plans/plan_2.md` §8 (append; the state stays `IMPLEMENTED` until review) and
   `master_plan.md` §4 row 2's note.
3. **Checkpoint commit**, subject prefixed `CHECKPOINT (not approved): `, explicit paths.
   Never squash, never push.
4. Handoff at
   `<project>/handoffs/implementer/20260823_plan2_fix_round2_handoff.md`, frontmatter
   `plan: plan_2`, `role: implementer`, `round: 2`, `date`, `actor`. Body: owner-readable
   opening; a table with **one row per item in this prompt** and its disposition
   (fixed / justified / declined-with-reason); the full mutation ledger with both sides and
   failing ids; the L4 stamp; the write perimeter from `git status`; the checkpoint SHA.
5. Final chat message is the charter's **owner layer**: what you did → what it means →
   what happens next → what needs the owner; one pointer line naming the handoff.
