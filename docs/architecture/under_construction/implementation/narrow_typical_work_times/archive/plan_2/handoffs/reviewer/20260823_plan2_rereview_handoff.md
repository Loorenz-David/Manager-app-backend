---
plan: plan_2
role: reviewer
round: 2
date: 2026-08-23
actor: Opus 5
verdict: APPROVED
---

# Plan 2 delta re-review — `typical_times_statement` extended for K specs

**Verdict: `APPROVED`.** 0 blocking · 0 should-fix · 4 notes · 1 owner card (graph
re-anchor authorization — **not** the item already pending).

**All five should-fix findings are closed, and four of the five are closed *and biting* —
measured here at mutant shapes nobody had run.** The fifth (S4) was a routing call, not a
code repair, and the amendment it produced is sound; my only residue on it is where the
amendment is *read*, not what it says.

The one thing that did not fully close is **N4**, and it closes as documentation rather
than as a guard: the NULL-width entry the round added is correct and complete as
enumeration, but I measured that it **cannot fail** — and in measuring it I found that
plan §6 C10's named **mutation (i) has never been run by any round, and does not do what
the plan says it does.** Nothing is wrong on the wire, the contract is guarded
structurally at the unit layer, and the correction is one paragraph of plan prose. It does
not earn a fourth round; it earns a fold.

I say the approval plainly: **this phase is done.** Three implementation rounds, one full
review and one delta re-review, no production defect ever found, and the instruments that
three rounds could not arm are now armed and measured from directions their authors did
not use.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card — the two graph entries that point at code that has moved

**Question.** May the two architecture-graph entries whose recorded code has since changed
be re-pointed at where that code now lives?

**Story.** The graph is the map agents read before touching the system. Two of its entries
were written when the code looked one way and the code has since been edited — one of them
now points at a window that begins in the middle of one function and ends inside two
others, so an agent following the map to read "how a task's governing step is chosen" lands
on three fragments of unrelated code. Neither is wrong about *what* it describes; both are
wrong about *where*. Last month's authorization covered approving and rejecting seven
entries; it did not cover moving an entry's pointer, so nobody may do this yet.

**Branches.**
- *Authorize the re-point:* a maintenance session moves both pointers; I have already
  measured exactly where they should go, so it is a short session.
- *Leave:* the map keeps two wrong addresses across phases 3–6, and each one costs the next
  agent the time it takes to notice.

**Recommendation.** Authorize it — the diagnosis is already done and recorded, so the
session executes rather than investigates.

**On silence.** Nothing is changed by any agent; the two flags stay and the gate holds.

**Trace.** `handoffs/maintenance/20260823_archgraph_queue_adjudication_handoff.md`
"Stale nodes investigated" · D28 (scoped to seven items, does not generalize) · N5.

> **This is not the entry already waiting for you.** One graph entry was rejected and
> re-recorded under D28 and sits in the queue for a normal approve/reject; it needs no
> second card and none is written here.

---

## Gate check

| # | check | result |
|---|---|---|
| 1 | `plans/plan_2.md` header `state: REVIEWING`; §8 carries the 2026-08-23 fix-round-3 consumption entry | **pass** |
| 2 | `git merge-base --is-ancestor 8718092 HEAD` | **pass** (`HEAD` = `1a0d744`, not pinned) |
| 3 | `git status --porcelain` = `?? .archgraph/contexts/` only | **pass** |

## Verified perimeter

`git diff --stat 0107c82 HEAD` — ten files, every one accounted for:

| file | owner |
|---|---|
| `app/tests/…/test_typical_times_narrowing.py`, `app/tests/…/test_typical_filters.py` | fix round 3 |
| `planning/query_cost_measurements.md`, `plans/plan_2.md`, `master_plan.md` | fix round 3 |
| `handoffs/implementer/20260823_plan2_fix_round3_handoff.md` | fix round 3 |
| `.archgraph/architecture.yml`, `.archgraph/reviews/2026-08-23T06-03-04-540Z--061a53.yml`, `handoffs/maintenance/…adjudication_handoff.md` | D28 maintenance session (`88092c6`, `731cc06`) |
| `prompts/reviewer/20260823_plan2_rereview_prompt.md` | coordinator |

**No file outside a declared perimeter.** `git diff 0107c82 HEAD -- app/beyo_manager/` is
empty — and I did not accept that as asserted: the SHA-256 of all three production files I
probe is **byte-identical to the values I recorded in round 1**, so the production tree has
not moved since my full audit. That audit stands unrevisited, as scoped.

---

## Findings — disposition of round 1

### S1 — the `K ≥ 1` branch's population definition — **CLOSED AND BITING (both branches)**

C5 gained four independently non-qualifying steps (`recorded_time_marked_wrong=True`,
`is_deleted=True`, `PENDING`, `closed_at` 91 days old), each with a distinctive `seconds`
(200–203) that moves the median if it leaks in. Literals `20` / `76` retained.

The implementer measured all four `K ≥ 1` deletions; the coordinator measured the
**inversion** (`is_(False)` → `is_(True)`, 21 failed). **Nobody measured the other
builder** — and S1's actual hazard is *divergence between the two builders*, which is
symmetric. So I mutated the **no-spec** branch.

**Probe P1 — delete `TaskStep.is_deleted.is_(False)` from `_no_spec_typical_times_statement`
only** (L2, tree `1a0d744`, `git status` clean, contract side the cited 63 passed / 1
skipped):

> **4 failed, 59 passed, 1 skipped.**
> `test_typical_times_statement_matches_pre_refactor_snapshot_at_both_clock_forms`
> **[default-clock] · [injected-clock] · [explicit-no-spec]** (C1) — and
> `test_spec_index_preserves_input_order_and_section_population_is_constant` (C5), on
> `assert base.sample_count == 20` → **`AssertionError: assert 21 == 20`**, the base row
> reading `('wsec_narrow_…', 'Narrow … 0', 21, 80)` — the median drifted 76 → 80 as well.

That is the finding closed from the direction it was actually about: the two duplicated
population builders are now **pinned to each other by literals in both directions**, and
the cross-branch assertion is the one that bites when the no-spec copy drifts. Charter rule
12 satisfied by construction — the K≥1 mutations trip the `== 20` sub-check, the no-spec
mutation trips the `base` sub-check, one mutation per sub-check.

**Note N-a (cosmetic).** The added final line
`assert all(row.section_sample_count == base.sample_count for row in rows)` is a
**tautology** given the two literal assertions above it (`row.section_sample_count == 20`
and `base.sample_count == 20`): it cannot fail once they pass. It is harmless and it
documents intent, but the guard is the pair of literals, not the equality — worth knowing
so no future round mistakes the equality for the instrument and weakens the literals.

### S2 — `narrowed_typical_worker_seconds` at `spec_index ≥ 1` — **CLOSED AND BITING**

`test_each_spec_index_selects_its_own_narrowed_typical`: `K = 2`, five groups per index
(both exactly at `TYPICAL_MIN_SAMPLE_SIZE = 5`), **distinct literal medians 30 and 80**,
both counts and both values asserted.

Two mis-key shapes were already measured (collapse-to-index-0 by the implementer, reversal
by the coordinator; each reddened exactly this test and nothing else). I ran a **third
shape neither used** — not a mis-key at all, but the failure the criterion is named for:

**Probe P2 — the narrowed *value* column publishes the *section-wide* median**
(`case((index == position, typical))` → `case((index == position, section_typical))`, K ≥ 2
coalesce only), L2:

> **1 failed, 62 passed, 1 skipped** — `test_each_spec_index_selects_its_own_narrowed_typical`,
> `AssertionError: assert 55 == 30`.

55 is the section-wide median of the ten seeded groups. **This is Critical rank 2's exact
shape** — "a section-wide median published as `item_narrowed`" — and before this round
*nothing in the phase caught it*. Exactly one test bites, and it is the one written for it.

### S3 — C0's bare-`str` enum row — **CLOSED AND BITING**

The row pins `match="must be a sequence of values"`; both enum fixtures derive from
`ItemMajorCategoryEnum.WOOD.value`. Both named mutations ran this time (S3a guard removal,
S3b one-character member with the guard removed), each reddening `[params4-major_categories]`;
the coordinator's probe C demonstrated the **contract side** positively (one-character
member, guard intact → 43 passed), which is the half that was actually in dispute.

My round-1 correction also predicted the adjacent `{"major_categories": {"wood": 1}}` row
would be armed by the same change. **It was not — it still matches only the family name.**
I measured whether that matters:

**Probe P5 — remove `Mapping` from `_optional_categories`'s isinstance guard** (L1,
`test_typical_filters.py`, contract side 43 passed):

> **1 failed, 42 passed** — `[params3-major_categories]`, **`DID NOT RAISE`**.

The mapping row's bite does not depend on its `match=` string at all: with the guard gone a
dict iterates to its keys, `"wood"` is a *valid* member, and nothing raises. The loose match
is inert, not dangerous. **Closed; the residue is not real.** (Recorded because I named it
in round 1 and it would otherwise read as an unimplemented correction — charter rule 14 in
the reviewer's direction.)

### S4 — column order vs §4A K2 — **CLOSED as decided; the amendment holds. One routing note.**

I judge **§4A K2-a sufficient on its content.** It does what a drift record has to do: it
prints the shipped tuple verbatim in its own block, states the rule that makes order
non-contractual (**read by name, never by position**), names the cost of getting it wrong
(the Critical rank 2 shape), and closes the question by observing that
`SectionTypicalEvidence`'s own field order is a *third* order — which is the argument that
makes "none of the three is a contract" true rather than convenient. It is a lettered
insertion that renumbers nothing, per the charter. Re-ordering verified-correct production
code to match prose would have bought nothing, and I agree with the call.

**Note N-b — the amendment is routed to the plan that does not call the statement, and not
to the two that do.**

| plan | names §4A K2-a in Read-first? | calls `typical_times_statement` |
|---|---|---|
| plan 3 | **yes**, explicitly | **no** — 0 occurrences, 0 `spec_index`, 0 `narrowed_*` |
| plan 4 | no (Read-first says "**§4A** K1–K4") | **yes** — `spec_index` ×3, `narrowed_sample_count` ×2 |
| plan 5 | no (Read-first says "**§4A K1** in full") | **yes** — `_typical_block` calls it **with `specs=…`** (§5 task 1) |
| plan 6 | no — despite the prompt's summary | no |

Plan 4 picks K2-a up by **physical adjacency** (it sits between K2 and K3, inside the
K1–K4 range), so it is covered in practice. **Plan 5 is not covered by either route**: it
reads `§4A K1` only, and it is a consumer. This is **N3's shape recurring on S4's own
amendment** — a rule stated well and routed to a reader who will not fire it. One line in
plan 5's Read-first (and, for cheapness, one in plan 4's) closes it. A forward pointer
inside K2's own code block would close it at the source.

### S5 — the measurement document — **CLOSED**

The paragraph discloses exactly the four things owed: cumulative seeding on one session
with positions 1–11, no `ANALYZE` (hence `cost` is a default planner estimate, which is why
`16.42` repeats across a 1-task and a 20-task seed of the identical query), `BUFFERS`
requested and unrecorded, and the 50×20 row's 1.9× stated as **undecidable from this
document**. No re-measurement, correctly — D26 sets no threshold. Nothing further owed.

### N4 / C10 row (c) — **CLOSED as enumeration; the new row CANNOT FAIL — and the criterion's own mutation is wrong**

This is the one item that does not close cleanly, and it is worth being exact about.

The fix seeds a NULL-width task in the `width` parameter, and the row's exact-literal
`narrowed_sample_count == 5` still holds. **Enumeration is complete and the behaviour is
correct.** But I checked the new row the way the prompt asked, and it does not discriminate:

**Probe P3 — C10's named mutation (i): drop the `IS NOT NULL` conjunct from
`_range_predicate`** (L1, narrowing file + `test_typical_item_filter.py`):

> **2 failed, 34 passed, 1 skipped** —
> `test_recorded_dimension_range_requires_a_non_null_dimension` (unit, structural) and
> `…[recorded-width-width_cm-recorded-width-null-width]` (row **h**, `assert 0 == 5`).
> Rows **(c) width, (d) height, (e) depth passed.**

**Probe P4 — the other candidate, `coalesce(<conjunction>, FALSE)` → `TRUE`** (C11's shape):

> **9 failed, 27 passed, 1 skipped** — every row whose "out" entry is a *missing item* or a
> *missing category* (category, major, designer, primary-less, removed-primary, and both
> threshold tests). **Rows (c), (d), (e) passed again.**

**Why, and why it matters.** `column.is_not(None)` on a NULL column evaluates to **FALSE,
not NULL**. So for a *bounded* range the conjunction is already definitely FALSE with or
without it, and `coalesce` never sees a NULL to convert. The `IS NOT NULL` conjunct is
load-bearing **only** for the unbounded `(None, None)` case — precisely what
`build_item_match`'s own docstring says, and precisely what row (h) tests.

Therefore plan §6 C10's mutation (i) — *"drop the `IS NOT NULL` conjunct from the range
rows → **rows (c), (d), (e)** flip their NULL entries out → in"* — **is false as written**,
and **no round has ever run it**: round 2's ledger carries (ii), (iii) and (iv) but not (i),
and my round-1 N4 assertion that "it bites on (d), (e) and (h)" was my own inference from
that ledger, not a measurement. It was wrong; this is the measurement.

**Why this is a note and not a should-fix.** I cannot name what breaks on the wire. NULL
dimensions *are* excluded from bounded ranges — that is SQL's three-valued logic plus the
`coalesce`, not an accident — and the contract is guarded **structurally** at the unit
layer by `test_recorded_dimension_range_requires_a_non_null_dimension`, which asserts the
compiled predicate contains `width_in_cm IS NOT NULL` and which **did** bite (doctrine rule
3: read what the code can do, not what a test observed). What is owed is a **prose
correction to plan 2 §6 C10**, folded by the coordinator: mutation (i) bites row (h) and
the unit structural row; rows (c)/(d)/(e)'s NULL entries are enumeration of the contract,
held structurally, not mutation-discriminating. **No test change, no code change, no round.**

### C8's inert median — **CLOSED, correctly, by deletion**

The equal-`100` median line is gone from
`test_primary_join_is_fanout_free_and_secondary_items_do_not_define_membership`; the count
assertion stays and remains the biting one (6 → 17 under outer attachment, measured round
2). I recommended arm-or-delete by whichever phase next edited the file; this was that
phase, and deleting was the right half of the choice given that S2's new test now pins the
value column properly. **Nothing was lost:** the only assertion removed was one I had
already measured as inert, and the value column it nominally covered is now covered by a
test that bites.

---

## The three new items — judged

### 1. §4A K2-a — **sufficient.** See S4 above; the one residue is N-b (routing), not content.

### 2. D27's two rows in `plans/plan_3.md` §6 C-N1 — **yes, they would catch what N1 describes.**

- **(a) the database backstop.** A real INSERT of a second active primary asserting
  `IntegrityError` catches an index that is dropped or renamed away. It also does the thing
  I most wanted and did not ask for: it **enumerates the partiality** — two *removed*
  primaries and a primary-plus-*related* pair must both stay legal — so a mutation that
  makes the index non-partial (dropping its `WHERE`) is caught by the legal-shapes half.
  That is charter rule 2 done properly, and it is stronger than the single row I proposed.
- **(b) the application guard.** Verified at source this session: `add_item_to_task`
  pre-selects an active primary and raises
  `ConflictError("Task already has an active primary item.")` — the criterion quotes it
  accurately, and it correctly carries S3's lesson forward by requiring the **message** be
  pinned, not just the type.

**Note N-c — one thing the rows do not determine, for plan 3's projection.** Row (a) asserts
an `IntegrityError` **and** two clean inserts in the same criterion. On a session that has
just raised `IntegrityError`, PostgreSQL aborts the transaction and every later statement
fails until a rollback or savepoint. The criterion does not say whether the legal shapes are
inserted **before** the violating one or inside a nested savepoint. Get it wrong and the row
either fails for the wrong reason or swallows its own evidence. Cheap to settle on paper
(charter rule 11½ is adjacent: a test that commits owns its teardown). Route to plan 3's
projection ledger, which is mandatory for that phase anyway.

### 3. The graph queue — **adjudicated correctly; the two stale nodes diagnosed here**

The maintenance session did exactly what D28 authorized and no more: six approved with
each cited span opened at source, one rejected and **re-recorded with the same id, left
pending** — never self-approved. It declined every mutation D28 did not name. The
coordinator's independent measurement (198 nodes / 298 edges, 1 pending / 2 stale / 0
diagnostics) matches the session's own. Master plan §8's stale "0 pending / 0 stale" is
corrected and dated. **I adjudicated nothing.**

The prompt asked what the two stale nodes are, if I could say cheaply. I can — both are
content drift, and they are **not the same kind**:

| node | link | what I measured |
|---|---|---|
| `domain-item-economics-typical-filters` | `typical_filters.py` · `_optional_values` · 78–88 | **The span is still exactly right** — `def _optional_values` is at line 78 and its body ends at 88. Only the *content* moved: plan 1's S2 fix and this phase's C0 work rewrote the isinstance guard inside it. A clean re-accept. |
| `projection-item-economics-task-production-time` | `budget_division.py` · `_governing_step` · 188–208 | **The span has drifted.** `_governing_step` now begins at line **182**; the window 188–208 covers its tail plus the whole of `_step_state_is_terminal` and the head of `_step_state_is_excluded`. Same class as N5, and **not this pipeline's doing** — the last edit there is `f904100`, a neighbouring pipeline's fix round. This one needs a re-anchor, not just a re-accept. |

Both need an authorization D28 did not grant. **Owner card above.**

---

## What I verified correct (delta scope)

- **The perimeter**, file by file, against three declared write perimeters (fix round 3,
  the D28 maintenance session, the coordinator). Zero unexplained files.
- **Production tree unmoved**, by checksum against my own round-1 declaration — not by
  reading the diff twice.
- **The three graph/doc commits are test-inert on this tree.** I checked rather than
  assumed: no test in `app/tests/` references `archgraph`, and the docs guard
  (`tests/unit/docs/`) reads only
  `docs/architecture/under_construction/implementation/**item_cost_calculation**/` — a
  different project's folder. So my tree is **test-equivalent** to the round-3 stamp's
  tree, and citing that stamp is correct rather than convenient.
- **S2's fixture clears the floor honestly**: `TYPICAL_MIN_SAMPLE_SIZE = 5`
  (`typical_constants.py:5`), both indices seed exactly five groups, and the medians 30 and
  80 are distinct from each other **and** from the section-wide 55 — which is what makes
  P2's bite meaningful rather than incidental.
- **C-N1(b)'s quoted code**, read at source in `add_item_to_task.py`.
- **N3's routing**, confirmed landed in **both** plan 3 and plan 6 Read-first lists, each
  with the conversion trigger restated in the phase's own terms. That one is fully closed.

## Evidence taken

**L4 runs: 0.** *Authorization for taking none, in the charter's own terms:* my tree and
the round-3 stamp's tree differ **only** in files no test reads (measured above, not
assumed), so the stamp is tree-bound evidence on this content and re-running it would be
over-evidence — a finding against the round.

**Consumed by citation, and corroborated arithmetically as instructed:**

| stamp | round 2 | round 3 | delta | corroboration |
|---|---|---|---|---|
| L4, `BEYO_TEST_SLOT=main`, Redis `PONG` | 21 F / 2660 P / 1 S | **21 F / 2661 P / 1 S**, ∅/∅ vs the 21-ID baseline | **+1 passed** | exactly one test was added (`test_each_spec_index_selects_its_own_narrowed_typical`) |
| L2 `working_sections/` | 62 P / 1 S | **63 P / 1 S** | **+1** | same one test |
| L1 `test_typical_filters.py` | 43 P | 43 P | 0 | the C0 repair changed fixtures and a `match=`, no row count |

The L2 figure is corroborated **independently on my own tree**, for free, without a
redundant contract-side run: P1 collected 4 + 59 = **63** and P2 collected 1 + 62 = **63**
non-skipped items. P5 collected 1 + 42 = **43**. The cited baselines are real on my tree.

**Nothing further is owed on the topology question.** My round-1 serial `-n 0` run returned
the identical 21-ID set; master plan §9 records the narrower truth (deltas are
composition-dependent, not random) and I did not revisit it.

**⚠ One L4 that is still owed, by someone else.** The charter and master plan §10 both list
**the approval gate** as an L4-required occasion. This handoff approves; the gate commit
has not been taken. Whoever takes it owes the stamp **on the tree actually committed** —
citing round 3's stamp there would be the mirror-image violation the charter names, since
the gate commit adds this handoff, the tracker row and the archive moves. Flagged so it
cannot evaporate between roles.

**Mutations — 5 probes, every one a shape no prior round ran.** Contract sides are the
cited round-3 baselines (matching content). Commands from `backend/app/`, whole files,
never `-k`:

| # | hypothesis | scope | mutation | result |
|---|---|---|---|---|
| P1 | the cross-branch guard bites from the **no-spec** side too | L2 | delete `TaskStep.is_deleted.is_(False)` in `_no_spec_typical_times_statement` **only** | **4 failed** — C1 ×3 + C5 on `base.sample_count`, `21 == 20` |
| P2 | the narrowed value column can publish the **section** median undetected | L2 | `case((index == position, typical))` → `…, section_typical))`, K ≥ 2 coalesce | **1 failed** — the new S2 guard, `55 == 30` |
| P3 | C10's named mutation (i) does what §6 says | L1 | drop `column.is_not(None)` from `_range_predicate` | **2 failed** — row (h) + the unit structural row; **rows (c)/(d)/(e) green** |
| P4 | rows (c)/(d)/(e) bite on the three-valued-logic shape instead | L1 | `coalesce(and_(*conditions), false())` → `true())` | **9 failed** — none of them (c)/(d)/(e) |
| P5 | the mapping row's still-loose `match=` matters | L1 | remove `Mapping` from `_optional_categories`'s guard | **1 failed** — `DID NOT RAISE`; the match string is irrelevant to its bite |

## Mutation-probe declaration

Applied and reverted; **SHA-256 verified byte-identical before and after**, and equal to the
values declared in my round-1 handoff:

| file | SHA-256 |
|---|---|
| `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` | `4e79395dba92dae5bce27525927890639a1ce94d692353ac370d517a78a20384` |
| `app/beyo_manager/services/queries/working_sections/_typical_item_filter.py` | `0822b3bf8079f9f3be1286e5f6969fcf7e4da1db8e4b731feb0da504f058a499` |
| `app/beyo_manager/domain/item_economics/typical_filters.py` | `7f65025565fd452cdbe14ee3451b439d504e43aa93ad0a579e86b013e7dc5076` |

`git diff` empty and `git status --porcelain` = `?? .archgraph/contexts/` at close.

**State side effects:** each probe ran under its own `BEYO_TEST_SLOT` (`rr2p1`, `rr2p1b`,
`rr2p2`, `rr2p3`, `rr2p4`, `rr2p5`); pytest drops its per-process databases at session end.
No `psql` writes. **Architecture graph: read-only — nothing listed, promoted, rejected,
edited, re-anchored or removed by this session.** Documents written: this handoff, plan 2
§8, master plan §4.

## Carry-forward dispositions

| item | destination |
|---|---|
| **N-a** C5's tautological `section_sample_count == base.sample_count` line | **record only** — do not let a later round mistake it for the instrument; the literals `20`/`76`/`base` are the guard |
| **N-b** §4A K2-a is not in plan 5's Read-first (a consumer) and only implicit in plan 4's | **coordinator fold** — one Read-first line in **plan 5**, one in **plan 4**; optionally a forward pointer inside §4A K2's own code block |
| **N-c** C-N1(a) does not determine insert order vs the aborted transaction | **plan 3 projection ledger** (round 0, mandatory for that phase) |
| **N-d** plan 2 §6 C10 mutation (i)'s bite set is wrong, and (i) has never been run | **coordinator fold into plan 2 §6 C10** — prose only; record that (i) bites row (h) + the unit structural row, and that (c)/(d)/(e)'s NULL entries are structurally held, not mutation-discriminating |
| the two stale graph source links, diagnosed above | **owner card** → a D28-style scoped authorization for a re-accept (typical_filters) and a re-anchor (budget_division) |
| the re-recorded graph item, pending | **owner**, in the normal queue — no card needed |
| §3D `ItemCategory` asymmetry; C11's conversion trigger | unchanged; both routed and both convert on their own recorded triggers |

## Lessons for the plans

1. **A symmetric hazard needs a mutation from each side.** S1 was about two builders
   diverging, and three rounds mutated only one of them. The repair was right, but the
   proof was half a proof until the no-spec side was cut. **When a criterion asserts an
   equality between two independently-written computations, the named mutations enumerate
   both operands** — candidate for master plan §9.
2. **A named mutation's stated bite set is a claim, and it decays.** C10's mutation (i) has
   sat in the plan across a projection, three implementation rounds and two reviews,
   asserting a bite set that was never true. It survived because it was never run and
   because the round-1 reviewer (me) restated it from a ledger instead of measuring it.
   **A mutation that has never been run is not evidence of anything, including of what it
   would catch** — and a plan's mutation prose should be re-derived from the code after
   each repair (charter rule 12's second half), not carried forward.
3. **`IS NOT NULL` inside a conjunction with bounds is not the guard people think it is.**
   It makes the conjunction *definitely FALSE* rather than NULL, which is why it is
   load-bearing only for the unbounded range. Any future criterion that reasons about NULL
   handling in a predicate should say **which of the two mechanisms** it is testing — the
   explicit conjunct or SQL's three-valued logic — because a fixture cannot tell them apart
   for a bounded range.
4. **Route an amendment to its consumers, not to its origin.** §4A K2-a landed in the
   Read-first of the plan that raised it and not in the Read-first of the plans that call
   the statement. This is N3's lesson recurring **inside the same phase, one finding
   later** — strong evidence that "who reads this?" belongs as an explicit line on every
   fold, not as a judgment made once per project.
5. **Deleting an inert assertion is a legitimate close, when something else now covers the
   claim.** C8's median line went away in the same round S2's test arrived. That is the
   arm-or-delete rule working: the choice is only safe because the coverage moved, and a
   round that deletes should say where the claim went. This one did.
