---
plan: plan_3
role: review
round: 2
verdict: APPROVED
date: 2026-08-25
actor: Claude Opus 5 (1M context)
---

# Plan 3 re-review round 1 — SF1, the exact README-cell guard

**Verdict: APPROVED.** Zero blocking, zero should-fix, two notes (N7, N8), zero owner cards.

SF1 is closed. `C4(d)`'s test now asserts one exact table cell per field — `string | Yes` for
`task_id`, `budget_state`, `currency` and `integer | Yes` for the seven numerics — and the guard
was shown to bite by a probe the implementer's ledger did not run: a **string**-row `Required`
mutation, which is the sub-check both declared mutations missed. The perimeter is exactly the one
allowed test file plus the fix handoff; `app/` at HEAD is byte-identical to checkpoint `709fe7c`;
the closing L4 reproduces the durable baseline **∅/∅**.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Card 1 from review r1 was answered and folded into intention round 13;
it is settled and outside this delta.

## Gate check

| Gate | Required | Observed |
|---|---|---|
| Intention status | RATIFIED round 13 | `planning/intention.md` header — `RATIFIED (round 13, 2026-08-25)` ✔ |
| Phase 2 | APPROVED | master plan §4 tracker row 2 ✔ |
| Phase 3 on entry | REVIEWING | master plan §4 tracker row 3 ✔ |

## Verified perimeter

`git diff --name-only 032b0d3..709fe7c` — **exactly two paths**:

1. `app/tests/unit/routers/api_v1/test_budget_signals_route.py` — the sole allowed implementation file
2. `.../task_budget_overrun_signal/handoffs/implementer/20260825_plan_3_fix_round_1.md` — the fix handoff

No production path, no `routers/README.md`, no frontend handoff, no `.archgraph/` path.
`c83c815..709fe7c` adds only the round-1 implementer handoff, as expected. The fix handoff's
declared write perimeter (§ "Gate and scope") matches the tree exactly.

Uncommitted work at review time is confined to the project and to pre-existing unrelated dirt —
`master_plan.md` (the Phase 3 tracker row + the round-12→13 intention pointer), `plans/plan_3.md`
(append-only Review log), `planning/intention.md` (the round-13 amendment), plus the pre-existing
`.archgraph/architecture.yml`, `docs/archgraph-anchor-observations.md` and six untracked
docs/graph paths. **None of it touches `app/`**, so no production or README edit is concealed
inside the dirty set. Preserved untouched, as instructed.

## Evidence identity

| Item | Value |
|---|---|
| HEAD | `709fe7c03050d700fa1317e455807b12f1a5e107` |
| `git status --porcelain` | 5 modified + 6 untracked, **all under `docs/` or `.archgraph/`** (enumerated above) |
| `git diff` digest (all tracked) | `51d65ecf4247d0c317256d8325fa51bc4488ac4382844756a175ea504774fa30` |
| `git diff -- app/` digest | `e3b0c442…b855` — the SHA-256 of the empty string; **`app/` is byte-identical to `709fe7c`** |
| `routers/README.md` sha256, entry **and** exit | `e23b93f8b17cb1d9034383a255254e81ec00f1f48b53a7cec6a1697e90db6620` — matches the implementer's declared restore value |
| `test_budget_signals_route.py` sha256, entry **and** exit | `8c36655ed192acc3dcce182e478f61e900d62b4998863d0691a3c6b8c4a8b3a2` |

The fix handoff's digest `6fcb43b2…` was correctly flagged as incomplete: it excludes dirty paths
and is therefore not a charter tree identity. It is superseded by the row above, which is complete
in both directions — and the `app/`-diff-is-empty statement is the stronger claim, because it
identifies the *tested source tree* with a commit rather than with a digest.

**L4 budget: exactly one, spent one.** Authorization recorded before the run: the fix handoff's
stamp cannot be cited (incomplete identity), and the closing stamp is mandatory on the tree handed
over. All probes were reverted and checksum-verified before it ran.

`PYTHONPATH=. pytest -m 'not e2e'` from `app/` → **21 failed / 2800 passed / 1 skipped / 2 warnings
in 51.27s**.

Failing-ID set compared member-by-member against the durable 21-ID baseline
(`HANDOFF_TO_FRONTEND_live_working_time_clock_20260822.md` §7), by set difference in both
directions, not by count:

- **additions: 0 · removals: 0 — ∅/∅.**

C5(a) siblings: the six named files plus this phase's own test file collect **97 tests** and none
of them appears in the failing set — all green.

## Findings

### N7 — note — the repair silently dropped the per-field occurrence guard

The pre-fix test asserted `section.count(f"data.budget_signals[].{field}") == 1` for each field.
The repair replaced that with `section.count(cell) == 1` on the *exact* cell string, which is
strictly stronger about the cell and strictly weaker about the row: a second, contradictory row for
the same field is no longer visible.

**Measured, not reasoned.** With
`| data.budget_signals[].currency | integer | No |  |` inserted directly beneath the correct
`currency` row, the file ran **6 passed**. The pre-fix assertion would have reddened (count 2).

**Not a should-fix, and here is why the line falls there.** `C4(d)` requires the heading to exist
once and to be followed by the ten rows with their exact type and `Required` cells. All of that is
now discharged cell by cell. `C4(d)` does not forbid an eleventh row, and the section legitimately
carries other rows (`ok`, `data.budget_signals[]`, `warnings[]`, the 422 table), so "nothing else"
was never the criterion. Charging this to a fix round would be relitigating the plan, not the
implementation. Recorded as a lesson with a one-line strengthening available if the coordinator
wants it folded: keep the occurrence count *and* the exact-cell count, one assertion each.

Authority: `plans/plan_3.md` §6 C4(d). Severity: note. Destination: coordinator — plan lesson.

### N8 — note — rule 12: both declared mutations landed on the same sub-check

The repaired test has two loops with two different literals — a `string` loop over three fields and
an `integer` loop over seven. The fix ledger's two mutations were `over_seconds` (type) and
`allowed_seconds` (`Required`) — **both numeric**. The three string-field assertions had no
mutation in the ledger and were never shown able to fail.

Review r1's correction said "one type, one `Required`, on different rows", and the implementer
satisfied that sentence literally. Charter rule 12 asks for one mutation *per sub-check*; a
different-row mutation inside the same loop is the same sub-check. This is the exact shape review
r1's own lesson 2 named one round earlier, reproduced in the round written to close it — which is
the point of the rule: the ledger is derived from the correction's prose, and the prose named rows,
not sub-checks.

**Closed empirically by this review's probe** (below), so nothing needs re-implementing.

Authority: charter standing rule 12; `handoffs/reviewer/20260825_plan_3_review_round_1.md` SF1
correction. Severity: note. Destination: coordinator — prompt-authorship lesson.

## What I verified correct

1. **The perimeter, both directions** — two files in `032b0d3..709fe7c`, and the `app/` working
   tree byte-identical to the checkpoint at entry and exit.
2. **The enumeration is complete and bijective, derived rather than transcribed.** Parsing the
   test's own AST: `string_fields` = 3 distinct, `numeric_fields` = 7 distinct, union = 10, overlap
   = ∅. Parsing the README section with the same row regex: 10 `data.budget_signals[].<field>`
   rows. Set difference in both directions: **∅/∅**. Every row is `Required: Yes`; the three
   strings are `string`, the seven numerics are `integer`.
3. **The documented contract is the served contract** (structural, not behavioural — doctrine 3).
   `serialize_budget_signal` (`domain/item_economics/division_serializers.py:74-88`) emits exactly
   those ten keys in exactly that order. The README enumeration cannot be documenting a field the
   serializer does not produce, nor omitting one it does.
4. **The section split is heading-local and cannot over-reach.**
   `text.split(heading,1)[1].split("\n### ",1)[0]` terminates at the next `### ` heading, and the
   `#### Parameters` / `#### Request Body` / `#### Responses` sub-headings do **not** terminate it
   (`"\n### "` requires a space in the fourth position; `"\n####"` has `#`). The 422 response table
   is inside the window, which is why the `data.budget_signals[].` prefix in every asserted cell
   matters — it is what keeps `detail[].msg | string | Yes` out of the field enumeration.
5. **No substring collision inside the enumeration.** `over_seconds` is a substring of
   `projected_over_seconds`, but each asserted cell is anchored by `| data.budget_signals[].` on
   the left, so the projected rows cannot satisfy the bare rows' assertions. The
   `count(...) == 1` form would have caught it if they could.
6. **Both declared fix mutations are credible from the assertion structure** and their L1 evidence
   is consumed by citation, not re-run: each breaks the literal `| ...<field> | integer | Yes |`
   its loop iteration searches for, driving `count` to 0. The implementer's reported `1 failed`
   matches this file's shape (6 tests: 1 failed / 5 passed), which my own probe reproduced
   independently.
7. **The tracker, Review log and fix handoff agree with the tree** — no claim in the fix handoff is
   contradicted by anything I measured, including its honest statement that its own digest excludes
   dirty paths.
8. **Passing-glance sweep, per the prompt's clause:** route ordering, the endpoint graph delta,
   N2–N6, and the Phase 1/2 surfaces were not reopened and nothing about them looked wrong in
   passing. No graph tool was called; `.archgraph/architecture.yml`'s mixed bootstrap/endpoint
   hunks are preserved unmodified for the approval closeout.

## Mutation-probe declaration

One probe pair, both on `app/beyo_manager/routers/README.md`, both applied-and-reverted, both
checksum-verified byte-identical afterwards.

| # | Probe | Scope | Result | Restored |
|---|---|---|---|---|
| P1 | `currency`: `\| string \| Yes \|` → `\| string \| No \|` — a **string** row's `Required` cell, the sub-check neither declared mutation touched (prompt required depth §2) | L1, `test_budget_signals_route.py` | **1 failed / 5 passed** — red at the string-loop exact-cell assertion, `assert 0 == 1` on `'\| data.budget_signals[].currency \| string \| Yes \|'` | sha256 `e23b93f8…6620` ✔ |
| P2 | Inserted a contradictory duplicate row `\| data.budget_signals[].currency \| integer \| No \|  \|` beneath the correct one (N7's hypothesis) | L1, same file | **6 passed** — the duplicate is invisible to the repaired guard | sha256 `e23b93f8…6620` ✔ |

Files written by this session: this handoff, the Phase 3 tracker row in `master_plan.md`, and one
append-only entry in `plans/plan_3.md` §9. Nothing else. No file was fixed, no graph state touched,
no database or other persistent state mutated — the L4 run creates and drops its own disposable
databases per `tests/database_isolation.py`.

## Carry-forward dispositions

| Item | Destination | Why |
|---|---|---|
| N1 / card 1 | **CLOSED** — owner answered; intention round 13 folded | Settled; outside this delta |
| SF1 | **CLOSED** — this re-review | Cell-by-cell assertions shipped and mutation-proven |
| N2 | **Coordinator — plan lesson**, next route-adding phase | Unchanged from r1: C4(a) names a column its home test cannot see |
| N3 | **Coordinator — record only** | Unchanged from r1 |
| N4 | **Coordinator — planner lesson** | Unchanged from r1; N8 is its second instance and strengthens the case for folding it into the planner's criterion template |
| N5 | **Coordinator — candidate criterion for C6(e)** + C6(a)/C6(b) locality | Unchanged from r1; **N7 is the same family** (a guard that pins part of a table instead of its rows) — fold the two together |
| N6 | **Coordinator — record only** | Unchanged from r1 |
| **N7** | **Coordinator — plan lesson**, folded with N5 | One-line strengthening available; not chargeable to `C4(d)` as written |
| **N8** | **Coordinator — prompt-authorship lesson** | A correction must name the sub-check, not the row |

## Lessons for the plans

1. **A correction that prescribes mutations names the *sub-check*, not the row.** "One type, one
   `Required`, on different rows" is satisfiable entirely inside one loop, and was. When a repair
   splits an assertion into N shapes, the mutation set is enumerated from the repaired code — rule
   12's "enumerate from the code *after* the repair" — which is precisely where a prose-derived
   ledger stops growing rows. This is review r1's lesson 2 recurring one round later, in the round
   written to close it; it should become a line in the coordinator's fix-prompt template rather
   than a lesson re-earned per project.
2. **A repair that tightens one dimension can loosen another, and nothing in the pipeline looks
   for that.** SF1 asked for exact cells and got them; the occurrence-uniqueness guard that already
   existed left with the line it lived on. The cheap check — "does the repaired assertion still
   catch everything the old one caught?" — has no home in any current gate. Candidate for the fix
   round's own closing protocol: diff the *deleted* assertions, not only the added ones.
3. **When a criterion's subject is a table, its rows are the criterion** — restated from r1
   lesson 4, now with a second instance (N7) and a third pending (N5). Three occurrences in one
   phase argues for a planner-side template row rather than three separate lessons.
