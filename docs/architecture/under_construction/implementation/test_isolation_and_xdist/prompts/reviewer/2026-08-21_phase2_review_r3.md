---
plan: 2
role: reviewer
round: 3
date: 2026-08-21
project: test_isolation_and_xdist
mode: NO-WRITE — findings are delivered in your final message only
---

# Session prompt — plan 2 review r3, `test_isolation_and_xdist`

## 1. Role and mode

First and only independent review of phase 2: **order-independence and per-checkout test
isolation, proven serially.** You did not write this and must not assume it is correct — or
wrong. Your output is findings and a verdict; you never fix, and you never relitigate the plan
(plan complaints are "lessons", not blockers).

**⚠ NO-WRITE MODE — this round only.** Do **not** create, edit or delete any file: no handoff,
no Review-log entry, no tracker edit, no plan amendment. Deliver everything in your final
message. The coordinator writes the artifacts from it. This is deliberate; a session that
writes files in this round has not followed the prompt.

Mutation probes that edit source and revert are still permitted and still must be declared —
that is measurement, not reporting. Every probe file must be restored byte-identical and listed.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Suite runs from `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`
Reversed order: `BEYO_TEST_COLLECTION_ORDER=reverse PYTHONPATH=. pytest -m 'not e2e'`

**Read first, by absolute path, as this session's doctrine:**
`/Users/davidloorenz/agent-skills/pipeline-charter.md` (including **"Test-evidence scope and
reuse"**) and `/Users/davidloorenz/agent-skills/plan-reviewer.md`.

## 2. Why this phase deserves a careful reader

This is the instrument every other measurement passes through. Every mutation bite, every
approval baseline and every "the suite is green" in this organisation is mediated by the code
under review, and this phase **republishes the authoritative failure-ID set** that plan 3,
`live_clock_for_working_time_economics` phase 4 and `narrow_typical_work_times` D23 will build
on. It also holds the only thing standing between the test tooling and the owner's development
database. If the isolation is subtly wrong, nothing downstream is trustworthy and nothing will
announce it.

## 3. Gate check — stop and report if false

- Branch `feat/test-isolation-xdist`; HEAD's `app/` tree identical to checkpoint **`8429442`**
  (`git diff 8429442 HEAD -- app/` empty — later commits are documentation only).
- `plans/plan_2.md` §7 carries four entries: projection r0 and its consumption, implement r1
  and its consumption, fix r2 and its consumption.
- `pytest-xdist` is **not** installed and no `-n` appears anywhere. That is plan 3 (OD-5).

## 4. Read order

1. `plans/plan_2.md` in full — §4 tasks, §5 criteria C1–C8, §5A traps, §7 Review log.
2. `planning/intention.md` — **OD-6** (the repair contract), OD-3, OD-5, §2.3, §5.
3. `handoffs/implementer/2026-08-21_phase2_implement_r1_handoff.md` and
   `…_phase2_fix_r2_handoff.md`.
4. `handoffs/reviewer/2026-08-21_phase2_projection_r0_handoff.md` §4 — what was already found
   on paper, so you do not re-find it.
5. The code: `app/tests/database_isolation.py`, `app/tests/conftest.py`,
   `app/tests/fixtures/phase2_row_factories.py`,
   `app/tests/integration/infrastructure/test_database_isolation.py`, and the twelve repaired
   files listed in plan_2 §3.

## 5. Settled ground — do NOT re-spend the round here

Verified independently by the coordinator on your tree. **Contradicting one is a finding worth
reporting loudly; re-deriving one is waste.**

- **C2's closing pair:** default `21 / 2561 / 1` and reversed `21 / 2561 / 1`, failing-ID sets
  identical, `comm` empty in both directions, enumerated in the fix-r2 handoff. The 21
  reconciles as the published 22 minus the repaired
  `test_add_task_steps_integration::test_adding_a_batch_of_steps_reopens_ready_task`.
- **Perimeter:** implement r1 is eighteen files at `a3c54b2`, no production code; fix r2 is two
  files across `0f08079` and `8429442`. Verified against `git show --stat`.
- **Suite growth reconciles exactly:** selected 2563 → 2582, `+19`, matching the criterion
  module's 17 → 36 rows. Nothing else grew.
- **Residue:** the server holds `beyo_test_main_template` only among `beyo_test_*`; the two
  orphaned `beyo_test_shell_*` databases found after implement r1 are gone. Coordinator-measured
  across a criterion run: membership identical before and after, `36 passed`.
- **The legacy sweep worked:** `beyo_test_template` is gone, `beyo_test_main_template` is in
  its place.

## 6. Named probes — extracted from the coordinator's consumption

These are where the round's budget should go. They are questions, not conclusions.

- **P1 — the B1 diagnosis does not match the session configuration.** Fix r2 explains the
  reversed-order failure (`assert 0 == 2`, `test_sku_templates_commands.py:132`) as an
  identity-mapped row going stale after independent sessions committed. But
  `models/database.py:47` sets **`expire_on_commit=False`**, under which that staleness would be
  **deterministic in every order** — yet the test passes alone (coordinator-measured `4 passed`
  three times, *before* the repair existed) and passed in the default-order run. Either the
  object is not in the identity map on the passing path, leaving the order-dependent mechanism
  unidentified, or the cause was something else. The repair (`await db_session.refresh(row)`) is
  sound either way. **The question is scope:** if the real cause is order-dependent identity-map
  state, every read-after-commit assertion in the suite shares the exposure, and C2's green
  would be an accident rather than a property.
- **P2 — reconcile the L4 count.** Fix r2's handoff says *"this replacement pair was necessary
  after the first pair exposed B1"*, which reads as a first pair taken in that session; only the
  two closing runs carry evidence rows. Its budget was 2 plus 1 pre-authorised. Determine
  whether the round took 3 or 4, from the artifacts.
- **P3 — does S1's new membership assertion actually bite?** A module-scoped teardown assertion
  that `beyo_test_*` membership is unchanged: can it fail a run, or does it raise somewhere
  pytest reports as a warning? Charter rule 2 — introduce the defect and check.
- **P4 — is every guard sub-check covered?** C4 requires one mutation per sub-check. Fix r2's
  ledger reports honestly that the first URL-parse probe *"stayed green because later validation
  still rejected the inputs"*. Confirm that reading, and check the remaining sub-checks for the
  same shape — a check whose disabling reddens nothing has no row testing it.
- **P5 — the guard is the safety mechanism; probe it structurally.** The widened pattern, the
  slot resolver's fail-closed validation, the configured-tuple check and the endpoint-confinement
  check. Prefer reading what the code *can* do over what its tests observed. The
  `localhost`/`127.0.0.1` normalisation is load-bearing — a mistake there refuses every drop or
  admits the wrong one.
- **P6 — C7(b)'s residue check placement.** It was moved into `isolated_database`'s teardown on
  the measured fact that session-fixture teardown runs before `pytest_sessionfinish`. Does it
  observe the whole run, or only part of it?
- **P7 — Redis reaches the shipped default.** `isolated_redis_prefix` was made session-scoped
  autouse. Does a test that requests no Redis fixture observe a process-scoped prefix
  (charter rule 10)?
- **P8 — the twelve repaired files.** OD-6's composition is create-your-own `Workspace` /
  adopt-or-create `Role`. Did any repair weaken an assertion, adopt a row it should have created,
  or create a globally-unique row inside a test that commits?

## 7. Evidence budget

**This session's L4 budget is 0 runs.** Your tree matches the closing stamps — `app/` at HEAD is
identical to `8429442`, and the fix-r2 pair was taken there. Those stamps are consumed **by
citation**; re-running the suite to see it with your own eyes is over-evidence and a finding
against the round (charter: "Over-evidence is a defect, symmetrically").

If a probe genuinely requires the full suite — an absence claim, or coupling discovery that
narrower evidence cannot reach — write the charter's authorization line *"narrower evidence
insufficient because …"* **before** the run and report it. That path is open; it is simply not
the default.

Everything else runs at L1/L2, and that is where the round's value is: a different site, a
different condition, a different mutant shape than the records used.

## 8. What to deliver, in your final message

Both layers, per `plan-reviewer.md`. No files.

1. **Verdict:** APPROVED or CHANGES_REQUESTED.
2. **Layer 2 first — the human briefing.** Open with a 2–4 sentence plain-language state of the
   build. Then, for every blocking and should-fix finding, a 3–6 sentence narrative told from
   the owner's perspective in the product's own domain: cause → what you would actually observe
   → why it matters. Strictly faithful to the verified failure; the story illustrates the
   finding and never inflates it. Key each to its finding id.
3. **Layer 1 — the technical review.** Findings by id and severity (blocking / should-fix /
   note), each with what is wrong, the violated authority (file + section), and a suggested
   correction.
4. **What you verified correct**, specifically. A review that only lists problems is not
   auditable, and settled ground is what makes the next round cheap.
5. **Evidence records** — hypothesis, scope, exact command, tree identity, result, ID-delta
   where applicable. State your L4 count explicitly.
6. **Mutation-probe declaration** — every file touched and reverted byte-identical, every
   database or state side effect restored, so the next perimeter reconstruction can tell your
   probes from real deltas.
7. **Lessons for the plans**, and any **decision card** in the charter's format for something
   only the owner can settle. If nothing needs the owner, one line saying so.
