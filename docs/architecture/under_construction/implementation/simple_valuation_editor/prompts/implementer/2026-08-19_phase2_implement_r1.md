---
plan: 2
role: implementer
round: 1
date: 2026-08-19
project: simple_valuation_editor
---

# Session prompt — implement r1, phase 2 (`simple_valuation_editor`)

## 1. Role and workspace

You implement phase 2: the read model, the serializer, the route and the route-mirror
artifacts. Phase 1 produced every number; this phase proves the wiring.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` — **run every command from here**; `.env` resolves only from
this directory.

Doctrine, by absolute path: `/Users/davidloorenz/agent-skills/pipeline-charter.md` and
`/Users/davidloorenz/agent-skills/implementation-executor.md`.

**`plans/plan_2.md` is your task list. Where this prompt differs from the plan file, the plan
file wins.**

## 2. Gate check — stop and report if any is false

- `master_plan.md` §3: phase 1 **APPROVED**, phase 2 **PROMPT_READY**.
- `plans/` holds `plan_2.md` only; `plan_1.md` closed to `archive/plan_1/`.
- `planning/owner_decisions.md` reads **Ledger empty**.
- `planning/intention.md` carries sections **§9.2A**, **§4.4B** and the `†` qualification in
  §9A.1. If any is missing you have a stale intention: the projection's corrections are not
  in it and three criteria will contradict it.
- `git status` clean at head; `PYTHONPATH=. pytest -m 'not e2e'` baseline **2373 / 26 / 1**.

## 3. Read order

1. `plans/plan_2.md` — in full, **including §2's two enumerated exceptions and §3's three
   delegations (D-5, D-6, D-7)**.
2. `master_plan.md` — §4 naming registry (**phase 1's twelve public names are your
   interface**), §5 standing rules, §6 environment, §7 gates, §8 closeout obligations.
3. `planning/intention.md` — §2.3–§2.8, §5.1–§5.3A, §6, §6B, §8, §8A, §9.2, **§9.2A**, §9.3,
   §9A.1 (**with its `†` qualification**), §9A.2 (**with its retraction**), §9A.3, §4.4,
   **§4.4B**, §10, §11, §12, §12A.
   **§9.1 is SUPERSEDED — do not implement from it.**
4. `archive/plan_1/plan_1.md` — what phase 1 proved and what it deliberately did not.
5. The code you compose: `price_scenario.py`, `budget_division.py`,
   `get_working_section_typical_times.py`, `get_task_budget_status.py`,
   `get_task_production_time.py` (your closest route precedent), `_common.py`,
   `commit_item_cost_evaluation.py`, `serializers.py`, `item_economics.py` + the three
   mirror artifacts.

## 4. Perimeter

The seven files in `plan_2.md` §2's table, **plus** its two enumerated exceptions
(`test_price_scenario.py`, one assertion; `calculator.py`, comment only). **Nothing else.**
The re-review verifies this with `git diff`; anything outside is an automatic finding.

**No change to `price_scenario.py`.** Phase 1 is settled — a defect found in it is a finding
routed back, not an edit made here.

## 5. What the projection already settled — not optional, not re-openable

A projection ran on this plan and found **seventeen** decisions the artifacts did not
determine. All are now routed. The five that will cost you an hour if you rediscover them:

- **§9.2A governs over §9A.1's status table on every non-`bound` binding.** They collide
  *every time*, not in an edge case. `item` is **`null`** for `detached`; `typical` stays
  **populated** on both paths.
- **`can_commit` is computed from the LIVE selection** (§9A.2's block form). The
  "equivalently A1/A2/B7/B10" shorthand is **retracted** — a task committed while the
  configuration was healthy keeps status `ok` after its cost model version expires, and the
  status form would publish `can_commit: true` for a guaranteed error.
- **§9A.1's B6/B7 are "present **iff** the model collapses."** With a purchase term and no
  purchase cost, `collapse_terms` returns `None` and all three blocks are `null`.
- **`is_estimated` is `true` for an EMPTY participating set** (§5.3A) — `any()` over ∅ is
  `False`, which would publish a *measured* typical of zero.
- **`suggested_price_minor` is `null` whenever `domain` is `null`** (§4.4B), not only when
  `break_even` is. Writing `ceil_to_step(B, domain.step_minor)` literally ships an
  `AttributeError` — a 500 where the contract wants a `null`. Reachable at
  `PriceModel(100_000, 0, 10_000)` with `T = 60`.

**The assertion-form rule, because this project has now earned it four times.** A named
mutation's check is on the **assertion form**, not the fixture: `f(0) == f(1)` is invariant
under any mutation that maps both call sites to the same value. **Prefer an exact literal
over an equality between two calls.** Compute both sides of every mutation, and run the
**whole file** — never `-k` — recording every test that reddens.

## 6. Your three delegations

`plan_2.md` §3 grants D-5 (how the participating set and median are reached — the one-copy
rule's names are private and not importable), D-6 (how the committed evaluation is loaded)
and D-7 (where the serializer is called). **Report all three choices in the handoff.**

**D-7 has a STOP attached.** Serializing router-side makes an existing test feed
`fake_run_service`'s `{"ok": "test"}` into your serializer, requiring a change to
`test_item_economics_router.py` beyond the one row the perimeter authorises. If you choose
router-side, **stop and report** rather than widening the perimeter. Service-side keeps §2
accurate and has a live precedent at `get_task_production_time.py:82`.

**D-5's silent trap:** `state in EXCLUDED_STEP_STATES` is **not** equivalent to
`_step_state_is_excluded`, which compares `.value` strings and tolerates a plain-string
state. They agree for ORM `TaskStep` rows today.

## 7. Standing rules that bite here

Charter 1–11½ in full. Named because this phase is where they apply:

- **Rule 2 — enumerate, never sample**, with its companion: **each row's fixture makes its
  own predicate the ONLY reason its outcome holds.** C1's twelve rows and C2's per-condition
  rows are exactly where a shared-cause fixture passes for the wrong reason — which is why
  C1 now states its fixture constraints.
- **Rule 11½ — tests that commit own their teardown**, in `try/finally`, naming their tables
  (precedent: `test_budget_allocations_query.py`). This is the first phase here that writes
  to the database.
- **One-copy rule** — the typical statement and the median are **not** reimplemented (D-5).
- **Tenant-boundary-row rule** — the cross-workspace case gets its own criterion (C10).
- **Rule 6** — M3, M6 and `can_commit` are all silent-failure surface.

## 8. Environment

- From `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`. **Baseline 2373 / 26 / 1.**
- **A single run is not evidence.** The failure count has been observed at 25, 26 and 27 on
  unchanged code with byte-identical ID sets. If yours disagrees with 26, **repeat and diff
  the ID sets**; a count alone is noise.
- The suite leaves ~24 `task_steps` and ~40 `step_state_records` per full run from tests
  outside these pipelines. Row-count drift is never evidence of a code change.
- **This phase ADDS a route**: the mirror counts move 25 → 26, and the mirror file's function
  name at `:123` and docstring at `:9` both need correcting. State before/after counts.
- `ruff check` and `ruff format --check` clean on every file you touch.

## 9. Scope fences

Everything in intention §10's cut list: no per-section breakdown, no already-logged card, no
cost-of-work card, no headroom bar, no percentage headline, no `terms[]`, no worker/seller
variant, **no write of any kind**, no multi-task items. **`divide_production_budget` is not
called** — C14 asserts it.

## 10. Closing protocol

1. Full suite; before/after counts, and the ID diff if any run disagrees with 26.
2. Handoff at `handoffs/implementer/2026-08-19_phase2_implement_r1_handoff.md`, charter
   frontmatter.
3. **Full write perimeter by path**, from `git status --porcelain --untracked-files=all` and
   `git diff --name-only` — never retyped.
4. **Checkpoint commit**, `CHECKPOINT (not approved):` prefix, standing authorization.
5. Architecture-graph delta at close: the endpoint and its read model belong under
   `projection-item-economics-task-price-scenario`, **which is deliberately free** — phase 1's
   node is `source-file-item-economics-price-scenario` and must not be reused for the
   endpoint. Never promote, reject or edit review items.
6. Do **not** update the master plan tracker or plan 2's Review log.

## 11. The handoff must contain

- **Criterion → test map**, one row per C1–C19, naming the test. A criterion with no test is
  stated as such, not omitted.
- **The mutation ledger**: site (file, definition vs call site), **both sides computed**, the
  complete observed-red set from a **whole-file** run, and the `sha256` confirming each
  revert.
- **D-5, D-6 and D-7**, each with the choice and its reason — and for D-7, confirmation that
  the perimeter still matches §2.
- **Any STOP**, with what you would have had to touch.
- Suite counts before and after; the route-mirror counts before and after.
