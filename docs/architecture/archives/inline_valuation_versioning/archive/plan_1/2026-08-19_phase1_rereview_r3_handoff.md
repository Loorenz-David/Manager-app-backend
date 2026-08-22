---
plan: 1
role: review
round: 3
verdict: APPROVED
state: APPROVED
date: 2026-08-19
actor: Claude (reviewer)
pipeline: inline_valuation_versioning
---

# Reviewer handoff — phase 1, re-review round 3 (fix r2 verification)

**Verdict: APPROVED.** S1 is closed. Nothing was loosened to close it. F1 is ruled a
**note, not a should-fix** — the coordinator's reading is correct, and I found a concrete
reason it is correct that strengthens it beyond the argument offered.

Zero new findings. Two notes carried, one recurrence.

## ⚠ OWNER DECISIONS REQUIRED (0)

None. Card 1 from r1 was answered and applied; nothing else needs the owner.

## Review history (what earlier rounds settled)

- **r1 (review)** — CHANGES_REQUIRED. M1 verified faithful and complete; six mutation
  probes; HC-2/HC-4 verified structurally; three coercion/edge traps checked and cleared.
  One should-fix (S1: C9's guard narrower than C9's perimeter), five notes, one owner card.
- **r2 (fix)** — S1 addressed in ten lines, one file.
- **r3 (this round)** — narrow. The r1 settled-ground section stands and was not
  re-derived, per the prompt.

## S1 — CLOSURE LINE

**S1 is CLOSED.** `test_retired_inline_refusal_identity_is_absent_from_live_sources`
(`app/tests/unit/docs/test_item_economics_handoff_accuracy.py:220-226`) now scans
`_APP_ROOT` and the whole of `_HANDOFFS`, and the guard fires on the roots it previously
could not see.

I did not repeat the coordinator's two plants. I extended to two roots **neither r1 nor the
coordinator has probed**, planting each alone so each proves itself:

| Probe | Plant (alone) | Result |
|---|---|---|
| **P7** | `app/migrations/_rev_probe.py` | ❌→✅ **red**, `AssertionError: PosixPath('…/app/migrations/_rev_probe.py')`, `1 failed, 50 passed` |
| **P8** | `docs/handoff/presentation_system/_rev_probe.md` | ❌→✅ **red**, `AssertionError: PosixPath('…/docs/handoff/presentation_system/_rev_probe.md')`, `1 failed, 50 passed` |

`app/migrations/` and `docs/handoff/presentation_system/` are the two roots the fix handoff
*claims* without demonstrating. Both are now genuinely inside the guard. Combined with the
coordinator's separated `app/scripts/` and `docs/handoff/from_frontend/` plants, all four
newly-covered roots are proven independently.

The r1 failure mode is gone: the exact plant that left the suite green at 51 passed in r1
now turns it red and names the offending path.

## F1 — RULING: note, not should-fix. I agree with the coordinator.

**The question.** C9 names the trees `app/` and `docs/handoff/`; the guard filters to
`*.py` and `*.md`. `app/_coord_probe.yml` carrying the literal leaves the guard green. Is
stating the narrowing in the criterion enough, or must the guard cover other file types?

**Ruling: stating it is enough. Note-level is correct.** Four reasons, in order of weight.

**1. Removing the filter is not "two more lines" — it is demonstrably broken.**
This is the fact that decides it, and it was not in the coordinator's argument. Inside the
guard's own new root sits
`docs/handoff/to_frontend/archived/beyo_partner_api (1).docx`. I ran `read_text()` on it:

```
read_text raises: UnicodeDecodeError 'utf-8' codec can't decode byte 0x87 in position 10
```

A guard with no extension filter would crash on that file and report C9 **red for a reason
that has nothing to do with the identity** — every run, forever, until someone deletes an
archived document. A tripwire that fires on an unrelated binary is worse than one with a
stated perimeter: it trains people to ignore it.

**2. The narrowing is principled, not arbitrary.** A Python error identity has exactly two
surfaces in this repo: raised in `.py`, published in `.md`. That is not a guess — it is
this phase's own HC-1 perimeter, where files 1–3 are `.py` and file 4 is `.md`.

**3. I checked the residual risk empirically rather than arguing it.** Enumerating every
non-`.py`/`.md` file under `app/` (excluding `.venv`/`__pycache__`) yields
`data.json`, `docker-compose.yml`, `.github/workflows/ci.yml`, four
`migration_reports/*.json` dumps, connecteam test fixtures, plus csv/log/sh/ini/txt.
`docs/handoff/` contains exactly one non-`.md` file — the archived `.docx` above. Not one
of these is a surface on which anyone would raise or publish a backend error identity.
The uncovered risk is real but empty.

**4. My own r1 rule is satisfied on its own terms.** I wrote: *"if any root is deliberately
left out, say so in the criterion, not silently in the test."* C9 as restated
(`plans/plan_1.md:68`) now names the extension filter **and** the `app/.venv/` exclusion
**and** cites why. The failure r1 punished was a *silent* narrowing — a guard quietly
claiming a perimeter it did not hold. A stated narrowing is a different object: it is a
scope decision on the record, which is what the criterion is for.

**Recorded refinement**, so a future session does not reopen this badly: if C9's coverage
is ever widened, the correct shape is to **extend the extension allowlist**
(`.yml`, `.json`, `.sh`, `.txt`), never to remove the filter. "All files" is not the strict
option here; it is the broken one.

## Adjudication of the remaining items

### 2. The `app/.venv/` exclusion — confirmed sound on all three counts

- **It is the only exclusion.** One `continue`, one condition, at `:224-225`. No other
  filter, skip or `try/except` was introduced.
- **It is minimally scoped.** The condition is guarded on `root == _APP_ROOT`, so it cannot
  touch `_HANDOFFS` at all. `_APP_ROOT` (`backend/app`) and `_HANDOFFS`
  (`backend/docs/handoff`) are disjoint, so nothing is double-scanned or double-skipped.
- **No live source root was narrowed by it.** Proven, not asserted: **P7** shows
  `app/migrations/` — one of the roots the exclusion could plausibly have swallowed — is
  covered and red. `app/scripts/` is covered (coordinator). `_PACKAGE` and `app/tests` are
  subsumed by `_APP_ROOT`. Top-level modules (`run.py`, `seed_*.py`, `list_workers.py`) sit
  directly under `_APP_ROOT`.
- **It cannot be used to hide a real occurrence.** **P9**: planting the literal at
  `app/.venv/_rev_probe.py` alone leaves the guard green — the exclusion is real and does
  what it says. That is only safe because nothing of ours can live there, which I confirmed
  independently: `.venv/` is gitignored (`.gitignore:11`, matched via `git check-ignore -v
  app/.venv`). Anything under it is installed third-party code that cannot be committed.

### 3. Nothing loosened — confirmed

`git diff 9e5738b e9531dc -- app/` is ten lines, and they are all widening or
re-pointing:

- `_HANDOFFS` `docs/handoff/to_frontend` → `docs/handoff` (widening).
- `_OPERATIONAL` / `_CONFIGURATION` re-pointed through the new `to_frontend/` child.
  **Both resolve** — `_text()` would raise `FileNotFoundError` otherwise, and the module is
  green at 51 passed with those two documents driving eleven assertions.
- Guard roots `(_PACKAGE, _APP_ROOT / "tests", _HANDOFFS)` → `(_APP_ROOT, _HANDOFFS)`
  (widening; `_APP_ROOT` strictly subsumes the two it replaced).
- The `.venv` skip (the only narrowing, adjudicated above).

No assertion elsewhere in the module was weakened, and I checked the one way this change
could have leaked: `_HANDOFFS` has exactly three other usages — its definition and the two
document constants. In particular **the widening did not silently pull
`from_frontend/` and `presentation_system/` into
`test_no_document_names_an_unregistered_error_identity`**, whose parametrize lists four
named documents explicitly (`:175`, `:187`) rather than globbing a directory. The change is
confined to the C9 guard, which is exactly where it belongs.

`_PACKAGE` is **not** dead after the root swap — it still backs
`test_every_literal_identity_is_greppable_in_the_package` at `:135`. Charter rule 4 holds.

**Suite, third independent full run this session** (`PYTHONPATH=. pytest -m 'not e2e'` from
`backend/app`): **2320 passed / 26 failed / 1 deselected**, 120.1s. Failure-ID set
**byte-identical** to the r1 runs A and B and to the declared baseline. No drift in any of
the three runs. Selected count unchanged at 2346, as expected for a widened glob.

Performance cost of the widened `rglob`: none worth naming — the module runs 1.38–1.52s
against 1.33s before.

### 4. The three declared DECISIONS — all three ruled correct

**(1) Exclude only `app/.venv/`. — RIGHT.** Adjudicated above; verified on all three counts
the prompt asked for, and the reasoning given ("installed dependency environment, not a
live source root") is the right reason, not a rationalisation.

**(2) Keep the C1→C7 rename and record it. — RIGHT.** This is exactly what r1's N1
recommended, and the recommendation stands for the reason given: reverting would break this
plan's citations and could not repair the archived ones, which the charter forbids
rewriting.

**(3) Do not apply `ruff format`. — RIGHT, and right for the right reason.**
I verified both halves of the claim: `ruff format --check` does report
`Would reformat: tests/unit/docs/test_item_economics_handoff_accuracy.py`, and
`ruff check` — the gate this project actually runs — passes clean.

Leaving it unformatted was correct. The fix perimeter was ten substantive lines in an HC-1
file; a whole-file reformat would have buried them in unrelated churn and made the
perimeter diff unreadable. That diff is not cosmetic bookkeeping — it is the evidence base
this entire round is built on, and the charter's checkpoint discipline exists precisely so
that "nothing changed outside the perimeter" is structurally verifiable. An implementer who
reformats a legacy module while fixing a bug destroys that property for every reviewer
downstream. Formatting this module is legitimate work; it is separate, declarable work.

The handling was also right: they explored it, saw the churn, **reverted completely before**
the final probe, suite, diff and checkpoint, and declared the whole episode. That is the
behaviour the DECISIONS section exists to capture — contrast r1's N1, where an undeclared
rename was the finding.

### 5. N1's mapping — recorded, accurate, and the archived citations are followable

Recorded twice in `plans/plan_1.md` (the review-r1 entry and the fix-r2 entry), both with
the same mapping. Verified end to end rather than read:

| | Old (as cited in the archive) | New (as it exists today) |
|---|---|---|
| function | `test_c1_inline_birth_writes_valuation_and_handles_exact_auto_statuses` | `test_c7_inline_birth_writes_valuation_and_handles_exact_auto_statuses` — 1 definition present |
| ids | `C1-row-*` | `C7-row-*` — 6 present |

Both citations confirmed to still read as recorded:
`item_cost_calculation/archive/plan_8b/2026-08-15_phase8b_implement_r1_handoff.md:49`
carries the old function name in its mutation-probe table, and
`…/2026-08-15_phase8b_review_r1_handoff.md:187` carries `C1-row-1-full-trio-purchase-term-commits`
in its coverage table. The mapping is a one-to-one substitution in both dimensions, so a
reader landing on either archived line can follow it to live code. **N1 is CLOSED.**

## Ledger

No blocking findings. No should-fix findings. One new note.

### N6 — note — F1, ruled: the extension filter stays, and stays stated

`app/tests/unit/docs/test_item_economics_handoff_accuracy.py:223`. Adjudicated in full
above. Disposition: **accepted and closed by ruling.** C9 (`plans/plan_1.md:68`) states the
narrowing; the refinement for any future widening (extend the allowlist, never remove the
filter) is recorded here and needs no further action.

### N7 — note — the prompt's evidence range spans an intervening commit (r1's N4, recurring)

The prompt names `git diff 6f82579 e9531dc` as "the whole evidence base — ten lines". That
range is **13 files / 1083 insertions**, because `9e5738b` (the coordinator's own routing
commit: graph records, the r1 handoff, master plan, prompts) sits between them. The
checkpoint's own diff — `git show e9531dc`, equivalently `9e5738b..e9531dc` — is the two
files and ten lines the prompt describes, and is what I reviewed.

The *substance* of the prompt was accurate; only the range was wrong, and it was wrong in
the same shape as r1's N4 (`aa95d5e` spanning the previous pipeline). The lesson was folded
into the r1 handoff but not applied at r3 compile time. No impact on this round — I
recomputed the range before reading it — but the second occurrence is worth one line,
because a perimeter check that starts from an over-broad range is the one check a reviewer
cannot afford to take on trust.

**Suggested correction, mechanical:** compile the range as
`git show --stat <checkpoint>` rather than a remembered earlier hash.

## Carry-forward dispositions

This is the project's final phase, so no note may be routed to "a later phase" — each one
gets a real destination or is closed here.

| Note | Origin | Disposition |
|---|---|---|
| N1 — undeclared C1→C7 rename | r1 | **CLOSED** at fix r2. Mapping recorded in `plan_1.md` and verified followable this round. |
| N2 — two criterion vocabularies share `test_phase8b_inline_task_prices.py` | r1 | **OPEN, accepted as debt.** No phase remains to hold it. Route to the coordinator's closeout ritual as an optional one-line banner comment naming which C-range belongs to which plan; if closeout declines it, it is accepted permanently — the `plan_1.md` mapping is the standing mitigation. Not a gate. |
| N3 — C8's trigger bite map (P4a red / P4b green) | r1 | **CLOSED by recording** in the r1 criterion→mutation table. Informational; no action. |
| N4 → N7 — prompt evidence range | r1, recurred r3 | **OPEN as a practice lesson**, not a work item. Destination: coordinator prompt compilation (see the mechanical correction above). Not a gate. |
| N5 — graph anchor `72-580` | r1, card 1 | **CLOSED.** Owner authorized; anchor widened to `72-594`. Confirmed independently this round: `archgraph_status` reports revision `50b3940273f51b9b…`, 183 nodes / 275 edges, 0 diagnostics, 0 stale, 4 pending. Not re-flagged. |
| N6 — F1 extension filter | r3 | **CLOSED by ruling.** Narrowing stated in C9. |

## Mutation-probe declaration

Three probes this round, each planted **alone** so each root proves itself.

| Probe | File created | Expected | Observed | Reverted |
|---|---|---|---|---|
| P7 | `app/migrations/_rev_probe.py` | red | red, path named | `rm`, absent |
| P8 | `docs/handoff/presentation_system/_rev_probe.md` | red | red, path named | `rm`, absent |
| P9 | `app/.venv/_rev_probe.py` | **green** (exclusion holds) | green, 51 passed | `rm`, absent |

Plus one read-only check with no filesystem effect: `read_text()` attempted on
`docs/handoff/to_frontend/archived/beyo_partner_api (1).docx` in a throwaway interpreter,
which raised `UnicodeDecodeError` (the F1 evidence). The file was not modified.

**No production file was touched this round.** `create_task.py` was not opened for
mutation; its hash is untouched since r1's declaration. Final state:
`git status --short` **empty**; all three probe paths verified absent by `ls`.

**Database/state:** all probe runs were scoped to the docs-accuracy module, which is
`@pytest.mark.unit` and touches no database. One full suite run was executed; per master
plan §6 it accrues `task_steps` rows from tests outside this pipeline, so row counts remain
an unreliable baseline — failure **IDs** are the signal, and they were byte-identical.

**Architecture graph:** read-only (`archgraph_status`). Zero mutations, zero records
written; revision unchanged at `50b39402…`.

## Write perimeter

Exactly one file, as the prompt directed:
`docs/architecture/under_construction/implementation/inline_valuation_versioning/handoffs/reviewer/2026-08-19_phase1_rereview_r3_handoff.md`

The tracker row and the plan-file Review log entry are deliberately **not** written — they
fall outside the declared perimeter. Text for the coordinator follows.

### Tracker line for the coordinator — master plan §3

> | 1 | M1 compare/inherit/version in `create_task`, identity retired, tests | **APPROVED** | 2026-08-19 | Claude (reviewer) | Re-review r3: **S1 CLOSED**, verified by two fresh single-root plants the earlier rounds never probed — `app/migrations/` and `docs/handoff/presentation_system/` each turn the guard red alone (P7, P8); `app/.venv/` correctly stays green (P9) and is gitignored, so it cannot hide committed source. **F1 ruled note, not should-fix**: removing the extension filter would make the guard crash on `docs/handoff/to_frontend/archived/beyo_partner_api (1).docx` (`UnicodeDecodeError`) and go red forever for the wrong reason; the narrowing is now stated in C9, which satisfies r1's own rule. Nothing loosened — the ten lines are all widening plus two path re-points; `_PACKAGE` still live at `:135`; the widening did not leak into the unregistered-identity arbiter. All three implementer DECISIONS ruled correct, including declining `ruff format` (verified: `format --check` would reformat, `check` is clean) — reformatting an HC-1 file mid-fix would have destroyed the perimeter diff this round runs on. N1 mapping verified followable. Suite 2320/26/1, third run this session, IDs byte-identical. New note N7 (prompt range spans an intervening commit — r1's N4 recurring). Handoff: `handoffs/reviewer/2026-08-19_phase1_rereview_r3_handoff.md`. |

### Review log line for the coordinator — plan_1.md

> - **re-review r3 (2026-08-19, Opus 5) — APPROVED.** Narrow round; r1's settled ground not
>   re-derived. **S1 closed.** Extended rather than repeated the coordinator's plants: P7
>   `app/migrations/_rev_probe.py` and P8 `docs/handoff/presentation_system/_rev_probe.md`
>   each planted **alone** turn the guard red and name the path — the two roots the fix
>   handoff claimed but never demonstrated. P9 confirms the `app/.venv/` exclusion holds
>   (green) and is the only one, guarded on `root == _APP_ROOT`; `.venv/` is gitignored
>   (`.gitignore:11`), so it cannot conceal committed source. **F1 ruled note, not
>   should-fix** — decisive fact: `docs/handoff/to_frontend/archived/beyo_partner_api
>   (1).docx` raises `UnicodeDecodeError` on `read_text()`, so a filter-free guard would
>   report C9 red permanently for an unrelated reason; the residual carriers under `app/`
>   were enumerated and none is a surface for a backend error identity; and C9 now states
>   the narrowing, which is what review r1's rule demanded. If ever widened, **extend the
>   extension allowlist — never remove the filter.** Nothing loosened: the ten lines are
>   widening plus two re-points, `_OPERATIONAL`/`_CONFIGURATION` resolve, `_PACKAGE`
>   remains live at `:135`, and `test_no_document_names_an_unregistered_error_identity`
>   still audits four named documents rather than globbing the widened `_HANDOFFS`. All
>   three DECISIONS ruled correct; declining `ruff format` was right — verified `format
>   --check` reports the module would reformat while `check` is clean, and a whole-file
>   reformat of an HC-1 file would have buried ten substantive lines and destroyed the
>   perimeter diff every review round depends on. N1 mapping verified accurate and both
>   archived phase-8b citations followable. Suite 2320/26/1, third independent run, IDs
>   byte-identical to baseline and to runs A/B. Graph confirmed at revision `50b39402…`,
>   0 diagnostics, not re-flagged. **New note N7:** the r3 prompt's `6f82579..e9531dc`
>   range spans the intervening routing commit `9e5738b` (13 files, not ten lines) — r1's
>   N4 recurring; compile ranges with `git show --stat <checkpoint>`.

## Lessons for the plans

1. **A stated narrowing and a silent one are different objects.** r1 punished a guard that
   claimed a perimeter it did not hold. F1 looks identical one layer out but is not: the
   scope decision is now on the record in the criterion, where a future reader meets it. The
   rule earned in r1 should be read as *"narrowings live in the criterion"*, not *"guards
   must have no narrowings"* — and this round is the precedent for that reading.
2. **Check whether the strict option is actually available before demanding it.** F1's
   "obvious" fix — drop the extension filter — would have shipped a permanently red test.
   One `read_text()` against the real tree settled in seconds what an argument about
   principle would not have. When ruling on a coverage gap, enumerate the actual files the
   widening would sweep.
3. **Declining a formatter mid-fix is a perimeter decision, not a style one**, and belongs
   in DECISIONS exactly where the implementer put it. Worth promoting to a standing rule:
   *a fix cycle never applies a whole-file reformat to a file inside its perimeter; the
   perimeter diff is the round's evidence base.*
4. **What worked and should be kept.** Planting each root **separately** rather than
   together — the coordinator's improvement on my r1 probe — is strictly stronger and cost
   nothing; it should be the default shape for any multi-root guard. And the fix perimeter
   held to ten lines in one file, which is why this round could be narrow and cheap.
