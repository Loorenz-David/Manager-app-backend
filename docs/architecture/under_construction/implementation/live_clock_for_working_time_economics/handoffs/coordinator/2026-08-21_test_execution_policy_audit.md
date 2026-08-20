---
plan: pipeline-governance (cross-phase)
role: coordinator
round: audit
date: 2026-08-21
state: OWNER_DECISIONS_PENDING
actor: coordinator (Claude)
---

# Test-execution policy audit — root cause, phase 2 case study, proposed policy

Owner directive 2026-08-21: the pipeline over-purchases full-suite evidence in the
inner implement/fix/review loop. Investigate before changing anything; preserve
adversarial guarantees; optimize for smallest sufficient evidence.

**Write perimeter of this session:** this file only. No skill, prompt, plan, memory,
test, or production file was modified.

## ⚠ OWNER DECISIONS REQUIRED (3)

**Card 1 — Question:** Does every implement/fix cycle keep exactly ONE full-suite
clean run at its close (the checkpoint stamp), with all other inner-loop runs scoped
to their hypothesis?
**Story:** Codex finishes a fix at 14:00. Under current rules it then runs ~2 minutes
of pytest after every mutation — fourteen times — and hands off near 15:00. Under the
proposal it runs each mutation against the file or domain the criterion names
(seconds each), then one final 2-minute stamp that fixes the baseline the reviewer
and every ID-diff cites.
**Branches:** *Yes* — one authoritative stamp per cycle, inner loop drops to seconds.
*No, stamp only at review entry + approval* — cheaper still, but mid-phase ID-diff
evidence loses its anchor tree.
**Recommendation:** Yes — the stamp is what makes ID-set evidence citable across
agents; one per cycle is its minimum viable frequency.
**On silence:** current per-mutation whole-suite practice stands.
**Trace:** charter Review protocol (3); executor Closing 1/1½; master plan §6.

**Card 2 — Question:** May the coordinator retire full re-execution of implementer/
reviewer evidence in favor of tree-bound reuse plus verification-by-variation?
**Story:** A ledger says "mutation M added exactly ID X at tree `b099423`". Today I
re-run the identical command and wait 2 minutes to learn the same thing. Under the
proposal I check the tree matches, then spend those 2 minutes running M at a site or
condition the ledger never tried — which is how the TZ=UTC hole, the E-A-site gap,
and the 21-vs-2 diagnosis were actually caught. Reproduction of identical commands
caught only tree drift, which the tree stamp now catches for free.
**Branches:** *Yes* — same budget, pointed at new evidence. *No* — keep full
re-execution; phase-2's ~23 coordinator minutes per phase stay.
**Recommendation:** Yes — the memory rule's own track record shows variation, not
repetition, found the defects.
**On silence:** `feedback_verify_dont_read_ledgers` stands as written.
**Trace:** that memory file; pipeline-coordinator Responsibility 1b; reviewer doctrine 1.

**Card 3 — Question:** Apply the charter + skill edits (§8 below) now, before phase
3's projection prompt is authored?
**Story:** Phase 3 (frozen blocks) and then `narrow_typical_work_times` will each run
5–7 rounds. Applied now, phase 3 becomes the first phase measured under the new
policy, with the old phase-2 numbers as the before/after comparison. Applied later,
phase 3 repeats phase 2's ~107 pytest-minutes and the comparison is lost.
**Branches:** *Now* — phase 3 is the pilot. *After phase 3* — one more phase of
current cost, zero risk of policy-transition confusion mid-project. *Never* — status
quo.
**Recommendation:** Now — the edits are additive-or-relaxing; nothing in flight
depends on the stricter form (no round is open).
**On silence:** no files change; this audit remains a report.
**Trace:** §8 file list below.

## 1. Root-cause classification

All five candidate causes exist; A, B and C dominate. Evidence per cause:

**A — explicit instruction (confirmed, four sites).**
1. `agent-skills/implementation-executor.md` Closing 1: "Full test suite + linters
   green" — required at the close of *every* implement and fix cycle.
2. `agent-skills/pipeline-charter.md` Review protocol (3): re-reviews run "full suite
   + spot-check of dependents" — every re-review round.
3. `agent-skills/plan-reviewer.md` doctrine 1: "Re-derive, never trust the log. Run
   the suite yourself." — unscoped; read as full-suite by every reviewer session.
4. Memory `feedback_verify_dont_read_ledgers.md`: "re-apply every named mutation
   yourself, whole-suite… A `-k` or single-file run is not an observation" — binds
   the coordinator to N whole-suite runs per consumption.

**B — emergent interaction (confirmed).** The evidence *format* forces the scope:
once a criterion's admissible evidence is "both-direction diff of the failing-ID set
against the enumerated 26-ID baseline", only a whole-suite run can produce a
comparable set. Three interacting rules compound it: the flaky-test rule ("a single
run is not evidence — repeat") doubles anomalous runs; the external cap-commit stream
required re-measuring the baseline each round; and checkpoint commits made every
round boundary a fresh tree needing a fresh stamp.

**C — prompt generation (confirmed, coordinator-authored).** Every phase-2 implement/
fix prompt I authored carries "Full suite green except the enumerated baseline; count
and ID-set diff recorded" as closing requirement 1, and "run the WHOLE suite, never
`-k`" in the mutation protocol. The fix r2 prompt ordered a re-sweep of **all
fourteen** named mutations whole-suite — including six already measured twice (by the
r1 implementer and by me at consumption). Master plan §6's closing absolute — "every
mutation run stays whole-suite" — is mine, dated 2026-08-20.

**D — agent discretion (partial, minor).** Codex ran full suites mid-implementation
beyond what prompts required (observed in its session logs during fix r2); prompts
only required closing runs plus per-mutation observations. Unquantifiable post-hoc,
but bounded: the required runs alone account for nearly all pytest wall time.

**E — necessary execution (partial).** Per-cycle clean stamps, the approval-gate
baseline, baseline re-enumeration after the foreign cap commits, and
repository-wide-absence hypotheses (r5's §4.3A path 3: "no guard anywhere in the
repository") were genuinely full-suite questions. ~15 of 51 runs.

**Instruction genealogy (important):** the whole-suite mandate is *young and mostly
project-level*. `feedback_named_mutation_both_sides` (2026-08-19, prior pipeline)
required only the **whole test file**. `feedback_verify_dont_read_ledgers`
(2026-08-20) escalated it to whole-suite; master plan §6 hardened it the same day.
The charter itself never says "whole-suite per mutation" — its full-suite
requirements are per-cycle-close and per-re-review. The most expensive sentence in
the pipeline is one day old and coordinator-authored.

## 2. Instruction trace (exact lines)

| File | Instruction | Effect |
|---|---|---|
| `implementation-executor.md` Closing 1 | "Full test suite + linters green" | 1 full run per cycle close (legitimate stamp) |
| `implementation-executor.md` Closing 1½ | "Run every mutation the plan names" | N runs per cycle; scope unspecified → inherited from prompts as whole-suite |
| `pipeline-charter.md` Review protocol (3) | "full suite + spot-check of dependents" | 1 full run per re-review |
| `plan-reviewer.md` doctrine 1 | "Run the suite yourself" | reviewer duplicates the implementer's stamp on an identical tree |
| `feedback_verify_dont_read_ledgers.md` | "whole-suite… a `-k` or single-file run is not an observation" | coordinator re-runs everything; 11 runs in phase 2 |
| master plan §6 | "**The one thing that does not get narrowed: every mutation run stays whole-suite.**" | binds all future rounds, all agents |
| every phase-2 implement/fix prompt, closing req. 1 | "Full suite green except the enumerated baseline; count and ID-set diff recorded" | per-cycle full run + per-mutation full runs |

No CLAUDE.md exists at repo or app level; `implementation-planner.md`,
`plan-projection.md`, `intention-shaper.md`, `mechanism-inventory.md` carry no suite
instructions. The behavior comes from exactly the seven rows above.

## 3. Phase-2 test-run audit (measured from ledgers; ~2m06–2m11 per run)

| Round / actor | Whole-suite runs | Composition | Necessary at full scope? |
|---|---|---|---|
| implement r1 (Codex) | 7 | 1 clean + 6 mutants | clean: yes. 6 mutants: **no** — each added exactly one named ID; hypothesis was L1 |
| fix r2 (Codex, ~1 h session) | 16 | 2 clean + 14 mutants | clean ×1: yes. 14 mutants: **6 were third measurements** of already-double-measured rows; most hypotheses L1/L2. The sweep did earn one L4 result: C6's `latest_state_record` mutant reddened two tests *outside* the phase file (cross-file coupling) |
| review r3 (Opus) | 4 (+1 single-file) | 1 clean + 3 mutants | clean: yes (tree differed — cap commits landed). Mutants: L2 would have sufficed |
| fix r4 (Codex) | 4 | 1 clean + 3 mutants | clean: yes. S3/N4's mutant reddened 9 IDs across the typicals module — L2 (typicals domain) would have shown all 9 |
| re-review r5 (Opus) | 6 | 1 clean + M-A…M-E | clean: yes. M-A/M-D/M-E asserted **repository-wide absence** (∅/∅) — genuinely L4. M-B/M-C: L1 |
| fix r6 (Codex) | 3 | 1 clean + 2 mutants | clean: yes (approval candidate). B1's "does any test anywhere guard path 3": genuinely L4. S2: L1 |
| coordinator (all consumptions) | 11 | clean re-runs + mutation re-applications | gate baselines (~2) yes; the rest duplicated identical commands on identical trees, except the *variations* (E-A site, non-crashing B1 shape), which were the valuable part |
| **Total** | **51** | | **~15 necessary at L4; ~36 avoidable** |

**Wall-clock:** 51 × ~2m08 ≈ **109 minutes of pure pytest**. Avoidable portion: ~36
runs ≈ **75–77 minutes**, replaceable by L1/L2 runs of 5–60 s each (~10 min total).
Duplicate-evidence share inside that: six mutations measured **three times each**
(r1 implementer → coordinator consumption → fix r2 sweep) ≈ 25 minutes; coordinator
clean re-runs on already-stamped identical trees ≈ 10–12 minutes.

**Why fix r2 took "almost an hour":** ~34 min was pytest (16 runs); the rest was
Codex reasoning between runs. Test execution was the majority cost of the session,
and the sweep's marginal information over the existing double measurements was one
cross-file coupling discovery.

**Where the day went (phase 2 total, measurement vs inference):** measured — 109 min
pytest across agents. Inferred from session durations — roughly comparable time in
agent reasoning, and prompt/handoff authoring+consumption overhead on top. Test
execution was the largest single measurable line item, and the only one that scales
per-mutation rather than per-round.

## 4. Current test-selection behavior

Every observation-bearing run is whole-suite by mandate; `-k`/single-file runs are
declared "not an observation"; evidence is admissible only as a both-direction diff
against the enumerated 26-ID baseline; each of implementer, reviewer, and coordinator
independently reproduces the same evidence; evidence carries a tree SHA only
incidentally (checkpoint commits), not as a binding.

## 5. Proposed test-evidence hierarchy (repo-specific)

- **L1 — targeted** (~5–20 s): the named test ID or the phase test file
  (`test_phase2_live_surfaces.py`-style). Default for: does this named test redden
  under this named mutation; does my change pass its own criteria rows.
- **L2 — domain** (~30–60 s): the affected domain trees, derived from the mutation
  site's import radius, not directory aesthetics. For item-economics work:
  `tests/**/item_economics/` + the typicals module tests + the coupled files the
  criterion names. Default for: cycle-internal completion checks; mutations whose
  criteria name cross-file bite sets.
- **L3 — integration** (~2–5 min of selected trees): `tests/integration/services/`
  subtrees crossed by the seam. For seams crossing E-P/E-B/E-A service boundaries.
- **L4 — full suite** (`PYTHONPATH=. pytest -m 'not e2e'`, ~2m10 serial): reserved
  for (a) the one clean stamp closing each implement/fix cycle; (b) review entry when
  the reviewer's tree differs from the last stamp; (c) the approval gate; (d)
  hypotheses that are repository-wide by construction — "no test anywhere guards X"
  (∅/∅ claims), coupling discovery, removed-ID surveillance; (e) baseline
  re-enumeration after runner/topology changes or foreign commit streams.

## 6. Escalation rules

Scope is chosen by the hypothesis, stated in the ledger row: every evidence row
records **hypothesis, scope, command, tree**. Escalate when the current decision
needs wider evidence: an L1 miss (named test stays green) is already a finding — no
escalation needed to detect it; an L2 run showing *unexpected* reds escalates to L4
to map the coupling; an absence claim ("nothing anywhere…") starts at L4. Choosing L4
inside an inner loop requires one line: "narrower evidence insufficient because …".
Both-direction ID diffs remain mandatory *at the chosen scope*; the enumerated 26-ID
baseline remains the comparator for every L4 run.

## 7. Cross-agent evidence reuse

Bind evidence to the tree: every ledger row and clean run records the checkpoint
commit SHA and asserts a clean `git status --porcelain` (dirty trees: SHA + sha256 of
`git diff` as the fingerprint). A consumer whose tree matches may **cite** the row
instead of re-running it. Re-execution is reserved for: tree mismatch, gate stamps,
and **variation** — a different site, condition (TZ), or mutant shape than the row
used. Earned example for the binding: fix r2 row 4's 7-vs-1 discrepancy happened
precisely because a foreign cap commit landed mid-sweep and the rows weren't
tree-stamped; the stamp converts that class from "re-run everything" to "compare two
SHAs". The checkpoint-commit discipline already provides the identity for free.

Reviewer budget redirects from reproduction to: semantics inspection, missing cases,
adversarial fixtures, collision surfaces, and challenging the implementer's *scope
selection* ("was L2 sufficient for this row?"). Coordinator budget likewise:
perimeter-vs-git check (cheap, kept), spot-verification **by variation** of a sample
of rows, full reproduction only at gates or on tree mismatch.

## 8. Skill/document changes required (exact, smallest durable form)

1. **`agent-skills/pipeline-charter.md`** — add section "Test-evidence scope and
   reuse" carrying §§5–7 above (levels, hypothesis-scoped selection, escalation
   line, tree-bound reuse); amend Review protocol (3) from "full suite" to "L4 stamp
   per the test-evidence section (tree-mismatch or gate)". Consumers: all seven
   skills, all future pipelines. This is the policy's home — per the user directive
   and the charter's own "skills stay thin and cite this file".
2. **`agent-skills/implementation-executor.md`** — Closing 1 stays (it *is* the
   per-cycle L4 stamp, Card 1); Closing 1½ gains "at the scope the criterion's
   hypothesis requires (charter test-evidence section); the ledger row records
   hypothesis, scope, and tree".
3. **`agent-skills/plan-reviewer.md`** — doctrine 1 reframed: "Re-derive, never
   trust the log — by variation and inspection, not by reproducing identical
   commands on identical trees; run the suite yourself when your tree differs from
   the last stamp or a cited row lacks a tree binding."
4. **`agent-skills/pipeline-coordinator.md`** — Responsibility 1b consumption:
   tree-check first, sample-verify by variation, full reproduction at gates only.
5. **Memory `feedback_verify_dont_read_ledgers.md`** — rewrite the "whole-suite"
   clause to the hypothesis-scoped + tree-bound form; **keep**: both-direction
   diffs, capture-IDs-before-repeating, TZ dual-runs, verify-claims-in-prose. The
   file's track record is variation catching defects — the rewrite makes that the
   instruction.
6. **Master plan §6** — strike "every mutation run stays whole-suite"; replace with
   a pointer to the charter section plus the two genuinely-L4 signals it was
   protecting (∅ absence claims, cross-file coupling), which move into L4's
   trigger list.
7. **Prompt templates** (coordinator practice, no file): closing requirement 1
   becomes "one L4 stamp, tree recorded"; mutation protocol paragraph becomes the
   hypothesis/scope/tree form.

## 9. Prompt/template changes

Covered by §8.7 — the prompts are generated fresh each round; once the charter
section exists, the coordinator skeleton cites it instead of restating whole-suite
language. Phase 3's projection prompt (next artifact due) would be the first
authored under the new policy.

## 10. Correctness guarantees preserved

Named mutations still run before submitting (executor 1½); both sides still computed
(`feedback_named_mutation_both_sides` unchanged — it already specified file scope);
both-direction ID diffs remain at every scope; ∅-absence and coupling hypotheses
remain full-suite *by definition* (they're L4 triggers, not casualties); the
approval gate keeps the authoritative full suite + enumerated ID set + published
baseline; checkpoint discipline unchanged; flaky-test rules (repeat, capture IDs
first) unchanged at L4; adversarial review is redirected, not reduced — same budget,
pointed at variation instead of reproduction. Nothing is deleted, skipped, xfailed,
or weakened in the test suite itself.

## 11. Expected impact

Phase-2 counterfactual under the policy: 51 L4 runs → ~15 L4 + ~36 L1/L2 runs;
~109 min pytest → ~40–45 min; the triple-measurement class disappears entirely.
Inner-loop latency per mutation: 2m10 → 5–60 s, which also shrinks agent reasoning
stalls between runs (fix r2's hour becomes ~25–30 min). Per remaining phase (3 and
4) and per future pipeline round structure: roughly **half the wall-clock**, before
xdist.

## 12. Interaction with per-worker DB + xdist

Orthogonal and both wanted, exactly as master plan §6 records: selection reduces how
many tests run; xdist reduces the cost of the runs that remain L4 (the stamps and
gates — which after this policy are the *only* ~2-minute runs left). Isolation
correctness stays prioritized over speed; the baseline failure-ID set is
re-enumerated under the new runner before any mutation evidence is trusted on it.
Neither change starts mid-round.

## 13. Owner decisions — see cards at top.

## 14. Recommended permanent policy (for the charter section)

"Run the smallest test surface that answers the hypothesis of the decision being
made, and record hypothesis, scope, and tree with the result. Escalate scope when
the dependency radius, an unexpected result, or an absence claim requires it —
absence claims and coupling discovery are full-suite by construction. Reserve
full-suite execution for the per-cycle stamp, review entry on a changed tree, the
approval gate, and baseline re-enumeration. Evidence bound to an unchanged tree is
citable across agents; independent verification spends its budget on variation —
new sites, conditions, and shapes — not on reproducing identical commands."
