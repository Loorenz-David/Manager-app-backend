---
plan: plan_1
role: implementer
round: 3 (fix cycle)
date: 2026-08-22
---

# Fix prompt — plan 1, round 3 (review findings)

The reviewer confirmed the engine's **behaviour** is right at every site it checked, and
that the frozen SQL snapshot is genuinely pre-refactor. What failed is the test layer over
`reconcile_task_typicals`: three separate defects — each one a false statement on the wire
in phase 4 — leave the phase suite at **33 passed**. The reviewer measured all three.

This cycle is **mostly tests, plus one small production fix** (F3, the parser). Two
blocking, three should-fix, four recorded — all nine are in scope here.

Read `/Users/davidloorenz/agent-skills/pipeline-charter.md` and
`/Users/davidloorenz/agent-skills/implementation-executor.md` first. Repo:
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`, branch
`main`. **Never push.** Explicit paths only.

**The plan is already amended** — `plans/plan_1.md` C4(c), C7, C8, C14, C15 and C17 now
carry every row and named mutation below. Build to the plan; this prompt explains *why*
each one exists so you can tell a real failure from a bookkeeping one.

## Write perimeter

- `app/tests/unit/domain/item_economics/test_typical_filters.py`
- `app/beyo_manager/domain/item_economics/typical_filters.py` — **F3 only** (the parser's
  `_optional_values`). No other production edit.
- **One new test file** for the package-purity guard (F6). Name it to mirror what it
  guards, e.g. `app/tests/unit/domain/item_economics/test_domain_purity.py`; master plan
  §5 records the mirror-rule deviations already taken, so if you deviate, say so.
- `plans/plan_1.md` (Review log) and `master_plan.md` (tracker row 1).

Anything else is a finding.

## F1 (blocking) — C8 row (g): the task-scope short-circuit has no test that can fail

`reconcile_task_typicals` carries its **own** copy of the narrowing decision
(`typical_filters.py:265-269`), separate from `resolve_section_typical`'s. Nothing
constrains it: the phase never calls `reconcile_task_typicals` with a **non-`None`,
non-narrowing** spec. Row (i) does not cover it — `spec is None` is false there by
construction.

Measured by the reviewer: mutate line 266, `effective_spec.is_narrowing` →
`(spec is not None)`. Contract on `reconcile({"a": E(600, 7, 900, 61)},
TypicalFilterSpec(), {"a"}, {"a"})` → `section_wide_uniform`, `applied_filter None`,
`a = (900, "section_wide", 61)`. Mutation → `item_narrowed_uniform`, `applied_filter`
**still `None`**, `a = (600, "item_narrowed", 7)`. **33 passed.**

Intention §3B B1 names that output as the defect it forbids — *"`item_narrowed_uniform`
for a task whose `applied_filter` is `null`. Both are false statements on the wire."* It
is one of the five Critical-ranked mechanisms.

Add row (g) with `spec=TypicalFilterSpec()`, every participant usable-narrowed. Assert the
task basis, `applied_filter is None`, and each participant's full tuple. Register the
mutation above as C8 mutation (0); row (i) is its recorded non-biting control.

## F2 (blocking) — C8's per-section tuple assertions, the branch nothing asserts

C8's closing sentence mandates exact-literal assertions on **each section's**
`(typical_worker_seconds, typical_basis, sample_count, participates)` tuple. In the tree
only the ghost row gets per-section assertions. **No test asserts what a *participating*
section publishes when the task basis is `section_wide_uniform`** — the branch at
`typical_filters.py:285-297`.

Two mutants, both measured green on row (b)'s own fixture:

| mutant (`reconcile_task_typicals` definition) | contract | mutation |
|---|---|---|
| line 288 `section_typical_worker_seconds` → `narrowed_typical_worker_seconds` | zero `(900, section_wide, 61)`, usable `(1200, section_wide, 61)` | zero **`(0, section_wide, 61)`**, usable `(600, section_wide, 61)` |
| line 296 `section_sample_count` → `narrowed_sample_count` | both `sample_count 61` | zero `5`, usable `7` |

The first is §3.6's naming rule and §3B B2 violated directly — a narrowed value wearing a
`section_wide` label — and in row (b) that value is **`0`**: the D25 defect re-entering
one layer below the predicate built to prevent it. The second is §3B B3, which exists
*precisely because* participating sections bypass `resolve_section_typical`.

Implement the closing sentence for rows **(a), (b), (e), (f), (j)** — full tuple, every
section named, participating ones included — and register the two mutants as C8 (viii)
and (ix).

## F3 (should-fix, **the one production change**) — the parser silently mis-reads a bare string

`_optional_values` (`typical_filters.py:78-82`) does `frozenset(str(v) for v in raw)`. A
`str` **is** a `Sequence[str]`, so it iterates character-wise. Measured, no mutation
required:

| input | today |
|---|---|
| `{"item_category_ids": "cat_a"}` | `frozenset({'c','a','t','_'})` — a narrowing spec over **zero** items |
| `{"designers": "dsg_a"}` | `frozenset({'d','s','g','_','a'})` |
| `{"item_category_ids": 5}` | bare `TypeError` → HTTP 500 |
| `{"major_categories": 5}` | `ValidationError` → HTTP 422 |

The first two are HC-3's shape reached through the parser: a spec narrowing to nothing,
which `BROADEN_TO_SECTION` answers section-wide with no signal. The last two are §3C's
boundary applied to one family and not the others.

Nothing ships broken today — the route is deferred and has no caller — but §3C binds this
parser now and phase 2 inherits it as a public contract. **Fix:** reject `str`/`bytes` and
any non-iterable in `_optional_values` with `ValidationError`, symmetric with the enum
family. Intention §3C and master plan §6.8 are already amended. Add C14 rows (o), (p),
(q) and the named mutation the plan now records.

## F4 (should-fix) — C7 row (n): no row can tell `has_section` from `has_narrowed`

Rows (h)/(m) set the two populations equal by construction; row (i) makes both predicates
`False`. Measured: mutate `typical_filters.py:172`, `evidence.has_section` →
`evidence.has_narrowed` → **33 passed**.

Add row (n): non-narrowing, narrowed `(61, 600)`, section `(3, None)`, BROADEN →
`("insufficient_sample", None, 3)`. Under the mutant it becomes `("section_wide", None, 3)`.
(SQL-impossible, dataclass-permitted — the totality standard C7 already states.)

## F5 (should-fix) — C7 rows (h)/(m) assert three of six fields

T17's claim is that the two policies return a **byte-identical `SelectedTypical`**; the
test asserts a 3-tuple. Measured: set `participates=True` in both returns of the
non-narrowing branch (`typical_filters.py:178,186`) → **33 passed**. The field survives
only because `reconcile_task_typicals` overwrites it at the sole call site; a phase-2+
consumer calling `resolve_section_typical` directly inherits an unconstrained field.

Assert the **entire dataclass** on rows (h) and (m) — all six fields. Keep the 3-tuple for
the other rows; the parametrised test can carry both shapes.

## F6 (recorded → now in scope) — C4(c) and C17 ship as committed tests

Both are absence criteria satisfied today by a grep someone ran in a session. Charter
rule 1: acceptance criteria are met by automated tests; the exemption is
environment-lifecycle checks only, and these are not. Nothing in the suite goes red if a
later phase adds `hashlib` or a `models.tables` import — and phases 4 and 5 **do** touch
this package.

Write one test module that walks every `*.py` under
`app/beyo_manager/domain/item_economics/` and asserts two term sets:

- **C17:** no `sqlalchemy`, no `models.tables` import. Currently clean — the reviewer
  re-measured.
- **C4(c):** none of `hashlib`, `sha1`, `sha256`, `md5`, `fingerprint`, `digest`, with
  **one named, asserted exception**: `serializers.py`'s pre-existing `config_fingerprint`
  (a price-scenario *configuration* fingerprint, unrelated to spec identity). Pin it by
  name so that removing it does not silently widen the claim and a *second* fingerprint
  anywhere in the package reddens.

Mutations: add `import hashlib` to `typical_filters.py` (C4(c) reddens); add
`from beyo_manager.models.tables.items.item import Item` (C17 reddens).

## F7 (recorded) — C8 row (c), bookkeeping only

Row (c) (A below floor, B usable → `section_wide_uniform`) has no two-participant
fixture. It is the recorded **non-biting control** for C8 mutation (ii), not a detection
gap — mutation (ii) still bites on row (b). Add the fixture so the plan and the tree
agree; if you judge it genuinely redundant, say so in the handoff instead of adding it.

## Already folded by the coordinator — do not re-do

- **S3** (the snapshot freezes structure, not values — `percentile_cont(0.5)` → `0.6`
  leaves the string byte-identical): recorded in `plans/plan_2.md` C1 and master plan §9.
  **No phase-1 change.** It is a property of the instrument, not a defect here.
- **N3** (C8 mutation (vii) bites on a different row than the plan named), **N4** (keep
  the single-cause ghost row beside its two-cause twin), **N5** (`IS false`, not
  `= false`): all corrected in `plans/plan_1.md`.

## Evidence budget

- Every named mutation above runs at **L1 whole-file scope** on the phase's test files —
  never `-k`. The reviewer's baseline is **33 passed**; state your new count.
- **One L4 stamp** closes this cycle (`PYTHONPATH=. pytest -m 'not e2e'` from
  `backend/app/`), on the tree you hand over, with the failing-ID delta against the 21-ID
  comparator in both directions. Check Redis first — without it the suite reads 23/2, not
  21. The `TZ=UTC` obligation is already discharged for this phase; the ordinary host
  timezone is fine.
- F3 changes production code, so **no earlier stamp carries over**.

## Closing protocol

Checkpoint commit (`CHECKPOINT (not approved): `, explicit paths, never squashed, never
pushed). Update `plans/plan_1.md` Review log and `master_plan.md` tracker row 1. Handoff
at `handoffs/implementer/20260822_plan1_fix_round3_handoff.md`, frontmatter `plan`,
`role`, `round: 3`, `date`, `actor`; body: owner-readable opening, the F1–F7 ledger with
both-sides mutation results, the L4 stamp, the full write perimeter from `git status`,
and the checkpoint SHA. Final chat message is the charter's owner layer.
