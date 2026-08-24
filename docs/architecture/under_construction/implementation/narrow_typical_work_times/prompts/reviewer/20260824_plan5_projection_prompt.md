---
plan: plan_5
role: reviewer (plan-projection doctrine)
round: 0
date: 2026-08-24
model: Opus 5
---

# Session prompt — plan-projection, phase 5 of `narrow_typical_work_times`

You are the **projectionist** for phase 5. You do not implement and there is nothing to review —
nothing has been built. You run the plan **forward against the real code** and answer one
question per row:

> **Could an implementer execute this exactly as written, and would the result be decidable?**

A row that cannot be executed, or whose named mutation would not catch what its criterion exists
to catch, is a **plan defect found before it costs a round.**

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`, branch
  `main`. **Never push. Never `git add -A`.** You **do not edit production code, tests or
  goldens.** You may run probes and must revert them.
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/` (`<project>/`).

**Doctrine first, by absolute path — it wins over this prompt wherever they differ:**
1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

**Do not read `prompts/coordinator/`.**

## Gate check — stop and report if any fails

1. `master_plan.md` §4: phases **1–4 `APPROVED`**; phase 5 **`PROJECTING`**, and
   `plans/plan_5.md`'s header reads **`state: PROJECTING`**. The two must agree.
2. `git merge-base --is-ancestor e81764b HEAD` succeeds (phase 4's approval gate is an ancestor).
   **Do not pin `HEAD` to a SHA.**
3. `git status --porcelain -- app/` is **empty**. Anything under `.archgraph/` is the owner's live
   work and is **expected whatever it contains** — do not enumerate it, diff it, or halt on it.

`redis-cli ping` → `PONG` before any suite run.

## Read first

`plans/plan_5.md` **in full, including its 2026-08-24 lint entry** — that entry tells you what was
already checked, and **what the lint explicitly cannot check**, which is where your value is.
Its §2 carries four items routed from phase 4's gate; **a source it fails to name is itself a
finding.** Then `master_plan.md` §§4, 5, 6, 7, **9**, 10.

**§9 is long and every rule was paid for by a round.** Six are live on this surface:
- **a criterion whose instrument cannot return the expected result**;
- **a fixture that satisfies two independent sufficient causes cannot prove either**;
- **a uniform fixture is an inert fixture**;
- **before citing a test as proof of a SQL predicate, check that the test issues SQL**;
- **a named mutation's stated bite set is a claim, and it decays**;
- **plant what an absence row forbids and confirm it reddens** (charter rule 15, new).

## What phase 5 is

Price-scenario becomes the fourth consumer of the shared engine: it gains an **injected clock**,
stops computing its own median, reconciles through the **same** `uniform_basis_v1` selection the
task surfaces use, and keeps `is_estimated` as a published value whose meaning must not move.
Task 0 removes the phase-1 `_median` compatibility bridge.

**Its projection gate is MANDATORY for a recorded reason:** `is_estimated` **reverses** if read
literally, and the clock change extends an APPROVED pipeline's determinism contract.

## Method — measure, do not read

**Every claim in the plan is a hypothesis until you check it at source.** The four prior
projections in this project each found that roughly a third of the test evidence was not
executable as written. Read the code, run probes, count things yourself.

**For every named mutation, decide — and where cheap, measure — whether it would bite:** can it
be applied at all; does it reach a fixture row that moves; and is the red it produces **the red
the criterion claims**, rather than a crash or a collateral failure elsewhere?

**Probe budget.** Apply a mutation, run the narrowest scope that would show its bite, and
**revert immediately** — checksum before and after. **Never `-k`; whole files.** Deterministic:
`BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest <path> -n 0 -p no:randomly`.
**No L4 is expected** — nothing has been implemented.

⚠ **After applying a mutation, assert it landed inside the symbol you meant.** A probe that
lands in the wrong place returns a clean green that reads exactly like a refutation. This project
has paid for that three times, most recently a reviewer's own mis-sited probe.

## Areas worth your attention — named as areas, not conclusions

None of these is a finding. **Judge each at source.**

1. **Does each criterion's fixture actually issue the SQL it reasons about?** This surface has a
   history here, and the file's own comments discuss it. A criterion asserting what the statement
   *receives* — a clock, a spec — cannot be decided by a fixture that discards the statement.
2. **The clock.** Check what price-scenario does about time **today**, before judging any
   criterion phrased as preserving current behaviour. Then ask what a two-`ctx.now` equality row
   proves if the fixture's history sits nowhere near a window boundary.
3. **`is_estimated`.** Find every production site. Then ask, for C2's four rows, whether each
   mutation's observable is **distinguishable from the others'** — two rows keyed on the same
   quantity, flipped by two different mutations, may be one row wearing two names.
4. **C7's presence form** — "computes no median of its own, calls `apply_business_fallback`
   exactly once, asserted by reading the source and by a spy." Is a source-reading assertion a
   test? Where is the spy installed, and does the thing it spies on actually get called in that
   fixture?
5. **C7's absence sweep was corrected at the lint** and now carries a required planted-defect
   probe. **Check the correction itself** — is the narrowed root right, is the allowlist complete
   as measured today, and does the term set still prove the thing the row is named for?
6. **Task 0's `_median` bridge removal.** Locate the bridge, its importer and its use. What
   exactly must be true for the removal to be safe, and does the plan's stated check establish it?
7. **The four items routed from phase 4** in §2 — especially that C13(c)'s guard **cannot see the
   private copy phase 5 is about to write**. Does plan 5 act on that, or merely cite it?

## The two shapes that have cost this project the most

State explicitly, for each criterion, whether it is exposed to either:

- **A row that cannot fail** — green under the very defect it names. **Five instances in phase 4
  alone, each written to close the previous one, and the fifth was authored by a reviewer.** The
  prior on this class is the highest of any defect family here. Budget for it.
- **A row that fails for the wrong reason** — two independent sufficient causes, so the mutation
  removes one and the row's colour does not change.

## Owner cards

Where a question is genuinely the **owner's** — a product-semantics choice, a contract the
intention does not settle — raise it as an **owner card** with a recommendation and do not decide
it. `is_estimated` is the plausible candidate: it is a published value and its meaning is the
frontend's. Where the plan is merely underspecified and the answer is derivable, **derive it and
say so**; do not manufacture a card to avoid a judgment.

## Output

Verdict: **`AMENDMENTS_REQUIRED`** or **`PROJECTION_CLEAN`**.

A ledger, one row per finding, each classified **blocking** / **should-fix** / **note**, naming:
the plan location, what is wrong, **the evidence you gathered at source**, and the **concrete
correction** — the literal, the count, the corrected citation, the replacement mutation. *A
correction an implementer still has to guess at has not been made.*

Then, separately: **reality checks** (claims you verified as correct, so a later round does not
re-verify them) and **refutations** (things you set out to break and could not, with the probe).

**One extra section, and it is new.** This plan was **linted before you saw it** — sizing,
resolvable references, derived counts, exact expected outcomes, satisfiable absence rows.
**For each of your findings, say whether the lint should have caught it.** Rows that the lint
should have caught are gaps in the coordinator's checklist and are worth more to this project
than the finding itself.

Handoff at `<project>/handoffs/reviewer/20260824_plan5_projection_handoff.md`, frontmatter
`plan: plan_5`, `role: reviewer`, `round: 0`, `date`, `actor`, `verdict`. Body: an owner-readable
opening (3–5 sentences, plain words); the ledger; reality checks; refutations; the lint-gap
section; owner cards; the tree you projected against (`git log --oneline -1`); and a
mutation-probe declaration with before/after checksums for every file you touched.

Final chat message is the charter's **owner layer**: what you did → what it means → what happens
next → what needs the owner. One pointer line naming the handoff.
