---
plan: 1
role: reviewer
round: 0 (projection — gate, mandatory)
date: 2026-08-16
pipeline: simple_production_budget_division
---

# Projection round 0 — plan 1 (typical times + budget allocations)

You are the projectionist (plan-projection doctrine,
`/Users/davidloorenz/agent-skills/pipeline-charter.md` + your role doctrine). You
implement nothing and fix nothing: you walk the planned mechanisms against the real
code and real data shapes BEFORE implementation, and deposit a ledger of everything
that would go wrong. Read-only session — your write perimeter is exactly one handoff
file.

## Read first (in this order)

1. `docs/architecture/under_construction/implementation/simple_production_budget_division/planning/intention.md` — all; §4 (M2) and §2.5 are the core.
2. `…/simple_production_budget_division/master_plan.md` — §4 naming registry, §6, §7.
3. `…/simple_production_budget_division/plans/plan_1.md` — tasks T1–T7, criteria C1–C18.
4. Code (read, verify claims independently — do not trust the intention's citations):
   - `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`
   - `app/beyo_manager/domain/item_economics/configuration.py` (status resolution + selection)
   - `app/beyo_manager/services/commands/item_economics/_common.py` (`_load_preview_inputs`)
   - `app/beyo_manager/models/tables/tasks/task_step.py`, `models/tables/working_sections/working_section.py`
   - `app/beyo_manager/services/commands/task_steps/remove_task_step.py:131-148`,
     `services/commands/tasks/force_task_ready.py:75-78,120-165`
   - `app/beyo_manager/routers/api_v1/working_sections.py`, `routers/api_v1/item_economics.py`
   - `app/beyo_manager/services/queries/tasks/step_light_bundle.py` (the batching idiom C14 cites)

## What to project (walk each with concrete numbers; pin expected values)

1. **B_seconds derivation** — `allowed_worker_minutes` is Decimal quantized to 0.01
   (e.g. `195.01`). Intention M2 says `B_seconds = allowed × 60` = `11700.6` — **not
   an integer**, and M2's arithmetic assumes integer seconds. Decide what the
   contract must say (quantize where, which rounding, does P-SUM hold against the
   rounded B) and ledger it — this is a known gap left for you deliberately.
2. **percentile_cont semantics** — interpolates on even sample counts (median of
   {600,1200} = 900, a value no group ever took) and returns numeric, not int. Walk
   odd and even samples; check the round-half-even step; state whether
   `percentile_disc` would better match "a real per-item total" and what each choice
   does to C9/C11. If it changes the intention's M1 wording, say exactly how.
2b. **D9 group aggregation (M1 as amended round 4)** — the sample unit is a
   (task, section) SUM with group-level window admission on `MAX(closed_at)`. Write
   the actual SQL shape (grouped subquery → percentile over it, sections
   left-joined) and walk it against: C9b (two same-section steps, one task), C9c
   (old first pass + recent rework — per-step window admission is the named
   failure), a group whose only steps are marked-wrong (group must vanish), and the
   `working_section_ids` filter interacting with the subquery. Confirm the existing
   `ix_task_steps_workspace_task_state` index (or an acceptable plan) covers it at
   workshop volume, or name the index the plan should add — remembering HC-2 means
   an index would need owner sign-off as the pipeline's only migration exception.
3. **Largest-remainder edge walk** — equal fractional parts (C5 fixture realism);
   `Σw` when the allocated set is empty but `D > 0` (task whose every step is
   excluded — what does E2 return?); zero allocated steps AND zero excluded; a task
   with steps but `D = 0`; `allowed_worker_minutes ≤ 0` (the `infeasible` status —
   intention §5 says numbers flow on `ok`/`infeasible`; verify M2's behavior with
   negative B is specified, not accidental).
4. **E2 batching reality** — status resolution for evaluation-less tasks needs
   valuation + selection inputs per PRIMARY item (`_load_preview_inputs` reads
   groups/basis/model versions per call). Verify constant-query-count is actually
   achievable for N mixed tasks (which loads are workspace-constant, which are
   per-item) and whether C14's statement-counting idiom exists in the repo (find a
   real precedent test or flag C14 as needing a different proof).
5. **E1 sections source** — enumerate exactly which table/filters produce "every
   non-deleted section of the workspace"; check `section_name` (E1, live) vs
   `working_section_name_snapshot` (E2, per-step) divergence after a rename — is the
   §6 consistency story still coherent for a component joining the two?
6. **Two-doors fixtures (C13)** — confirm both doors are constructible in tests
   without invoking the full remove/force services (or that invoking them is the
   right fixture strategy); verify the removal path's direct record closure
   (`remove_task_step.py:140-148`) leaves `total_working_seconds` in the state C13
   assumes.
7. **Route mounting** — verify the working-sections router's dependency/role
   conventions match what T5 assumes; verify no existing two-segment
   `/tasks/{param}` route in the item-economics router contradicts the
   declaration-order note.
8. **Rule 11½ / fixtures** — what existing factories (v1 economics tests) create
   committed evaluations + steps cheapest; name them for the implementer prompt.
9. **Contradiction hunt** — any disagreement between intention §4/§5, plan criteria
   C1–C18, and the code you read. An intention that contradicts the code is a
   ledger row, not something you silently reinterpret.
10. **Inventory sweep (you carry a waived gate)** — the mechanism-inventory session
   was waived because the intention carries contracts inline (master plan §9). Your
   condition: enumerate every mechanism this phase will ship (derivations, rounding,
   filters, admission rules, batch semantics, serialization) and check each has a
   contract in the intention. **A mechanism without a contract is severity BLOCKING
   (gate failure → route to intention), never a NOTE.**

## Output

One handoff:
`…/simple_production_budget_division/handoffs/reviewer/2026-08-16_phase1_projection_r0_handoff.md`
with frontmatter (`plan: 1, role: reviewer, round: 0, state: PROJECTED, actor: <model>`),
your **full write perimeter** declared (should be: that one file), a ledger table
(id, severity BLOCKING/PLAN-FIX/NOTE, finding, evidence `path:line`, proposed
routing), and the owner-cards section headed `⚠ OWNER DECISIONS REQUIRED (n)`
immediately after the opening summary — `(0)` with one line if nothing needs the
owner. Cards follow the charter card format (story-shaped, ≤120 words). Everything
else stays technical, written for the coordinator.

Do not edit the intention, the master plan, the phase plan, or any code. The
coordinator routes your ledger.
