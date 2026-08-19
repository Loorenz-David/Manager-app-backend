---
plan: 1
role: reviewer (plan-projection)
round: 0
date: 2026-08-19
project: simple_valuation_editor
---

# Session prompt — projection r0, phase 1 (`simple_valuation_editor`)

## 1. Role and workspace

You run the **plan-projection** gate on phase 1. You do the implementer's first hour of
work on paper, **without permission to improvise**, and you are adversarial to the plan's
author: assume every task hides a decision the plan does not actually determine.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (where `.env` resolves; commands run from here)
Project folder:
`backend/docs/architecture/under_construction/implementation/simple_valuation_editor/`

**Read these two files first and follow them as this session's doctrine**, by absolute
path:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

If you are a Claude session, invoking the `plan-projection` skill loads (2); read (1)
regardless.

## 2. Gate check — stop and report if any of these is false

- `planning/intention.md` reads `status: RESOLVED and PLAN-READY (round 4 …)` and the
  mechanism-inventory gate reads **PASSED**.
- `planning/owner_decisions.md` reads **Ledger empty**.
- No handoff anywhere under `handoffs/` is in `OWNER_DECISIONS_PENDING`. You are never
  dispatched against an authority that is still moving.
- `plans/plan_1.md` reads `state: NOT_STARTED`.

## 3. Inputs discipline — this is the rule that makes the gate work

**Read only what the implementer will get.** The phase plan, its read-first list, and the
actual codebase. There is no planning-session context to have, and you must not go looking
for one: what you cannot derive from the artifacts, the implementer cannot either, and that
gap is the product of this session.

Read order:

1. `plans/plan_1.md` — your task list, and the artifact under audit.
2. `master_plan.md` — §4 naming registry, §5 standing rules, §6 environment, §7 gates.
3. `planning/intention.md` — the sections plan 1 cites: §3.1, §3.1A, §3.1B, §3.2, §3.2A,
   §3.5, §4.1, §4.2, §4.2A, §4.4, §4.4A, §5.3, §7A.1, §7A.2, §12, §12A. Read §9.1's
   superseded banner too, so you do not implement a rule that was replaced.
4. The code the arithmetic must agree with, read at `path:line`, never assumed:
   - `app/beyo_manager/domain/item_economics/calculator.py` — `calculate_term_amount`,
     `calculate_term_amounts`, `calculate_production_budget`,
     `calculate_allowed_worker_minutes`
   - `app/beyo_manager/domain/item_economics/budget_division.py` — `_budget_seconds`,
     `_median`, the constants
   - `app/beyo_manager/models/tables/item_economics/cost_model_term.py` and
     `production_cost_basis_version.py` — the storage precisions the contract's exactness
     arguments rest on
   - `app/tests/unit/domain/item_economics/test_budget_division.py` and
     `test_calculator.py` — the house test idiom you are projecting new tests into

## 4. Depth targets — allocate by silent-failure risk

Everything in this phase is charter rule-6 surface, so there is no "config plumbing gets a
glance" tier here. Rank your passes in this order and say in the handoff how you spent
them:

1. **`round_half_even` on negative operands** (§3.1A). The reference algorithm is stated;
   your job is whether the plan's criteria actually *decide* it, and whether the two
   languages' transcriptions agree at every enumerated case.
2. **The `(n+1)/2` bound against the real persisted path** (§3.2A, C7). This is the one
   criterion that compares new code against shipped code. Can you write it today, holding
   real `CostModelTerm` instances, with one exact expected outcome per model shape?
3. **The two searches** (§4.2A) — break-even and `infeasible_at_or_below_minor`. The
   monotonicity precondition, the doubling bound, the cap, and what each returns when it
   does not resolve.
4. **The band** (§7A.1) — exact rationals, the per-piece derivation order, the two-way
   `max(...)` on `min_minor`, and `two_significant_digits`.
5. Everything else.

## 5. What the ledger must capture

Per the skill: every point where the artifacts do not determine the next decision, each
classified as **plan gap** (proposed amendment), **intention gap** (routed upstream — never
patched downstream), or **free choice** (proposed as an explicit delegation, in writing, so
the implementer's freedom is granted on purpose rather than taken silently). **The goal is
zero *silent* freedom, not zero freedom.**

Specific things this phase can hide a decision inside, offered as places to look and not as
an exhaustive list:

- what a function returns when a model has no terms at all;
- whether the "no model" signal is an exception, a sentinel or an `Optional`, and who
  decides;
- the exact types crossing each boundary — `Fraction`, `Decimal`, `int` — and where the
  conversion happens;
- what `two_significant_digits` does at `b > a`;
- whether any criterion names an outcome you cannot turn into one exact assertion today.

Also run the skill's **reality checks**: every path in plan 1 §2 exists or is marked new;
every cited section resolves and says what the plan claims; every claim about existing code
is verified at the line, not assumed. And **criteria decidability**: for each of the 21
criteria, could you write the test right now, from the artifacts alone, with one exact
expected outcome per case? A criterion you cannot turn into a concrete assertion is a
finding, whatever its prose quality.

## 6. Constraints

- **You write no code and no test.** The skeleton you derive is **discarded** — it may
  survive only as a clearly-marked non-authoritative appendix. If the implementer receives
  your sketch as guidance you have become a second planner, which is exactly the coupling
  the fresh-session rule exists to prevent.
- **You never edit the plan, the intention, or code.** Findings route through the
  coordinator.
- **You never relitigate the intention's semantics** — the mechanism-inventory gate owned
  that and passed. A semantic hole is an upstream-routed finding, not a debate.
- Running the existing suite is permitted and not required; no database is needed for
  anything in this phase.

## 7. Closing protocol

Deposit at `handoffs/reviewer/2026-08-19_phase1_projection_r0_handoff.md` with the charter
row schema (`plan`, `role`, `round: 0`, `verdict`, `date`, `actor`), containing:

- **verdict** — `PROJECTED_CLEAN` (empty ledger; the implementer prompt may compile) or
  `AMENDMENTS_REQUIRED`;
- an **owner-readable opening**, 3–5 sentences, no citations and no jargon: what the
  projection concluded, whether anything needs the owner personally, what happens next.
  The owner decides from this paragraph alone whether to read further;
- immediately after it, `⚠ OWNER DECISIONS REQUIRED (n)` — every intention gap or free
  choice only the owner can settle, as decision cards in the charter format (story first,
  branches as consequences, one recommendation with its reason, on-silence behaviour, trace
  line). Findings cite their card; the card never restates the finding. If nothing needs
  the owner, one line saying so;
- the **decision ledger** as a table: decision point / classification / proposed routing;
- **reality-check and decidability findings**, each with its exact artifact and line;
- your **full write perimeter**, by path, generated from `git status --porcelain
  --untracked-files=all` — note that this project folder is entirely untracked, so
  `git diff` is empty by construction and cannot serve as the perimeter; say so and
  enumerate from the untracked listing, cross-checked against mtimes.

Do **not** write the phase plan's Review log line and do **not** touch the master plan
tracker — the coordinator owns both when it consumes this handoff.

**Exit gate:** every ledger row is routed — amendment applied, upstream change made, or
delegation recorded — before the implementer prompt compiles.
