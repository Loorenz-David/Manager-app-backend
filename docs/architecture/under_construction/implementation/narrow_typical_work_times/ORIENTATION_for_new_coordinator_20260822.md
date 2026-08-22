---
project: narrow_typical_work_times
role: coordinator
date: 2026-08-22
written_by: the outgoing live_clock_for_working_time_economics coordinator, at that pipeline's closeout
---

# Orientation — incoming coordinator, `narrow_typical_work_times`

You have **no conversation history and do not need any.** Everything is here or cited by
path. Read this once, then read §3's list.

Repo at writing: branch `main`, HEAD `7bac5d1`, worktree clean, **126+ commits ahead of
`origin/main` deliberately — do not push without asking.**

## 1. Your role

You are the **pipeline coordinator**. You author prompts into `prompts/<role>/`; the owner
passes them to implementer (Codex) or reviewer (Opus 5) sessions; you consume the handoffs
those sessions deposit in `handoffs/<role>/` **adversarially** — verifying claims against
git and the tree rather than believing them, and spending verification on **variation**
rather than re-running what a tree-matched record already proves.

Doctrine, in reading order, by absolute path:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/pipeline-coordinator.md`

**The owner is not a reviewer.** The charter's "owner layer" governs every message you send
them: what you did → what it means in plain words → what happens next → what needs you. No
section numbers, no `file:line`, no finding IDs. Decision cards are relayed **verbatim**;
re-compressing one into a tidy table is how the story dies and the human rubber-stamps.

## 2. Where this project actually is

**The intention is RESOLVED with zero open cards** (D1–D24 settled). Nothing else exists
yet — no master plan, no phases, no prompts, no handoffs. The folder is
`planning/intention.md` + `planning/owner_decisions.md` and nothing more.

**The next step is the mechanism-inventory gate** (§13 step 2). Not planning, not
implementation. That gate is a separate skill —
`/Users/davidloorenz/agent-skills/mechanism-inventory.md` — run in its own session by
**Opus 5**, and your job is to compile its prompt.

**D23's blocker is gone.** The intention was written while `live_clock_for_working_time_economics`
was still running, and D23 serialized this project behind it. That pipeline **closed
2026-08-22**, all four phases APPROVED, merged as `57d8c25`. So implementation may follow
the gate rather than waiting on anything.

## 3. Read order

1. **`planning/intention.md` §2A first** — it is the newest thing in the document and it
   invalidates the header of the section above it. Then the intention front to back; it is
   the semantic authority and nothing downstream patches it (gaps route *up*).
2. **`planning/owner_decisions.md`** — D1–D24, all settled, with the reasoning.
3. **`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7** —
   the published baseline D23 tells you to regenerate goldens against. Read it there; it is
   the authoritative copy, not a master plan's summary of it.
4. **`docs/architecture/archives/live_clock_for_working_time_economics/planning/intention.md`,
   §2.5A and §4.3A** — the two sections of the neighbouring pipeline most likely to change
   how you read this one. §2.5A is the eight-row inventory of everything consuming settled
   step seconds (row 5 is the typicals statement you are about to refactor); §4.3A calls
   that path *"the most expensive mistake available in this feature"* and it had no guard
   anywhere in the repository until that pipeline's phase 2 round 6.
5. **`docs/architecture/archives/simple_valuation_editor/master_plan.md` §5** — the shared
   earned-rules corpus (~30 rules, six pipelines), adopted by reference and binding. It is
   archived but it is **doctrine, not history**.

## 4. The finding waiting for you, and why it is first

**`planning/intention.md` §2A**, written 2026-08-22 and measured, not asserted.

The intention was grounded on 2026-08-20. The shared files moved on 2026-08-21/22. A
sample of five call-site citations found **four had drifted** — and one drift is not a line
number:

`typical_times_statement` **gained an injected clock** (`now: datetime | None = None`), and
the four consumers deliberately split over it — production-time and budget-allocations pass
`now=ctx.now`, the working-sections route and price-scenario keep their own wall-clock read.
**§3's proposed signature and §5's call form were written before that parameter existed and
erase both it and the split.** A refactor built literally from them compiles, reads fine,
and returns two endpoints to a wall-clock read on the request path — violating the
neighbouring pipeline's HC-3A determinism contract and reddening its byte-identity goldens
for a reason nobody would connect to typicals.

**§2A does not rule on what to do about it** — keeping the split, collapsing it
deliberately, or threading the spec alongside the clock are all open designs. It is a
mechanism the gate must contract. Two consequences for you:

- **The gate prompt should name it as a depth target** without telling the gate what to
  conclude.
- **§2A is a sample, not a sweep.** ~30 further citations in §2.2 and §§4–11 were never
  re-checked. Re-grounding is owed before the planner runs; §13 step 1a now says so.

## 5. The calibration seal — do this before you author the gate prompt

The mechanism-inventory gate in this lineage runs with a **calibration seal**: before
writing the prompt, you seal your own hypotheses about what the gate will find, into
`prompts/coordinator/<date>_inventory_calibration_seal.md`, with an honest contamination
statement (say which of your hypotheses the prompt's own scope rows will hint at). You open
it at the fold and record which hypotheses the gate found, exceeded, or missed.

It earns its keep. Last time: two hypotheses found and one **exceeded** — the gate corrected
the seal's own arithmetic — and one **missed by the sweep**, a three-vs-four count in a
list, caught only at the coordinator's fold. The standing lesson from six pipelines is that
**enumeration and count defects survive even a sweep instructed to treat counted sentences
as checklists**, so your consumption pass re-counts every counted sentence in a delta, every
round. This document's §2.1 says "four consumers" and §8 names "two terminals" — those are
counted sentences.

## 6. Environment — the runner changed and nothing announces it

- `PYTHONPATH=. pytest -m 'not e2e'` from `app/` runs **six xdist workers**,
  `--dist loadfile`, from `app/pytest.ini`'s `addopts`. `PYTHONPATH=.` is still required.
- **Baseline: 21 failed / 2576 passed**, collection 2597, ~51 s (the `-n 0` serial
  comparator: 21 / 2575 / 1 skipped, ~132 s).
- **Redis must be reachable** at `settings.redis_url` or the number is 23 failed / 2 errors.
- Every pytest process builds its own database from `beyo_test_main_template` and drops it
  at session end, behind a fail-closed guard. Suite residue no longer reaches the
  development database. `app_test` on port 5432 is dead.
- **Two pytest runs in the same checkout collide** — both default to slot `main` and
  workers `gw0…gw5`, so the second run's startup drops the first's databases mid-flight.
  **Never dispatch two sessions that both run the suite.**
- `--pdb` does not work under xdist, `-x` stops differently than you expect, output
  interleaves.
- **Two named tests are intermittent and are NOT members of the 21; a third,
  unrecoverable, IS.** So the set can shrink as well as grow. **A single run is not
  evidence — repeat and ID-diff.** Full node IDs are in the archived live-clock master
  plan §6 and in the frontend handoff §7.

## 7. Hazards this lineage has already paid for

Each cost a real round. They are not hypothetical.

- **Reviewer model: Opus 5, never Sonnet as the only reviewer.** Measured head-to-head on
  an identical tree: Sonnet approved a phase carrying an inert safety switch and a silent
  `DROP DATABASE`, and affirmed coverage that did not exist by trusting the implementer's
  ledger.
- **Never rewrite a published handoff.** An in-place edit cost the frontend team four days
  and a feature built on a refusal that no longer existed. Corrections ship as a **new
  dated document** naming what they supersede. The rule holds even when the fix looks free.
- **A ledger entry is a claim, not evidence.** Diff a ledger against the criterion's own
  text row by row. And when one obligation spans **two artifacts** (a document and
  tool-recorded state), it gets **one ledger row per artifact** — a single row spanning both
  reports on whichever was easier to satisfy. Earned four days ago.
- **A criterion that compresses an authority's sentence quotes its operative words.** A
  criterion paraphrased *"is not named to the client"* into *"not named as a cause"*; the
  deliverable satisfied the paraphrase and violated the authority, and every actor was
  correct against the artifact in front of them. A paraphrase in a criterion is a second
  source of truth with no changelog.
- **A prompt's convenience claims become the round's evidence.** If you hand a session a
  sentence, either derive it or label it plainly as unverified.
- **Never `git add -A`.** Commit explicit paths; it destroys the per-round checkpoint
  boundary that makes "nothing changed outside the perimeter" checkable later.
- **Review earlier than feels necessary.** The last documentation-only phase ran two
  internal rounds before its first external review, and that review immediately found two
  things both had missed — in prose everyone was confident about.
- **Over-evidence is a defect, symmetrically.** Re-running a command whose tree identity
  matches yours, with no variation and no pre-run authorization line, is a finding against
  the session. Spend verification on a site, condition or mutant shape the record never
  tried.

## 8. How the owner works

They answer decision cards directly and delegate explicitly in writing ("I trust it") when
they want an agent to hold authority normally reserved to them — and you **quote their
words** in the prompt that carries the authority. They want plain language, not artifact
prose. They will tell you when a recommendation is wrong and why — **treat that as decision,
not discussion, and implement the full request.** Graph adjudication is **always** theirs:
never promote, reject or edit a review item without their written say-so.

## 9. What is not yours

- **`archGraph_mapping_mantainance`** (still live in `under_construction/implementation/`)
  is a standing register of graph tooling findings, **one still open**. Read its `open/`
  file before any `archgraph_repair_anchors` call — one operation per call, batches fail —
  and before trusting a `conflicting-canonical-relationship` diagnostic. Do not archive it.
- The archived pipelines are **closed**. Read them for authority; do not reopen them.
- **The frontend handoff delivery** for live-clock is the owner's, not an agent's.

## 10. Your first move

1. Read §3's list, §2A first.
2. **Re-ground what §2A only sampled**, or scope that explicitly into the gate prompt —
   and say which you chose, in writing.
3. **Seal your calibration hypotheses** (§5) *before* authoring anything.
4. Author the mechanism-inventory prompt into `prompts/reviewer/`, with the charter's
   frontmatter, an explicit evidence budget, and §2A's signature drift as a named depth
   target — stated as a question, never as a conclusion.
5. Create `master_plan.md` only after the gate passes; the planner starts on `PASS` and
   nothing else.

Write your own orientation for whoever comes next, dated, in this folder. Do not edit this
one.
