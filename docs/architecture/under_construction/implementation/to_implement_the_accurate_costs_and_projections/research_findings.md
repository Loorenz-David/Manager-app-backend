# Research findings — accurate costs & projections

```
role:   evidence record (never edited — corrections are routed, not patched)
date:   2026-08-16
scope:  what the codebase already provides for per-section time attribution,
        issue-based time estimation, and per-section cost rates
method: direct file reads in backend/app on 2026-08-16 (after item cost v1 closed
        2026-08-15 — its docs phase had already landed, so drift rows reflect that)
```

Paths are relative to `backend/app/` unless stated. Line numbers date to 2026-08-16;
re-verify by symbol before relying on them.

---

## 1. Per-section time attribution — ALREADY COMPLETE

The single most important finding: **the data needed for per-section actuals and for
ratio samples already exists and has been accumulating.** No new collection is
required, and history is queryable retroactively.

| Fact | Evidence |
|---|---|
| `TaskStep.working_section_id` — NOT NULL | `models/tables/tasks/task_step.py:65` |
| `TaskStep.total_working_seconds` — `Integer NOT NULL default 0` | `models/base/aggregate_metrics.py:6` (`AggregateMetricsTimeMixin`, mixed into `TaskStep` at `task_step.py:37`) |
| `TaskStep.created_at` / `created_by_id` (nullable) | `task_step.py:92,97` |

**Consequence.** A ratio sample — "what did section S cost on episode T" — is
`SUM(total_working_seconds) WHERE task_id = T AND working_section_id = S`, over the
task's non-deleted steps. Multiple steps of the same section on one task (a rework
pass) sum into **one** sample, not several.

**Consequence.** Batch dilution is already applied upstream by the concurrency sweep
(`domain/analytics/concurrency.py`), so samples are already fair across simultaneous
work — see `item_cost_calculation/planning/intention.md` §2.3, §9.2.

---

## 2. Aggregates that already exist (do not rebuild)

### `working_section_daily_work_stats` — maintained, ZERO readers

- `models/tables/analytics/working_section_daily_work_stats.py`
- Prefix `wsdws`; grain **unique `(working_section_id, work_date)`**; carries
  `section_name_snapshot`; index `ix_working_section_daily_work_stats_section_date`
- Mixes in `AggregateMetricsTimeMixin`, `CountsMixin`, `InaccurateTimeMixin`,
  `TotalsMixin`, **`CostMixin`** (`:17-24`)
- Confirmed zero readers by `item_cost_calculation/planning/intention.md` §2.4

**Consequence.** A per-section *period* view is a query away, not a table away.

**Caution.** It carries `AggregateMetricsCostMixin`, i.e. the salary-priced
`total_cost_minor`. Any period view built on it is subject to item-cost master plan
rule **P-A** — that number and item-economics money must not co-occur without the
divergence statement.

**Limitation.** The grain has already discarded the item. It can answer "what is
section S's throughput over time" but **cannot** produce ratio samples, which need
the `(episode, section)` grain from §1.

### `ItemCostResult` (arrives with item cost v1 phase 8)

Carries the episode's amounts plus `task_closed_at`. An economics-over-time view
aggregates these on read; no daily materialization is needed until it is measurably
slow.

---

## 3. Issue system — current state

`models/tables/items/item_issue.py` (prefix `iti`) carries **more than labels**:

| Column | Note |
|---|---|
| `item_id`, `step_id`, `worker_id` | FKs, all NOT NULL |
| **`working_section_id`** | **NOT NULL — the issue is already attributed to a section** |
| `item_category_id` | NOT NULL |
| `issue_type_id` | nullable FK → `issue_types` |
| `issue_type_snapshot` | `String(255)` NOT NULL |
| `issue_mode_snapshot` | `String(32)` nullable |
| `placement_of_issue_snapshot` | `String(255)` nullable |
| **`intensity`** | `Integer` NOT NULL, `CHECK intensity >= 1` (`ck_item_issues_intensity_positive`) |
| `created_at` / `updated_at`, soft-delete trio | |

Indexes: `ix_item_issues_workspace_item`, `ix_item_issues_workspace_step`.

**Consequence.** "Which issues were found in which section, and when" is a direct
query today — no new attribution plumbing. `created_at` gives the discovery timeline,
which is what makes *discovery drift* (raw_intention §5.5) measurable retroactively.

### `issue_types` — `models/tables/issue_types/issue_type.py` (prefix `ist`)

`name`, `source` (`IssueSourceEnum`), `issue_mode` (`IssueModeEnum`, default `GRADED`),
audit + soft delete, `uq_issue_types_workspace_name`. **No time-related columns.**

### `item_category_issue_types` — created by the rework migration

`migrations/versions/99accdeba8b9_issue_system_rework.py:41-58`. Columns
`(workspace_id, item_category_id, issue_type_id, placement_of_issue)`, unique
`uq_item_category_issue_types_unique`.

**Consequence.** This is the `(category × issue_type)` junction — exactly the grain the
deleted `issue_category_configs.base_time_seconds` used (§4). A coefficient table would
hang here naturally.

---

## 4. The DELETED issue-timing system — read this before redesigning

A time-estimation model for issues **already existed and was removed**. This is the
single most valuable pointer in this document.

### What was removed

| Artifact | Evidence |
|---|---|
| `item_issues.base_time_seconds`, `item_issues.time_multiplier` | dropped by `migrations/versions/99accdeba8b9_issue_system_rework.py` (Create Date 2026-06-03); constraint drop visible at `:121` |
| `issue_category_configs` — defined `base_time_seconds` per `(issue_type_id, item_category_id)` | dropped earlier; cited `7d92a90e6282:260-289` in `item_cost_calculation/planning/intention.md` §2.4, where it is noted as **the repo's only effective-dated-table precedent** |
| `issue_severities.time_multiplier` | referenced by the surviving README below |

### The formula it used — still documented in-tree

`models/tables/issue_types/README.md`:

- `:38` — **`base_time_seconds × time_multiplier = timing estimate`**
- `:37` — `time_multiplier` is `Numeric(8,4)`, Python `Decimal`, **never float**
- `:40` — `CHECK(time_multiplier >= 0)` enforced at DB level
- `:47` — base time defined per `(issue_type_id, item_category_id)`
- `:39` — *"Historical item issues must preserve the applied multiplier via
  `time_multiplier` snapshot on `item_issues.time_multiplier`"*
- `:51` — *"When base time is applied to an `item_issue`, it must be snapshotted into
  `item_issues.base_time_seconds`. Future config changes must not retroactively mutate
  historical issue timing."*

**Surviving documentation of the deleted model (re-verified 2026-08-16, after v1's
docs phase landed):**

| File | Lines | State |
|---|---|---|
| `models/tables/issue_types/README.md` | 37-40, 47, 51 | ❌ still describes the deleted columns |
| `models/tables/README.md` | 332, 350, 401, 402 | ❌ still lists them as live columns |
| `routers/README.md` | 2096-2097, 2280-2281 | ❌ still in the OpenAPI mirror |
| `models/tables/items/README.md` | — | ✅ **fixed** by item cost v1's documentation phase |

Archived frontend handoffs under `docs/handoff/to_frontend/archived/` also contain the
fields; those are historical records, not drift.

### Assessment

- `intensity` (§3) is what **replaced** graded severity — a two-coefficient model
  (base × multiplier) collapsed into a single scalar.
- **The snapshot doctrine at `:39` and `:51` was correct** and should be re-adopted
  verbatim by any replacement. It is `HC-1` expressed in a different domain.
- **Owner-stated reason for removal (2026-08-13):** the approach derived per-issue
  time from collected data by keying on issue label + item type, and that derivation
  did not hold up. See raw_intention §5.4 — the co-occurrence / identifiability
  problem is the most likely mechanism of that failure, and it is testable against
  existing data before anything is rebuilt.
- Documentation drift: v1's documentation phase fixed `items/README.md`; three other
  files still describe the deleted columns (table above) and were **not** in that
  scope. `models/tables/README.md` presents them as live columns, which is the most
  misleading of the three.

---

## 5. Item typing — the axis that needs expanding

`models/tables/items/item.py`:

- `item_category_id` nullable FK (`:30`)
- `item_category_snapshot` `String(255)` nullable (`:50`)
- `item_major_category_snapshot` `String(64)` nullable (`:51`) — values `wood | seat`
- partial index `ix_items_workspace_item_major_category_snapshot`
  `WHERE item_major_category_snapshot IS NOT NULL AND is_deleted = false` (`:73-76`)

**Gap.** There is no style / variant / complexity dimension. "A chair can have
different styles each with its own complexity" (owner, 2026-08-13) has no home in the
schema today. Adding one should follow the catalog lesson cited in
`item_cost_calculation/planning/intention.md` §2.4 (`pause_reason.py:25-34`):
manager-owned rows with a **code-owned discriminator**, never slug-resolved rows.

---

## 6. Roles and audit gaps around reassignment

### A WORKER can add task steps

`routers/api_v1/tasks.py:970-974`:

```python
@router.post("/{task_id}/steps")
async def route_add_task_step(
    ...
    claims: dict = Depends(require_roles([ADMIN, MANAGER, WORKER])),
```

**Consequence.** Any design that recomputes an economic figure on step addition lets a
WORKER move a money number they are not permitted to see (item cost `§11A.1`:
monetary payloads are ADMIN/MANAGER only). This is the decisive argument against
auto-re-committing an evaluation on route change.

### What a reassignment leaves behind

`services/commands/task_steps/add_task_steps.py` writes the new step and an initial
`StepStateRecord` (`:144-155`, setting `step.latest_state_record_id`). It writes **no
task-level history record**.

Available for reconstruction:

| Question | Answerable? | From |
|---|---|---|
| That a step was added late | ✅ | `task_steps.created_at` |
| Who added it | ✅ | `task_steps.created_by_id` |
| Which section it went to | ✅ | `task_steps.working_section_id` |
| How long it took | ✅ | `total_working_seconds` |
| **Why** it was added (rework? scope change?) | ❌ | nothing captures intent |

**Gap.** No rework flag, no reason, no link back to the section that handed off. This
is the accountability gap to close if handback attribution matters — see
raw_intention §9.

---

## 7. Item cost v1 anchors these designs must respect

Verified against `item_cost_calculation/planning/intention.md` (round 6 at time of
reading) and `master_plan.md`.

### The consumption expression (§8A.1) — one scalar, one rate

```sql
SELECT COALESCE(SUM(task_steps.total_working_seconds), 0)
FROM task_steps
WHERE task_steps.task_id = :task_id AND task_steps.is_deleted = false
```

- Only filter is `is_deleted`; step state deliberately unfiltered
- Never reads `step_state_records` (HC-3: one time-truth, owned by the concurrency sweep)
- Never reads `inaccurate_*`, `total_pause_seconds`, `total_ended_shift_seconds`
- **No `GROUP BY working_section_id`** — this is the exact seam per-section pricing
  must open

Consumed cost is then `seconds/60 × cost_per_worker_minute_minor_snapshot` — a single
snapshot scalar on the evaluation.

**Consequence.** A step added in any section is picked up automatically (only
`task_id` and `is_deleted` filter). What is missing is *pricing granularity*, not
plumbing.

### The snapshot set (§6A.11) and `rederive()`

An evaluation reproduces its own rate, budget and allowance from a closed field set
**without dereferencing any FK**, guarded by `calculation_version`. Any design that
introduces a composite rate must extend that closed set or `HC-7` breaks.

### `CALCULATION_VERSION` (§6A.10)

Exists with an explicit bump contract; `rederive()` emits a skip marker on version
mismatch rather than failing. Composite-rate work is therefore an **additive**
change: new child table + version bump, old evaluations unaffected.

### Deferred-but-seamed items relevant here

From `intention.md` §7.4, §9.1, §9.3, §13:

- Group **section membership** (`ProductionCostGroupSection`) is built in v1 and
  deliberately read by nothing — it exists *"for future observed-utilization and
  per-section analytics attribution"* (R-8). Do not let a reviewer delete it.
- Selection is "the workspace's **single** active production cost group"; 0 or 2+ is a
  hard error. **Category-based selection does not exist** — a future per-section or
  per-category selection would be the first such mechanism.
- Evaluations key `(task_id, item_id)` as the multi-item seam.
- Per-section observed *utilization* is blocked by an attribution gap (§2.4): shift
  time carries no section; only step time is section-attributed.

### The compensation seam (§10.3)

The interface is exactly two fields on `ProductionCostBasisVersion`:
`fixed_monthly_cost_minor` and `monthly_paid_hours`. Compensation populates them
through the same command path — new version, same calculator, same snapshots.

**Not covered by that seam:** compensation yields **per-worker** cost. Turning that
into **per-section** cost needs its own allocation rule, because §2.4 establishes that
working-section memberships are many-to-many and time-varying, so "a worker belongs to
one section" is not derivable. See raw_intention §7.4.
