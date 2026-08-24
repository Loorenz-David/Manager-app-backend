---
plan: plan_5
role: review
round: 2
verdict: CHANGES_REQUESTED
date: 2026-08-24
actor: Opus 5 (delta re-review, three questions)
---

# Plan 5 — delta re-review. Three questions, answered by measurement.

**Verdict: `CHANGES_REQUESTED`.** 1 blocking / 1 should-fix / 3 notes / **0 owner cards**.

Q1 holds. **Q2 does not.** Q3's free pass is declined where the prompt aimed it and spent
where measurement put it.

The short version: fix round 4 did exactly what it was asked to do, and the decoupling is real
and correctly measured. But decoupling C1(b) from narrowing moved M7's only composed guard off
the **spec branch** of `typical_times_statement` and onto the **no-spec branch** — and the spec
branch is the one every narrowed task takes. I planted a spec-branch clock defect and **the
whole suite stayed green**; I then planted the same defect against C1(b)'s *pre-round-4* form and
it **reddens at `:127`**, the byte-identity assertion. The coverage did not move to a better
place; it left.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Both items are routine corrections that route to the implementer.

## Gate check — content only

| # | check | expected | observed |
|---|---|---|---|
| 1 | `git status --porcelain -- app/` | empty | **empty** ✓ |
| 2 | `plans/plan_5.md` header `state:` | `IMPLEMENTED` | **`IMPLEMENTED`** ✓ |
| 3 | master plan §4 row 5 | `IMPLEMENTED` | **`IMPLEMENTED`** ✓ |
| 4 | `planning/intention.md` `status:` | `RATIFIED` | **`RATIFIED`** (round 10, 2026-08-24) ✓ |
| 5 | `redis-cli ping` | `PONG` | **`PONG`** ✓ |
| 6 | `plain_task` inside `test_c1b_…` | a hit | **hit at `:118`** ✓ |

Tree at review: `22da229`, `app/` clean. `.archgraph/` not read (D31).

---

## Q1 — Does C1(b) still *compose* clock and window? **Yes. Genuinely.**

It is not a test that merely notices a number changed, and the fixture alignment the question
worries about is precisely what *arms* it rather than what weakens it.

The mechanism, verified at source: `get_working_section_typical_times.py:147` computes
`cutoff = (now if now is not None else datetime.now(timezone.utc)) - timedelta(days=90)`, and
`qualifying = latest_closed_at >= cutoff` gates both the count and the percentile. The fixture
pins **all twelve** completed groups at `closed_at == 2026-08-01T00:00:00Z`; the test freezes
`ctx.now` at `2026-10-30T00:00:00Z`. That is exactly `TYPICAL_WINDOW_DAYS` apart, so the
`FakeDatetime`'s two readings (`frozen − 1s`, `frozen + 1s`) put the boundary group **inside**
on the first call and **outside** on the second. Under either boundary convention (`>=` or `>`)
the two readings straddle.

Two things make this a composed guard rather than a stability check:

1. The failure is a **difference between two calls inside one frozen context** — M7's stated
   observable — not a drift from a stored expectation.
2. I observed the "out" state directly (probe P2, output captured): `total_seconds: 0`,
   `is_estimated: true`, `sections_by_basis: {"insufficient_sample": 1, …}`, against `375` /
   `false` on the "in" side. The 90-day window is what swings, and nothing else can produce that
   payload.

The decoupling claim also holds structurally: `plain_task`'s primary item carries no category, so
`derive_spec_from_primary_item` yields a non-narrowing spec, `specs = ()`, and `_typical_block`
routes to `_no_spec_typical_times_statement`. No narrowing predicate is on the path. The plan's
`375` is the section-wide median of the full twelve-group population
(`100…400` ∪ `500…700`, median `(350+400)/2`), which is arithmetic, not a coincidence.

**Q1 verdict: holds.** See S1 for the one qualification — it does not undo this answer.

---

## Q2 — Did moving C1(b) off `narrowed_task` remove coverage nothing else has? **Yes. Measured both ways.**

### B1 — blocking — the spec branch's injected clock is guarded by nothing

`typical_times_statement` carries **two independent cutoff lines**, one per branch:

- `:40` — the **spec** branch (`len(specs) > 0`), taken by every narrowed task;
- `:147` — the **no-spec** branch, taken by `plain_task`.

Both compute `(now if now is not None else datetime.now(timezone.utc)) - timedelta(days=TYPICAL_WINDOW_DAYS)`
in duplicated source. C1(b) used to exercise `:40`. It now exercises `:147` only.

**Probe P1 — plant the defect on `:40` alone** (`(now if now is not None else datetime.now(...))`
→ `datetime.now(timezone.utc)`; `:147` untouched):

| scope | command | result |
|---|---|---|
| L1 | phase's two test files, `-n 0` | **67 passed** — inert |
| **L4** | `TZ=UTC … pytest -m 'not e2e'` | **2705 passed / 23 failed / 1 skipped**, 53.89s |

The L4 ID delta against the published 21-ID set is **∅ removed / +2 added**, and both additions
are `test_database_isolation.py::test_worker_name_resolution*`, which pin the literal slot name
`beyo_test_main_main` and fail under my `BEYO_TEST_SLOT=rvw`. Verified independently: that file
is **50 passed / 1 skipped** on the same mutated tree at the default slot. **The mutation's
whole-suite bite set is ∅.**

L4 was the correct entry scope here, not an escalation: the hypothesis is an absence claim
("nothing anywhere guards this"), which is repository-wide by construction.

**Probe P2 — the same defect against C1(b)'s pre-round-4 form.** With P1 still applied I
repointed C1(b) at `narrowed_task` and `600` — the two edits fix round 4 made, reversed — and ran
it alone:

```
FAILED test_c1b_same_frozen_context_produces_byte_identical_typicals
>   assert json.dumps(first["typical"], sort_keys=True) == json.dumps(...
-  {"is_estimated": true,  … "sections_by_basis": {"insufficient_sample": 1, "item_narrowed": 0,
                              "section_wide": 0}, "total_seconds": 0,   "task_typical_basis": "section_wide_uniform"}
+  {"is_estimated": false, …
```

**Red at `:127`, the byte-identity assertion, boundary group in then out.** So the property was
observed before the fix and is observed by nothing after it.

**Why nothing else covers it.** `test_typical_times_narrowing.py` drives the spec branch at
statement level fifteen times and passes `now=NOW` on **every** call — but its populations cannot
see which clock supplies the cutoff. Its default group sits at `NOW − 1 day` (`:125`) and its one
`"outside-window"` group at `NOW − 91 days` (`:278`), while `NOW = 2026-08-22` is two days from
the real wall clock. A two-day shift cannot move a group that is 1 day inside, or 91 days outside,
across a 90-day line. Every one of those rows is green under P1 — which is what the ∅ bite set
says. `test_c1a` asserts the kwarg *handed to* the statement, not what the statement does with it,
so it is green under P1 by construction.

**Authority.** Plan 5 §6A **C1**, trace **M7**; charter rule 15 (a guard ships with proof it can
fail) and rule 12 (a named mutation must reach every sub-check — C1(i) now reaches only the
no-spec branch's sub-check).

**Suggested correction — cheap, and it keeps what round 4 earned.** Do **not** move C1(b) back;
its `plain_task` form is right and the coupling argument that motivated the move is sound. Add
one **statement-level** row that pins a boundary group on the spec branch:

```python
# spec branch, boundary group at NOW - TYPICAL_WINDOW_DAYS, two injected clocks
spec = TypicalFilterSpec(item_category_ids=frozenset({category_id}))
inside  = _rows(await db_session.execute(typical_times_statement(ws, specs=(spec,), now=BOUNDARY + timedelta(days=TYPICAL_WINDOW_DAYS))))
outside = _rows(await db_session.execute(typical_times_statement(ws, specs=(spec,), now=BOUNDARY + timedelta(days=TYPICAL_WINDOW_DAYS, seconds=1))))
assert inside[0].narrowed_sample_count == 5 and outside[0].narrowed_sample_count == 0
```

This asserts on the injected clock alone, has no `_typical_block` on the path, and **no narrowing
mutation can redden it** — the exact property the fix round was chasing. It belongs beside C1 in
`test_narrowed_price_scenario.py` (row (c) already sets the recorded-deviation precedent), or in
`test_typical_times_narrowing.py` if the coordinator would rather the statement own it. Declare
it as a **candidate criterion** — C1(d) — so it traces.

---

## Q3 — the free pass for a row that cannot fail

**I decline it where the prompt aimed it, and spend it where measurement put it.**

### `_TypicalSession` is not the instrument to distrust here — measured

I checked every row built on it (`test_c1a`, `test_c1c`, `test_c2` ×3, `test_c2d`, `test_c3`,
`test_c4` ×2, `test_c7`-delegates). None of them *claims* something the SQL decides:

- `test_c1a` / `test_c1c` assert the **kwargs handed to** the statement, captured by a delegating
  spy. `test_c1c` even carries its own anti-vacuity guard (`assert calls`) so an empty `captured`
  cannot pass as an absence. Both are armed: `now=ctx.now` is keyword-only, so mutation (ii)
  cannot slip past as a positional.
- `test_c2` / `test_c2d` / `test_c3` / `test_c4` assert **Python-side reconciliation and
  aggregation** over rows the fake legitimately supplies. That is what the fake is for.

And the division of labour is real, not assumed. **Probe P3 — I broke a genuine SQL property of
the spec branch** (dropped `TaskStep.state == COMPLETED` from `:48`, no-spec branch untouched):

| scope | result |
|---|---|
| phase's two test files | **67 passed** — invisible, as the prompt predicts |
| `tests/integration/services/queries/working_sections/` | **1 failed** — `test_spec_index_preserves_input_order_and_section_population_is_constant` |

Phase 2 owns the statement and catches it. The fake's blindness is correct scoping, not a
row-that-cannot-fail. The one spec-branch property phase 2 does *not* guard is `now` — which is
B1, not a `_TypicalSession` defect.

### S1 — should-fix — C1(b) is one legal config change away from being unable to fail

The row's entire discriminating power rests on `2026-08-01` (fixture, `_narrowing_fixture.py:…`)
and `2026-10-30` (test, `:99`) being **exactly `TYPICAL_WINDOW_DAYS` apart**. That subtraction was
done by hand and is asserted nowhere — neither literal references the constant.

**Probe P3b, measured.** With `TYPICAL_WINDOW_DAYS = 91` and the row's own named mutation
**C1(i)** applied (`now=` dropped at the `_typical_block` call site):

```
FAILED test_c1a_typical_block_passes_the_request_clock_to_the_statement   (KeyError at :92)
1 failed, 2 passed
```

**`test_c1b` passes.** One day on a config constant and C1(i)'s red lands only on `test_c1a` —
*the same observable `test_c1a` already asserts*, which is verbatim the defect round 1's B2 was
raised to fix. The row would not announce its own death; it would simply stop being the composed
guard while staying green.

The config change is not silent overall — `TYPICAL_WINDOW_DAYS = 91` alone reddens two rows in
`test_typical_times_narrowing.py` (`test_spec_index_preserves_…`, `test_service_no_spec_payload_is_explicitly_unchanged`).
But that is the failure mode that makes it worse, not better: the reds come from *unrelated rows
pinning the literal*, someone updates them to `91`, and C1(b) is inert from then on with nothing
pointing at it.

**Authority.** Charter rule 13 (a criterion asserting a configured value asserts its contract, not
its literal) and rule 15.

**Suggested correction — two lines, no fixture change.** Import the constant and derive the frozen
clock from the fixture's boundary instead of typing it:

```python
from beyo_manager.domain.item_economics.typical_constants import TYPICAL_WINDOW_DAYS
BOUNDARY = datetime(2026, 8, 1, tzinfo=timezone.utc)          # == the fixture's max(closed_at)
frozen = BOUNDARY + timedelta(days=TYPICAL_WINDOW_DAYS)        # was: datetime(2026, 10, 30, …)
```

`seed_divergent_category_task` is plan 5's own addition (§4A), so pinning `BOUNDARY` from it — or
exporting it from the fixture module — is inside this phase's perimeter. `test_c5` and `test_c8`
run at `now = 2026-08-24T12:00` and are unaffected either way (their cutoff is `2026-05-26`; the
boundary group qualifies with 85 days to spare).

---

## Notes

**N1 — the `spec_index` filter is exercised by nothing.** `_typical_block:157` guards
`if int(row.spec_index) != 0: continue`, but `_spec_row` hard-codes `spec_index=0` and every
DB-backed row (`test_c5`, `test_c8`) passes exactly one spec, so the SQL emits `spec_index = 0`
only. Deleting the guard is a no-op across the phase. Correct defence-in-depth — `_typical_block`
constructs `specs` as a 0-or-1 tuple, so no reachable defect exists today — but it is uncovered
surface that a future multi-spec caller would inherit unguarded. Record; do not add a row for it
in this phase.

**N2 — C2 row (a)'s shipped fixture is weaker than its criterion.** §6A C2 row (a) specifies
*"every section excluded → participating set empty"*; the shipped parametrize case is
`([], [], (0, True, 0, 0))` — **no steps at all**. Those differ: the criterion's fixture leaves
`section_ids` non-empty while `participating_ids` is empty, and the shipped one empties both, so
it cannot separate "no steps" from "no participating steps". The row is still armed on its own
mutation (i), and `test_c3` covers the participation split, so no coverage is lost — but a fixture
cardinality is an assertion wearing a description's clothes (the plan's own S3 lesson, one row
above). Fold into the plan's C2 prose.

**N3 — environment, passing glance.** The Postgres server at `localhost:5433` holds **51 orphaned
`beyo_test_*_template` databases** from prior probe sessions (`r2c*`, `r3s*`, `revm*`, `rr2p*`,
each a full migrated schema). They are not this round's doing and are not test-affecting, but
nothing in the pipeline drops them and the set grows by ~6 per review round.

---

## Mutation-probe declaration

Every probe applied to a working copy and reverted; **all five files md5-verified byte-identical
to their pre-probe values**, `git status --porcelain -- app/` empty, `HEAD` still `22da229`.

| file | md5 before | md5 after |
|---|---|---|
| `services/queries/working_sections/get_working_section_typical_times.py` | `48833e44…bb20` | `48833e44…bb20` ✓ |
| `services/queries/item_economics/get_task_price_scenario.py` | `213a38a0…a16a` | `213a38a0…a16a` ✓ |
| `domain/item_economics/typical_constants.py` | `7a615ece…ea55` | `7a615ece…ea55` ✓ |
| `tests/…/_narrowing_fixture.py` | `0e4f2eab…3d59` | `0e4f2eab…3d59` ✓ (read only) |
| `tests/…/test_narrowed_price_scenario.py` | `577c2097…a48c` | `577c2097…a48c` ✓ |

Probes: **P1** spec-branch clock (`:40`); **P2** P1 + C1(b) repointed to `narrowed_task`/`600`;
**P3** spec-branch `COMPLETED` filter dropped (`:48`); **P3a** `TYPICAL_WINDOW_DAYS = 91`;
**P3b** P3a + C1(i) (`now=` dropped at the `_typical_block` call site). Five shapes, three files,
none previously run by this phase.

**⚠ One state side effect NOT restored.** My runs used `BEYO_TEST_SLOT=rvw`, which created the
template database **`beyo_test_rvw_template`** on `localhost:5433`. I attempted to drop it; the
`DROP DATABASE` was **denied by this session's permission policy**, correctly. It is declared here
rather than worked around — the coordinator or owner can drop it, and it joins the 51 in N3. No
other database or row-level side effect: every DB-backed test in the phase owns its `try/finally`
cleanup and I added no rows of my own.

## Evidence ledger

| # | hypothesis | scope | condition | result |
|---|---|---|---|---|
| P0 | comparator: phase's two files green pre-probe | L1, `-n 0` | host TZ | 67 passed, 3.60s |
| P1 | spec-branch clock defect is guarded by nothing | **L4** | `TZ=UTC`, `-n 6` | 2705/23/1, id delta ∅/+2 (slot-caused) → **bite set ∅** |
| P1′ | the +2 are the slot, not the mutation | L1 | default slot | 50 passed / 1 skipped |
| P2 | the pre-round-4 form catches P1 | L1 | host TZ | **RED at `:127`** |
| P3 | spec-branch SQL break is phase 2's to catch | L1 ×2 | host TZ | phase files 67 passed; phase 2 file 1 failed |
| P3a | window 90→91 is noticed somewhere | L1 | host TZ | 2 failed (phase 2 file) |
| P3b | C1(i) still reaches C1(b) at window 91 | L1 | host TZ | **`test_c1b` green**; only `test_c1a` red |

**Cited, not re-run** (tree identity matches: `22da229`, `app/` clean): the round's stamp
**2707 / 21 / 1**, 21-ID set ∅/∅; C1(i)'s red at `:127`; C8(ii) → `test_c8` alone; C8(i) →
`test_c2d` · `test_c5` · `test_c8`. My single L4 was **variation** (a new mutant shape at a site
no round has probed, under `TZ=UTC`), not reproduction, and it was authorized before the run as an
absence claim.

## Where my evidence ends

- **I did not re-verify**, per the scope fence: the perimeter, the stamp, citation discipline, the
  orphan sweep, §6D compliance, the production code beyond the two cutoff lines and
  `_typical_block`'s statement call, or the graph.
- **B1's absence claim is whole-suite** (`-m 'not e2e'`) at `TZ=UTC` only. I did not run it under a
  second timezone; the mutation removes a clock read rather than changing naive/aware handling, so
  the topology's two-TZ rule is satisfied in spirit by the UTC run, but a second zone is unpaid.
- **`-n 6` parallel for L4, `-n 0` serial for every L1.** I did not run the serial comparator at L4.
- **P3b was measured at L1 on the three C1 rows only.** I did not establish the whole-suite
  consequence of `TYPICAL_WINDOW_DAYS = 91`; P3a's two reds are from one directory, not a survey.
- **N1 and N2 are reasoned from source plus the phase's own runs, not from planted defects.**
  Neither is a claim about what reddens.
- I read `.archgraph/` not at all (D31).

## Lessons for the plans

1. **A "decouple this row from that mechanism" fix must state which branch the row lands on.**
   Round 4's instruction — drive `plain_task`, assert `375` — was executed exactly, and it silently
   changed which of two duplicated `cutoff` lines the phase's only composed clock guard covers. The
   plan reasoned about the *task* (narrowed vs plain) and never about the *statement branch*
   (`specs` vs no-`specs`), which is where the duplication lives. **When a repair changes a row's
   subject, the plan's ledger names the code path the row exercised before and after.**
2. **Two copies of a computation need two guards, or one copy.** `:40` and `:147` compute the same
   cutoff from the same constant in duplicated source. A phase that guards one and not the other
   has covered a line, not a rule.
3. **Rule 13 has a silent-green half.** The known shape is a literal that turns a legal config
   change into a false red. S1 is the mirror: a literal whose drift from the constant turns a live
   guard into a green no-op. Both are "assert the contract, not the literal" — the plan lint should
   flag a test literal computed from a production constant by hand.
4. **The row-that-cannot-fail count for this phase is now seven** — and the seventh (S1) is, again,
   inside a row rewritten to close a previous one. Third occurrence. The pattern is not carelessness;
   it is that each rewrite optimises against the *named* mutation and nobody re-derives what the new
   form can no longer see. **A repair to a guard re-states the guard's full bite set, not the one
   red it was asked to produce.**

## Carry-forward dispositions

| id | severity | disposition |
|---|---|---|
| B1 | blocking | fix round 5 — new statement-level row, declared as candidate criterion C1(d) |
| S1 | should-fix | fix round 5 — derive `frozen` from `TYPICAL_WINDOW_DAYS`, same round as B1 |
| N1 | note | record in plan 5 §6A C1 prose; no row this phase |
| N2 | note | fold into plan 5 §6A C2 row (a) prose |
| N3 | note | owner/coordinator housekeeping; not phase-blocking |
