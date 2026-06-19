# PLAN_scheduler_interruptible_sleep_20260619

## Metadata

- Plan ID: `PLAN_scheduler_interruptible_sleep_20260619`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-06-19T00:00:00Z`
- Last updated at (UTC): `2026-06-19T12:57:55Z`
- Related issue/ticket: none
- Intention plan: none

## Goal and intent

- Goal: Replace the single long `asyncio.sleep(sleep_for)` inside the sleep-mode block of both scheduler runners with a short-interval polling loop that re-checks `ActivityTracker.is_sleeping()` every 2 seconds, so an HTTP-request wake signal is acted on within 2 seconds instead of up to 300 seconds.
- Business/user intent: The step-completion undo window is 5 seconds. When the system is in sleep mode and a worker marks a step as complete, the `delayed_scheduler_runner` can currently be stuck in `asyncio.sleep(300)`, making the actual completion fire up to 5 minutes late. This destroys the undo window semantics for the first interaction after an idle period.
- Non-goals: Changing the sleep-mode entry/exit logic in `ActivityTracker` or `task_router`. Changing `POLL_INTERVAL_SECONDS`, `SCHEDULER_SLEEP_CAP_SECONDS`, or any firing logic. Changing `WAKE_CHECK_INTERVAL_SECONDS` below 2 — values under 2 seconds increase Redis query load without meaningful benefit.

## Scope

- In scope:
  - `backend/app/beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py`: replace `await asyncio.sleep(sleep_for)` inside the `if ActivityTracker.is_sleeping():` block with an interruptible loop.
  - `backend/app/beyo_manager/services/infra/schedulers/recurring_scheduler_runner.py`: same change — identical sleep-mode block, identical fix.
- Out of scope:
  - `task_router.py` sleep mode — its 30-second sleep is for a different purpose (skipping task dispatch when idle) and is not on a critical timing path.
  - The 10-second `asyncio.sleep(POLL_INTERVAL_SECONDS)` at the bottom of each runner's loop — this runs only in non-sleeping mode and is already bounded and acceptable.
  - Frontend, commands, queries, models, or any other files.
- Assumptions:
  - Both files already import `timedelta` from `datetime` — no new imports needed.
  - A 2-second re-check interval is sufficient. It bounds the worst-case wake delay at 2 seconds, well within any reasonable undo window.
  - `ActivityTracker.is_sleeping()` is a synchronous Redis EXISTS call — cheap and safe to call every 2 seconds from an async context.

## Clarifications required

*(none — root cause confirmed, fix confirmed)*

## Acceptance criteria

1. When `ActivityTracker.touch()` is called (e.g., by an HTTP request) while `delayed_scheduler_runner` is in sleep mode, the runner exits its sleep within ≤ 2 seconds and resumes normal polling.
2. When `ActivityTracker.touch()` is called while `recurring_scheduler_runner` is in sleep mode, the runner exits its sleep within ≤ 2 seconds and resumes normal polling.
3. When the sleep mode persists and `next_due_at` arrives during the loop, the runner still fires on schedule — existing `next_due_at` logic is preserved exactly.
4. `py_compile` passes on both changed files.
5. No change to `POLL_INTERVAL_SECONDS`, `SCHEDULER_SLEEP_CAP_SECONDS`, or any firing logic.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/contracts/11_infra_events.md`: background workers — understand dispatch boundaries.
- `backend/docs/architecture/contracts/51_worker_runtime.md` (if present): worker lifecycle — confirms the sleep/wake model.

### Local extensions loaded

*(none)*

### File read intent — pattern vs. relational

Permitted reads before editing:
- Both scheduler runner files — to locate exact anchor lines for replacement.

Prohibited:
- Reading other worker files to understand sleep logic — the pattern is self-contained in each runner file.

### Skill selection

- Primary skill: direct file edit — no command/router/serializer skill applies here.

## Implementation plan

### Step 1 — `delayed_scheduler_runner.py`: add constant and replace sleep

File: `backend/app/beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py`

**1a. Add constant**

Locate the existing constants block:
```python
POLL_INTERVAL_SECONDS      = 10
SCHEDULER_SLEEP_CAP_SECONDS = 300   # max sleep even when no jobs are due
ERROR_RETRY_MINUTES         = 15
```
Replace with:
```python
POLL_INTERVAL_SECONDS       = 10
SCHEDULER_SLEEP_CAP_SECONDS = 300   # max sleep even when no jobs are due
WAKE_CHECK_INTERVAL_SECONDS = 2     # re-check is_sleeping() at this cadence
ERROR_RETRY_MINUTES         = 15
```

**1b. Replace the uninterruptible sleep**

Locate the exact block inside `run_delayed_scheduler_runner`:
```python
        if ActivityTracker.is_sleeping():
            if next_due_at is not None:
                sleep_for = max(0.0, (next_due_at - datetime.now(timezone.utc)).total_seconds())
                sleep_for = min(sleep_for, SCHEDULER_SLEEP_CAP_SECONDS)
            else:
                sleep_for = SCHEDULER_SLEEP_CAP_SECONDS
            await asyncio.sleep(sleep_for)
            if next_due_at is None or datetime.now(timezone.utc) < next_due_at:
                continue
            ActivityTracker.touch()  # due time arrived — wake the system before firing
```

Replace with:
```python
        if ActivityTracker.is_sleeping():
            if next_due_at is not None:
                sleep_for = max(0.0, (next_due_at - datetime.now(timezone.utc)).total_seconds())
                sleep_for = min(sleep_for, SCHEDULER_SLEEP_CAP_SECONDS)
            else:
                sleep_for = SCHEDULER_SLEEP_CAP_SECONDS
            deadline = datetime.now(timezone.utc) + timedelta(seconds=sleep_for)
            while ActivityTracker.is_sleeping():
                remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
                if remaining <= 0:
                    break
                await asyncio.sleep(min(WAKE_CHECK_INTERVAL_SECONDS, remaining))
            if next_due_at is None or datetime.now(timezone.utc) < next_due_at:
                continue
            ActivityTracker.touch()  # due time arrived — wake the system before firing
```

`timedelta` is already imported at line 3 of this file. No new imports needed.

---

### Step 2 — `recurring_scheduler_runner.py`: add constant and replace sleep

File: `backend/app/beyo_manager/services/infra/schedulers/recurring_scheduler_runner.py`

**2a. Add constant**

Locate the existing constants block:
```python
POLL_INTERVAL_SECONDS       = 10
SCHEDULER_SLEEP_CAP_SECONDS = 300   # max sleep between checks when sleeping
BATCH_SIZE                  = 200   # prevents unbounded memory load
```
Replace with:
```python
POLL_INTERVAL_SECONDS       = 10
SCHEDULER_SLEEP_CAP_SECONDS = 300   # max sleep between checks when sleeping
WAKE_CHECK_INTERVAL_SECONDS = 2     # re-check is_sleeping() at this cadence
BATCH_SIZE                  = 200   # prevents unbounded memory load
```

**2b. Replace the uninterruptible sleep**

Locate the exact block inside `run_recurring_scheduler_runner`:
```python
        if ActivityTracker.is_sleeping():
            if next_due_at is not None:
                sleep_for = max(0.0, (next_due_at - datetime.now(timezone.utc)).total_seconds())
                sleep_for = min(sleep_for, SCHEDULER_SLEEP_CAP_SECONDS)
            else:
                sleep_for = SCHEDULER_SLEEP_CAP_SECONDS
            await asyncio.sleep(sleep_for)
            if next_due_at is None or datetime.now(timezone.utc) < next_due_at:
                continue
            ActivityTracker.touch()  # due time arrived — wake the system before firing
```

Replace with:
```python
        if ActivityTracker.is_sleeping():
            if next_due_at is not None:
                sleep_for = max(0.0, (next_due_at - datetime.now(timezone.utc)).total_seconds())
                sleep_for = min(sleep_for, SCHEDULER_SLEEP_CAP_SECONDS)
            else:
                sleep_for = SCHEDULER_SLEEP_CAP_SECONDS
            deadline = datetime.now(timezone.utc) + timedelta(seconds=sleep_for)
            while ActivityTracker.is_sleeping():
                remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
                if remaining <= 0:
                    break
                await asyncio.sleep(min(WAKE_CHECK_INTERVAL_SECONDS, remaining))
            if next_due_at is None or datetime.now(timezone.utc) < next_due_at:
                continue
            ActivityTracker.touch()  # due time arrived — wake the system before firing
```

`timedelta` is already imported at line 5 of this file. No new imports needed.

---

## Risks and mitigations

- Risk: `ActivityTracker.is_sleeping()` calls Redis on every 2-second tick — adds Redis query load.
  Mitigation: Redis EXISTS on a single key is ~0.1ms. At one call per 2 seconds per runner, this is 1 call/second total across both runners — negligible.

- Risk: The `while ActivityTracker.is_sleeping():` loop exits immediately if `is_sleeping()` is already False when first entered (e.g., the system was woken between the outer `if` check and entering the loop).
  Mitigation: This is correct behavior — if sleep mode ended, skip the loop entirely and fall through to the `next_due_at` check. The `continue` at the bottom (`if next_due_at is None or now < next_due_at: continue`) ensures the runner goes back to normal polling rather than accidentally firing stale jobs.

- Risk: `deadline` computed once at the top of the loop — if the system stays in sleep mode for exactly `sleep_for` seconds, `remaining` hits 0 and the loop breaks. This mirrors the original single-sleep behavior for the normal case.
  Mitigation: Behavior is identical to the original when `is_sleeping()` never becomes False. The loop simply runs `sleep_for / 2` iterations of 2-second sleeps instead of one big sleep.

## Validation plan

- `python3 -m py_compile backend/app/beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py backend/app/beyo_manager/services/infra/schedulers/recurring_scheduler_runner.py`: must pass with no output.
- `grep -n "WAKE_CHECK_INTERVAL_SECONDS\|while ActivityTracker" backend/app/beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py backend/app/beyo_manager/services/infra/schedulers/recurring_scheduler_runner.py`: must match in both files.
- `grep -n "await asyncio.sleep(sleep_for)" backend/app/beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py backend/app/beyo_manager/services/infra/schedulers/recurring_scheduler_runner.py`: must return no matches — the bare single-sleep must be gone from both files.

## Review log

- `2026-06-19T12:57:55Z` — Implemented the planned scheduler sleep-loop change in both runner files, validated with `py_compile`, wrote the implementation summary, and archived the plan.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `codex`
