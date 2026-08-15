# Migration squash — research context & findings

```
project: squash_migrations (NOT STARTED — deliberately deferred)
seeded: 2026-08-13, by the item-cost pipeline coordinator at the owner's request
status: research deposit only; no intention, no plans, no prompts yet
gate when started: charter flow — intention → mechanism-inventory → plans
```

## Why this project exists (owner's motivation, 2026-08-13)

The migration chain is piling up and **slowing daily development**. The owner
will consolidate ("squash") the migration history into a fresh baseline.

## Timing decision (owner, 2026-08-13)

**After the item-cost implementation is fully complete and stable** — not
between its phases. Justification:

- The item-cost pipeline's environment facts (master plan §10), its baseline
  evidence, and its disposable-DB recipes all reference the current chain and
  head. Squashing mid-pipeline forces a re-verification of that environment
  while phases are in flight; after v1 it is a single clean cut with nothing
  in flight.
- The production database is **already built and at head**; no fresh
  production build is planned. Nothing about the current chain is urgent for
  production — the cost is developer time only.

## The hard evidence this project inherits (do not re-derive — cite)

All of this was proven during item-cost phase 4B (2026-08-13). Primary
sources, in order of value:

1. **The 4B review r1 handoff** —
   `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-13_phase4b_review_r1_handoff.md`
   (after 4B closeout it moves to `…/item_cost_calculation/archive/plan_4b/`).
   Its "OD-1 probe outcomes" section is the transaction-mechanism map.
2. **Owner decisions OD-1 and review-r1 card 1** —
   `…/item_cost_calculation/planning/owner_decisions.md` (tail sections).
3. **Master plan §10** — `…/item_cost_calculation/master_plan.md`, the
   from-scratch recipe entry (CORRECTED 2026-08-13) with its history note.

### Finding 1 — Alembic transaction handling in `env.py` is accident-shaped

Mechanism (reproduced, not theorized — reviewer P4B-0a):

- `_cold_build_workspace_callbacks(connection)` runs a **preflight SELECT**
  before `context.configure()`. SQLAlchemy autobegins an implicit transaction
  on that SELECT.
- `MigrationContext` therefore sees `_in_external_transaction = True`, and
  **every** `begin_transaction()` — outer and per-migration — returns
  `nullcontext()`. Alembic assumes the caller owns the transaction and never
  commits; the connection close at the end rolls everything back.
- Result before 2026-08-13: `alembic upgrade` could exit **0** while
  persisting **neither the revision nor the DDL**.

### Finding 2 — two historical migrations masked Finding 1 for months

`6787eabf4c32` and `7a3e91c4b2d8` issue raw `op.execute("COMMIT")` to build
indexes `CONCURRENTLY`. Any run that passes through them gets its accumulated
work committed **out from under Alembic** — which is why full from-scratch
builds and long warm upgrades "worked" while a single-step warm upgrade of a
new migration (4B's) was the first to expose the defect. **A squash removes
these masks**: whatever transaction handling the squashed `env.py` has must
be correct on its own, because nothing will accidentally commit anymore.

### Finding 3 — the two patches now in `env.py` (both owner-authorized)

Current state (hash `09261d91c7813483…` at 4B fix-r1, `8285cf1`):

- **OD-1 rollback** (implement r1): `connection.rollback()` right after the
  cold-build callbacks — clears the preflight's implicit transaction so
  Alembic's per-migration boundaries are real. Proven load-bearing (P4B-0a
  reproduced without it).
- **B1 cleanup commit** (fix r1): `connection.commit()` as the last statement
  of `_do_run_migrations()`'s `finally` — the cold-build cleanup DELETEs
  otherwise autobegin a fresh transaction nothing commits, and every fresh
  build ships a ghost "Migration workspace" + 7 pause reasons (C9 criterion
  + §10 evidence: clean end-state now verified by state queries, 1.70s).

**Squash decision to make:** in a squashed world with no cold-build
machinery, both patches may become unnecessary — but that must be a
deliberate decision with a state-asserted test, not an inheritance. See
lesson P-Z / L5 below.

### Finding 4 — what a squash deletes outright

- The **cold-build workspace machinery** in `env.py`
  (`_cold_build_workspace_callbacks`: transient workspace for the historical
  pause-reason migrations + cleanup). Gone entirely in a squashed baseline.
- **N6 (open defect, routed to migration-infra owner, deliberately unfixed):**
  a cold build targeting a revision BELOW the pause-reason migrations crashes
  in cleanup (`UndefinedTableError: relation "pause_reasons" does not exist`
  — the anchor is created at `a1312183fdfb`, the table arrives later). Moot
  after a squash; this is a reason NOT to fix it separately beforehand.
- The **owner-authorized acyclic-graph metadata edit** (`8cf57fa23110`,
  phase-2 maintenance): the on-disk revision graph had a genuine CYCLE,
  repaired by a one-line metadata correction. A squash supersedes it; the
  squashed chain must be verified acyclic by construction.
- The per-migration idioms that only matter historically: the journaled
  data-migration exemplar (`97b60e06d42a`), the report-and-refuse pre-flights
  (4B's `5caae620088c` included), reused-enum `create_type=False` sites.

### Finding 5 — constraints the squashed baseline must honor

- **Production is at head and stays there.** The squash must be
  stamp-compatible: the baseline revision's schema must equal the live
  production schema byte-for-byte (the phase-2 arbiter exists:
  `compare_metadata(compare_type=True)` — but note P-X, it is BLIND to
  partial-index predicates, `server_default` expressions and comments; those
  need explicit structural checks, the 4B S1 lesson).
- **Enum type ownership:** today `item_major_category_enum` is created by
  `item_categories.major_category` and REUSED (`create_type=False`) by
  `production_cost_groups.major_category`. In a squashed baseline each type
  is created exactly once — ownership must be restated, and the "exactly ONE
  pg_type row" arbiter (4B C1) re-asserted.
- **Partial-unique idioms:** `uix_*` via `postgresql_where`
  (idiom `595e7b840926`) — the squash carries them all; the §6.2 registry in
  the item-cost master plan is the closed inventory for the economics tables.
- The item-cost §10 recipes and environment facts reference the current head;
  after the squash they need ONE re-verification pass (state-asserted — L5:
  never record an environment fact from an exit code).

### Standing lessons that bind this project (earned the hard way)

- **P-Z:** any change to shared migration machinery carries a before/after
  property test in the same cycle — name the property the machinery had,
  re-assert it after. (OD-1 fixed persistence and silently broke cleanup;
  only a hand-written probe caught it.)
- **L5 / §10 rule:** environment facts recorded from a command's exit code
  need a **state assertion** behind them. The old "verified twice"
  from-scratch claim was never true — the runs persisted nothing.
- **P-X:** name what a verification harness can actually SEE
  (`compare_metadata` blindness classes).
- **Charter rule 7:** destructive verification on disposable databases only;
  the configured/production DB is never the test bench.

### Finding 6 — the phase-6 journal table must be dropped/excluded at squash
(added 2026-08-14, phase-6 projection r0)

Phase 6 ships `item_valuation_migration_journal` solely to make its data
migration reversible. After the squash the data-migration file is gone and the
journal has no reader — the squashed baseline must **drop or exclude** it, and
nothing else will flag it: `env.py`'s `_MIGRATION_BOOKKEEPING_SUFFIX` filter
(`:30`, `:33-48`) deliberately hides `*_journal` tables from autogenerate (a
rename would also silently forfeit that protection). Until the squash lands,
the journal is the only recovery path for legacy amounts.

## Suggested opening move (when the owner starts this)

Author a **mechanism-inventory prompt** citing this document and the three
primary sources above. Its job: enumerate the full migration surface (count,
data-migrations vs DDL, raw-COMMIT sites, enum creations, cross-database
assumptions), decide the baseline strategy (single baseline revision +
`alembic stamp` on existing DBs vs. keep-tail-squash-head), and decide the
squashed `env.py`'s deliberate transaction shape. Gate: the item-cost
pipeline is COMPLETE and stable, per the timing decision above.

## Finding 7 (2026-08-15, phase-8 closeout)

Phase 8 added one migration AFTER the drop head:
`c1d2e3f4a5b6_add_process_item_cost_result_task_type.py`
(`ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS
'process_item_cost_result'`; downgrade is an honest no-op — PostgreSQL
cannot drop enum values). The squashed baseline must create
`task_type_enum` WITH this label included; the chain to collapse now ends
at `c1d2e3f4a5b6`, not `be9dfe42a035`.

## Finding 8 (2026-08-15, phase-9 projection F11)

Phase-2 review N4 wanted `checkfirst=True` removed from the five enum
creations in `90cdd23a828e_item_economics_schema.py:53-57` so a pre-existing
type fails loudly instead of being silently adopted. UNDISCHARGEABLE on the
live chain (applied migration; charter rule 7; the five types already
exist, so the posture can never fire again). Closed WONTFIX in phase 9's
Review log. **Squash consequence:** the squashed baseline creates the enum
types WITHOUT `checkfirst=True` — the loud-failure posture N4 wanted is
free at squash time.
