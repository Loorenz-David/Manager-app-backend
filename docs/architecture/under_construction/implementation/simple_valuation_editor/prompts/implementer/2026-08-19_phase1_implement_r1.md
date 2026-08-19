---
plan: 1
role: implementer
round: 1
date: 2026-08-19
project: simple_valuation_editor
---

# Session prompt — implement r1, phase 1 (`simple_valuation_editor`)

## 1. Role and workspace

You implement phase 1: the pure price arithmetic for the "Expected sold price" screen. No
I/O, no route, no serializer — every number the feature publishes, and nothing that loads
or emits it.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` — **run every command from here**; `.env` resolves only
from this directory.
Project folder:
`backend/docs/architecture/under_construction/implementation/simple_valuation_editor/`

**Read these two files first and follow them as this session's doctrine**, by absolute
path:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

**`plans/plan_1.md` is your task list. Where this prompt differs from the plan file, the
plan file wins.**

## 2. Gate check — stop and report if any of these is false

- `plans/plan_1.md` reads `state: PROMPT_READY` and
  `gate: projection r0 COMPLETE — AMENDMENTS_REQUIRED, all 17 ledger rows routed`.
- `planning/intention.md` reads `status: RESOLVED and PLAN-READY (round 4 …)` and its
  changelog carries a **Round 5** entry (the projection fold). If round 5 is missing you
  have a stale intention and the corrected mutations are not in it.
- `planning/owner_decisions.md` reads **Ledger empty**.
- `master_plan.md` §3 shows phase 1 `PROMPT_READY`.
- `git status --porcelain -- app/` is empty. You start from a clean application tree at
  head `f1c0ebb`.

## 3. Read order

1. `plans/plan_1.md` — in full, including §3's four **delegations** and §6's Review log.
2. `master_plan.md` — §4 naming registry, §5 standing rules (note the two rules earned
   before any code was written), §6 environment, §7 gates.
3. `planning/intention.md` — §3.1, §3.1A, §3.1B, §3.2, §3.2A, §3.5, §4.1, §4.2, §4.2A,
   §4.4, §4.4A, §5.3, §7A.1, §7A.2, §12, §12A. **Read the correction banners**: §4.2A,
   §12A.3 and §12A.9 each carry one, and each says the opposite of what the section said
   before. §9.1 carries a superseded banner too — nothing in this phase depends on it, but
   do not implement from it.
4. The code your arithmetic must agree with, read at the line:
   `domain/item_economics/calculator.py`, `domain/item_economics/budget_division.py`,
   `models/tables/item_economics/cost_model_term.py`,
   `models/tables/item_economics/production_cost_basis_version.py`.
5. The house test idiom: `tests/unit/domain/item_economics/test_calculator.py` — the
   `SimpleNamespace` factory at `:39-51` and the real unpersisted ORM instance at `:370`.
   **Rule 3 forces the second idiom for C4 and C7.**

## 4. Perimeter — exactly two files

| Path | |
|---|---|
| `app/beyo_manager/domain/item_economics/price_scenario.py` | new |
| `app/tests/unit/domain/item_economics/test_price_scenario.py` | new |

**Nothing else.** Not `budget_division.py`, not `calculator.py`, not any router, service,
migration or existing test. **If a criterion appears to require a change outside these two
files, that is a STOP and a report, not a judgement call.** The re-review verifies this
perimeter with `git diff`; anything outside it is an automatic finding.

HC-2 was extended to authorize the new pure module — see `plan_1.md` §2. That extension is
the whole extension: it does not license a third file.

## 5. What the projection already settled — not optional, and not re-openable

A projection ran on this plan and found **three named mutations that could not fail**. They
have been corrected upstream in the intention and in the plan. **Do not restore any of
them**, and if a corrected mutation looks wrong to you, that is a report, not an edit.

- **C7's mutation is now two mutations**, not `n → len(terms)` (which only weakens a `<=`
  bound and is the identity on the shape it named).
- **C17 now asserts exact literals at `Q = 7`** — `15_400 / 415_800 / 1_647_800` — because
  `step_minor % 7 == 0` survives the mutation it was supposed to catch (`15_001 = 7 × 2_143`).
- **C10 is now an exact-literal assertion**, `26_649_350_000`, because the old form named a
  mutation of a circular definition that cannot be written in code.

Two facts the projection established that will cost you a debugging hour if you rediscover
them:

- **`infeasible_at_or_below_minor` for the mockup's configuration is `29`, not `0`.** The
  old "purely proportional ⇒ 0" shortcut in §4.2A was false. **There is no shortcut — always
  run the search.**
- **An unflushed `CostModelTerm(...)` carries `is_deleted = None`, not `False`.** SQLAlchemy
  applies column defaults at flush, and your tests have no session. `if not term.is_deleted`
  works; `if term.is_deleted is not True` works; **`if term.is_deleted is False` silently
  drops every term in every test you write**. Confirmed empirically at head `f1c0ebb`.

## 6. Delegations — decisions that are genuinely yours

`plan_1.md` §3 grants four, in writing, so your freedom is granted on purpose rather than
taken silently. **D-1 obliges you to report**: the module name, every public function name
and the parameter carrier you choose become phase 2's interface, and the coordinator
registers them in the master plan at closeout. Name them in the handoff.

Everything else in §3 is specified. In particular: the two outcomes of `collapse_terms`
(`None` for a missing purchase cost; `ValidationError` beginning
`ITEM_COST_TERM_SHAPE_INVALID:` for a shape error) are **different kinds of thing on
purpose** — phase 2 needs to tell a status from a 500. The identity token is **reused, never
minted**: a new one would require editing the registered-identity set under
`tests/unit/docs/`, which is outside your perimeter.

## 7. Standing rules that bite hardest here

Charter rules 1–11½ in full. Named because this phase is where they apply:

- **Rule 2 — enumerate, never sample**, with its companion: **each row's fixture must make
  its own predicate the ONLY reason its outcome holds.** A fixture satisfying two
  independent sufficient causes cannot fail when one breaks.
- **Rule 3 — invariants on the production object type.** C4 and C7 hold real
  `CostModelTerm` instances. The projection confirmed this works unpersisted, and that this
  is the first unit-test use of that class in the repo.
- **Rule 11 — a named mutation names its site**, definition or call site. And the new
  project rule: **compute both sides of every mutation before claiming it bites.** State
  the value under the contract and the value under the mutation in your ledger. A mutation
  whose two sides were never computed is a claim, not a guard.
- **Rule 4 — no dead scaffolding.** Every helper you add has a test caller in this phase.
- **No adjectives for mechanisms** (rule 5). "Nice", "near", "reasonable" already cost this
  project a gate round.

**Mutation discipline:** mutate at the named definition site → run → **observe red and
record the observed failure** → revert → confirm the file is byte-identical
(`sha256`). A ledger row without an observed-red is not evidence.

## 8. Environment and the suite

- Commands run from `backend/app/`. Tests: `PYTHONPATH=. pytest -m 'not e2e'`.
- **Baseline: 2320 passed / 26 failed / 1 deselected** (2347 collected), head `f1c0ebb`,
  measured by the coordinator on a clean tree. This phase **adds** tests, so the selected
  count rises; state before and after.
- **SUITE INSTABILITY — a single run is not evidence.** On unchanged code the failure count
  has been observed at **25, 26 and 27**, with byte-identical ID sets. If your run disagrees
  with 26, **repeat it and diff the ID sets**. Only an ID added or removed across repeated
  runs is a finding; a count alone, higher or lower, is noise. The drifting test is
  unidentified and inherited.
- No database is needed for anything in this phase. If you find yourself opening a session,
  stop — that is phase 2.

## 9. Scope fences

**No query service, no serializer, no route, no route-mirror artifact, no role test, no
`config_fingerprint`, no `can_commit`, no typical statement, no byline, no status table.**
Those are phase 2 and touching them is a scope breach however small the edit looks.

`is_fundable`, `anchors` and `domain` are **payload keys**, produced in phase 2. This phase
ships functions; criteria are asserted in the functions' vocabulary
(`break_even_price_minor(...) is None`, `slider_domain(...) is None`), never in the
payload's.

## 10. Closing protocol

1. Full suite, from `backend/app/`. Record before/after counts and, if the count disagrees
   with the baseline, the repeated run and the ID diff.
2. Deposit your handoff at
   `handoffs/implementer/2026-08-19_phase1_implement_r1_handoff.md` with charter frontmatter
   (`plan`, `role`, `round`, `date`, `state`, `actor`).
3. **Declare your full write perimeter by path**, generated from `git status --porcelain
   --untracked-files=all` and `git diff --name-only`, never retyped from memory. Note that
   the project documentation folder is entirely untracked, so `git diff` covers `app/` only;
   say which command produced which part of the list.
4. **Checkpoint commit** when you reach `IMPLEMENTED`, subject line prefixed
   `CHECKPOINT (not approved):`, under the owner's standing authorization. Do not stop to
   ask. Checkpoints are never squashed — they are the provenance the review runs on.
5. Do **not** update the master plan tracker or write the plan's Review log — the
   coordinator owns both.

## 11. The handoff must contain

- **Criterion → test map**, one row per criterion C1–C21, naming the test that satisfies it.
  A criterion with no test is stated as such, not omitted.
- **The mutation ledger**: for each named mutation — site (file, definition or call), the
  value under the contract, the value under the mutation, the observed failure, and the
  `sha256` confirming the revert. **Both sides computed**, per §7.
- **The four delegations**, each with what you chose and why — and for **D-1**, the module
  name, every public function name and the parameter carrier, called out for the registry.
- **Any STOP you hit**, with what you would have had to touch.
- Your **full write perimeter**, per §10.3.
- Suite counts before and after, and the ID diff if any run disagreed with the baseline.
