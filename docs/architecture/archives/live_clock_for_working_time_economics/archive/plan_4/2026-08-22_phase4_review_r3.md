---
plan: 4
role: reviewer
round: 3
date: 2026-08-22
project: live_clock_for_working_time_economics
---

# Phase 4 — review r3: the phase's first external review (full checklist)

You are the **independent reviewer** for phase 4 of
`live_clock_for_working_time_economics`. This is the phase's **first review round** — a
full checklist against the plan's criteria and the semantic authorities, not a delta
review, even though a fix cycle has already run.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`

Doctrine, by absolute path, read first and follow as session doctrine:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-reviewer.md`

## Why a documentation phase gets a full round

Phase 4 ships no code. Its projection gate was waived on that basis and the review was
**not** — deliberately. In this project every blocking finding of the last three phases
was in a plan, a criterion, an intention section or a coordinator note, never in the
implementer's code; and the valuation pipeline's comparable documentation phase drew 24
findings across three rounds, every blocking one in coordinator-authored prose. **The
prose is the deliverable here, so the prose is the attack surface.** Two of this phase's
three fix-round findings were in sentences that sounded correct.

## State

- Plan: `plans/plan_4.md`, `state: IMPLEMENTED` (implement r1 → coordinator consumption →
  fix r2). Criteria are §5: **C1–C9**. Note C4 and C9 were amended/added by the
  coordinator on 2026-08-22 *before* implementation; §6A's baseline bullet is superseded
  and kept only as provenance — read the superseded marker, do not follow the old text.
- Deliverable: `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md`
- Tool-recorded deliverable: the `.archgraph/` delta — five relationships (r1) and five
  node descriptions (fix r2).
- Checkpoints: `80b8cca` (r1) → `3df02ae` (fix r2). Coordinator consumption is `e13923f`.
- Semantic authority: `planning/intention.md`. Environment authority: `master_plan.md` §6,
  **first block**. Obligations: `master_plan.md` §7, all seven rows.

## Verified perimeter — step 1, before anything else

`git diff 80b8cca 3df02ae --name-only` and `git show --stat 3df02ae`. The fix cycle's
allowed perimeter was: the new frontend handoff, `.archgraph/`, `plan_4.md`,
`master_plan.md` (own row only), and its handoff. **Anything else is an automatic
finding.** Note `master_plan.md` §7 lists three recognized external commit streams whose
files are foreign-but-expected; consult it before attributing.

## Settled by coordinator measurement — do NOT re-spend these

Each was verified against the tree, not read from a ledger. Re-running them is
over-evidence and is itself a finding; if you doubt one, vary it rather than repeat it.

- **Perimeter, both rounds** — exactly as declared; **nothing under `app/`** in either
  (`git diff 0aae85e HEAD -- app/` empty), and the only file under `docs/handoff/` is the
  new one, so no published handoff was edited.
- **The 21 published failing IDs** `comm`-diff **empty in both directions** against the
  authoritative enumeration in
  `test_isolation_and_xdist/archive/plan_3/2026-08-22_phase3_fix_r5_handoff.md`, and the
  five removed IDs match master §6's five exactly.
- **`dc76db8` resolves** to the stated subject and `git diff dc76db8 HEAD -- app/` is
  empty — so S2's republished tree identity is sound.
- **No evidence `summary` or `inferenceReason` was touched** by the description edits —
  zero matching `+`/`-` lines in the `architecture.yml` diff. The HC-5 invariant on the
  budget-allocations node survives with its wording unchanged.
- **Graph status reproduces**: revision `897d57b3…`, 194 nodes / 296 edges, 5 pending,
  0 stale, 0 diagnostics. The 5 pending are r1's `ai_inferred` relationships; the
  maintenance edits moved no count and the five nodes remain `human_confirmed`.
- **C7's tripwire is non-vacuous over this document — measured, not assumed.** The
  coordinator inserted the retired identity token into the new handoff and ran the guard:
  **1 failed / 58 passed**, the single red being
  `test_item_economics_handoff_accuracy.py::test_retired_inline_refusal_identity_is_absent_from_live_sources`
  at its rglob line. Probe reverted, file SHA-256 byte-identical
  (`257093891e1c…`), tree clean. So "59 passed" is a real green, not a green wired to
  nothing. **Do not re-run this probe.**
- **§6A B's "one disowning action produces two drops" is correctly ABSENT** from the
  document: §6A C opens *"the closeout handoff tells the frontend what to do, not what we
  believe"*, and C's "any decrease → render the served value" already covers the later
  drop. This was examined and closed; do not file it as a gap.

## Probes — where this round's depth goes

**P1 — the reserved judgment call (this is yours to decide, and it was kept open for
you).** The document's decrease mode 2 says *"Record deletion is not a shipped client
event and is not a cause to handle."* Intention §6A A says E5 is not a capability and that
*"naming it to the frontend as a decrease cause would be telling another codebase to
handle an event our API cannot emit"*; plan C5 requires that record deletion is **not
named as a cause**. The document names it as a **non**-cause. The coordinator judged
C5's literal met and the authority's rationale arguably brushed, and **deliberately did
not decide it** — the fix prompt instructed the implementer to leave the sentence
untouched so you would meet an unresolved call rather than a pre-empted one. Decide it,
and say which way and why.

**P2 — the fifth node, the implementer's own declared judgment call.** C6 says "five nodes
updated"; the fix prompt said to handle `projection-item-economics-task-price-scenario`
"on its own terms". Its description now claims it *"composes task budget status and so
inherits that read's worked-time dependency transitively; it publishes no live worked-time
field of its own and reads no open interval record directly."* **Verify all three clauses
at source** (`get_task_price_scenario.py`), not against the handoff's account of them. A
description that overstates is the graph's version of a false comment.

**P3 — C5 against §6A C, row by row, re-derived independently.** The coordinator found one
drift here (S1: *"do not animate the descent over time"* had shipped as *"never animate
time that the workspace has disowned"*, satisfiable by an ease-out) and it was repaired.
**Do not trust that the list is now complete because one member of it was fixed** — this
project's signature failure is a class re-appearing inside the correction of its own class,
six times so far. Re-derive §6A C's rules from the intention and check each against the
document yourself. One specific tension worth judging: mode 1 says *"a visible snap is not
required"* while §5's closing paragraph says smoothing *"must snap down to the served
value rather than clamp"* — decide whether a client can obey both.

**P4 — C9's baseline block, element by element.** C9 enumerates what must be published:
the 21 IDs written out, the runner (six workers, `--dist loadfile`), Redis, the per-process
disposable database, tree identity, and the subset relation. The ID set and the tree
identity are settled above. **What is not settled**: whether every other element is
present and *correct*, and whether the block is usable by a reader with no access to this
project. The consumer is `narrow_typical_work_times` D23, which will regenerate two goldens
against this baseline. Judge it as that reader.

**P5 — do the four new node descriptions describe what the code actually does?** They now
assert a specific mechanism: *settled working seconds plus the concurrency-averaged share
of any open WORKING interval, resolved once per request through the shared live
worked-seconds loader, persisted nowhere.* Verified so far: only that the text changed and
that no evidence summary moved. **Nobody has checked the claims against source.** Check
them per node — the batched allocations node's "one shared map loaded once per request"
and the production-time node's "passed both to budget status and into the allocator's
response-only step rows" are the two most specific and therefore the two most falsifiable.

**P6 — the full checklist: obligations 1–6 against the intention.** C1, C2, C3, C4, C8.
Every numeric claim in the document (bounds, modes, windows, the ≤ 1 s parity bound, the
"roughly 48 hours" overnight-close condition, the cost statement) traced to the intention
section that derives it. C4 must cite **both** §2.3A (feasibility) and §3.4A (cost) — that
amendment was made before implementation because the intention and the master plan
disagreed; confirm it survived. C4.3 must carry the **eight-row** consumer list, not four.

**P7 — the graph now expresses one dependency twice; judge whether that is right.**
`projection-item-economics-task-budget-status` carries a pre-existing `human_confirmed`
`reads_from` → `projection-live-worked-seconds` (phase 2's edge, promoted 2026-08-21) and
now also r1's `reads_from` → `table-step-state-record`. Intention §8 asks for the table
edge "as the graph vocabulary allows", diagnostics are 0, and both are defensible — but
nobody has ruled on whether the graph now overstates the dependency or records it at two
legitimate granularities. If you find a genuine conflict, file it per the
`archgraph-discrepancies` route; **do not promote, reject or edit any review item** —
graph adjudication is the owner's, always.

**P8 — anything seen wrong in passing.** The charter's clause is not decorative; it has
caught real defects in this project every round it was exercised.

## Evidence budget

**This session's L4 budget is exactly 0 runs.** Review entry earns an L4 stamp only when
your tree differs from the last recorded stamp; it does not. `git diff 0aae85e HEAD --
app/` is empty, so the authoritative baseline (master §6's gate block: **21 failed /
2576 passed**, collection 2597, six workers, `--dist loadfile`, Redis reachable, taken on
`dc76db8`'s `app/` tree) is **citable by tree identity, not reproducible for
independence**. Re-running it is a finding against this session.

Everything you need runs at **L1** — `PYTHONPATH=. pytest tests/unit/docs/` from `app/`,
or a narrower selection. Source reading and graph queries cost nothing.

If a probe genuinely requires L4, write the charter's authorization line **before** the
run: one sentence saying "narrower evidence insufficient because …". Then it is not a
violation. Two hazards if you do: `PYTHONPATH=.` is required, and **two pytest runs in
the same checkout collide** — never run one while another session is running the suite.

Any mutation probe you apply is reverted and **proven** reverted (hash or `git status`),
and named in your handoff's applied-and-reverted list.

## Verdict and closing protocol

Verdict is one of `APPROVED` / `CHANGES_REQUESTED` / `OWNER_DECISIONS_PENDING`. Findings
graded **blocking / should-fix / note**, each with the correction clause stated
operatively — name the source of truth, not the symptom, because your clause is quoted
verbatim into any fix prompt and a summary loses the instruction.

Deposit at `handoffs/reviewer/2026-08-22_phase4_review_r3_handoff.md` with the charter's
frontmatter (`plan`, `role`, `round`, `date`, `verdict`, `actor`), declaring your **full
write perimeter** (documents *and* tool-recorded state), your evidence rows with tree
identity, and a section headed `⚠ OWNER DECISIONS REQUIRED (n)` immediately after the
opening summary — or one line saying zero.

Close with **lessons for the plans**: for each, name the artifact that should absorb it
(intention / master plan / this phase's criteria / the next phase's prompt). The
coordinator routes them; you name the home.
