# Stock report versions — drafts, scheduled activation, live drafts, manual requested quantity

> Status: **PLAN, revision 7 (2026-09-28) — owner's third intention round folded, *(O-9)*: a
> draft's missing is borrowed from the active version unless typed, and activation carries a
> flag to keep or reset the active version's missing.** Revision 6 folded projection r2
> (Q-1..Q-18, marked *(Q-n)*) and owner cards 5–7. Revision 4 folded projections r0 (24 items, *(P-n)*) and r1 (15
> items, *(R-n)*) and the owner's cards 1–4 *(card n)*. Revision 5 folded the owner's second
> intention round of 2026-09-27, marked *(O-n)*. Revision 6 folds
> `PROJECTION_draft_versions_plan_r2_20260928.md` — five blockers (activation's freeze and
> stamp in one statement; a supersede skip is a return, not a raise; a consolidated reference
> file for the docs guard; the demand webhook's statement bound; UTC schedule comparison) and
> the owner's three rulings of 2026-09-28, all the projection's recommendations:
>
> | Card | Ruling |
> |---|---|
> | 5 (r2 card 1) | equal `scheduled_activation_at` → the draft **created later** wins; tie broken on `(scheduled_activation_at, created_at, client_id)`. |
> | 6 (r2 card 2) | typing the value Scanner already shows **pins** it: the no-op compares against the stored manual value. The ship-time reference file corrects v8 §5.22. |
> | 7 (r2 card 3) | the demand webhook's statement bound rises from 8 to **11**, constant in batch size and draft count. |
>
> The owner's rulings of 2026-09-27 (afternoon), marked *(O-n)*:
>
> | | Ruling |
> |---|---|
> | O-1 | A draft's `quantity_requested` is **live**, not frozen. Only activation snapshots it. |
> | O-2 | Two stored columns, source derived: `quantity_requested_scanner` (frozen at activation) and `quantity_requested_manual` (the override). Effective = manual, else the frozen Scanner value once active, else the live row. |
> | O-3 | A draft's **row set is live too**: a row Scanner creates joins every draft at once. "A draft is the manager's playground and stays loyal to the current stock rows." |
> | O-4 | The user may set `quantity_requested` by hand on a draft and on the active version, and revert it on the same route: to the live row on a draft, to the frozen Scanner value on the active version. Roles: admin, manager, seller. |
> | O-5 | A draft's rows carry the **active version's `quantity_missing`** beside their own, as a read value, never stored on the draft; one join, shared by every draft. |
> | O-6 | Refresh is a choice: keep the manual overrides or replace them. |
> | O-7 | A manual change on the active version writes a history record, of a new type, and history records gain a column that says where their requested came from. |
> | O-8 | v7 is with the frontend (planning only so far): the differences ship as **v8**; v7 is never edited. |
> | O-9 (2026-09-28) | A draft row's `quantity_missing` works like its requested: the draft's **own typed value if there is one, otherwise the active version's value**. At activation the new version's missing is the draft's typed value where typed; elsewhere the user **chooses, on the activate action, to keep the active version's missing or reset it to 0** — a flag the frontend shows in a drawer; stored on the draft for a scheduled activation. |
>
> Consequences folded, not separately ruled: the activation refresh flag, the draft's stored
> refresh choice and the draft refresh route disappear — activation always freezes the live
> Scanner value, and a draft has nothing to refresh. **R-13 (batch split) stays declined**: one
> implementation by the plan's author, with the §12 checkpoint. Written from the shipped code at
> `438c4f7`; nothing is implemented. Contracts: `06_commands_local`, `07_queries_local`,
> `08_domain`, `03_models`, `30_migrations`, `37_scheduled_jobs`, `16_background_jobs`,
> `42_event`, `46_serialization` "Exempt cases".
>
> This document is an owner-shaped plan, not a pipeline intention; if it enters the pipeline
> it needs a RATIFIED intention first (projection reality check).

## 1. The intention, restated

Today a version has two derived states: **active** (`closed_at IS NULL`) and **closed**
(`closed_at IS NOT NULL`); `active_at` always equals `created_at`; a snapshot's
`quantity_requested` is frozen when the version is created.

The owner adds a third, **draft**: a plan prepared against the **current** stock report while
the active version keeps running, invisible on the board.

1. `POST /snapshots/versions` keeps creating an **active** version directly.
2. The same act can instead create a **draft**. A workspace may hold **many** drafts, each
   with a **title**.
3. **A draft is live** *(O-1, O-3)*: its rows' `quantity_requested` is the live row's, and a row
   Scanner creates joins every draft the moment it is created. What a draft holds of its own is
   `priority`, `priority_order`, `quantity_missing` and the manual requested overrides.
4. A draft is **activated** by hand, or **on a schedule** the user sets and can change,
   through the existing delayed-scheduler worker. Activation closes the current active
   version and **freezes** each row's live `quantity_requested` into the snapshot
   (`quantity_requested_scanner`). Manual overrides survive activation.
5. **Manual requested** *(O-2, O-4)*: on a draft or on the active version a user may set a
   row's `quantity_requested` by hand. The Scanner value stays intact beside it; the effective
   value is the manual one while it is set. The same route reverts: on a draft back to the live
   row, on the active version back to the frozen Scanner value.
6. A **refresh** of the **active** version re-freezes the Scanner value from the live rows and
   adds rows created since; the caller chooses whether manual overrides are kept or replaced
   *(O-6)*. Drafts have nothing to refresh.
7. On a draft the user may edit priority, priority order and `quantity_missing`. **A draft's
   missing is borrowed unless typed** *(O-5, O-9)*: a row shows and uses the draft's own value
   where the user typed one, otherwise the active version's value for the same row, so a
   planner sees today's missing situation while planning. At activation the typed values carry
   over, and for the rest the user chooses to **keep** the active version's missing or **reset**
   it to 0 (§3.4b, §4.2).
8. Drafts can be **hard-deleted**.
9. **The folder model.** The frontend is always inside one version: a versions page shows the
   cards (title, progress per priority), and only after opening a card does the user see that
   version's stock cards and edit them. An edit therefore always belongs to the open version.
   Workers and sellers see drafts read-only *(card 2)*; their board read, `GET /items` without
   `version_id`, shows only the active version as today.

Confirmed: `POST /snapshots/versions/{client_id}/apply-priorities` already copies a closed
version's priorities onto the active one.

## 2. What the code does today that this collides with

"Active" is spelled `closed_at IS NULL` at every snapshot predicate site (the site table is
Appendix A) and in **two partial unique indexes**:

| Index | Predicate | Invariant |
|---|---|---|
| `uix_stock_report_snapshot_versions_active` | `closed_at IS NULL` | one open version per workspace |
| `uix_stock_report_item_snapshots_row_active` | `closed_at IS NULL` | one open snapshot per row |

A draft is a second open version with a second open snapshot per row. Both indexes refuse it
today, and if they were merely relaxed every site would treat the draft's snapshots as the
board. So the change is **two predicates instead of one**:

| Predicate | SQL | Who uses it |
|---|---|---|
| **open** | `closed_at IS NULL` | counter derivation: the serializer and the progress engine read the row's live counters while a snapshot is open, the frozen copies once closed (unchanged) — this is what gives the versions page its live preview |
| **active** | `active_at IS NOT NULL AND closed_at IS NULL` | everything that means "the board": the items read's default, the shortcut routes' target, resolved credit, the clamp, the webhooks' discovery, the active-version read, the close-freeze, the missing-summary |

And, new in revision 5, a **third derivation** beside the counters' live-or-frozen switch:
the **effective requested quantity** (§3.4). Every site that reads `s.quantity_requested`
today (Appendix B) reads that expression instead.

The quantity counters have one source of truth, the row: no open snapshot, active or draft,
is written by an assignment move, and the counters land on a snapshot only at close. Drafts
add no writes to that path. What is per version **by design** is `priority`,
`priority_order`, `quantity_missing` and `quantity_requested_manual`.

Plus one structural change that is right regardless: **an ordering group is
`(version_id, priority)`**, not `(workspace_id, priority)`.

## 3. The model

### 3.1 State is derived, never stored

| State | `active_at` | `closed_at` |
|---|---|---|
| `draft` | NULL | NULL |
| `active` | set | NULL |
| `closed` | set | set |

`active_at NULL, closed_at set` is unstorable on **both** tables: check
`ck_stock_report_snapshot_versions_closed_implies_activated` and
`ck_stock_report_item_snapshots_closed_implies_activated` (`closed_at IS NULL OR active_at IS NOT NULL`).
A draft, and a draft's snapshot, leave their table by **deletion**, never by closing (§4.7, §4.8).

The item snapshot carries its version's `active_at` (denormalised, as it already carries
`closed_at`): the partial indexes and the per-snapshot predicates need it without a join.

Domain (`08_domain`), in `domain/stock_report/enums.py` and `snapshot_rules.py`:

- `StockReportSnapshotVersionStateEnum` (`draft`, `active`, `closed`); `version_state(version)`;
  `is_version_draft`, `is_version_active`.
- `StockReportQuantityRequestedSourceEnum` (`scanner`, `manual`) *(O-2, O-7)*.
- The existing `is_snapshot_active` (`closed_at is None`) is **renamed `is_snapshot_open`**, its
  unit test updated; a new `is_snapshot_active` tests the pair *(P-18)*.
- One SQL spelling of each predicate **and of the effective-requested expression** in a new
  `services/commands/stock_report/_predicates.py` (ORM clauses **and** the `text()` fragments
  the raw statements need), so no site hand-types the pair or the `COALESCE` — the §9 rule-16
  lesson (`resolved_early`) applied to a two-column state.
- Model docstrings that become false and are rewritten: `stock_report_snapshot_version.py`
  ("closing **is** their lifecycle"; "a future scheduled activation does not need a schema
  change") and `stock_report_item_snapshot.py` ("active while `closed_at IS NULL`"; "one
  row's frozen demand").

### 3.2 New columns on `stock_report_snapshot_versions`

| Column | Type | Meaning |
|---|---|---|
| `title` | `String(200)`, nullable | the user's note; editable in any state. Stripped; empty or whitespace-only → `null` *(P-24)*. |
| `scheduled_activation_at` | `DateTime(tz)`, nullable | when a **draft** activates itself. Null = no schedule. Cleared by activation and by the user; the row is gone on delete. Check `ck_…_schedule_only_on_draft` (`scheduled_activation_at IS NULL OR active_at IS NULL`). |
| `scheduled_activation_keeps_active_missing` | `Boolean`, not null, server default `false` | what a **scheduled** activation does with the rows the draft typed no missing for: keep the active version's value (`true`) or reset to 0 (`false`, the owner's default: "a new active one should reset its missing"). Read from **this column at fire time**, never from the scheduler payload *(P-5)*. May be stored on a draft with no schedule *(P-14)*. A manual activation ignores it and uses its body *(R-6)*. *(O-9)* |

The delayed-scheduler row (§5) is the mechanism; these columns are the user-facing truth.
Revision 4's `scheduled_activation_refreshes_requested` is **gone** *(O-1)*: a scheduled
activation has no refresh choice to store. The missing flag above takes its place in the same
shape, for a different question.

### 3.3 The requested quantity on `stock_report_item_snapshots` *(O-1, O-2)*

| Column | Type | Meaning |
|---|---|---|
| `quantity_requested_scanner` | `Integer`, **nullable** | the Scanner value frozen at activation (or at a direct active create). **NULL exactly while the version is a draft**: check `ck_…_scanner_iff_activated` (`(quantity_requested_scanner IS NULL) = (active_at IS NULL)`). Re-frozen by a refresh of the active version. Check `ck_…_quantity_requested_scanner_nonneg`. |
| `quantity_requested_manual` | `Integer`, nullable | the user's override; NULL = none. Set and cleared by the requested-quantity route (§4.11); cleared by a refresh with `keep_manual_requested=false`. Never written by Scanner. Check `ck_…_quantity_requested_manual_nonneg`. |

This is the **rename** of today's `quantity_requested` (non-null, always frozen) into the first
column, plus the second. Today's column name is gone from the table on purpose: the wire field
`quantity_requested` keeps its name but becomes a **derived** value (§3.4), and a column with the
wire's name holding something else would be read as the wire value at the next site someone
writes. Every reader of the old column is in Appendix B.

Three states of one snapshot row, with the article Scanner asks 10 of and a manager's override of 7:

| | `active_at` | `…_scanner` | `…_manual` | effective (wire `quantity_requested`) |
|---|---|---|---|---|
| draft, no override | NULL | NULL | NULL | the row's live value — 10 now, 12 if Scanner sends 12 |
| draft, override | NULL | NULL | 7 | 7 |
| activated | set | 12 (frozen at activation) | 7 (kept) | 7; revert → 12 |

### 3.4 The effective requested quantity — one expression everywhere

```
effective = COALESCE(s.quantity_requested_manual,
                     CASE WHEN s.active_at IS NULL THEN r.quantity_requested
                          ELSE s.quantity_requested_scanner END)
source    = CASE WHEN s.quantity_requested_manual IS NULL THEN 'scanner' ELSE 'manual' END
```

- SQL: `_predicates.effective_quantity_requested(s, r)` (ORM) and
  `EFFECTIVE_QUANTITY_REQUESTED_SQL` (a `text()` fragment over aliases `s` and `r`) —
  every consumer already joins the row (the items list, the progress engine, the ceiling and
  the clamp, the consistency checks), so the expression costs one `COALESCE` over columns in
  hand, no extra query, no index (the zero-requested filter is not index-driven today either).
- Python: `snapshot_rules.effective_quantity_requested(snapshot, *, row)` and
  `quantity_requested_source(snapshot)`; `outstanding_quantity(snapshot, *, row)` gains the
  row; `missing_quantity_ceiling` already takes `quantity_requested=` as a keyword and its
  signature is **unchanged** — callers pass the effective value *(Q-16)*.
- On a **closed** snapshot the expression still reads the frozen Scanner column (never the
  row): `active_at` is set, so the `CASE` never reaches `r`.
- Serializer (§6): the wire keys are built by **calls** (`effective_quantity_requested(...)`,
  `quantity_requested_source(...)`) — the docs guard resolves a serializer value to the first
  mapped column it reads, and an inline `snapshot.quantity_requested_manual if … else …`
  would be documented as a nullable field. These keys are documented outside the §6.6 table,
  as `state` is.

### 3.4b A draft's missing — borrowed unless typed *(O-9)*

`stock_report_item_snapshots.quantity_missing` becomes **nullable**, with check
`ck_…_missing_set_once_activated` (`active_at IS NULL OR quantity_missing IS NOT NULL`): on
an active or closed snapshot it is the version's own number, as today; on a draft it is
**NULL until the user types a value**, and `null` on the versioned missing route clears it
again (§4.6). Draft creation (§4.1) and the webhook's draft insert (§4.9) write NULL, not 0.

The effective missing, the missing twin of §3.4:

```
effective_missing = CASE WHEN s.active_at IS NOT NULL THEN s.quantity_missing        -- own
                         ELSE COALESCE(s.quantity_missing, a.quantity_missing, 0) END -- typed, else active's, else 0
missing_source    = CASE WHEN s.active_at IS NOT NULL OR s.quantity_missing IS NOT NULL THEN 'own'
                         WHEN a.client_id IS NOT NULL THEN 'active' ELSE 'none' END
```

where `a` is the row's **active** snapshot (`LEFT JOIN … a.stock_report_item_id =
s.stock_report_item_id AND a.active_at IS NOT NULL AND a.closed_at IS NULL`, at most one row by
the partial unique index) — the join §6 already adds for `active_quantity_missing`, now also
carried by the progress engine. `_predicates.py` holds the ORM expression and the `text()`
fragment; `snapshot_rules.effective_quantity_missing(snapshot, *, active_quantity_missing)` and
`quantity_missing_source(...)` the Python. `StockReportQuantityMissingSourceEnum` (`own`,
`active`, `none`).

Three states of one draft row, the active version's missing for the article being 5:

| | draft `quantity_missing` | effective on the draft | at activation, `keep_active_missing=true` | `…=false` |
|---|---|---|---|---|
| nothing typed | NULL | 5 (borrowed) | 5 | 0 |
| typed 2 | 2 | 2 | 2 | 2 |
| typed, then cleared with `null` | NULL | 5 | 5 | 0 |
| nothing typed, no active version | NULL | 0 | 0 | 0 |

Every draft reader of `quantity_missing` reads the effective value: the serializer, the
progress engine's `target`, the items list's `missing_only`, the ceiling check on the missing
route (which compares the **typed** value being written, not the effective one). The active
version's readers are unchanged: for an activated snapshot the expression is its own column.

### 3.5 History records *(O-7)*

- `StockReportHistoryRecordTypeEnum.QUANTITY_REQUESTED_OVERRIDE = "quantity_requested_override"`
  (`ALTER TYPE stock_report_history_record_type_enum ADD VALUE IF NOT EXISTS`): written when a
  user sets or reverts the manual value on the **active** version's snapshot (§4.11), and per
  snapshot whose override a refresh clears (§4.3). `quantity_requested` on the record is the
  **effective** value after the change; `quantity_awaiting`, `priority`, `priority_order` as
  the other snapshot-driven records write them.
- New column `stock_report_history_records.quantity_requested_source`
  (`stock_report_quantity_requested_source_enum`, not null, server default `'scanner'`): where
  the record's `quantity_requested` came from.
- **One rule for every record written against a snapshot** *(Q-10)*: the priority and
  priority-order commands, apply-priorities onto the active version, activation and the
  override route all write the **effective** value and its source, through one helper
  (`snapshot_history_quantities(snapshot, row) -> {"quantity_requested", "quantity_requested_source"}`).
  Today those writers record `row.quantity_requested` (MC-6); with an override on the active
  version that would put two meanings under one record type. Scanner's
  `quantity_requested_change` records stay the row's value with `scanner`. Nothing reads the
  columns except the goal credit, which filters by type (`_goal_credit.py:26-27`), so the
  change is safe; **it lands in §12 step 2, not step 1**, because with no override the
  effective value is the frozen Scanner value, which differs from the live row whenever Scanner
  has moved, and step 1's "identical" claim would not hold.
- Drafts still write **no** history; an override on a draft leaves no record until the draft
  is activated (activation's `priority_change` record then says `manual`).

### 3.6 Schema migration (`<rev>_make_stock_report_versions_draftable`)

All existing rows have `active_at = created_at` (verified: `create_stock_report_snapshot_version.py:129-130, 153-154`),
so nothing is backfilled and every new predicate holds on day one; every existing snapshot is
activated, so the renamed column is non-null on every existing row and the `iff` check holds.

1. `active_at` → nullable on both tables (instant).
2. Recreate `uix_stock_report_snapshot_versions_active` with `WHERE active_at IS NOT NULL AND closed_at IS NULL`.
3. Recreate `uix_stock_report_item_snapshots_row_active` with the same predicate.
4. Replace `ix_stock_report_item_snapshots_workspace_priority_order` by
   `ix_stock_report_item_snapshots_version_priority_order (version_id, priority, priority_order) WHERE closed_at IS NULL`.
5. Versions: add `title`, `scheduled_activation_at`, `scheduled_activation_keeps_active_missing`
   *(O-9)*, the `closed_implies_activated` check, the `schedule_only_on_draft` check, and
   `ix_stock_report_snapshot_versions_workspace_created_at`.
6. Snapshots *(O-2)*: `ALTER TABLE … RENAME COLUMN quantity_requested TO quantity_requested_scanner`
   (instant), drop its NOT NULL and server default, rename its nonneg check; add
   `quantity_requested_manual` and its nonneg check; add `ck_…_scanner_iff_activated`; add the
   `closed_implies_activated` check. *(O-9)*: drop `quantity_missing`'s NOT NULL and server
   default (every existing snapshot is activated and keeps its value); add
   `ck_…_missing_set_once_activated`; the existing nonneg check stays (NULL passes it).
7. History *(O-7)*: create `stock_report_quantity_requested_source_enum`, add
   `quantity_requested_source` with the server default; `ALTER TYPE
   stock_report_history_record_type_enum ADD VALUE IF NOT EXISTS 'quantity_requested_override'`.
8. `ALTER TYPE delayed_scheduler_type_enum ADD VALUE IF NOT EXISTS 'stock_report_version_activation'`,
   `ALTER TYPE task_type_enum ADD VALUE IF NOT EXISTS 'stock_report_version_activation'` and
   `ALTER TYPE stock_report_repair_target_kind_enum ADD VALUE IF NOT EXISTS 'snapshot_version'`
   (the repair target of the scheduler and membership kinds, §7) *(R-4)* — in this same
   revision, which is safe because nothing in it uses the values (Postgres 18); enum values
   are never removed on downgrade (`f4a1c9d8e2b0` precedent) *(P-22)*.
9. Downgrade **raises** if any version has `active_at IS NULL` or any snapshot has
   `quantity_requested_manual IS NOT NULL` (a manual value has no home in the old schema),
   then reverses the schema: drop the manual column and the new checks, rename the column
   back, restore NOT NULL and the default on both requested and missing (no draft ⇒ no NULL
   missing), drop the history column and its type *(P-22)*.

`tests/unit/domain/stock_report/test_schema_contract.py` is updated for every predicate, name
and check.

## 4. Commands

Every command below: `maybe_begin`; MC-1 lock order (rows → snapshots → assignments); events
collected inside and dispatched after the block; `run_service` as the HTTP boundary; refusals
as `ValidationError` with a `STOCK_REPORT_*` identity. The advisory lock
`stock_report_order:<ws>` comes first in every command that reads or writes positions; the
missing-quantity command deliberately takes none today (rows → snapshot) and keeps that shape
*(P-19)*; the requested-quantity command (§4.11) takes the same shape.

### 4.1 `create_stock_report_snapshot_version` — gains an optional body

`POST /snapshots/versions`; body optional, `{"draft": false, "title": null,
"scheduled_activation_at": null, "scheduled_activation_keeps_active_missing": false}`
(Pydantic, `extra="forbid"`). **A no-body call behaves exactly as today** *(P-8)*. Roles unchanged.

- `draft=false`: today, plus `title`. The freeze writes `quantity_requested_scanner` from the
  live rows (the renamed column); `quantity_requested_manual` NULL; `quantity_missing` 0 as
  today. Either schedule key **sent** (`model_fields_set`, whatever its value) with
  `draft=false` → 422 `STOCK_REPORT_VERSION_NOT_DRAFT`; the documented default body with
  `draft=false` is accepted *(R-9)*.
- `draft=true`: same row lock and copy of the **membership** (one snapshot per live row:
  priority null, **missing NULL** *(O-9)*, resolved 0, counters copied), **no** requested value —
  `quantity_requested_scanner` NULL, `quantity_requested_manual` NULL *(O-1)* — **no** close
  of the active version, `active_at=None` on the version and its snapshots. With
  `scheduled_activation_at`, the scheduler row is created in the same transaction (§5.2).
  `scheduled_activation_at` is a Pydantic `AwareDatetime` (naive → 422) and must be `> ctx.now`
  (else 422 `STOCK_REPORT_SCHEDULE_IN_THE_PAST`) *(P-13)*. **Normalised to UTC at write**
  (`.astimezone(timezone.utc)`) before it reaches the column and the scheduler payload *(Q-5)*:
  v8's own example carries `+02:00`, and a string comparison at fire time would judge every
  such schedule "moved" and skip it silently.
- The close-freeze, the snapshot lock and the `previous` lookup all take the **active**
  predicate: a direct create must never close or lock a draft.
- `stock_report_snapshot_version:created` `extra` gains `state` and `title`. (v6 refetches
  the board on `:created`; a draft's `:created` makes that a harmless extra refetch.)
- **Known window** (documented, accepted like S3): the demand webhook takes no advisory lock,
  so a row it creates in the same instant a draft is being created can miss that draft (each
  transaction cannot see the other's uncommitted row). §4.12's membership kind reports it,
  repair closes it, and §4.2 step 4 closes it before the draft can ever be published.

### 4.2 New `activate_stock_report_snapshot_version`

`POST /snapshots/versions/{client_id}/activate`, body optional
`{"keep_active_missing": false}` (bool, default `false` = reset) *(O-9)*. Roles: admin,
manager. Also the worker's entry point (§5.3). The requested quantity has no flag *(O-1: the
live Scanner value is always the one frozen)*; the flag is about **missing**: for every row the
draft typed no missing for, `true` carries the active version's missing over, `false` starts
the new board at 0. The frontend shows the choice in a drawer.

**The body model has that one field and `extra="forbid"`** *(Q-8)*: `body:
_ActivateSnapshotVersionBody | None = None`. FastAPI 0.115.12 ignores the body of a route that
declares none, so without a model a v7-built client sending `{"refresh_quantity_requested":
false}` would be silently accepted. Reproduced on the installed version: no body → 200, `{}` →
200, an unknown key → 422, non-JSON → 422. **Manual activation uses the body's flag only** and
ignores the draft's stored `scheduled_activation_keeps_active_missing` *(R-6)*; the reference
file tells the frontend to pre-fill the drawer from the stored value.

**"Scheduled" ⇔ `expected_scheduled_activation_at` is present in `incoming_data`** *(R-6)*: the
handler passes it, the HTTP route never does. It is compared **as an aware datetime**
(`datetime.fromisoformat(expected)` against the stored `timestamptz`), never as a string *(Q-5)*.

1. Advisory lock → every live row `FOR UPDATE` (sorted) → every **open** snapshot `FOR UPDATE` → the version `FOR UPDATE` → its `ACTIVE` scheduler row, if any.
2. 404 if absent/foreign; 422 `STOCK_REPORT_VERSION_NOT_DRAFT` unless a draft — both raised
   refusals that change nothing. **Scheduled only** *(P-5, card 4 "skip when superseded")*, a
   **skip is a return, not a raise** *(Q-2)*: `maybe_begin` rolls back on exception
   (`services/commands/utils/transaction.py`), so a raised skip would undo the very clear it
   must commit, the draft would keep a past schedule with no `ACTIVE` row, repair would
   recreate the row, and it would fire and skip again forever. The command returns
   `{"skipped": "<reason>"}` and commits. The three rules:
   - **moved**: the stored `scheduled_activation_at` differs from
     `expected_scheduled_activation_at` (the schedule was moved or cleared) → return, touch
     nothing, emit nothing: the new schedule is still pending;
   - **hand-published**: the current active version's `active_at` is **later than** the
     scheduled time (a board went live after this fire was due — by hand, or another draft's
     fire) → clear the schedule, `CANCELED` the row, emit `:updated`;
   - **later plan due**: another draft of the workspace is also due (`scheduled_activation_at
     <= ctx.now`) and sorts **after** this one on the tuple `(scheduled_activation_at,
     created_at, client_id)` *(Q-6, card 5: an equal time is won by the draft created later, in
     either processing order)* → clear, `CANCELED`, emit `:updated`.
   The `:updated` for a skipped draft carries `extra`: `title`, `scheduled_activation_at: null`
   (v8 §5.21 promises it). The handler logs the reason at info with the token
   `STOCK_REPORT_SCHEDULE_SUPERSEDED:` so the identity stays scannable in logs and in `api.md`
   (the docs guard's identity regex needs it there; v7 §8 lists it as "never in an HTTP response").
3. Close the active version exactly as 4.1 does (freeze + `closed_at`, `:closed` event).
   **Order is load-bearing**: step 3 precedes step 6 because both partial unique indexes are
   checked per statement and are not deferrable *(R-2)*.
4. **Reconcile the row set** — the safety net for §4.1's window and for §4.12's kind: insert a
   snapshot (priority null, missing NULL, resolved 0, counters copied, both requested columns
   NULL for the moment) for every live row the draft has none for, `ON CONFLICT
   (version_id, stock_report_item_id) DO NOTHING` (target: `uq_stock_report_item_snapshots_version_row`);
   `snapshot_count` follows. With live membership *(O-3)* this is expected to add nothing.
5. **Freeze, settle the missing and stamp the snapshots in ONE statement** *(Q-1, O-9)*:
   ```sql
   UPDATE stock_report_item_snapshots s
   SET quantity_requested_scanner = r.quantity_requested,
       quantity_missing = COALESCE(s.quantity_missing,                      -- typed on the draft
                                   CASE WHEN :keep THEN a.quantity_missing END,  -- the closing board's
                                   0),                                       -- reset
       active_at = :now,
       quantity_in_queue = r.quantity_in_queue, quantity_in_progress = r.quantity_in_progress,
       quantity_awaiting = r.quantity_awaiting
   FROM stock_report_items r
   LEFT JOIN stock_report_item_snapshots a
          ON a.stock_report_item_id = r.client_id AND a.version_id = :previous
   WHERE s.version_id = :v AND r.client_id = s.stock_report_item_id
   ```
   `:previous` is the version step 3 just closed (`NULL` → the join is empty and the fallback is
   0); `:keep` is the body's `keep_active_missing`, or for a scheduled fire the draft's stored
   `scheduled_activation_keeps_active_missing` read now *(P-5)*. Deleted rows included (a
   snapshot of a deleted row is unreachable anyway and the checks need values).
   `ck_…_scanner_iff_activated` is `(scanner IS NULL) = (active_at IS NULL)` and
   `ck_…_missing_set_once_activated` is `active_at IS NULL OR quantity_missing IS NOT NULL`;
   both are evaluated per statement, so the Scanner column, the missing and `active_at` must
   land together: filling either column first, or stamping `active_at` first, violates a check
   on every snapshot of a non-empty draft. Revision 5 had them as two steps in the wrong belief
   that one order was safe; neither is. `quantity_requested_manual` is **kept** *(O-4)*.
6. **One UPDATE** on the version sets `active_at = ctx.now` **and** clears
   `scheduled_activation_at` — `ck_…_schedule_only_on_draft` is checked per statement, so two
   statements in that order would fail on every scheduled draft *(R-2)*. `active_at` is the
   **fire time**, not the scheduled time *(R-15)*, the same `:now` as step 5. The scheduler row
   `CANCELED` (a fired one is already `FIRED`). The missing settled by step 5 is then
   **clamped** to the effective ceiling in one bulk statement (§4.3d shape) — a carried or
   typed value can exceed what the live counters leave uncovered.
7. **History**: one `priority_change` record per snapshot whose priority is set, one bulk insert
   (`priority`, `priority_order`, the **effective** `quantity_requested` and its
   `quantity_requested_source` through the §3.5 helper *(O-7, Q-10)*, the row's live
   `quantity_awaiting`, the activating user, `created_at = now`). Unprioritised rows get none.
8. **Events**: `:closed` for the previous version and **`stock_report_snapshot_version:activated`**
   (`extra`: `snapshot_count`, `title`, `scheduled: bool`, `keep_active_missing: bool`). **No
   per-snapshot `:updated` at activation** — not for the freeze, not for the missing, not for
   the clamp; clients refetch on `:activated` *(P-16)*.
9. Response: `{"stock_report_snapshot_version": <serialized version>}`, column-only as create
   returns today; `progress` stays on the reads *(R-7)*. A skip (step 2) returns
   `{"skipped": …}` to the handler only; the HTTP route can never produce one.

### 4.3 New `refresh_stock_report_snapshot_version_requested` — the active version only

`POST /snapshots/versions/{client_id}/refresh-requested`, body optional
`{"keep_manual_requested": true}` (bool, default `true`) *(O-6)*. Roles: admin, manager.

- Target: **the active version only**. A draft has nothing to refresh (its requested and its
  rows are live, O-1/O-3); a closed version is history. Either → 422
  **`STOCK_REPORT_VERSION_NOT_ACTIVE`** (v7's `STOCK_REPORT_VERSION_IS_CLOSED` on this route is
  replaced; v8 lists it).
- Locks: advisory → live rows `FOR UPDATE` → the version's open snapshots `FOR UPDATE` → the version.
- (a) `UPDATE s SET quantity_requested_scanner = r.quantity_requested … WHERE version_id = :v
  AND closed_at IS NULL AND r.is_deleted IS FALSE AND s.quantity_requested_scanner <>
  r.quantity_requested RETURNING …` — changed rows only.
- (b) `keep_manual_requested=false`: `UPDATE s SET quantity_requested_manual = NULL … WHERE
  version_id = :v AND closed_at IS NULL AND quantity_requested_manual IS NOT NULL RETURNING …`;
  one `quantity_requested_override` history record per cleared snapshot (source `scanner`,
  effective = the freshly frozen Scanner value) *(O-7)*. `true`: overrides untouched — a later
  revert lands on the refreshed Scanner value.
- (c) Reconcile new live rows into the version (as 4.2 step 4, then the Scanner column from
  the row in the same statement). A snapshot added to the active version gets the **version's
  `active_at`**, not `now`; counters copied; resolved 0; no history; no per-snapshot event *(P-15)*.
- (d) Clamp `quantity_missing` to its effective ceiling in one bulk statement (the
  `_CLAMP_STATEMENT` shape keyed by `version_id`).
- Events: `stock_report_item_snapshot:updated` per snapshot changed by (a), (b) or (d) — its
  `extra` carries the two requested columns (§4.10) — plus
  **`stock_report_snapshot_version:refreshed`** (`extra`: `snapshot_count`, `changed`, `added`,
  `keep_manual_requested`). `changed` counts snapshots whose **effective** requested changed.
- Response: `{"stock_report_snapshot_version": <version>, "changed": n, "added": m}`.
- **Progress can go down** *(R-10; owner: "if requested is reshaped, so is progress — that is
  fair")*: a refresh re-freezes what the version set out to do, so `quantity_target`,
  `items_completed` and the completion ratio may drop mid-version. The v6 promise "completion
  never goes backwards" has that one exception (v7 §0.0), now shared with §4.11: a manual
  requested change moves the target the same way. Criterion: a refresh that raises the
  effective requested on a completed snapshot drops `items_completed` by 1.

### 4.4 `apply_stock_report_snapshot_version_priorities` — target becomes a parameter

Route unchanged; `{client_id}` stays the **source**; body **optional**
`{"target_version_id": null}`; **a no-body call behaves exactly as today** *(P-8)*.

- `null` target → the active version, resolved **after** the advisory lock *(R-3)*; a draft's
  id → that draft.
- Refusals: the target must be open (`STOCK_REPORT_TARGET_VERSION_IS_CLOSED`); source ≠ target.
  For the exact v6 case — source is the active version and the target is omitted — the
  identity stays **`STOCK_REPORT_SOURCE_VERSION_IS_ACTIVE`**, since v6 published it; every
  other source = target case → `STOCK_REPORT_SOURCE_IS_TARGET` *(P-8)*.
- The source may be closed, active or another draft. Only priorities move: the manual
  requested values of the source are **not** copied (they belong to a version's own plan).
- Locks: advisory → the target's open snapshots. The write statement carries
  `s.version_id = :target` beside `s.closed_at IS NULL` *(P-8)*.
- **No history records when the target is a draft** (owner: draft edits write no history);
  the active target keeps today's records *(P-8)*.
- The response serializes each changed row with **the target version's** snapshot (§4.6's
  loader), not the active one *(P-7)*.

### 4.5 New `update_stock_report_snapshot_version` — title and schedule

`PATCH /snapshots/versions/{client_id}`, body with any of `title`, `scheduled_activation_at`,
`scheduled_activation_keeps_active_missing` *(O-9)*. Roles: admin, manager.

- Absent vs `null` is read from `model_fields_set` (`exclude_unset=True`): omitted keys are
  untouched; `title: null` clears; `scheduled_activation_at: null` unschedules. `{}` changes
  nothing and emits no event *(P-14)*.
- `title` on any state, stripped, empty → `null` *(P-24)*.
- The two schedule keys only on a draft (422 `STOCK_REPORT_VERSION_NOT_DRAFT`);
  `scheduled_activation_at` is an `AwareDatetime` and must be `> ctx.now` (422
  `STOCK_REPORT_SCHEDULE_IN_THE_PAST`) *(P-13)*. Setting the missing flag alone on an
  unscheduled draft stores it and creates no scheduler row *(P-14)*.
- `scheduled_activation_at` normalised to UTC at write, as §4.1 *(Q-5)*.
- Locks: advisory → the version `FOR UPDATE` → its `ACTIVE` scheduler row *(P-19)*.
- Scheduler side effect: §5.2. One event `stock_report_snapshot_version:updated`
  (`extra`: `title`, `scheduled_activation_at`, `scheduled_activation_keeps_active_missing`).
- Response: `{"stock_report_snapshot_version": <serialized version>}` *(R-7)*.

### 4.6 The row-level edits — the version is the folder

Four **new versioned routes**, the first three with the same bodies as their board twins and
**the same roles as their board twins** *(card 1: admins, managers and sellers edit a draft's
priority and order because they edit the board's; no role logic inside any command)*:

| Route | Roles | Target |
|---|---|---|
| `PATCH /snapshots/versions/{version_id}/items/{client_id}/priority` | admin, manager, seller | the row's snapshot in that version |
| `PATCH /snapshots/versions/{version_id}/items/{client_id}/priority-order` | admin, manager, seller | same |
| `PATCH /snapshots/versions/{version_id}/items/{client_id}/missing-quantity` | admin, manager, worker | same |
| `PATCH /snapshots/versions/{version_id}/items/{client_id}/requested-quantity` *(O-4, §4.11)* | admin, manager, seller | same |

- The version must be **open**: closed → 422 `STOCK_REPORT_VERSION_IS_CLOSED`; absent/foreign
  version → 404; a live row with no snapshot in that version → 404 (with live membership this
  is only §4.1's window or a row created after the active version).
- The three **existing** routes `PATCH /items/{client_id}/priority|priority-order|missing-quantity`
  stay **unchanged on the wire** as the active-version shortcut. The shortcut's service opens
  the transaction (`maybe_begin`), takes the command's **first lock** (the advisory lock for the
  two priority routes, the row lock for missing — both re-entrant within the transaction),
  resolves the active version **under that lock**, and calls the same command in the same
  transaction *(R-3)*: a shortcut PATCH that waits behind an activation lands on the **newly**
  active version and returns 200, exactly as today's post-lock discovery does. It maps both
  "no active version" and "row not in the active version" to today's
  **422 `STOCK_REPORT_NO_ACTIVE_SNAPSHOT`**; the versioned routes keep the 404s *(P-7)*. The
  requested-quantity route has **no** shortcut: it is new, and the frontend is always inside a
  version.
- `_load_row_with_snapshot` gains `load_version_snapshot(session, ws, row_id, version_id)` and
  `serialize_row_with_version_snapshot(...)`, which also fetch the row's **active** snapshot's
  `quantity_missing` (one correlated scalar subquery, the `apply_stock_demand._active_snapshot_column`
  shape) for the payload's `active_quantity_missing` *(O-5)*; every versioned command and
  apply-priorities answer with the **target version's** snapshot *(P-7)*.
- `lock_snapshot_and_groups`, `_ordering._group_where`, `append_to_priority_group`,
  `close_priority_gap`, `shift_within_group` become **version-scoped**; the commands take
  `version_id` from `incoming_data`.
- Priority PATCHes: advisory → target snapshot + its source and destination groups **in that
  version**. Missing and requested PATCHes: rows → snapshot, no advisory (today's shape) *(P-19)*.
- **History**: the two priority commands and the requested command write their record only
  when the target version is **active**, decided on the **post-lock read** of the version — a
  draft edit can queue behind that draft's activation, and after the lock the target *is*
  active *(P-20)*. The missing-quantity command writes no history today and still does not.
- `missing-quantity` on a draft *(O-9)*: the body becomes `{"quantity_missing": <strict int
  ≥ 0> | null}` — a number **types** the draft's own value, `null` **clears** it so the row
  borrows the active version's again. On the active version `null` → 422
  `STOCK_REPORT_VERSION_NOT_DRAFT` (an activated snapshot always has its own number). The
  ceiling check applies to the typed number, with the **effective** requested (the live row or
  the override; `requested − (row live covered + resolved)`, resolved 0 on a draft), same
  refusal identity. Same stored value (including `null` on a row with nothing typed) → 200
  no-op, no event. The v6 shortcut route keeps its non-null body.

### 4.7 The row-deletion cascade — active snapshot closes, draft snapshots are deleted *(P-1)*

A draft snapshot cannot be closed: the `closed_implies_activated` check forbids it, and
stamping a fake `active_at` would forge a history the row never had. So step (iii) becomes:

- the row's **active** snapshot: today's treatment — close its group's gap, then close it with
  counters frozen at 0;
- each **draft** snapshot of the row: close its gap in that draft's `(version_id, priority)`
  group, then **hard-delete** it and decrement that draft's `snapshot_count`.

No new event: the coalescer already drops snapshot events for a row that carries `:deleted`.
`lock_active_snapshots_and_groups` (shared with the Scanner delete webhook) locks the rows'
**open** snapshots and every open snapshot of the same `(version_id, priority)` groups.

Scope note: this edits `_delete_stock_report_item_cascade.py`, `delete_stock_report_item.py`
and `process_stock_demand_deleted.py`, the files of open item **S3** (`REMAINING_WORK.md`).
S3 is **not** folded in; draft creation takes the advisory lock, so no draft snapshot can
appear mid-delete, and this change does not widen S3's window.

### 4.8 New `delete_stock_report_snapshot_version` — drafts only

`DELETE /snapshots/versions/{client_id}`: 422 `STOCK_REPORT_VERSION_NOT_DRAFT` otherwise.
Roles: admin, manager. Locks: advisory → **the version `FOR UPDATE` first** → the draft's
snapshots `FOR UPDATE` → its `ACTIVE` scheduler row. The version comes before its snapshots
(a change from revision 4's P-19 order) because the demand webhook (§4.9) locks a draft's
version row before inserting into it: whichever of the two holds the version row, the other
waits, and the delete then sees every snapshot the webhook added — a snapshot inserted
between the delete's snapshot statement and its version statement would otherwise make the
version `DELETE` fail on the FK. Hard delete of the snapshots, then the version; the scheduler
row `CANCELED`. Nothing references a draft (history records point at rows; resolved is 0; no
assignment points at a snapshot; a repair record's target id is a string with no FK). Event
`stock_report_snapshot_version:deleted`. Response `{"client_id": …}` (the `DELETE /items`
precedent) *(R-7)*. `states.md` §2 records the exception to "closing is the lifecycle".

### 4.9 `apply_stock_demand` — a new row joins every draft *(O-3)*

After step 6 (the rows locked by identity) and before the history insert, for the rows the
webhook **created** in this call (`created_client_ids`, filtered to those it then locked):

1. `SELECT client_id FROM stock_report_snapshot_versions WHERE workspace_id = :ws AND
   active_at IS NULL ORDER BY client_id FOR UPDATE` — the drafts, **locked**, and the insert
   uses exactly this result (never an earlier read: a draft deleted meanwhile is gone by the
   time the lock is granted, §4.8).
2. One `INSERT INTO stock_report_item_snapshots (…) SELECT …` over drafts × created rows:
   priority null, **missing NULL** *(O-9)*, resolved 0, counters copied from the row (all 0 on
   a new row), both requested columns NULL, `active_at` NULL; `ON CONFLICT (version_id,
   stock_report_item_id) DO NOTHING`; `RETURNING version_id`.
3. `snapshot_count += <inserted>` per draft, one statement.

- **Statement bound** *(Q-4, card 7)*: the all-new path runs exactly 8 statements today, and
  `test_apply_stock_demand.py::test_c6a/c6b` hold `<= 8` (intention §8B D6). The three
  statements above make the bound **11**, still **constant in batch size and in draft count**
  — the ratified promise was "does not grow with the batch", and that is kept. The tests
  become `<= 11`, with cases for 0 and ≥ 2 drafts present; the three statements run before the
  deadline check, which stays last.
- The **active** version is untouched: a row created after activation joins it only at
  refresh (§4.3c), unchanged from v6.
- No snapshot event: the row's `stock_report_item:created` is the signal; v8 tells the
  frontend that a draft page refetches on it.
- Lock order stays MC-1: rows (held) → version rows → snapshot inserts. The webhook's
  `lock_timeout` covers the version-row wait, so a webhook queued behind a long activation
  still answers 503 `StockDemandDeadlineExceeded` and Scanner retries, as today.
- Rows are never resurrected (the identity index is partial on `is_deleted = false`, and the
  insert is `ON CONFLICT DO NOTHING`), so there is no "re-add a cascaded snapshot" case.
- A row that arrives with `quantity_requested = 0` still joins the drafts (the draft's
  `include_zero_requested` filter hides it as on the board).

### 4.10 Sites that change predicate (full table in Appendix A)

- → **active**: `list_stock_report_items` default join, `load_active_snapshot`,
  `get_stock_report_active_snapshot_version`, `get_stock_report_missing_summary`,
  `_snapshot_resolved`, `_snapshot_missing._CLAMP_STATEMENT` **(drafts are not clamped on
  assignment creation; see P-4 in §7)**, `create_stock_task_assignments` discovery,
  `process_items_processed` discovery, `apply_stock_demand._active_snapshot_column`, the
  shortcut routes' target, `create…version`'s freeze, lock and `previous` statements.
- → **open, grouped per version**: the cascade and its lock helper (§4.7), `consistency` and
  `repair_stock_report` (§7) *(P-3)*.
- stays **open**: `serializers.serialize_stock_report_item_snapshot` (counters),
  `_version_progress._live_or_frozen`.

### 4.10b The two requested columns on `stock_report_item_snapshot:updated` — every site *(P-17, O-2)*

The coalescer drops an `:updated` whose `extra` equals `snapshot_values(snapshot)`, so the
builder, `snapshot_values` and **every** RETURNING that feeds the builder gain
`quantity_requested_scanner` and `quantity_requested_manual` **together**:
`_ordering._RETURNING_COLUMNS`, `set_…priority._MOVER_RETURNING`,
`set_…priority_order._MOVER_RETURNING`, `set_…missing_quantity._RETURNING`, the new
`set_…requested_quantity._RETURNING`, `_snapshot_missing._CLAMP_STATEMENT` (`text()` RETURNING
plus `.columns`), `_snapshot_resolved._RETURNING`, the apply-priorities `text()` RETURNING plus
`.columns`, the refresh statements; repair goes through `snapshot_values`.

The event carries the **stored** columns, not the effective value: `snapshot_values` is built
from the ORM instance without the row, and several RETURNING statements have no row join. v8
states the one rule for the frontend (§3.4): effective = `manual ?? scanner ?? the row's live
quantity_requested`, and the row's live value arrives on `stock_report_item:updated` as it
does today. Criterion: a refresh that changes only `quantity_requested_scanner` emits the
event (the no-op drop would otherwise swallow it); a revert that changes only
`quantity_requested_manual` emits it.

### 4.11 New `set_stock_report_item_snapshot_requested_quantity` *(O-2, O-4)*

`PATCH /snapshots/versions/{version_id}/items/{client_id}/requested-quantity`, body
`{"quantity_requested": <strict int ≥ 0> | null}` (`null` = revert). Roles: admin, manager, seller.
The field is `Annotated[StrictInt, Field(ge=0)] | None`, **required, no default** *(Q-9)*:
`{}` → 422, `-1` → 422, `"3"` → 422, `null` → 200 (`StrictInt` alone accepts `-1`; reproduced).

1. Locks: the row `FOR UPDATE` → the version's snapshot of it `FOR UPDATE` (the missing
   command's shape, no advisory) → the version (plain read, post-lock).
2. 404 version / row / no snapshot in that version; closed → 422 `STOCK_REPORT_VERSION_IS_CLOSED`.
3. Write `quantity_requested_manual = :value` (a number or NULL). **The no-op compares against
   the stored manual column, never the effective value** *(Q-7, card 6: typing the value Scanner
   already shows PINS it)*: a typed 10 on a snapshot with no override is stored, the row shows
   `manual`, and the draft stays at 10 when Scanner moves to 14. Same stored value → 200, no
   write, no event; `null` on a snapshot with no override is the one no-op among reverts. v8
   §5.22 says "already the value in force"; the ship-time reference file (§8) corrects that
   sentence, and v8 is never edited.
4. On the **active** version only: clamp this snapshot's `quantity_missing` to the new
   effective ceiling when it fell (the single-row `_CLAMP_STATEMENT` shape, keyed by version and
   row), in the same transaction; one `quantity_requested_override` history record (effective
   value after the change, source `manual` on a set, `scanner` on a revert) *(O-7)*, decided
   post-lock *(P-20)*. On a draft: no clamp (a draft's missing is a guide, re-clamped at
   activation) and no history.
5. Events: `stock_report_item_snapshot:updated` for the snapshot (and the clamp's, coalesced
   into one). Response: `{"stock_report_item": <row with THIS version's snapshot>}`.
6. Progress moves with it on any open version (the target is the effective requested); on the
   active version that is the second and last exception to "completion never goes backwards"
   (§4.3).

A revert is one `NULL` write, whatever the state: on a draft the effective value falls back
to the live row, on the active version to the frozen Scanner value — the same column, the
same route, no branch *(O-2)*.

### 4.12 Consistency: draft membership *(O-3)*

New kind `draft_membership_mismatch` (target kind `snapshot_version`): a draft that lacks a
snapshot for a live row (§4.1's window, or a repair-recreated row), or holds one for a deleted
row (a cascade that did not run). Repair inserts the missing snapshots (as §4.9 does) and
deletes the stray ones — a stray may hold a priority, so repair closes its gap in the draft's
group and decrements `snapshot_count`, under repair's lock sequence *(Q-18)*. The active
and closed versions are **not** checked by this kind: their membership is fixed by design.
Divergence fields: §7's table *(Q-13)*.

## 5. Scheduled activation — through the delayed scheduler

The runner mapping, the cancel lookup and a handler exist for `pending_step_completion`, but
that producer is commented out (`transition_step_state.py:211-251`): **this is the delayed
scheduler's first live producer** *(P-10)*. The chain is three processes — `delayed-scheduler`
→ `task-router` → `tasks-worker` (`Procfile`) — none of which `python run.py` starts.

### 5.1 Pieces

- **Four registries, all four** *(R-1)*: `DelayedSchedulerTypeEnum.STOCK_REPORT_VERSION_ACTIVATION`;
  `TaskType.STOCK_REPORT_VERSION_ACTIVATION`; the pair in the runner's `DELAYED_TYPE_TO_TASK_TYPE`;
  **`TaskType.STOCK_REPORT_VERSION_ACTIVATION: "queue:tasks"` in the router's `QUEUE_MAP`**
  (`services/infra/execution/task_router.py`) — without it `_route_open_tasks` logs
  `no queue mapped` and leaves the task OPEN forever while the scheduler row is already
  `FIRED`, and fifty such rows starve routing for every other task type; the handler in
  `tasks_worker.py`'s `HANDLER_MAP`; the DB enum values from §3.6(8).
- Typed payload `domain/execution/payloads/stock_report_version_activation.py`
  (`StockReportVersionActivationPayload`: `workspace_id`, `version_id`, `scheduled_by_user_id`,
  `scheduled_for` = `scheduled_activation_at.astimezone(timezone.utc).isoformat()` *(Q-5)*),
  built with `asdict()` *(P-11, P-5)*. **The payload is not a
  copy of the draft**: the draft's content is read from the tables at fire time, so every edit
  a user makes to a scheduled draft — priorities, missing, manual requested — is what gets
  published, over the live Scanner values of that moment.
- Handler `handle_activate_stock_report_snapshot_version(payload, task_client_id)` in the
  **new** directory `services/tasks/stock_report/`: opens `get_db_session()`, builds a
  `ServiceContext(identity={"workspace_id", "user_id": scheduled_by_user_id},
  incoming_data={"client_id": version_id, "expected_scheduled_activation_at": scheduled_for}, session)`
  and calls `activate_stock_report_snapshot_version` **directly, not through `run_service`**.
  A `{"skipped": reason}` return (§4.2 step 2) is logged at info with the
  `STOCK_REPORT_SCHEDULE_SUPERSEDED:` token and completes *(Q-2)*. It catches `DomainError`
  (the base: `NotFound` for a deleted draft, `ValidationError` for "not a draft") → logs at
  info and completes, no retry; anything else propagates for the worker's normal retry
  *(P-6)*. Registered in `tasks_worker.py`'s handler map.
- A reset phase cancels this type's `ACTIVE` rows whose `event_client_id` is one of the
  workspace's versions, run **immediately before** `delete_stock_report_snapshot_versions`
  (`reset_app.py`), since it needs the version ids that phase removes *(P-21, R-11)*.
- `CLAUDE.md` "Running the app" gains one line naming the three processes scheduling needs *(P-10)*.

### 5.2 Keeping the column and the scheduler row in step

At most one `ACTIVE` row per draft, found by `(event_client_id = version_id, type, state = ACTIVE)`:

| Change | Scheduler row |
|---|---|
| date set or moved | existing `ACTIVE` row → `CANCELED`; new row via `create_delayed_scheduler` with the new `scheduled_for` in the payload |
| missing flag changed | **nothing** — read from the column at fire time *(P-5, O-9)* |
| date cleared | `ACTIVE` row → `CANCELED` |
| activated by hand | `ACTIVE` row → `CANCELED`; column cleared |
| deleted | `ACTIVE` row → `CANCELED` |
| fired | the runner sets `FIRED`; the activation clears the column |

**Stale fires** *(P-5)*: the runner reads `ACTIVE` rows without a lock and can overwrite a
just-cancelled row with `FIRED` after the execution task exists. That is why the payload
carries `scheduled_for` and the activation refuses `STOCK_REPORT_SCHEDULE_SUPERSEDED` when it
differs from the stored column: a moved or cleared schedule never activates at the old time,
and the new schedule is still pending.

### 5.3 Timing and concurrency

- **Late activation is accepted** *(card 3, owner)*: a due row that the runner finds after
  downtime fires then, as the runner does today. No lateness window is built.
- **But a superseded one is skipped** *(card 4, owner: "skip when superseded")*: the runner
  fires every overdue row with no `ORDER BY`, and the router routes with none, so with
  Monday's and Tuesday's drafts both overdue the final board would depend on processing
  order, and a board published by hand at 07:00 would be replaced by a late 06:00 fire. The
  three supersede rules of §4.2 step 2 make it deterministic: the later plan wins in either
  order, and a hand-published board stands. **An equal time** is won by the draft created
  later *(card 5)*: the tuple `(scheduled_activation_at, created_at, client_id)` orders every
  pair, so "Monday upholstery push" and "Monday frames" both at 06:00 come out the same way
  every Monday. A skipped draft stays a draft with its schedule cleared, so it is visible on
  the versions page as "was scheduled, did not run".
- No latency is claimed or asserted: three hops, worker backoff and the runner's 300 s sleep
  cap while `ActivityTracker` sleeps *(P-10)*.
- The handler's activation takes the same advisory lock as every version command; a manual
  and a fired activation serialize, and the loser sees "not a draft" and skips.

## 6. Queries

- **`GET /snapshots/versions`**: gains `state` (`draft|active|closed`, optional single value;
  unknown → 422 `STOCK_REPORT_UNKNOWN_VERSION_STATE`). **Omitted → all states** *(P-12; the
  folder model shows every card)*, so v6 consumers will see drafts first with
  `active_at: null` — declared in v7 §0.0 as a nullability change. Order:
  `active_at DESC NULLS FIRST, created_at DESC, client_id DESC`. Each row gains `state`,
  `title`, `scheduled_activation_at`, `scheduled_activation_keeps_active_missing`. A draft's
  `progress` comes from the same engine: live counters against the **live** requested (or the
  override) and the draft's **effective** missing (typed, else the active version's, §3.4b).
  Roles unchanged: workers and sellers see drafts *(card 2)*.
- **`GET /snapshots/versions/active`**: unchanged.
- **`GET /snapshots/versions/{client_id}`** (new): one version with `progress` and
  `filtered_snapshot_count`, same `priority` parameter; any state; 404 absent/foreign. Roles:
  admin, manager, worker, seller, as the list *(R-14, card 2)*.
  Declared **after** `/snapshots/versions/active` — FastAPI matches the first declared route,
  and `"active"` would otherwise be read as a client id *(P-23)*.
- **`GET /items`**: gains `version_id` (optional). Omitted → the active version (workers'
  default, unchanged). Given → that version's snapshots in **any state**; 404 absent/foreign
  version; 422 `STOCK_REPORT_LIVE_STOCK_FILTER_CONFLICT` with `live_stock=true`. Ordering,
  `priority`, `missing_only`, pagination unchanged, scoped by the join's `version_id`.
  `include_zero_requested` and the outstanding rule use the **effective** requested (§3.4).
  Open ⇒ live counters, so a draft's rows show live queue / progress / awaiting beside the
  live requested. **One more `LEFT JOIN`** on every non-`live_stock` read *(O-5)*: the row's
  **active** snapshot (`stock_report_item_snapshots a ON a.stock_report_item_id = r.client_id
  AND a.active_at IS NOT NULL AND a.closed_at IS NULL`, at most one row by the partial unique
  index), whose `quantity_missing` becomes the payload's `active_quantity_missing`. Per row
  read, not per draft: every draft shares the one active value.
- **`_version_progress`**: `target` = `GREATEST(0, effective requested − effective missing)`,
  and the `quantity_requested` and `quantity_missing` sums are the effective values; the row is
  already joined, and the engine gains the same `LEFT JOIN` to the row's active snapshot as
  the items read (§3.4b). A draft's target therefore follows Scanner live, the manager's
  overrides, and the board's missing until the draft types its own.
- **`get_stock_report_missing_summary`**: reads only `quantity_missing` and joins no row
  (`get_stock_report_missing_summary.py:16-31`); **only its predicate changes** (Appendix A),
  no join is added *(Q-15)*. `consistency.missing_over_ceiling`: the effective value (it has
  the row).
- **Serializer** `serialize_stock_report_snapshot_version`: `state` via
  `version_state(version).value` (a call, so the docs guard's nullability walk skips it; never a
  conditional on `version.active_at`, which the guard would read as a nullable field); `title`,
  `scheduled_activation_at`; `active_at` documented nullable ("null while draft"), same for
  the item snapshot's.
- **Serializer** `serialize_stock_report_item_snapshot(snapshot, *, row, active_quantity_missing)`:
  - `quantity_requested` → `effective_quantity_requested(snapshot, row=row)` (a call);
  - **new** `quantity_requested_scanner` → `scanner_quantity_requested(snapshot, row=row)`: the
    live row's value on a draft, the frozen column otherwise (a call) — "what Scanner says or
    said", never null on the wire;
  - **new** `quantity_requested_source` → `quantity_requested_source(snapshot).value`;
  - **new** `active_quantity_missing` → the keyword (a bare name; the guard skips it): the
    active version's missing for this row, `null` when the workspace has no active version or
    the row has no snapshot in it; on the active version's own snapshot it equals
    `quantity_missing`.
  - `quantity_missing` → `effective_quantity_missing(snapshot, active_quantity_missing=…)`
    (a call) *(O-9)*: the draft's typed value, else the borrowed one, else 0; an activated
    snapshot's own number. **new** `quantity_missing_source` → `own` | `active` | `none`.
  All six are documented outside the §6.6 nullability table, as `state` is (§3.4).
  `stock_report_item:updated`'s row `quantity_requested` is unchanged: the live Scanner value.
- **Threading `active_quantity_missing`** *(Q-17, delegated)*: `serialize_stock_report_item(row,
  *, category, snapshot, active_quantity_missing)` passes it through. The items read joins
  `StockReportItemSnapshot` twice (the version's snapshot and the row's active one), so the
  second is an `aliased()` entity; the `live_stock=true` read, which already joins the active
  snapshot, passes that snapshot's own `quantity_missing` (or `None` when it has none); the
  command responses use the loader's scalar subquery (§4.6).

## 7. Consistency and repair — one snapshot set, one grouping *(P-2, P-3, P-4)*

**Binding sentence:** consistency and repair read the **same** snapshot set — open snapshots,
drafts included — grouped by `(version_id, priority)`; the repair lock locks that set.

- `order_density` (the existing kind): per `(version_id, priority)` over open snapshots, so a
  draft's order is repaired within its own version and never renumbered together with the
  active one. Repair's final guard then agrees with the check.
- `snapshot_version_state_mismatch` replaces `snapshot_version_closed_mismatch` and is
  **one-directional**: (i) an open snapshot in a closed version → close it (today; never
  reopen); (ii) a snapshot of an activated version whose `active_at` is NULL or differs from
  the version's → copy the version's; (iii) a snapshot with `active_at` set in a draft → set it
  NULL. **A closed snapshot in an open version is not a divergence** (that is every
  cascade-closed row) *(P-2)*. The `scanner_iff_activated` check makes a Scanner-column
  mismatch unstorable, so (ii) and (iii) also carry the Scanner column: (ii) fills it from the
  row when NULL, (iii) nulls it — in the same statement as `active_at`, for the check.
- `missing_over_ceiling`: **active snapshots only** *(P-4 option b)*, over the **effective**
  requested. A draft's missing is a guide, re-clamped at activation, and the PATCH refuses
  values above the live ceiling at edit time; the clamp on assignment creation stays
  active-only, so an assignment on a row whose draft has missing produces no divergence.
- `draft_membership_mismatch` *(O-3)*: §4.12.
- New `schedule_scheduler_mismatch` *(R-4)*: a draft with `scheduled_activation_at` set must
  have exactly one `ACTIVE` scheduler row with that `scheduled_for`, and an `ACTIVE` row of
  this type must match a draft's column. **"ACTIVE only" is deliberate**, and what follows is
  written down:
  (a) a fire **in flight** (runner committed `FIRED`, worker not yet run) shows as a divergence
  until the worker activates — constant in local development where the worker is not running;
  if repair runs meanwhile it recreates the row, the duplicate fire is skipped by the handler
  (superseded or not a draft), harmless;
  (b) a fire whose execution task **failed** (`max_try` exhausted), or whose scheduler row went
  to `ERROR` while due (`_retry_errored_schedulers` retries only rows whose `scheduled_for` is
  still in the future, so a due errored row is never retried), leaves the draft with a past
  schedule and no `ACTIVE` row: **repair is the recovery path** — it recreates the row with
  `scheduled_by_user_id` = the repairing user, and the late fire then activates (card 3) or
  skips (card 4);
  (c) an `ACTIVE` row with no matching column is `CANCELED`.
  Repair target kind: the new `StockReportRepairTargetKindEnum.SNAPSHOT_VERSION`
  (`snapshot_version`, the enum value of §3.6(8)) with a `_TARGETS` entry in
  `repair_stock_report.py`. Repair's lock sequence: rows, open snapshots (drafts' included,
  grouped per version), versions, **then scheduler rows last** *(Q-18)*. `scheduled_for` is
  compared to the column **as datetimes** *(Q-5)*. **Workspace scoping** *(Q-13)*:
  `delayed_schedulers` has no workspace column and `payload_snapshot` is JSON, so the kind
  reads the rows whose `event_client_id ∈ the workspace's version ids`; an orphan row whose
  version is already deleted is out of scope and harmless (the handler's 404 → skip). v7 tells
  the frontend that a draft whose `scheduled_activation_at` is in the past is **overdue** and
  should be shown as such — the only way a failed schedule reaches a person.

**Divergence rows, field by field** *(Q-13)* — `GET …/consistency` returns
`{kind, client_id, field, stored, expected}` (api.md:78) and api.md:135 enumerates the kinds
(`snapshot_version_closed_mismatch` leaves the list; three kinds join it):

| Kind / case | `client_id` | `field` | `stored` | `expected` | repair target |
|---|---|---|---|---|---|
| `snapshot_version_state_mismatch` (i) open snapshot, closed version | the snapshot | `closed_at` | `null` | the version's `closed_at` | `snapshot`, the snapshot |
| … (ii) activated version, snapshot `active_at` null or different | the snapshot | `active_at` | the snapshot's | the version's | same |
| … (iii) draft, snapshot `active_at` set | the snapshot | `active_at` | the snapshot's | `null` | same |
| `draft_membership_mismatch`, missing snapshot | **the version** | `stock_report_item_id` | `null` | the live row's id | `snapshot_version`, the version |
| … stray snapshot of a deleted row | the version | `stock_report_item_id` | the row's id | `null` | same |
| `schedule_scheduler_mismatch` (a)/(b) column set, no `ACTIVE` row with that `scheduled_for` | the version | `scheduled_activation_at` | the column (ISO, UTC) | `null` (no row) | `snapshot_version`, the version |
| … (c) `ACTIVE` row, no matching column | the version | `scheduled_activation_at` | `null` | the row's `scheduled_for` | same |

The repair record's `target_id` is the `client_id` column above.

## 8. Docs and guards

- **v7 stays as issued** *(O-8)*: it is with the frontend. **v8**
  (`HANDOFF_TO_FRONTEND_stock_report_snapshots_v8_20260927.md`) lists only what differs from v7
  — v7's own §10 promises exactly that shape. **The docs guard cannot read a delta file**
  *(Q-3)*: its checks search `_CURRENT_HANDOFF` for every event name, identity and the six
  assignment states, and need a nullability table per serializer; v8 has two tables, no
  states, and a computed-field table whose third column is a meaning, not a nullability. And
  v7's own tables no longer match (its snapshot table lists `quantity_requested`, now a call;
  its version table lists the removed flag). **v9**
  (`HANDOFF_TO_FRONTEND_stock_report_snapshots_v9_20260928.md`, issued 2026-09-28 because v8
  had already left) is the third delta: O-9 (the activate body's `keep_active_missing`, the
  stored flag on create / PATCH / the version shape, `quantity_missing` as the draft's
  effective value with `quantity_missing_source`, `null` on the versioned missing route, the
  drawer pre-filled from the stored flag), card 6's pin rule replacing v8 §5.22's no-op
  sentence, card 5's tie-break, and Q-8/Q-9's request validation. So **at ship, step 5 writes
  a consolidated reference file as a new file, never an edit** —
  `HANDOFF_TO_FRONTEND_stock_report_snapshots_v10_<date>.md`, v7 + v8 + v9 merged, full
  tables, computed keys outside them, adding nothing — points `_CURRENT_HANDOFF` at it, and
  moves v6, v7, v8 and v9 to `archived/` unedited. The guard's logic stays untouched; teaching it an ordered document
  list would be test-code redesign for a one-off. v8's content: drafts are live
  (requested and rows); the four requested fields on the snapshot; `active_quantity_missing`;
  the requested-quantity route; the activate body removed; the refresh body, its active-only
  target and its identity; the create and PATCH-version bodies without the refresh flag; the
  event `extra` changes; the card 4 rule, closing v7's open item; the second "goes backwards"
  exception; v7 §0.1 item 5 void; the demand webhook adding rows to drafts and the refetch it
  asks for.
- **Frontend instructions and a sequencing gate** *(P-9)*: v7 states "apply
  `stock_report_item_snapshot:updated` only when `extra.version_id` is the version the view
  shows; on `:activated` refetch the board, the active version and the missing summary; on
  `:refreshed` refetch the board". Verified in the frontend repo: today's `applySnapshotUpdate`
  ignores `version_id`, so draft edits would paint the live board, and v6 has no `:activated`
  handler. **Drafts and scheduling are not used in production until the frontend ships both.**
- `api.md`: route rows (19 → 28), the new identities **including `STOCK_REPORT_SCHEDULE_SUPERSEDED`**
  (a log token, never a response; the guard's identity regex reads api.md) *(Q-2)*; the
  divergence-kind list at api.md:135 (drop `snapshot_version_closed_mismatch`, add the three
  kinds of §7's table) *(Q-13)*.
- `states.md`: §1.5 lifecycle `draft → active → closed` and the delete exception; the
  requested-quantity derivation (§3.4) and the two columns; §2 both tables; §3.1 the cascade's
  draft branch and the webhook's draft insert; §4 the new event names and the widened snapshot `extra`.
- Docs guard: `_SNAPSHOT_EVENT_NAMES` gains `:activated`, `:refreshed`, `:updated`, `:deleted`;
  route count 19 → 28; the serializer table for the item snapshot loses `quantity_requested`
  as a column-backed field (§3.4) — the guard's own "computed keys are documented outside the
  table" rule, verified at implementation for a bare-name value.
- `CLAUDE.md`: the snapshot paragraph (drafts are live; the two predicates; the effective
  requested; the two exceptions to "never goes backwards") and the "Running" line (§5.1).

## 9. Tests (from `app/`, `BEYO_TEST_SLOT=<unique>`, baseline diff both ways)

Every row is an outcome at a public boundary; no mocked internal collaborator. Every new
behaviour armed with a mutant observed red.

Unit: `version_state` (three states; the unstorable pair raises); `is_snapshot_open` (renamed,
existing test) and `is_snapshot_active` on all four column combinations;
`effective_quantity_requested` / `scanner_quantity_requested` / `quantity_requested_source` on
the three rows of the §3.3 table plus a closed snapshot with a deleted row (never reads the
row); `missing_quantity_ceiling` and `outstanding_quantity` with the effective value; serializer
`state`, the version's fields, the snapshot's four requested/missing keys; schema contract
(predicates, checks incl. `scanner_iff_activated`, the renamed column, the group index, the
history column and enum value, the downgrade guard's two conditions); router bodies/params/roles
for every new or changed route (the requested route's `null` body, strict int, negative → 422);
docs guard; the payload dataclass round-trips through `asdict()`.

Integration, one seeded matrix per test workspace:
- **create draft** while active exists: `GET /items` and `versions/active` byte-identical before
  and after; `GET /snapshots/versions` now lists the draft first with `active_at: null`; two
  drafts coexist; `snapshot_count` = live rows; title stored; a no-body call unchanged; the
  draft's snapshots have both requested columns NULL and the read shows the row's live value.
- **live requested** (O-1): Scanner posts a new quantity for a row → `GET /items?version_id=<draft>`
  and the draft's `progress` show it; the active version's frozen value unchanged.
- **live membership** (O-3): Scanner creates a row while two drafts and the active version
  exist → both drafts hold it (unprioritised, `snapshot_count` +1 each), the active version
  does not; the row's `stock_report_item:created` is the only event; a row that arrives with
  quantity 0 joins too; two-session: a webhook queued behind a draft delete adds nothing to
  the deleted draft and answers 200 (the version-first lock of §4.8); **C6a/C6b at `<= 11`**
  with 0 drafts and with 2 drafts present, equal across batch sizes (card 7).
- **draft is invisible to**: resolved credit, the clamp on assignment creation, the demand
  webhook's history priority, missing-summary, the close-freeze of a direct create.
- **versioned edits**: groups per version (a `high` group of 3 on the active and of 2 on the
  draft, both dense); a closed `version_id` → 422; a row absent from the version → 404; the
  response carries the target version's snapshot; a draft edit writes no history; an edit that
  queues behind the draft's activation writes one (P-20); roles per route.
- **requested quantity** (O-2, O-4), each a row: set on a draft → effective = the value, scanner
  = live, source `manual`; revert on a draft → live again; set on the active → effective = the
  value, scanner frozen, `progress.quantity_target` moved, a `quantity_requested_override`
  record with source `manual`; revert on the active → the frozen value, a record with source
  `scanner`; lowering below the covered quantity on the active clamps its missing, on a draft
  does not; **pin** (card 6): typing the value Scanner shows on a snapshot with no override
  stores it, source `manual`, and the draft holds it when Scanner then moves; same stored
  manual value → no event; `null` with no override → no event; closed → 422; seller allowed,
  worker refused; `{}` → 422, `-1` → 422, `"3"` → 422 (Q-9); the event carries both columns
  and a revert that changes only the manual column emits it; a priority change on the active
  version with an override records the effective value with source `manual` (Q-10).
- **active missing beside drafts** (O-5): a draft read shows `active_quantity_missing` = the
  active snapshot's missing; a missing PATCH on the active version is visible on the draft
  read next; no active version → `null`; on the active version's own read it equals
  `quantity_missing`; a closed version's read shows the current active's value.
- **borrowed unless typed** (O-9), each a row: a fresh draft row shows `quantity_missing` =
  the active's value with source `active`, and its `progress.quantity_target` and
  `missing_only` follow it; typing 2 → 2, source `own`, target moves; `null` → borrowed again;
  no active version and nothing typed → 0, source `none`; `null` on the active version → 422;
  typing above the ceiling on a draft → the v6 identity; activation with
  `keep_active_missing=true` → untyped rows carry the closing board's missing, typed rows keep
  theirs; `false` → untyped rows 0, typed rows keep theirs; both then clamped where the live
  counters cover more; a scheduled fire uses the stored flag and a manual activation ignores
  it (R-6); no previous active version → 0 either way; the `:activated` event carries the flag.
- **shortcuts**: unchanged results on the active board; a row with no snapshot in the active
  version → 422 `STOCK_REPORT_NO_ACTIVE_SNAPSHOT`; no active version → the same 422 (P-7);
  two-session: a shortcut priority PATCH that waits behind an activation edits the newly
  active version and returns 200 (R-3).
- **create body** (R-9): the documented default body with `draft=false` → 200; a sent
  `scheduled_activation_at` with `draft=false` → 422.
- **apply-priorities**: active → draft, closed → draft, draft → draft; onto a draft writes no
  history and answers with the draft's snapshots; manual values of the source not copied;
  source = active with no body → the v6 identity; source = target otherwise → the new one;
  closed target refused; a no-body call unchanged.
- **activate**: previous closes with frozen counters; `active_at` set on version and every
  snapshot; the Scanner column frozen from the live rows (a row whose Scanner value moved
  after the draft was made freezes the new value); a manual value survives with effective =
  manual; missing clamped where the effective ceiling fell; one `priority_change` per
  prioritised row, none for the rest, each with the effective requested and its source; the
  previous version's `progress` frozen afterwards; the schedule cleared and its scheduler
  `CANCELED`; no per-snapshot event, one `:activated`; **v7's activate body
  `{"refresh_quantity_requested": false}` → 422; no body and `{}` → 200** (Q-8); a draft with
  every snapshot's Scanner column NULL and `active_at` NULL activates in one statement and
  `GET /consistency` is clean afterwards (Q-1).
- **refresh** on the active version: Scanner column changes only where it differs; a change of
  the Scanner column alone emits the event; `keep_manual_requested=true` leaves an override
  and a later revert lands on the refreshed value; `false` clears overrides with one override
  record each (source `scanner`); missing clamped; resolved untouched; a new live row added
  with the version's `active_at` (P-15) and `snapshot_count` follows; a draft → 422
  `STOCK_REPORT_VERSION_NOT_ACTIVE`, a closed version → the same.
- **progress can go backwards, twice**: a refresh raising the effective requested on a completed
  snapshot drops `items_completed` by 1; a manual raise on the active version does the same.
- **schedule**: create-with-schedule and PATCH create an `ACTIVE` scheduler with `scheduled_for`
  = the column, **in UTC**; moving the date cancels and recreates; changing only the missing
  flag touches no scheduler row (O-9); clearing cancels; naive
  datetime → 422 and past → 422 at both create and PATCH (P-13); `{}` changes nothing and emits
  nothing; `{"title": null}` clears only the title (P-14); on a non-draft → 422; **a schedule
  set through the API with a `+02:00` offset fires and activates, not skipped** (Q-5).
- **the scheduler chain, end to end, all three hops** (P-10, R-1, R-8): a due row of the new
  type driven through `_fire_due_schedulers`, the OPEN task through `_route_open_tasks(redis)`
  with a fake Redis that records `rpush` — asserting it lands on `queue:tasks` — then through
  `HANDLER_MAP[TaskType.…]`, and the draft observed active, stamped with the scheduling user,
  frozen over the live Scanner values of fire time with the manual values kept.
  **Fixture hygiene** *(Q-11)*, replacing revision 5's "no other test creates scheduler rows"
  (false as soon as this plan's own schedule tests exist; the runner's and router's queries are
  global, `limit(50)` / `limit(BATCH_SIZE)`, no `ORDER BY`, and `purge_stock_report_workspace`
  does not delete scheduler rows, which have no workspace column):
  (a) `purge_stock_report_workspace` gains, **before** it deletes the versions, the deletion of
  `delayed_schedulers` whose `event_client_id` is one of the workspace's version ids and of
  the execution tasks and payloads whose `origin_id` is one of those schedulers; every test
  that creates a scheduler row purges in `finally`;
  (b) the precedent wrapper (`test_finalize_pending_step_completion_integration.py:46-59`)
  remaps only `begin()`, while `_fire_due_schedulers` and `_route_open_tasks` call
  `session.commit()` directly (`delayed_scheduler_runner.py:99`, `task_router.py:137`) — on the
  shared `db_session` that commits the whole fixture; the e2e wrapper therefore maps
  `commit()` to `flush()` as well, or the test runs on its own committed workspace and purges;
  (c) the docstring states the purge guarantee, not the absence of neighbours.
  **Overdue fixtures** *(Q-12, delegated)*: the API refuses past times, so an overdue schedule
  is built by writing `scheduled_activation_at` **and** a matching `ACTIVE` scheduler row
  directly, both, so consistency stays clean.
- **handler skip causes** (P-6, card 4, Q-2), each an integration row: draft deleted; activated by
  hand; schedule moved after the row fired (the handler completes, the draft unchanged, the new
  schedule still pending, no event); a board activated by hand after the scheduled time (the
  late fire skips: **`scheduled_activation_at` is NULL after commit**, the scheduler row
  `CANCELED`, one `:updated`, `GET /consistency` clean); Monday's and Tuesday's drafts both
  overdue → Tuesday's wins in **either** processing order; **two drafts at the same minute →
  the later-created wins in either order** (card 5); workspace reset (P-21).
- **activating by hand a draft that has a schedule → 200** (R-2, the one-statement clear).
- **scheduler consistency** (R-4): fired-but-unprocessed shows the documented divergence;
  a failed task → repair recreates the row → activates late; an `ERROR` row past due → same;
  an `ACTIVE` row with no column → cancelled.
- **membership consistency** (O-3): a draft with a snapshot removed by hand → reported with
  the version as `client_id` and the row id in `expected`, repair re-inserts it and fixes
  `snapshot_count`; a stray snapshot of a deleted row **holding a priority** → reported and
  removed with its gap closed and the count decremented (Q-18); the active version with a row
  created since → **not** reported; every new kind's five fields as §7's table (Q-13).
- **response shapes** (R-7): one row each for activate, PATCH version, DELETE version, refresh,
  requested-quantity.
- **cascade** (P-1): delete a row that is in the active version and in two drafts → the active
  snapshot closed, both draft snapshots gone, each draft's group dense, each draft's
  `snapshot_count` down by 1; same through the Scanner delete webhook.
- **consistency and repair** (P-2, P-3, P-4): repair never reopens a cascade-closed snapshot;
  a draft's gap is repaired within its own version and the active group untouched; an
  assignment on a row with draft missing produces no divergence; the state-mismatch kinds in
  all three directions, the Scanner column moving with `active_at`.
- **delete draft**: snapshots and version gone, scheduler `CANCELED`, board untouched; non-draft → 422.
- **reads**: `GET /items?version_id=` on a draft (live counters, live requested), on a closed
  version (frozen, and a closed snapshot's requested never reads the row), with `live_stock=true`
  → 422; `include_zero_requested` and the outstanding rule on a draft follow the effective value;
  `GET /snapshots/versions?state=draft` lists only drafts; `/versions/active` still returns the
  active version and `/versions/<draft id>` the draft (P-23).
- **migration**: upgrade on a database with an active and a closed version keeps every
  requested value under the new column name; downgrade refuses with a draft present and with a
  manual value present, succeeds once both are gone.
- **lock order** for activate, refresh, delete draft (version before snapshots), PATCH version,
  the versioned priority routes and the webhook's draft insert (the ascending-lock pattern);
  concurrency: manual vs fired activation under the advisory lock (the two-session pattern).

## 10. Owner rulings on the projection's cards (2026-09-27)

| Card | Ruling |
|---|---|
| 1 — who edits through the versioned routes | the same roles as the board twins: admins, managers and sellers for priority, order and (O-4) requested quantity; workers for missing, as today. No role logic inside commands. The old routes stay as shortcuts. |
| 2 — can workers and sellers see drafts | yes, read-only, through the versions list and `GET /items?version_id=`; their default `GET /items` stays the active version. |
| 3 — a scheduled activation whose time passed while the system was down | activate late, today's runner behaviour. |
| 4 — several scheduled boards due at once, or a hand activation after the scheduled time | skip when superseded (§4.2 step 2, §5.3): the later plan wins, a hand-published board stands, the skipped draft keeps being a draft with its schedule cleared. |
| 5 (r2 card 1) — two drafts scheduled for the same moment | the draft **created later** wins; tie broken on `(scheduled_activation_at, created_at, client_id)` in either processing order (§4.2 step 2, §5.3). |
| 6 (r2 card 2) — typing the number Scanner already shows | a **pin**: compared against the stored manual value, stored, source `manual` (§4.11 step 3); the ship-time reference file corrects v8 §5.22. |
| 7 (r2 card 3) — the demand webhook's statement bound | 8 → **11**, constant in batch size and draft count; C6a/C6b at `<= 11` with 0 and ≥ 2 drafts (§4.9). |
| — (r1 note) refreshing the active board can lower progress | accepted: "if requested is reshaped, so is progress — that is fair" (§4.3); a manual requested change on the active version is the same exception (§4.11). |
| — (r1 R-13) split into batches | **declined**: one implementation by the plan's author, with the §12 checkpoint. |

## 11. Settled by the owner (2026-09-27)

- Many drafts per workspace; each may carry a `title` (optional, 200 chars, any state).
- A draft is live: its rows' requested is the live row's, and a new Scanner row joins every
  draft at once (O-1, O-3). Only activation freezes the Scanner value.
- Two columns on the snapshot: `quantity_requested_scanner`, `quantity_requested_manual`;
  effective and source derived (O-2). The wire keeps `quantity_requested` as the effective value.
- A user (admin, manager, seller) sets or reverts a row's requested by hand on a draft or the
  active version, on one route (O-4); the active version's change writes a
  `quantity_requested_override` record, and history records carry `quantity_requested_source` (O-7).
- Every snapshot read carries `active_quantity_missing` from the active version (O-5); a
  draft's `quantity_missing` is its typed value, else that borrowed one (O-9).
- Activation body `{"keep_active_missing": false}`: for rows the draft typed no missing for,
  keep the closing board's value or reset to 0; stored on the draft as
  `scheduled_activation_keeps_active_missing` for a scheduled fire (O-9).
- Refresh: the active version only; `keep_manual_requested` chooses whether overrides survive (O-6).
- Activation has no body; a scheduled activation freezes the live values of fire time.
- A draft can be edited in priority, priority order and `quantity_missing`.
- Drafts are hard-deleted; a delete or a manual activation cancels the scheduled event.
- `GET /items?version_id=` for any version; live counters beside the live or frozen requested.
- Refresh, create, activate, PATCH version, delete draft: admin and manager.
- A scheduled activation is stamped with the user who set the schedule.
- No history for draft edits; activation writes one `priority_change` per prioritised row.
- Row edits go through `PATCH /snapshots/versions/{version_id}/items/{client_id}/…`.
- v7 is with the frontend; v8 lists the differences (O-8).

## 12. Implementation order — one implementation, one checkpoint (owner ruling on R-13)

The plan is implemented as a single unit by its author, in this order, with **one
mid-implementation checkpoint** that must be green before any code path can create a draft or
a manual value:

1. Migration (§3.6); `_predicates.py` with the effective-requested expression; the rename at
   every Appendix B site (each reads the effective expression; with every snapshot activated
   and no manual value it equals the old column); `is_snapshot_open` / `is_snapshot_active`;
   every §4.10 predicate site; version-scoped `_ordering` and `lock_snapshot_and_groups`; the
   cascade (§4.7); consistency and repair (§7 without the scheduler and membership kinds);
   `_load_row_with_snapshot`'s version loader and the active-missing subquery; the serializer's
   four keys; the two columns on every RETURNING (§4.10b); the history column (its writers'
   rule, §3.5 Q-10, is step 2). **Test perimeter** *(Q-14)*: `tests/helpers/stock_report.py:202`
   seeds snapshots with `quantity_requested=`, and about twenty test files read a snapshot's
   `quantity_requested` — every such reference is renamed **mechanically, with no expected
   value changing**; `test_schema_contract` is updated for the rename.
   **Checkpoint:** full suite from `app/` with a unique `BEYO_TEST_SLOT`, failure IDs diffed both
   ways against the 23-ID baseline. Expected delta, **stated by ID** *(Q-3 iv)*: exactly
   `test_c2a…[serialize_stock_report_item_snapshot]` and
   `test_c2a…[serialize_stock_report_snapshot_version]` newly failing — the guard still reads
   v6, whose tables carry `quantity_requested` as a column and `active_at` as non-null, and v6
   may not be edited; both go green at step 5 when `_CURRENT_HANDOFF` moves to the reference
   file. **Nothing else** — with no draft and no manual value present, behaviour is today's.
   Anything else is a predicate-site or expression-site defect and is fixed here.
2. Create draft (§4.1); the webhook's draft insert and the C6 bound (§4.9); the versioned routes
   incl. requested-quantity and the shortcuts (§4.6, §4.11); the history helper on every
   snapshot-driven writer (§3.5, Q-10); apply-priorities target (§4.4); delete draft (§4.8);
   `GET /snapshots/versions/{id}`, `state`, `version_id` (§6); the membership consistency kind
   (§4.12); the purge helper's scheduler deletion (§9, Q-11a).
3. Activate by hand (§4.2 without the supersede rules' scheduled branch); refresh (§4.3);
   history at activation; events.
4. Scheduling (§5): PATCH version (§4.5), payload, handler, the four registries, the supersede
   rules (card 4 is ruled, so nothing gates this), reset phase, the scheduler consistency kind,
   `CLAUDE.md` "Running".
5. The consolidated reference file (§8, Q-3: v7 + v8 + v9 merged as a new dated file, v10, with cards 5
   and 6 stated), `_CURRENT_HANDOFF` repointed, v6/v7/v8/v9 to `archived/`; `api.md` (routes,
   identities incl. the log token, the kind list), `states.md`, the docs guard (route count
   moves as each route lands; the guard is updated with it), `CLAUDE.md`; full suite — the
   two step-1 IDs now green, the diff against the baseline empty both ways; ruff on touched
   files; every new behaviour armed with a mutant observed red.

The frontend gate (§8, P-9) is unchanged: drafts are not used in production until the
frontend filters snapshot events by `version_id` and refetches the board on `:activated`.

## Appendix A — every snapshot predicate site and where this plan puts it

| Site | Today | Plan |
|---|---|---|
| `serializers.serialize_stock_report_item_snapshot` | open | open |
| `snapshot_rules.is_snapshot_active` | open | renamed `is_snapshot_open`; new `is_snapshot_active` = the pair |
| `_version_progress._live_or_frozen` | open | open |
| `list_stock_report_items._ACTIVE_SNAPSHOT_JOIN` | open | active, or `version_id`; plus the active-missing left join |
| `get_stock_report_active_snapshot_version` | open | active |
| `get_stock_report_missing_summary` | open | active |
| `create_…version` freeze text, snapshot lock, `previous` lookup | open | active (all three) |
| `_load_row_with_snapshot.load_active_snapshot` | open | active, plus a version-scoped loader |
| `set_…priority.lock_snapshot_and_groups` and post-lock checks, `set_…order`, `set_…missing`, new `set_…requested` | open | version-scoped; history decided post-lock |
| `_ordering._group_where` | ws + priority, open | version + priority, open |
| `_snapshot_missing._CLAMP_STATEMENT` | open | active |
| `_snapshot_resolved` | open | active |
| `create_stock_task_assignments` discovery | open | active |
| `process_items_processed` discovery | open | active |
| `apply_stock_demand._active_snapshot_column` | open | active; plus the draft insert (§4.9, drafts = `active_at IS NULL`) |
| `apply_…priorities` source check, lock, write | closed / open / open | §4.4: target open, write keyed by `version_id` |
| `delete_stock_report_item.lock_active_snapshots_and_groups` | open | open, version-grouped |
| `_delete_stock_report_item_cascade` (iii) | open | active closes; drafts deleted |
| `consistency` | open / closed versions | open, per version; one-directional state kinds |
| `repair_stock_report._repair_priority_orders`, its lock | open | open, per version (same set as consistency) |

## Appendix B — every reader of the snapshot's `quantity_requested` and what it reads now *(O-2)*

| Site | Today | Plan |
|---|---|---|
| `serializers.serialize_stock_report_item_snapshot` | the column | `effective_quantity_requested(snapshot, row=row)` + the three new keys (§6); `quantity_missing` likewise a call (§3.4b) |
| every draft reader of `quantity_missing` (serializer, progress `target`, `missing_only`) *(O-9)* | the column | the effective missing (§3.4b); activated snapshots unchanged |
| `snapshot_rules.missing_quantity_ceiling`, `outstanding_quantity` | the column | the effective value (the row joins the signature) |
| `snapshot_rules.SNAPSHOT_VALUE_KEYS` / `_snapshot_values.snapshot_values` | the column | the two stored columns |
| `_snapshot_missing._CEILING_SQL`, `_CLAMP_STATEMENT` | `s.quantity_requested` | `EFFECTIVE_QUANTITY_REQUESTED_SQL` (`r` already joined) |
| `set_…missing_quantity` ceiling check and RETURNING | the column | effective; RETURNING both columns |
| `list_stock_report_items` outstanding rule, `include_zero_requested` | the column | effective |
| `_version_progress` `target`, `quantity_requested` sum | the column | effective |
| `consistency.missing_over_ceiling` | the column | effective, active only |
| `set_…priority`, `set_…priority_order`, `apply_…priorities` history values | the **row's** value (MC-6) | effective + source through the §3.5 helper, active version only *(Q-10)* |
| `create_…version` freeze text | writes the column from the row | writes `quantity_requested_scanner` (direct create) or NULL (draft) |
| `activate` (new) | — | freezes `quantity_requested_scanner`; keeps `quantity_requested_manual` |
| `refresh` (new) | — | re-freezes the Scanner column; clears manual on request |
| history at activation, `quantity_requested_override` records | — | the effective value + `quantity_requested_source` |
| every RETURNING in §4.10b | (none carry it today) | both stored columns |
| `test_schema_contract`, the docs guard's serializer table | the column | the renamed column; the wire key documented as computed |
