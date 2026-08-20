---
plan: 1
role: reviewer
round: 1
date: 2026-08-20
project: live_clock_for_working_time_economics
---

# Session prompt — plan 1 review (round 1), `live_clock_for_working_time_economics`

## 1. Role and workspace

You are the **reviewer** for phase 1 — first review, full checklist. Adversarial
re-derivation against the plan's criteria and the semantic authorities; the
implementer's handoff is a set of **claims to verify**, never a source of truth.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (tests: `PYTHONPATH=. pytest -m 'not e2e'`)
Project folder:
`backend/docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/`

**Read these two files first and follow them as this session's doctrine** (plain
markdown, by absolute path):

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

If you are a Claude session, invoking the `plan-reviewer` skill loads (2); read (1)
regardless.

## 2. Gate check — stop and report if any of these is false

- `master_plan.md` §3 shows phase 1 at **REVIEWING (r1)**.
- The implementation exists at checkpoints `1081a2b` (goldens only) and `a7659bc`
  (the rest); working tree clean at a descendant of `a7659bc`.
- `plans/plan_1.md` §7 carries three entries: the projection-consumption line, the
  implementer's line, and the coordinator's consumption line of 2026-08-20.

## 3. Read order

1. `master_plan.md` §4 (N-1, N-3 — the build targets), §5 (standing rules — the
   mutation and ID-set disciplines bind you too), §6 (environment; baseline
   **26 / 2454 / 1** now includes this phase's 18; the 26-ID set is enumerated
   there).
2. `plans/plan_1.md` in full — criteria C1–C10 are the review checklist; §6 carries
   the delegations D1–D3 (granted in writing — you verify the *outcomes* were
   recorded and sound, you do not relitigate the grants); §7's Review log includes
   what the coordinator already verified.
3. Intention §1A, §3.1/§3.1A, §3.2/§3.2A, §3.3/§3.3A, §9A — the semantic authorities.
4. The implementation diff: `git diff 08fc141..a7659bc` (code) and the handoff at
   `handoffs/implementer/2026-08-20_phase1_implement_r1_handoff.md` (claims).

## 4. Already verified — do not re-spend these passes

The coordinator verified at consumption (plan 1 §7, last entry): the write perimeter
against git; goldens-first sequencing from checkpoint content; the clean-suite count
and failure-ID set; and **all three named mutations re-applied whole-suite with
reverts hash-verified** — including resolving a discrepancy in mutation 3's site
description (both shapes measured; the record is in the Review log). Do not re-run
the three named mutations. Everything else is yours — and anything you see wrong *in
passing*, in any area, you report (that clause catches real bugs; it is not
decorative).

## 5. The checklist — C1–C10 against the artifacts, plus named probes

Walk every criterion C1–C10 in `plans/plan_1.md` §5 against the shipped code and
tests: assertion forms, fixture reasons (each row's predicate the ONLY reason its
expected value holds), exact-literal discipline, teardown ownership. Then, the
probes — extracted from the implementer's own report and the coordinator's
consumption, in priority order:

- **P1 — the naive-`now` boundary guard (the one with teeth).**
  `live_worked_seconds.py:load_live_worked_seconds` opens with an explicit
  `TypeError` guard the plan did not order; the plan's C9 expected the failure
  "inside the sweep". The implementer's justification: *"the configured asyncpg path
  normalizes a naive bind value at the SQL boundary, so the loader preserves the
  contract with a loud boundary check."* Three things to settle, each by
  computation, not reading: (a) **delete the guard and run the C9 row** — with an
  open working record present, does the sweep's `(end − entered_at)` raise the
  TypeError naturally anyway? (b) with **no** open record for the probed steps, does
  a naive `now` pass silently through the guarded-less loader (the case where the
  guard is the only loud path)? (c) reconcile the asyncpg claim — what actually
  happens to a naive bind on this driver, and does it matter given the probe query
  carries no `now` bind? Then recommend: the guard is a **semantic addition**
  (charter fold-back rule) — should intention §1A HC-3A absorb "the loader fails
  closed at its own boundary" as the contract, with a mutation row that bites on the
  guard's deletion? Route the recommendation; do not edit the intention.
- **P2 — C7's expected `90900`, by hand.** Re-derive it from the fixture's
  timestamps against `concurrency.py:_sweep`'s segment rules, and verify the fixture
  honors A9's separation constraint (the closed record's `exited_at` precedes
  `max(entered_at) − 1 day`) — the constraint the mutation's discrimination depends
  on.
- **P3 — the golden composition, walked against plan task 1 exactly.** Two task keys
  per file; E-B both faces captured at their own serialization sites; E-A one
  single-task call per task (never batched); the typicals-invariance constraint (no
  `COMPLETED` fixture step, every `closed_at` NULL) actually holds in the fixture;
  both required docstring rationales present (typicals invariance; the
  D9-divergence note on fixture b). A golden that quietly violates the composition
  is worth a finding even while byte-green today — it fails in phase 2 or 3 where
  the diagnosis costs a round.
- **P4 — attribution semantics.** The loader groups by
  `record.credited_user_id or record.created_by_id` (Python `or`); the contract says
  `COALESCE` (§3.1A). The two differ on empty-string values. Establish whether any
  writer can produce `credited_user_id == ""` (check the commands that set it); if
  none can, a note recording the scope of the equivalence suffices; if one can, it
  is a finding.
- **P5 — the zero-cases row.** One test carries two predicates (future entry;
  missing attribution). Per the charter rule 2 companion: does each step's fixture
  make its own predicate the only reason its `0` holds?
- **P6 — teardown audit.** Which phase tests commit rows? `_apply_step_transition`
  does not commit per its docstring, and the fixtures ride the rollback-scoped
  `db_session` — confirm nothing in the phase's tests commits, or that whatever does
  owns a `try/finally` (charter 11½). Row-count residue is never evidence (master
  plan §6).
- **P7 — the graph delta.** Three pending `ai_inferred` items were created (node +
  edges). Verify their evidence anchors resolve by **symbol**, summaries carry no
  counts, and the recorded shape matches what shipped. You never promote, reject or
  edit — the owner adjudicates; report what you find.

## 6. Constraints and closing protocol

- Suite discipline: full runs; a count disagreeing with the recorded baseline is
  repeated and its **ID set** diffed (two named flaky tests, master plan §6). Every
  mutation you apply yourself: both sides computed, named site, whole suite,
  reverted, revert hash-verified.
- You write your handoff and nothing else — no code edits, no plan edits, no tracker
  row. Any mutation probes you apply are reverted; your handoff **declares every
  probe applied and its revert**, and your full write perimeter from
  `git status` / `git diff --name-only`.
- Findings routed by severity per the plan-reviewer doctrine: blocking / should-fix /
  notes, each with the exact artifact and citation (`path:symbol`), plus **lessons
  for the plans** the coordinator folds back.
- Owner cards, if any, in ONE `⚠ OWNER DECISIONS REQUIRED (n)` section directly
  after your opening summary; one line saying "none" if none.
- Deposit at `handoffs/reviewer/2026-08-20_phase1_review_r1_handoff.md`, charter
  frontmatter (`plan: 1`, `role: reviewer`, `round: 1`, `verdict`, `date`, `actor`).
