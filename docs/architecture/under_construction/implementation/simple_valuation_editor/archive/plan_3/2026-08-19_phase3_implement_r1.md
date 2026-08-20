---
plan: 3
role: implementer
round: 1
date: 2026-08-19
project: simple_valuation_editor
---

# Session prompt — implement r1, phase 3 (`simple_valuation_editor`)

## 1. Role and workspace

You close the seven notes phase 2's review raised and deliberately batched instead of
spending a fix cycle on each. **None is a behaviour defect** — review r1 applied 34 mutations
one at a time and recorded that *no mutation produced a wrong-but-green payload*. Six are
missing evidence or tidy-ups; one (F9) is latency.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` — **run every command from here**; `.env` resolves only from
this directory.

Doctrine, by absolute path: `/Users/davidloorenz/agent-skills/pipeline-charter.md` and
`/Users/davidloorenz/agent-skills/implementation-executor.md`.

**`plans/plan_3.md` is your task list. Where this prompt differs from it, the plan wins.**

## 2. Gate check — stop and report if any is false

- `master_plan.md` §3: phases 1 and 2 **APPROVED**; phase 3 **PROMPT_READY**.
- `plans/plan_3.md` reads `gate: projection WAIVED`.
- `git status` clean at head, apart from the untracked
  `live_clock_for_working_time_economics/` folder — **a different project, out of scope, do
  not read or touch it.**
- Baseline **2425 passed / 26 failed / 1 deselected**.

## 3. Perimeter — exactly two files

| Path | |
|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | F3, F6, F9 |
| `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py` | F2, F4, F5, F8 |

**Nothing else.** Not `price_scenario.py`, `calculator.py`, `cases/serializers.py`,
`serializers.py`, the router, or any mirror artifact — phases 1 and 2 are APPROVED and closed.

**If a repair appears to need a third file, that is a STOP and a report.** This project has
produced three implement blockers, all on coordinator artifacts, all correct, zero files
changed across them. **The presumption is with you.**

## 4. Running in parallel

The coordinator is authoring the frontend handoff (plan 4) at the same time, under
`backend/docs/handoff/to_frontend/` and `…/to_backend/`. **No shared files** — you touch only
`app/`. You will see new untracked documents appear there; they are not yours and not a
perimeter breach.

## 5. Read order

1. `plans/plan_3.md` — in full. Every expected value in it was computed by review r1; **write
   them down, do not rediscover them.**
2. `archive/plan_2/plan_2.md` §6 — the Review log, for what phase 2 settled and what F1–F11
   actually measured.
3. `master_plan.md` §5 — the standing rules, especially the two this round is the test of:
   **compute both sides of a named mutation**, and **a ledger's observation is a property of
   every file that asserts the mutated symbol — measure across the SUITE**.
4. `planning/intention.md` §3.1B, §5.3A, §6B, §9A.2 — the authorities the repairs restore.

## 6. Order of work, and the one that matters

**Do F4 first.** It is the only repair guarding a silent failure with a live trigger: the
previous pipeline made re-pricing write a **new chain row** rather than refuse, so supersession
chains are a common state in this system, and nothing currently pins that the endpoint reads
the *current* row. Review r1's probe: deleting `superseded_at.is_(None)` leaves the entire
phase file green.

Then F3 (one line), F5 (one fixture), F2 (one deletion). Then decide F6, F8 and F9 — **each of
those three is a decision you may resolve either way, and the unacceptable outcome is an
unrecorded one.**

## 7. Mutation discipline — this round is where the rule was earned

Mutate at the named **definition** site → run the **whole suite**, never `-k` → record **every**
test that reddens → revert → confirm `sha256` byte-identical.

Phase 2's F1 is why: the ledger recorded one reddened test where two was the truth, because
the same assertion had been duplicated into a second file and a whole-*file* run could not see
it. **Your F2 deletion is what makes that set one again — prove it across the suite.**

For each named mutation state **both sides**: the value under the contract and the value under
the mutation, confirmed different. A mutation whose two sides were never computed is a claim,
not a guard.

## 8. Environment

- From `backend/app/`: `PYTHONPATH=. pytest -m 'not e2e'`.
- **Baseline 2425 / 26 / 1.** Net expectation: −1 test (F2's deletion) + the rows you add.
  State the arithmetic.
- **A single run is not evidence.** The failure count has been observed at 25, 26 and 27 on
  unchanged code with byte-identical ID sets. If yours disagrees with 26, repeat and **diff
  the ID sets**; a count alone is noise.
- This phase writes to the database. **Rule 11½**: every test that commits owns its teardown in
  `try/finally`, naming its tables. Precedent in the same file: `test_c10_…`.
- `ruff check` and `ruff format --check` clean on both files. Note that four of phase 2's
  roster files are **not** globally formatted at baseline — do not reformat anything outside
  your two files.

## 9. Closing protocol

1. Full suite; before/after counts with the arithmetic.
2. Handoff at `handoffs/implementer/2026-08-19_phase3_implement_r1_handoff.md`, charter
   frontmatter.
3. **Full write perimeter by path**, from `git status --porcelain --untracked-files=all` and
   `git diff --name-only` — never retyped. The coordinator's new handoff documents will appear
   in that listing; declare them as not yours.
4. **Checkpoint commit**, `CHECKPOINT (not approved):` prefix, standing authorization.
5. Architecture graph: this phase adds no architectural concept. Expect a **0-node, 0-edge**
   delta and say so. If F9 collapses the duplicated loads, the projection node's evidence span
   may drift — **report the drift, do not repair it**; a pending `ai_inferred` item's addresses
   are the coordinator's to correct, and the route is narrower than it looks.
6. Do **not** update the master plan tracker or plan 3's Review log.

## 10. The handoff must contain

- **Criterion → test map** for C1–C7, one row each.
- **The mutation ledger**: site, **both sides computed**, the complete observed-red set from a
  **whole-suite** run, and the `sha256` per revert. Include the F2 confirmation row — that
  `max(6, quantity)` now reddens exactly one test.
- **F6, F8 and F9: what you decided and why**, in prose. These are the three the plan
  deliberately left open.
- **Any STOP**, with what you would have had to touch.
- Suite counts before and after, with the arithmetic reconciling the deleted test against the
  added rows.
