---
plan: 4
role: review
round: 5
date: 2026-08-22
verdict: APPROVED
actor: Claude Opus 5 (independent reviewer)
---

# Phase 4 — re-review r5 handoff (delta-scoped, the phase's last gate)

## Summary

**APPROVED — 0 blocking, 0 should-fix, 3 notes.** All four of review r3's corrections are
present, faithful to the clauses they were quoted from, and — for S1 — swept as a class
rather than point-fixed. The perimeter is exactly the allowed set, the fix's declared
dirty-tree digest reproduces cryptographically on my own tree, and the two probes that
mattered most (§5 mode 2's prose after a deletion; §7's baseline block as D23 will read it)
both hold on the merits.

Phase 4's deliverable is correct and complete against C1–C9 and the semantic authorities.
The three notes are improvements to a document that is already right, not defects in it;
all three are dispositioned below and none of them should hold the gate.

## ⚠ OWNER DECISIONS REQUIRED (0)

Zero. Nothing in this round needs an owner answer. The one owner item this phase carried
(the graph-modelling call) was answered 2026-08-22 and recorded as OD-11; I did not
re-open it and raise no dispute with it.

## Write perimeter declared

Documents (three, all in this implementation folder):

- `handoffs/reviewer/2026-08-22_phase4_rereview_r5_handoff.md` (this report)
- `plans/plan_4.md` — the Review log entry below, appended; and the `state:` line moved
  `REVIEWING → APPROVED`
- `master_plan.md` — **one row, my own**, inserted above the previous top row, not over it

Tool-recorded state: **none**. No `archgraph_*` write call was made and no graph read
mutated state. **No mutation probe was applied** — every verification this round was a
read, a hash, or set arithmetic over document text — so there are no applied-and-reverted
files to declare and no database or state side effect to restore. `git status --porcelain`
was empty at entry and my only writes are the three files above.

## P1 — the verified perimeter, confirmed independently

`git status --porcelain` empty at entry. Reconstructed rather than accepted:

- `git show --stat 4e79e9d` — **exactly three files**: the frontend handoff, `plans/plan_4.md`,
  `master_plan.md`. The master row is `1 insertion`, its own row, above the previous one.
- `8bc8984` — one file, the fix's own handoff. `e6a49c6` — three files, all coordinator
  artifacts (master row, plan log, this round's prompt).
- `git diff c543640 HEAD --name-only` over the whole tree returns **five files**, every one
  of them a document inside the declared perimeter of one of those three commits.
- `git diff c543640 HEAD --name-only -- app/ .archgraph/` is **empty**. Nothing under
  `app/`, no tool-recorded state moved.

No file required attribution to any of master §7's three recognized external streams —
stream 3 is quiet across this range. **No perimeter finding.**

**The digest reproduces.** The fix handoff declares dirty-tree digest
`db0045f66f63d5abb720db9780fbe11531b9e58eda0e7777225a6bf9b81029de`;
`git diff --binary c543640 4e79e9d | shasum -a 256` on my tree returns
**exactly that value**. The content its L1 guard measured is byte-identical to what
shipped, so C7's "green before and after" is evidence about the delivered document rather
than about some intermediate state — confirmed, not accepted.

## P2 — §5 mode 2 after the deletion: reads correctly

A deletion is not a null operation on prose, so I read the mode end to end rather than
diffing it. It holds.

**The prose is intact.** Mode 2 now runs cause-sentence → rule-sentence with no dangling
referent, no orphaned connective, and no sentence whose antecedent left with the deleted
one. Nothing else in mode 2 was altered (confirmed against the r3 correction's "change
nothing else in mode 2").

**It carries intention §6A A's family correctly, event by event.** The surviving sentence
is *"Marking any record of a step inaccurate, or removing the step, can remove the step's
live contribution."*

- **E1** (mark the *open* record inaccurate) — covered by "any record".
- **E2** (mark *any closed* record inaccurate) — covered, and this is the load-bearing
  word: §6A A flags E2 as *"not named in §6"*, and the document's "any record" is what
  keeps it named. Had the fix narrowed this to "the open record" while deleting the
  adjacent sentence, E2 would have gone silent. It did not.
- **E3** (a sibling's records leave the divisor) — correctly absent: §6A A records its
  effect as other steps' figures **rising**, so it is not a decrease mode.
- **E4** (step removal) — covered by "or removing the step".
- **E5** (record deletion) — correctly absent, which is S1's whole point.
- **E6** (task deletion) — correctly absent: §6A A calls it a 404, *"not a decrease — a
  different contract"*.

**The surviving general rule genuinely covers what the deleted sentence claimed.** The
deleted sentence told the client that record deletion is not a cause to handle. What
survives — *"A drop larger than 1 second is authoritative: snap down immediately to the
served value…"* plus §5's closing *"For every mode… its smoothing baseline must snap down
to the served value rather than clamp"* — is cause-independent by construction. A client
obeying it responds correctly to a decrease from **any** cause, including one our API
cannot emit. The r3 justification was right, and the register test it invoked is the same
one that correctly kept §6A B's two-drop fact out; I did not re-open that call.

**S1 as a class, swept with different terms than the coordinator used.** The coordinator
grepped `deletion|deleted|delete`. I ran a wider net —
`eras|purg|remov|destro|discard|wipe|reset|hard delete|soft.delet|not a cause|not a shipped|capabilit`
— plus every occurrence of `record` in the document. Six hits total, all benign: mode 2's
own "removing the step" / "remove the step's live contribution" (E4, required by §5.4);
"reset the smoothing baseline" (the N2 rule); and three baseline-arithmetic uses of
"removed" about failing IDs. **No site in the document names record deletion in any
register.** Class closed by an independent instrument.

## P3 — the instability caveat against the "durable comparator" claim

Judged as `narrow_typical_work_times` D23 — the pipeline that will diff two goldens against
this block.

**No contradiction.** *"The count is context; the failing-ID set is the durable comparator"*
is a claim about which of two artifacts to diff, not a claim that the set is immutable.
The instability bullet then qualifies the set's own stability. The two sit consistently:
prefer the set, and do not trust one observation of it.

**The instruction is actionable, not merely a warning.** *"A single run is therefore not
evidence — repeat and ID-diff before concluding that the set has changed"* is a procedure a
consumer can execute, and it discriminates correctly in every case I could construct — an
extra ID that is one of the two named; an extra ID that is not; and a **missing** ID. It
also works without knowing the third test's identity, which is what makes publishing an
unrecoverable identity useful rather than decorative: repetition separates intermittent
from durable whether or not you can name the test. The phrase *"that the set has changed"*
is direction-neutral, so the rule bites on a shrink as well as a growth.

**Both named IDs transcribed exactly** against master §6, and **both exist at source**
(`test_phase4_fix_coverage.py:240`, `test_process_shopify_products_integration.py:82`).
**Neither is a member of the published 21** — verified by basename over the enumeration,
which is a stronger instrument than the full-path grep the earlier rounds used, since it
would also catch a same-named test at a different path. 0 and 0.

Two improvements, both notes: **N4** (the third test's direction) and **N5** (the two named
IDs are published as bare basenames). Neither defeats the rule above.

## P4 — the two "exactly" claims in §5, re-derived after the edit

**Three is still the right number and the right three.** Derived from the authority, not
from the document:

| § 6A C bullet | mode in the document | intention source |
|---|---|---|
| drop ≤ 1 s → rounding sense, no visible snap required | 1. Rounding sense | §3.3A A |
| drop > 1 s → authoritative, reset the smoothing baseline, do not animate | 2. Disowning | D7, §6A A E1/E2/E4 |
| drop-then-return within seconds → settlement window, render as served | 3. Settlement window | D8, §3.3A C.1 |

§6A C's remaining two bullets are not modes: *"Any decrease"* is the general rule (the
document carries it as §5's closing paragraph, correctly outside the numbered list), and
*"`share_state` is rendered as received"* is a standing rule, also carried there. Intention
§5.4 independently states *"decreases between polls in exactly **three** ways"*, and master
§7 obligation 5 says three (with its own note that this row *"originally said 'exactly two
ways'"* — so the count has been wrong here before and is worth re-deriving; it is right
now). The event family E1–E6 collapses onto exactly these three because E3 is an increase,
E6 is a 404, and E5 is not a shipped capability. **Both "exactly" claims survive the edit.**

**N2's correction is verbatim-faithful.** §5's closing rule now reads *"its **smoothing
baseline** must snap down to the served value rather than clamp"*, matching intention §5.4
round 4i (*"Client smoothing must snap its **smoothing baseline** down to the served value,
never clamp"*) and resolving the three-section reconciliation §5.4 warns about.

## Verified correct — new evidence bought this round

Every item here is a fact no prior round held, produced by a different instrument or a
different derivation path than the record used.

1. **The digest reproduces cryptographically** (above) — the fix's tree identity is proven,
   not asserted.
2. **The published 21 are all members of master §6's 26.** `comm` between the document's
   enumeration and master §6's: **zero document IDs foreign to the master set.** Nobody had
   run the containment in this direction.
3. **The five-removed enumeration reproduces by independent arithmetic.** `master26 −
   doc21` derived on my tree equals the document's published five, **exactly, both
   directions** (`diff` empty). C9's fold-time `comm` derived this against the *source*
   project's handoff; this derives it against master §6 and lands on the same five. The
   subset claim now has two independent derivations.
4. **Obligation 2 / C2 verified structurally, not textually.** Across the entire phase,
   `git diff 80b8cca HEAD --name-only -- docs/handoff/to_frontend/` returns **exactly one
   file — the new dated document**. No published handoff was edited in place, proven from
   git history rather than from the document's own statement about itself. This is the
   strongest available form of that check and closes
   [[feedback-never-rewrite-a-published-handoff]]'s concern for this phase by construction.
5. **The tree-identity claim D23 depends on most holds.** `dc76db8` exists, its subject is
   the document's quoted string character-for-character, and `git diff dc76db8 HEAD -- app/`
   is **empty** — so the document's *"a measurement taken on today's tree is comparable
   without checking anything out"* is true as of this review, not just as of the fix.
6. **The runner sentence is exact.** `app/pytest.ini` line 2:
   `addopts = -ra --strict-markers --strict-config -n 6 --dist loadfile`. Six workers,
   `loadfile`, from `addopts` — as published.
7. **All twelve provenance-appendix paths resolve on this tree** (seven implementation
   anchors, five baseline/handoff citations) — checked one by one. A cross-codebase handoff
   with a dead pointer costs the receiving team an hour; none of these is dead.
8. **C9's seven required elements are all present**: the enumerated 21 written out (counted:
   21), the runner, Redis with its 23-failed / 2-errors diagnostic, the per-process
   `beyo_test_main_template` database identity, the asserted-clean tree identity, the
   26→21 subset note with the five named, and the new **known instability** field.
9. **Arithmetic**: 21 + 2576 = 2597 = the published collection count.

Everything review r3 verified — C1, C3, C4's both amendments, the eight-row consumer list,
C8's OD-10 correction, the five graph node descriptions at source — stays passed and was not
re-spent.

## Findings

**0 blocking. 0 should-fix. 3 notes.**

### N4 (note) — the third intermittent test is published without its direction, next to a sentence about non-membership

**What.** §7's known-instability bullet names the two intermittent tests, states they *"are
not members of the 21"*, then says *"A third intermittent test's identity is
unrecoverable."* Master §7's baseline schema attaches a consequence to that third:
*"the fact that a third one's identity is unrecoverable **(so the set can shrink too)**"*.
The parenthetical is not carried, and master §6 explains why it exists: the third was
detected as *"one of the enumerated 26 baseline IDs **passed**"* — i.e. unlike the two named
ones, the third **is** a member of the published set, and it can only ever **remove** an ID,
never add one.

**Why it is a note and not a should-fix.** The document states nothing false — "are not
members of the 21" is predicated on the two named tests only, and the third sentence makes
no membership claim. Master §7's schema lists three required elements (named tests; the
unrecoverable third; the binding consequence) and the document carries all three; the
"(so the set can shrink too)" clause is a gloss on the second, not a fourth field. And the
published rule is direction-neutral — *"repeat and ID-diff before concluding that the set
has changed"* protects a reader who observes a shrink exactly as well as one who observes a
growth. The residual risk is only that the adjacency implies an additive-only reading and
so weakens a rule it does not defeat.

**Suggested correction** (one clause, whenever a baseline is next published): *"A third
intermittent test's identity is unrecoverable, and unlike the two above it was observed as
a member of the published set — so the set can shrink as well as grow."*

**Authority:** `master_plan.md` §7 published-baselines schema; `master_plan.md` §6's
⚠ THIRD-intermittent bullet. **Route:** master §7's schema wording, for the next publisher.

### N5 (note) — the two named intermittent tests are published as bare basenames in a section built to be ID-diffed

**What.** Every other test identifier in §7 — the 21, the five removed — is a full pytest
node ID (`tests/…/file.py::test_name`). The two intermittent tests are published as
`test_phase4_fix_coverage.py::…` and `test_process_shopify_products_integration.py::…`,
with the directory dropped. The section's own instruction is *"repeat and **ID-diff**"*,
which is a mechanical operation over full node IDs; a bare basename does not match one
without a lookup.

**Measured this round** (so the correction costs nothing to apply):

```text
tests/integration/services/commands/item_economics/test_phase4_fix_coverage.py::test_c3_real_concurrent_open_insert_translates_the_loser[model]
tests/integration/services/commands/shopify/test_process_shopify_products_integration.py::test_process_shopify_products_fans_out_to_all_active_workspace_shops_and_enqueues_one_task
```

**Why a note.** Inherited from master §6, which uses the same short form; a human reader
resolves it in seconds, and the identifiers are unambiguous on this tree (one match each).
**Route:** master §6's ⚠ Suite instability bullet and §7's schema — publish full node IDs
wherever a published set is meant to be diffed.

### N6 (note) — the provenance appendix's intention path is not repo-root-relative, and collides with the successor project's own file

**What.** The appendix's "Semantic authority" block cites `planning/intention.md:§…` ten
times, while every other citation in the same appendix is repo-root-relative
(`app/beyo_manager/…`, `docs/…`). `planning/intention.md` resolves only from inside this
implementation folder. The consumer named in the same document —
`narrow_typical_work_times` — has a `planning/intention.md` of its own, so the ambiguity is
live rather than theoretical.

**Why a note.** The section anchors (`§1A HC-3A`, `§5.3A`, `§6A C`) are distinctive enough
that a reader landing in the wrong document notices immediately, and the frontend audience
does not need the intention at all — the document is self-contained on every rule it
issues. **Route:** documentation hygiene, next handoff authored by this pipeline.

## Carry-forward dispositions

| Note | Disposition | Destination |
|---|---|---|
| **N4** — third intermittent test's direction unstated | Fold the clause into the baseline schema so the **next** publisher carries it; do not re-open this document. | `master_plan.md` §7 published-baselines schema (coordinator, at closeout) |
| **N5** — bare basenames for the two named intermittents | Publish full node IDs; the two are measured verbatim above. | `master_plan.md` §6 ⚠ Suite instability bullet + §7 schema (coordinator, at closeout) |
| **N6** — `planning/intention.md` not repo-root-relative | Documentation hygiene; no action owed by this phase. | Next handoff this pipeline authors |

None of the three is owed by phase 4, and none is a defect in the delivered document. They
are recorded here so they cannot evaporate at closeout.

## Evidence

**L4: 0** — as budgeted. `git diff 0aae85e HEAD -- app/` is empty and so is
`git diff dc76db8 HEAD -- app/`, so master §6's **21 failed / 2576 passed** is cited by
tree identity. Re-running it would have been a finding against this round.

**L1: 0.** I did **not** run `tests/unit/docs/`, and this is deliberate. Fix r4 measured
**59 passed** on content I have now proven byte-identical to `4e79e9d`; the two commits
since touch no file that guard reads (`docs/handoff/`, `docs/domains/item_economics/`);
and the guard's non-vacuity over this document is already measured by the coordinator's
planted-token probe (1 failed / 58 passed, reverted byte-identical). A re-run would have
been the same command on a tree-matched surface with no variation — the named
anti-pattern. I also note the coordinator's own recorded lesson from r3 on exactly this
(justifying a re-run by a directory that merely *contains* the read surface) and did not
repeat it.

**Where the budget went instead — nine facts, all new:**

| # | Hypothesis | Instrument | Tree identity | Result |
|---|---|---|---|---|
| E1 | The fix's declared dirty-tree digest describes the committed content | `git diff --binary c543640 4e79e9d \| shasum -a 256` | `HEAD e6a49c6`, porcelain empty | `db0045f66f63d5abb720db9780fbe11531b9e58eda0e7777225a6bf9b81029de` — **exact match** to the declaration |
| E2 | The perimeter is exactly the allowed set | `git show --stat` ×3 + `git diff c543640 HEAD --name-only` (whole tree, and `-- app/ .archgraph/`) | same | 5 files, all declared; `app/` + `.archgraph/` **empty** |
| E3 | S1 is closed as a class, not at one site | `grep -niE` over 11 alternative terms + every `record` occurrence | same | 6 hits, all benign; **0 sites name record deletion** |
| E4 | The published 21 are members of master §6's 26 | `comm -23 doc21 master26` | same | **∅ foreign IDs** |
| E5 | The five-removed enumeration is correct | `comm -13 doc21 master26` then `diff` vs the document's five | same | **exact match, both directions** |
| E6 | No published handoff was edited in place, across the whole phase | `git diff 80b8cca HEAD --name-only -- docs/handoff/to_frontend/` | same | **exactly one file — the new document** |
| E7 | `dc76db8`'s subject and `app/` identity are as published | `git log -1 --format=%s dc76db8`; `git diff dc76db8 HEAD --stat -- app/` | same | subject matches character-for-character; diff **empty** |
| E8 | The two named intermittents exist and are non-members | `find` + `grep -rn "def <name>"`; basename grep over the published 21 | same | both found at source; **0 and 0** membership |
| E9 | Every provenance-appendix path resolves | existence test over all 12 | same | **12/12 OK** |

Plus the runner check (`app/pytest.ini:2`) and the 21 + 2576 = 2597 arithmetic.

**Mutation-probe declaration: none applied.** No file was modified, no database row written,
no `archgraph_*` write call made, no environment variable or service touched. Every
instrument above is a read, a hash, or set arithmetic over text. Nothing to revert;
`git status --porcelain` shows only my three declared writes.

## Closeout readiness

**Nothing in master §7's seven obligations is materially undischarged.** Checked one by one
against the delivered document:

| # | Obligation | State |
|---|---|---|
| 1 | Go-live statement retiring the interim verdict-suppression flag | **Discharged** — §1, citing the 2026-08-19 §4 promise it keeps |
| 2 | New dated handoff, never an edit | **Discharged, and proven from git history** (E6): one file touched under `to_frontend/` across the whole phase |
| 3 | The 2026-08-18 "Live time" correction | **Discharged** — §3, client ticking superseded, smoothing from receipt preserved |
| 4 | The four open questions | **Discharged** — §4.1–4.4, with §§2.3A **and** 3.4A both cited, the eight-row consumer list, and HC-3A/T1 |
| 5 | Decrease semantics — three modes, §6A C's per-event rules | **Discharged** — re-derived independently this round (P4); record deletion not named, swept as a class (P2) |
| 6 | The graph delta | **Discharged** — adjudicated and closed under OD-11: 5 promoted, 0 pending, 0 stale, 0 diagnostics, revision `7241b831…`; no graph work remains |
| 7 | The published approval baseline | **Discharged** — §7 carries all seven required elements, and its subset arithmetic now has two independent derivations (E4, E5) |

Two housekeeping items for the coordinator's approval-gate commit, neither a condition of
approval: fold **N4** and **N5** into master §6/§7 so the next publisher inherits them, and
archive this phase's rows per the closeout ritual. The baseline `narrow_typical_work_times`
D23 consumes is, in my judgment, ready to publish as it stands.

## Lessons for the plans

1. **A deletion needs a family re-derivation, not a diff.** The r3 correction was "delete
   one sentence, change nothing else", and the fix did exactly that — but what made mode 2
   still *correct* afterwards was a word in the surviving sentence ("any record") carrying
   E2, an event intention §6A A explicitly flags as missing from §6. A future
   delete-one-sentence correction in a document that enumerates a family should say which
   family members the surviving text must still carry, so the check is decidable rather
   than aesthetic.
2. **A schema field's parenthetical is where the field's *purpose* hides.** Master §7
   requires publishing the third intermittent test; the reason — "so the set can shrink
   too" — sits in a parenthesis, and the published document carried the field and dropped
   the reason (N4). When a schema field exists to prevent a specific misreading, the field
   text should state the misreading, not gloss it.
3. **"Publish the set" and "publish the exceptions to the set" should use one identifier
   format.** N5 is a small instance of a general shape: a document that instructs a
   mechanical diff must make every identifier in it mechanically comparable.
4. **The count was wrong here once already.** Master §7 obligation 5 records that it
   "originally said 'exactly two ways'". A criterion asserting an *exact count* over an
   enumerated family (C5's "three modes") is worth re-deriving from the family at every
   round that edits the family's prose — which is what P4 was, and it is a good standing
   probe shape for any phase shipping an "exactly N" claim.
