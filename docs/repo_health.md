# Repository health — known debt and deferred work

**Living document.** Things this codebase knows are wrong or unfinished, kept here so they survive
the feature sets that found them. An item living only in a plan's Review log is lost the moment that
plan archives — which is what this file exists to prevent.

Nothing here is a defect in any shipped feature. Each was an explicit scope decision.

**When you fix one, delete it.** When you find one, add it with enough detail that the next reader
can act without re-deriving it.

---

## Test and tooling debt

| Item | Detail |
|---|---|
| **~122 `ruff check` errors**, 5 of them ours | Down from 149 overall. `services/commands/task_steps/transition_step_state.py` carries **5 F401 unused imports** and was touched by the `system_transition_reasons` set, so this is the one ruff item that feature set inherited rather than merely coexisted with. Every other touched file is clean. |
| **The shared `count_queries` fixture is broken** | Unused. Use a local SQLAlchemy listener for batching assertions. |
| **Fresh empty-DB `alembic upgrade head` stalls** | Hangs idle-in-transaction after `CREATE TABLE alembic_version`. Reproduced repeatedly. It is why "bootstrap two workspaces on a disposable database" could not be run as written and had to be substituted with a direct invariant probe. |
| **`client_id_prefix_map.md` records `ussr`** for `UserShiftStateRecord`, whose real prefix is `uss`. |
| **`_step_transition_core.py`'s auto-pause path is unreachable, so its tests prove nothing** | `transition_step_state_batch.py:130` rejects the only steps that would trigger it, which means any test claiming to exercise that path is not reaching it. *(This entry previously also recorded a `NameError` from a missing `select` import. That is fixed — the import rode along in `867b8fb` — and the residue is the coverage claim.)* |
| **The "latching shopify node" description is stale** | An older baseline note said one suite node fails on re-runs and passes in isolation. **None of the current failures passes in isolation.** Do not carry the old description into new prompts. |

## Code defects, unfixed by decision

| Item | Detail |
|---|---|
| **`heal_current_shift` `IntegrityError`** | A worker who clocks in at 08:00 and starts their first task at 09:00 collides on the open-record index: the clock-in's open `IDLE` falls outside the rebuild window and collides when the tail reopens. `_run` catches it as `skipped_raced_live_reconcile`, so it degrades safely. Pre-existing, reproduces identically at `b59deb0`, no `shift_ended` record involved. |

## Data-quality issues

| Item | Detail |
|---|---|
| **The breakdown endpoint's `pause_reasons` map does not resolve worker-level reasons** | Its map is built from step records only, so a worker-level reason with no matching step reason produces an unresolvable key. Verified pre-existing by probing both trees. The kiosk clock-out endpoint *does* guarantee full resolution; this one never did. |

## Deferred work — real features, not debt

| Item | Detail |
|---|---|
| **`manually_recorded` subsumption** (was T7) | `transition_reason` probably subsumes it, and the `changed_by_id IS NOT NULL` provenance heuristic that cost four fix cycles probably becomes unnecessary. Deferred because it fixes nothing user-facing and proving the equivalence safely is a phase of work. Do it when someone next touches that code with a reason to. |
| **`ended_shift_collapse_journal` is never dropped** | Deliberate — it makes the collapse migration reversible, and it holds genuinely per-row information. But it lives in production indefinitely and wants a decision rather than drift. |

## Accepted risks

| Item | Detail |
|---|---|
| **Hardcoded S3 image URLs in `domain/transitions/labels.py`** | They reproduce what the seeded catalog rows carried, and `update_pause_reason.py` has no guard preventing a manager diverging the real row. Worst case is a stale icon, not a broken one. Assessed on **repository evidence alone** — production was never measured. |

---

## The sweep problem — read this before changing what a value means

Three separate times, a change to what a value *is* left a site behind, and each was invisible to
the technique that caught the previous one:

1. **Attribute grep** missed a render site that called `serialize_pause_reason` on a
   separately-fetched local rather than through the attribute being grepped.
2. **Output-key grep** caught that one — it does not depend on how the value was obtained — but
   could not reach the third.
3. **Population change**: a filter that was *never edited* became wrong because the data moved into
   its selection. `_TIME_STATES = (WORKING, PAUSED)` excluded clock-out force-closes only because
   those used to be a different state; when they became `paused`, the query silently started
   matching them.

So when you change what a value means, ask all three:

- what **reads** this value,
- what **emits** it, and
- **what filter previously excluded it, and now doesn't?**

State the result as a list with `file:line`, never as a count. Both files the third mode has bitten
— `heal_open_shifts_today.py` and `backfill_worker_shift_state_records.py` — are offline repair
scripts with no test coverage, which is exactly why nobody notices.
