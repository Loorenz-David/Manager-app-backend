---
plan: 2
role: implementer
round: 1
date: 2026-08-20
project: live_clock_for_working_time_economics
---

# Session prompt — plan 2 implement (round 1), `live_clock_for_working_time_economics`

## 1. Role and workspace

You are the **implementation executor** for phase 2: the three read surfaces go live.
Phase 1 shipped the loader, the request clock and the goldens; you wire them in.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (tests: `PYTHONPATH=. pytest -m 'not e2e'`)
Project folder:
`backend/docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/`

**Read these two files first and follow them as this session's doctrine** (plain
markdown, by absolute path):

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/implementation-executor.md`

If you are a Claude session, invoking the `implementation-executor` skill loads (2);
read (1) regardless.

**`plans/plan_2.md` is your task list. Where this prompt differs from it, the plan
file wins.**

## 2. Gate check — stop and report if any of these is false

- `master_plan.md` §3 shows phase 1 **APPROVED** and phase 2 **PROJECTED**.
- `plans/plan_2.md` §7 carries the projection-r0 consumption entry (it is the record
  that the ledger was routed; the implement prompt exists only because it was).
- `planning/intention.md` reads `RESOLVED and PLAN-READY`, latest fold **round 4e**,
  §10 ledger empty.
- Working tree clean at `ac799b3` or later.

## 3. Read order

1. `plans/plan_2.md` **in full** — §2's read-first list is your read list; walk it
   completely. §5's criteria C1–C12 and §6's delegations D4–D9 are the contract.
2. `master_plan.md` §4 (N-1…N-4), §5 (**twelve** earned rules now — the three added at
   this projection's fold bind your test-writing directly), §6 (the **current**
   baseline `26 / 2459 / 1` and its enumerated failure-ID set; the three flaky tests;
   the `TZ` fact).
3. `plans/plan_1.md` §5 **C5** and **C10**, §6's structural-facts note and delegations,
   §7's Review log.
4. `planning/intention.md` — the sections plan 2 §2 names, in full, **including HC-3A's
   scope bullet through round 4e** and §2.3A's four corrections.
5. The source files plan 2 §3 names — every one read, not assumed.
6. `.archgraph/` via the archgraph MCP: orient at start (`archgraph_status`, targeted
   searches), record the phase delta at end as **one batched** `apply_changes` with
   accurate evidence spans. **Never promote, reject or edit a review item** — three
   `ai_inferred` items sit pending the owner's adjudication and are not yours.

Do **not** read `handoffs/` or `prompts/` other than this file. The projection's
skeleton appendix is explicitly non-authoritative and must not reach you as guidance;
if you find yourself reading it, stop.

## 4. What you are building

The five ordered tasks of plan 2 §4, in order: the fold in `_build_evaluated_status`
(N-2 — the SQL aggregate is **deleted**, not kept-and-added), E-P's one-map
composition, E-A's batch probe plus `today_utc()` → `ctx.now.date()`, the two
additive `now` shims (typicals **and** `_common.py:_load_preview_inputs`), then the
tests.

**Hard scope fences — each of these is phase 3 or later, not yours:**

- No change to `budget_division.py`, `concurrency.py`, `averaged_time.py`, any router,
  or any serializer's key set.
- **The two frozen-percent feed sites stay on today's wiring** — `final.percent_consumed`
  (E-P) and the worker face's `result.percent_consumed`. That is D9 and phase 3's whole
  content. Do not "fix" them in passing.
- The three golden files and `test_live_clock_goldens.py` are **read-only in this
  phase's diff**. Any edit to them is an automatic review finding (C1).
- No closeout handoff, no frontend signal — phase 4.
- `_load_preview_inputs` is the **only** thing you touch in
  `services/commands/item_economics/`, and only additively.

## 5. Inherited hazards — not optional

1. **Every blocking finding in this project so far has been in a plan or review
   artifact, never in the implementer's code.** Phase 1's loader was correct at its
   first attempt and changed once, for a message string, across six rounds. The
   expensive direction here is *tests that cannot fail*, not code that does not work.
   Budget your effort accordingly.
2. **Three flaky tests** (§6): two named, the third permanently unattributable because
   a repeat was once performed against a bare count. If any run disagrees with the
   baseline count, **capture the failing-ID set first, then repeat.** Never repeat
   against a count.
3. **`TZ` matters in this codebase.** asyncpg reinterprets a naive datetime bind in the
   *client host's* local offset. Any observation that could depend on it is run under
   at least two `TZ` settings, one of them `UTC`.
4. **The identity-element rule.** A fixture sitting at an operator's identity element
   makes that operator untestable while the row's name says otherwise. C3's population
   row exists because of exactly this — its SKIPPED step must carry `240`, not `0`.
5. **The sort-stack rule (new, §5).** `_governing_step` applies three *stable* sorts;
   only the last applied is primary. C6's rows 2 and 3 need **different fixtures**, and
   the plan states which key each one ties. Do not merge them — the merged form is
   measurably inert, and the measurement is in plan 2 §7.

## 6. Delegations — decisions granted to you on purpose

`plans/plan_2.md` §6 carries **D4–D9** in full. They are yours to take; take them as
written, and honour each one's "record the choice as a comment at …" clause — a
delegation whose medium is a handoff line is a delegation that vanishes at closeout
(earned in phase 1). Nothing outside D4–D9 is a free choice: if you find yourself
choosing, that is a finding for the Review log, not a decision.

## 7. Mutation-ledger obligations

Master plan §5's protocol applies to every named mutation in C3–C12. Per row:

- Apply the mutation **at the site the criterion names** — file, and
  definition-vs-call-site. These differ and the plan says which.
- Run the **whole** suite (`PYTHONPATH=. pytest -m 'not e2e'`), never `-k`, never a
  single file. A `-k` run is not an observation.
- Diff the failing-ID set against §6's enumeration in **both** directions — added and
  removed. A mutation that removes a baseline ID is telling you something.
- Revert, and **verify the revert by hash**.
- Record both sides *for the named fixture*: what the contract asserts, what the
  mutation produces. "Red" is not an observation; the value is.

Where the plan states a measured expectation (C3's `840` vs `600`, C6's `stp_b` →
`stp_a`), your ledger either reproduces it or reports the discrepancy — the
coordinator re-runs every one of these independently and reconciles them ID-for-ID.

**C3's population mutation:** note the plan's explanation of why it is asserted on the
E-B face. If you also probe the E-P/E-A site, record the `KeyError` as the observed
red — it is the correct behaviour under D7, not a defect.

**C10 is a measurement, not a construction:** run the seven enumerated suites at your
head and record, **per file**, which of the two outcomes happened (time dependence /
statement shape / green as-is). Remedies go in fixtures, never in a shipped service.

## 8. Closing protocol

1. Full suite green except the enumerated baseline; count and ID-set diff recorded.
2. **Checkpoint commit the moment you reach IMPLEMENTED**, subject line prefixed
   `CHECKPOINT (not approved):` — standing owner authorization, do not stop to ask.
3. Update **only** phase 2's tracker row in `master_plan.md` §3; findings go to
   `plans/plan_2.md` §7, not the tracker.
4. Archgraph delta: one batched `apply_changes`, accurate evidence spans, no review
   adjudication.
5. Deposit your handoff at
   `handoffs/implementer/2026-08-20_phase2_implement_r1_handoff.md`, frontmatter
   `plan: 2`, `role: implementer`, `round: 1`, `state`, `date`, `actor`. It must carry:
   - an owner-readable opening (3–5 sentences, no citations) and an
     `⚠ OWNER DECISIONS REQUIRED (n)` section — "none" in one line if none;
   - the **full mutation ledger**, both sides per row, sites named;
   - the C10 per-file measurement and the C8 50-task ceiling measurement (§9A T8 —
     a Review-log obligation, with the fixture shape);
   - every delegation taken, with where its comment landed;
   - any judgment call you made that D4–D9 did not cover;
   - your **full write perimeter** from `git status` / `git diff --name-only`,
     including the archgraph delta and every file touched by a mutation probe.
