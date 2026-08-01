# Deploy runbook — 2026-08-01, three feature sets, eight migrations

**Read this before pushing.** `git push origin main` **is** the deploy — `.github/workflows/deploy.yml`
triggers on push to `main`, and there is no manual approval step between the push and
`alembic upgrade head` running against production.

There are **126 unpushed commits** on `main` carrying three undeployed feature sets:
`declared_worker_states`, `system_transition_reasons`, and the `ended_shift` collapse — plus the
case-created transition reason, which adds no migration.

---

## The whole chain has been rehearsed against a copy of RDS — 2026-08-01

`secretes/refresh_local_from_rds.sh` restored the RDS `managerbeyo_test` dump over the local
database and ran `alembic upgrade head` on it. **All eight migrations applied cleanly to real data,
in 21 seconds including dump and restore.** `alembic current` → `2645b4327b17 (head)`.

That is worth more than any of the pre-flight probes below, because it *is* the deploy, run once
against the data it will run against. Measured on the result:

| Check | Result |
|---|---|
| `ended_shift` enum member | gone (0) |
| Rows still in `ended_shift` | 0 |
| CHECK violations (both reason channels set) | 0 |
| `pause_other_task_priority` references remaining | 0 (**234** retyped by migration 5) |
| `transition_reason_backfill_journal` | dropped |
| `step_state_records` / `task_steps` | 5,398 / 1,962 |
| The reasonless case-created pauses | **40**, as reported |

**The P2 guard could not have fired** — if it had, migration 8 would have raised and `alembic
current` would not read head.

*Assumption worth naming:* this treats RDS `managerbeyo_test` as the database the server actually
talks to. `alembic current` on the server reads `alembic_version` in that same database, so P1 below
still confirms it directly — and if P1 does not read `d8e4f1a2c6b7`, this rehearsal was against
something else and everything here needs re-deriving.

### The E2 split — measured, and not what this runbook first predicted

| E2 row | What it means | Predicted | **Actual** |
|---|---|---|---|
| 1 | system-typed (`transition_reason = shift_ended`) | 0 | **0** |
| 2 | worker-picked — keeps its catalog reference, stays untyped | some | **153** |
| 3 | untyped clock-out force-close — gets typed `shift_ended` | *"expected to be the bulk"* | **0** |

Row 3 is **empty on real data**, not the bulk. All 153 rows point at `pause_ended_shift`.

The reason is the one migration `97b60e06d42a` already names: before the cutover, a clock-out
force-close *attached the catalog row* rather than leaving the record bare, so a system write and a
worker's pick are historically indistinguishable — and both land in row 2. There was never an
untyped population to find.

### The consequence: `total_ended_shift_seconds` goes to zero for all history

`bucket_for` returns the `ended_shift` bucket only for `state = paused AND transition_reason =
shift_ended`. All 153 rows keep `transition_reason = NULL`, so every one of them now buckets as
**ordinary pause time**. Before the deploy their bucket key was the state itself, so they counted as
ended-shift time.

**100% of historical ended-shift time reclassifies into `total_pause_seconds`.** This is E1 working
exactly as ruled — the metric narrows to *the item stopped and nobody said why* — but the magnitude
was never measured, and it is manager-visible. Going forward the bucket refills normally: post-cutover
clock-out writes the typed `shift_ended` transition, so new force-closes land in it.

**Tell anyone who reads that number before they notice it themselves.**

---

## The chain

Server is expected at `d8e4f1a2c6b7`. Eight migrations, single linear chain, no branches (verified
by walking `down_revision` across all 112 revisions):

```
d8e4f1a2c6b7 (server)
  1. 595e7b840926  create user_declared_state_records table
  2. c2f4a6b8d0e1  repair open legacy manual pause provenance
  3. 67cfba8fcb2d  add clock_in_code to user_work_profiles
  4. a7d21f4c8b03  add transition_reason columns
  5. 97b60e06d42a  backfill other_task_priority  (writes a journal)
  6. b4e7a1c93f28  retire system pause-reason machinery
  7. c8f3d2e60a17  drop the transition-reason backfill journal
  8. 2645b4327b17  collapse ended_shift  ← the expensive one
=> head
```

`alembic upgrade head` runs all eight. No flags, no explicit targets, no environment variables —
`c8f3d2e60a17`'s `ALLOW_DROP_BACKFILL_JOURNAL` guard was removed in `4bece10`.

---

## Why a mid-chain failure is the thing to avoid

`deploy.yml` runs under `set -e`, in this order:

```
git pull → pip install → alembic upgrade head → apply_db_triggers.py → systemctl restart (11 services)
```

A migration that raises stops the script **before the restart**. That leaves the schema partly
migrated, the new code pulled but not running, and every service still on the old code. This has
already happened once in this project's history and is why the journal-drop guard was withdrawn.

So the goal of the pre-flight is simple: **prove no guard can fire, before pushing.**

---

## Pre-flight — run on the server, before `git push`

### P1. Confirm the revision

```bash
cd /var/www/managerbeyo-backend/app && source .venv/bin/activate
set -a; source /home/ubuntu/config/managerbeyo/.env; set +a
APP_ENV=production alembic current
```

**Expect `d8e4f1a2c6b7`.** If it is anything else, stop and re-derive the chain — this figure was
wrong once already in this project and the error propagated into two documents before `alembic
current` caught it. Do not deploy on a remembered revision.

### P2. The one guard that can fire on unknown production data

Every other upgrade-path `raise` is either a post-condition of a migration's own writes, or reads a
table this deploy creates empty. **This one reads live production history:**

```sql
-- 2645b4327b17:147 refuses if any `ended_shift` row is typed as a transition
-- other than `shift_ended`. The only way that arises is a row that is BOTH in
-- state ended_shift AND references pause_other_task_priority (which migration 5
-- retypes to 'other_task_priority').
SELECT count(*) AS must_be_zero
FROM step_state_records ssr
JOIN pause_reasons pr ON pr.client_id = ssr.pause_reason_id
WHERE ssr.state = 'ended_shift'
  AND pr.slug = 'pause_other_task_priority';
```

**Must be `0`.** If it is not, migration 8 raises *after* migrations 1–7 have already applied — the
worst available outcome. Bring the number to me before pushing; it is a real historical
contradiction and wants a rule, not a workaround.

### P3–P6. The before-numbers

```sql
-- P3. What the ACCESS EXCLUSIVE rewrite actually costs. This, not the
-- reclassified rows, sets the lock window. Local: 6,164 / 2,389.
SELECT
  (SELECT count(*) FROM step_state_records) AS step_state_records,
  (SELECT count(*) FROM task_steps)         AS task_steps;

SELECT c.relname,
       (SELECT count(*) FROM pg_index WHERE indrelid = c.oid) AS indexes,
       pg_size_pretty(pg_total_relation_size(c.oid))          AS total_size
FROM pg_class c
WHERE c.relname IN ('step_state_records', 'task_steps');

-- P4. The reclassification population. Local: 208.
SELECT count(*) AS ended_shift_rows
FROM step_state_records WHERE state = 'ended_shift';

-- P5. The E2 split. ANSWERED by the rehearsal above — 153 row 2, 0 row 3 —
-- so this is now a confirmation, not a discovery. Re-run it only if P1
-- disagrees with `d8e4f1a2c6b7`.
SELECT count(*) FILTER (WHERE pause_reason_id IS NOT NULL) AS row_2_worker_picked,
       count(*) FILTER (WHERE pause_reason_id IS NULL)     AS row_3_untyped
FROM step_state_records WHERE state = 'ended_shift';

-- P6. What migration 5 will retype and migration 6 will then retire.
SELECT count(*) AS otp_refs
FROM step_state_records ssr
JOIN pause_reasons pr ON pr.client_id = ssr.pause_reason_id
WHERE pr.slug = 'pause_other_task_priority';
```

Optional but satisfying — the defect the frontend fix stops:

```sql
SELECT count(*) FROM step_state_records
WHERE state = 'paused' AND pause_reason_id IS NULL AND transition_reason IS NULL;
-- ~40 expected, ~35 of them July. Should stop growing after this deploy.
```

### P7. RDS snapshot

Take it, and **wait for it to reach `available`** before pushing. Migration 8 rewrites two tables
under `ACCESS EXCLUSIVE`; a snapshot started against a locked table is not the position you want to
discover it from.

---

## Deploy

```bash
git push origin main
```

Watch the Actions log. The two lines worth reading:

- `[2645b4327b17] reclassified step_state_records: E2 row 1 (system-typed)=…, row 2
  (worker-picked)=…, row 3 (untyped)=…; task_steps=…` — these should reconcile against P4/P5.
- The `systemctl list-units` tail. **If you do not see it, the restart did not happen.**

---

## The two windows, both expected, neither a defect

**1. Between `alembic upgrade head` and `systemctl restart`, old code queries a removed enum
member.** Seven pre-restart sites bind `ended_shift` and will raise:

```
asyncpg.exceptions.InvalidTextRepresentationError:
  invalid input value for enum task_step_state_enum: "ended_shift"
```

`averaged_time._TIME_STATES` and its six analytics consumers, `_roster.TIME_STATES`,
`get_worker_daily_step_breakdown._TIME_STATES` and `_WORK_STATES`,
`get_user_last_active_step_record._ACTIVE_STATES`, `get_worker_working_sections._ACTIVE_STATES`, and
the analytics worker's `TIME_BEARING_STATES`. The working-sections read is worker-facing, so this is
visible to workers, not only to reporting. **It self-heals on restart** and is inherent to removing
an enum member.

**2. `_recreate_enum` rewrites every row of `step_state_records` and `task_steps` under `ACCESS
EXCLUSIVE`, rebuilding every index on both.** Locally that is ~8,500 rows and 21 indexes against 208
rows of actual reclassification — a factor of forty. **P3 is what tells you the real duration.**
Sizing this from the 208 will be wrong.

---

## After

```sql
-- Chain landed
-- (shell) APP_ENV=production alembic current   → expect 2645b4327b17

-- The member is gone and nothing was left behind
SELECT count(*) FROM step_state_records WHERE state = 'paused'
  AND transition_reason = 'shift_ended';     -- ≈ P4 (rows 1+3)
SELECT count(*) FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
WHERE t.typname = 'task_step_state_enum' AND e.enumlabel = 'ended_shift';  -- 0

-- The worker-picked population survived as itself (E2 row 2 keeps its catalog
-- reference and stays untyped) — this is the one that must NOT have moved.
SELECT count(*) FROM step_state_records
WHERE pause_reason_id IS NOT NULL AND transition_reason IS NOT NULL;  -- 0, enforced by CHECK
```

Then **eyeball one manager timeline** for a worker who clocked out that day. Pause segments should
carry labels, not raw keys, and the ended-shift blocks should read as ordinary pauses.

---

## If it stops mid-chain

1. **Do not re-push.** Get `alembic current` first — it tells you exactly how far it got.
2. Read the raised message. Every guard in this chain names its own number and the reason it
   refused; none of them are opaque.
3. Services are still on old code against a partly-new schema. Migrations 1–4 are additive
   (new table, new column, new columns) and old code tolerates them. **5 onward are not** — from
   migration 6 the `pause_other_task_priority` catalog row is gone, and from 8 the enum member is.
4. Downgrade is available but `b4e7a1c93f28`'s downgrade **refuses** if any slug is held by more
   than one workspace — which is the capability its upgrade delivers, so after any workspace
   creates a colliding slug that path closes. Restoring the snapshot is the cleaner recovery.

---

## Known, accepted, not blocking

- **`ended_shift_collapse_journal` is never dropped.** Deliberate — it is what makes migration 8
  reversible, and it holds genuinely per-row information. It will live in production until someone
  decides otherwise.
- **A pre-existing `IntegrityError` in `heal_current_shift`** (open-record index collision when a
  clock-in's `IDLE` falls outside the rebuild window). Reproduces identically at `b59deb0`,
  degrades safely as `skipped_raced_live_reconcile`.
- **The frontend must already be shipped.** Both handoffs are done as of 2026-08-01. The
  case-created one gates this deploy: without it, every case raised from a working step shows the
  worker an error.
