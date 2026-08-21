# Plan 3 — parallelism, and a baseline worth trusting

```
state: NOT_STARTED
hub: ../master_plan.md (tracker §3, environment §6, gates §7, baselines §8)
phase: 3
date: 2026-08-21
actor: coordinator (authoring)
depends_on: plan_2 APPROVED (2026-08-21, `e57ffaf`). Satisfies live_clock phase 4's ⛔ gate.
projection_gate: MANDATORY. Ordering, derivation keys and destructive lifecycle, all at once —
                 charter rule 6 three times over, same as phase 2, whose projection returned 15
                 ledger rows.
```

## 1. Goal

Install `pytest-xdist`, choose a worker count from measurement rather than convention, and
**republish the authoritative failure-ID set under the new runner with every difference
explained.** The intention's deliverables 6–14 land here.

The secondary objective is speed. **The primary objective is a baseline the rest of the
organisation can build on** — `live_clock` phase 4 and `narrow_typical_work_times` D23 consume
whatever this phase publishes, and a fast suite measured against an untrustworthy baseline is
worth less than the slow one it replaced.

**NOT in this phase:** no production domain change. No weakened assertions, no retries, no
`xfail`/`skip` applied to tests that parallelism exposes — the intention forbids each by name.
If parallelisation reveals a real race, ordering dependency or invalid fixture assumption, report
it; fix it only when the correct repair is clear and inside the test-infrastructure perimeter, and
**raise an owner decision rather than improvising** if it needs a production-domain call.

## 2. Read first

1. `../master_plan.md` — **§6 is the environment authority** (commands, topology, the five-step
   invariant, Redis, the schema constants). §5's eight standing rules. §7's gates. §8's baseline
   provenance, which explains why the number is 21 and not 26.
2. `planning/intention.md` — §1 verbatim, especially the **correctness gate** (the list of shared
   resources that PostgreSQL isolation does *not* solve) and the **mutation-testing consequence**;
   §2.2's runner inventory; §3's phase-3 bullet, which carries this phase's first gate.
3. `plans/plan_2.md` §5 C2 — read the **scope correction** appended to it. It is the reason task 1
   exists.
4. `archive/plan_2/2026-08-21_phase2_review_r3_handoff.md` — S5 (object lifetime, not order),
   N3, N4, and lessons 2–4.

## 3. Files expected to change

- `app/requirements*.txt` / dependency manifest — `pytest-xdist`.
- `app/pytest.ini` — only if a default `-n`/`--dist` is adopted; **state it explicitly if so**,
  because it changes what every future bare `pytest` invocation measures.
- `app/tests/database_isolation.py` — template-copy contention (task 3), and N3/N4 (task 6).
- `app/tests/conftest.py` — only if worker-scoped resource isolation requires it.
- `app/tests/integration/infrastructure/test_database_isolation.py` — criterion rows.
- **New:** a perturbation harness for task 1 — location yours, declared in the handoff.
- Nothing under `app/beyo_manager/`. The `config.py` carve-out is spent (OD-7); if you need it
  again, raise a decision card.

## 4. Ordered tasks

### 1. The perturbation gate — before `pytest-xdist` is installed

**This runs first and nothing else starts until it has an answer.** Phase 2 proved the failing-ID
set is invariant under *reversal*. It also produced counter-evidence to the general claim, inside
its own fix-r4 verification: **with eight extra criterion rows temporarily present, the failing-ID
set differed.** That round attributed the extras to "pre-existing order seams" and restored
collection size rather than reporting the divergence.

xdist redistributes every test across processes — a perturbation orders of magnitude larger than
eight rows. Measure parallelism first and the first `-n 4` number mixes two effects, and the new
authoritative baseline inherits both.

**Deliverable:** the set of test IDs whose pass/fail outcome is a function of collection position
rather than of code, **enumerated**, or a demonstration that the set is empty. Insert no-op tests
at several collection positions on the **serial** runner and diff the failing-ID sets against the
published 21. The count and placement are yours; the enumeration is not optional.

Whatever this finds is **reported, not repaired**, unless the repair is obvious and inside the
test perimeter. A phase-2-style repair round here would push parallelism into a fourth phase, and
that is an owner decision, not yours.

### 2. Install `pytest-xdist`, and re-establish serial

Installing a plugin changes collection and reporting even at `-n 0`. **Take a fresh serial stamp
with xdist installed** before any parallel run: that, not the pre-install 21, is the comparator
every parallel measurement is diffed against. Any difference between pre-install and
post-install serial is a finding to explain — the plugin should not change outcomes, and if it
does, that is the most important thing this phase will discover.

### 3. Template-copy contention — the hazard that only exists once workers do

`CREATE DATABASE … TEMPLATE …` **fails while any other session holds the source database open.**
Phase 2's projection recorded this (ledger row L15) as undecidable serially and routed it here.
With N workers starting at once, worker 2's copy can collide with worker 1's connection to the
template, and the failure surfaces as a startup error that looks like flakiness.

Solve it deliberately — serialise template access, retry with backoff, or build per-worker
templates — and say which and why. **Do not discover it as an intermittent failure during the
matrix**; it will be attributed to the wrong cause.

### 4. Shared resources that PostgreSQL isolation does not cover

The intention's correctness gate names them: execution order, module/session-scoped mutable
state, shared filesystem state, fixed ports, **Redis**, background workers, global caches,
environment mutation, timestamps, unique constraints, and processes outside pytest. Its closing
sentence is binding:

> *Per-worker PostgreSQL isolation solves only PostgreSQL interference. Do not infer that the
> entire suite is parallel-safe merely because the DB is isolated.*

**Inventory them against this suite**, state which are actually reached, and isolate or declare
each. Redis already has a per-process prefix (master plan §6.4) — confirm it holds per *worker*,
since workers are separate processes and that is the same seam, not a new one.

### 5. The measurement matrix, and a conservative default

Serial, `-n 2`, `-n 4`, and a higher count if useful and safe (the machine has **14 cores**).
Per run record: wall-clock, pass/fail counts, worker count, distribution mode, any new or flaky
failures, PostgreSQL or resource problems, and whether the failing-ID set differs from the serial
comparator.

**Start with `--dist loadfile`**, which keeps a file's tests on one worker so file-local ordering
survives; treat any move to finer distribution as a **separate, measured step** with its own row,
not a tweak. Choose a conservative default if more workers bring diminishing returns or
contention — `-n auto` is not assumed optimal.

### 6. The two carried code items

- **N4, the time bomb.** `EXPECTED_HEAD = "c1d2e3f4a5b6"` and `EXPECTED_PUBLIC_TABLE_COUNT = 107`
  are hardcoded, so the next Alembic revision makes `_ensure_template` rebuild and
  `_migrate_and_assert` raise `RuntimeError` — **the suite wedges until a human edits the file.**
  This phase owns the template lifecycle; derive both from the repository rather than pinning
  them, or state why pinning is right and make the failure message say what to do.
- **N3.** `_normalised_endpoint` maps only the literal string `"localhost"`. `LOCALHOST`, `::1`,
  `0.0.0.0` or a hostname alias mismatch and make **every** drop refuse, so the suite cannot
  start. Fail-closed and therefore safe, but the failure mode is total and the diagnosis
  non-obvious.

### 7. The deliverables the intention asks for by name

A **before/after table** covering full-suite wall time, databases used, persistent test residue,
failure count, failing-ID set and worker count; and the actual database lifecycle **as a
diagram**. These are deliverables 8, 9 and the closing request of §1 — not optional decoration.

## 5. Acceptance criteria

Each names the defect it would catch and carries a named mutation with both sides computed and
its site named. No criterion asserts documented third-party behaviour — that xdist distributes
tests, or that PostgreSQL copies databases, is not this phase's to prove.

- **C1 — collection-position sensitivity is enumerated, not assumed away.**
  *Defect:* a parallel measurement that attributes to xdist an order sensitivity that was already
  there, permanently corrupting the baseline three other projects consume.
  *Contract:* for each probe position, the failing-ID set is stated and `comm`-diffed against the
  published 21 in both directions. The deliverable is the **union of IDs that ever differ**,
  enumerated — empty is a valid and welcome answer, but it must be measured, not inferred from
  the reversal result.
  **No named mutation** — an equality claim over the whole suite under several conditions, L4 by
  construction. The enumerated positions *are* the evidence.

- **C2 — concurrent worker startup does not collide on the template.**
  *Defect:* `CREATE DATABASE … TEMPLATE` fails while another session holds the source open, so
  the run dies at startup intermittently and the cause is attributed to parallelism in general.
  *Rows:* N workers starting simultaneously all obtain their database; the template survives; a
  deliberately-held connection to the template does not wedge a starting worker.
  **Named mutation, site named:** remove whatever serialisation/retry task 3 adds ⇒ contract =
  all workers start, mutation = at least one fails with `source database … is being accessed by
  other users`, red.

- **C3 — worker databases are disjoint, and all are reclaimed.**
  *Defect:* two workers sharing a database — cross-talk indistinguishable from a race, which is
  the exact failure this whole project exists to prevent.
  *Rows:* under `-n 4`, four distinct `beyo_test_<slot>_gw0..gw3` exist **during** the run; after
  it, server membership is identical to before.
  **Named mutation, site named:** make the resolver ignore `PYTEST_XDIST_WORKER` ⇒ contract = four
  distinct names, mutation = one name four times, red.

- **C4 — every worker process gets its own Redis namespace.**
  *Defect:* workers sharing rate-limit, auth and activity keys — interference that looks like a
  race and that PostgreSQL isolation cannot touch.
  *Row:* under `-n 2`, the two workers observe different `settings.redis_key_prefix` values, and
  neither is the shipped default.
  **Named mutation, site named:** remove the per-process component of the prefix ⇒ contract = two
  distinct prefixes, mutation = one shared prefix, red.

- **C5 — the parallel failing-ID set equals the serial one, or every difference is explained.**
  *Defect:* a baseline that silently absorbed a parallelism-induced failure, making every future
  mutation measurement meaningless. *"A mutation is only meaningful relative to a trustworthy
  baseline."*
  *Contract:* at the chosen default, the failing-ID set is `comm`-diffed both directions against
  the **post-install serial** comparator. Any difference is **explained with evidence, never
  updated into the baseline** — and per standing rule 7, a single-occurrence difference triggers
  **re-measurement, not attribution**. Phase 2 lost a round to a difference labelled "known" and
  part of another to one labelled "pre-existing order seams".
  **No named mutation** — L4 by construction.

- **C6 — the schema constants cannot silently wedge the suite.**
  *Defect:* the next Alembic revision makes the template rebuild and `_migrate_and_assert` raise,
  stopping every run until a human edits a constant — with a message that does not say so.
  *Rows:* with a new revision applied, the template rebuilds and the suite runs; if the phase
  keeps the constants pinned instead, the failure names the file and the value to change.
  **Named mutation, site named:** point `EXPECTED_HEAD` at a stale revision ⇒ contract = the run
  proceeds (or fails with an actionable message naming the fix), mutation = today's opaque
  `RuntimeError`, red.

## 5A. Traps this plan inherits

- **All of plan 1 §5A and plan 2 §5A still apply.** Assert DDL, never a migration's exit code.
  Compute both sides of every fixture before choosing it. Report dead scaffolding rather than
  deleting it silently.
- **Standing rule 7 is the one this phase will be tempted to break.** A single new failing ID
  under `-n 4` will look explainable. Re-measure it; do not name it.
- **Standing rule 8.** Your closing stamp is defined by the tree you hand over. If you change
  anything after stamping, the stamp is void and re-taking it is **not** over-budget.
- **Do not restate the environment.** Master plan §6 is the authority; two rounds have already
  restated it inconsistently into prompts. Cite it.
- **The topology-fold trap.** Phase 2 folded new criterion rows into existing tests to keep
  collection size constant, which preserved comparability and cost attribution — a driver check
  now reddens through a test named for unmarked databases. **Do not let measurement convenience
  drive test design.** If adding rows perturbs the baseline, that is task 1's subject, not a
  reason to avoid adding rows.
- **S5's class.** One test's outcome was a function of object lifetime, not order: 13 test files
  create a second session and the repository carries 89 `refresh()` calls. Under workers, that
  class gets a new axis.

## 6. Evidence budget

This phase is a measurement matrix, so **the matrix is the budget** (charter: "a phase whose own
criteria enumerate L4 measurements states that enumerated matrix as its budget"). Each row is a
distinct condition and therefore variation, not repetition.

| # | run | purpose |
|---|---|---|
| 1–n | perturbation probes, serial, pre-install | task 1 / C1 — `n` is yours, declared before you start |
| — | the published `21 / 2561 / 1` at `11b4d02` | the control, **cited not re-run** |
| n+1 | serial, xdist installed | the comparator every parallel run is diffed against |
| n+2 | `-n 2 --dist loadfile` | matrix |
| n+3 | `-n 4 --dist loadfile` | matrix |
| n+4 | higher count, if useful and safe | matrix |
| n+5 | the chosen default, on the tree you hand over | **the mandatory closing stamp** |
| n+6 | `BEYO_TEST_COLLECTION_ORDER=reverse` at the chosen default | C5's second condition |

Declare `n` in the handoff **before** the first run. Anything beyond the enumerated matrix needs
the charter's authorization line, written before it. Everything else is L1/L2.

**State your total L4 count as a number.** Two reviewers spent effort disambiguating a previous
round's prose; it should have been one line.

## 7. Review log

*(empty — this plan has not been implemented)*
