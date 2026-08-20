---
plan: 2
role: reviewer
round: 5
verdict: CHANGES_REQUESTED
date: 2026-08-20
actor: Opus 5 (1M context)
project: live_clock_for_working_time_economics
---

# Re-review r5 — plan 2, fix r4 (delta-scoped)

Fix r4 did what the prompt asked on four of its five findings, and I confirmed the fifth is
where the round's value was. The production perimeter is exactly the three lines it declared,
the suite reproduces at `26 / 2478 / 1` with the published failure set unchanged, and the two
findings the coordinator did not verify — S1's clauses and S2's walk — are in the file and
sound, except for one clause that is not there at all. Chasing that clause led to the round's
real finding: the allowance path the intention calls *"the most expensive mistake available in
this feature"* has **no guard anywhere in this suite**, and the clause that was supposed to
guard it would have watched the wrong value even if it had shipped. I measured it: every
section weight fed to the allocator at E-P can be replaced with live worked seconds and the
whole suite does not move — not one ID added, not one removed. The code is right — I re-read
both typicals sites and neither can see the live map — so this is once again a round whose
defect is in the proof rather than in the code. One
smaller thing rhymes with it: review r3 condemned a fixture for having no allowance to compare, fix
r4 replaced it under the row the finding named, and C6 row 1 is still standing on the old one,
asserting that `0` equals `0`.

The lead probe came back negative, as the prompt anticipated: **no mutation exists that the
byte-identity rows alone catch.** Reported plainly in §3, with what they do guard.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Nothing in this round needs an owner answer. (The three pending `ai_inferred` graph
items and r1's N6 remain the owner's under `plans/plan_4.md` C6 — untouched by this session,
as instructed.)

---

## 1. Perimeter (step 1)

`git status` clean at `2dee09e` before I ran anything. `git diff 771ff46..HEAD` is **8 files**:

| File | Change | Verdict |
|---|---|---|
| `get_task_production_time.py` | +1 (D7 comment) | declared ✓ |
| `get_task_budget_allocations.py` | +1 (D7 comment) | declared ✓ |
| `get_working_section_typical_times.py` | ±1 (N4 token) | declared ✓ |
| `test_phase2_live_surfaces.py` | +199 | declared ✓ |
| `handoffs/implementer/2026-08-20_phase2_fix_r4_handoff.md` | new | declared ✓ |
| `master_plan.md` **and** `plans/plan_2.md` (two files) | tracker + Review log | declared ✓ |
| `prompts/reviewer/2026-08-20_phase2_rereview_r5.md` | new | coordinator's own fold (`2dee09e`) ✓ |

`git show a9a143f -- app/beyo_manager/` is four `+`/`-` lines total — the two D7 comments and
N4's single token, confirmed by reading the diff, not the handoff. **No golden JSON moved by
anything in this range**; no cap-stream file appears in it at all, so master §7's escalation
clause is not engaged. Nothing outside fix r4's declared perimeter.

## 2. Baseline, measured on the tree I ran on

`PYTHONPATH=. pytest -m 'not e2e'` at **`2dee09e`**: **26 failed / 2478 passed / 1 deselected**
in 131.08 s. Failing-ID set `comm`-diffed against master §6's enumeration: **added ∅, removed
∅**. No count carried from any prior round. Every measurement in §3–§4 below was taken at this
tree, and no foreign commit landed during the sweep (`git log` unchanged at `2dee09e`
throughout).

## 3. F-R4 — the lead probe. Conclusion: **none found.**

I could not find a single-site production mutation that
`test_c4_frozen_open_record_payloads_are_byte_identical` alone catches. Two measurements and
one structural argument.

**The premise reproduces, independently.** Replacing `ctx.now` with
`datetime.now(timezone.utc)` at E-P's loader call
(`get_task_production_time.py:get_task_production_time`) gives **30 / 2474 / 1** — exactly four
added IDs, zero removed:

```
test_c2_c3_c7_live_payloads_reconcile_and_worker_face_stays_money_free
test_c2_positive_allowance_moves_share_state_under_live_basis
test_c6_allowances_are_byte_identical_after_settlement_recompute
test_c9_settlement_window_drop_is_visible_until_recompute
```

The byte-identity row is **not** among them. That is the coordinator's F-R4 measurement,
reproduced ID-for-ID by me.

**Candidate probed and dead.** Deleting E-P's `.order_by(TaskStep.client_id.asc())` at the
step-load site: **26 / 2478 / 1 — added ∅, removed ∅.** Not only do the byte-identity rows not
catch it; nothing in the suite does. Two serves of the same query inside one transaction return
the same order, so a byte comparison across serves cannot see an ordering contract disappear.

**Why no candidate can work, structurally.** The two serves run on one `db_session`, inside one
transaction, over rows the request does not write, with `ctx.now` frozen to the same value. Every
input to serve 2 is identical to serve 1 by construction. The payloads can therefore differ
through exactly two channels:

1. **Serve 1 mutates state serve 2 reads.** That is HC-1A, and
   `test_c4_each_surface_uses_one_loader_call_and_c5_does_not_persist_live_seconds` bites first
   and more precisely — it asserts `session.dirty` holds no `TaskStep`, then `expire_all()`, then
   re-reads the column. A byte comparison would report "the payloads differ" where that row
   reports which column moved.
2. **A clock read between the serves.** Its advance is microseconds, and `int(round(·))` per step
   collapses it to the same integer. **This is exactly T1**, which the mechanism-inventory gate
   found inert and rewrote as T1′ for this reason. The row is the defect T1′ replaced, one level
   up.

There is no third channel, which is why the search is not merely unsuccessful but closed.

**What the rows actually guard — record this, do not delete them.** Two things, both real:
(a) the loader-invocation total is **2 across two serves** for each of E-P, E-B manager, E-B
worker and single-task E-A — under M-C below (worker face silently settled) that total falls to 0
and this row reddens; (b) payload determinism under a frozen `ctx.now` at whole-second
granularity. Both are worth keeping. What the rows are **not** is an open-record determinism
guard: the name over-promises, and review r3's justification for adding them does not hold.

**Consequence for plan 3, and it is smaller than feared.** `plans/plan_3.md` C1 and C2 already
specify the discriminating shape — the `final` / `result` block compared against *the same task's
pre-open payload*, which is a comparison between two genuinely different states. Plan 3 does not
need rewriting; it needs one line saying its determinism guard is that pre-open comparison and
**not** phase 2's two-serve rows.

## 4. Remaining depth targets

### 4.1 S1's three clauses (C6 row 1)

**Clause (i) — no excluded step holds an open working record.** Present
(`assert open_excluded == []`). **It cannot fail under any production mutation.** The fixture's
two excluded steps (`tsp_failed_*` at 1200 s from `_seed`, `tsp_phase2_skipped_*` at 240 s) are
constructed with **no state record at all**, and no code on the request path creates one. The
assertion pins the fixture, not the mechanism. It is the honest form §9A T12 prescribed, so I do
not file it as a defect — but the intention says something stronger about it, which is **S3**.

**Clause (ii) — `charged_seconds` computed from settled values, asserted on the division
input.** Present and correctly built: the division input is captured by monkeypatching
`divide_production_budget` at both consumer modules, `settled_charged_seconds` is computed from
the ORM rows and pinned absolutely at `1440`, and `assert len(division_inputs) == 4` guards the
`all(...)` clauses against vacuity — the one thing most likely to have been skipped. It cannot
fail on the live→`charged_seconds` class (that needs an excluded step with an open record, which
T12 already records as unconstructible), but it **does** discriminate a real class: dropping
excluded steps from the substituted rows takes the sum to 0. Sound.

**Clause (iii) — `typical` blocks byte-identical. Absent.** There is no occurrence of `typical`
anywhere between the C6 test's first and last line. And had it been written where the criterion
puts it, it would have compared **`None` to `None`**: I served the fixture and dumped the payload,
and its one section reports `{'typical_worker_seconds': None, 'sample_count': 0, …}` on both sides
of the settlement close — `_make_live_fixture` seeds no completed section-totals, so no typical
qualifies. See **B1** and **S1**.

**The headline — allowance byte-identity across the settlement close.** Present, and it cannot
fail on the property it names, for two independent measured reasons. See **S2**.

### 4.2 S2's recursive walk (C7)

**Closed, and correctly.** `walk_keys` recurses through dicts and lists and yields keys at every
level **including the top**, so the `include_monetary=False` branch's own
`payload["allowed_worker_minutes"]` (`serializers.py:serialize_task_budget_status`, the `else`
branch) is now inside the walk — that key was the specific hole S2(b) named. Non-vacuity is
carried by the five `worker_payload[field] == manager_payload[field]` assertions above it, which
would `KeyError` on an empty payload, and by `status.result` being non-`None` on this fixture so
`_serialize_result`'s sub-dict is walked too.

**The greater-than clause bites — measured.** Mutation: the worker face delegates with settled
step totals instead of the live fold, at
`get_task_budget_status_worker.py:get_task_budget_status_worker` (intention §4.1A D row 2, "worker
face silently stays settled"). **29 / 2475 / 1 — three added IDs, zero removed:** the C7
reconciliation row itself, the C4 loader row, and the byte-identity row. This reproduces fix r2's
ledger row 7 ID-for-ID on the delivered tree, and it confirms S2(a) is closed: the row is now
non-vacuous because the live term is asserted to exceed the settled sum.

### 4.3 The C2 positive-allowance fixture

**Its own predicate is the only reason the outcome holds.** `_make_share_state_fixture` zeroes
`total_working_seconds` on every non-deleted step and converts the excluded ones to `PENDING`, so
`charged_seconds` is 0 and the section's whole `distributable_seconds` is the allowance:
`3.10 min × 60 = 186`. The live basis works 1500 s (25 min, one open record); the settled basis
works **0**. `over_share` therefore has exactly one sufficient cause — `1500 > 186` — and under
the settled substitution the category moves to `on_track`, which the coordinator measured. This is
the correction of review r3's B1 done properly: the previous fixture's allowance was degenerate at
0, and this one is not.

### 4.4 Intention §4.1A C.1

Its structural claim is true — `_step_transition_core.py:_apply_step_transition` sets
`closing_record.exited_at = now` unconditionally, so a step cannot enter an excluded state with its
working record still open (re-read at source this session). Its **last sentence** is not: "Plan 2
C6 row 1 carries the assertion that pins it." See **S3**.

---

## 5. Findings

### BLOCKING

**B1 — §4.3A path 3 has no guard anywhere in the suite, and C6 clause (iii) is aimed at the wrong
value.** Authority: `planning/intention.md` §4.3A path 3 and §9A T12; `plans/plan_2.md` §5 C6 and
§6 ("Path 3 warning verbatim").

*Measured.* Replacing E-P's entire `typicals_by_section` with values derived from the live map —
the "make it consistent" change §4.3A names as **"the most expensive mistake available in this
feature"** — leaves the whole suite green: **26 / 2478 / 1, added ∅, removed ∅.** The section
weights handed to `divide_production_budget` are unobserved by every test in this repository. The
narrower, phase-specific form of the same mutation (add each section's live-minus-settled delta
into `typicals_by_section`, i.e. a typical that ticks while someone works) is likewise **∅**, which
follows from the first result.

*Why clause (iii) would not have closed it even if written — two reasons.* First, it compares the
payload's `typical` block, which is built from `typical_details`
(`get_task_production_time.py:get_task_production_time`) — a **different dict** from
`typicals_by_section`, which is what actually reaches the allocator. A live figure entering the
weights moves every `allowance_seconds` on the payload and leaves the `typical` block untouched.
Second, on the fixture the criterion puts it on, that block is
`{'typical_worker_seconds': None, 'sample_count': 0, …}` on both sides — measured — so the clause
would have asserted `None == None`. Review r3 was right that clause (iii) has no substitute; it is
also true that clause (iii) is not itself the guard, and its prescribed placement is inert for the
reasons in **S2**.

*The code is correct.* I re-read both sites: E-P builds `typicals_by_section` only from
`typical_result`, and `get_task_budget_allocations.py:_load_typicals` only from
`typical_times_statement`, whose `SUM(TaskStep.total_working_seconds)` is a SQL aggregate over
COMPLETED steps that never sees `live_seconds`. There is no live defect today. What is missing is
the row that would keep it that way through phase 3 and through
`narrow_typical_work_times`, whose D23 rewrites `typical_times_statement` for all four of its
consumers on this pipeline's approval baseline.

*Required correction — a row that pins the weights.* Fixture: one task, **two** working sections,
each with at least one step and its own qualifying typical (five completed section-totals per
section; `test_budget_allocations_query.py:_seed_typicals` is the house shape), one step holding an
open `working` record. Assert the **exact** `allowance_seconds` per section on the E-P payload, and
the same on E-A's `steps[]` in the same test (master §5, sweep the class — `_load_typicals` is the
same construct at the other surface). **Named mutation, call site,
`get_task_production_time.py:get_task_production_time`, between the typicals loop and the
`divide_production_budget` call:** add each section's live-minus-settled delta into
`typicals_by_section`. **Both sides must be computed before the row ships** — the section holding
the open record gains weight and the other loses it, and if the chosen typicals make the two
shares tie, the fixture is inert and must be re-chosen. Note for the implementer: nothing existing
will catch a mistake in this row's own construction, because the ∅ above says the weights are
unguarded today.

### SHOULD-FIX

**S1 — clause (iii) is recorded as shipped in two artifacts and is not in the file.** Authority:
`handoffs/implementer/2026-08-20_phase2_fix_r4_handoff.md` §"Finding closure" ("It also compares
the `typical` blocks before and after settlement/recompute"); `plans/plan_2.md` §7, *Implementer
fix r4* ("compares `typical` blocks across settlement/recompute"). Neither is true: `grep`
returns no occurrence of `typical` between the C6 test's first and last line. The coordinator's own
fold was explicit that S1 was **not** verified, so nothing downstream has yet leaned on the claim —
which is exactly why it should be corrected now, in place at the next fold, the way review r3's S5
corrected ledger row 4's ID set. Correction: strike the clause from both records and replace it
with what B1 establishes.

**S2 — C6 row 1's headline cannot fail on the property it names, for two independent reasons,
both measured.** Authority: `plans/plan_2.md` §5 C6 row 1; intention §9A T12; master §5 (the
identity-element rule and the *controlling term* rule).

The row serves the payload with an open record, closes it through `_apply_step_transition`, runs
`_recompute_step_time_totals`, serves again, and asserts allowance byte-identity.

*(a) The two sides are computed from an identical input vector.* I captured what
`divide_production_budget` is actually handed on each serve:

```
BEFORE: {tsp_failed_…: 1200, tsp_live_…: 600, tsp_phase2_skipped_…: 240}
AFTER : {tsp_failed_…: 1200, tsp_live_…: 600, tsp_phase2_skipped_…: 240}   identical: True
```

After the recompute the settled figure **equals** the live one — the phase's own C9 row asserts the
same thing from the payload side (`2040` → `1440` → `2040`). Two payloads built from identical
inputs are identical for every function of those inputs, including a defective one: a mechanism
that made `allowance_seconds` depend on the live basis would move **both** sides equally and the
comparison would still hold.

*(b) The compared value is the identity element.* The same probe shows the fixture's one section
reporting `(allowance_seconds, left_seconds, worked_seconds) = (0, -2040, 2040)` on **both** sides.
The allowance is `0` — the excluded steps charge 1440 s against a 1200 s budget, so
`distributable_seconds` is `max(0, -240) = 0`. This is the *exact* degeneracy review r3's B1
condemned in the C2 row, on the *same* `_make_live_fixture`. Fix r4 gave C2 a new fixture with a
positive allowance and left C6 on the old one: the class was swept for one instance and not the
other (master §5, "sweep the class, not the instance").

The row's entire discriminating power therefore comes from `left_seconds`, which the test compares
alongside the allowance and which is worked-derived — that is why the settled-substitution mutation
reddens it (r4 ledger, reproduced here by M-B) while nothing about an allowance ever moved. This is
the **tenth** instance of the row-that-cannot-fail class on this project, and reason (a) is a new
shape: the two sides of the comparison are made equal *by the operation the row itself performs*.
Correction: the discriminating comparison is live-basis versus **settled-basis** (the B1(a)
substitution) on a fixture with a **positive** allowance, not live-basis versus recomputed-settled
on one with none. Either re-anchor the row that way or record — next to it — that what it guards is
the ≤ 1 s settle/live parity bound, not allowance independence.

**S3 — intention §4.1A C.1's closing sentence overstates what the assertion pins.** Authority:
`planning/intention.md` §4.1A C.1 (round 4f), last line: *"Plan 2 C6 row 1 carries the assertion
that pins it."* The assertion queries for open records on steps that were constructed with no
state records at all; the hazard C.1 names — *"any future path that moves a step to
SKIPPED / CANCELLED / FAILED without closing its record"* — would not redden it, because such a
path is not exercised by the fixture. I also checked whether the close-then-open discipline is
pinned anywhere else: no test in `tests/` asserts `exited_at` is set when a step enters an excluded
state. The precondition is guarded by reading `_apply_step_transition`, and by nothing else.
Correction: amend C.1's last line to say the assertion pins the *fixture's* precondition, and that
the structural guarantee rests on the transition core's close-then-open discipline, which no test
in this pipeline exercises. §4.1A C is cited by phases 3 and 4, so the sentence should say what is
true before they read it.

### NOTES

**N1 — the byte-identity rows' `counted.calls == 2` duplicates
`test_c4_each_surface_uses_one_loader_call_…`'s own counter.** Not a defect — it is the assertion
carrying the rows' real weight (M-C reddens through it). Recorded so a later round does not file it
as redundancy and delete the part that works.

**N2 — the C6 test asserts the same `all(... division_inputs ...)` clause twice**, once with two
captured inputs and once with four. The second subsumes the first. Harmless; recorded so it is not
mistaken for two different checks.

**N3 — M-D's ∅ is wider than phase 2.** The section-weight input is unguarded for *any* wrong
value, not only a live one; that is pre-existing coverage debt in the budget-division family, which
phase 2 did not create. B1 asks only for the live-direction row, which is this phase's to owe. The
wider gap is recorded here, not filed against this phase.

**N4 — do-not-refile, carried from earlier rounds and re-confirmed as still true:** C11/C12's four
call-site mutations redden one shared row (r2 N1); `test_budget_allocations_query.py`'s
`first_count + 1` is the shared probe (r2 N2); C9 correctly names no production mutant (r2 N5); the
50-task ceiling fixture was removed after measuring (r2 N6).

---

## 6. Verified correct, specifically

So the next round does not re-spend these:

- **Perimeter and baseline** — §1 and §2, both measured by me, both reproducing.
- **S3 and S4 of review r3, closed at source** — `closed_at=datetime.now(UTC) - timedelta(days=1)`
  with the `typical_times_statement` call still argument-free (so the row keeps exercising the
  wall-clock branch and no longer expires on 2026-11-17); the D7 comment present at **both**
  substitution sites and naming the fail-loud consequence.
- **N4 closed, and D4's post-closeout medium satisfied at both shims** —
  `get_working_section_typical_times.py:typical_times_statement` and
  `_common.py:_load_preview_inputs` are both on the keyword-only `is not None` form, and both carry
  the comment beside the parameter naming the shim's purpose and its out-of-pipeline callers.
- **C7 (§4.2)** — recursive, reaches the top level, greater-than clause measured to bite.
- **C2 (§4.3)** — single sufficient cause, exact integers, category moves.
- **C6 clauses (i) and (ii) (§4.1)** — present, correctly built, non-vacuity guarded by
  `len(division_inputs) == 4`.
- **Path 3's production correctness** — both typicals sites read only the SQL statement; the
  loader's output cannot reach the weights.

## 7. Lessons, routed by artifact

- **`plans/plan_2.md` §5 C6** — clause (iii) names the wrong value: the payload's `typical` block
  is not the weights `typicals_by_section`. A criterion guarding a *derivation* must name the term
  the derivation reads, not a field that happens to carry the same number on the payload.
- **`plans/plan_2.md` §5 C6 row 1** — new member of the row-that-cannot-fail class: *a comparison
  whose two sides are equalized by a step the test itself performs*. The eight earlier instances
  were degenerate fixture values and the ninth was a degenerate controlling term; this one is a
  degenerate **procedure**. Worth a §5 rule: when a criterion compares state before and after an
  operation, check that the operation does not erase the difference the comparison exists to see.
- **`master_plan.md` §5, companion to the *controlling term* rule** — when a finding condemns a
  fixture as degenerate, sweep every row standing on that fixture, not the row the finding named.
  Review r3's B1 condemned `_make_live_fixture`'s zero allowance; fix r4 gave C2 a new fixture and
  left C6 row 1 asserting `0 == 0` on the old one. Same instruction as "sweep the class, not the
  instance", applied to fixtures rather than to comments — and this is its first instance here.
- **`master_plan.md` §5** — companion to the above: *a finding may be routed into a fix cycle and
  come back closed-in-the-record but absent-in-the-file*. Review r3's S1(iii) is the instance. The
  cheap defence is the one this project already uses for ledgers — the consuming fold greps for the
  clause rather than reading the sentence that claims it.
- **`planning/intention.md` §4.1A C.1** — see S3; a claim that a named test pins an invariant is a
  mechanism claim and inherits the mutation rule (master §5, earned at phase 1 r1 S1). It was
  written without probing whether the fixture could exercise the hazard.
- **`plans/plan_3.md`** — one line: the open-record determinism guard is C1/C2's pre-open
  comparison, not phase 2's two-serve byte-identity rows (§3 above).

## 8. Carry-forward dispositions

| Item | Destination |
|---|---|
| N3 — the wider section-weight coverage gap | recorded in `plans/plan_4.md` notes at closeout; not phase 2's to fix |
| The F-R4 record — what the byte-identity rows guard | `plans/plan_2.md` §5 C4, at the next fold |
| Plan 3 must not lean on the two-serve rows | `plans/plan_3.md` §2 or §6, before its projection |
| Closeout obligation 7 — publish the approval tree **and** its baseline (count + enumerated ID set) | `plans/plan_4.md`; `narrow_typical_work_times` D23 builds on it |
| Three pending `ai_inferred` graph items + r1's N6 | owner, via `plans/plan_4.md` C6 — **not adjudicated here** |

## 9. Mutation-probe declaration

All probes whole-suite at `2dee09e`, both-direction ID diff against my own clean run, reverted,
revert verified by SHA-256 against the pre-probe digests.

| id | Mutation | Site | Result |
|---|---|---|---|
| M-A | delete `.order_by(TaskStep.client_id.asc())` | `get_task_production_time.py:get_task_production_time`, step-load site | 26/2478/1 — **∅ / ∅** |
| M-B | `ctx.now` → `datetime.now(timezone.utc)` | same file, loader call site | 30/2474/1 — **4 added / ∅** |
| M-C | delegate with settled step totals | `get_task_budget_status_worker.py:get_task_budget_status_worker` | 29/2475/1 — **3 added / ∅** |
| M-D | `typicals_by_section` replaced by live-derived sums | `get_task_production_time.py`, before `divide_production_budget` | 26/2478/1 — **∅ / ∅** |
| M-E | `typicals_by_section` += per-section live delta | same site | 26/2478/1 — **∅ / ∅** |

Files touched by probes, applied and reverted, digests byte-identical to `HEAD` afterwards:

- `app/beyo_manager/services/queries/item_economics/get_task_production_time.py`
  — `488eb5ed5ca42d82fe699cca0008b188ce697539b2fe5e26b0fad4f10b600774`
- `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py`
  — `7264709ff94fe340534e7b3c254f94a7eb314fdd4ef94322a2c31a0b6c92f462`

One temporary probe test (`test_zzz_r5_probe.py`) was written, run focused and **deleted**; it was
kept outside the tests tree for the duration of the sweep above and never entered a whole-suite
run, so no ID set includes it. It captured the division-input worked vector and the served section
row on either side of C6 row 1's settlement close — the measurements behind **S2** and the `None`
typicals behind **B1**. No database or state side effect: every probe ran
under the rollback-scoped `tests/conftest.py:db_session`, and at the close of this session
`git status` shows exactly one entry — this handoff, untracked. No tracked file differs from
`2dee09e`.

## 10. Write perimeter

**Exactly one file:** this handoff,
`handoffs/reviewer/2026-08-20_phase2_rereview_r5_handoff.md`. No code, no plan edit, no tracker
edit, no Architecture Graph write.
