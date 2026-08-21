---
plan: 3
role: reviewer (plan-projection)
round: 0
date: 2026-08-21
project: live_clock_for_working_time_economics
---

# Session prompt — plan 3 projection (round 0), `live_clock_for_working_time_economics`

## 1. Role and workspace

You are running the **plan-projection** gate on phase 3: the implementer's first hour
of work, done on paper, **without permission to improvise**. You are adversarial to
the plan's author — assume every task hides a decision the plan does not actually
determine. You carry no planning-session context, and that is the point: what you
cannot derive from the artifacts below, the implementer cannot either.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (suite command: `PYTHONPATH=. pytest -m 'not e2e'`)
Project folder:
`backend/docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/`

**Read these two files first and follow them as this session's doctrine** (plain
markdown, by absolute path):

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

If you are a Claude session, invoking the `plan-projection` skill loads (2); read (1)
regardless. The charter gained a **"Test-evidence scope and reuse"** section on
2026-08-21 — read it, it governs §6 of this prompt.

## 2. Gate check — stop and report if any of these is false

- `master_plan.md` §3 shows **phase 1 APPROVED** (`d21fe9e`) and **phase 2 APPROVED**
  (`efd6b99`), with phase 3 at `PROMPT_READY (projection r0)`. A phase never starts on
  an unapproved predecessor.
- `plans/plan_3.md` reads `state: NOT_STARTED`; its Review log contains exactly one
  entry, the coordinator's dated pre-projection amendment.
- `planning/intention.md` reads `RESOLVED and PLAN-READY`, carries changelog rounds
  **4a through 4g**, and its owner ledger (§10) is empty.
- No implementer prompt for phase 3 exists under `prompts/implementer/` — you run
  **before** it is compiled.

## 3. Read order — exactly the implementer's inputs, nothing else

1. `plans/plan_3.md` — **the artifact you are projecting.** Its §2 Read-first list is
   your read list; walk it completely, including:
2. `master_plan.md` §4 (**N-4 — the reconstruction formula and its verification
   obligation**), §5 (the earned rules, including the ten from phase 2 — they bind
   here), §6 (environment; the published approval baseline **26 / 2479 / 1 at
   `efd6b99`** and its enumerated failure-ID set; the flaky-test facts; the `TZ` fact).
3. `plans/plan_2.md` §5 and §7 — the criterion shapes phase 3's rows are modelled on
   and six rounds of findings against them.
4. `planning/intention.md` — the sections plan 3 §2 names, in full (§5.3 D9, §4.1A B,
   §4.2, §9A T13, §10.3). Where two changelog rounds address the same statement, the
   later one is the standing statement.
5. The source files plan 3 §3 names — **every one read, not assumed**, every citation
   resolved against the tree, plus the phase-2 code this phase consumes.
6. `.archgraph/` via the archgraph MCP if available — orientation only
   (`archgraph_status`, targeted searches). You never promote, reject or edit; three
   items sit pending the owner's adjudication and are not yours.

Do **not** read: `prompts/`, `handoffs/`, `archive/`, or any conversation summary. The
plan file is the task list; a *contradiction* between the plan and its cited
authorities is a finding, not a choice.

## 4. Depth allocation — the phase's silent-failure mechanisms

Charter rule 6 allocates your deep passes. This phase is **money and percent
derivation**: a percentage that is wrong by a few points looks entirely plausible on
screen, and the block it lives in is one a user reads as a settled historical record.
Nothing here fails loudly. Deep passes, in this order:

1. **N-4's identity — the whole phase rests on it.** `allowed ≡
   result.actual_worker_minutes + result.variance_worker_minutes` is an *asserted*
   identity, and plan 3 §4 task 1 tells the implementer to verify it before wiring
   anything. Derive it yourself from `calculator.py:calculate_variance_worker_minutes`
   and `:calculate_percent_consumed`. Where does it hold, and — the question that
   matters — **is there any input under which it does not?** Clamping, negative
   variance, a zero or absent allowance, `None` fields on a partially-populated result,
   an over-budget task. If the identity has a domain, the plan must say so and the
   criteria must have a row at each boundary of it.
2. **Quantization and rounding loci.** Both stored fields are `Numeric(12, 2)` and the
   percent is serialized through `_decimal(…)`. Plan 3 §6 asserts that no new rounding
   locus appears and makes a discovered one a STOP-and-report. Test that assertion on
   paper: reconstruct a percent by both routes at values where the two disagree in the
   last place, if such values exist.
3. **The frozen/live split — which fields freeze and which must keep ticking.** D9
   freezes the `final` block whole; D6 keeps the live percent ticking. The two live one
   payload apart. Establish from the artifacts alone exactly which keys belong to which
   set on each surface, and whether the plan's file set can implement that split without
   a key moving between them (HC-4 freezes shapes).
4. **The two feed sites and the one-copy rule.** Plan 3 §3 defaults to two serializer
   sites and permits a service-layer routing with a declared file set. Project both
   shapes far enough to say whether the plan determines the choice, or delegates it —
   and if it delegates, whether the reciprocal-comment obligation is implementable in
   each shape.

## 5. Phase-specific constraints — carried from phase 2, non-negotiable

`plans/plan_3.md` §5A is part of your read, not a summary of it. Two of its statements
are the ones most likely to be violated by a plausible-looking criterion, and your
decidability pass is where they get caught:

- **The determinism guard for this phase is C1/C2's pre-open comparison, NOT phase 2's
  two-serve byte-identity rows.** Those rows guard the loader count and whole-second
  determinism, nothing more. A criterion that leans on them to prove a *frozen* value
  is proving something else.
- **`allowed ≡ actual + variance` means a fixture with `variance_worker_minutes = 0`
  makes the frozen and live denominators identical.** That fixture cannot fail, and it
  is the most natural one to reach for. Apply the same test to every other degeneracy a
  ratio admits: a zero allowance, a zero actual, a result whose stored figures already
  equal the live ones, a re-commit that lands on the same quantized percent.

Both are instances of the class that produced **ten** of phase 2's findings across four
shapes (master plan §5 names them): degenerate fixture *value*, degenerate *controlling
term*, degenerate *procedure*, and *absent-but-recorded-as-shipped*. For every criterion
in §5, your decidability pass answers a specific question: **can I write this test right
now from the artifacts alone, with one exact expected literal per case, and is there any
state in which its expected outcome holds even when the mutation is applied?**

## 6. Evidence scope — new policy, and phase 3 is the pilot

The charter's **"Test-evidence scope and reuse"** section (added 2026-08-21 by owner
decision) replaces the previous whole-suite-per-mutation rule, and master plan §6 and
§5 have been amended to match. You do not run the suite in this session — projection is
paper work — but two things fall in your scope:

- Each of §5's named mutations implies a **hypothesis**, and the hypothesis determines
  the evidence scope (L1 targeted / L2 domain / L3 integration / L4 full suite). Where a
  criterion's hypothesis is genuinely repository-wide — an absence claim ("nothing
  anywhere reads the current evaluation for this value"), or coupling discovery — say so
  in your ledger, because those are the rows that still earn a full-suite run. **C5 is
  the row to look at hardest**: it asserts that an existing golden stays green, which is
  a claim about a test file this phase does not own.
- If a criterion cannot be turned into an evidence record — hypothesis, scope, command,
  tree identity, result, ID delta — that is a decidability finding like any other.

## 7. Closing protocol

Per `plan-projection.md`, in order:

1. Handoff to `handoffs/reviewer/`, filename `2026-08-21_phase3_projection_r0_handoff.md`,
   frontmatter `plan: 3`, `role: projection`, `round: 0`, `verdict`, `date`, `actor`.
2. Verdict **PROJECTED_CLEAN** or **AMENDMENTS_REQUIRED**.
3. An **owner-readable opening** (3–5 sentences, no citations, no jargon), then the
   charter's `⚠ OWNER DECISIONS REQUIRED (n)` section — decision cards in charter format,
   or one line saying nothing needs the owner.
4. The **decision ledger** as a table: decision point / classification (plan gap ·
   intention gap · free choice) / proposed routing. Free choices become **proposed
   explicit delegations** — the goal is zero *silent* freedom, not zero freedom.
5. Reality-check and decidability findings, each with the exact artifact and location
   (`path:symbol`, never a bare line number — master plan §5).
6. Your **write perimeter**, declared in full: documents, code, and tool-recorded state.
   You edit no plan, no intention, no code. The skeleton is discarded or survives only as
   a clearly-marked non-authoritative appendix.
7. Tracker row for phase 3 → the state your verdict implies, one line, your row only.
   The plan's Review log entry is written by the **coordinator** when it consumes your
   handoff, not by you.

The coordinator routes every ledger row before compiling the implementer prompt. Where
this prompt and `plans/plan_3.md` differ, **the plan file wins**.
