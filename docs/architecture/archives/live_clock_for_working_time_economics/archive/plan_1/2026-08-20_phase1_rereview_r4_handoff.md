---
plan: 1
role: reviewer
round: 4
verdict: CHANGES_REQUESTED
date: 2026-08-20
actor: Opus 5
---

# Phase 1 re-review (round 4) — `live_clock_for_working_time_economics`

**Verdict: CHANGES_REQUESTED — 1 blocking, 0 should-fix, 4 notes.**

r2 and r3 did what they were asked, correctly and completely. C11's two rows, C12's
three rows, N1, N3, N7 and S2 all hold, and I re-measured the third leg of C12's
orthogonality claim myself (M-float ⇒ exactly (a), (b), (c); nothing removed) — the
three C12 rows are orthogonal as r3 claimed and the coordinator confirmed. The
perimeter is exactly as declared: **zero production lines across both fix cycles**,
loader hash `6d11b922…fa82ca`.

The blocking finding is not in r2's or r3's work. It is in the **round-4c correction
of S1** — the sentence r1 wrote, the coordinator folded into intention §1A HC-3A, and
the implementer transcribed into the tree as C9's docstring. Measured this session:
**it is false.** `concurrency.py:_sweep` *can* raise on a naive `now`; whether it does
depends on the client host's UTC offset, and the C9 fixture clears that boundary by ten
minutes against a sixty-minute shift. On a host at UTC — the ordinary CI configuration —
deleting the boundary guard leaves `test_c9_naive_now_fails_closed_at_the_loader_boundary`
**green**, because the sweep then raises the identical `TypeError` with the identical
message that the guard raises. C9's named mutation is host-conditional; the safety test
cannot distinguish the guard it exists to prove from the failure it exists to pre-empt.

This is the same shape the project has now recorded six times: **the defect class
arriving inside the correction of its own class.** r1's S1 finding was "HC-3A names a
failure site it never probed." Its correction named a new failure-site fact — "the sweep
cannot fire" — and that one was never probed either. Two consumption re-verifications
missed it because all three of us re-ran the same fixture.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Nothing in this round needs the owner. (r1's N6 — the graph evidence summary
carrying a count — remains routed to `plans/plan_4.md` C6 for owner adjudication and is
not re-routed here.)

---

## 1. Step 1 — the verified perimeter

Confirmed from `git`, not from the handoffs:

| Check | Result |
|---|---|
| `git diff --name-only ae7d723..HEAD` | The phase test file + `plans/plan_1.md` + the two fix handoffs + `master_plan.md`, `plans/plan_4.md` and two prompt files (all coordinator commits, all under the project folder). **Union as specified; nothing outside.** |
| `git diff ae7d723..HEAD -- app/beyo_manager/` | **empty** ✓ |
| loader hash | `6d11b922fbec3031be49adf1313b6d1685bef95659caf81f2b6cb7e918fa82ca` ✓ |
| clean-tree full suite, this session | **26 failed / 2459 passed / 1 deselected** in 131 s; failing-ID set extracted and `diff`ed against master plan §6's enumerated 26 — **identical, zero delta** ✓ |

No perimeter finding.

---

## 2. Blocking

### B1-r4 — C9's fails-closed row cannot tell the guard from the sweep; its bite is an artifact of this host's UTC offset

- **Sites.**
  `app/tests/integration/services/queries/item_economics/test_live_worked_seconds.py:test_c9_naive_now_fails_closed_at_the_loader_boundary`
  (the docstring and the `pytest.raises(TypeError)` assertion);
  `app/beyo_manager/services/queries/item_economics/live_worked_seconds.py:load_live_worked_seconds`
  (the guard's message).
- **Authorities.** Intention §1A HC-3A Type bullet **as amended round 4c**; `plans/plan_1.md`
  §5 C9; charter rule 11 ("a safety test that survives the defect it exists to prevent is
  decoration"); master plan §5 ("a claim that names WHERE a failure surfaces is a mechanism
  claim and inherits the mutation rule").

**The claims under test.** The docstring: *"the configured driver normalizes a naive bind
before the sweep, so the sweep cannot raise (0 rows observed)."* HC-3A round 4c: *"the rows
never reach the sweep, so the named site cannot fire."*

**Measured** (probe file declared in §8, created and removed; no production file touched for
these four measurements):

| # | Measurement | Result |
|---|---|---|
| 1 | Naive `2026-01-10 09:10` bound as `timestamptz` through the configured driver | becomes the UTC instant **`2026-01-10 08:10`** — the value is reinterpreted in the **client host's local zone at that date** (host is `+02:00` today, `Europe/Stockholm` is `+01:00` on 10 January ⇒ −1 h). Postgres `TimeZone` is `UTC` and is *not* what applies: the same naive value cast `::timestamptz` through a text bind yields `09:10`. |
| 2 | Fetch boundary, `entered_at = 09:00Z`, naive `window_end` swept | `09:10` ⇒ **0 rows**; `10:59`, `11:00`, `11:01`, `12:00`, `23:00` ⇒ **1 row**. |
| 3 | Un-guarded loader shape (`compute_record_contributions(…, naive, naive)`), naive now = `09:10` | no raise, 0 rows — the C9 fixture's observation, reproduced. |
| 4 | **Same code, naive now = `23:00`** | **`TypeError: can't subtract offset-naive and offset-aware datetimes`, raised inside `concurrency.py:_sweep`.** |
| 5 | The guard's own message | `TypeError("can't subtract offset-naive and offset-aware datetimes")` — **byte-identical to the sweep's**. |

**What is wrong.**

1. *"the sweep cannot raise"* is false. Row 4 is the counter-measurement: same code, same
   fixture, a naive `now` one hour later, and the sweep raises. The parenthetical
   "(0 rows observed)" is not a property of the driver — it is a property of
   (this fixture's timestamps) × (this host's January offset), holding by a **ten-minute
   margin against a sixty-minute shift**. HC-3A carries the same false generalization and
   needs the same correction upstream.
2. **The named mutation is host-conditional.** On a host at UTC the shift is zero, so
   `entered_at 09:00 < 09:10` holds, the row is fetched, and `_sweep` raises the same
   `TypeError` — and `pytest.raises(TypeError)` **passes with the guard deleted**. The
   measurement chain behind C9 (r1's probe 4, the coordinator's consumption re-run, r2's
   ledger row) is three observations of one fixture on one host, not three independent
   confirmations. *(Rows 1–5 are measured; the UTC-host consequence is one step of
   arithmetic from row 1 and row 4, not an independent measurement — stated as derived.)*
3. **The root cause is the mimicry.** The guard was given the *exact* message CPython
   produces at the site it pre-empts. Type-only assertion + identical message + identical
   exception ⇒ the two failure sites are indistinguishable by construction. Nothing else in
   the tree checks a naive `now` (`grep -rn "tzinfo is None" beyo_manager/ tests/` → the
   loader's guard is the only one).

**Correction (test-only, no production change).** Pin the failure *site*, not the type:

```python
with pytest.raises(TypeError) as excinfo:
    await load_live_worked_seconds(
        db_session, workspace.client_id, [step], datetime(2026, 1, 10, 9, 10)
    )
assert excinfo.traceback[-1].path.basename == "live_worked_seconds.py"
```

With the guard, the deepest frame is the loader; without it, the deepest frame is
`concurrency.py:_sweep`. This discriminates on every host. Rewrite the docstring to record
what was measured — the naive bind is silently **shifted by the client host's local UTC
offset** (not "normalized"), so the un-guarded behaviour is *a wrong live term or a
`TypeError` from the sweep, depending on the host and the timestamps*; either way the
loader must fail closed at its own boundary. Then **re-measure the named mutation**, which
must now redden regardless of host.

**Alternative (one production line, arguably the better fix, coordinator's call):** give the
guard a message that names the boundary — e.g. `"load_live_worked_seconds requires an
aware UTC now"` — and assert `pytest.raises(TypeError, match="load_live_worked_seconds")`.
This removes the ambiguity at its source rather than working around it, at the cost of the
"zero production lines" streak. I recommend the test-only fix for this cycle and the message
change folded into phase 2, where `live_worked_seconds.py` is opened anyway.

**Routed upstream (coordinator, do not edit from here).** Intention §1A HC-3A Type bullet:
retire *"the rows never reach the sweep, so the named site cannot fire"*; replace with the
measured mechanism and the host-dependence. Plan C9's wording follows.

---

## 3. Should-fix

None.

---

## 4. Notes

- **N1-r4 — the C4 deleted-record docstring is true, but not the sentence C4 asks for.**
  Site: `test_live_worked_seconds.py:test_c4_deleted_record_is_excluded_defensively`.
  I swept the class as S1's correction required, and the claim holds: `grep` over
  `beyo_manager/` finds **no assignment of `StepStateRecord.is_deleted = True` anywhere**,
  the only `delete(StepStateRecord)` is `reset/phases/delete_step_state_records.py`, and
  every FK on `step_state_records` is `ondelete="RESTRICT"` — so no cascade deletes them
  either. What the docstring does *not* say is the half plan §5 C4 names verbatim
  ("docstring: **no shipped writer**, defense-in-depth"): the state the fixture builds
  (`is_deleted=True`) has **no writer at all**, and the file named issues a hard `DELETE`
  that never produces that state. As written, "this hard DELETE" has no antecedent in the
  test and can be read as attributing the fixture's state to that file.
  Suggested one-line addition: *"No shipped command sets `StepStateRecord.is_deleted = True`;
  the only hard `DELETE` is `reset/phases/delete_step_state_records.py` (whole workspace).
  This row is defense-in-depth (§3.1A D)."*

- **N2-r4 — the fourth property in the C12 seam: the per-step accumulation form, and no row
  can pin it.** Recorded explicitly rather than left unremarked, as the prompt asks.
  `live_worked_seconds.py:load_live_worked_seconds` accumulates
  `live_by_step[contribution.step_id] += int(round(contribution.seconds))`. Replacing `+=`
  with `=` is **observationally identical through any database fixture**:
  `uix_step_state_records_active` is `UNIQUE (workspace_id, step_id) WHERE exited_at IS NULL`
  and does not exclude soft-deleted rows (§3.1A E), so at most one open record exists per
  step; `averaged_time.py:compute_record_contributions` emits exactly one row per record;
  the loader's filter (`is_open ∧ state == "working" ∧ record_id ∈ probe set`) therefore
  admits **at most one contribution per `step_id`**, and the two forms cannot differ. The
  user loop cannot break this either — two users cannot hold open records on the same step,
  by the same index. **No row is owed**; it is untestable by construction, not overlooked.

- **N3-r4 — the r3 count anomaly: the vanished ID is a *third* flaky test, and its identity
  is unrecoverable.** §6's two named flakes
  (`test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`
  and `test_process_shopify_products_integration.py::…fans_out…`) are **not members of the
  enumerated 26**, so neither can vanish *from* it — a "26 failed with the new ID present"
  reading means one of the 26 baseline IDs passed. That is a third, intermittently-passing
  test and a new §6 environment fact. Its identity cannot be recovered: r3's ledger records
  the anomalous run's **count** and the presence of the new ID, but not its failing-ID set,
  so §5's mandated "ID set diffed" step was never performable. Four whole-suite runs this
  session (1 clean + 3 mutations) each produced the 26 with **zero removals**, so it did not
  recur. Recommend §6 absorb: *(a)* at least one of the 26 baseline IDs can pass
  intermittently, identity unknown; *(b)* the process rule in lesson 4 below.

- **N4-r4 — `test_c12_loader_output_values_are_ints` would pass vacuously on an empty
  result.** `assert all(isinstance(value, int) for value in result.values())` is `True` for
  `result == {}`. It is not vacuous today — one input step means one key, and M-float
  reddens the row as measured — but the assertion form does not guarantee that, and the
  loader has an early `if not settled: return {}` branch. One-word hardening:
  `assert result and all(...)`. Doctrine rule 2 ("would this loop pass vacuously on an empty
  intersection?"); no criterion violated.

---

## 5. Verified correct this round (so the next round can skip these)

- **Perimeter, hash, zero production lines** — §1 above.
- **C11 row (a)** — `settled=100`, `allows_batch_working=False`, one open record, 600 s share
  ⇒ 700. Its non-identity settled term is the only reason 700 holds (drop-settled ⇒ 600).
- **C11 row (b)** — `create_record=False` produces a step with **no state record at all**,
  not a record in another state: the helper's `if create_record:` branch skips the
  `StepStateRecord` construction, the `add`/`flush`, and the `latest_state_record_id`
  back-link, returning `record = None`
  (`test_live_worked_seconds.py:_add_step_record`, lines 116–134). Asserting exactly 250
  therefore also pins `live_by_step.get(step_id, 0)`'s default. Charter rule 4: the
  `create_record` parameter has exactly one caller, this row — no dead scaffolding.
- **C12 orthogonality, all three legs.** (a) and (b) confirmed by the coordinator's own
  M-mode run; the third leg measured by me this session: **M-float ⇒ `B ∪ {(a), (b), (c)}`,
  27→29 failed, zero removals** — exactly r3's ledger. Arithmetic re-derived independently
  against `concurrency.py:_sweep`: 61 s ⇒ 30.5 each (`round` 30, half-up 31; both loci agree
  at `settled = 0`); 63 s ⇒ 31.5 each with `settled = 1` ⇒ `1 + round(31.5) = 33`, while
  `round(31.5) == floor(31.5+0.5) == 32` makes it mode-neutral and
  `int(round(1 + 31.5)) = 32 ≠ 33` makes the sum-locus bite. Both segment values are exactly
  representable in binary float, so the halves are exact, not approximate.
- **N3's added C7 assertion (`result[second.client_id] == 1800`)** — holds for the right
  reason (the two open batch records are co-open for the whole of 10:00–11:00 on 2 Jan, so
  the divisor is 2 over 3600 s), and **survives the C7 anchor mutation as expected**:
  M-anchor (`min` → `max`, definition site) gives `B ∪ {test_c7_window_anchors_at_minimum_open_entry}`,
  zero removals, and the failure is `assert 91800 == 90900` at line 350 — the *first*
  assertion. Derivation confirmed: `window_start` filters the fetch but never clips an
  interval, so the `max` anchor only drops the overlapping closed record (90900 + 900 =
  91800) and leaves the second step's 1800 untouched. The added assertion is not reached
  under this mutation and is unaffected by it.
- **N1's docstring, both halves.** Second half was already measured (coordinator's
  consumption: sweep-timestamp-only ⇒ 11 IDs, `zero_cases` green; both-args ⇒ 12 IDs,
  `zero_cases` red). First half measured here for the first time: **M-attr** (delete
  `if user_id is not None`, definition site) ⇒ `B ∪ {test_c4_zero_cases_future_entry_and_missing_attribution_are_skipped}`,
  27 failed, zero removals. The mechanism: with the skip gone the both-NULL record is grouped
  under `user_id = None`, SQLAlchemy renders `coalesce(...) == None` as `IS NULL`, the record
  is fetched and earns 600 s. The docstring's assignment of halves to mutations is true.
- **N7's D1 comment** — "two overlapping 30-minute cross-task records yield 900 seconds each"
  is true of the fixture it sits beside (both records open `09:00 → 09:30`, same user, both
  `allows_batch_working=True` ⇒ divisor 2 ⇒ 900), and it is in the tree as a code comment, so
  it survives archival (master plan §5's delegation-medium rule).
- **S2's writer claim** — see N1-r4; the hard-DELETE claim itself is true and class-swept.
- **`_add_step_record`'s refactor is behaviour-preserving** for the 17 pre-existing callers:
  `create_record` defaults to `True` and the guarded block is byte-identical to the previous
  unconditional body.
- **Suite discipline** — every measurement this session is a whole-suite run
  (`PYTHONPATH=. pytest -m 'not e2e'`), never `-k`, with the failing-ID set extracted and
  `comm`-diffed against §6's enumerated 26 in both directions.

---

## 6. Carry-forward dispositions

| Item | Disposition |
|---|---|
| **B1-r4** | Fix cycle r5, this phase. Blocks approval. |
| **N1-r4** (C4 docstring) | Fix cycle r5, same file, one line. |
| **N4-r4** (vacuous `all`) | Fix cycle r5, same file, one word. |
| **N2-r4** (`+=` untestable) | **Closed here, no destination.** Recorded as a structural fact; no row is owed and none can be written. |
| **N3-r4** (third flake) | `master_plan.md` §6 (environment fact) + §5 (the process rule). Coordinator-owned; nothing for the implementer. |
| r1 **N2** | Already folded (intention round 4c) — not re-routed. |
| r1 **N6** | Already routed to `plans/plan_4.md` C6 for owner adjudication — not re-routed. |

---

## 7. Lessons for the plans (coordinator folds these upstream)

1. **The correction of a failure-site claim is itself a failure-site claim, and inherits the
   same rule.** r1's S1 retired one unprobed site claim and installed another; it then passed
   through a coordinator fold, an implementer transcription and two consumption
   re-verifications untouched, because every one of them re-ran the *same fixture in the same
   direction*. A site claim must be probed in **both** directions before it ships: one fixture
   where the mechanism does fire, one where it does not. Sixth instance of the
   class-inside-its-own-correction shape on this project.
2. **A guard whose exception type *and* message imitate the failure it pre-empts is
   untestable by `pytest.raises(Type)`.** When a safeguard duplicates a downstream failure's
   signature, the criterion must pin the failure **site** — traceback origin, or an
   observable absence of side effects (here: no SQL issued) — never the exception type alone.
   Generalises charter rule 11's "name where the mutation is applied" to "name where the
   failure must originate".
3. **An observation whose value depends on the host's timezone, locale or clock is an
   environment fact, not a mechanism fact.** Record the host offset beside it, or build the
   fixture so the observation is offset-independent. "0 rows observed" held here by a
   ten-minute margin against a sixty-minute shift, and inverts on a UTC host.
4. **A count is not a set.** When a run's count disagrees with baseline, capture its failing-ID
   set *before* repeating — §5 already mandates the diff, but a repeat performed against a
   count makes the diff impossible and the anomaly unattributable forever (N3-r4: the
   identity of a third flaky test is now unrecoverable).

---

## 8. Mutation-probe declaration and write perimeter

**Probe file** (created, run, deleted — `git status` clean at close):
`app/tests/integration/services/queries/item_economics/test_zzz_r4_probe_naive_bind.py`,
two successive versions, both removed. It touched **no production file**; it called
`averaged_time.py:compute_record_contributions` and `load_live_worked_seconds` directly on
the rollback-scoped `db_session` fixture (`tests/conftest.py:db_session`) — flush-only,
never committed, rolled back at teardown.

**Production mutations** — each applied to
`app/beyo_manager/services/queries/item_economics/live_worked_seconds.py`, measured with the
whole non-e2e suite, reverted with `git checkout --`, hash re-verified. `B` = master plan §6's
26 baseline IDs. Restored hash after **every** probe:
`6d11b922fbec3031be49adf1313b6d1685bef95659caf81f2b6cb7e918fa82ca`.

| Mutation / site | Both sides, named fixture | Whole-suite result |
|---|---|---|
| **M-float** — `+= int(round(contribution.seconds))` → `+= contribution.seconds`; definition site, the contribution loop | (a) `600` → `600.0`; (b) `{30, 30}` → `{30.5, 30.5}`; (c) `{33, 32}` → `{32.5, 31.5}` | **29 failed / 2456 passed / 1 deselected** = `B ∪ {test_c12_loader_output_values_are_ints, test_c12_half_even_rounding_is_applied_to_each_half_second_share, test_c12_rounding_locus_is_share_before_settled_addition}`; **0 removed** |
| **M-attr** — delete `if user_id is not None:`; definition site, the attribution grouping | missing-attribution step `0` → `600`; future-entry step `0` → `0` (unchanged) | **27 failed / 2458 passed / 1 deselected** = `B ∪ {test_c4_zero_cases_future_entry_and_missing_attribution_are_skipped}`; **0 removed** |
| **M-anchor** — `min(entered_at)` → `max(entered_at)`; definition site, the window computation | `first` `90900` → `91800`; `second` `1800` → `1800` (unchanged) | **27 failed / 2458 passed / 1 deselected** = `B ∪ {test_c7_window_anchors_at_minimum_open_entry}`; **0 removed**; failure is `assert 91800 == 90900` at line 350 |

**Suite runs this session:** 4 whole-suite runs — 1 clean (**26 / 2459 / 1**, ID set identical
to §6) and the 3 above. No baseline ID was removed in any of the four.

**Database / state side effects:** none persisted. Every fixture used the rollback-scoped
`db_session`; nothing was committed, no `.archgraph` call was made, no tracker or plan file
was touched.

**Write perimeter (from `git status` at close):** exactly this one file —
`docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/handoffs/reviewer/2026-08-20_phase1_rereview_r4_handoff.md`.
The tracker row (`REVIEWING → CHANGES_REQUESTED`) and the `plans/plan_1.md` §7 Review-log
entry are coordinator-owned on this project, per the prompt's §7 and r1's precedent.
