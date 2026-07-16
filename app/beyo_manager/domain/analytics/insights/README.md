# Worker Insights Engine

Predefined, statistically-gated observations about a worker's performance **on a given day**,
compared against that worker's **own** recent baseline. Consumed today by
`GET /api/v1/worker-stats/last-interacted-steps` (one `insights` array per worker), but the
engine is a **reusable domain service** — any service can call it.

> Keep this file up to date. When you add or change an insight, update the [catalog](#insight-catalog)
> and, if the pipeline changes, the [how it's computed](#how-an-insight-is-computed) section.

---

## Layout

Pure domain logic (no DB, no session, fully typed, unit-tested without fixtures — see `08_domain`):

```
domain/analytics/insights/
  results.py   # DailyStats (input) + Insight (output) dataclasses
  metrics.py   # MetricSpec registry — how to extract each number from a day
  rules.py     # InsightRule registry — the menu, as data (codes + thresholds)
  config.py    # InsightsConfig — tunable knobs (baseline window, gates, top_k)
  stats.py     # median, z-score, materiality, severity
  engine.py    # evaluate(...) — the pure pipeline
```

The session-bound entrypoint lives in the query layer:

```
services/queries/analytics/compute_worker_insights.py
  compute_worker_insights(ctx, user_ids, target_date, config) -> dict[user_id, list[Insight]]
```

It does **one** bounded window read of `user_daily_work_stats`, builds `DailyStats` per day, and calls
`evaluate` per user. Other services (worker-detail view, digest email, alerting worker) call this same
function — the engine never knows who's asking.

---

## How an insight is computed

For a worker's target day `D`, `evaluate` runs this pipeline per rule:

1. **Target must be active.** If the worker did nothing on `D` (`DailyStats.is_active` false), no insights.
2. **Extract the day's value.** `MetricSpec.extract(target)`. If `None` (undefined, e.g. a zero
   denominator), skip this rule — never crash.
3. **Build the baseline.** The **same weekday** over the previous `baseline_weeks` weeks
   (`D-7, D-14, …`), counting **only active days** where the metric is defined. Days off are excluded
   so they can't deflate the average and fake a surge.
4. **Sufficiency gate.** Need at least `min_samples` (default 2) baseline points, else stay silent
   (new workers legitimately show nothing).
5. **Compare.** `baseline = median(samples)` (robust to one weird day); `delta = value − baseline`.
   Skip if `delta == 0`.
6. **Direction → code.** `improved = (delta > 0) == metric.higher_is_better`. Pick `code_positive` if
   improved else `code_negative`; if that direction's code is `None`, skip (e.g. we flag *rising*
   pauses but don't celebrate low ones).
7. **Materiality gate.** Must clear **both** an absolute (`abs_threshold`) and a relative
   (`rel_threshold = |delta|/|baseline|`) bar. When the baseline is 0 the relative bar is undefined, so
   the absolute bar alone decides.
8. **Statistical gate.** Once samples ≥ `z_min_samples` (default 3), also require `|z| ≥ z_threshold`.
   With fewer samples, threshold-only. *This is why widening `baseline_weeks` later self-tightens the
   results — more samples → the z-gate activates → fewer false positives, no code change.*
9. **Rank & cap.** Correlated duplicates are dropped (a `throughput` insight is removed if a
   `completed_count` insight of the same polarity is present — same story). Remaining candidates are
   sorted **strongest-first** (severity, then magnitude) and capped at `top_k` (default 3).

**Streak** (`on_a_roll`) is computed separately (it needs consecutive days, not same-weekday) and appended
before ranking — skipped on an in-progress day.

### In-progress day

When `target_date` is today (UTC), the day isn't over, so **cumulative-volume** metrics look artificially
low. Rules whose metric is not `intraday_safe` are withheld; distribution ratios (focus, avg-pause) still
run. `compute_worker_insights` sets this flag from `target_date == now(UTC).date()`.

---

## Insight catalog

Metrics come from `user_daily_work_stats` columns. `higher_is_better` decides which direction is positive.

| Metric | Formula | Higher is better | Intraday-safe |
|---|---|---|---|
| `completed_count` | `total_completed_count` | ✅ | ❌ |
| `focus_ratio` | `working / (working + pause)` | ✅ | ✅ |
| `throughput` | `completed / (working_seconds / 3600)` | ✅ | ❌ |
| `avg_pause_seconds` | `pause_seconds / pause_count` | ❌ | ✅ |
| `fragmentation` | `working_count / completed_count` | ❌ | ❌ |
| `shift_end_count` | `ended_shift_count` | ❌ | ❌ |
| `resolve_rate` | `issues_resolved / issues` | ✅ | ❌ |

Rules (thresholds are v1 starting points in `rules.py`, tune freely):

| Code | Polarity | Metric | Fires when… | abs / rel thresholds |
|---|---|---|---|---|
| `completion_surge` | positive | `completed_count` | completed well above their same-weekday median | 3 / 40% |
| `completion_dip` | negative | `completed_count` | completed well below | 3 / 40% |
| `deep_focus` | positive | `focus_ratio` | much less time paused than usual | 0.10 / 30% |
| `faster_pace` | positive | `throughput` | more steps per focused hour | 0.40 / 25% |
| `slower_pace` | negative | `throughput` | fewer steps per focused hour | 0.40 / 25% |
| `rising_pauses` | negative | `avg_pause_seconds` | longer average pause (possible blockers) | 120s / 30% |
| `leaving_steps_mid_shift` | negative | `shift_end_count` | ending shifts mid-step more than usual | 2 / 50% |
| `choppy_work` | negative | `fragmentation` | more work-sessions per finished step | 1.0 / 40% |
| `quality_watch` | negative | `resolve_rate` | resolving a smaller share of issues | 0.20 / 25% |
| `on_a_roll` | positive | `completed_count` | ≥ `streak_min_days` consecutive days at/above their recent bar | — |

> The code set will grow. Consumers must treat unknown codes as ignorable and branch on
> `polarity` / `severity`, never hard-code the full list.

---

## Reading an Insight

`Insight` (see `results.py`) is codes + numbers only — **copy is rendered client-side** (i18n).

| Field | How to read it |
|---|---|
| `code` | Which observation (see catalog). Drives the copy string. |
| `polarity` | `"positive"` (recognize) or `"negative"` (attention). **Trust this — do not infer valence from `delta`'s sign** (rising pauses is negative though the number went up). |
| `metric` | The underlying metric key. |
| `target_value` | The day's value for that metric. |
| `baseline_value` | The median of the baseline samples it was compared against. |
| `delta` | `target_value − baseline_value` (signed). |
| `delta_pct` | `delta / baseline_value`, or `null` when the baseline is 0. |
| `sample_size` | How many baseline days back this stands on — surface it for honesty ("vs your last 3 Wednesdays"). |
| `severity` | `"low" \| "medium" \| "high"` — ordering/emphasis. The list is already sorted strongest-first. |

For `on_a_roll`: `target_value` is the streak length (days), `baseline_value` the bar it cleared.

---

## Configuration

`InsightsConfig` (in `config.py`) — pass a custom one to `evaluate` / `compute_worker_insights`:

| Knob | Default | Meaning |
|---|---|---|
| `baseline_weeks` | 4 | Same-weekday samples looked back. **Widen here later.** |
| `min_samples` | 2 | Minimum baseline points before any insight fires. |
| `z_min_samples` | 3 | Sample count at which the statistical gate activates. |
| `z_threshold` | 1.0 | `|z|` a candidate must clear when the gate applies. |
| `top_k` | 3 | Max insights per worker. |
| `streak_min_days` | 3 | Consecutive days needed for `on_a_roll`. |
| `streak_lookback_days` | 14 | Window used to compute the streak bar. |
| `rules` | `DEFAULT_RULES` | Which rules are enabled. |

Severity bands live in `stats.py`: with a z-score, `|z| ≥ 2` high / `≥ 1.3` medium; otherwise relative
magnitude `≥ 100%` high / `≥ 60%` medium.

---

## Adding a new insight

1. **Need a new number?** Add a `MetricSpec` to `METRICS` in `metrics.py` — set `higher_is_better` and
   `intraday_safe`, and make `extract` return `None` when undefined (no div-by-zero).
2. **Add the rule** to `DEFAULT_RULES` in `rules.py`: metric key, `code_positive` / `code_negative`
   (`None` to disable a direction), and `abs`/`rel` thresholds.
3. **No engine changes needed** for a standard comparison insight — the pipeline is metric-agnostic.
   (Only special shapes like streaks need engine code.)
4. **Test it** in `tests/unit/domain/analytics/insights/` — pure, no DB: build a `daily_by_date` dict and
   assert the code fires / stays silent at the boundary.
5. **Update this README's [catalog](#insight-catalog)** and tell the frontend team the new `code`
   (copy is theirs to write).

---

## Testing

- Engine: `tests/unit/domain/analytics/insights/test_engine.py` — pure, fast, no fixtures.
- Query path: `tests/integration/services/queries/analytics/test_compute_worker_insights.py` — seeds real
  rows and asserts an insight fires through the SQL.
