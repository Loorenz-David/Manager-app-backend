---
plan: 2
role: review
round: 3 (re-review)
verdict: APPROVED
date: 2026-08-17
actor: Opus 5 (reviewer)
---

# Re-review round 3 — plan 2 (fix r2 verification)

**Verdict: APPROVED.** 0 blocking, 0 should-fix, 9 notes — all carried forward, none
blocking the gate.

All seven r1 findings are closed, and — the part that matters — **closed by guards that
can now fail**. I applied a named mutation at the definition site for each of the four
findings the coordinator did not probe (S2/C1b, S4/C25b, C6b, C6c) plus S5/C27, and every
one produced red at the expected assertion with the expected message. The two fixtures
that r1 caught surviving their own mutations now bite.

Nothing was loosened. Across the entire test diff `aa95d5e → f904100`, nine assert lines
were added and exactly one exact assertion was deleted without replacement; I probed
whether that deletion cost coverage and it does not (N1 — the surviving criterion pins the
same value transitively, proven by drifting it one unit and watching C27 go red). No `==`
anywhere became an inequality or a membership test.

Suite re-derived independently, not taken from the handoff: **2313 passed / 26 failed / 1
deselected**, failure IDs diffed against the set I captured myself in r1 — **0 added, 0
removed**. The +2 is C1b and C6c.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. D16 was ratified in r1 and is implemented as ratified.

---

## Closure table — r1 finding → closed? → which test bites on which mutation

Per the **criterion-kind rule** (master plan §6, earned this phase), each row names the
test that reddens, not the criterion.

| r1 finding | Closed | Mutation applied at its definition site | Test that bites | Observed |
|---|:--:|---|---|---|
| **B1** governing step never consults liveness | ✅ | delete the liveness partition in `_governing_step` | `test_c4_c6a_c6b_c25a_c25b_...` (DB) **and** `test_c6_later_live_step_governs_section_state` (unit) | coordinator-verified; both rows red. The DB row **survived** this exact mutation in r1 |
| **B1(b)** `entered_at`/`created_at` precedence inverted | ✅ | swap the two `candidates.sort` calls back to r1's order | `test_c6c_multi_open_governing_precedence_...` | `AssertionError: assert 'working' == 'pending'` |
| **S1 / D16** `share_state` vs `left_seconds` | ✅ | compare non-excluded worked seconds instead of the total | `test_c8_c9_...` (DB) + `test_excluded_consumption_...` (unit) | coordinator-verified `worked=110 allowance=10 left=-100 share_state=over_share` |
| **S2** C1's `name` tie-break unguarded | ✅ | replace the `name` component of `_section_sort_key` with `""` | `test_c1b_reversed_insertion_order_keeps_name_tie_break` | **1 failed, 26 passed** — and it is the *only* test that reddens. In r1 this same mutation left the whole suite green |
| **S3(a)** C6's DB row does not guard | ✅ | (as B1) | `test_c4_c6a_c6b_c25a_c25b_...` | coordinator-verified |
| **S3(b)** `state_entered_at` zero coverage | ✅ | read `entered_at` from `group["steps"][0]` instead of `governing` | same DB row | `assert '2026-08-17T11:00:00+00:00' == '2026-08-17T10:00:00+00:00'` |
| **S3(c)** C6c vacuous | ✅ | (as B1(b)) | `test_c6c_...` | red at level 1-vs-2 of the precedence |
| **S4** snapshot from query order, no `ORDER BY` | ✅ | take the first non-null snapshot in group order (the pre-fix code) | same DB row | `assert 'Upholstery' == 'Upholstery installation'` |
| **S5** P-PROP not restated at the section unit | ✅ | flatten `resolved_weights` to `Fraction(1,1)` | `test_budget_allocation_uses_shared_typicals_for_section_proportional_split` | `assert 2400 == (2 * 2400)` |
| **S6** perimeter not declared by path | ✅ | perimeter audit, not a runtime test | `git show --name-only f904100` = 6 files; **all 6 declared, 0 undeclared** | see N4 for the inverse defect |

**Seven of seven closed.**

---

## Precedence-disagreement audit (the round's main instrument)

Every new or amended fixture, against master plan §6's rule: *does the fixture make every
level of the precedence it pins disagree with the others?*

| Fixture | Precedence pinned | How the levels are made to disagree | Verdict |
|---|---|---|---|
| **C1b** | `order_list` tie → `name` → `id` | sections **and** their steps inserted in reverse; `Alpha` carries id `wsec_tie_b_…`, `Beta` carries `wsec_tie_a_…`, so name order and id order are **opposite** | ✅ strongest available — the assertion can only pass via `name` |
| **C6a** | liveness → `entered_at` → `created_at` → `client_id` | the `completed` step wins **all three** sorting levels (created 10:00 vs 09:59; entered 11:00 vs 10:00; client id `…_1` vs `…_2`). Only liveness selects the pending step | ✅ textbook — exactly the fixture r1 asked for |
| **C6b** | which step's record is read | the two `entered_at` values are an hour apart, so the assertion identifies the step, not just the field | ✅ |
| **C6c** | `entered_at` → `created_at` → `client_id` | three candidates, **three different winners**, and their states (`pending`/`working`/`paused`) are pairwise distinct so the asserted state names the winner | ✅ for levels 1–2; level 3 unpinned (N2) |
| **C9** | total worked vs non-excluded worked | the mixed section's non-excluded worked is **0** and its excluded worked is **1200** against a slice of 0 — the excluded seconds are the only thing that can cross it | ✅ |
| **C25a/C25b** | governing step vs first-in-query-order | the two steps carry **genuinely different** snapshots, and E3's `client_id ASC` order returns the **non**-governing one first | ✅ |
| **C27** | section unit vs step unit | — the fixture holds **one non-excluded step per section**, so the two units cannot disagree | ⚠️ structural only (N3) |
| C1a | (control for C1b) | insertion order equals expected order — deliberately | ✅ as designed; C1b is its complement |

---

## The three implementer decisions — ruled

**(a) C6b asserts the serialized ISO string, not the ORM `datetime` — ACCEPTED, and it is
the better choice.** C6b is a DB-kind criterion whose subject is E3's *wire*: §6.5's
client-side live tick consumes the ISO string, and `division_serializers.py:95` is
precisely where a dropped `.isoformat()` would land. Asserting the ORM object would have
tested `group_steps_by_section` and skipped the serializer. The assertion also carries the
timezone offset (`+00:00`), so a naive-datetime regression reddens it.

**(b) The teardown clears `latest_state_record_id` before deleting `StepStateRecord` —
ACCEPTED, and I verified it leaves no residue.** Measured by isolation, which is stronger
than the accumulation figure the prompt cites:

| | `task_steps` | `step_state_records` |
|---|---:|---:|
| before any of my runs | 3376 | 8983 |
| after a full targeted run of **every phase-2 test file** (166 tests) | **3376** | **8983** |
| after a full-suite run (2340 tests) | 3400 | 9023 |

**Zero** rows attributable to this pipeline; the `+24 / +40` comes entirely from tests
outside it. Also checked: `0` rows matching `ssr_pending_%`/`ssr_completed_%`, `0`
`tsp_extra_%`/`tsp_failed_%`/`tsp_live_%`/`tsp_typical_%`, `0` `wsec_tie_%`/`wsec_null_%`/
`wsec_excluded_%`/`wsec_left_%`/`wsec_second_%`, and **`0` task_steps holding a dangling
`latest_state_record_id`** — so the RESTRICT-ordered teardown is not merely tidy, it
leaves no broken FK either. This also converts master plan §7's careful hedge ("this
pipeline's own tests are not the proven source") into a proven statement. See N6 for the
one caveat.

**(c) E3's deterministic order is `TaskStep.client_id ASC` — ACCEPTED.** `client_id` is
unique, so the order is total, which is all HC-11 needs from this read. It changes no
allocation outcome: grouping is by dict key, the grouped-unit remainder ties on
`working_section_id` (B6), the intra-section split ties on `_sort_key`, and every pinned
literal (C5 4320/2160/4320, C10's 61, C12, C23's 21) is unchanged. It is deliberately not
M3.2's render order and not `sequence_order` — correct, because E3 emits no step rows, so
nothing on the wire reads this order. See N9.

---

## Item 6 — did the fixes introduce anything new?

The `live_steps or list(steps)` fallback and M3.5b's residual routing, probed directly:

| case | expected (M3.4 / M3.5b) | observed |
|---|---|---|
| all-terminal, two `completed` — one created 2 days ago but **closed most recently** | governing = the most recently *closed* one | ✅ its state and its `entered_at` are the row's |
| all-terminal **mixed** `completed` + `skipped` | `live_steps` empty → fallback to all steps → most recently closed | ✅ returns `skipped` |
| no open step, residual **negative** (slice 30, closed burned 150) | residual −120 absorbed by the governing step | ✅ `a: allowance −20 = own 100 + (−120)`; `b` keeps its own 50 |
| single terminal step (the 98.2% case) | whole slice to that step | ✅ 30 = 30 |

P-AGREE held exactly in all four; `share_state`/`left_seconds` agreed in all four
(`over_share` with `left −120`, no repeat of r1's S1). **The fallback is correct and
introduces nothing.** One structural observation worth a contract line — N8.

---

## Notes (carried forward, none blocking)

**N1 — one exact assertion was deleted; I probed it and it costs no coverage.**
`test_budget_allocations_query.py`: `assert second["typical_worker_seconds"] == 1800` was
present at `aa95d5e` and is absent at `f904100`. It is the only deletion-without-
replacement in the whole test diff, and it landed in a file the fix prompt scoped to "S5
only, **by strengthening**". Under a mechanical reading of §6's no-weaker-assertions rule
and this round's own approval bar, that alone would fail the round — so I measured it
rather than ruling on the letter.

Probe: at `get_working_section_typical_times.py`'s definition of `typical_seconds`, drift
**only** the second section's derived typical `1800 → 1801` (a `case()` guarded on the
value, leaving the first section's 3600 untouched). Result:

    FAILED …::test_budget_allocation_uses_shared_typicals_for_section_proportional_split
    E   assert 3199 == (2 * 1601)

C27's exact 2:1 ratio pins that typical **transitively, to the rounding grid** — a
one-unit drift reddens it. Every other defect class I could construct (swapping the two
typicals, nulling the second below the sample minimum, shifting both) is caught by the
surviving `== 3600` pin or by the same ratio. **Coverage did not decrease**, so I am not
holding the gate on it. Restore the line anyway: it is one line, it makes the fixture
readable without deriving 1800 from a median in your head, and the rule is cheaper to keep
than to re-adjudicate. Routed to: **phase-2 closeout, or the next touch of that file.**

**N2 — C6c's third precedence level is unpinned.** Inverting `candidates.sort(key=client_id)`
to `reverse=True` leaves **27 tests green**. C6c makes `entered_at` and `created_at`
disagree, but `client_id` is only reachable when both of those tie exactly, which no
fixture constructs. Same shape as C3's backstop for section ordering — a determinism
tie-breaker with no guard. Cost of closing it is one three-step unit fixture with identical
`entered_at` and identical `created_at`. Routed to: **phase-3 or the next M3.4 touch;
record in plan 2's Review log so the gap is documented rather than assumed covered.**

**N3 — C27's unit restatement is structural, not demonstrable.** The assertion now
aggregates `allowances_by_section[…]` over all steps, which is unit-correct; but
`_seed_two_section_allocation` gives each section exactly **one** non-excluded step, so no
mutation can make the step unit and the section unit disagree on this fixture. C27's own
text permits this ("or over Σ step allowances per section"), and the proportionality it
guards *is* demonstrable (weight-flattening reddens it), so this is a documented limit,
not a defect. Closing it properly means a second step in one of the two sections — which
would also change the pinned values. Routed to: **plan 2's Review log as a known limit of
C27.**

**N4 — the handoff over-declares its perimeter (confirmed).** Declared but **not** in
`f904100`: `master_plan.md`, `plans/plan_2.md`, and the fix handoff itself. Nothing is
undeclared, so the direction is the safe one and nothing is hidden. The substance: the
first two are the **coordinator's** uncommitted edits (they carry r1's review-log entry
and §6's four new rules), so the implementer declared files it did not write; the third is
its own untracked output and is arguably right to list. The habit is the finding — a list
assembled by hand rather than from `git show --name-only` is the same habit that let r1's
green probe be summarised as red. Recommend the perimeter-by-path rule gain a sentence:
**generate the list from `git`, then add untracked artifacts explicitly.**

**N5 — the enumerated failure list mis-transcribes one path three times.** The handoff
writes `test_set_current_stored_amount_inventory.py`; the file is
`test_set_current_stored_amount_inventory_integration.py`. Nothing was concealed — the
diff is by test name and all 26 IDs match — but a hand-transcribed baseline is exactly
what the suite-number-verification rule exists to distrust. Same recommendation as N4:
paste from `pytest` output, never retype.

**N6 — the new teardown's blanket `UPDATE` is safe only by fixture convention.**
`test_production_time_query.py`'s C6a teardown runs
`update(TaskStep).where(TaskStep.workspace_id == workspace.client_id).values(
latest_state_record_id=None)` — unfiltered by step id. That is correct **only** because
`_seed` mints a fresh workspace per test. A future fixture that reuses a workspace would
silently null a live FK on rows it does not own. One comment line on the `update` stating
the precondition. Routed to: **next touch of that file.**

**N7 — three dead imports (pre-existing, not this round's).**
`test_production_time_query.py` imports `DivisionStep`, `_section_sort_key` and
`divide_production_budget` and uses none of them — each appears exactly once, on its own
import line. Importing a private domain symbol into a test that never calls it reads as
coverage that does not exist. Present since `98aa31b`; not introduced by fix r2. Routed
to: **phase-2 closeout tidy.**

**N8 — the two `_governing_step` call sites can legitimately select different steps.**
`group_steps_by_section:151` passes **all** the group's steps (so an all-terminal mixed
group's displayed governing step can be a `skipped` one); `_section_step_allowances:239`
passes **only** the completed steps (because an excluded step has no allowance row to
absorb a residual). Both are right, and the divergence is invisible on the wire — but it
is undocumented, and a future reader "fixing the inconsistency" would break one of them.
One sentence in M3.5b step 3: *the residual routes to the most recently closed
**allocatable** step, which is not always the section's displayed governing step.* Routed
to: **intention §12.5, coordinator's fold.**

**N9 — E3's `order_by` has no guard, and correctly cannot have one.** Removing
`.order_by(TaskStep.client_id.asc())` reddens nothing, because a test cannot deterministically
observe an unspecified order. That is not a coverage hole: the class was actually closed by
**taking the snapshot from the governing step** (C25b's guard), and the `order_by` is
belt-and-braces on top. Recorded so nobody later adds a theatrical "call twice, compare"
test and believes it guards this. Routed to: **plan 2's Review log.**

---

## Carry-forward dispositions

| Note | Destination | Owner |
|---|---|---|
| N1 restore the deleted typical pin | phase-2 closeout / next touch of `test_budget_allocations_query.py` | implementer |
| N2 C6c's `client_id` level | plan 2 Review log now; fixture at next M3.4 touch | coordinator → implementer |
| N3 C27's structural limit | plan 2 Review log | coordinator |
| N4 perimeter generated by hand | master plan §6 — extend the perimeter-by-path rule | coordinator |
| N5 failure list retyped | same rule as N4 | coordinator |
| N6 blanket `UPDATE` precondition | next touch of `test_production_time_query.py` | implementer |
| N7 three dead imports | phase-2 closeout tidy | implementer |
| N8 two governing-step call sites | intention §12.5 M3.5b, one sentence | coordinator |
| N9 `order_by` is unguarded by design | plan 2 Review log | coordinator |

None of these gates phase 3. Every one is a record or a one-line edit.

---

## Mutation-probe declaration

Seven mutations applied, each at the definition site, each reverted. **Verified by
`git status --short -- app/ .archgraph/` returning empty** — stronger than per-file
checksums, since it covers every file in the tree, not only the ones I remembered to hash.
`budget_division.py` also confirmed at `461c8b66…`, matching the fix handoff's declared
SHA, and `get_working_section_typical_times.py` restored from its pre-probe copy.

| # | File · definition site | Mutation | Observed |
|---|---|---|---|
| 1 | `budget_division.py:90` `_section_sort_key` | drop the `name` component | **RED** C1b only (1 failed / 26 passed) |
| 2 | `budget_division.py:155` `group_steps_by_section` | snapshot ← first non-null in group order | **RED** `'Upholstery' == 'Upholstery installation'` |
| 3 | `budget_division.py:153` `group_steps_by_section` | `entered_at` ← `group["steps"][0]` | **RED** `'…11:00:00+00:00' == '…10:00:00+00:00'` |
| 4 | `budget_division.py:191-198` `_governing_step` | swap the `entered_at`/`created_at` sorts | **RED** `'working' == 'pending'` |
| 5 | `budget_division.py:190` `_governing_step` | `client_id` sort → `reverse=True` | **GREEN, 27 passed** → N2 |
| 6 | `budget_division.py:321-322` `divide_production_budget` | `resolved_weights` ← `Fraction(1,1)` | **RED** `2400 == (2 * 2400)` |
| 7 | `get_working_section_typical_times.py:42-45` | drift the derived typical `1800 → 1801` only | **RED** `3199 == (2 * 1601)` → settles N1 |

Non-mutating derivations (no repo file touched): item 6's four-case fallback table and the
all-terminal residual routing were produced by calling `divide_production_budget` and
`group_steps_by_section` from a scratch interpreter session.

**Database side effects: none.** Read-only `psql` `SELECT`s plus test runs whose fixtures
own their teardown; residue and FK-orphan counts re-checked to zero afterwards (table
above). Configured DB at head, no migration written or run. **Architecture graph: not
touched** — no review item promoted, rejected or edited.

---

## Tracker line for the coordinator to fold

> | 2 | E3 — one task-scoped, section-keyed production-time endpoint (intention §12, mechanism M3) | **APPROVED** | 2026-08-17 | Opus 5 (reviewer r3) | Verdict APPROVED, 0 blocking / 0 should-fix / 9 carried-forward notes. All 7 r1 findings closed **and demonstrated by definition-site mutation**: C1b, C6a, C6b, C6c, C9, C25b, C27 each reddened at the expected assertion; the two fixtures that survived their own mutations in r1 now bite. Nothing loosened — 9 asserts added, 1 deleted, probed to cost no coverage (N1). Suite 2313/26/1, failure IDs byte-identical to the phase-1 closeout set (0 added, 0 removed), re-derived independently. Phase-2 tests proven to leave **zero** DB residue and zero orphan FKs by isolation. Three implementer decisions ruled acceptable. Checkpoints `98aa31b` → `f904100`. |

## For master plan §6 — one rule earned this round

- **Deleted-assertion rule.** In a round scoped to *strengthen only*, a **deleted**
  assertion is reviewed exactly like a loosened one, and the reviewer does not rule on the
  letter: they must **demonstrate** that the surviving criteria still pin the value —
  by drifting it and observing red — before letting the deletion stand. Earned here: one
  `== 1800` line vanished from a strengthen-only diff; the mechanical reading fails the
  round, the probe showed the ratio assertion pins the same value to the rounding grid, and
  only the probe could tell those two apart. A diff that greps clean for `==` → `!=` is not
  a loosening check; **removed lines are the other half of it.**

Also worth adding to the perimeter-by-path rule (N4/N5): **the perimeter list and the
failure list are generated from `git` and from `pytest` output, never retyped.** Both of
this round's filing defects are transcription, and both are in the one artifact whose
whole job is to be machine-comparable.

## Perimeter of this session

Write perimeter: **this file only.** The tracker row and `plans/plan_2.md`'s Review log
were deliberately not edited — the prompt scoped this session to one handoff file. The
tracker line above is ready to paste.
