---
plan: phase 7 (evaluations — commit/supersede, projections, auto-commit)
role: projection
round: 0
verdict: AMENDMENTS_REQUIRED
date: 2026-08-14
actor: reviewer (projection r0)
---

# Phase 7 projection — round 0 handoff

## Opening (owner-readable)

Phase 7 is the piece that actually decides what a chair may cost to make and freezes
that decision. I did the implementer's first hour on paper and the plan does not yet
survive it: the plan was written on 11 August, before four later phases shipped and
before six rounds of decisions changed the rules underneath it. Twenty-three points
need settling before anyone writes code — twelve of them would otherwise ship as
silent defects, including one where saving a corrected price at the same moment as a
budget decision would quietly put the old price back with no error anywhere. I have
proposed the fix for each and verified them against the real database and the real
code, so most are paragraph edits rather than rework.

One question needs you personally: whether committing a price decision should appear
in the activity history everyone reads on a task, or only in the admin audit trail.
Everything else is technical and goes to the coordinator. The gate holds until the
ledger is routed; no implementer prompt should be compiled before then.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — Should a committed budget show up in the task's activity history?

**Question.** When someone commits an economic decision for a task, should that appear
in the task's activity history (the timeline the whole team reads), or only in the
admin audit log?

**Story.** Anna commits a budget for chair #412 on Monday: 4 000 kr sale price,
92 allowed worker-minutes. On Thursday the chair has overrun and Björn opens the task
to find out what happened. If the commitment is in the activity history he sees "Anna
set the production budget, Monday 09:14" between the assignment and the first step,
and the conversation is over in ten seconds. If it lives only in the audit log, the
task's timeline shows the chair moving through production with no trace of the
decision that constrained it, and someone has to ask an admin.

**Branches.**
- **Activity history (+ audit).** Everyone on the task sees who decided the budget and
  when; costs one small database change to add "evaluation" to the list of things the
  history can point at.
- **Audit log only.** Nothing new in the timeline; the record exists but only admins
  can reach it; no database change.

**Recommendation.** Activity history — the whole point of a committed decision is that
it is answerable later, and the audience that needs the answer is the team on the task,
not an auditor.

**On silence.** The gate holds; no implementer prompt is compiled. Nothing is guessed.

**Trace.** intention §7.2 step 5, §7B.1 step 9; master plan §6.4 audit vocabulary;
plan criterion C10; ledger D8.

---

## Environment and live measurements (verified in this session, 2026-08-14)

| Fact | Prompt said | Measured | Note |
|---|---|---|---|
| Alembic head (dev DB) | `be9dfe42a035` | `be9dfe42a035` (`alembic current` → "(head)") | matches |
| git HEAD | — | `133590c` | the projection-prompt commit |
| `item_cost_evaluations` rows | 0 | **0** | also 0: eval terms, valuations, groups, basis versions, model versions, results |
| Archgraph | 156 nodes / 201 edges, rev `53261a23…`, 2 pending | **155 nodes / 200 edges**, rev `53261a232cafa5a3…`, **2 pending**, 0 stale | revision and pending count match; the counts in the prompt are one high on each — recorded, not acted on |
| PostgreSQL | — | **18.4** | `ALTER TYPE … ADD VALUE` is available and has five in-tree precedents (D8) |
| `history_record_entity_type_enum` labels | — | **8**: item, item_upholstery, item_upholstery_requirement, task, case, user, task_post_handling, task_customer_coordination | **no evaluation member** (D8) |
| `_common.py::INDEX_IDENTITIES` | — | **8 entries**, no `uix_item_cost_evaluations_current` | (D2) |
| `production_cost_groups` INV-G3 index | — | present: `uix_production_cost_groups_major_category_active` on (workspace_id, major_category) WHERE `is_deleted = false` | makes C6's 2-group row unreachable (D11) |

**Citation checks (all three plan-cited precedents re-verified against the current tree):**
- `services/commands/users/reconcile_worker_shift_state.py:278` — `async with session.begin_nested():` — **exact**.
- `services/commands/tasks/create_task.py:76` — `async with maybe_begin(ctx.session):` — **exact** (§7B.5's cite).
- `services/commands/tasks/resolve_task.py` — `event_bus.dispatch` outside `maybe_begin` at **:102–104**; §7B.1 step 9 cites ":53-104", which spans the body rather than the dispatch. Harmless, worth narrowing when §7B.1 is next touched.

**Files expected to change — path existence:** all listed paths resolve except the four
new command files and `list_task_evaluations.py` (correctly new). `routers/api_v1/item_economics.py`,
`domain/item_economics/serializers.py`, `services/commands/item_economics/requests/__init__.py`
and `services/commands/tasks/create_task.py` all exist. **Two required files are missing
from the list** — `services/commands/item_economics/_common.py` (D2) and a migration (D8,
branch A).

**Dependency greps re-run against the current tree (axis 4).** `ItemCostEvaluation(` →
model + 3 test files (`test_calculator.py:364`, `test_item_economics_schema.py:130`,
`test_phase4_fix_coverage.py:357,454,521`); `item_cost_evaluations` → model, result FK,
migration `90cdd23a828e`; `ItemCostEvaluation` (import) → the two phase-4 delete guards
(`delete_cost_model_version.py:25`, `delete_production_cost_basis_version.py:26`);
`rederive` / `REDERIVE_MISMATCH` → calculator + `tests/unit/domain/item_economics/test_calculator.py`
only — **no production caller exists yet** (D16); `promote` → nothing in item-economics
outside the `promoted_from_id` column. **Payload-key greps** (Projection practice,
review-r1 L2): `"evaluation"`, `"evaluations"`, `"item_cost_evaluation"`, `"projections"`,
`evaluation-committed`, `item_economics:` — **zero hits anywhere in `beyo_manager/` or
`tests/`**. Phase 7 introduces no key that collides with a shipped assertion.

**Shipped tests that change.** Only one is *forced*:
`tests/unit/routers/api_v1/test_item_economics_router.py::_ROUTES` — a hand-maintained
16-row list that both role-gate tests parametrize over; phase 7's five routes must be
added or they ship with no role arbiter (D14). The four `create_task` integration files
(`tests/integration/services/commands/tasks/test_create_task_*.py`) were checked: their
workspaces carry no cost groups / basis versions / model versions, so every auto-path
pre-check is false and no evaluation is written — **no change expected**, but the
implementer owes the run that confirms it, because the auto path is the one change that
touches every task creation in the suite.

**N15 discipline (axis 6) — CLEAN.** The plan consumes `rederive` in exactly one place
(C1, "reproduces rate/budget/allowance bit-for-bit") and nowhere calls the marker proof
of corruption. No wording change needed. The real N15 problem is the opposite one: the
escalation the note governs is built by nobody (D16).

---

## Decision ledger (23 rows)

| # | Decision point | Class | Severity | Proposed routing |
|---|---|---|---|---|
| D1 | `ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY` is unregistered, and no status→identity mapping exists for the commit path | registry gap | **BLOCKER** | register in master §6.4 with the full mapping table |
| D2 | `uix_item_cost_evaluations_current` absent from `INDEX_IDENTITIES`; `_common.py` outside the write perimeter | plan gap | **BLOCKER** | add file + index row; decide the conflict sentence |
| D3 | C2's INV-E1 DB-conflict row is unreachable once §7B.1 step 1 takes the task `FOR UPDATE` | plan gap (P-S) | **BLOCKER** | P-S judgment + direct-insert harness + a lock-observable criterion |
| D4 | §7B.4's mirror race is arbitrated only against *uncommitted* valuation writers; a writer that commits mid-transaction is silently clobbered | intention gap | **BLOCKER** | amend §7B.4/§7B.1 step 4: lock `V` `FOR UPDATE`; add criterion row |
| D5 | §7A.6's `FOR SHARE` has no criterion, and the natural one is discharged by PostgreSQL's free FK `KEY SHARE` lock | plan gap (P-T/P-J) | **BLOCKER** | new criterion naming the observable + both race paths |
| D6 | C9's named mutation offers an alternative ("patched calculator") that is inert by construction | plan gap (P-Q) | **BLOCKER** | pin the fixture to a real failed SQL statement |
| D7 | §7B.5's auto-path pre-checks omit `currency_mismatch` and "task has no item"; C9's "eight rows" maps to no table | intention + plan gap (P-V) | **BLOCKER** | restate the pre-check as one resolver call; re-enumerate C9 |
| D8 | "History record" — audit log or `history_records`? The enum has no member; the plan lists no migration | plan gap | **BLOCKER** | **owner card 1**; then perimeter + criterion |
| D9 | A subordinate command may not dispatch events (`06_commands_local`), so the auto path changes more of `create_task.py` than "the savepoint block only" | plan gap | **BLOCKER** | decide whether the auto path emits; amend the file-change sentence |
| D10 | Reuse shape for the auto path: `_in_session` helper vs sub-`ServiceContext` command call — unregistered either way | free choice | **BLOCKER** | delegate explicitly + register the name |
| D11 | C6's "five failure fixtures / 0-1-2-group rows" is pre-round-12; the 2-group row is unreachable under INV-G3 | plan gap (P-V/P-S) | **BLOCKER** | re-enumerate against §7C.2; P-S note for the ambiguous row |
| D12 | `ITEM_COST_AMBIGUOUS_COST_GROUP` must name count + ids; `EconomicsSelection` carries no candidates | plan gap | should-fix | state where the message's ids come from |
| D13 | Rate snapshot: recompute via `calculate_cost_per_worker_minute` or copy `basis.cost_per_worker_minute_minor`? | free choice | should-fix | delegate (recommend recompute) + a criterion that can tell them apart |
| D14 | No criterion for the history read or any of the five new routes; `_ROUTES` has no completeness arbiter | plan gap (P-R/P-J) | **BLOCKER** | add router criteria naming the shipped TestClient harness + a surface-completeness row |
| D15 | History read: order, envelope keys, pagination idiom, term-row order all undetermined | plan gap | should-fix | pin all four in the plan |
| D16 | §6A.11's "phases 7–8 log/escalate the marker" is built by neither phase | plan gap | should-fix | assign to phase 7's read or defer to 8, in writing |
| D17 | The §11A.4 auto-path status log (the third surface §11A.4 names) is unbuilt; the WARNING line has no named shape | plan gap | should-fix | name both log lines verbatim |
| D18 | Serializer names, request models, projection-source field and `label` are unregistered | registry gap | should-fix | register before the prompt |
| D19 | The valuation chain write and the config loader live in `set_item_valuation.py`, outside the perimeter | free choice | should-fix | delegate (recommend extract into `_common.py`) |
| D20 | C10's "event-bus test seam" does not exist as a shared fixture, and capturing `dispatch` does not prove "after the transaction" | plan gap (P-R) | should-fix | name the monkeypatch target + the after-commit observable |
| D21 | Promotion's admission: does it re-run §7B.2, take the task lock, and check the projection belongs to the task? | plan gap | should-fix | state it; C8 gets the rows |
| D22 | C8's "byte-unchanged projection row" has no named comparison basis, and `updated_at` carries `onupdate` | plan gap | should-fix | name the column set and the read-back |
| D23 | Cross-phase, seen in passing: phase 8's C7 enumerates "all eleven values" of a 12-value vocabulary | drift | note | phase-8 plan; `item_missing_major_category` missing |

---

## Blockers in detail

### D1 — the commit path has no identity to raise, and no mapping to raise it from

The commit path consumes `resolve_economics_selection` (phase 5, `configuration.py:80`),
which returns an `EconomicsSelection` whose `status` is an `EconomicsStatusEnum` member.
Every commit-path refusal is therefore a translation from a *status* to an *error
identity*, and that translation is registered nowhere.

Two concrete holes:

1. **`ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY` does not exist in master §6.4.** Grepping
   `master_plan.md` for the token returns exactly one hit — §6.3 line 268, which
   registers the *enum member* `ITEM_MISSING_MAJOR_CATEGORY`, not an error identity. The
   plan's own 4B forward note says "propose to the coordinator before use"; the proposal
   was never consumed. Under §7C.2 step 1 this is the **first** failure the commit path
   can hit, so the phase cannot start without it.
2. **The other four have no written mapping.** The coordinator should record it as a
   table in §6.4 so it is not re-derived per command:

   | `EconomicsStatusEnum` | commit-path identity | class |
   |---|---|---|
   | `ITEM_MISSING_MAJOR_CATEGORY` | `ITEM_COST_ITEM_MISSING_MAJOR_CATEGORY` *(to register)* | ValidationError |
   | `NOT_CONFIGURED_NO_COST_GROUP` | `ITEM_COST_NO_COST_GROUP` | ValidationError |
   | `NOT_CONFIGURED_AMBIGUOUS_COST_GROUP` | `ITEM_COST_AMBIGUOUS_COST_GROUP` | ValidationError |
   | `NOT_CONFIGURED_NO_BASIS_VERSION` | `ITEM_COST_NO_BASIS_VERSION` | ValidationError |
   | `NOT_CONFIGURED_NO_COST_MODEL_VERSION` | `ITEM_COST_NO_COST_MODEL_VERSION` | ValidationError |
   | `ITEM_UNVALUED` | `ITEM_COST_ITEM_UNVALUED` | ValidationError |
   | `ITEM_MISSING_EXPECTED_PRICE` | `ITEM_COST_EXPECTED_PRICE_REQUIRED` | ValidationError |
   | `ITEM_MISSING_PURCHASE_COST` | `ITEM_COST_PURCHASE_COST_REQUIRED` | ValidationError |
   | `CURRENCY_MISMATCH` | `ITEM_COST_CURRENCY_MISMATCH` | ValidationError |
   | `NOT_EVALUATED` | *(proceed)* | — |

   Note that `ITEM_COST_EXPECTED_PRICE_REQUIRED` / `_PURCHASE_COST_REQUIRED` /
   `ITEM_COST_CURRENCY_MISMATCH` are *also* raised from inside the calculator
   (`calculator.py:168,208,395`), so the commit path can reach the same identity by two
   routes. The plan should say which route C7's rows exercise (recommend: the resolver's,
   so the calculator never runs on an unevaluable item — P-F's "nothing is written before
   the calculator succeeds" already implies the resolver gate comes first).

### D2 — the concurrent-commit identity cannot be raised as shipped

`_common.py::INDEX_IDENTITIES` (verified: 8 entries) maps partial-unique index names to
identities and `translate_integrity_error` re-raises anything unlisted. `uix_item_valuations_current`
→ `ITEM_COST_CONCURRENT_VALUATION` is present (so the mirror's race is covered);
**`uix_item_cost_evaluations_current` is absent**, so an INV-E1 violation surfaces as a
raw `IntegrityError`, which `run_service` converts into the generic "An unexpected
internal error occurred." — not `ITEM_COST_CONCURRENT_COMMIT`.

`services/commands/item_economics/_common.py` is **not** in "Files expected to change".
Add it. Two sub-decisions come with it:
- the shipped conflict sentence is `"{identity}: configuration conflicts with an existing row"`
  — accurate for phase-4 config commands, wrong noun for a commit and for a valuation
  mirror. Phase-4 N4 pinned "the DB-path translation emits the uniform conflict sentence";
  confirm that still binds, or authorise a per-identity sentence (identity token unchanged
  either way, so criteria asserting the leading token are unaffected).
- `promote_item_cost_projection` and the auto path must route through the same helper, or
  the identity exists on one path only.

### D3 — C2's DB-conflict row cannot happen, and the criterion as written rewards deleting the lock

§7B.1 step 1 loads the task `FOR UPDATE`. INV-E1 is scoped `(task_id)`. Two commits for
the *same* task therefore serialize at step 1 — the second blocks before it reaches S1,
let alone S2. Two commits for *different* tasks never contend on the index. Promotion is
"the commit procedure", so it takes the same lock. **`ITEM_COST_CONCURRENT_COMMIT` is
unreachable through every surface phase 7 ships.**

C2 requires "INV-E1 DB conflict path (two sessions past S1) → exactly one current +
loser's exact `ITEM_COST_CONCURRENT_COMMIT`". As written the only way to make that test
pass is to *not take the task lock* — the criterion actively rewards deleting the
mechanism §7B.1 step 1 exists for. Route:

- record the P-S reachability judgment: the DB path is unreachable from the command
  surface, so the identity is armor, and its test drives the conflict from a second
  session doing a direct `ItemCostEvaluation` INSERT (precedent:
  `test_phase4_fix_coverage.py:521`, which already builds exactly such a row) — the
  translation is then proven without pretending the command can produce it;
- add the criterion that is currently missing: **the task lock itself**. P-T form — name
  the observable that flips (`second_commit_blocked_while_task_locked`), name the
  counterparty (`SELECT … FROM tasks … FOR UPDATE` in `commit_item_cost_evaluation.py`),
  bound the wait (P-T r2 L3), and name the mutation (delete `.with_for_update()` at the
  definition site) that must redden it.

### D4 — the mirror rule silently overwrites a price that commits mid-transaction

§7B.4 says a concurrent valuation write "is arbitrated by INV-V1 (7A.2); the losing
transaction is the whole commit". That is true only while the other writer is
**uncommitted**. Trace the other interleaving, at READ COMMITTED, which is what this repo
runs (§7A.2):

1. T1 (commit) step 4: `SELECT` the current valuation `V` — **no lock anywhere in §7B.1**.
2. T2 (`set_item_valuation`, `set_item_valuation.py:128-158`) closes `V`, inserts `V2`
   with the manager's corrected price, **commits**.
3. T1 step 9: the mirror predicate fires (E's figures ≠ `V`'s). Its S1
   (`UPDATE item_valuations SET superseded_at = now WHERE item_id = … AND superseded_at IS NULL
   AND is_deleted = false`) re-evaluates against T2's committed state and closes **`V2`**,
   rowcount 1. S2 inserts the mirror row. **No index conflict — nothing to arbitrate.**

Result: the price the manager just saved is superseded by a mirror row carrying figures
derived from the *older* valuation, with no error on either side. This is the
silent-failure class charter rule 6 exists for, and §7B.4's own guarantee ("the current
valuation always shows the currently-operative figures") is false in this window.

**Proposed amendment (intention, §7B.4 + §7B.1 step 4):** resolve the current valuation
with `SELECT … FOR UPDATE` at step 4 and hold it for the transaction. T2 then blocks at
its own S1 until the commit finishes and supersedes the mirror row afterwards — the
manager's price wins, and §7B.4's arbitration clause becomes true for both orderings.
Criterion (C5 gets a sixth row): concurrent `set_item_valuation` *committing between the
commit's step 4 and step 9* → afterwards the item's current valuation carries the
manager's figures, not the mirror's; named mutation — dropping `FOR UPDATE` from the
step-4 read must redden it.

### D5 — `FOR SHARE` has no observable of its own; the free FK lock discharges the naive test

The phase-4 projection's forward item B5 requires "a criterion here [that] exercises the
delete-vs-commit race against the real commit path". No criterion in C1–C10 does. Worse,
the obvious criterion cannot tell whether `FOR SHARE` exists:

- `delete_production_cost_basis_version.py:22` holds `SELECT … FOR UPDATE` on the version
  row for the whole transaction;
- inserting an `ItemCostEvaluation` that references that row takes an implicit
  `FOR KEY SHARE` on the parent — PostgreSQL supplies it for free, and it conflicts with
  `FOR UPDATE`. This is exactly the counterparty P-T was written about, and it is what
  the shipped `test_c6_interleaved_fk_insert_is_blocked_by_the_delete_row_lock_then_proceeds`
  (`test_phase4_fix_coverage.py:498`) observed — with a hand-built INSERT, not the command.

So "the commit blocks while the delete holds the lock" stays green with
`.with_for_update(read=True)` deleted from the commit path. The distinguishing observable
is **the outcome, not the block**:

| Race path | With `FOR SHARE` at step 3 | Without it |
|---|---|---|
| delete locks first, commit arrives second | commit blocks at **resolution**, then re-reads and finds no applicable version → `ITEM_COST_NO_BASIS_VERSION`; **no evaluation row exists** | commit reads the pre-delete snapshot, proceeds, and writes an evaluation referencing a **soft-deleted** version — §7.5's guarantee false |
| commit resolves first, delete arrives second | delete blocks on the shared lock, then re-runs its reference check inside its own lock, finds the new evaluation → `ITEM_COST_BASIS_VERSION_IN_USE` | same outcome (the FK lock covers this direction) |

Route: one criterion with both rows, the outcome asserted per row, the wait bounded
(P-T r2 L3), and the named mutation stated as *deleting the `read=True` lock clause from
`commit_item_cost_evaluation.py`'s configuration resolution (definition site)* must
redden **row 1 only** — the plan should say so, because a declaration claiming both rows
redden is the P-I fifth-extension defect. The same question applies to the **cost model
version** chain (`delete_cost_model_version.py:22` has the identical `for_update=True`
guard), so the criterion is parametrized over two chains, not one. The **group** row
needs no lock: `delete_production_cost_group.py` takes none, and group deletion is
transitively blocked by its basis versions' own guard — state this so nobody adds a lock
that has no counterparty, or omits one that does.

### D6 — C9's named mutation is inert on one of its two offered fixtures

C9: "replacing the `begin_nested()` savepoint with a plain `try/except` … must turn red
the test in which the evaluation INSERT itself raises (induced §7A.2 conflict **or**
patched calculator)".

- **Patched calculator.** The calculator is pure Python and runs *before* any INSERT
  (§7B.1 step 5). A Python exception leaves the PostgreSQL transaction perfectly healthy,
  so `try/except` catches it, `create_task` continues, the task commits, and the test
  stays **green**. The mutation is inert — the exact P-Q defect from phase-5 review L3.
- **Induced §7A.2 conflict.** Also unreachable on the auto path: INV-E1 needs a
  pre-existing current evaluation for a task created microseconds ago, and INV-V1 needs
  the mirror to fire, which §7B.4 says is false by construction on the auto path.
- Fabricating an `IntegrityError` from Python does not help either: only a genuinely
  failed *SQL statement* poisons the transaction, which is the whole premise of §7B.5.

**Route:** pin the fixture to a real database failure inside the savepoint body. One that
needs no production patching and no new seam: seed the workspace's cost model with two
`fixed_amount` terms of `2 147 483 647` each and give the item an expected sale price of
`0`. `calculate_production_budget` returns `-4 294 967 294`, which overflows
`item_cost_evaluations.production_budget_minor` (`Integer`) and PostgreSQL rejects the
INSERT — a real aborted transaction. Under `begin_nested()` the savepoint rolls back and
the task commits; under `try/except` the next statement (or the outer commit) raises and
the task is lost. The criterion states the fixture, the assertion ("the task row is
committed and readable from a second session"), and the mutation site
(`create_task.py`, definition site of the `async with` block).

### D7 — the auto path's pre-check list is not total, and C9's row count maps to no table

§7B.5 enumerates the pre-checks as "all of 7A.5's rows 1–5 pass ∧ current valuation with
non-NULL expected price ∧ (iff the model carries an `item_purchase_cost` term) a non-NULL
purchase cost", and opens with "**exceptions never as control flow**". Two cases fall
through that enumeration into the exception path it forbids:

- **`currency_mismatch`.** `resolve_item_economics_status` (`configuration.py:154`) is a
  registered phase-5 status; a mismatched item passes every listed pre-check and then
  raises `ITEM_COST_CURRENCY_MISMATCH` inside the savepoint. Observable outcome is the
  same (task created, no evaluation) but the mechanism is exactly the one §7B.5 bans, and
  it logs a WARNING for a perfectly ordinary configuration state.
- **A task created with no item.** `create_task` reaches line 292 only when
  `request.item is not None`; a task without an item has no PRIMARY, so §7B.3 would raise
  `ITEM_COST_NO_PRIMARY_ITEM`. Nothing in §7B.5 mentions it.

**Proposed amendment (intention §7B.5, plan task 4):** replace the enumeration with the
resolver the phase already consumes — *the auto path runs iff
`resolve_item_economics_status(valuation, selection, model_terms) is EconomicsStatusEnum.NOT_EVALUATED`,
and the task has an active PRIMARY item*. That is total by construction (the resolver's
`ITEM_READINESS_PRECEDENCE` ends in `NOT_EVALUATED`), it is the same expression the
preview and phase-8 status use, and it makes the pre-check drift-proof.

Consequently **C9's "eight pre-check-false rows" maps to no table** (P-V). Against §7C.2 +
§11A.4 as amended the enumeration is **ten**: `item_missing_major_category`,
`not_configured_no_cost_group`, `not_configured_ambiguous_cost_group` *(unreachable —
P-S note, see D11)*, `not_configured_no_basis_version`, `not_configured_no_cost_model_version`,
`item_unvalued`, `item_missing_expected_price`, `item_missing_purchase_cost`,
`currency_mismatch`, plus the no-PRIMARY-item row. Restate C9 against that table with one
parametrize id per authority row (P-V third extension: each row's *expression* must
differ, not just its id).

### D8 — "history record" is two different mechanisms, and one of them needs a migration

The plan says "History record + `item_economics:evaluation-committed` workspace event"
(task 5) and C10 asserts "history record written". The repo has two mechanisms and the
plan's own cited precedent uses the one the registry does not:

- **`write_audit`** (`services/infra/audit/write_audit.py`) — what every shipped
  item-economics command uses (`_common.py::audit`), and what master §6.4 anticipates:
  "*phase 7 adds `item_cost_evaluation.*` rows here before use — never free-formed in a
  command*". Those rows are **not yet registered** either way.
- **`_create_history_record_in_session`** — what `resolve_task.py:61` (the plan's Read-first
  precedent) and `create_task.py:467` use. Its `HistoryRecordLink.entity_type` is a native
  PG enum with `create_type=False`; I read the live labels: **8, none for evaluations**.
  Using it therefore needs `ALTER TYPE history_record_entity_type_enum ADD VALUE …` in a
  migration — and **phase 7's "Files expected to change" lists no migration at all**.
  (PostgreSQL 18.4 confirmed; five in-tree precedents exist, e.g.
  `migrations/versions/f2c3d4e5f6a7_add_shopify_process_products_task_type.py`.)

This is owner card 1. Whichever branch wins, the coordinator then owes: the registered
audit event names (`item_cost_evaluation.committed` / `.projected` / `.promoted` /
`.deleted` — mirroring §6.4's existing `<entity>.<action>` rows), and C10 rewritten to
name the table it asserts against.

Verified in passing: `item_economics:evaluation-committed` will **not** produce an audit
row by itself — `audited_events.py` gates the audit handler on an allow-list the name is
not on. The explicit `write_audit` call is the only audit carrier.

### D9 — the auto path cannot dispatch its own event, and it changes more of `create_task.py` than the plan says

`06_commands_local.md:62-76` (the "subordinate-command event rule" the plan's Read-first
already cites): "*Subordinate commands must NOT dispatch events — they collect
`pending_events` and return them to the parent, which dispatches after its own block
exits.*" `maybe_begin` in subordinate mode does not commit, so anything dispatched inside
`create_task`'s transaction fires before the commit.

Two consequences:

1. **Does the auto path emit `item_economics:evaluation-committed` at all?** The plan is
   silent. Recommend **yes** — the realtime surface has no other way to learn that a task
   arrived with a budget already attached, and §7B.1 step 9 makes the event part of the
   commit, not of the explicit surface. The event is appended to `create_task`'s
   `pending_events` list (`create_task.py:480`) **only after the savepoint block exits
   normally**, so a rolled-back savepoint cannot leave a queued event behind.
2. Therefore the plan's "*§7B.5 savepoint block only; nothing else in the file changes*"
   is false: `pending_events` gains a conditional append. Amend the sentence rather than
   let the implementer resolve the contradiction silently — and keep the *spirit*, which
   is that no existing statement in `create_task` moves.

### D10 — the auto path's reuse shape is undetermined and, either way, unregistered

`commit_item_cost_evaluation(ctx)` parses `ctx.incoming_data`, which inside `create_task`
holds the task-creation payload — so the command cannot be called as-is. Two idiomatic
shapes exist in this very file:

- **sub-`ServiceContext`** (`create_task.py:141-151`, `223-227`) — build a fresh context
  with a synthetic payload and call the command; `maybe_begin` joins the transaction
  correctly, but the command's post-`maybe_begin` `event_bus.dispatch` then violates D9's
  rule;
- **`_in_session` helper** (`_create_item_in_session`, `_create_history_record_in_session`)
  — the command becomes a thin wrapper over a helper that takes explicit arguments and
  returns its pending events.

Recommend the helper, which is the only shape compatible with D9. Either way the name is
not in master §6.5 and §6's registry rule forbids inventing it — propose
`_commit_item_cost_evaluation_in_session` (in `commit_item_cost_evaluation.py`, alongside
its command) and register it, together with the fact that `promote_item_cost_projection`
consumes the same helper ("promotion = the commit procedure", plan task 3).

### D11 — C6's authority table was superseded nine months of decisions ago

C6 reads "the five failure fixtures (sole-predicate each) → exact identities; 0/1/2-group
rows → exact outcomes". Both halves are pre-round-12:

- §7A.5's own text now says its group-resolution rows are **superseded by §7C.2**, and
  §7C.2 inserts `item_missing_major_category` *first*. The failure enumeration is **six**
  outcomes, not five: missing category, no group for the category, ambiguous, no basis
  version at all, none applicable today (same identity, §7A.5 row 4), no model version.
- "0/1/2 groups" is the pre-category counting. Under §7C the count that matters is
  *groups active for the item's major category*, and **2 is unreachable**: I verified
  `uix_production_cost_groups_major_category_active` is live on
  `(workspace_id, major_category) WHERE is_deleted = false`, so no command and no direct
  INSERT can produce it. P-S applies — the ambiguous row is discharged by the pure-resolver
  test 4B already ships (`tests/unit/domain/item_economics/test_phase4b_category_classifier.py`)
  plus a recorded reachability note, never by a command-level fixture.

Restate C6 against §7C.2's table with a parametrize id per authority row (P-V third
extension).

### D14 — the whole HTTP surface of this phase has no arbiter

Phase 7 adds five routes (§6.5: `POST /tasks/{id}/evaluations/commit`,
`GET /tasks/{id}/evaluations`, `POST /tasks/{id}/projections`,
`DELETE /projections/{id}`, `POST /projections/{id}/promote`) and one query service.
**No criterion in C1–C10 mentions a route, a role gate, or the history read.** P-R is
explicit that a criterion only the router can satisfy names its harness in the plan.

The harness exists and is good: `tests/unit/routers/api_v1/test_item_economics_router.py`
builds a `FastAPI` app, overrides `get_db` and `get_jwt_claims`, monkeypatches
`run_service`, and parametrizes two tests over a module-level `_ROUTES` list —
`test_every_item_economics_route_rejects_worker_and_seller` and
`…_retains_admin_and_manager_access` (the latter is P-G(a)'s retention row). Phase 7 must
add five rows to `_ROUTES`.

But `_ROUTES` is a **hand-maintained list with no completeness arbiter** — I checked
`test_router_surface_has_no_term_mutation_and_no_derived_rate_input`, which introspects
`item_economics.router.routes` for two specific properties only. A route added without a
`_ROUTES` row is silently ungated, and that is precisely the P-J second-extension failure
("a test that constructs the set and then asserts about one member has not discharged
it"). Route: add a criterion asserting
`{(method, path) for route in item_economics.router.routes} == {(method, path) for _ROUTES}`,
with the named mutation "add a route to the router without adding its `_ROUTES` row must
redden it" — this is the arbiter phase 8 will also need.

---

## Should-fix rows, briefly

- **D12.** C6 requires `ITEM_COST_AMBIGUOUS_COST_GROUP` to name "count + ids", but
  `EconomicsSelection` (`configuration.py:23-30`) carries only `status` and the three
  selected rows. The command must build the message from the group rows it already
  loaded, filtered by category. State that this is message construction, **not** a second
  selection derivation (the prompt's "never re-derives selection" still binds), or extend
  the frozen dataclass — but extending it is a phase-5 file outside this perimeter.
- **D13.** §6A.11's theorem requires `cost_per_worker_minute_minor_snapshot` to be
  reproducible from the three snapshot inputs, and `rederive` (`calculator.py:438`)
  recomputes it — so C1 goes red if the snapshot is a *copy* of
  `basis.cost_per_worker_minute_minor` and the two ever disagree. P-F ("snapshots are
  written only from calculator outputs") points at recompute; phase 5's preview
  (`set_item_valuation.py:98`) uses the stored column, so preview and commit would take
  different routes to the same number. Recommend **recompute**, and record why the two
  agree today (R11-1 quantizes the request numerics to column scale before deriving, so
  stored inputs re-derive the stored rate exactly). P-Q: any mutation pinning this needs a
  fixture where persisted ≠ derived, which only a hand-written basis row can produce.
- **D15.** The history read is undetermined on four axes: (a) **order** — the plan says
  "ordered by `committed_at`" with no direction and no tie-break; the sibling shipped read
  `get_item_valuation_history.py:30` uses `created_at DESC, client_id DESC` per R13-2;
  (b) **envelope keys** — one list or separate committed/projection keys (greps confirm no
  key is taken); (c) **pagination** — the two shipped idioms diverge (unpaginated history
  vs `limit + 1` / `has_more` lists) and the registry's route carries no query params;
  (d) **term-row order** — `item_cost_evaluation_terms` has no ordinal column and
  `created_at` is per-row `now()`, so the drill-down needs an explicit
  `ORDER BY created_at, client_id` or the payload is non-deterministic. Pin all four.
- **D16.** §6A.11 states that "calling services (phases 7–8) log/escalate the marker at
  error level and the read still renders", and the N15 forward note is written for exactly
  that code. I grepped: `rederive` has **no production caller** — and phase 8's plan
  (read in full) carries no task or criterion for it either. The mechanism is currently
  orphaned between two phases. Decide: phase 7's history read owns it (natural — it is the
  read that returns snapshots), or it defers to phase 8's status query **in writing**.
- **D17.** §11A.4's preamble names three consumers: the status query, the valuation
  preview, and "**the auto-path log line**". The plan builds no status log — task 4 logs
  only on exception. And the WARNING line has no named shape; the repo idiom is a
  prefixed pipe-delimited message (`reconcile_worker_shift_state.py:285`:
  `"worker_shift.reconcile_unique_retry | workspace_id=%s user_id=%s"`). Propose both
  verbatim, e.g. `"item_economics.auto_commit_skipped | task_id=%s item_id=%s status=%s"`
  at INFO/DEBUG and `"item_economics.auto_commit_failed | task_id=%s item_id=%s error=%s"`
  at WARNING, and give C9 an assertion on the second (charter rule 2's error-contract
  clause — a criterion naming a log line owes a test on it).
- **D18.** Unregistered names the implementer would otherwise invent: the evaluation and
  term serializers (`domain/item_economics/serializers.py` currently ends at
  `serialize_item_economics_preview`, `:111`); the request models and parsers in
  `requests/__init__.py`; the field that selects a projection's source (§7.3's three
  origins: current committed / another projection / scratch); and whether `label`
  (`item_cost_evaluation.py:24`, nullable String(255)) is accepted, required for
  projections, or ignored. §6's registry rule sends all of these to the coordinator.
- **D19.** The valuation chain's S1→S2→S3 is written **inline** in
  `set_item_valuation.py:128-159`, and the workspace-wide config loader is
  `_load_preview_inputs` in the same file. The mirror rule needs the first and the commit
  path needs the second, but `set_item_valuation.py` is outside this phase's perimeter, so
  the implementer must either duplicate both or widen the perimeter silently. Recommend
  extracting both into `_common.py` (already being added by D2) with the phase-5 call
  sites re-pointed — and if that is refused, say so, because duplicating a chain writer is
  how the two drift.
- **D20.** C10 says the event is "captured via the event-bus test seam". There is no such
  shared fixture — the repo idiom is a per-module monkeypatch
  (`tests/unit/services/commands/upholstery/test_set_current_stored_amount_inventory.py:165`
  patches `"<module>.event_bus.dispatch"`). Name the module, and note that this pins the
  assertion to whichever module dispatches — patching the commit command's symbol will
  **not** capture the auto path's event, which rides `create_task`'s dispatch (D9). Also:
  capturing `dispatch` proves the event fired, not that it fired *after* the transaction.
  Give C10 an observable for the ordering — the standard one is a fake `dispatch` that
  reads the committed row from a **second session** and asserts it is visible.
- **D21.** "Promotion = the commit procedure with the projection's inputs" leaves three
  predicates unstated: does promotion re-run §7B.2 task admission (recommend yes — a
  projection on a RESOLVED task must not become a commitment), does it take the task
  `FOR UPDATE` (yes, if it is the commit procedure — which is what makes D3's analysis
  hold), and does it verify the projection belongs to the task and is not soft-deleted
  (`DELETE /projections/{id}` is a separate route keyed only by the projection id, so a
  cross-task promote is reachable through the URL). C8 needs the rows.
- **D22.** C8 asserts the promoted projection "row is left byte-unchanged" with no named
  comparison basis. `ItemCostEvaluation.updated_at` carries `onupdate=` — merely touching
  the ORM object inside the transaction bumps it, so "byte-unchanged" must name the column
  set and be read back from a second session after commit, not compared against a stale
  in-session identity map entry.
- **D23** *(cross-phase, reported in passing).* Phase 8's C7 says "**all eleven values**
  enumerated" and lists ok, infeasible, four `not_configured_*`, `item_unvalued`,
  `item_missing_expected_price`, `item_missing_purchase_cost`, `currency_mismatch`,
  `not_evaluated`. §7C.3 made the vocabulary **12** and the shipped
  `EconomicsStatusEnum` has 12 members — `item_missing_major_category` is missing from
  C7's list. Round-12 drift of exactly the same shape as D11; the phase-8 plan will need
  it before its own projection.

---

## Clean findings (checked, nothing to route)

- **C3 (§7B.2 admission)** — nine rows, and `TaskStateEnum` has exactly the eight members
  §7B.2 enumerates plus the deleted row. P-V satisfied as written; the only addition
  worth making is the parametrize-id convention (P-V third extension).
- **C1 (snapshot immutability)** — decidable as written. `rederive` returns
  `(rate, budget, allowed)` on success (`calculator.py:547`), so "reproduces bit-for-bit"
  turns into one exact tuple assertion. Note for the implementer prompt: `rederive` is
  order-independent over term rows (each amount derives from its own row, budget is a
  sum), so D15's ordering question does not leak into C1.
- **Payload-key collision check** — zero hits for every key phase 7 introduces.
- **N15 wording** — the plan never reads the rederive marker as proof of corruption.
- **Event/audit interaction** — `item_economics:evaluation-committed` is not on the
  audit-handler allow-list, so it cannot double-write audit rows.
- **`create_task` blast radius** — the four `create_task` integration files run in
  unconfigured workspaces; the auto path's pre-checks are false throughout.

---

## Write perimeter and probe declaration

**Documents written (1):** this handoff, at
`docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-14_phase7_projection_r0_handoff.md`.

**Code:** none. No file under `app/` was created, edited or deleted. No plan, intention or
master-plan edit was made (projection doctrine: report, never fix).

**Mutation probes:** **none run.** No mutation was applied to any source file; every
inertness claim above (D6 in particular) is derived from the code as shipped and is
labelled as an analysis, not an observation — the implementer's own mutation run is the
arbiter.

**Tests:** no suite run. The baseline in the prompt (2012 / 23 / 1 deselected = 2035
selected at `be9dfe42a035`) is carried forward unverified by this session, deliberately —
a projection proves the plan is implementable, and a full run would have added economics
residue to the dev database for no evidentiary gain.

**Database:** read-only. Three commands touched it — `alembic current` (reads
`alembic_version`), one `SELECT count(*)` across seven economics tables, and one
`pg_enum` label query. No writes, no disposable database created, configured DB left at
head `be9dfe42a035`.

**Archgraph:** READ-ONLY, **zero delta**. Four calls: one `archgraph_status` and three
`archgraph_search_nodes` orientation queries, which resolved the plan's two named nodes
(`table-task-item`, `helper-task-state-transitions`) plus `table-item-cost-evaluation` —
all three `human_confirmed` / `reviewed`. No `apply_changes`, no review adjudication.
State at exit:
155 nodes / 200 edges, revision `53261a232cafa5a3d920b72c058bc5a452dc9e1d565824dc76618bbe0ee12e0a`,
2 pending, 0 stale — unchanged from entry, and one node / one edge below the count the
prompt recorded (recorded in the environment table above; not acted on).

**Skeleton:** discarded per doctrine — no non-authoritative appendix is attached, so the
implementer receives no sketch from this session.

---

## Exit gate

**AMENDMENTS_REQUIRED.** 12 blockers, 10 should-fix, 1 note (counted from the ledger
table's severity column, not from prose — P-L). Every row must be routed —
amendment applied, upstream change made, or delegation recorded — before the phase-7
implementer prompt is compiled. One owner card is open (card 1); the gate holds on it.
The plan's Review log line is the coordinator's to write when it consumes this handoff.
