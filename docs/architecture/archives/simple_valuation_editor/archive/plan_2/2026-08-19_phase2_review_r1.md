---
plan: 2
role: reviewer
round: 1
date: 2026-08-19
project: simple_valuation_editor
---

# Session prompt — review r1, phase 2 (`simple_valuation_editor`)

## 1. Role and workspace

You review phase 2: the price-scenario read model, its serializer, its route and the
route-mirror artifacts. You did not write this code and must not assume it is correct — or
wrong. Your output is findings and a verdict; **you never fix**, and you never relitigate the
plan (plan complaints are lessons, not blockers).

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` — run every command from here.

Doctrine, by absolute path: `/Users/davidloorenz/agent-skills/pipeline-charter.md` and
`/Users/davidloorenz/agent-skills/plan-reviewer.md`.

**Mode: first review of the phase — the full checklist.** Master plan §7 withholds the light
MVP round for this project: the cheap first review is earned when most of a phase's surface
is not rule-6, and M3, M6 and `can_commit` are all silent-failure surface.

## 2. Gate check

- `plans/plan_2.md` §2 carries the perimeter roster **7 + 4 = 11**.
- `handoffs/implementer/2026-08-19_phase2_implement_r1c_handoff.md` reads `IMPLEMENTED`.
- Checkpoint `48705b3`, subject `CHECKPOINT (not approved): implement task price scenario
  read model`.
- The only untracked path is
  `docs/architecture/.../live_clock_for_working_time_economics/` — **a different project the
  owner is shaping; out of scope, do not read, do not touch.**

## 3. Read order

1. `plans/plan_2.md` — 19 criteria, §2's roster and four exceptions, §3's three delegations.
2. `handoffs/implementer/2026-08-19_phase2_implement_r1c_handoff.md`.
3. `master_plan.md` §4 (registry, incl. phase 1's twelve public names and the two sanctioned
   duplications), §5 standing rules, §6 environment, §7 gates, §8 closeout obligations.
4. `planning/intention.md` — §2.3–§2.8, §5.1–§5.3A, §6, §6B, §8, §8A, §9.2, **§9.2A**, §9.3,
   §9A.1 **with its `†` qualification**, §9A.2 **with its retraction**, §9A.3, §4.4, **§4.4B**,
   §10, §11, §12, §12A. **§9.1 is superseded — do not review against it.**
5. The code: `get_task_price_scenario.py`, `serializers.py`, `item_economics.py`, the three
   mirror artifacts, and the new integration suite.

## 4. Settled ground — verified by the coordinator at consumption, do not re-spend

- **Perimeter is exact.** `git diff --name-only 302c3ab 48705b3 -- app/` returns **11 files**,
  matching the roster row for row.
- **The three comment-only exceptions are genuinely comment-only.** Read the diffs: one line
  in `price_scenario.py`, one in `calculator.py`, two in `cases/serializers.py`, zero
  executable changes. Both reciprocal pairs land and each names the other's path.
- **The `test_price_scenario.py` exception is exactly one assertion** — the inert
  `slider_domain(1_211_335, 0, 29) == slider_domain(1_211_335, 1, 29)` replaced by the exact
  `SliderDomain(110, 3_080, 12_100)` literal at `B = 8_919`. Nothing else in that file moved.
- **D-5 took the import branch** — `_median`, `_step_state_is_excluded` and
  `group_steps_by_section` imported from `budget_division`, which preserves the `.value`
  comparison semantics the plan flagged as the silent trap. No reimplementation.
- **Suite**: the coordinator re-measured independently; see §7.

## 5. Named probes — where this round's attention is bought

### P1 — the mutation ledger's observed-red set, again (start here)

The ledger records **one** reddened test for the single named mutation
(`max(1, quantity) → max(6, quantity)`), measured by running
`tests/unit/domain/item_economics/test_price_scenario.py` whole.

**But the same assertion now exists in two files.**
`test_c16_discriminating_literal_is_exact`
(`test_price_scenario_query.py:731`) asserts
`slider_domain(8_919, 0, 0) == SliderDomain(110, 3_080, 12_100)` — the identical literal on
the identical function. Under the mutation it must redden too.

So the observation is whole-*file* where the assertion has been duplicated across *files*.
This is phase 1's F2 in a new shape, and the rule master plan §5 earned there —
*a mutation ledger's observation is a property of the whole file, not of the test you were
watching* — needs testing against its own next case. **Probe: apply the mutation and measure
across both files (or the whole suite). Report the true set.**

### P2 — is the duplicated assertion wanted at all?

`plan_2.md` §2 exception 1 said **replace** the inert assertion in `test_price_scenario.py`,
which was done. The integration copy is *additional*, in an authorized file, so it is not a
perimeter breach — but it is two representations of one fact, which is the pattern this
project has repeatedly found drifting. Judge it: does the duplicate earn its place, or does
it dilute which test owns the guard? Note also that it carries `@pytest.mark.integration`
while opening no session and touching no database.

### P3 — can `test_c16_reciprocal_comment_pairs_are_present` fail?

It asserts four substrings across four module sources — the enforceable form of master plan
§4's sanction condition, and a good idea. **Probe it**: delete one comment, confirm the test
reddens, revert. Then judge the form: a substring assertion against source text is brittle in
one direction (a reworded comment breaks it) and blind in another (a comment in the wrong
function still passes). Is that the right trade here?

### P4 — the twelve-row status matrix and rule 2's companion

C1's twelve rows plus the two B6/B7 collapsibility rows are exactly where a shared-cause
fixture passes for the wrong reason. **Each row's fixture must make its own predicate the
ONLY reason its outcome holds.** Check specifically: do the five "present" rows use a
**fundable** model (a degenerate model or `T = 0` makes `domain` null while the status is
still `ok`), and do the B6/B7 rows use a model whose collapsibility is the stated one?

### P5 — `can_commit` from the live selection

§9A.2's status shorthand was **retracted** because a task committed while the configuration
was healthy keeps status `ok` after its cost model version expires. C2 claims a row for that
asymmetry. Verify the predicate reads the live selection, not the status, and that the row
genuinely constructs the drift rather than asserting it abstractly.

### P6 — D-5's private imports, and the one-copy rule

`_median` and `_step_state_is_excluded` are private and not in `budget_division.__all__`.
The choice was delegated and is defensible, but assess: does importing two private names from
a sibling domain module create a coupling that should be registered? And confirm the
participating-section set is built from the same rule the allocator uses — this is the
cross-screen agreement M3 exists to preserve.

### P7 — the discarded test run

The handoff discloses an initial run against `.env.testing` that was discarded as
schema-stale (`user_shift_state_records.transition_reason` absent). Confirm the reported
numbers come from the profile master plan §6 prescribes, and that nothing was written to the
wrong database.

## 6. Doctrine that bites hardest here

- **Re-derive, never trust the log.** Run the suite yourself.
- **Mutation-test the tests** — a test proves nothing until you know it can fail. This phase
  ships 52 new tests and **one** named mutation; the rest of the criteria are guarded by
  ordinary assertions, and the MVP calibration says that is correct for routes, serializers
  and role admission — but **not** for M3, M6 and `can_commit`. Probe those yourself.
- **Verify structurally, not behaviourally, where ownership matters** — "the test passes" is
  weaker than "the query cannot select outside the workspace".
- **Probe the seams the checklist doesn't name.** The live ones here: type coercion across
  the ORM boundary, `Decimal`/`Fraction`/`int` conversions, the `.get()` defensive lookup
  (C19), and teardown on a phase that finally writes to the database (rule 11½).
- **Report what you verified correct**, specifically — settled ground is what makes the
  re-review cheap.

## 7. Suite and environment

- From `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`.
- **Expected 2425 / 26 / 1** (+52 over the 2373 phase-1 baseline). The implementer measured
  it; the coordinator re-measured independently.
- **A single run is not evidence.** The failure count has been observed at 25, 26 and 27 on
  unchanged code with byte-identical ID sets. If yours disagrees with 26, repeat and **diff
  the ID sets**.
- The suite leaves ~24 `task_steps` and ~40 `step_state_records` per run from tests outside
  these pipelines. Row-count drift is never evidence of a code change.
- `ruff format` was **deliberately not applied** to seven pre-existing files: they are not
  globally formatted at baseline, and formatting them would rewrite executable lines outside
  the comment-only authorizations. Assess that call; the same judgment was ruled correct in
  a previous pipeline.

## 8. Closing protocol

Per the reviewer skill's dual-audience rule: **layer 1** technical findings (id, severity,
violated authority with file + section, suggested correction), **layer 2** the human briefing
in your final message — 2–4 sentences on the state of the build, then a 3–6 sentence story
per blocking/should-fix finding, told from the owner's side in kronor and minutes, strictly
faithful to the verified failure.

Deposit at `handoffs/reviewer/2026-08-19_phase2_review_r1_handoff.md`, charter frontmatter
(`plan`, `role`, `round`, `verdict`, `date`, `actor`), containing:

- verdict `APPROVED` or `CHANGES_REQUESTED`;
- `⚠ OWNER DECISIONS REQUIRED (n)` immediately after the opening summary — one line if none;
- findings by severity;
- **what you verified correct**, specifically;
- **lessons for the plans**, which the coordinator folds upstream;
- a **mutation-probe declaration**: every file your probes touched, `sha256` byte-identical
  after revert, and any database state restored;
- a **carry-forward dispositions table** if you approve with open notes — every note routed
  to a named destination, so nothing evaporates at closeout;
- your **full write perimeter** by path.

Do **not** update the master plan tracker and do **not** write plan 2's Review log — the
coordinator owns both.

**The architecture graph**: the session recorded `projection-item-economics-task-price-scenario`,
`endpoint-item-economics-task-price-scenario`, one `accepts` edge and four source links, and
correctly did **not** reuse phase 1's `source-file-item-economics-price-scenario`. Assess
type, naming against the sibling family, and evidence-span accuracy — **but you never promote,
reject or edit review items**; recommendations go to the human-authorization backlog.
