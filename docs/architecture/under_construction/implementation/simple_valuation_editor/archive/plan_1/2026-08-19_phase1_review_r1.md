---
plan: 1
role: reviewer
round: 1
date: 2026-08-19
project: simple_valuation_editor
---

# Session prompt — review r1, phase 1 (`simple_valuation_editor`)

## 1. Role and workspace

You review phase 1: the pure price arithmetic. You did not write this code and must not
assume it is correct — or wrong. Your output is findings and a verdict; **you never fix**,
and you never relitigate the plan (plan complaints are lessons, not blockers).

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` — run every command from here.
Project folder:
`backend/docs/architecture/under_construction/implementation/simple_valuation_editor/`

**Read these two files first and follow them as this session's doctrine**, by absolute path:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

**Mode: first review of the phase — the full checklist.** Master plan §7 explicitly
withholds the light MVP round here: the calibration's cheap first review is earned when most
of a phase's surface is *not* rule-6, and this phase is nothing but rule-6.

## 2. Gate check

- `plans/plan_1.md` reads `state: PROMPT_READY`; its §6 Review log carries the projection r0
  entry.
- `handoffs/implementer/2026-08-19_phase1_implement_r1_handoff.md` reads
  `state: IMPLEMENTED`.
- Checkpoint commit `b72821c` exists on `main`, subject
  `CHECKPOINT (not approved): simple valuation editor phase 1`.
- Working tree is clean.

## 3. Read order

1. `plans/plan_1.md` — the 21 criteria, §3's four delegations, §6's Review log.
2. `handoffs/implementer/2026-08-19_phase1_implement_r1_handoff.md` — the artifact under
   audit alongside the code.
3. `master_plan.md` §4 (naming registry), §5 (standing rules — note the two rules earned
   before any code was written), §6 (environment and the suite-instability rule), §7 (gates).
4. `planning/intention.md` §3.1, §3.1A, §3.1B, §3.2, §3.2A, §3.5, §4.1, §4.2A, §4.4A, §5.3,
   §7A.1, §7A.2, §12, §12A. **Read the correction banners in §4.2A, §12A.3 and §12A.9** —
   each says the opposite of what the section said two rounds ago.
5. The code: `app/beyo_manager/domain/item_economics/price_scenario.py` and
   `app/tests/unit/domain/item_economics/test_price_scenario.py`.

## 4. Settled ground — verified by the coordinator at consumption, do not re-spend

State these as settled in your handoff rather than re-deriving them:

- **Perimeter is clean.** Two application files, both new; `.archgraph/architecture.yml`
  written and declared; no other tracked modification. The checkpoint commit additionally
  swept the previously-untracked project documentation folder into version control — those
  files were **not modified by the session**, only newly tracked.
- **The revert hashes are real.** `91dbceb4…` (module) and `560dd0d2…` (tests) were
  recomputed after an independent probe and match the handoff exactly.
- **Rule 3 holds.** `_term()` (`test_price_scenario.py:45-64`) builds real `CostModelTerm`
  instances and deliberately leaves `is_deleted` unset, so the fixtures genuinely exercise
  the unflushed-`None` trap.
- **C21's forbidden set is implemented as specified** — AST direct-import walk,
  prefixes `sqlalchemy` / `beyo_manager.models` / `beyo_manager.services`, and the module
  duck-types terms through a `Protocol` as the plan required.
- **C7's float mutation arithmetic checks out**: `Decimal("1.001")` → 1001 milli-percent,
  residual 98 999; the float path truncates to 1000, residual 99 000, `Δ = 2` against a
  bound of 1. Recomputed independently.

## 5. Named probes — extracted from the implementer's report

These are where this round's attention is bought. Each is a question, not a verdict.

### P1 — the mutation ledger's observation column (start here)

**The C10 row understates its own result.** The coordinator re-applied that mutation
(`SEARCH_CAP_MINOR = 2**40 → 2**33`) and ran the whole file: **two tests redden, not one** —
`test_c10_break_even_search_is_independent_of_the_slider_band` *and*
`test_c12_degenerate_model_publishes_the_exact_infeasibility_cap`, whose assertion is the
chained `== SEARCH_CAP_MINOR == 2**40`. Both failures are correct and desirable; the defect
is in the **record**, and it implies the observation was taken from a filtered run rather
than the file.

**Probe: re-apply every ledger row's mutation yourself and run the whole test file each
time.** The ledger is the artifact the whole discipline rests on — if its observation column
is assembled from `-k` runs, then a mutation that reddens something *unexpected* would go
unnoticed, which is the failure mode the discipline exists to prevent. Report per row
whether the observed set matches.

### P2 — `collapse_terms` returns mid-loop, so its outcome is order-dependent

`collapse_terms` (`price_scenario.py`) does `return None` **inside** the term loop when a
purchase term meets a `None` purchase cost. A malformed term *later* in the sequence
therefore never raises. So for the same term set, the result depends on the order:
purchase-term-first yields `None`, malformed-term-first raises.

§3.1B fixes the order (`created_at, client_id` from `_load_preview_inputs`), and persisted
rows cannot be malformed (`ck_cost_model_terms_value_by_type`), so this may be unreachable
in production. **Probe: is it? And is order-dependence in a rule-6 mechanism acceptable
undeclared?** Charter rule 5 and the mechanism-inventory doctrine both say ordering
semantics get contracted, not inherited. Judge it on its merits and route it — a
`should-fix`, a note, or a lesson for the intention.

### P3 — the architecture-graph node

The session recorded `projection-item-economics-expected-sold-price-scenario`,
`type: projection`, evidenced by `price_scenario.py:25-209`. Three things to assess:

- **Type.** The 17 existing `projection` nodes are read models tied to endpoints. This one's
  own description says it *"performs no queries, persistence, or serialization."* The
  description is honest; is the type?
- **Name.** Siblings are `projection-item-economics-task-budget-status`,
  `…-task-budget-allocations`, `…-task-production-time`. Intention §11 says this feature's
  node is recorded *"alongside"* those two. `…-expected-sold-price-scenario` leaves the
  family, and the route is `price-scenario`.
- **Timing.** The actual projection — the endpoint — is phase 2. Does recording it now
  create a second node later, or does phase 2 extend this one?

**You never promote, reject or edit review items** — the human adjudicates. The node is
`ai_inferred` and pending, so nothing is damaged. Put your recommendation in the
human-authorization backlog.

### P4 — `digits` is now public (delegation D-4)

The implementer exposed `digits(value)` and asserted `digits(0) == 1` directly, which is the
cleaner of the two options the plan offered. Consequence: it joins the twelve public names
that become phase 2's interface. Is a bare `digits` the right thing to expose from this
module's public surface, or is it an internal that leaked through a test requirement?

### P5 — rule 2's companion, across all 21 criteria

**Each row's fixture must make its own predicate the ONLY reason its outcome holds.** This
is where this pipeline has repeatedly found decoration with a correct name. Specifically
worth checking: C4's seven shapes, C6's three rows (the two failure kinds must be
distinguishable for the right reason), C12's three rows, and C13/C20, which assert the same
two absences for different causes — does each fixture fail for its own reason if the other's
cause is removed?

### P6 — can C21 actually fail?

Plant a forbidden import in the module, confirm the test bites, revert. The purity assertion
has no precedent in `tests/unit/` and was invented this round.

## 6. Doctrine that bites hardest here

- **Re-derive, never trust the log.** Run the suite yourself. The coordinator measured
  **2372 passed / 26 failed / 1 deselected** independently; the pre-phase baseline was
  2320/26/1, so the pass count rose by exactly 52.
- **A single run is not evidence.** On unchanged code the failure count has been observed at
  25, 26 and 27 with byte-identical ID sets. If your run disagrees with 26, repeat it and
  **diff the ID sets** before concluding anything.
- **Probe the seams the checklist doesn't name** — the passing-glance clause is license.
  Type coercion, defaults on unflushed objects, and integer/`Fraction`/`Decimal` boundaries
  are the live ones in this module.
- **Report what you verified correct, specifically.** Settled ground is what makes the
  re-review cheap, and this phase's arithmetic will be composed by phase 2 without being
  re-derived.

## 7. Closing protocol

Per the reviewer skill's dual-audience rule: **layer 1** technical findings (id, severity,
violated authority with file + section, suggested correction) and **layer 2** the human
briefing in your final message — a 2–4 sentence state of the build, then a 3–6 sentence
story per blocking/should-fix finding, told from the owner's side in kronor and minutes,
strictly faithful to the verified failure.

Deposit at `handoffs/reviewer/2026-08-19_phase1_review_r1_handoff.md` with charter
frontmatter (`plan`, `role`, `round`, `verdict`, `date`, `actor`), containing:

- verdict `APPROVED` or `CHANGES_REQUESTED`;
- `⚠ OWNER DECISIONS REQUIRED (n)` immediately after the opening summary — decision cards
  only for what needs an owner *answer* (the graph adjudication in P3 is a
  human-authorization item, so it belongs here as a card or in the backlog, not buried in a
  finding). One line if there are none;
- findings by severity;
- **what you verified correct**, specifically;
- lessons for the plans — under-specified criteria, missing enumerations, process
  contradictions — which the coordinator folds upstream;
- a **mutation-probe declaration**: every file your probes touched, applied-and-reverted,
  with `sha256` confirming byte-identical, plus any state restored;
- a **carry-forward dispositions table** if you approve with open notes — every note routed
  to a named destination phase, so nothing evaporates between phases;
- your **full write perimeter** by path, generated from `git status --porcelain
  --untracked-files=all` and `git diff --name-only`.

Do **not** update the master plan tracker and do **not** write the plan's Review log — the
coordinator owns both.
