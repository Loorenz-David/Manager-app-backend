# Completion-counting gap — measured 2026-08-11

Substantiating evidence for `backfill_missing_completion_counts.py`. Recorded because
the figures below were measured against a production snapshot and are not derivable
from any code in this repo — the script encodes the *remedy*, not the measurement.

## What was measured

Completions are written to `step_state_records` on every transition, but were only
counted into the analytics rollups from a certain date. Before it, the records exist
and the rollups do not reflect them.

Measured against a production copy restored locally on 2026-08-11, before any backfill
was applied to it:

| month | from records | in `user_daily_work_stats` | gap |
|---|---|---|---|
| 2026-06 | 59 | 0 | **59** |
| 2026-07 | 1038 | 600 | **438** |
| 2026-08 | 431 | 431 | **0** |

Total gap: **497** completions, against 1528 COMPLETED records.

Day-level, the last day showing any gap:

| day | from records | in rollup | gap |
|---|---|---|---|
| 2026-07-16 | 50 | 41 | **9** |
| 2026-07-15 | 71 | 0 | 71 |
| 2026-07-14 | 81 | 0 | 81 |
| 2026-07-13 | 47 | 0 | 47 |
| …earlier days… | | 0 | all uncounted |

Every day from **2026-07-17** onward is exact. So 2026-07-16 is a partial go-live day,
not the start of a leak — which is why `--until 2026-07-16` is the recommended bound.

## Why this is historical debt and not an ongoing leak

Two independent signals, both from the same measurement session:

1. The gap was **exactly 497** in two separate production snapshots taken days apart.
   A live leak would have grown between them.
2. Between those snapshots, records rose 1523 → 1528 and rollups rose 1026 → 1031 —
   both by exactly 5. Every completion recorded in that window was counted correctly.

## The query

Re-runnable against any snapshot that has not yet been backfilled:

```sql
with rec as (
  select coalesce(r.credited_user_id, r.created_by_id) as user_id,
         (r.entered_at at time zone 'UTC')::date as work_date,
         count(*) as recorded
  from step_state_records r
  where r.state = 'completed' and r.is_deleted is false
    and r.created_by_id is not null
  group by 1, 2
)
select to_char(date_trunc('month', coalesce(rec.work_date, ud.work_date)), 'YYYY-MM') as month,
       sum(coalesce(rec.recorded, 0))::int                                    as from_records,
       sum(coalesce(ud.total_completed_count, 0))::int                        as in_rollup,
       sum(coalesce(rec.recorded, 0) - coalesce(ud.total_completed_count, 0))::int as gap
from rec
full outer join user_daily_work_stats ud
  on ud.user_id = rec.user_id and ud.work_date = rec.work_date
group by 1 order by 1;
```

Attribution uses `COALESCE(credited_user_id, created_by_id)` to match the live worker,
the backfill, and the functional index `ix_step_state_records_ws_credited_entered`.

## Caveats

- **The August row has a shelf life.** "2026-08 gap 0" was true on 2026-08-11. It is a
  statement about that snapshot, not a standing guarantee. Re-run the query to confirm
  the gap has not reopened before relying on it.
- **The local copy no longer reproduces this.** The backfill was executed against it on
  2026-08-11 (rollups now 1528 = records 1528). Reproducing these figures needs a fresh
  snapshot or a read-only production query.
- Production was **not** backfilled as part of this measurement.
