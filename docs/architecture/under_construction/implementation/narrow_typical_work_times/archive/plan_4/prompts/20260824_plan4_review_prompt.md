---
plan: plan_4
role: reviewer
round: 1
date: 2026-08-24
model: Opus 5
---

# Review — phase 4, `narrow_typical_work_times`

You are the **independent reviewer** for phase 4. Your job is not to confirm the implementer's
report; it is to **re-derive the phase's claims against the plan's criteria and the semantic
authorities, and to attack the tests that are supposed to protect them.**

**Workspace:** `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
**Test working directory:** `backend/app/`

**Doctrine, by absolute path, before anything else — it wins over this prompt where they differ:**
1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

**Do not read `prompts/coordinator/`.**

## Gate check — stop and report if any fails

1. `git merge-base --is-ancestor 353a8c9 HEAD` succeeds. **Do not pin `HEAD` to a SHA** — doc
   commits land on top of the implementation while you work.
2. `plans/plan_4.md` header reads **`state: REVIEWING`** and `master_plan.md` §4 row 4 agrees.
3. `plans/plan_4.md` §8 ends with the entry **"2026-08-24 — fix round 2 + correction 2 consumed
   → `REVIEWING`"**, and §6B exists. If that last entry is absent you have a partially folded
   plan and must stop. *(Gate on that entry, not on a count of entries — the coordinator's first
   draft of this line said "five" where there are seven, which would have halted you over a
   miscount. §9's rule about counts in prompt sentences has now fired four times in this phase.)*
4. `git status --porcelain -- app/` is **empty**. Anything under `.archgraph/` is the owner's
   live work and is **expected whatever it contains** — never enumerate it, diff it, or halt on it.

`redis-cli ping` → `PONG` before any suite run — without it this machine measures 23 failed / 2
errors, not 21, and you will misread your own stamp.

## What phase 4 was

The phase where **the engine turns on**. Both task-economics consumers derive a spec, call
`typical_times_statement` once with specs, build `SectionTypicalEvidence`, reconcile through
`uniform_basis_v1`, and feed **the same `SelectedTypical`s** to display and to weights.
`divide_production_budget`'s third parameter became `Mapping[str, SelectedTypical]`,
`DivisionStep.typical_worker_seconds` and both fallback reads were removed, `ALLOCATION_METHOD`
became v2, two goldens regenerated, and §7.2/§7.3's keys shipped.

It took a projection, two coordinator consumptions of that projection, one implementation round
and one fix round with two corrections. **Read `plans/plan_4.md` §6A and §6B before §6** — the
criteria were amended heavily and the amendments carry the measurements behind them.

## Read order

1. `master_plan.md` §§4, 5, 6.1, 6.2, 6.4, 6.5, 6.7, 6.9, 7, 8, 9, 10. **§9 is ~58 rules, each
   bought with a real defect; sixteen were added by this phase alone.**
2. `plans/plan_4.md` **in full, including §6A, §6B and all five §8 entries.**
3. The intention sections plan 4 §2 names — especially **§4A K1–K4 and K2-a**, **§3B** in full,
   **§6C**, **§7.2/§7.3**, **§11A**.
4. `handoffs/implementer/20260823_plan4_implementation_handoff.md` and
   `handoffs/implementer/20260824_plan4_fix_round2_correction2_handoff.md`.

## Evidence budget

**Your L4 budget is exactly 1 run, and it is NOT a repeat of the implementer's.**

The implementer's stamp — `2687 passed / 21 failed / 1 skipped`, 21-ID diff ∅/∅ — was taken on
`9693a26`, and **`git diff HEAD -- app/` against that tree is empty**, so it already describes
the tree you will open. Re-running the identical command is **over-evidence and a finding
against you**.

Spend the run on **genuine variation with a live question behind it**:

> `BEYO_TEST_SLOT=main PYTHONPATH=. pytest -m 'not e2e' -n 0 -p no:randomly`

**The question:** phase 4 added three integration tests to
`tests/integration/services/queries/item_economics/`, and this project has *measured* that
adding an integration **file** re-partitions `--dist loadfile` and moves its neighbours
(master plan §9, §10: the 21-ID set is **composition-dependent, not random**). Phase 2
established that the serial and parallel failing sets were identical **on its tree**. Nobody has
re-established it on a tree with three more integration tests. **If the serial set differs from
the 21-ID set, that is a finding and it outranks everything else in your review.**

Everything else runs at L1/L2. Any additional L4 requires the charter's authorization line,
written **before** the run.

## Judgment-call probes — extracted from the implementer's reports, not invented

None of these is a finding. **Judge each at source.**

1. **The new `spec_index is None` branch** (`get_task_budget_allocations.py`, +13 lines, the
   phase's only production defect fix). It resolves `(section_id, 0)` and hard-sets the narrowed
   slots to `None, 0`. **Attack it from three sides:** what happens when a task's section has
   **no** row at index 0 (a soft-deleted section named by a step — C3(c)'s shape) — is the guard
   right? Is `(section_id, 0)` guaranteed to exist whenever `K ≥ 1`? And is the `K == 0` path
   genuinely untouched, or does the new `continue` change control flow for it?
2. **C10's four rows live in one test function**, so the ledger's rows 20, 21 and 22 all report
   the same test id. The coordinator's note **N2** says each mutation must have failed at a
   different assert (`:242`, `:246`, `:250`) but that the ledger **does not show it**.
   **Verify it by running them** — this is exactly the inferred-vs-observed distinction §9
   names, and if two of those mutations actually fail at the *same* assertion, one of C10's rows
   is unarmed.
3. **C9(a)'s snapshot.** It was captured, hand-reconciled, then re-captured from `b988b8c` after
   the coordinator measured that the test **wrote its own baseline**. Now it reads
   `assert SNAPSHOT.exists()`. **Two questions:** does the committed snapshot actually contain
   pre-refactor numbers (it must have no `typical_resolution` at top level), and does
   `assert_preexisting_numeric` compare anything that would move if the refactor moved a number,
   or only keys that are trivially equal?
4. **C8's fixture precondition.** §6A requires C8's task to use only the **two well-sampled
   sections**, or `task_typical_basis` is `section_wide_uniform` and the row fails for a reason
   that is not the defect. Check the fixture actually honours that.
5. **C1, critical rank 5.** The settled-basis guard. §6A states three fixture preconditions
   (≥2 participating sections; the substituted section contains the open WORKING step; both
   `ctx.now` values inside one 90-day window). **Verify all three, and verify the mutation still
   bites with them in place.** This is the row the neighbouring pipeline calls the most expensive
   mistake available in this feature.
6. **C11's exact literals.** The criterion demands exact literals on **both** surfaces, never an
   equality between two calls. Check it is not written as `production == allocations`.
7. **B4 is openly unresolved.** Task 0's red baseline was never captured, and the implementer
   said so plainly instead of reconstructing it. **That was the correct choice and is not a
   finding against them.** Your question is what it costs: with no red baseline, is there any
   criterion whose test you cannot confirm was ever red?

## The two shapes that have cost this project the most

For each criterion, state whether it is exposed to either:

- **A row that cannot fail** — green under the very defect it names. This phase has already
  produced one (C9(a)'s self-writing baseline, caught by the coordinator) and phase 3's best
  finding was another.
- **A row that fails for the wrong reason** — two independent sufficient causes, so the mutation
  removes one and the row's colour does not change.

## Perimeter

Verify the **declared** perimeter against the tree: `git diff 353a8c9 HEAD -- app/`. The plan's
§4 names **eleven modified** (four production, one hand-maintained doc, six tests/goldens) and
**three new**. An undeclared write is a finding whoever made it. **`app/beyo_manager/routers/README.md`
is in that perimeter and no test reads it** — check it against the serializers that were actually
written, because nothing else will.

## Output

Verdict: **`APPROVED`** or **`CHANGES_REQUESTED`**.

A ledger, one row per finding, each classified **blocking** / **should-fix** / **note**, each
naming the location, what is wrong, **the evidence you gathered at source**, and the concrete
correction. Then, separately: **reality checks** (claims you verified as correct, so a later
round does not re-verify them), **refutations** (things you set out to break and could not, with
the probe), and **lessons for the plans** routed by artifact.

Handoff at `<project>/handoffs/reviewer/20260824_plan4_review_handoff.md`, frontmatter `plan`,
`role`, `round`, `date`, `actor`, `verdict`. Body: an owner-readable opening in plain words; the
ledger; reality checks; refutations; owner cards; the tree you reviewed
(`git log --oneline -1`); and a mutation-probe declaration with before/after checksums for every
file you touched.

Final chat message is the charter's **owner layer**: what you did → what it means → what happens
next → what needs the owner. One pointer line naming the handoff.
