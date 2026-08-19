---
plan: 3
role: reviewer
round: 1
date: 2026-08-19
project: simple_valuation_editor
kind: review — first review of this phase
---

# Session prompt — review r1, phase 3 (`simple_valuation_editor`)

## 1. What phase 3 is

Seven repairs carried out of phase 2's review as notes, batched instead of spending a fix
cycle on them. **None was a behaviour defect** — phase 2's review applied 34 mutations and
recorded that no mutation produced a wrong-but-green payload. Six were missing evidence or
tidy-ups; one (F9) is latency.

Read `plans/plan_3.md` for the seven tasks and the seven criteria, and
`handoffs/implementer/2026-08-19_phase3_implement_r1b_handoff.md` for what was done.

Perimeter: exactly two application files, both verified against the commit.

| Path | |
|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | +3 / −2 lines |
| `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py` | +183 / −13 |

Checkpoint `ef55f6d`. Phases 1, 2 and 4 are APPROVED and closed; **their files are not
yours.** `price_scenario.py`, `calculator.py`, the serializers, the router and both frontend
handoffs are all out of scope.

## 2. What the coordinator already verified — do not re-run these

These were measured independently at consumption, on this machine, at `ef55f6d`. They are
given so you spend your round on what is *not* yet settled, not so you accept them: if your
own reading disagrees with any of them, that disagreement is a finding.

- **Suite: 26 failed / 2430 passed / 1 deselected.** Failure IDs byte-identical to the
  inherited 26-ID set. The count reconciles exactly: `2425` (phase-2 baseline) `+3` new rows
  `−1` deleted duplicate `+3` net from a **concurrent owner change outside this pipeline**
  (`purchase_api.py` currency normalisation, which renamed one test into a 3-way parametrize
  and added one more). That owner change is uncommitted in the working tree and is **not
  yours to review or to attribute to phase 3.**
- **All four named mutations re-applied at their definition sites, whole-suite, and
  reverted byte-identical** (hashes `948a7a0f…` for `price_scenario.py`, `6900297d…` for
  `get_task_price_scenario.py`). Every observed-red set matched the ledger exactly:

  | Mutation | Observed-red set, measured across the suite |
  |---|---|
  | `max(1, quantity) → max(6, quantity)` | `test_quantity_zero_falls_back_to_a_divisor_of_one` — **exactly one**, C4 satisfied |
  | drop `superseded_at.is_(None)` | `test_phase3_c1_saved_uses_current_valuation_in_a_supersession_chain` — exactly one |
  | unfiltered `any(...)` in `_has_purchase_term` | `test_phase3_c2_…` — exactly one |
  | `round_half_even(...) → int(resolved)` | `test_phase3_c3_…` — exactly one, **and C4's own row stayed green**, which is the independent half of plan §3's F5 premise |

- **F6's removal is safe by reading**: `binding = "detached" if item is None`
  (`get_task_budget_status.py:111`) and `can_commit` already requires `item is not None`
  (`get_task_price_scenario.py:188`). The two predicates are the same fact.
- **F9's acceptance reason is true**: `TaskBudgetStatus` (`:34-48`) carries `item_id` and no
  object — not the `Task`, `Item`, selection, terms or valuation. Collapsing the duplicate
  reads genuinely requires changing that shared dataclass, which is a third file and a
  contract other screens consume. Declining was correct.
- **`_current_valuation` has no `ORDER BY`, and does not need one.**
  `uix_item_valuations_current` (`models/tables/item_economics/item_valuation.py:35`) is a
  partial unique index on `item_id` where `superseded_at IS NULL AND is_deleted = false`.
  At most one current row can exist. **Recorded so nobody re-raises it.**
- Ruff check and format both clean on the two files.

## 3. Probes

### P1 — the coordinator's own finding, and the handoff overstates it. **Confirm and extend.**

F8 was resolved by comment rather than by new rows. Both comments read:

```python
# Redundant defence-in-depth: _load_task_and_item owns the tenant boundary (C10).
```

The handoff's criterion table claims *"Both F8 comments point to
`test_c10_task_resolution_is_workspace_scoped_and_hides_deleted`."* **They do not.** They
point at `C10`, a criterion label that lives in `plans/plan_2.md` — a document that moves to
`archive/plan_2/` at closeout. `grep` puts these at **the only two criterion-ID references in
the entire `app/beyo_manager/` tree**; every other cross-reference comment this project has
shipped names a `file:symbol` (the phase-2 reciprocal pairs) or a test function.

So a future reader of production code meets a dangling reference into a pipeline artifact —
which is the exact defect class this project fixed in `force_task_ready` three commits ago.

**Your job:** confirm the reading, then extend it. Is naming the test function the right fix,
or does something else already establish the boundary more durably? Is there anywhere else in
the two files where a comment refers to something a reader outside this pipeline cannot
resolve? Give verbatim replacement text.

### P2 — the C1 fixture buys its determinism from the query planner. Is that a debt?

`test_phase3_c1_…` makes the *mutant* fail deterministically by issuing
`SET LOCAL enable_indexscan = off` / `enable_bitmapscan = off` and ordering two UPDATEs so a
sequential scan meets the older live tuple first. The handoff is candid that the first
fixture form **did not discriminate** — PostgreSQL returned the current row first even with
the predicate removed.

The contract side is unconditional and fine. The question is the **ledger** side.

- Does the discrimination survive a `VACUUM`, a HOT update landing on the same page, or a
  different PostgreSQL version — or is the recorded mutation result reproducible only on this
  heap layout? (It reproduced for the coordinator on a second, later run. That is two
  observations, not a guarantee.)
- Is a plan-dependent mutation ledger row *acceptable evidence* under master plan §5, or does
  it need a comment at the fixture saying what the GUCs are for and that the assertion does
  not depend on them? The inline comment currently explains the UPDATE order and not the GUCs.
- Do the two `SET LOCAL` statements leak? They are issued after a `commit()`, so they bind
  the next transaction, which the `finally` rolls back. **Check that reading** — a GUC that
  escaped into a pooled connection would be a suite-wide hazard.

### P3 — a name for the drifting test. Close it or refute it.

Master plan §6 records suite instability at **25/26/27 on unchanged code** with the drifting
test **unidentified and inherited**. This round produced a candidate:

- The implementer measured **27** twice, and both times the single extra ID was
  `tests/integration/services/commands/item_economics/test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]`,
  which **passed 1/1 in isolation between the two full runs**.
- The coordinator measured **26** on the same commit, with that ID absent.

That is the same test observed both red and green on identical code — the signature §6
describes. **Run the full suite and report whether that ID appears.** A third observation
either way is worth more than any argument. If it appears in your run too, say so plainly;
naming the drifting test after three pipelines of "unidentified" is a real result and belongs
in the master plan, not in a handoff.

Do **not** attempt to fix it. It is outside this phase's two-file perimeter and the
implementer was right to stop at evidence.

### P4 — where does an accepted debt live?

F9 was accepted: roughly eight redundant round trips on the **common** branch — a task with
no committed evaluation, which is the state this screen exists to resolve. The reason is
sound (P-2 above) and it is recorded in a handoff that moves to `archive/plan_3/` at closeout.

**Is that discoverable?** A latency acceptance that only exists in a consumed handoff is
invisible to the next person who profiles this endpoint and to the next pipeline that touches
it. Should it carry a comment at the call site, a line in the master plan, or a graph node?
Say which, and why that one. This is a should-fix at most — but an unrecorded-in-practice
acceptance is exactly what plan 3 §3 said was unacceptable.

### P5 — attack the three new rows the way phase 2's review attacked its own

34 mutations was the standard phase 2 was held to. Three new rows do not need 34, but they
need the same question asked of each: **is the row's own predicate the only reason its
outcome holds?** In particular —

- `test_phase3_c2_…` asserts `can_commit is True` **and**
  `model["constant_deduction_minor"] == 0`. The handoff's own ledger says the mutant leaves
  the second assertion green. Is the second assertion pulling any weight, or is it decoration
  that will read as coverage later?
- `test_phase3_c3_…` asserts `total_seconds == 35` and `sections_without_sample == 1`. Verify
  `35` from the intention's rule rather than from the code: usable `{11, 12}`, median `11.5`,
  half-even to `12`, substituted once. Confirm truncation gives `34` and half-**up** gives
  what — if half-up also gives `35`, this row does not separate half-even from half-up, and
  that should be said out loud rather than left implied.
- The C1 residue block sits **outside** the `try/finally`, so it does not run if the body
  fails. Correct by design — confirm it, and confirm the four named tables are the complete
  set this test writes.

## 4. What a finding looks like

Blocking = the endpoint or the evidence is wrong. Should-fix = true but a future reader is
misled or a claim in the handoff overstates the code. Notes = everything else.

**A handoff claim that does not match the code is a finding even when the code is correct.**
P1 is already one of those; the coordinator found it, and the presumption after four rounds of
this project is that where there is one there are two.

## 5. Closing protocol

Deposit at `handoffs/reviewer/2026-08-19_phase3_review_r1_handoff.md`, charter frontmatter.

State **explicitly whether each of C1–C7 is met**, and whether F6, F8 and F9's decisions are
each *recorded in a place that survives closeout* — that is the question plan 3 §3 actually
asked, and the handoff answered a narrower one.

Findings by severity, each with verbatim replacement text. Carry-forward table if you approve
with notes. Owner cards story-shaped and ≤120 words if any.

**Full write perimeter — you write no code and no handoff but your own.** Do not update the
master plan tracker or plan 3's Review log.

## 6. Environment

- Working directory `backend/app/`; `PYTHONPATH=. pytest -m 'not e2e'`.
- Expect **26 / 2430 / 1** on this tree. A different count is repeated and **ID-diffed**
  before any conclusion — master plan §6 is binding here, and P3 is the whole reason.
- **The working tree carries an uncommitted owner change** to
  `app/beyo_manager/services/queries/items/lookup/purchase_api.py`,
  `app/tests/unit/services/queries/items/test_lookup_item_by_article_number.py` and
  `.archgraph/architecture.yml`, made in parallel and unrelated to this pipeline. **Do not
  review it, do not revert it, do not stage it, and do not count it against phase 3.**
- The focused file is 49 tests and runs in under a second:
  `pytest tests/integration/services/queries/item_economics/test_price_scenario_query.py`.
- **Architecture graph**: the pending inferred projection's anchors drifted again with this
  phase's line changes (service symbol `149–273` → `152–274`; the C1 table/test span
  `387–419` → `416–448`), and `archgraph_status` still reports `stale: false`. These are
  coordinator-owned and pending; **report drift, repair nothing.** Reaching a pending
  `ai_inferred` item through maintenance is refused by the server and `repair_anchors`
  returns `INTERNAL_ERROR` — the review path is the only door, and it is not yours.
