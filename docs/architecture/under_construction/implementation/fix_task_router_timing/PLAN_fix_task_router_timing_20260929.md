# PLAN_fix_task_router_timing_20260929

## Metadata

- Plan ID: `PLAN_fix_task_router_timing_20260929`
- Status: `under_construction`
- Owner agent: implementer (Codex session), handed over by the containerization track
- Created at (UTC): `2026-09-29`
- Last updated at (UTC): `2026-09-29`
- Related finding: deployment repo `managerbeyo-deployment/docs/decision-log.md`, D29 (Step 15 acceptance test), open finding "router race"
- Intention plan: none. This is a one-defect fix; the finding below is the intent.

## Goal and intent

- **Goal:** the task router must commit a task's `OPEN -> PENDING` change **before** it pushes the task id onto its Redis queue.
- **Why:** today it pushes first and commits after the whole batch. A worker can pop the id in that gap. It then runs its claim (`state == PENDING ... FOR UPDATE SKIP LOCKED`), sees the committed `OPEN` row and finds nothing. It logs `task_id=... already claimed — skipping` and drops the id. The row is then committed as `PENDING` with nothing in Redis. It waits until `_recover_stuck_pending_tasks` resets it after `STUCK_PENDING_MINUTES` (5), and the next poll routes it again.
- **Observed:** once, in the Step 15 acceptance run. A `DELAYED_REMINDER` was routed at 08:44:20 and recovered by `stuck_pending_recovered` at 08:49:21, 5 minutes late. Nothing was lost, and 20 further trials did not reproduce it, because locally the router usually wins by milliseconds. The legacy server has the same code, so it has the same exposure.
- **Business intent:** notifications, reminders, scheduled stock-report activations and every other background task start within seconds, never 5 minutes late.
- **Non-goals:**
  - no change to the worker claim, the recovery timings or the queue map;
  - no new retry or error handling for Redis;
  - no change to how many routers may run (still exactly one).

## Scope

- **In scope:**
  - `app/beyo_manager/services/infra/execution/task_router.py`, function `_route_open_tasks` only;
  - one new integration test file;
  - the line keys of the `task_router.py` entries in the write-site registry.
- **Out of scope:**
  - `worker_base.py`;
  - `_requeue_retry_scheduled_tasks`, `_cleanup_stale_tasks` and `_recover_stuck_pending_tasks`, none of which touch Redis;
  - the deployment repository;
  - adding `FOR UPDATE SKIP LOCKED` to the router's `OPEN` select (only matters with more than one router);
  - the duplicate queue entries that stuck-pending recovery can create during a long Redis backlog (harmless, because the claim guard skips them).
- **Assumptions, all verified 2026-09-29:**
  - `async_sessionmaker(..., expire_on_commit=False)` (`models/database.py`), so `task.client_id` and `task.state` stay readable after `commit()` without a lazy load.
  - `task_router.py:141` is the **only** `rpush`/`lpush` onto a `queue:*` list in `beyo_manager/`.
  - The router's `OPEN` select takes no row lock. Its `UPDATE` is flushed only at `commit()`. So before the commit, another connection reads the committed `OPEN` row without blocking. The regression test relies on this.
  - The Redis client is the synchronous `redis` 5.2.1 client (`redis.rpush(...)` is not awaited). Keep it that way.

## The working tree is not clean — read this first

The backend working tree carries a large set of **uncommitted** changes from the containerization track, including this very file (outbound guard, `application_name`, heartbeat). They are intentional and under review.

- Build on the file **as it is on disk**. Do not `git checkout`, `git stash`, reset or reformat anything.
- Touch only the three files listed under "Scope".
- **Do not commit and do not push.** The owner reviews and commits. `backend/CLAUDE.md`: stage explicit paths only, never `git add -A`, never push.
- Why pushing matters: pushing `main` auto-deploys to the legacy production server (`.github/workflows/deploy.yml`).

## Clarifications required

None. The owner approved the fix on 2026-09-29.

## Acceptance criteria

1. In `_route_open_tasks`, no `redis.rpush` runs before the `session.commit()` of the batch that set those tasks `PENDING`.
2. The new regression test **fails on the current code** and passes after the fix. Record both runs in the report.
3. If `rpush` raises after the commit, the task is left `PENDING` with `locked_at` set, and `_recover_stuck_pending_tasks` returns it to `OPEN` once `locked_at` is older than 5 minutes. This failure mode existed before, and the test pins it down.
4. Outbound-cancelled tasks and tasks with no mapped queue behave exactly as before: cancelled or skipped, never pushed.
5. The write-site registry guard passes, with only the `task_router.py` line keys changed. There is no new site, no removed site, and the header count stays unchanged.
6. The full suite's failures are **exactly** the 23 in the baseline file, diffed by ID in both directions.
7. `ruff check` on the two touched Python files reports nothing new. Pre-existing errors stay; confirm any failure is yours before fixing it.

## Contracts and skills

### Contracts loaded

- None needed. This is infrastructure code, not a command, router or serializer.

### File read intent

Relational reads only:
- `task_router.py`
- `worker_base.py` (`_claim_task`, to see what a worker considers claimable)
- `models/database.py` (`expire_on_commit`)
- `tests/integration/services/infra/test_outbound_task_guard.py` (the `_RecordingRedis` seam and the drive-until-settled pattern)

### Skill selection

- Primary skill: none.

## Implementation plan

### Step 1 — write the regression tests first and watch them fail

Create `app/tests/integration/services/infra/test_task_router_commit_before_push.py`. Follow the style of `test_outbound_task_guard.py` in the same folder:
- `pytestmark = [pytest.mark.asyncio, pytest.mark.integration]`;
- the `db_session` fixture;
- `create_instant_task` to make tasks;
- re-read rows with `.execution_options(populate_existing=True)`;
- drive the router in a bounded loop, because it is global and batched (other `OPEN` rows in the worker database may be routed in the same call).

**Test A — `test_a_task_is_committed_pending_before_its_id_reaches_redis`**

A fake Redis records, at the moment of each `rpush`, the task's state **as a separate database connection sees it**. That is exactly what a worker's claim sees. `rpush` is synchronous and runs inside the event loop, so the read has to run on its own thread with its own loop and its own asyncpg connection:

```python
def _committed_state(task_id: str) -> str | None:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def read():
        conn = await asyncpg.connect(dsn)
        try:
            return await conn.fetchval(
                "SELECT state::text FROM execution_tasks WHERE client_id = $1", task_id
            )
        finally:
            await conn.close()

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(read())).result(timeout=10)


class _CommittedStateRedis:
    """Records each push and what a worker would see for that row at that instant."""

    def __init__(self):
        self.pushed = []
        self.state_at_push = {}

    def rpush(self, name, value):
        self.pushed.append((name, value))
        self.state_at_push[value] = _committed_state(value)

    def llen(self, name):
        return sum(1 for queue, _ in self.pushed if queue == name)
```

Arrange, act and assert:
- Create one internal task, e.g. `TaskType.CREATE_NOTIFICATIONS`, which maps to `queue:notifications`. Leave it `OPEN` and commit.
- Set `settings.outbound_integrations_enabled` to `True` with `monkeypatch` so the switch cannot affect it.
- Drive `_route_open_tasks(redis)` until `("queue:notifications", task_id)` is in `redis.pushed`, at most 20 times.
- Assert `redis.state_at_push[task_id] == ExecutionTaskStateEnum.PENDING.value`.

Notes:
- **Corrected 2026-09-29:** the migrated database stores the enum **values** (lowercase: `'pending'`, `'open'`), not the member names. This was observed on a freshly migrated database. So compare with `.value`. If in doubt, run `SELECT enum_range(NULL::execution_task_state_enum)` against the test database.
- Also confirm the column is `client_id` in `execution_tasks`.
- On the current code this test must fail with `'open' != 'pending'`. That is the race, made deterministic.
- There is no deadlock risk. Before the commit, the router holds no lock on the row. After the commit, it holds none either.

**Test B — `test_a_push_that_fails_after_the_commit_is_recovered_by_stuck_pending`**

- Use a fake Redis whose `rpush` raises `redis.exceptions.ConnectionError("down")` and whose `llen` returns 0.
- Create one internal task, `OPEN`, and commit.
- Drive `_route_open_tasks` in a bounded loop, wrapping each call in `pytest.raises(ConnectionError)` or catching it. Stop once the task is no longer `OPEN`.
- Assert the task is `PENDING` and `locked_at is not None`.
- Move its `locked_at` back to `now - timedelta(minutes=STUCK_PENDING_MINUTES + 1)` and commit. Then drive `_recover_stuck_pending_tasks()` until the task is `OPEN`, at most 20 times.
- On the current code, this test fails differently: the push raises **before** the commit, so the task stays `OPEN` and the first assertion fails. That is acceptable. The report should say which assertion failed.

Run both tests **before** changing `task_router.py`:

```bash
cd app && BEYO_TEST_SLOT=<unique> .venv/bin/python -m pytest -q -n 0 \
  tests/integration/services/infra/test_task_router_commit_before_push.py
```

Expected: both fail. Record the failure messages.

### Step 2 — the fix in `_route_open_tasks`

Collect the pushes during the loop, commit, then push. The target shape:

```python
async def _route_open_tasks(redis) -> None:
    now = datetime.now(timezone.utc)
    async for session in get_db_session():
        result = await session.execute(
            select(ExecutionTask)
            .where(ExecutionTask.state == ExecutionTaskStateEnum.OPEN)
            .limit(BATCH_SIZE)
        )
        tasks = result.scalars().all()
        routed: list[tuple[str, str]] = []

        for task in tasks:
            if outbound_blocked(task.task_type):
                ...unchanged...
                continue
            queue_name = QUEUE_MAP.get(task.task_type)
            if not queue_name:
                ...unchanged...
                continue
            task.state = ExecutionTaskStateEnum.PENDING
            task.locked_at = now
            routed.append((queue_name, task.client_id))

        if tasks:
            # Commit before pushing: a worker claims only a committed PENDING row, so an
            # id it pops earlier is dropped until stuck-pending recovery requeues it.
            await session.commit()
            for queue_name, task_id in routed:
                redis.rpush(queue_name, task_id)
            depths = {name: redis.llen(name) for name in set(QUEUE_MAP.values())}
            logger.info("task_router | routed=%d queue_depths=%s", sum(t.state is ExecutionTaskStateEnum.PENDING for t in tasks), depths)
```

Rules:
- Keep the `outbound_task_cancelled` branch, the `no queue mapped` branch, the log line and its wording exactly as they are.
- Keep `if tasks:` as the commit guard. A batch of only cancelled tasks must still commit.
- Do **not** catch the `rpush` exception. It propagates to the existing `task_router: poll error` handler in `run_task_router`. Any tasks not yet pushed stay `PENDING` and are recovered by `_recover_stuck_pending_tasks`. This is the same worst case as today, but now it happens only when Redis is failing, not on a timing coincidence.
- Do not switch to a Redis pipeline or to async Redis. That would be a behaviour change beyond the fix.

Why this is safe:
- If the commit fails, nothing was pushed, the rows stay `OPEN`, and the next poll retries. Before, a queued id with an `OPEN` row was popped and dropped.
- An id reaches Redis only after its row is committed `PENDING`, so a worker that pops it always finds it claimable.

### Step 3 — update the write-site registry

`app/tests/unit/services/commands/stock_report/task_state_write_site_registry.py` keys its entries by `(relpath, lineno)`. Editing `task_router.py` shifts the line numbers of its `.state` writes. Today they are at 142, 162, 181 and 204.

Run:

```bash
cd app && BEYO_TEST_SLOT=<unique> .venv/bin/python -m pytest -q -n 0 \
  tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py
```

- Take the unregistered and stale keys the failure lists, and move **only** the four `beyo_manager/services/infra/execution/task_router.py` entries to their new line numbers.
- Keep them `NOT_TASK` / `ExecutionTask`.
- The number of entries must not change. If the diff shows any other file, or a different count, stop and report; do not "fix" it.

### Step 4 — run the tests

From `app/`, with a slot nobody else is using:

1. The new file: both tests pass.
2. The neighbours that drive `_route_open_tasks`: all pass.
   ```bash
   BEYO_TEST_SLOT=<unique> .venv/bin/python -m pytest -q -n 0 \
     tests/integration/services/infra/test_outbound_task_guard.py \
     tests/integration/services/commands/stock_report/test_draft_version_scheduling.py \
     tests/unit/services/commands/stock_report/test_task_state_write_sites_are_registered.py
   ```
3. The full suite:
   ```bash
   BEYO_TEST_SLOT=<unique> .venv/bin/python -m pytest -q 2>&1 | tee /tmp/router_fix_full.txt
   ```
   Diff the failed test IDs **both ways** against
   `backend/docs/architecture/under_construction/implementation/stock_report/handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`.
   Expected: exactly the same 23, no new failure and none missing. Compare IDs, not counts; the pass count drifts.
4. Lint only the touched files:
   ```bash
   .venv/bin/ruff check beyo_manager/services/infra/execution/task_router.py \
     tests/integration/services/infra/test_task_router_commit_before_push.py
   ```
   An E402 or similar that already exists at HEAD is not yours.

Gotchas:
- Use `-n 0` for single-process runs. `-p no:xdist` exits with code 4 because `pytest.ini` carries `-n 6`.
- Never run two suites on one `BEYO_TEST_SLOT` at the same time; it produces hundreds of spurious failures.
- Use `app/.venv/bin/python`, not a bare `python3`.

### Step 5 — optional end-to-end check

Only if a local stack is already available. The deployment repository's local stack uses fake credentials and has `OUTBOUND_INTEGRATIONS_ENABLED=false`.

- Rebuild the backend image, then create a few internal tasks in a burst.
- Confirm the router log shows no `already claimed — skipping` for them and no `stuck_pending_recovered`.
- **Never** point workers at a production database or use production credentials.
- The race is rare locally, so a clean run proves little. Test A is the real proof.

## Risks and mitigations

- **Risk:** `rpush` fails after the commit and leaves tasks `PENDING` without a queue entry.
  **Mitigation:** existing stuck-pending recovery after 5 minutes. This already happened before, just from a different cause. Test B pins it down.
- **Risk:** reading `task.client_id` after `commit()` triggers a lazy load (`MissingGreenlet`).
  **Mitigation:** `expire_on_commit=False` (verified). The ids are also captured into `routed` before the commit.
- **Risk:** the registry update hides a real new write site.
  **Mitigation:** only the four `task_router.py` keys may move, and the entry count must not change.
- **Risk:** the change reaches the legacy production server.
  **Mitigation:** nothing is pushed by this task. When the owner pushes `main`, the legacy server gets the fix too. It is backward-compatible and needs no migration and no config change.

## Validation plan

- Test A against unfixed code: fails, the state at push is `OPEN`.
- Tests A and B after the fix: pass.
- `test_outbound_task_guard.py`, `test_draft_version_scheduling.py` and the registry guard: pass.
- Full suite: failed IDs equal the 23 baseline IDs, diffed both ways.
- `ruff check` on the touched files: no new errors.

## Report back

Hand back a short report with:
- the diff of the three files;
- the red run of Test A before the fix and the green run after (the failing assertion message);
- the registry key changes (old line to new line);
- the full-suite baseline diff (expected: empty both ways);
- anything you did **not** do, and why.

Do not commit.

## Review log

- `2026-09-29` containerization track: plan written from the Step 15 finding. Code facts verified against the working tree the same day.
- `2026-09-29` containerization track: corrected the enum label note (values, not names). The race reproduced a second time in the D30 acceptance rerun: a worker dropped a scheduled reminder 0.8 ms before the router's commit.

## Lifecycle transition

- Current state: `under_construction`
- Next state: `approved` after owner review of the implementer's report
- Transition owner: owner
