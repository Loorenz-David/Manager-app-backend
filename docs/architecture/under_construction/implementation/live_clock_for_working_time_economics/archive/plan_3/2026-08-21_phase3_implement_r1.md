---
plan: 3
role: implementer
round: 1
date: 2026-08-21
project: live_clock_for_working_time_economics
---

# Session prompt — plan 3 implement (round 1), `live_clock_for_working_time_economics`

## 1. Role and workspace

You implement **exactly** phase 3 of this pipeline: D9 — the frozen percent blocks stop
tracking the request-level percent and derive from the frozen result record's own stored
figures. `plans/plan_3.md` is your task list and acceptance criteria. **Where this prompt
and the plan file differ, the plan file wins.**

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (suite: `PYTHONPATH=. pytest -m 'not e2e'`)
Project folder:
`backend/docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/`

**Read these two files first and follow them as this session's doctrine** (plain
markdown, by absolute path):

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

If you are a Claude session, invoking the `implementation-executor` skill loads (2); read
(1) regardless. **The charter gained a "Test-evidence scope and reuse" section on
2026-08-21 and it changes how you test — see §6 of this prompt.**

## 2. Gate check — stop and report if any of these is false

- `master_plan.md` §3 shows phase 1 **APPROVED** (`d21fe9e`), phase 2 **APPROVED**
  (`efd6b99`), and phase 3 at **PROMPT_READY (implement r1)**.
- `plans/plan_3.md` reads `state: NOT_STARTED` and its Review log carries **two**
  coordinator entries (the pre-projection amendment and the projection fold).
- `planning/intention.md` reads `RESOLVED and PLAN-READY`, changelog rounds **4a–4h**,
  and its owner ledger is **empty** (OD-10 was ratified 2026-08-21).
- No unconsumed handoff sits in `handoffs/implementer/`.

## 3. Read order

1. `plans/plan_3.md` **in full** — including §5A (what phase 2 earned), §5B (the fixture
   numbers and evidence scopes), §6 (three notes, each a trap), and §6A (your written
   delegations).
2. `master_plan.md` §4 (**N-4**, and the new `D`-namespace registry — your delegations
   are `P3-D1…P3-D3`, never `D10`), §5 (the earned rules — they bind), §6 (environment:
   the published baseline **26 / 2479 / 1 at `efd6b99`**, its enumerated failure-ID set,
   the flaky-test facts, and the **superseded** graph line).
3. `planning/intention.md` §5.3 + **§5.3A** (OD-10's contract), §4.1A B, §4.2, §9A T13,
   §10.3 D9, **§10.4 OD-10**.
4. The source files `plans/plan_3.md` §3 names — every one read, not assumed.
5. `.archgraph/` — orient only. **The graph is not clean**: 9 pending, 2 stale, measured
   2026-08-21. Those are not yours; you never promote, reject or edit review items.

## 4. What is already settled — do not re-derive it

The projection gate ran and 15 ledger rows were routed into the plan. Three things are
**measured facts**, not open questions; spending your session re-deriving them is waste:

- **N-4's identity holds unconditionally.** `calculate_variance_worker_minutes` is
  `allowed − actual` with no quantize and no clamp; both columns are `Numeric(12, 2) NOT
  NULL` with a single writer. Verified at every boundary (over-budget, zero actual, zero
  and negative allowance) by the projection, and re-derived independently by the
  coordinator at nine quantization-stressing values including half-even boundaries.
  **Cite it; do not re-prove it.**
- **No new rounding locus appears.** Exact Decimal addition under `prec = 50`; the only
  quantize is the one already inside `calculate_percent_consumed`. The STOP-and-report
  clause stays for the case you find one anyway.
- **The goldens do reach the changed path** (`15.00 / 85.00 → 15.00 %` in both golden
  files), so C5 is non-vacuous by construction and its expected bite set is written down.

What is **not** settled and is your actual work: the boundary where the identity's output
is undefined (C6), and every criterion's fixture arithmetic.

## 5. Hazards inherited — not optional

1. **The fixture you will reach for first cannot fail on half the criteria.**
   `test_phase2_live_surfaces.py:_make_live_fixture` sits at `variance_worker_minutes =
   0.00` with `actual = allowed = 20.00`, which is exactly the degeneracy §5A names: the
   reconstructed and current denominators **coincide**, so C3's and C5's mutations are
   **inert** on it. Reuse it only for C1/C2/C4b. §5B carries the computed numbers.
2. **One observation per reconstruction site.** Under the default shape there are two.
   Measured: mutating E-P alone and mutating *both* produce the **identical** ID delta,
   so a single red proves nothing about the other site. This is phase 1's
   definition-vs-call-site defect, which cost that phase a full fix cycle.
3. **Your golden instrument short-circuits.**
   `test_prechange_payloads_match_byte_golden_files` is **one** test function looping over
   three goldens, asserting in sequence — it stops at the first mismatch, so its ID cannot
   attribute which golden or which site moved. Per-site observations are how you recover
   the attribution.
4. **Two existing test files will go red for a reason that is not your bug.** They
   hand-build status/result objects with **string** minute fields; `"120.00" + "40.00"`
   silently concatenates and surfaces as `TypeError: allowed_worker_minutes must be a
   Decimal` one frame away at `calculator.py:_guard_type`. Fix the **fixtures** (give them
   `Decimal`s). Do **not** loosen `_guard_type` and do **not** make production tolerate
   strings. Both files are enumerated in §3 — a third file appearing is a STOP-and-report.
5. **A pre-existing test asserts D9's negation and stays green.**
   `test_c17_frozen_final_uses_live_percent_without_money` sits at the no-drift point.
   §6 gives you a binding choice: retarget it or record the coincidence with its numbers
   in the Review log. Silence is not available.
6. **Guard on `result is not None` at both sites** — ten parametrized cases and the
   `idle_no_result` golden serve `result=None`; an unguarded computation raises
   `AttributeError` on all eleven.
7. **You will falsify a docstring.** `_serialize_production_time_final` says "with the
   **live** percentage". Correct it in the same edit — a comment asserting a property is
   a claim and inherits the mutation rule.

## 6. Testing — the policy changed, read this

The old rule ("every mutation observation is whole-suite") is **retired**. The charter's
**"Test-evidence scope and reuse"** section governs, and `plans/plan_3.md` §5B assigns a
scope to every criterion. In short:

- Work the inner loop at **L1/L2** — the named test, the phase file, the affected domain
  trees. A full suite is not the reflexive response to a local change.
- **C5 is the exception and runs at L4** (full suite): its hypothesis is a bite set
  *outside* this phase's file, and a bite set can only be bounded by the whole suite. Its
  expected two IDs are written in the criterion — **any additional ID is a finding, not
  noise.**
- **One authoritative L4 stamp at the close of this cycle** (charter, executor Closing 1):
  full suite + linters, tree identity recorded, failure-ID delta against §6's enumerated
  26. That stamp is what the reviewer and coordinator will **cite instead of re-running**,
  so it must be honest and it must be on the tree you hand over.
- **Every evidence record carries: hypothesis · scope · exact command · tree identity ·
  result · ID delta (both directions at that scope).** Tree identity is the commit SHA
  plus an asserted-clean `git status --porcelain`; if the tree is dirty, add a digest of
  `git diff`. A record without tree identity is not evidence and will be re-run.
- Still binding, unchanged: run **every** named mutation the plan names before submitting;
  compute **both sides** and state them; apply each at the site the criterion names; revert
  and verify the revert; if a run's count disagrees with baseline, **capture the failing-ID
  set first, then repeat** (two named flaky tests exist, and a third whose identity was
  lost exactly this way).
- No `TZ` variation is required this phase — nothing on the changed path reads a clock or
  a naive datetime (the projection checked; `result.computed_at` is tz-aware and untouched).

## 7. Scope fences

- **No liveness work.** The live basis shipped in phase 2 and is not yours to touch.
- **No key added or removed on any payload** (HC-4). Nothing persisted (HC-1). No change
  to `ItemCostResult`, the analytics worker, or migrations.
- **Do not touch** `serializers.py:serialize_item_cost_result_worker` — §1 names it out of
  scope with its measured reason (no production caller). Reporting it as an omission is
  not required and changing it is out of scope.
- **Do not edit any published handoff.** The frontend document carrying the same
  `infeasible` promise is **phase 4's** to correct, by new dated document
  (master §7 obligation 2). The two internal `docs/domains/item_economics/` lines **are**
  yours (§4 task 3).
- Delegations are `P3-D1` (shape), `P3-D2` (test file), `P3-D3` (fixture literals) — see
  §6A, including the **measured cost** of the service-layer shape. Take them explicitly
  and record which you took.

## 8. Closing protocol (in order)

1. **The cycle's one L4 stamp**: full suite + `ruff` green except the enumerated baseline;
   record tree identity and the both-direction ID delta.
2. **Every named mutation in `plans/plan_3.md` §5 run at its named site**, at the scope
   §5B assigns — C3 and C5 **per reconstruction site**, C5 at L4 — each recorded as a full
   evidence record, each reverted, the revert verified.
3. Tracker row → `IMPLEMENTED` (date, actor, one line with test counts). **Your row only.**
4. **Review log entry** in `plans/plan_3.md`: what you built, every judgment call with its
   rationale, the delegations you took and how, deviations with justification, and the
   `test_c17` disposition (retarget or record — §6 obligation).
5. Architecture graph delta if the phase warrants one; **the graph is already dirty (9
   pending / 2 stale) and that is not yours to clean**. Declare what you added.
6. **Handoff file** at `handoffs/implementer/2026-08-21_phase3_implement_r1_handoff.md`,
   charter row schema (`plan`, `role: implement`, `state`, `date`, `actor`), declaring your
   **full write perimeter** — documents, code, tool-recorded state, and every file a
   mutation probe touched (applied-and-reverted), listed separately from the change itself.
   Any question only the owner can settle goes in an `⚠ OWNER DECISIONS REQUIRED` section
   as a decision card (charter format); if there are none, say so in one line.
   **The handoff file, not your chat message, is what the coordinator consumes.**

Checkpoint-commit at `IMPLEMENTED` under the owner's standing authorization, subject
prefixed `CHECKPOINT (not approved):`. Never squash.
