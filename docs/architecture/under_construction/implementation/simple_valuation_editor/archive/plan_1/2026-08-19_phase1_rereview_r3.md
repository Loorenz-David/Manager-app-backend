---
plan: 1
role: reviewer
round: 3
date: 2026-08-19
project: simple_valuation_editor
kind: re-review (delta-scoped)
---

# Session prompt — re-review r3, phase 1 (`simple_valuation_editor`)

## 1. Review history — what is settled, and by whom

**Review r1 (you, or your predecessor session) returned `CHANGES_REQUESTED`: 0 blocking,
2 should-fix, 7 notes.** It established the following as **settled ground. Do not
re-derive it.**

- **The arithmetic is correct.** A reference implementation written from the intention
  alone, without importing the module, reproduced all 22 published values exactly —
  `round_half_even`'s eight rows, both tie cases, `1_211_335`, `26_649_350_000`, `29`,
  `1_893_153 / 681_847 / 702_000`, both bands, both step-helper forms, the whole
  `two_significant_digits` ladder.
- **Mutation sensitivity is real**: 18 of r1's own 22 mutations bit, including half-up
  instead of half-even (6 red) and the D-2 unflushed-`None` trap (19 red).
- **Structural verification stands**: `collapse_terms`' three guards are the exact
  complement of `ck_cost_model_terms_value_by_type`; the imports are clean; the identity
  token is reused from the registered set, not minted.
- **N3, N4 closed. N2, N6 carried forward. N1, N5, N7 routed by the coordinator** (see §4).

**Your scope this round is the delta and nothing else** — plus the charter's
passing-glance clause: anything you see wrong in passing is reported, which is not
decorative and has caught real bugs in this project.

## 2. Step 1 — the verified perimeter

`git diff --name-only b72821c aea97ca -- app/` must be **exactly**:

```
app/beyo_manager/domain/item_economics/price_scenario.py
app/tests/unit/domain/item_economics/test_price_scenario.py
```

**Anything else is an automatic finding.** The coordinator has already run this and it
matched, but the check is yours to make.

**Declared non-application writes you will see in `git status`, all the coordinator's:**
`master_plan.md`, `planning/intention.md`, `plans/plan_1.md`, this prompt, r1's prompt and
handoff, the fix prompt — and **`.archgraph/architecture.yml` plus two records under
`.archgraph/reviews/`**. The graph was mutated twice this session under the owner's
answer to r1's owner card 1; §5 explains exactly what happened, and it is offered for your
assessment, not hidden.

## 3. The delta — what to attack

The whole production change is **two comment lines**. The whole test change is **one new
test**. Read the diff first; it is smaller than its handoff.

### F1 — the `max(1, quantity)` guard

The new test carries both required assertions:

```python
assert slider_domain(1_211_335, 0, 29) == SliderDomain(15_000, 420_000, 1_650_000)
assert slider_domain(1_211_335, 0, 29) == slider_domain(1_211_335, 1, 29)
```

**This is the only ledger row nobody has independently measured** — r1 measured the other
six. Probe it properly: apply `divisor = max(1, quantity)` → `divisor = quantity` at the
definition site, run the file whole, and confirm the observed-red set is exactly
`test_quantity_zero_falls_back_to_a_divisor_of_one`. The handoff claims one; the
coordinator confirmed both sides of the mutation (contract `SliderDomain(15000, 420000,
1650000)`; mutation `ValueError: b must be positive`) but did not enumerate the red set.

Second question, and the one worth judgment: **does the second assertion actually add
what it claims?** It was added because the first assertion's literals coincide with C16's
`Q = 6` band, so the row could not distinguish "the guard clamped to 1" from "the band
happened to be the same". Does `Q = 0 == Q = 1` close that, or does it merely restate the
mutation's crash in a second form? A mutation that makes `Q = 0` raise reddens both
assertions equally.

### F2 — the re-measured ledger

The fix handoff reports the six original rows re-measured whole-file, agreeing exactly with
the table the fix prompt supplied. **Note the circularity and judge accordingly**: the
prompt gave the implementer the numbers, so agreement is weak evidence on its own. What is
*not* circular is that **you measured these independently at r1** — so the cheap, sound
check is whether the handoff's sets match your own r1 measurements (C8 → 5, C17 → 3,
C10 → 2, the other three unchanged), not whether the implementer re-derived them honestly.

If any row disagrees with what r1 measured, that is a finding regardless of which is right.

## 4. Notes — routed, and NOT this round's work

Confirm the diff shows none of these was acted on (it should not):

- **N1** → folded into **intention §3.1B** (the short-circuit, its order-dependence, and the
  structural reason it is sound). `collapse_terms` unchanged.
- **N5** → `_shape_error`'s duplication **sanctioned** in master plan §4, with a third copy
  forbidden in phase 2. The cross-reference comments land with phase 2's edit, deliberately
  not here — adding them now would touch a line this round has no finding on. Assess that
  call if you disagree.
- **N7** → `digits` registered **internal to phase 1**; phase 2 calls
  `two_significant_digits`.
- **N2, N6** → carried forward (N2 accepted as unreachable; N6 to plan 2).
- **N3, N4** → closed. **N4 in particular: the unreachable `P = 0` pre-check stays** — §4.2A
  mandates it.

## 5. The architecture graph — for your assessment

Owner card 1 was answered: *"the recommended option is correct."* The coordinator enacted
your recommendation, then corrected its own record:

1. `reject` of `projection-item-economics-expected-sold-price-scenario` and its edge;
   re-recorded as `source-file-item-economics-price-scenario`, `type: source_file`, evidence
   span `14-209`. Audit: `.archgraph/reviews/2026-08-19T15-13-32-988Z--741606.yml`.
2. After fix r2, that record had drifted twice — the spans moved (`209 → 211`,
   `417 → 426`) and its test evidence summary said *"Fifty-two unit tests"* where there are
   now 53. An evidence summary is immutable through review and maintenance, so the count
   could only be corrected by reject-and-re-record. Done, with **symbol anchors and no counts
   in either summary** so the record stops rotting on the next test added. Audit:
   `.archgraph/reviews/2026-08-19T15-29-08-038Z--f161b6.yml`.

The node is `ai_inferred` and **pending** — the owner adjudicated the type and name, not the
description's verification, and promotion is a separate act. `projection-item-economics-task-price-scenario`
is left free for phase 2's endpoint.

**Assess whether the re-recorded node is right**, and say so either way. You never promote,
reject or edit review items — recommendations go to the human-authorization backlog.

## 6. Suite and environment

- From `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`.
- **Expected 2373 / 26 / 1** — the implementer measured it and the coordinator re-measured
  it independently. Baseline before this phase was 2320/26/1; +52 at r1, +1 here.
- **A single run is not evidence.** If your count disagrees with 26 failures, repeat and
  **diff the ID sets**. Only an ID added or removed across repeated runs is a finding.
- `ruff check` and `ruff format --check` on both phase files must stay clean.

## 7. Closing protocol

Deposit at `handoffs/reviewer/2026-08-19_phase1_rereview_r3_handoff.md`, charter frontmatter
(`plan`, `role`, `round: 3`, `verdict`, `date`, `actor`):

- verdict `APPROVED` or `CHANGES_REQUESTED`;
- `⚠ OWNER DECISIONS REQUIRED (n)` right after the opening summary — one line if none;
- findings by severity, and **explicitly whether F1 and F2 are closed**;
- a **carry-forward dispositions table** if you approve with open notes — N2 and N6 are
  already in flight and must appear there with their destinations, so they cannot evaporate
  at closeout;
- the **mutation-probe declaration**: every file touched, `sha256` byte-identical after
  revert, and any state restored. Current head hashes:
  `6e00d426…` (module), `819684c0…` (tests);
- your **full write perimeter** by path, from `git status --porcelain --untracked-files=all`
  and `git diff --name-only`;
- **layer 2**: the human briefing — state of the build in 2–4 plain sentences, and a story
  per blocking/should-fix finding if any survive. If the verdict is `APPROVED`, say plainly
  what the owner now has.

Do not update the master plan tracker or plan 1's Review log — the coordinator owns both.
