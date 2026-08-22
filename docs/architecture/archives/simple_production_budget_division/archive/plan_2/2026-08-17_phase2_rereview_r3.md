---
plan: 2
role: reviewer
round: 3 (re-review)
date: 2026-08-17
pipeline: simple_production_budget_division
---

# Re-review round 3 — plan 2 (fix r2 verification)

You are the reviewer (plan-reviewer doctrine). You fix nothing. This is a **narrow
round**: confirm the seven findings of review r1 are closed, that nothing was loosened to
close them, and that the new fixtures can actually fail. Write perimeter: exactly one
handoff file:

`…/simple_production_budget_division/handoffs/reviewer/2026-08-17_phase2_rereview_r3_handoff.md`

Do not re-open review r1's "Verified correct (settled ground)" section, and do not
re-derive anything in the list below.

## Already verified by the coordinator at consumption — do NOT redo

- **B1 closed.** All three previously-deviating fixtures now return `pending`
  (pending-created-first / identical `created_at` / `created_at` absent), and the control
  still returns `pending`. `_governing_step` partitions on liveness, then sorts
  `entered_at` DESC → `created_at` DESC → `client_id` ASC, matching M3.4.
- **B1's named mutation now bites on BOTH rows.** Deleting the liveness partition reddens
  `test_c4_c6a_c6b_c25a_c25b_grouped_row_preserves_state_and_snapshot` (the DB row that
  **survived** this same mutation in r1) *and* `test_c6_later_live_step_governs_section_state`.
  S3(a) is genuinely repaired.
- **S1/D16 closed.** The mixed section that read `on_track` beside `−100` now reports
  `worked=110, allowance=10, left=-100, share_state=over_share` — the three numbers agree.
  P-SUM3 still exact on that fixture.
- **Reversion is real.** After the probe, `budget_division.py` hashes to
  `461c8b6611a8a33d90aaa6c4312f0b0596004d81d72a55d92af2e62d2bf491d9` — **identical to the
  handoff's declared SHA**.
- **Suite re-run: 2313 passed / 26 failed / 1 deselected**, failure IDs byte-identical to
  the approved baseline (0 added, 0 removed).
- **Perimeter clean.** Checkpoint `f904100` contains 6 files, all declared; nothing
  undeclared. S6's fix works.

## What to verify (this is the whole round)

1. **The four findings the coordinator did not probe: S2, S4, S5, and the C6b/C6c halves
   of S3.** For each, apply its named mutation at the definition site, observe red,
   revert, `sha256`. Specifically:
   - **S2/C1b** — does the reversal fixture actually reverse *both* section and step
     insertion order, and do the section ids disagree with name order? The r1 fixture's
     ids happened to sort in name order, which is why the mutation was invisible.
   - **S4/C25b** — two steps of one group with genuinely divergent snapshots, and the row
     takes the **governing** step's. Also confirm E3's new `order_by` is present and that
     it changes no allocation outcome.
   - **S5/C27** — the P-PROP row now asserts at the **section** unit. Confirm it was
     **strengthened, not loosened**: its value must be unchanged and its invariant
     section-level. A rename with the same step-level assertion underneath is a fail.
   - **C6b** — `state_entered_at` exact value. This field had zero coverage anywhere
     before this round and §6.5's live tick depends on it.
   - **C6c** — the multi-open precedence fixture. r1's was vacuous (both steps pending, so
     it held under any rule).
2. **Apply the precedence-disagreement rule to every new or amended fixture** (master plan
   §6, earned this phase). For each of C1b, C6a, C6b, C6c, C9, C25b, C27: does the fixture
   make **every level** of the precedence it pins disagree with the others? A fixture where
   two independent causes both produce the expected value is not a criterion. This rule is
   the round's main instrument — five of r1's seven findings were that exact shape.
3. **Nothing loosened.** `git diff aa95d5e f904100 -- app/tests/` is the complete evidence
   base. Any assertion that became weaker, any exact literal that became an inequality or a
   membership test, is a failed round regardless of suite colour.
4. **The three DECISIONS the implementer had to make.** Rule on each:
   (a) C6b asserts the serialized ISO string rather than the ORM `datetime`;
   (b) test teardown clears `TaskStep.latest_state_record_id` before deleting state-record
   rows because the FK is RESTRICT — **check this leaves no residue**, given the measured
   ~24-steps-per-run accumulation recorded in master plan §7;
   (c) E3's deterministic order is `TaskStep.client_id ASC`.
5. **Two filing defects the coordinator found — confirm and rule on severity.**
   - The handoff **over-declares**: it lists `master_plan.md`, `plans/plan_2.md` and its own
     handoff as perimeter, but none are in checkpoint `f904100` (they are the
     coordinator's uncommitted edits). Direction is the safe one, but the list was clearly
     assembled by hand rather than from `git`.
   - Its enumerated failure list writes `test_set_current_stored_amount_inventory.py`
     three times; the real path is `test_set_current_stored_amount_inventory_integration.py`.
     Nothing was concealed — the coordinator's diff compares test names — but a
     hand-transcribed perimeter/failure list is the same habit that hid r1's green probe.
6. **Did the fixes introduce anything new?** In particular check that the liveness
   partition's `live_steps or list(steps)` fallback behaves correctly for a group whose
   steps are *all* terminal, and that M3.5b's residual still routes to the governing step
   in that case.

## Approval bar

`APPROVED` requires: all seven r1 findings closed; every new fixture non-vacuous under the
precedence-disagreement rule; no assertion loosened anywhere; the three implementer
decisions ruled acceptable or raised as findings.

If everything closes, say so plainly and do not manufacture findings to justify the round.
If something does not, `CHANGES_REQUIRED` with the named mutation that demonstrates it.

## Output

Verdict, then a numbered ledger (`S<n>` / `N<n>`) with file:line and, for each, the
mutation applied and the observed output. Include a closure table: r1 finding → closed?
→ which test bites on which mutation. Finish with the tracker line the coordinator should
fold, and anything that belongs in master plan §6 as a rule.
