---
plan: plan_4
role: reviewer (plan-projection doctrine)
round: 0
date: 2026-08-23
model: Opus 5
---

# Session prompt — plan-projection, phase 4 of `narrow_typical_work_times`

## Role

You are the **projectionist** for phase 4. You do **not** implement and you do **not** review
an implementation — there is none. You run the plan **forward against the real code** and
answer one question per row:

> **Could an implementer execute this exactly as written, and would the result be
> decidable?**

A row that cannot be executed, or whose named mutation would not catch what its criterion
exists to catch, is a **plan defect found before it costs a round**. That is the entire value
of this gate.

- Repo: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`,
  branch `main`. **Never push. Never `git add -A`.** You **do not edit production code, tests
  or goldens.** You may run probes and must revert them.
- Project folder:
  `docs/architecture/under_construction/implementation/narrow_typical_work_times/`
  (below `<project>/`).

Doctrine first, by absolute path — it wins over this prompt wherever they differ:

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/plan-projection.md`

**Do not read `prompts/coordinator/`.**

## Gate check (stop-and-report if any fails)

1. `master_plan.md` §4: phases 1–3 **`APPROVED`**; phase 4 **`PROJECTING`**, and
   `plans/plan_4.md` header reads **`state: PROJECTING`**. The two must **agree** — they
   disagreed once in phase 3 and the next session's gate is what reads the header.
   *(`PROJECTING` was added to §3's state machine in the same commit that dispatched you; the
   machine previously jumped `NOT_STARTED → PROJECTED` with no in-flight state, which is why
   it is worth naming here.)*
2. `git merge-base --is-ancestor 353a8c9 HEAD` succeeds. **Do not pin `HEAD` to a SHA.**
3. `git status` shows no modified tracked file under `app/`. Untracked
   `?? .archgraph/contexts/` is expected, and the owner may have
   `.archgraph/agent-operating-policy.md` modified — **that is the owner's live edit; leave
   it alone and do not report it as a finding.**

## Read first

`plans/plan_4.md` **in full** — it carries its own Read-first list (§2), and that list is part
of your subject matter: **a source it fails to name is itself a finding.** Then `master_plan.md`
§§4, 6, 7, **9 in full**, 10.

**§9 is ~34 rules and every one was paid for by a round.** Four of them have now fired **twice
or more** in this project and are the highest-yield lenses you have:

- **A count in a plan sentence is a checklist**, and one that counts to nothing is worse than
  no count.
- **A named mutation's stated bite set is a claim, and it decays** — verify it would bite.
- **A line number handed to a session is a claim with a shelf life.**
- **A fixture that satisfies two independent sufficient causes cannot prove either.**

And two earned last round, which apply directly to a phase that publishes new keys:

- **A key-set criterion must serialize a *service-produced* object**, not a hand-built one —
  otherwise it sees only unconditional leaks.
- **Name the mutation at the *definition* as well as the call site when a helper fans out.**

## What phase 4 is

The phase where **the engine turns on**. Both division consumers derive a spec, call the
statement with specs, build `SectionTypicalEvidence`, reconcile through `uniform_basis_v1`,
and feed **the same `SelectedTypical`s** to display and to weights.
`divide_production_budget`'s third parameter becomes `Mapping[str, SelectedTypical]`,
`DivisionStep.typical_worker_seconds` and both fallback reads are removed, `ALLOCATION_METHOD`
becomes v2, two goldens regenerate **by key addition only**, and §7.2/§7.3's new keys ship.

**Its projection gate is MANDATORY** for a recorded reason: the neighbouring pipeline calls a
"make it consistent" change here **"the most expensive mistake available in this feature"**,
and records that no guard against it existed anywhere in the repository until its own phase 2
round 6. C1 is that guard.

## Method — measure, do not read

**Every claim in the plan is a hypothesis until you check it at source.** The three prior
projections in this project each found that roughly a third of the test evidence was not
executable as written, and each found citations that had drifted. Read the code, run probes,
count things yourself.

**For every named mutation, decide — and where cheap, measure — whether it would bite:**
can it be *applied* at all (is the target frozen, generated, or forbidden by a shipped
contract?); does it reach a fixture row that moves; and is the red it produces **the red the
criterion claims**, rather than a crash, a `KeyError`, or a collateral failure elsewhere?

**Probe budget.** You may apply a mutation, run the narrowest scope that would show its bite,
and **revert immediately** — checksum the file before and after. **Never `-k`; whole files.**
Deterministic invocation:
`BEYO_TEST_SLOT=main PYTHONPATH=. python3 -m pytest <path> -n 0 -p no:randomly`.
`redis-cli ping` → `PONG` first. **Never run two suite sessions concurrently in this checkout.**
**No L4 is expected** — this is a projection, and nothing has been implemented.

⚠ **After applying a mutation, assert it landed inside the symbol you meant.** The coordinator
was caught by this at the phase-3 gate: `serializers.py` has four `payload = {`, the edit hit
the wrong function, and the suite came back green — which reads exactly like a refutation and
was in fact a mutation that never applied.

## Areas worth your attention — named as areas, not conclusions

None of these is a finding yet. Several may be correct. **Judge them yourself, at source.**

1. **Every line-number citation in plan 4.** §5 and §6 cite roughly a dozen. Re-derive each
   by locating the symbol now. **This project has watched citations drift three times**, and
   phase 3's projection found three drifted in one plan.
2. **The `fake_status` widening surface (§2, plan-3 projection L15).** L15 names one fake at
   `test_price_scenario_query.py:559-560`. **Is that the whole surface?** The first phase to
   read `budget_status.typical_filter_spec` gets an `AttributeError` from anything narrower.
3. **`ALLOCATION_METHOD`'s publish sites, and whether C2's mutation can see all of them.**
   Find every site that puts an allocation method on a payload, and check what C2's mutation
   (revert the constant) does and does not reach.
4. **C12's "review half, not automatable and stated as such".** Task 0 requires every
   criterion row to be transcribed into an executable case. Is that half genuinely
   un-automatable, or is it automatable and simply unwritten?
5. **C10's 50-task fixture.** Cost it. Is it constructible, and are the exact literals rows
   (b)/(c) demand stable under it?
6. **C1's fixture preconditions.** Rows (a)/(b) assert that allowances are identical across
   two `ctx.now` values. **What must be true of the fixture for that equality to mean
   anything**, and does anything assert it?
7. **C9(a)'s baseline.** It compares against "the pre-refactor payload for the same fixture".
   Where does that baseline come from, and when is it captured?
8. **C0's three escapes.** They were measured on the approved phase-1 tree and the plan says
   *do not re-measure them, close them*. **Are they still reproducible on today's tree?** An
   escape that has since been closed by another phase would make its row unfallible.

## The two shapes that have cost this project the most

State explicitly, for each criterion, whether it is exposed to either:

- **A row that cannot fail** — the assertion is green under the very defect it names. Phase 3's
  best finding was of this shape: a key-set row that was blind to a *value-gated* leak because
  its fixture carried no value.
- **A row that fails for the wrong reason** — two independent sufficient causes, so the
  mutation removes one and the row stays red (or green) regardless.

## Owner cards

Where a question is genuinely the **owner's** — a product-semantics choice, a contract the
intention does not settle, an authorization — raise it as an **owner card** with a
recommendation, and do not decide it yourself. Where the plan is merely underspecified and the
answer is derivable from the code or the intention, **derive it and say so**; do not
manufacture a card to avoid a judgment.

## Output

Verdict: **`AMENDMENTS_REQUIRED`** or **`PROJECTION_CLEAN`**.

A ledger, one row per finding, each classified **blocking** / **should-fix** / **note**, each
naming: the plan location, what is wrong, **the evidence you gathered at source**, and the
**concrete correction** — the literal, the count, the corrected citation, the replacement
mutation. A correction an implementer still has to guess at has not been made.

Then, separately: **reality checks** (claims you verified that turned out **correct** — record
them, so a later round does not re-verify them) and **refutations** (things you set out to
show were broken and were not, with the probe).

Handoff at `<project>/handoffs/reviewer/20260823_plan4_projection_handoff.md`, frontmatter
`plan: plan_4`, `role: reviewer`, `round: 0`, `date`, `actor`, `verdict`. Body: an
owner-readable opening (3–5 sentences, plain words); the ledger; reality checks; refutations;
owner cards; the tree you projected against (`git log --oneline -1`); and a mutation-probe
declaration with before/after checksums for every file you touched.

Final chat message is the charter's **owner layer**: what you did → what it means → what
happens next → what needs the owner; one pointer line naming the handoff.
