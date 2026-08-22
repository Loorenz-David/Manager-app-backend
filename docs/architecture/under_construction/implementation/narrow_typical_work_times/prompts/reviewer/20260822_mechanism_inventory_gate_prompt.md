---
plan: mechanism_inventory_gate
role: reviewer
round: 0
date: 2026-08-22
---

# Session prompt — mechanism-inventory gate on `narrow_typical_work_times`

## Role and workspace

You are the **mechanism-inventory gate** for the `narrow_typical_work_times` pipeline —
an adversarial, standalone session. You audit **mechanisms**, not meanings: assume every
mechanism description in the intention hides an ambiguity an implementer would resolve
silently in code. You are adversarial to the intention's author.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. The branch is deliberately ~126+ commits ahead of `origin/main` — **do
  not push. Do not commit** — leave all changes in the worktree; the coordinator folds
  and commits.
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below: `<project>/`).

Doctrine, read first, in this order, by absolute path — it is this session's operating
procedure and **wins over this prompt wherever they differ**:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/mechanism-inventory.md`

## Gate check (stop-and-report if any fails)

1. `<project>/planning/intention.md` header states RESOLVED with D1–D24 settled.
2. `<project>/planning/owner_decisions.md` shows **0 open cards** and an empty ledger.
3. No `<project>/master_plan.md` exists (the planner must not have run).

## Read order (after doctrine)

1. `<project>/planning/intention.md` — **§2A first** (it invalidates §2's own header),
   then front to back. This is the semantic authority; gaps route INTO it, never into
   downstream artifacts.
2. `<project>/planning/owner_decisions.md` — D1–D24 verbatim, with the owner's reasoning.
3. `docs/architecture/archives/live_clock_for_working_time_economics/planning/intention.md`
   — §1A (the HC-3A determinism contract), §2.5A (the eight-row settled-consumer
   inventory; row 5 is the typicals statement you are gating), §4.3A (the typicals path
   as a worked-seconds→allowance route; its closing sentence calls a mistake here "the
   most expensive mistake available in this feature").
4. `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7
   — the published 21-ID baseline. Context only; this session runs no suite (see
   evidence budget).
5. `docs/architecture/archives/simple_valuation_editor/master_plan.md` §5 — the shared
   earned-rules corpus. Archived location, but **binding doctrine, adopted by
   reference**.
6. Architecture graph: orient read-only (`archgraph_status`, then targeted reads). A
   generated impact context exists at `.archgraph/contexts/current-task.md` (built
   2026-08-22 from `projection-working-section-typical-times`, 51 impacted nodes) — read
   it rather than rebuilding. **Record nothing in the graph**: this is shaping-stage
   work (intention §13.4); the graph delta belongs to implementation sessions. If you
   find a graph node contradicting code, file it per the archgraph-discrepancies
   convention in your handoff — do not edit the graph.

## Deliverable A — re-grounding sweep (coordinator scoping decision, recorded)

The coordinator chose to scope the §13 step 1a re-grounding INTO this gate rather than
pre-running it, so one session owns both the sweep and the contracts it feeds.

§2A re-verified only **five** sampled citations. You sweep **every** code citation in the
intention — §2.1's table, §2.2's F-A…F-J, and each `path:line`/`path:symbol` reference in
§§3–12 — against the current tree:

- Confirm or correct each citation (file, symbol, line, and the **claim's substance**,
  not just its address — a line that moved but says the same thing is drift; a line that
  says something different is a finding).
- Record the results as a lettered amendment in the intention (e.g. §2B) with a
  changelog entry. Never renumber existing sections; other artifacts cite them.
- Any citation whose *substance* changed feeds the inventory below — a drifted fact a
  contract silently leans on is exactly a silent-failure mechanism.

**Every counted sentence in the intention is a checklist**: re-count it against what it
counts ("four consumers", "two terminals", "five citations", table row counts, test-matrix
row counts). Six pipelines of evidence say enumeration and count defects survive sweeps
that were instructed to look for them — count anyway, in both directions (sentence→table
and table→sentence).

## Deliverable B — the mechanism inventory (skill procedure, steps 1–5)

Walk the intention and inventory every load-bearing mechanism; rank by silent-failure
risk; demand a contract-grade definition **written into the intention itself** (lettered
sections + changelog) for each risky one. The intention's own §13 step 2 names a starting
set — the spec→predicate translation incl. NULL semantics; the two-population FILTER
arithmetic; the reconciliation quantifier; §3.6's sample_count naming rule; the layer-2
terminals; HC-4 — **the named set is a floor, not the inventory.**

### Named depth targets (questions the gate must answer — not conclusions)

1. **The §2A signature question.** `typical_times_statement` today is
   `(workspace_id, *, now: datetime | None = None)` and the four consumers deliberately
   split over `now` (two inject `ctx.now`, two keep a wall-clock read). §3.1, §4.2 and
   §5 propose spec-bearing forms written before that parameter existed. What is the
   contract for how the narrowing spec and the clock coexist, stated per consumer?
   Keeping the split, collapsing it deliberately, or threading spec alongside clock are
   all open designs — **contract one, or put the choice to the owner as a card; do not
   let §3/§5 stand as written.** Whatever the answer, state what HC-4's byte-identity
   claim means with respect to that parameter.
2. **The statement's output contract under multiple distinct specs.**
   `get_task_budget_allocations` dedupes hashable specs across ≤50 tasks and makes "one
   statement call for the batch" (§6.2). What is the statement's *result* contract for
   K > 1 specs — what shape comes back, and how does a caller map evidence to
   (working_section, spec)? The internal execution strategy is explicitly not contract
   (§4.2); the output shape has to be. If the intention cannot answer, that is a
   contract to write.

### Standing rules that bind hardest here

- **No adjectives for mechanisms** (charter rule 5) — any surviving adjective standing in
  for a contract is a gate failure.
- **A worked example is a test** — where the intention states numbers or a table claims
  an outcome (§3.4's resolution table, §7's payload examples, §11.1's matrix), do the
  arithmetic; a mismatch is a finding.
- **A named mutation is not accepted until both sides are computed** — §11.1 names 21
  mutations. For each mutation your contracts touch or add, state the value under the
  contract and under the mutation and confirm they differ; an inert named mutation is a
  finding (three were proved inert in one prior pipeline; all read well in prose).
- **Ranked/branching rules must be total** (skill step 4) — §3.4's policy table, §4.3's
  quantifier and §4.5's null/`<=0` gate must decide every input; undecidable rows are
  findings.
- **A `>=` in a contract implies two rows**; every `max(`/`min(`/`or 0` is a candidate
  criterion row; each fixture predicate must be the ONLY reason its row's outcome holds.

## Evidence budget (charter test-evidence section applies)

- **This session's L4 budget is exactly 0 runs.** Documents-and-code-reading gate; no
  suite execution, no test runs, at any scope — with ONE exception: if you write any
  file under a doc-guard root, run `PYTHONPATH=. pytest tests/unit/docs/` from `app/`
  (L1, ~1.3 s) before closing and record the result. The intention and this project
  folder live under `docs/architecture/`, which is inside the docs-guard roots of
  `test_retired_inline_refusal_identity_is_absent_from_live_sources` — so expect to run
  that L1 check once.
- Never start a full suite: two pytest runs in one checkout collide (shared DB slots) and
  another session may be live.
- Static reading (Read/Grep/SQL-free reasoning) is unrestricted and is where this
  session's depth belongs.

## Write perimeter (the handoff declares it in full; anything else is a finding)

- `<project>/planning/intention.md` — lettered amendments + changelog entries only.
- `<project>/planning/owner_decisions.md` — only to append new open cards, if any.
- `<project>/handoffs/reviewer/20260822_mechanism_inventory_gate_handoff.md` — your
  report (see closing protocol).
- Nothing else. No code, no tests, no graph writes, no commits.

## Closing protocol

Deposit the handoff at
`<project>/handoffs/reviewer/20260822_mechanism_inventory_gate_handoff.md` with
frontmatter `plan: mechanism_inventory_gate`, `role: reviewer`, `round: 0`,
`date`, `verdict`, `actor`. Body, in order:

1. Opening summary (verdict: PASS / amendments written / owner cards pending) — then
   immediately the section `⚠ OWNER DECISIONS REQUIRED (n)` with every card together in
   charter format (story first, branches, one recommendation, on-silence), or the one
   line "zero cards" so the owner learns nothing needs them.
2. The inventory table: mechanism / silent-failure risk rank / contract status
   (pre-existing · contracted-this-session · owner-card).
3. The re-grounding sweep results: citations checked, drift found, substance changes,
   count-check results (every counted sentence, both directions).
4. Amendments written into the intention (section letters + one-line content each).
5. Internal inconsistencies you resolved **unilaterally** by contract, listed separately
   for owner ratification — deciding which side of a contradiction wins can carry
   product consequences even when no sentence changes.
6. Anything you could not define without an owner decision (these are the cards in §1).
7. Full write perimeter, generated from `git status`/`git diff`, never retyped.
8. The L1 docs-guard result if run (command + outcome), and the explicit line "L4 runs:
   0" confirming the budget held.

**Exit gate:** every silent-failure mechanism has a contract-grade definition in the
intention (or an owner card blocking it, named). Only then does the coordinator hand to
the implementation-planner. Your verdict states which of those two states the intention
is in.

Your final chat message is the charter's **owner layer**: what you did → what you found
and what it means → what happens next → what needs you (cards verbatim, or "nothing
needs you"), under ~300 words unless cards are pending, no section numbers or file:line
citations, one pointer line naming the handoff file.
