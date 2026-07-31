# MASTER_PLAN_system_transition_reasons_20260731

## Metadata

- Plan ID: `MASTER_PLAN_system_transition_reasons_20260731`
- Status: `under_construction`
- Owner agent: `claude-opus-5` (operator: David)
- Created at (UTC): `2026-07-31T00:00:00Z`
- Last updated at (UTC): `2026-07-31T14:13:35Z`
- Intention plan: `docs/architecture/under_construction/intention/INTENTION_system_transition_reasons_20260730.md`

## Goal

Move system-controlled state transitions out of the workspace-managed `pause_reasons` catalog and
onto the source records themselves, as a code-owned `transition_reason` vocabulary — so that
clock-out and task switching never depend on a seeded catalog row existing in a workspace.

## Why this matters

Measured at commit `de0b3b3`: **3132 workspaces, exactly 1 holding `pause_ended_shift`.** In the
other 3131, clock-out with an open WORKING step fails with `NotFound`, and — because
`pause_other_task_priority` has the same dependency across two more call sites — **task switching
fails as well**. A mandatory state-machine transition is gated on user-editable data.

Full reasoning, the seven traced findings, and the root-cause mechanism are in the intention plan.
This master plan does not restate them; implementers must read it.

## Architecture (target state)

| Case | `transition_reason` | `pause_reason_id` |
|---|---|---|
| Clock-out closing an open working step | `SHIFT_ENDED` | `NULL` |
| Auto-pause because another task took priority | `OTHER_TASK_PRIORITY` | `NULL` |
| Worker paused a step with a catalog reason | `WORKER_PAUSED` | the chosen catalog row |
| Worker declared an off-task state | *(implicit — see T3)* | the chosen catalog row |

`pause_reasons` returns to being purely a catalog of things a **worker chooses**. No runtime code
path resolves a row by slug.

## Traced model facts (established 2026-07-31; do not re-derive)

- **`StepStateRecord`** — `pause_reason_id` nullable FK → `pause_reasons.client_id`
  `ondelete="RESTRICT"`, plus a separate `description` (which carries the auto-pause text
  `"started working with {identifier}"`). This is the table that needs `transition_reason`.
- **`StepStateRecord` has NO `reason` column.** Migration `b58cdffb5ccc` dropped it together with
  `step_event_reason_enum`. Any plan text implying a live legacy free-text column there is wrong.
- **`UserDeclaredStateRecord.pause_reason_id` is `NOT NULL`** — a declared state always carries a
  catalog reason, so the row's existence already encodes its transition semantics. See T3.
- **`UserShiftStateRecord`** is **derived**, rebuilt at clock-out. `reason` is a `String(512)`
  holding either a `par_…` catalog id or legacy free text; `manually_recorded` is a boolean carrying
  provenance. Historical rows are never rebuilt — they are the migration's real problem.
- **`pause_case_created`** is a soft-deleted catalog row that historical `step_state_records` point
  at via FK. It is a live label-resolution target, not dead weight.

## Cross-phase decisions (binding for every phase)

Numbered `T…` to avoid collision with the declared_worker_states set's `D1–D14`.

- **T1 — The vocabulary is code-owned.** `transition_reason` is a domain enum persisted as a
  constrained string/enum column. It is never resolved through a database lookup.
- **T2 — System transitions write `pause_reason_id = NULL`.** A row carries a catalog reference only
  when a human chose it.
- **T3 — `UserDeclaredStateRecord` does NOT get a `transition_reason` column.** Its
  `pause_reason_id` is `NOT NULL`, so the column would be constant for every row. The declared-state
  semantics are carried by the table identity and surfaced during derivation. If a phase finds a
  concrete case this breaks, escalate rather than adding the column silently.
- **T4 — Readers tolerate both representations before any writer changes** *(relaxed
  2026-07-31)*. Originally this forced read tolerance into its own phase ahead of every writer
  cutover. That protects against a **partial deploy** — a window where new-format rows exist and
  readers discard them. The operator is shipping this set in one deploy, so that window does not
  exist, and the separation bought three extra review cycles for nothing. **Revised rule:** readers
  and writers may ship in the same phase, provided the readers are implemented and tested *first
  within it* and they reach production in the same deploy. If the delivery plan ever changes to
  incremental deploys, this reverts to the strict form.
- **T5 — Retire, do not leave inert** (operator ruling, 2026-07-31). Historical rows are backfilled
  to `transition_reason`, their system `pause_reason_id` nulled, and the system catalog rows then
  soft-deleted. Ends with one representation everywhere. The alternative — permanently dual
  representation — was rejected: it preserves exactly the read-layer ambiguity this feature set
  exists to remove.
- **T6 — `slug` is KEPT; `uq_pause_reasons_slug` is scoped to `(workspace_id, slug)`** *(amended
  2026-07-31 by operator ruling, on phase 1's evidence — supersedes the original form below)*.
  Phase 1's out-of-repo audit found **live consumers** of `pause_reasons.slug`, so the condition the
  original ruling rested on does not hold. The decisive one is
  `frontend/packages/pause-reasons/src/types.ts:19`, where `slug: z.string()` is **required and
  non-nullable** — dropping the column would fail Zod validation on *every* pause-reasons response,
  not merely break the ended-shift branch. Two shipped worker-app call sites and the published
  `HANDOFF_TO_FRONTEND_pause_reasons_step_transition_contract_20260722.md` ruling also key off it.
  Full consumer table in "Phase 1 inventory".

  Scoping the index still resolves the second-workspace `IntegrityError`, and phase 4's other
  retirement work is unchanged. Note this makes the index change a **supporting** change, which the
  intention plan explicitly permits — it does not make it the architectural fix. The fix remains
  moving system transitions onto `transition_reason` (T1/T2), which phases 1–3 deliver regardless.

  *Original form, superseded:* "`slug` and `uq_pause_reasons_slug` are removed, not scoped… Operator
  confirmed 2026-07-31: drop the column, not only the index." That ruling was explicitly conditional
  on phase 1's audit finding no out-of-repo consumer; it did.
- **T7 — `manually_recorded` subsumption is a FOLLOW-UP, not part of this set** *(demoted
  2026-07-31)*. `transition_reason` probably subsumes it, and the `changed_by_id IS NOT NULL`
  heuristic that declared_worker_states Phase 2 settled on after four fix cycles (F1/F2, G1, H1, I1)
  probably becomes unnecessary. But removing it fixes nothing user-facing, and proving the
  equivalence safely is a whole phase of work. **Recorded as deferred cleanup** — do it when
  someone next touches that code with a reason to. No phase in this set may remove
  `manually_recorded` or the heuristic; doing so is a scope violation.
- **T9 — Commits stay clean and single-purpose.** *(Added 2026-07-31, operator instruction.)*
  Implementation, lifecycle close-out, and planning changes are **separate commits**, even when they
  land in the same session:

  - **Implementation** — production and test files for one phase, nothing else.
  - **Close-out** — summary, archive record, plan move, master phase-table flip, together.
  - **Planning** — plan or prompt edits for a *different* phase.
  - **Domain docs** (`docs/domains/`) ride with the implementation commit that made them true,
    because they document that change. They are not a separate commit.

  Never `git add -A` or `git add <broad-directory>`. Stage by explicit path. This decision exists
  because an over-broad `git add docs/architecture/under_construction` swept phase 1's plan move and
  master-table flip into a commit amending phase 4's scope — so phase 1's close-out is split across
  two commits and neither is self-describing.

  Parallel work is live in this repository (the reassigned-steps handoff, and a successor intention),
  and its files sit in the same tree. A broad add will capture them. Check `git status` before every
  commit and stage only what belongs to the change being committed.

- **T8 — No phase repairs baseline debt.** The repository has documented pre-existing validation
  debt (see the declared_worker_states master plan's "Repository validation baseline"). Implementers
  must not absorb it; reviewers must not block on it.

## Amendments to declared_worker_states decisions

This feature set amends three binding decisions of `MASTER_PLAN_declared_worker_states_20260729.md`.

**How amendments are recorded (decided 2026-07-31).** That feature set is **archived** — all seven
phases complete, its folder moved to `archives/implementation/declared_worker_states/`. Archived
documents are historical records and are **not edited**. So each amendment is recorded **here**, in
the table below, and the amending phase's Review log states which decision it changed and how. No
phase edits the archived plan. Anyone reading the archived D3/D5/D14 finds them via this plan, which
the intention links.

- **D3** — declared state surfaces as `IN_PAUSE` + `reason = pause_reason_id` +
  `manually_recorded = true`. **Amended, final form (phase 2, 2026-07-31):** the derived row
  surfaces as `IN_PAUSE` + `reason = pause_reason_id` + `transition_reason =
  WORKER_DECLARED_STATE` + `manually_recorded = true`. `reason` keeps the catalog reference
  unchanged — what changes is that the row is now *typed*, so a reader learns the segment came
  from a declaration without inferring it from `manually_recorded` or from the id's shape. This is
  the one row in the system carrying both representations, and it is deliberate (see the
  operator qualification in phase 1's Review log: phase 4's check constraint must be per-table or
  exempt `WORKER_DECLARED_STATE`). `manually_recorded` is untouched (T7).
- **D5** — auto-pause carries the declared `pause_reason_id`. **Amended, final form (phase 2,
  2026-07-31):** an auto-pause caused by *task switching* carries `transition_reason =
  OTHER_TASK_PRIORITY` and `pause_reason_id = NULL` — it resolves no catalog row at all, which is
  what lets it work in a workspace with an empty catalog. An auto-pause caused by a *declaration*
  is unchanged and still carries the declared `pause_reason_id`: the worker chose that reason, so
  it stays a catalog reference. D5's original wording covered only the second case; the first is
  what this feature set retyped.
- **D14** — kiosk clock-out analytics return `pause_by_reason` keyed by reason id plus a
  `pause_reasons` label map. Amended only if the retirement changes which keys can appear; the
  published contract is preserved (see "Sequencing against Phase 7").

## Sequencing against declared_worker_states Phase 7

Phase 7 (clock-out analytics) is in an active implement→review cycle and its contract is **already
published to the frontend**. Operator ruling: **Phase 7 lands and archives first.** This feature set
does not begin implementation until it does.

Consequence for this plan: Phase 7's `pause_by_reason` map becomes a concrete compatibility test for
the read-tolerance phase. Any phase here that changes what keys can appear in that map owns a
handoff update, and the handoff is operator-owned — phases propose, they do not edit.

## Phase orchestration

**Restructured 2026-07-31 from eleven phases to four.** The original set applied the ceremony of the
declared_worker_states feature set — which built new tables, a new auth scope, new endpoints, and a
kiosk flow — to a migration that adds a column, teaches readers to read it, flips three call sites,
backfills, and deletes the leftovers. Eleven phases meant eleven implement→review→fix cycles, at
roughly seven exchanges each before a single defect. That cost was not justified by the risk.

Three of the removed phases existed only to satisfy the strict form of T4, which guards against a
partial deploy. This set ships in one deploy (see "Delivery shape"), so that guard bought nothing.
One more, `manually_recorded` subsumption, was cleanup that fixes nothing user-facing and is now
deferred under T7.

| # | Phase | Status | Delivers | Independent review earns its cost because |
|---|---|---|---|---|
| 1 | **Inventory, vocabulary, schema & read tolerance** | `archived` ✅ (APPROVED round 2, 2026-07-31; round 1 `NEEDS_CHANGES` on F1 blocking + F2–F4, all closed in one fix cycle and re-verified by execution. Node-set diff vs `26d290d` empty. **Overturned T6** — see the amendment note below.) | The read-path audit and volume figures; `TransitionReasonEnum`; nullable `transition_reason` on `step_state_records` and `user_shift_state_records`; every read path resolves both representations. **Zero behaviour change** — nothing writes the column yet. | The audit is the foundation the rest is built on, and a missed read path ships broken in phase 2. |
| 2 | **Cutover** | `under_construction` | Clock-out, both task-switch sites, the derivation rebuild, and the serializer all move to `transition_reason`. `get_system_pause_reason_id` reaches zero runtime callers. **Ends the outage.** | One behavioural change with one question: does clocking out and switching tasks still work, including in a workspace with an empty catalog. |
| 3 | **Historical backfill** | `under_construction` | One-time migration: `transition_reason` set on historical rows, their system `pause_reason_id` nulled. | Irreversible. This is where real history gets destroyed if the row selection is wrong. |
| 4 | **Retirement & constraints** | `under_construction` | System rows retired; `get_system_pause_reason_id` deleted; `is_system_managed` removed; **`slug` kept, `uq_pause_reasons_slug` scoped to `(workspace_id, slug)`** (T6 as amended); check constraints added; final verification. | Drops/scopes constraints — cheap to review, but must follow 3. |

**Phase 1 artefacts.**
Plan: `../../../archives/implementation/system_transition_reasons/PLAN_system_transition_reasons_phase1_foundation_20260731.md` ·
Summary: `../../../implemented_summaries/SUMMARY_system_transition_reasons_phase1_foundation_20260731.md` ·
Archive record: `../../../archives/implementation/system_transition_reasons/ARCHIVE_RECORD_PLAN_system_transition_reasons_phase1_foundation_20260731.md`

**Three things phase 1 established that later phases are bound by** (full detail in "Phase 1
inventory"):

1. **Phase 2 must rewrite R14/R15** (`_reconstruct_shift_middle`, `reconcile_worker_shift_state`).
   They are writers of the derived table, so phase 1 correctly left them alone — but once phase 2
   types `step_state_records`, they emit `reason=NULL` and the kiosk buckets everything as
   `unspecified`. This is a required deliverable, not a discovery.
2. **Phase 3 must null only `pause_ended_shift` and `pause_other_task_priority`.**
   `pause_case_created` is `is_system_managed = false` and is a catalog reason a user action
   selects; nulling its 7 anchored rows without a `transition_reason` to carry loses their label and
   fails success criterion 5.
3. ~~**Phase 3 owns the `image_url` consequence.**~~ **CLOSED by phase 2 (review round 1,
   finding 2).** The premise was wrong: the seeded URLs are hardcoded literals identical in every
   workspace, not workspace-specific paths. `domain/transitions/labels.py` now reproduces them, so
   backfilled rows keep their kiosk icon and phase 3 has no asset decision to make. Detail in the
   "Label-resolution strings" section below.

**Ordering rationale.** Phase 1 is additive and observably inert, so it carries no deploy risk.
Phase 2 ends the outage **without needing the backfill**: new rows do not require the catalog row
that is missing, so the 3131 broken workspaces work the moment it ships. Phases 3 and 4 are cleanup
that removes the second representation — valuable, but not what unblocks anyone.

**What was preserved from the eleven-phase draft.** The acceptance criteria, which were the real
output: the zero-catalog tests, the label-parity requirement, "select by the three specific system
rows, never by `is_system_managed` alone", the mutation proofs, and the escalation triggers. They
live in fewer, larger plans, unchanged in substance.

**Delivery shape.** Phases 1–4 run as one continuous set, begun immediately after
declared_worker_states Phase 7 archives, and reach production in a single deploy. Each phase must
still be independently deployable, but none is designed as a resting point. If this changes to
incremental deploys, T4 reverts to its strict form and phase 1 must split.

### Per-phase workflow (operator: David)

1. Operator hands the phase's implementer prompt to a fresh implementer session.
2. Implementer: implement → validate → Review log entry → **STOP**.
3. Operator hands the phase's review prompt to a fresh independent reviewer session.
4. On `NEEDS_CHANGES`: operator writes a fix brief; implementer fixes; re-review.
5. On `APPROVED`: **then** summary → archive → master phase-table flip.

No implementer performs step 5. No phase plan may carry an acceptance criterion instructing the
implementer to flip a liveness row or edit an operator-owned handoff.

### Validation baseline

This feature set inherits the recorded baseline in
`MASTER_PLAN_declared_worker_states_20260729.md` → "Repository validation baseline", including:

- Canonical quiet-tree measurement **27 failed / 1275 passed**; compare failure **node sets**, never
  counts; never accept a suite number taken while another session is active.
- **Run `git` from `backend/`, not from `ManagerBeyo-app/`.** *(Diagnosed 2026-07-31, phase 2
  round 3.)* `ManagerBeyo-app/` is **not** a repository — `backend/` and `frontend/` are two
  separate repositories. An agent whose working directory is the parent sees `git rev-parse` fail
  and reasonably concludes there is no repository at all. **This has silently degraded two reviews
  in this codebase**: declared_worker_states Phase 7's reviewer skipped the baseline node-set diff
  on that basis, and phase 2 round 3's implementer could not diff against `HEAD`. Both reports were
  accurate about the command failing and wrong about the cause. Every prompt that asks for a
  baseline worktree or a history check must say where to run it.
- **A baseline git worktree needs its gitignored config copied in.** `.gitignore` excludes
  `app/.env*`, so a fresh worktree lacks them and cannot start — `Settings` raises on import
  because `.env.testing` defines no `JWT_SECRET_KEY` and the suite actually reads `.env`. Copy all
  of `app/.env*`. Verify config parity with a small smoke run in both trees before trusting any
  full-suite number. (Learned the hard way during declared_worker_states Phase 7.)
- **"Run-2 vs run-2" is necessary but not sufficient — some nodes latch.** *(Corrected 2026-07-31,
  phase 2 round 3.)* The rule exists because the test DB and Redis are shared and not reset, so a
  second consecutive run dirties them. But at least one node does not merely fail on run 2 — it
  **stays** failed on run 3 and beyond, having accumulated state that does not clear. Round 3
  measured 26/1396 on run 1 and 27/1395 on runs 2 and 3, the extra node being a shopify test that
  passes in isolation and sits in untouched code. So a run-2 comparison can show a node that is
  neither new nor caused by the change under review. **Compare like-for-like run indices, and treat
  a node that passes in isolation and lives outside the diff as a measurement artefact** — verify
  it, do not absorb it (T8).
- 149 pre-existing `ruff check .` errors in untouched files; the shared `count_queries` fixture is
  broken — use a local SQLAlchemy listener.

## Phase 1 inventory (recorded 2026-07-31 by the phase 1 implementer)

**Source database for every figure below:** the `.env` database
`postgresql+asyncpg://postgres:postgres@localhost:5433/beyo_manager` (operator ruling, 2026-07-31).
This is also the database the test suite runs against — `beyo_manager/config.py::_resolve_env_file()`
selects `.env` when `APP_ENV` is unset, and `.env.testing` cannot be used because it defines no
`JWT_SECRET_KEY`. The RDS in `.env.production.ec2` is unreachable from the operator's machine
(connection timeout), so **no figure here is measured against production.**

> **Corrected 2026-07-31 (operator).** The `.env` database is a **dockerised exact copy of the
> current server database**, re-downloadable and replaceable on demand. So the figures are measured
> against production *data* after all — with one qualification that phase 1's own F2 finding still
> stands: the suite also runs against it, so **globals carry accumulated test residue while
> workspace-scoped figures reproduce.** Read "not production" above as "not the live server", not
> as "not production data".
>
> **This resolves phase 3's rehearsal-database clarification, and changes that phase's risk
> profile.** The backfill can be rehearsed against real data and the database restored afterwards,
> rather than validated only against fixtures. Phase 3 must use that: restore a fresh copy → run
> the migration → verify label parity through the real read paths → restore again. Record the
> restore points. A rehearsal that cannot be repeated from a known state is not a rehearsal.

### Correction to the intention's "3132 workspaces, exactly 1"

That figure came from the **shared test database** `app_test` on port 5432, not from production or
from the dev database. Measured 2026-07-31, `app_test` now holds **4118 workspaces and ZERO
`pause_reasons` rows** — it accumulates workspaces from test runs and is not representative of
anything. The architectural argument is untouched (a workspace without the row cannot clock out),
but **the "3131 broken production workspaces" framing is not supported by evidence available on
this machine.** Phase 3 must not choose its backfill strategy from that number.

### Volumes (`beyo_manager` @5433) — re-measured quiescent 2026-07-31 (review round 1, F2)

**Why the first measurement did not reproduce.** This database is also the suite's database, so
every *global* count moves with every suite run: between the first inventory and the re-measurement
(three full-suite runs later) `workspaces` went 1 → 531 and global `step_state_records` 5299 → 5400.
The drift is **entirely rows in test workspaces**. Scoping to the one workspace that actually holds
a catalog — `ws_01KVX0G0T7Z6NE69YVRVMFAB98`, the real dev data — every phase-3-relevant figure
reproduces **exactly**.

**All figures below are workspace-scoped and marked STABLE unless noted.** Global counts are marked
VOLATILE and must not be used to size anything. Two consecutive quiescent samples 3s apart were
identical.

Scope predicate applied to each query below: `WHERE workspace_id = 'ws_01KVX0G0T7Z6NE69YVRVMFAB98'`.

| Figure | Value | Mark | Query |
|---|---|---|---|
| `step_state_records` total / with `pause_reason_id` / without | 5299 / 570 / 4729 | **STABLE** (reproduced exactly) | `SELECT count(*), count(pause_reason_id), count(*) FILTER (WHERE pause_reason_id IS NULL) FROM step_state_records WHERE workspace_id='ws_01KVX0G0T7Z6NE69YVRVMFAB98';` |
| `step_state_records` → `pause_ended_shift` | 152 | **STABLE** | `SELECT pr.slug, count(*) FROM step_state_records ssr JOIN pause_reasons pr ON pr.client_id = ssr.pause_reason_id WHERE ssr.workspace_id='ws_01KVX0G0T7Z6NE69YVRVMFAB98' GROUP BY pr.slug;` |
| `step_state_records` → `pause_other_task_priority` | 228 | **STABLE** | *(same query)* |
| `step_state_records` → `pause_case_created` | 7 | **STABLE** | *(same query)* |
| *(non-system, for context)* `pause_lunch_break` / `pause_coffee_break` / `waiting_for_upholstery` / `pause_meeting` | 71 / 52 / 45 / 15 | **STABLE** | *(same query)* |
| `user_shift_state_records.reason`: null / legacy slug string / `par_…` id | 3256 / **272** / 98 | **legacy-string count STABLE**; null VOLATILE; `par_` count corrected (the first inventory reported 100 unscoped — 2 of those rows are in test workspaces) | `SELECT CASE WHEN reason IS NULL THEN 'null' WHEN reason LIKE 'par\_%' THEN 'par_ id' ELSE 'legacy slug string' END, count(*) FROM user_shift_state_records WHERE workspace_id='ws_01KVX0G0T7Z6NE69YVRVMFAB98' GROUP BY 1;` |
| `user_declared_state_records` total | **0** | **STABLE** | `SELECT count(*), count(pause_reason_id) FROM user_declared_state_records;` |
| `step_state_records.description` non-null / `'started working with %'` | 157 / 113 | **STABLE** (reproduced exactly, even unscoped) | `SELECT count(*) FILTER (WHERE description IS NOT NULL), count(*) FILTER (WHERE description LIKE 'started working with %') FROM step_state_records;` |

**VOLATILE — do not size anything from these:** global `workspaces` (1 → 531), global
`step_state_records` (5299 → 5400), global `user_shift_state_records` (3620 → 3716), global
`step_state_records → pause_ended_shift` unscoped (152 → 157) and `pause_coffee_break` unscoped
(52 → 80). The unscoped slug join counts rows from *any* workspace pointing at the dev catalog,
which is why it drifts while the scoped version does not.

**Standing instruction for phase 3:** take every figure from this database **workspace-scoped and
with the suite quiescent**, or the number is not evidence.

### Correction to Finding 3 / "traced model facts": there is **no free text** — **STABLE**

`UserShiftStateRecord.reason` is documented as holding "either a `par_…` catalog id or legacy free
text". Measured: the 272 non-`par_` values are **legacy slug strings plus the literal
`"unspecified"`** — there is no human-authored free text at all.

```sql
SELECT count(*) FROM user_shift_state_records
WHERE reason IS NOT NULL AND reason NOT LIKE 'par\_%'
  AND reason NOT IN (SELECT slug FROM pause_reasons WHERE slug IS NOT NULL)
  AND reason <> 'unspecified';
-- 0
```

The complete distinct set is: `pause_case_created`, `pause_coffee_break`, `pause_lunch_break`,
`pause_meeting`, `pause_other_task_priority`, `unspecified`, `waiting_for_upholstery`.

**Reproduced exactly on re-measurement (2026-07-31, quiescent): count still 0, distinct set still
these 7, legacy-string row count still 272.** This is the figure phase 3 depends on most and it is
STABLE both scoped and unscoped.
**This makes phase 3's backfill materially simpler** — legacy values map slug → `transition_reason`
directly, with no text parsing and no unmappable tail. Note `"unspecified"` is stored in 13 rows and
collides with the published `UNSPECIFIED_REASON` bucket key.

### Per-workspace distribution (`beyo_manager` @5433)

Workspaces total **1**; holding any `pause_reasons` row **1**; holding each of `pause_ended_shift` /
`pause_other_task_priority` / `pause_case_created` **1 / 1 / 1**. A single-workspace dev database
cannot confirm or refute the 1-of-N claim — see the correction above.

```sql
SELECT (SELECT count(*) FROM workspaces),
       (SELECT count(DISTINCT workspace_id) FROM pause_reasons),
       (SELECT count(*) FROM pause_reasons WHERE slug='pause_ended_shift');
```

### Label-resolution strings (criterion 5 — phase 3 must reproduce these)

| slug | `name` | `pause_type` | `is_system_managed` | `is_deleted` | `image_url` |
|---|---|---|---|---|---|
| `pause_ended_shift` | **Ended shift** | BLOCKER | true | false | `.../ws_workspace_test/pause_reasons/ended_shift.webp` |
| `pause_other_task_priority` | **Other task priority** | BLOCKER | true | false | `.../ws_workspace_test/pause_reasons/other_task_priority.webp` |
| `pause_case_created` | **Case created** | BLOCKER | false | **true (soft-deleted anchor)** | *(null)* |

Finding 4 confirmed: `pause_case_created` is soft-deleted and still the FK target of 7
`step_state_records`.

~~**`image_url` is NOT reproduced by the code-owned map** — it is per-environment seed data pointing
into a workspace-specific S3 path… Phase 3 owns choosing a code-owned asset or accepting the loss.~~

**CORRECTED (phase 2, review round 1, finding 2). The URLs are reproduced, and they are not
per-environment.** They are hardcoded literals, identical in every workspace, appearing in exactly
two places: `seed_pause_reasons.py::_PAUSE_REASONS` and migration `49bd666da846` (lines 50–51),
which are byte-identical to each other. Nothing about them is workspace-authored — the
`ws_workspace_test` path segment is part of the constant, not a per-workspace substitution. Phase 1
read the URL's *shape* as evidence of provenance and inferred wrongly.

`domain/transitions/labels.py` now carries them, so a system transition resolves to the same name
**and icon** its catalog row carried. **This closes the phase 3 consequence: there is no icon loss
to own.** `WORKER_DECLARED_STATE` keeps `image_url: None` because no catalog row ever existed for
it — that is reproduction, not loss.

### `pause_case_created` disposition (review round 1, F4)

**What the 7 rows are.** All 7 are `step_state_records` in state `paused`, entered between
2026-06-27 and 2026-07-21, **none still open**. A further **6** `user_shift_state_records` carry the
legacy string `'pause_case_created'` in `reason`. The catalog row itself is `is_deleted = true` and
— importantly — **`is_system_managed = false`**.

**Ruling: no enum member, and phase 3 owns the final call.** Recorded here with the evidence and a
recommendation rather than decided unilaterally, because it changes which rows an irreversible
migration touches.

Reasoning for the recommendation: `pause_case_created` is **not a system transition**. It is a
catalog reason a *user action* selects — the frontend looks it up by slug and sends it as
`pause_reason_id` when a worker opens a case from a working step
([use-task-step-detail.controller.ts:228](../../../../../../frontend/apps/workers-app/ManagerBeyo-app-workers/src/features/task_steps/controllers/use-task-step-detail.controller.ts)).
Under the target semantics that is exactly the `pause_reason_id`-carrying case, not the
`transition_reason` case. Giving it a member would put a worker-chosen reason into a vocabulary
defined as system-controlled (T1/T2).

**Consequence phase 3 must not miss.** T5 says historical rows are backfilled and their *system*
`pause_reason_id` nulled. `pause_case_created` is **not** one of the two system slugs and is not
`is_system_managed`. If phase 3 nulls these 7 rows' `pause_reason_id` without a `transition_reason`
to carry, they lose their label and **master-plan success criterion 5 fails**. The preserved
acceptance criterion "select by the three specific system rows, never by `is_system_managed` alone"
cuts both ways here: selecting by the three *named* rows would wrongly include this one, and
selecting by `is_system_managed` would wrongly exclude it from delete-protection reasoning.
**Recommendation: phase 3 nulls only `pause_ended_shift` and `pause_other_task_priority`, and leaves
`pause_case_created` rows pointing at the anchor**, which is what Finding 4 already requires of the
anchor's role.

**Side finding (pre-existing, not repaired here).** The anchor is soft-deleted, and
`list_pause_reasons` filters `is_deleted IS false` — so the frontend's slug lookup returns
`undefined` today, and a case-created pause is currently written with **no** `pause_reason_id` at
all. That is why the row count is 7 and static rather than growing. Logged for the operator; out of
scope for this feature set per the intention's scope boundary.

### Second-workspace `IntegrityError` — **CONFIRMED by execution**

Run against a disposable database `beyo_str_repro_tmp` (created and dropped for the test; never the
shared dev/test database), driving the real `seed_pause_reasons` with `pause_reasons` created from
the live model metadata:

```
index uq_pause_reasons_slug: CREATE UNIQUE INDEX uq_pause_reasons_slug ON public.pause_reasons USING btree (slug)
workspace 1 seeded OK: 6 rows
RESULT: CONFIRMED — second workspace raised IntegrityError
  UniqueViolationError: duplicate key value violates unique constraint "uq_pause_reasons_slug"
```

Independently corroborated by the full-suite runs: on a **second consecutive** suite run,
`test_seed_pause_reasons_is_idempotent` and `test_pause_reason_crud_and_system_delete_guard` fail
through this same mechanism (see "Validation baseline" note below).

### Out-of-repo slug-consumer audit (T6) — **CONSUMER FOUND; T6 AMENDED**

The audit was extended past `grep app/` into the frontend monorepo at
`ManagerBeyo-app/frontend/`, the published handoffs, and `Application_contracts/`. It found live
consumers:

| Consumer | What it does |
|---|---|
| `frontend/apps/workers-app/.../features/task_steps/lib/pause-reason-transition.ts:12` | `reason.slug === "pause_ended_shift" ? "ended_shift" : "paused"` — decides the transition target state |
| `frontend/apps/workers-app/.../controllers/use-task-step-detail.controller.ts:228` | `reason.slug === "pause_case_created"` — resolves the pause reason id used when a case is created |
| `frontend/packages/pause-reasons/src/types.ts:19` | `slug: z.string()` — **required, non-nullable** in the response schema. Dropping the field fails Zod validation for every pause-reasons response, breaking the picker entirely |
| `frontend/packages/pause-reasons/src/lib/pause-reason-view-model.ts:11,14` | carries `slug` into the picker option and its `data-testid` |
| `frontend/apps/workers-app/.../tests/playwright/.../pause-reason.spec.ts:56,90` | e2e selectors keyed on slug |
| `docs/handoff/to_frontend/archived/HANDOFF_TO_FRONTEND_pause_reasons_step_transition_contract_20260722.md:101-116` | published ruling: *"keep that pattern — key off `slug === 'pause_ended_shift'` in the sheet"* |

The first two are compiled into the shipped `dist/` bundle. T6's ruling was made "on the basis that
none exist in this repository"; that basis does not hold.

**Operator ruling 2026-07-31 (escalation answered): T6 is AMENDED — keep the `slug` column.**
Phase 4 scopes `uq_pause_reasons_slug` to `(workspace_id, slug)` instead of dropping column and
index, which the intention already permits as a *supporting* change. Everything else in T6 stands:
phase 4 still retires the system rows, `is_system_managed`, and `get_system_pause_reason_id`. No
phase 1–3 deliverable depended on `slug` dying.

**Side finding (pre-existing, not repaired here):** `create_pause_reason.py:37` sets `slug=None`, and
`serialize_pause_reason` emits it — so a workspace-created reason already serialises `"slug": null`
against a frontend schema that requires a string. Logged as out-of-scope per the intention's scope
boundary.

### Read-path audit (model-outward from `PauseReason` / `pause_reason_id`)

Derived from inbound references, not from guessing at call sites. The three runtime sites the
intention names are present at `_clock_worker_shift.py:197`, `transition_step_state.py:271`,
`_step_transition_core.py:111` (the intention's `:200/:274/:114` point at the same statements; line
numbers drifted by 3).

**Label-resolving paths — tolerance added in phase 1:**

| # | Path | Test |
|---|---|---|
| R5 | `domain/users/serializers.py::pause_reason_reference_is_unresolved` | `test_transition_row_is_not_reported_unresolved`, `test_transition_row_outranks_a_dangling_catalog_id` |
| R6 | `domain/users/serializers.py::serialize_current_worker_shift_state` | `test_transition_reason_row_resolves_to_a_pause_reason_label`, `test_catalog_reference_wins_over_transition_reason`, `test_transition_reason_wins_over_free_text_reason` |
| R7 | `services/queries/users/get_current_worker_shift_state.py:88` (unresolved warning) | covered via R5 |
| R8 | `worker_stats/get_worker_linear_timeline_breakdown.py::_load_step_timeline_records` | `test_breakdown_resolves_a_transition_reason_step_record` |
| R9 | same file, `record_detail` nested `pause_reason` | ~~same test (asserts `pause_reason: null`, no new key)~~ **DECIDED (phase 2, review round 3, blocking finding F1): synthesise the catalog object shape, same as R2.** This is R2 in a third render site, and it survived round 2 because the sweep grepped `.pause_reason` while `record_detail` calls `serialize_pause_reason` on a **separately-fetched local**. `pause_reason_id = NULL` on every system transition made the field serialise `null` where a populated object used to be; the consumer is shipped (`packages/stats/.../segment-adapter.ts:113` → `record.pause_reason?.name`, same full `PauseReasonSchema` at `packages/stats/src/types.ts:304`). Test assertion reversed and proven failing-first; `test_breakdown_prefers_the_catalog_reason_when_a_row_carries_both` is the unmodified control. |
| R10 | same file, segment-level `reason` back-derivation | same test + `test_breakdown_prefers_the_catalog_reason_when_a_row_carries_both` |
| R11 | `worker_stats/list_workers_linear_timeline.py::_load_pause_reasons_lookup` | `test_roster_buckets_and_labels_a_transition_reason_pause`, `test_transition_reason_labels_cost_no_extra_query` |
| R12 | same file, `build_recorded_shift_timeline` bucket key | `test_pause_bucket_key_falls_back_to_transition_reason`, `test_catalog_reason_still_wins_the_bucket_key` |
| R13 | `worker_stats/get_worker_clock_out_analytics.py:277-284` (published kiosk contract) | `test_clock_out_analytics_resolves_transition_and_unspecified_keys` + the existing `test_pause_reasons_resolves_every_timeline_key_including_unspecified`, unmodified |

**Added in review round 1 (F3) — pure-domain sweep, deliberately unchanged in phase 1:**

| # | Path | Ruling |
|---|---|---|
| R23 | `domain/analytics/linear_timeline.py:220` — `owner.interval.reason or UNSPECIFIED_REASON` | The sweep treats `reason` as an **opaque key**; it never resolves a label. Phase 1 feeds the fallback in at the composer (R8/R12/R14), so this line needs no change and gets none. Covered indirectly by `test_pause_bucket_key_falls_back_to_transition_reason` and the existing `tests/unit/domain/analytics/test_linear_timeline.py`. |
| R24 | `domain/analytics/linear_timeline.py:264` — `pause_by_reason[seg.reason or UNSPECIFIED_REASON]` | Same: opaque key, no resolution. |
| — | **Phase 2 note** | Both lines are on `LinearInterval.reason`, which phase 2 rewrites when it changes what the composers put there. They are listed here because **this audit is phase 2's checklist**, and an unlisted line is one phase 2 can miss — not because phase 1 owes them a change. |

**Audited, deliberately unchanged in phase 1 — each with the reason and its test:**

| # | Path | Ruling |
|---|---|---|
| R1 | `domain/pause_reasons/serializers.py::serialize_pause_reason` | Catalog leaf. A transition reason has no catalog row. Existing `test_pause_reason_serializer_exposes_public_shape_only` unmodified and green. |
| R2 | `domain/tasks/serializers.py:186,377` | ~~The nested `pause_reason` is a **catalog object**. Synthesising one for a transition reason would invent contract… **Phase 2 decides whether step payloads need the transition surfaced.**~~ **DECIDED (phase 2, review round 1, blocking finding R2): synthesise the catalog object shape from the code-owned vocabulary.** Phase 1's reasoning was wrong on the contract question — `packages/tasks/src/types.ts` parses this field with the **full** `PauseReasonSchema`, so a transition-typed row serialising `null` blanks a label the client renders. Synthesising the same shape *preserves* the contract rather than inventing one; it is what "invisible" (clarification 3) requires. Both sites now call `serialize_step_pause_reason`. **Procedural lesson recorded: a deferred decision with no owner is how a listed path goes unhandled — "phase N decides" must name what happens if phase N does not.** |
| R3/R4 | `serialize_declared_state`, `_serialize_pause_reason_reference` | Take a `PauseReason` directly; T3 gives `UserDeclaredStateRecord` no column. |
| **R14** | `services/commands/users/_reconstruct_shift_middle.py:85-233` | **WRITER — phase 2.** It reads `pause_reason_id` into `LinearInterval.reason` and writes `reason=segment.reason` onto derived rows. Making it read `transition_reason` would write the new vocabulary into the old column. **This is the highest-risk item on this list: after phase 2 types `step_state_records`, this derivation returns `reason=NULL` and the kiosk buckets everything as `unspecified` unless phase 2 changes it.** |
| **R15** | `services/commands/users/reconcile_worker_shift_state.py:200-203` | **WRITER — phase 2.** Same mechanism for the live derived row. |
| R16 | `list_task_steps.py:40`, `tasks.py:650`, `list_working_section_steps.py:306`, `step_record_payload.py:237` | `selectinload` feeding R2; no label logic. |
| R17 | `transition_step_state.py:174-186`, `transition_step_state_batch.py:66-78` | Write-path validation. Phase 2. |
| R18 | `declare_worker_state.py:89-102` | Write-path validation. T3. |
| R19 | `services/queries/pause_reasons/*` | Catalog CRUD; unaffected. |
| R20 | `services/tasks/task_steps/finalize_pending_step_completion.py:35,116` | Opaque payload passthrough. |
| R21 | `services/queries/pause_reasons/get_system_pause_reason.py` + its 3 callers | Phase 2 removes the callers; phase 4 deletes it. |
| R22 | `services/commands/bootstrap/phases/seed_pause_reasons.py` | Seeding; phase 4. |
| — | migrations `ad5da5b32355`, `fb10ac7fd439`, `49bd666da846`, `b58cdffb5ccc` | Historical; not re-run. |

### Validation baseline note (2026-07-31)

The recorded canonical figure (27 failed / 1275 passed at `ccdffa9`) no longer matches this tree —
a clean baseline worktree at `26d290d` measures **24 failed / 1341 passed**. Compared by **node
set**, phase 1 introduces **zero** new failures. The apparent +3 in a naive back-to-back comparison
(`test_seed_pause_reasons_is_idempotent`, `test_pause_reason_crud_and_system_delete_guard`,
`test_create_uses_client_supplied_id_for_new_preference`) are **shared-dirty-database artifacts**:
a *second consecutive run of the unmodified baseline tree* reproduces the identical 27-node set.

## Success criteria (feature set as a whole)

1. Clock-out succeeds in a workspace holding **zero** `pause_reasons` rows, with an open WORKING
   step, and the resulting record is unambiguously identifiable as a shift-ended transition.
2. Task switching auto-pauses a conflicting step in that same zero-catalog workspace.
3. `get_system_pause_reason_id` has no runtime callers and is deleted.
4. No field requires prefix-sniffing to determine its meaning; the
   `startswith(CLIENT_ID_PREFIX)` branch in `domain/users/serializers.py` is gone or provably dead.
5. Historical rows resolve to the same human-visible labels after migration as before.
6. Bootstrapping a second workspace succeeds.

## Open questions

- **Q4 (from the intention) — `auto_pause_description`.** `"started working with {identifier}"` is
  written to `StepStateRecord.description`, a genuinely per-instance value. Provisional ruling: it
  stays where it is; typing the transition does not make the instance detail redundant. Phase 4
  confirms or escalates.
- Whether `WORKER_PAUSED` is the right member name for a worker-chosen step pause, or whether that
  case should carry no `transition_reason` at all (catalog reference alone). Phase 1 decides and
  records; it is cheap to change before any writer ships.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved` (operator reads and approves this master plan, then per-phase plans)
- Transition owner: `David`

## Progress notes

- `2026-07-31`: **Phase 4 amended — `pause_ended_shift` is no longer retired.** Raised by
  `INTENTION_ended_shift_step_state_collapse_20260731`, which found that
  `list_pause_reasons.py:19` filters `is_deleted.is_(False)`, so soft-deleting the row removes it
  from the worker's pause sheet — and the worker app maps that slug to a different state machine
  target. Phase 4 as written would have broken a live frontend flow. Retiring the *machinery* is
  this set's job; retiring the *row* is not, because a worker legitimately picks it. The distinction
  is the feature set's own thesis: a catalog row is fine, a catalog row that system behaviour
  depends on is not.
- `2026-07-31`: **`INTENTION_ended_shift_step_state_collapse_20260731` assessed — successor set, not
  a phase here** (operator ruling). It proposes removing `TaskStepStateEnum.ENDED_SHIFT`, which is
  the same category error one layer up: a state encoding a reason. The dependency on
  `transition_reason` is real, but folding it in would put a **second irreversible enum-and-backfill
  migration** over `step_state_records` and `task_steps` into the single deploy that already carries
  phase 3's, and would make this set cross-repo when every phase of it is backend-only. It must
  start after phase 3's backfill, since its bucketing rewrite reads `transition_reason` on
  historical rows. Its worry that phase 4's check constraints would need revisiting does not hold —
  that constraint governs `transition_reason` vs `pause_reason_id`, which removing a `state` member
  does not touch.

- `2026-07-31`: **Phase 1 archived (APPROVED).** Round 1 returned `NEEDS_CHANGES` on F1 — the
  segment-level reason read dropped a resolution guard that looked incidental
  (`details[0]["pause_reason"]` was in fact the workspace-resolution check), which leaked a foreign
  workspace's `par_…` id into a workspace-scoped response. Fixed structurally:
  `bucket_key(resolved_catalog_ids)` cannot return a catalog id that did not resolve; the reviewer
  confirmed the new guard's extension is *identical* to the deleted one, not merely equivalent in
  the tested case. F2 (inventory figures re-measured quiescent and marked STABLE/VOLATILE), F3
  (`linear_timeline.py:220,264` added to the audit as R23/R24) and F4 (`pause_case_created`
  disposition) closed in the same cycle.

  **T6 was amended** — see the decision above. Phase 1's slug-consumer audit was the mechanism the
  ruling itself named for testing its own condition, and the condition failed. Keeping `slug` costs
  this feature set nothing: no phase 1–3 deliverable depended on the drop.

  Also corrected in flight: the intention's "3132 workspaces, exactly 1" was traced to the shared
  **test** database (accumulated test residue; production remains unmeasured), and
  `UserShiftStateRecord.reason` was shown to hold **no free text at all** — every non-`par_` value is
  a legacy slug string or the literal `"unspecified"`, which makes phase 3's backfill a direct slug
  map with no unmappable tail. The intention's Finding 2 was **confirmed by execution** on a
  disposable database.

- `2026-07-31`: **Phase 1 APPROVED** after one fix cycle. Two repo-health items surfaced that are
  **out of scope for this feature set** (T8) but must not be lost:
  - **Case-created pauses are currently written with no reason at all.** The `pause_case_created`
    catalog row was seeded already soft-deleted (`deleted_at` equals `created_at`) purely as an FK
    target for historical rows, so it is invisible to `list_pause_reasons` and cannot be selected.
    Live rows created by that path therefore carry neither a `pause_reason_id` nor — after phase 1 —
    a `transition_reason`. Phase 3's backfill will meet them, and they are **not** the same 7 rows
    that point at the anchor. Worth attention independently of this migration.
  - **The breakdown endpoint's `pause_reasons` map does not resolve worker-level reasons.** Its map
    is built from step records only, so a worker-level reason with no matching step reason produces
    an unresolvable key. Verified pre-existing by probing both trees. The kiosk clock-out endpoint
    does guarantee full resolution; the breakdown endpoint never did.

- `2026-07-31`: **Restructured from eleven phases to four** (operator call). The eleven-phase draft
  applied declared_worker_states' ceremony — which was sized for new tables, a new auth scope, new
  endpoints and a kiosk flow — to a migration that adds a column, teaches readers, flips three call
  sites, backfills, and deletes leftovers. At ~7 exchanges per implement→review→fix cycle, eleven
  phases cost ~77 exchanges before a single defect. Three of the removed phases existed only to
  satisfy the strict form of T4, which guards against a partial deploy that this delivery shape does
  not have; a fourth (`manually_recorded` subsumption) was cleanup fixing nothing user-facing and is
  now deferred under T7. **The acceptance criteria were preserved verbatim in substance** — they were
  the real output; only the phase boundaries changed. The eleven phase-plan files and the phase 0
  prompts were deleted rather than left alongside the new set.
- `2026-07-31`: **All eleven phase plans written** (phase0 … phase10, this folder). Operator
  resolved the remaining open inputs: T6 confirmed as *drop the column, not only the index*
  (conditional on phase 0's out-of-repo consumer audit finding nothing); delivery runs 0–10 as one
  continuous set with no deliberate stopping point; `pause_ended_shift` confirmed present in the
  production workspace, which this feature set supersedes anyway; `clock_in_code` assignment handled
  manually by the operator; PERSONAL pause reasons already seeded in local and server databases.
  (Superseded by the restructure above.)
- `2026-07-31`: Master plan drafted. Model layer traced: the intention's Finding 4 was corrected
  (`step_state_records.reason` was dropped by `b58cdffb5ccc`; what survives is the soft-deleted
  `pause_case_created` anchor row that history points at via FK). Operator ruled **T5 retire** over
  leaving system rows inert, which makes T6 (drop `slug` + the global unique index) available and
  resolves the second-workspace `IntegrityError` as a consequence. Phase plans not yet written.
