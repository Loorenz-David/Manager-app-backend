---
plan: 3
role: review
round: 4
verdict: CHANGES_REQUESTED
date: 2026-08-22
actor: Opus 5
---

# Phase 3 review r4 handoff — first external review

## 1. Verdict

**CHANGES_REQUESTED.**

One blocking finding, five should-fix, six notes. The four pending architecture-graph items were
verified and promoted; two needed their evidence addresses corrected first.

## 2. What this review concluded

The parallel test runner works and the safety machinery underneath it is sound — I tried to break
the guard that authorises database deletion at nineteen different address spellings and it refused
every one it should. What is not yet trustworthy is the *proof*: one of the three tests written to
protect the new locking mechanism passes whether the mechanism is there or not, and I showed a
one-line change that removes the protection the plan warned about in writing while all fifty-one
tests stay green. Separately, the published "21 failures" number that three other projects are
about to build on quietly depends on Redis running on this machine, and two documentation surfaces
still tell an operator to run commands that are now unsafe or meaningless under six workers.

Nothing here is a wrong behaviour shipping to users — the code does the right thing today. All of
it is cheap to fix, and none of it needs a redesign. One item needs the owner personally, in the
card below.

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — may a maintenance pass correct the settled architecture records phase 3 moved?

**Question.** Authorise an architecture-graph maintenance session to re-point (and in one case
re-word) the three settled records that phase 3 invalidated — yes or no?

**Story.** Three architecture records were locked in as confirmed fact the morning of the 21st,
each pointing at exact line ranges in the test-isolation file. Phase 3 then rewrote that file and
everything moved by roughly seventy lines. Today one of those records points a future reader at a
completely unrelated function, and another still describes a rule the phase deliberately deleted —
it says the test template is reused when its table *count* matches a fixed number, which was the
brittle constant this whole phase existed to remove. The next agent that reads the graph to plan a
change will be told something that stopped being true yesterday.

**Branches.**
- *Yes* — a maintenance session repairs the addresses and the one stale sentence; the graph matches
  the code again. Costs one short session.
- *No* — the records stay as they are; every future session reading them gets a wrong line range
  and one wrong rule, and the error compounds as the file keeps moving.

**Recommendation.** Yes — the anchor-repair tooling is already enabled in this workspace
(`allowAnchorRepair: true`), so re-pointing is a mechanical, audited operation; only the one stale
sentence needs judgment.

**On silence.** Nothing happens; the records stay wrong and the gate on phase 3 is unaffected.
This does not block the fix round or approval.

**Trace.** Graph items `node:infrastructure-test-database-isolation`,
`node:test-database-isolation-contract`, and the `configured_by` edge between them, all promoted at
revision `f5bf3a7`; review r4 finding N3; prompt §8's out-of-bounds clause.

---

# Layer 1 — technical review

## 3. Findings

### BLOCKING

#### B1 — C2 row (c) cannot fail, and the region-narrowing defect plan task 3 names in writing ships green

**Artifact.** `app/tests/integration/infrastructure/test_database_isolation.py:415-435`
(`test_concurrent_starts_survive_current_template`).

**Authority.** `plans/plan_3.md` §5 C2 (rows and named mutation); §4 task 3 ("The serialised region
is the whole of `_ensure_template` plus the copy — not the `CREATE DATABASE` statement… a guard
around the copy alone leaves the real window open"); charter standing rule 2's companion; charter
standing rule 11; project standing rule 3.

**The defect it would let through.** A future change that narrows the advisory lock so it covers
template provisioning but not the worker copy. That reintroduces the exact failure C2 exists to
prevent — `source database … is being accessed by other users` at worker startup — and no test in
the repository detects it.

**What is wrong.** C2 row (c) specifies its observer as *"a held inspection connection overlapping
a copy."* The implementation holds no connection. It fires two concurrent `start()` calls against
an already-current template and depends on winning a race whose losing side is a sub-millisecond
window. It has now never lost, in two independent runs.

**Mutation M4 — the plan's own named mutation, applied at the definition site**
(`app/tests/database_isolation.py:381-396`, `_template_operation_lock` body replaced by a bare
`yield`):

| C2 row | contract | mutation | result |
|---|---|---|---|
| (a) template absent | green | red, own error | **RED** — `UniqueViolationError: duplicate key value violates unique constraint "pg_database_datname_index"` |
| (b) template stale | green | red, own error | **RED** — `InvalidCatalogNameError: database "beyo_test_p3stale_template" does not exist` |
| (c) template current | green | red, own error | **GREEN — 49 passed, 2 failed** |

C2's named mutation reads *"mutation = each row red **with its own error**, not one shared
string."* Rows (a) and (b) satisfy that exactly. Row (c) does not fire.

**Mutation M5 — the narrowing plan task 3 warns about**, applied at
`app/tests/database_isolation.py:242-245`: the lock kept around `_ensure_template`, with
`_drop_database_if_exists(worker)` and `_create_database_from_template(worker)` moved outside it.

> **Result: 51 passed.** The whole criterion module is green with the copy unprotected.

**The hazard is real and deterministic — proven independently of pytest.** A standalone asyncpg
probe against `localhost:5433`, holding exactly one connection to a template across the copy:

```
RESULT:  copy REFUSED -> ObjectInUseError: source database "beyo_test_p3probe_template"
         is being accessed by other users
         DETAIL: There is 1 other session using the database.
CONTROL: copy succeeded with no held connection
```

So the failure mode row (c) is named for is one line of setup away from being reproducible on
demand; the row simply does not do it.

**Suggested correction.** In `test_concurrent_starts_survive_current_template`, open a connection
to the template (`await _connect(seed._url, seed.template_database_name)`) before
`_assert_concurrent_starts_succeed` and close it after, asserting the copies still succeed. With
the lock present the copy waits behind it and passes; with either M4 or M5 applied it raises
`ObjectInUseError`. One row then covers both the removal and the narrowing.

---

### SHOULD-FIX

#### S1 — C8's skip guard enumerates three of the four spellings of one option, and the published serial comparator false-reds under the fourth

**Artifact.** `app/tests/integration/infrastructure/test_database_isolation.py:110-116`.

**Authority.** Charter standing rule 2 (enumerate, never sample); project standing rule 4
(enumerate sub-checks from the code's branch points, not from the prose); master plan §6.1 and §8.

The guard matches `-n0`, `--numprocesses=0`, and the adjacent pair `-n` `0`. It does not match
`--numprocesses 0` — the space-separated long form of the same xdist option.

**Both sides computed (L1, whole criterion module):**

| invocation | result |
|---|---|
| `pytest <module> -n 0` | 50 passed, **1 skipped** — correct |
| `pytest <module> --numprocesses 0` | **1 failed** — `AssertionError: the shipped default did not reach an xdist worker` |

**Why this one matters more than it looks.** §8's published serial-comparator baseline is
`21 failed / 2575 passed / 1 skipped / 1 deselected`, and that `1 skipped` **is C8**. A consuming
project that spells the comparator `--numprocesses 0` gets `22 failed / 2575 passed / 0 skipped`
and a failing ID that is in neither published set. That is a baseline mismatch presenting as a
parallel-only failure — precisely the class this phase exists to end — reachable today, not on a
future edit. `live_clock` phase 4 and `narrow_typical_work_times` D23 consume this row.

**Suggested correction.** Decide the skip from the option rather than from raw argv spellings. The
repair that also fixes S2: skip when `-n` or `--numprocesses` appears in `invocation_params.args`
**at all**, in any spelling.

#### S2 — C8 hardcodes the worker count OD-10 expects to change (Probe B, confirmed)

**Artifact.** `app/tests/integration/infrastructure/test_database_isolation.py:119-122` — requires
the literal contiguous sequence `["-n", "6", "--dist", "loadfile"]`.

**Authority.** `plans/plan_3.md` §4B (the contract C8 owns is *"the configuration, not the command
line, produced parallelism"*); `planning/intention.md` OD-10 (*"Raising the count later requires a
measurement, not an edit"*).

**Both sides computed (L1, mutation M3 at `app/pytest.ini`):**

| `addopts` | result |
|---|---|
| `-n 6 --dist loadfile` | 51 passed |
| `-n 8 --dist loadfile` — exactly what OD-10 permits | **1 failed** — `shipped parallel default is missing from pytest.ini addopts: ['-ra', '--strict-markers', '--strict-config', '-n', '8', '--dist', 'loadfile']` |

The message is false in every particular: the default is present, it is parallel, and eight workers
genuinely ran (18.97 s, all other rows green). This is the N4 time-bomb shape — a pinned constant
that turns a legitimate change into a red suite with a misleading diagnosis — reintroduced by the
criterion written to protect the default, in the phase that removed the original N4.

**Suggested correction.** Assert the contract, not the number:

1. skip when the invocation args carry any `-n` / `--numprocesses` (this subsumes S1);
2. otherwise assert `addopts` contains `--dist loadfile` and an `-n` whose value is a positive
   integer;
3. and assert `PYTEST_XDIST_WORKER` matches `gw\d+`.

That survives a count change, keeps `--dist loadfile` (which OD-10 calls part of the default, not
an incidental flag), and gives sub-check 3 a mutation the guard cannot short-circuit.

#### S3 — `.env.example` still documents the legacy reclamation sweep as a bare `pytest`, which is now six workers

**Artifact.** `app/.env.example:11-12`:

```
# One-time cleanup of pre-slot test database names, only when explicitly exported:
# BEYO_RECLAIM_LEGACY_TEST_DATABASES=1 pytest -m 'not e2e'
```

**Authority.** Project standing rule 5 — *"An environment variable's documentation surface is part
of its contract"* — earned by OD-7, on this exact file. `plans/plan_3.md` §4 task 9.

Fix r3 corrected the master-plan §6.1 copy of this identical command to `-n 0`. This copy was not
corrected, and it is the operator-facing one: `.env.example` is the file a developer copies and
reads. Task 9's chosen branch was *"document the command as serial-only"* rather than *"exclude the
sweep from non-controller workers"*, and that branch is only sound if **every** documentation
surface says serial-only.

**Failure mode (structural).** Under `-n 6` all six workers reach `_sweep_legacy_databases()`
(`database_isolation.py:240-241`, `:376-379`). `_drop_database_if_exists` checks existence at
`:540`, then calls `inspect()` at `:542`, which opens a connection. A sibling dropping the same
legacy name between those two statements makes `_connect` raise `InvalidCatalogNameError`, which is
not caught, escapes `start()`, and kills the worker at session startup. Fail-fast and noisy, not
silent — but it is the documented invocation of a documented maintenance flag.

**Suggested correction.** `# BEYO_RECLAIM_LEGACY_TEST_DATABASES=1 pytest -m 'not e2e' -n 0`, matching
§6.1 exactly.

#### S4 — the published baseline is a function of Redis availability, and the environment authority states it is not

**Artifact.** `master_plan.md` §6.4, final clause: *"Teardown deletes the process prefix
best-effort: an unreachable Redis produces warnings, not errors, **so the failing-ID set is not a
function of Redis availability**."*

That reasoning holds for `isolated_redis_prefix` (`app/tests/conftest.py:63-87`), which does guard
`redis.exceptions.ConnectionError` in both setup and teardown. It does not hold for the suite:

- `app/tests/integration/services/commands/auth/test_logout_user_integration.py` asserts against a
  live Redis **by name** — `test_floor_logout_blocklist_has_no_ttl_in_real_redis` and
  `test_expiring_logout_blocklist_ttl_in_real_redis`;
- the function-scoped `redis_client` fixture (`app/tests/conftest.py:135-142`) has no
  `ConnectionError` guard in its teardown `scan_iter`.

**Both sides computed (L1):**

| condition | result |
|---|---|
| Redis reachable (`redis://localhost:6379/0`) | **2 passed** in 1.28 s |
| `REDIS_URL=redis://localhost:6399/0` | **2 failed, 2 errors** in 1.47 s |

So a fresh checkout without Redis running gets 23 failures plus 2 teardown errors, not the
published 21 — while §6 instructs consuming sessions to **cite** §6.4 rather than re-derive it.
This is the phase's primary deliverable ("a baseline the rest of the organisation can build on")
carrying an unstated environmental precondition.

**Suggested correction.** Narrow §6.4's clause to what is true (the isolation-prefix teardown is
availability-tolerant; the two logout rows are not), and state "Redis reachable at
`settings.redis_url`" as an explicit precondition on §8's phase-3 baseline row.

#### S5 — §6.1's reversed-collection row now runs under six workers and no longer measures what it is named for

**Artifact.** `master_plan.md` §6.1, row *"full suite, reversed collection"*:
`BEYO_TEST_COLLECTION_ORDER=reverse PYTHONPATH=. pytest -m 'not e2e'` — no `-n 0`, so it inherits
the shipped default.

**Authority.** `plans/plan_3.md` §5 C5, second condition, and projection ledger row L16: *"Under
xdist the execution order is the scheduler's, not the collection list's, so
`BEYO_TEST_COLLECTION_ORDER=reverse` only permutes within a worker's assignment and proves far
less than it did serially."*

The command that was phase 2's serial order-independence probe — and half of phase 2's approval
evidence — is published uncaveated in a form the plan itself says no longer isolates ordering.
Same class as S3: task 10 silently re-pointed an inherited command. This was the specific candidate
review prompt §5.4 named, and it is confirmed.

**Suggested correction.** Add `-n 0` to that row, or caveat it in place citing L16.

---

### NOTES

#### N1 — two named loopback aliases have no criterion row

`_normalised_endpoint` (`app/tests/database_isolation.py:138`) recognises three literal names:
`localhost`, `localhost.localdomain`, `ip6-localhost`. C7's parametrize
(`test_endpoint_aliases_are_confined_to_same_server:300-306`) covers `LOCALHOST`, `::1`,
`localhost.` — exercising the case-folding, the `is_loopback` branch and the trailing-dot strip,
but neither of the other two literals.

**Mutation M6** — both extra literals deleted from the set: **51 passed**. Deleting them is
fail-closed (every drop refuses and the suite cannot start), which is exactly N3's failure mode that
C7 exists to prevent.

**Full boundary enumeration I ran against the guard** (configured `localhost:5433`, target a
`beyo_test_main_gw0` drop):

| target host | normalises to | verdict |
|---|---|---|
| `localhost`, `LOCALHOST`, `LocalHost`, `localhost.`, `localhost.localdomain`, `ip6-localhost` | `127.0.0.1` | allowed |
| `127.0.0.1`, `127.0.0.2`, `::1`, `0:0:0:0:0:0:0:1`, `::ffff:127.0.0.1` | `127.0.0.1` | allowed |
| `0.0.0.0`, `::` | unchanged | **refused** |
| `127.1`, `0177.0.0.1`, `2130706433` | unchanged (not parsed as IPs) | **refused** |
| `host.docker.internal`, `other-host`, `192.168.1.10` | unchanged | **refused** |

The guard is fail-closed at every boundary I could construct, and S2's narrowing of `0.0.0.0` holds
in both the IPv4 and the IPv6-unspecified form.

#### N2 — C3(a)'s sibling-disjointness sub-row cannot fail

`_assert_concurrent_starts_succeed` (`:361-363`) asserts
`len({probe.worker_database_name for probe in probes}) == len(probes)` over hand-constructed
distinct worker ids (`gw900`/`gw901`), so the set can only be smaller if the resolver collapses
them — which is the *other* row's job. The substance of C3(a) is carried by
`test_worker_name_resolution_uses_xdist_worker:103-105`, which does bite on the named mutation
(r1's ledger, and structurally re-derived here). The disjointness line is decoration with a correct
name — worth deleting or re-pointing at the resolver, not worth a fix round on its own.

#### N3 — six settled evidence spans drifted; one is stale on substance

The three items promoted to `human_confirmed` at `f5bf3a7` (2026-08-21 19:07) were confirmed against
the pre-phase-3 tree. Phase 3 then added ~70 lines to `app/tests/database_isolation.py`. Out of
bounds per prompt §8, so **reported, not repaired**:

| item | evidence | recorded | actual today |
|---|---|---|---|
| `node:infrastructure-test-database-isolation` | `DatabaseIsolation.start` | 167-185 | **234-252** |
| — | `_drop_database_if_exists` | 463-489 | **539-565** |
| — | inline: `assert_disposable_database (lines 81-107)` | 81-107 | **148-174** |
| — | `isolated_database` (conftest) | 22-37 | 22-37 ✓ |
| `node:test-database-isolation-contract` | `resolve_worker_database_name` | 46-55 | **103-112** |
| — | `_migrate_and_assert` | 364-414 | **449-490** |
| — | `test_dev_database_counts_are_untouched` | 277-311 | **537-570** |
| `edge:…--configured_by-->test-database-isolation-contract` | `_ensure_template` | 314-343 | **398-428** |

**The substantive one.** That last edge's evidence summary reads: *"An existing template is reused
only when it carries the marker, its Alembic head and **public-table count match the expected
constants**…"*. `_ensure_template:418-423` today checks head, `REQUIRED_PUBLIC_TABLES ⊆
public_table_names(template)`, and the absence of the legacy column — **no count, and no
constants**. Task 6 deleted that mechanism on purpose. An address can be repaired with `anchors`;
a wrong claim cannot, and evidence summaries are immutable, so that one needs reject-and-re-record.
Routed to **owner card 1**.

#### N4 — `app/run_pytest_suite.py` is unreferenced scaffolding that now spawns six workers

`pytest.main(["-x"])` at `:9`, invoked from inside a running asyncio loop, with no marker filter (so
it includes `e2e`). `git grep run_pytest_suite` returns nothing outside the file itself. Pre-existing
dead scaffolding (charter rule 4), but task 10 changed what it does without anyone listing it —
reported under the passing-glance clause.

#### N5 — the perturbation harness ships permanently and no phase owns retiring it

Three probe modules (`tests/connecteam/test_00_…`, `tests/integration/test_50_…`,
`tests/unit/test_zz_…`), the `phase3_collection_probe` marker in `pytest.ini`, and the
`BEYO_TEST_COLLECTION_PROBE` branch in `pytest_collection_modifyitems` are inert by default — which
plan task 1 **required**, so this is not a defect. But nothing schedules their removal, and the
three consuming projects inherit them along with the baseline. Worth a carry-forward owner, not a
fix.

#### N6 — a hypothesis I formed and refuted, recorded because it is settled ground now

I expected `make test-unit` to have regressed: `pytest tests/unit -m unit` inherits `-n 6`, so a
small subset would pay six template copies through one advisory lock. Measured at L2, both sides:

| invocation | result |
|---|---|
| `pytest tests/unit -m unit` (shipped default) | 7 failed / 918 passed in **8.68 s** |
| `pytest tests/unit -m unit -n 0` | 7 failed / 918 passed / 643 deselected in **12.04 s** |

Identical outcomes, and the parallel default is faster on the narrow path too. **Refuted — the
Makefile's four inherited targets are fine.**

---

## 4. Probes A and B, answered by name

### Probe A — "C8's behavioural sub-check may have no mutation" — **CONFIRMED IN PART, REFUTED IN PART**

**Confirmed:** the plan's named mutation never executes the sub-check. M1 — `-n 6` removed from
`app/pytest.ini`, no `-n` on the command line — reddens on the **first** assertion and returns:

```
AssertionError: shipped parallel default is missing from pytest.ini addopts:
['-ra', '--strict-markers', '--strict-config', '--dist', 'loadfile']
```

`PYTEST_XDIST_WORKER` is never read. And the executor's test that the coordinator asked for — M2,
delete the `PYTEST_XDIST_WORKER` assertion and run the shipped default — gives **51 passed**.
Nothing in the module's own run covers it. So the recorded evidence does prove only that the string
check works, exactly as the coordinator suspected.

**Refuted:** the sub-check is **not** inert. It is reachable and it bites. Probe P1 —
`PYTEST_ADDOPTS="-n 0"`, which pytest merges *after* the ini `addopts` (so `numprocesses` becomes 0)
but which never appears in `invocation_params.args` (so the skip guard does not see it):

```
E  AssertionError: the shipped default did not reach an xdist worker
E  assert None
FAILED …::test_shipped_default_reaches_an_xdist_worker
1 failed, 50 passed in 17.30s
```

So C8's second half is a live check with a real defect class behind it — it is the plan's *choice
of named mutation* that is wrong, not the assertion. The repair is not to delete the sub-check but
to name a mutation that reaches it. S1's fix supplies one for free: once the guard skips on any
`-n` spelling rather than on `-n 0` argv shapes, `PYTEST_ADDOPTS="-n 0"` becomes the sub-check's
named mutation with both sides computed above.

### Probe B — "C8 hardcodes the worker count that OD-10 expects to change" — **CONFIRMED**

Verbatim, and measured: see **S2**. Raising `addopts` to `-n 8` — the change OD-10 explicitly
permits — produces `1 failed` with the message *"shipped parallel default is missing from
pytest.ini addopts"*, which is false about a legitimate change while eight workers are demonstrably
running. The coordinator's proposed contract ("skip when `-n` appears in the invocation args at all
and assert only the worker environment") is right and I have adopted it into S2's correction, with
one addition: keep `--dist loadfile` and an `-n > 0` assertion on the ini, because OD-10 states
`loadfile` is part of the default rather than an incidental flag, and dropping the ini check
entirely would let a config with no `-n` at all pass whenever some other route supplied one.

---

## 5. Criteria table

| # | verdict | reason |
|---|---|---|
| **C1** | **met** | Settled ground, cited not re-run: harness collection-neutral by ID count (unset → 2594/0 probes, each position → +1), `n = 3` and positions declared before row 0, rows 0/0b controls present, unstable union empty. No named mutation by design (L4 equality claim); the declared positions are the evidence, and they are declared. |
| **C2** | **partially met — (a) and (b) met, (c) decoration** | M4 at the definition site: (a) red with `UniqueViolationError`, (b) red with `InvalidCatalogNameError`, (c) **green**. Row (c) does not implement its own specified observer (no held connection). M5 — the narrowing task 3 names in writing — is 51 passed. See **B1**. |
| **C3** | **met, one sub-row decoration** | (a) own-name assertions present; resolver observer `test_worker_name_resolution_uses_xdist_worker` bites on the named mutation. The sibling-disjointness line cannot fail — **N2**. (b) module fixture's before/after over owned names, with charter rule 1's exemption invoked in writing. (c) snapshots scoped to this process's own slot/worker names, with a live `gw990` sibling started by the fixture. |
| **C4** | **met, but its record is wrong** | Confirm-and-record executed; `test_default_redis_key_uses_the_process_prefix` cited; no new row written, correctly. The recorded claim about Redis availability is measurably false — **S4**. |
| **C5** | **met** | Settled ground: `comm` empty in both directions on all three L4 runs against the phase-2 21-ID comparator; second condition is a second shipped-default run varying scheduling, not reversal, per L16. The "explained" clause is where **S4** lands: one environmental dependency remains unstated. |
| **C6** | **met — independently verified** | M7, a *different site* from r1's (`migration_head_revision`'s return, not `_migrate_and_assert`'s pin): `test_new_migration_rebuilds_template_without_pinned_schema_count` goes red with `RuntimeError: Migration DDL assertion failed for beyo_test_p3c6_template: expected head c1d2e3f4a5b6, got 'p3c6c72b501d6f'`. The wedge returns exactly as the criterion promises; the head derives from the scripts and the brittle count is gone. |
| **C7** | **met, under-enumerated** | Aliases resolve, a genuinely different host still refuses, `0.0.0.0` and `::` refused. Two of the three named literals have no covering row — M6 leaves 51 green — see **N1**. Full boundary table in N1. |
| **C8** | **met as to its stated defect, carrying two false-red time bombs** | It does catch silent degradation to serial: both sub-checks are reachable and both bite (M1, P1). But its named mutation exercises only the first (**Probe A**), it false-reds on OD-10's permitted count change (**S2**), and it false-reds on an equivalent spelling of the phase's own published serial comparator (**S1**). |

---

## 6. Architecture graph

Owner authority delegated in writing, prompt §8. All four items re-derived from source
independently before any decision, per the operating policy's step 4.

| item | claimed | verified | decision |
|---|---|---|---|
| `node:infrastructure-template-copy-contention-lock` | "Per-slot template-copy advisory lock", scope covers ensure + drop + copy | True. `_template_operation_lock` takes `pg_advisory_lock(hashtextextended(template_database_name, 0))` on a dedicated maintenance connection, yields, unlocks and closes in `finally`; `start():242-245` wraps `_ensure_template` + worker drop + worker copy in it. **Evidence address had drifted**: recorded 344-359 now points at `_marker_present`. Actual span **381-396**. | **promote**, with `anchors` correcting index 0 to 381-396 |
| `edge:…--contains-->…contention-lock` | the lock is contained by the isolation infrastructure | True. `DatabaseIsolation.start` invokes the protected region as one lifecycle step, so the lock is a contained mechanism, not a free-standing utility. **Evidence address had drifted**: recorded 197-209 now points at the `DatabaseInspection` dataclass and `__init__`. Actual span of `start` is **234-252**. | **promote**, with `anchors` correcting index 0 to 234-252 |
| `node:configuration-shipped-pytest-parallel-default` | "Shipped pytest parallel default", `-n 6 --dist loadfile` | True. `app/pytest.ini:2` reads `addopts = -ra --strict-markers --strict-config -n 6 --dist loadfile`; `test_shipped_default_reaches_an_xdist_worker` occupies **108-125** exactly. Both recorded addresses are exact — no correction needed. Type `configuration` is right. | **promote**, no anchor change |
| `edge:…--configured_by-->…parallel-default` | the isolation infrastructure is configured by that default | True, and correctly typed: `configured_by`'s canonical direction is *node → configuration*, and the target is a `configuration` node. Address `app/pytest.ini:1-2` exact. | **promote**, overriding the server's `investigate` suggestion |

**The one override, stated openly.** The server flagged
`conflicting-canonical-relationship` on the fourth item: a `configured_by` edge from
`infrastructure-test-database-isolation` already targets `test-database-isolation-contract`. I
promoted anyway. `test-database-isolation-contract` is itself a `configuration` node, and the two
configure different things — the contract fixes name grammar, template acceptance and the
destructive guard; the new node fixes the worker topology the lifecycle runs under. The schema
declares a canonical *direction* for `configured_by`, not a cardinality, and each edge carries a
distinguishing description. Two configuration nodes legitimately configuring one infrastructure
node is the accurate architecture. The rationale is recorded verbatim in the audit record.

**No item required correction beyond an address, so no second pass was needed** — the immutability
of evidence summaries did not bite this round. Where it *would* have bitten is N3, which is out of
bounds and routed to owner card 1.

**Final state.** Revision **`0dd6785a158409121a63063f3326bbcc440136333db42337a8742b71613463bd`**
(was `2c3f0c58a6…`). **194 nodes, 291 edges, 0 pending reviews, 0 diagnostics**, `staleNodeCount` 0,
`unreadableRecordCount` 0. Audit record at
`.archgraph/reviews/2026-08-22T09-54-23-230Z--78f98a.yml`. Counts are unchanged because all four
items were already in the graph as `ai_inferred`; the promotion changes origin, not topology.

The three items promoted at `f5bf3a7` were not reopened, edited or re-recorded.

---

## 7. Write perimeter

### 7.1 My own writes

| artifact | kind |
|---|---|
| `handoffs/reviewer/2026-08-22_phase3_review_r4_handoff.md` | document (this file) |
| `.archgraph/architecture.yml` | tool-recorded state — four `ai_inferred` → `human_confirmed`, two evidence addresses corrected, prior addresses preserved under `metadata.evidenceHistory` |
| `.archgraph/reviews/2026-08-22T09-54-23-230Z--78f98a.yml` | tool-recorded state — new audit record |

No plan file, no master plan, no intention, no prompt. The Review-log line in `plans/plan_3.md` is
the coordinator's, per prompt §9.

### 7.2 Mutation-probe files — listed separately, all reverted and checksum-verified

Baseline checksums taken **before** the first mutation and re-verified after **every** revert:

| file | SHA-256 (before and after) |
|---|---|
| `app/pytest.ini` | `392e7102e99bb3646e402f7652318dc6e55843afedd75189655e406f2b4414b2` |
| `app/tests/integration/infrastructure/test_database_isolation.py` | `5b78a16a63f8731c6409f752ac679fc2c14c555cee32e1943b6fc87c3f125bc9` |
| `app/tests/database_isolation.py` | `86434edf8eb3efff73e2ad4486967ffc4ba67b8df133b3875bc813336ba6c049` |

These match the checksums fix r3 published for the first two, independently corroborating that the
tree I reviewed is the tree r3 measured. `git status --porcelain` shows **only** the two
`.archgraph` paths from §7.1 — no code path, tracked or untracked.

Mutations applied and reverted, in order: **M1** (`pytest.ini`, remove `-n 6`), **M2**
(criterion module, delete the `PYTEST_XDIST_WORKER` assertion), **M3** (`pytest.ini`, `-n 8`),
**M4** (`database_isolation.py`, `_template_operation_lock` body → bare `yield`), **M5**
(`database_isolation.py`, copy moved outside the lock), **M6** (`database_isolation.py`, two
loopback literals deleted), **M7** (`database_isolation.py`, `migration_head_revision` pinned).

### 7.3 Databases

| database | disposition |
|---|---|
| `beyo_test_p3probe_template`, `beyo_test_p3probe_gw0` | created and dropped by my standalone `ObjectInUseError` probe; cleanup verified empty in the same script |
| `beyo_test_p3absent_*`, `beyo_test_p3stale_*`, `beyo_test_p3current_*`, `beyo_test_p3c6_*`, `beyo_test_main_gw99x` | created and reclaimed by the criterion module's own fixtures across my runs |
| `beyo_manager` | **never a target.** Left at head, untouched |
| `housing_parser_plan1_20260807` | untouched |

Final server state, queried directly: `beyo_manager`, `beyo_test_main_template`,
`housing_parser_plan1_20260807`, `postgres`. **Residue is `beyo_test_main_template` alone**, matching
the settled ground exactly. No temporary Alembic revision file remains in `app/migrations/versions/`.

### 7.4 Evidence

**L4 count: 0.** Against a budget of 0. No full-suite run was taken; the fix-r3 stamp is tree-bound
to my tree (`git diff b96802f HEAD -- app/` empty, verified at gate) and is cited throughout, never
reproduced. No repository-wide absence claim was needed, so no authorization line was written.

Everything else was L1 or L2:

| # | scope | hypothesis | command shape |
|---|---|---|---|
| 1 | L1 | green side | criterion module, shipped default → 51 passed, 19.32 s |
| 2 | L1 | Probe A: can sub-check 2 bite? | `PYTEST_ADDOPTS="-n 0"` → 1 failed |
| 3 | L1 | Probe A: named mutation reaches only sub-check 1 | M1 → 1 failed on the addopts assertion |
| 4 | L1 | Probe A: sub-check 2 uncovered by the module's own run | M2 → 51 passed |
| 5–6 | L1 | S1 both sides | `-n 0` → 1 skipped; `--numprocesses 0` → 1 failed |
| 7 | L1 | Probe B / S2 | M3 (`-n 8`) → 1 failed |
| 8–9 | L1 | B1: C2's named mutation, all three rows | M4 → (a) red, (b) red, (c) green |
| 10 | L1 | B1: is path (c) real? | standalone asyncpg probe → `ObjectInUseError` vs. control success |
| 11 | L1 | B1: does C2 catch the narrowing? | M5 → 51 passed |
| 12 | L1 | N1 | M6 → 51 passed |
| 13 | L1 | C6 named mutation, varied site | M7 → 1 failed with the wedge message |
| 14 | — | N1 boundary table | in-process enumeration of 19 host spellings, no pytest |
| 15–16 | L1 | S4 both sides | logout Redis file, live Redis vs. dead port |
| 17–18 | L2 | N6 both sides | `tests/unit -m unit`, default vs `-n 0` |

Every mutation names its site as file plus definition-vs-call-site: M4 and M6 and M7 are
definition-side; M5 is the call site in `start()`; M1 and M3 are the configuration file; M2 is the
criterion row.

---

## 8. Settled ground consumed by citation, not re-run

Per the charter's test-evidence section and prompt §4, none of this was re-measured, and none of it
contradicted what I found:

- shipped default `21 failed / 2576 passed` (52.62 s, 53.26 s) and `-n 0` comparator
  `21 failed / 2575 passed / 1 skipped / 1 deselected` (150.70 s), all on `b96802f` clean, `comm`
  empty both directions against the phase-2 21-ID set;
- collection 2597 selected, exactly one more than fix r2, that one being C8;
- the perturbation harness is collection-neutral by ID count, gated on the environment variable and
  never on worker identity;
- residue is `beyo_test_main_template` alone — **independently reconfirmed** after my probes, since
  my own writes could have changed it;
- `app/requirements.txt` byte-identical to `c73c017`; `pytest-xdist==3.6.1` pinned only in
  `requirements-dev.txt`;
- `planning/intention.md` byte-identical to `c73c017` plus the coordinator's OD-10 section.

## 9. Verified correct, specifically

Recorded so the re-review is cheap:

- **The advisory lock itself is right.** Cluster-wide `pg_advisory_lock` on a dedicated connection
  keyed per slot template, released in `finally` and released again by PostgreSQL if the holder
  dies; the key is derived from the template name so slots cannot collide; the lock spans the whole
  ensure/rebuild/drop/copy region including the ~1 s alembic subprocess. Both hazard paths a
  concurrent start can actually lose are proven red without it. Only the *test* for the third path
  is missing (B1).
- **The five-step destructive guard holds at every boundary I could construct** — nineteen host
  spellings, Unicode digits, trailing newline, uppercase slot, over-long slot, embedded
  `; DROP DATABASE`, missing username, wrong driver, unparseable URL, the configured database
  itself, and the marker-less-but-populated case. See N1's table.
- **The N4 time bomb is genuinely gone.** Head derives from `ScriptDirectory`; the pinned table
  count is replaced by a derived set with both directions covered by their own rows. C6 bites at a
  site nobody had mutated before (M7).
- **The `0.0.0.0` narrowing from fix r2 held** in both the IPv4 and IPv6-unspecified forms.
- **The Makefile's four inherited targets are fine** under the new default — measured, not assumed
  (N6).
- **The graph delta from all four implementation rounds is additive and accurate**, once two
  addresses are corrected.

## 10. Lessons for the plans (coordinator folds upstream)

1. **A criterion row that names an observer must implement it.** C2(c) named "a held inspection
   connection overlapping a copy" and the implementation substituted "two concurrent starts". The
   substitution passed three coordinator consumptions because the *row* was present and the
   *mutation ledger* reported a green as expected. The plan's own text — "each row red with its own
   error" — was the check that would have caught it, and nobody ran it against the ledger. Consider
   a standing rule: **when a criterion enumerates per-row mutation outcomes, the consuming session
   diffs the implementer's ledger against that enumeration row by row.** r1's ledger stated row (c)
   stayed green, in writing, and it was read four times.
2. **A named mutation must be shown to reach every sub-check, not just to redden the test.** C8's
   two assertions are sequential, so the first one's mutation makes the second unobservable.
   Project standing rule 4 says enumerate sub-checks from branch points; the missing half is
   *enumerate the mutations too*, one per sub-check, and state which bites on which — the rule the
   charter already applies to two tests dividing the labour, applied to two assertions inside one.
3. **A criterion that pins a value the owner may legitimately change is a time bomb regardless of
   what it protects.** S2 is N4's shape reintroduced in the phase that removed N4, by the criterion
   written to enforce the decision that permits the change. Worth a standing rule: **a criterion
   asserting a configured value asserts its contract, not its literal** — a positive integer, not
   `6`.
4. **A shipped-default change has a documentation perimeter, and it is wider than the master plan.**
   Fix r3 found one re-pointed command; this round found two more, one of them in `.env.example`,
   the file OD-7 already taught this project is part of a variable's contract. Consider making
   "enumerate every invocation surface in the repository" an explicit task deliverable for any phase
   that changes `addopts`, with `git grep` output in the handoff.
5. **A published baseline needs its environmental preconditions enumerated, not just its tree.**
   §8's schema is `failure-ID set + tree identity + database identity`. S4 shows a third axis:
   *service* identity. Redis-down changes the number, and the environment authority asserts the
   opposite. Suggest extending §8's baseline schema to name the services that must be reachable.

## 11. Carry-forward dispositions

Not an approval, so this is advisory for the fix round rather than a gate condition.

| item | destination |
|---|---|
| B1, S1, S2, S3, S5 | phase 3 fix r5 — all local, all cheap |
| S4 | phase 3 fix r5 (master plan §6.4 and §8 wording) |
| N1, N2 | phase 3 fix r5 if the round is open anyway; otherwise phase 4 |
| N3 | owner card 1 → an architecture-graph maintenance session |
| N4 | unassigned — pre-existing dead scaffolding, worth a one-line deletion whenever someone is in the file |
| N5 | needs an owner for harness retirement; suggest the phase that closes this project |
