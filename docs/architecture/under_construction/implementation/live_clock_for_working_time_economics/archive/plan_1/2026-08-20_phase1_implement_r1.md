---
plan: 1
role: implementer
round: 1
date: 2026-08-20
project: live_clock_for_working_time_economics
---

# Session prompt — plan 1 implement (round 1), `live_clock_for_working_time_economics`

## 1. Role and workspace

You are the **implementing agent** for phase 1. You execute `plans/plan_1.md` — **the
plan file is your task list; where this prompt differs, the plan file wins.**

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (tests: `PYTHONPATH=. pytest -m 'not e2e'`; the bare
`make test` form fails collection in some shells)
Project folder:
`backend/docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/`

**Read these two files first and follow them as this session's doctrine** (plain
markdown, by absolute path):

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

If you are a Claude session, invoking the `implementation-executor` skill loads (2);
read (1) regardless.

## 2. Gate check — stop and report if any of these is false

- `master_plan.md` §3 shows phase 1 at **PROJECTED** (its projection ledger is fully
  routed) and no phase before it exists to be unapproved.
- `plans/plan_1.md` header reads `state: NOT_STARTED` and its Review log's only entry
  is the coordinator's projection-consumption line of 2026-08-20.
- `planning/intention.md` reads `RESOLVED and PLAN-READY (round 4a, …)` with the
  round-4b changelog entry present.
- Working tree clean at start; `git log -1` is `1035384` or a descendant that touched
  only `docs/`.

## 3. Read order

1. `master_plan.md` — §4 (decisions N-1…N-4 — N-1 and N-3 are your build targets),
   §5 (standing rules; the mutation-ledger obligations bind every named mutation),
   §6 (environment; **the baseline you diff against: 26 failed / 2436 passed /
   1 deselected at `2711b58`, ID set enumerated there**).
2. `plans/plan_1.md` — in full. §4 is your ordered task list; §5 your acceptance
   criteria C1–C10; §6 carries your three **written delegations** (D1–D3) and the
   phase notes.
3. The intention sections plan 1 §2 names: §1A, §3.1/§3.1A, §3.2/§3.2A, §3.3/§3.3A,
   §9A.
4. The source files plan 1 §2 names — read before writing; the pattern-authority rule
   applies (contracts and plans say how to write; implementation files only say what
   exists).

## 4. Phase constraints — not optional

- **Sequencing is a criterion.** The T5 goldens + their assert test land in your
  **first checkpoint commit**, before any other change of this phase (C2). A golden
  captured after any change is a gate failure.
- **Hard scope fence:** exactly the files in plan 1 §3. No service, serializer,
  router, or `budget_division.py`/`concurrency.py`/`averaged_time.py` change — the
  surfaces go live in phase 2, D9 in phase 3. All three endpoint payloads stay
  byte-identical throughout (C1/C2 prove it).
- **HC-1A:** no code you write assigns to `TaskStep.total_working_seconds` — the
  loader computes and returns; it never mutates.
- **Delegations D1–D3** (plan 1 §6) are decisions granted to you **in writing** —
  take them, record what you chose in your handoff; everything else the artifacts
  determine, and a point they do not determine is a **STOP-and-report**, not a
  judgment call.
- **Every named mutation** (C5's naive-elapsed at the loader call site, C7's
  `max(entered_at)` anchor, C8's inserted clock read): compute both sides, apply at
  the named site, run the **whole suite**, record the complete observed-red ID set
  diffed against §6's baseline set, revert, and verify the revert byte-identical
  (hash). A `-k` or single-file run is not an observation.
- **A count disagreeing with baseline is repeated and its ID set diffed** before any
  conclusion — two named flaky tests exist (master plan §6). A single run is not
  evidence.
- **Tests that commit rows own their teardown** (`try/finally`) — C5's fixtures
  commit; the golden fixtures are flush-only per D3.

## 5. Closing protocol

1. Full suite run(s); counts and the failure-ID diff against §6's enumerated set.
2. Append your entry to `plans/plan_1.md` §7 (Review log): date, actor, what shipped,
   test count delta, the mutation-ledger table (mutation / site / observed-red IDs /
   revert hash), and the golden-capture checkpoint hash.
3. **Architecture graph** (`.archgraph/` via archgraph MCP): record the phase delta in
   ONE batched `apply_changes` — the new `live_worked_seconds` module and its read
   dependencies (step-state records via the analytics wrapper), evidence anchored by
   **symbol**, summaries without counts. You never promote, reject or edit review
   items. If a graph claim contradicts the code, file it per the
   archgraph-discrepancies route in your handoff; do not work around it.
4. **Checkpoint commit** at IMPLEMENTED, subject prefixed
   `CHECKPOINT (not approved):`, under the owner's standing authorization. (Plus the
   earlier goldens-first checkpoint from §4 — two commits minimum this phase.)
5. Deposit your handoff at
   `handoffs/implementer/2026-08-20_phase1_implement_r1_handoff.md` with charter
   frontmatter (`plan: 1`, `role: implementer`, `round: 1`, `state`, `actor`, `date`)
   containing: what shipped per task; the delegation outcomes (D1 values, D2 choice,
   D3 confirmation); the mutation ledger; suite counts with the ID diff; the two
   checkpoint hashes; and your **full write perimeter** generated from
   `git status` / `git diff --name-only` — documents, code, and tool-recorded state
   (archgraph delta), never retyped from memory.
6. Do **not** update the master plan tracker — the coordinator owns it.
