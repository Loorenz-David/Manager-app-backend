---
plan: 4
role: coordinator
round: 0
date: 2026-08-22
project: live_clock_for_working_time_economics
---

# Orientation — incoming coordinator, `live_clock_for_working_time_economics` phase 4

Written by the outgoing coordinator at the owner's request. You have **no conversation history
and do not need any** — everything below is either stated here or cited by path. Read this once,
then read §3's list.

Repo at writing: branch `feat/live-clock-phase4`, HEAD `63c8770`, worktree clean.

## 1. Your role

You are the **pipeline coordinator**. You author prompts into `prompts/<role>/`; the owner passes
them to implementer (Codex) or reviewer (Opus 5) sessions; you consume the handoffs those sessions
deposit in `handoffs/<role>/` **adversarially** — verifying claims against git and the tree rather
than believing them, and spending verification on *variation* rather than re-running what a
tree-matched record already proves.

Doctrine, in reading order, by absolute path:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/pipeline-coordinator.md`

**The charter gained four amendments on 2026-08-22**, promoted from the project that just closed:
rule 12 (a named mutation must reach every sub-check), rule 13 (a criterion asserts its contract,
not its literal), rule 14 (a fix round that does not implement a quoted correction says which and
why), and the missing half of the closing-stamp clause — *the stamp is defined by the tree, not the
count; re-taking an invalidated stamp is not over-budget.* Each cost a real round.

**The owner is not a reviewer.** Charter's "owner layer" governs every message you send them: what
you did → what it means in plain words → what happens next → what needs you. No section numbers, no
`file:line`, no finding IDs. Decision cards are relayed **verbatim**; re-compressing one into a
tidy table is how the story dies and the human rubber-stamps.

## 2. Gate check — confirm before doing anything

- `plans/plan_4.md` frontmatter reads `state: NOT_STARTED`.
- `master_plan.md` §6 contains a block headed **"⛔ THE GATE IS SATISFIED — 2026-08-22"**. If it
  does not, you are looking at a tree older than this prompt; stop.
- `git status --porcelain` empty.
- Architecture graph: **0 pending, 0 diagnostics** (`archgraph_status`).

*(Gate checks in this repo are written against **diffs**, never against `HEAD` equalling a SHA.
That rule was earned five times, twice by prompts the outgoing coordinator wrote and then
invalidated by the very commit that dispatched them. Write `git diff <sha> HEAD -- app/` is empty,
not `HEAD == <sha>`.)*

## 3. Read order

1. **`master_plan.md`** — the hub. §3's tracker is the **only** authority on state. §6 is the
   environment authority; **its first block is new and supersedes both baselines recorded below
   it.** §7 tracks the frontend obligation.
2. **`plans/plan_4.md`** — your phase. Six §7 closeout obligations, a five-node graph delta, and
   **C6** (an owner-adjudication item carried from phase 1's N6) and **C8** (below).
3. **`planning/intention.md`** — semantic authority. Nothing downstream patches it; gaps route
   *up* to it.
4. **`ORIENTATION_for_new_coordinator_20260820.md`** at the project root — **history, not
   instructions.** It carries its own superseded banner. Still binding inside it: §4 (the shipped
   promise to the frontend), §5 (load-bearing code facts), §6 (standing rules), §8 (how the owner
   works), §9 (what is not yours). Its baseline and its §2 status table are stale twice over —
   §6 of the master plan is the live number.
5. **`archive/plan_2/`** and **`archive/plan_3/`** — closed rounds, if you need provenance for a
   decision. Do not read them speculatively; they are large.

## 4. What phase 4 is

**Documentation only.** No mechanism, no production code. Its projection gate is **WAIVED** on
record (charter allows this for documentation-only phases; the waiver is in `master_plan.md` §3's
phase-4 row). **It still takes a full review round** — that is deliberate, not an oversight.

The work: a closeout handoff discharging six obligations recorded in §7, headline being **retirement
of the frontend's interim verdict-suppression flag**; a five-node architecture-graph delta; and:

- **C8** — the OD-10 correction to a **published** frontend handoff. It ships as a **new dated
  document**, never as an edit. This project's scar: an in-place edit of a published handoff cost
  the frontend team four days and a feature built on a refusal that no longer existed. That rule is
  absolute here.

**Its closeout publishes the baseline `narrow_typical_work_times` D23 consumes.** That baseline must
be stated *with its runner* — six workers, `--dist loadfile`, Redis reachable. A bare number is not
acceptable output.

## 5. The test runner changed underneath this project, silently

The `test_isolation_and_xdist` project closed 2026-08-22 (merge `0aae85e`). `master_plan.md` §6's
new block has the full fold; these are the parts that will bite a session that does not read it.

- **`pytest -m 'not e2e'` now runs six xdist workers.** `app/pytest.ini`'s `addopts` carries
  `-n 6 --dist loadfile`. Nothing announces this. `PYTHONPATH=.` is still required.
- **The baseline is `21 failed / 2576 passed`, collection 2597** — 50.61 s parallel, 131.91 s under
  the `-n 0` serial comparator. **The 21 is a strict subset of the 26 this project used to cite:
  five removed, zero added**, all five fixed by the isolation work rather than by any product
  change. They are enumerated in §6's block. **No criterion of yours gains a failure; five stop
  appearing.**
- **Redis must be reachable** at `settings.redis_url` or the number is 23 with 2 errors.
- **Every pytest process gets its own database now**, dropped at session end, behind a fail-closed
  guard. Suite residue no longer reaches the development database. `app_test` on port 5432 is dead;
  ignore it.
- **`--pdb` does not work under xdist**, `-x` stops differently than you expect, and output
  interleaves.
- **Two pytest runs in the same checkout collide** — both default to slot `main` and worker names
  `gw0…gw5`, so the second run's startup drops the first's databases mid-flight. `BEYO_TEST_SLOT`
  exists for *separate checkouts*, not concurrent runs in one. Never dispatch two sessions that
  both run the suite.

## 6. Carried items — verify, do not trust

- **`plans/plan_4.md` C6** — an owner-adjudication item from phase 1's N6: an archgraph evidence
  summary is immutable through both review and maintenance, so "correcting" one means
  **reject-and-re-record**, and a re-record re-enters the review queue needing a **second
  confirmation pass**. Plan for two passes on anything corrected. Graph adjudication is
  **human-owned**; you never promote, reject or edit a review item without the owner saying so in
  writing, and you quote their words in the prompt that carries the authority.
- **"3 pending `ai_inferred` graph items"** appears in phase 2's closeout notes. The graph currently
  reports **0 pending**. Something resolved them. **Confirm what, rather than assuming** — a
  carried item that quietly disappeared is exactly the shape that hides a real change.
- **N3's section-weight coverage debt** — recorded in `plans/plan_4.md` notes.

## 7. Hazards this pipeline has already paid for

Each cost a round somewhere. They are not hypothetical.

- **Never rewrite a published handoff.** Corrections to an earlier round's numbers go in *your*
  consuming record or the next round's handoff, naming what they supersede.
- **A prompt's convenience claims become the round's evidence.** The outgoing coordinator asserted
  a file "matches §6.1 character for character" without diffing it; it differed by the one prefix
  that made the documented command fail. Twice today, wording supplied in a prompt was taken as
  spec rather than as a reading — once dropping a safety clause from an architecture record. **If
  you hand a session a sentence, either derive it or label it plainly as unverified.**
- **Never `git add -A` while another session is in flight.** It sweeps their half-finished work into
  your commit under your subject line, and the per-round checkpoint boundary — which is what makes
  "nothing changed outside the perimeter" and "every mutation probe was reverted" checkable later —
  is destroyed. Commit explicit paths.
- **Reviewer model: Opus 5, not Sonnet.** Measured head-to-head on an identical tree: Sonnet
  approved a phase carrying an inert safety switch and a silent `DROP DATABASE`, and affirmed
  coverage that did not exist by trusting the implementer's ledger. Sonnet is a capable *second*
  reviewer and an unsafe *only* one.
- **A ledger entry is a claim, not evidence.** When a criterion enumerates per-row expected
  outcomes, diff the implementer's ledger against that enumeration **row by row**. A row reading
  "green, as expected" was read three times before anyone checked it against the criterion's own
  text saying it must be red.
- **Review earlier than feels necessary.** The phase that just closed ran four internal rounds
  before its first external review, and that review immediately found what all four had missed.

## 8. How the owner works

They answer decision cards directly and delegate explicitly in writing ("I trust it") when they
want an agent to hold authority normally reserved to them. They want plain language, not artifact
prose. They will tell you when a recommendation is wrong and why — **treat that as decision, not
discussion, and implement the full request.** They keep `main` deliberately ahead of `origin/main`
(113 commits as of writing); do not push without asking.

## 9. Your first move

**Do not author the phase-4 implement prompt yet.** In order:

1. Run §2's gate check and read §3's list.
2. **Reconcile §6's carried items against reality** — the vanished graph items especially.
3. Confirm `plans/plan_4.md`'s six obligations against `master_plan.md` §7's tracking, and check
   that each is still true after two phases and a runner change. An obligation discharged by
   someone else, or made moot, is a finding.
4. **Then** author the implement prompt into `prompts/implementer/`, with the charter's frontmatter
   and an explicit evidence budget. For a documentation-only phase, that budget is plausibly
   **0 L4 runs** — say so, and say what the session cites instead. Do not add verification
   exhortations beyond it; stacked urging buys repeat runs, not rigor.
5. Full review round after, per §3's phase-4 row, despite the waived projection.

Write your own orientation for whoever comes next, dated, in this folder. Do not edit this one.
