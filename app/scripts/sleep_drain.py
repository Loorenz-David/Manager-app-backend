"""Wait until the background workers have finished every task, before a planned stop.

    python -m scripts.sleep_drain --timeout 930 [--poll 5]
    # host: docker compose run --rm migrate python -m scripts.sleep_drain --timeout 930

Run by the host's drain sequence after ingress and the API are stopped, while the task
router and the queue workers still run (they finish the work; the router must run for
OPEN tasks to reach a queue). It needs neither the API nor its heartbeat.

Drained means, for task types some worker consumes (``scripts.sleep_eligibility``'s
``CONSUMED_QUEUES``; orphan types are ignored as they never drain):

    OPEN + PENDING + IN_PROGRESS + RETRYING == 0   and   every consumed Redis queue is empty

RETRY_SCHEDULED tasks are not waited for — the eligibility check that precedes the drain
refuses when a retry is due within its horizon.

Progress lines go to stderr; stdout gets exactly one JSON object at the end::

    {"schema":1,"drained":bool,"outcome":"drained|timeout|aborted|failed",
     "waited_seconds":float,"remaining":{"open":n,"pending":n,"in_progress":n,
     "retrying":n,"queues":{"queue:…":n}}|null,"orphan":{…}|null,"error":str|null}

Exit codes: 0 drained, 1 timed out or aborted (SIGTERM/SIGINT, promptly — the host
aborts a drain when a wake request arrives), 2 the drain itself failed (database or
Redis unreachable, bad arguments). Uses one database connection
(``managerbeyo:sleep-drain``) for the whole wait, closed before exit.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import signal
import sys
import time
from collections.abc import Sequence

from beyo_manager.domain.execution.enums import ExecutionTaskStateEnum
from scripts.sleep_eligibility import (
    CONSUMED_QUEUES,
    SCHEMA,
    close_redis,
    connect,
    consumed_queue_backlog,
    logs_to_stderr,
    query_task_counts,
    read_queue_lengths,
    safe_error,
    summarize_tasks,
)

EXIT_DRAINED = 0
EXIT_NOT_DRAINED = 1
EXIT_FAILED = 2

APPLICATION_NAME = "managerbeyo:sleep-drain"
DEFAULT_POLL_SECONDS = 5.0

_WAITED_FOR = (
    ExecutionTaskStateEnum.OPEN,
    ExecutionTaskStateEnum.PENDING,
    ExecutionTaskStateEnum.IN_PROGRESS,
    ExecutionTaskStateEnum.RETRYING,
)


def _progress(message: str) -> None:
    print(f"[sleep-drain] {message}", file=sys.stderr, flush=True)


async def poll_remaining(connection) -> tuple[dict, dict]:
    """(remaining work that blocks the drain, orphan counts that do not)."""
    summary = summarize_tasks(await query_task_counts(connection), {})
    queues = consumed_queue_backlog(await read_queue_lengths(CONSUMED_QUEUES))
    remaining = {state.value: summary.count(state) for state in _WAITED_FOR}
    remaining["queues"] = queues
    return remaining, summary.orphan


def is_drained(remaining: dict) -> bool:
    return not any(remaining[state.value] for state in _WAITED_FOR) and not remaining["queues"]


def _result(outcome: str, waited: float, remaining: dict | None, orphan: dict | None, error: str | None = None) -> dict:
    return {
        "schema": SCHEMA,
        "drained": outcome == "drained",
        "outcome": outcome,
        "waited_seconds": round(waited, 3),
        "remaining": remaining,
        "orphan": orphan,
        "error": error,
    }


async def drain(timeout: float, poll: float, *, clock=time.monotonic) -> dict:
    """Poll until drained, ``timeout`` elapses, or SIGTERM/SIGINT arrives."""
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    state = {"aborted": False}

    def _abort() -> None:
        if not state["aborted"]:
            state["aborted"] = True
            task.cancel()

    handled = []
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _abort)
            handled.append(sig)
        except (NotImplementedError, RuntimeError):  # not the main thread
            pass

    started = clock()
    remaining: dict | None = None
    orphan: dict | None = None
    try:
        connection = await connect(APPLICATION_NAME)
        try:
            while True:
                remaining, orphan = await poll_remaining(connection)
                waited = clock() - started
                if is_drained(remaining):
                    _progress(f"drained after {waited:.1f}s")
                    return _result("drained", waited, remaining, orphan)
                _progress(
                    f"waiting {waited:.0f}s/{timeout:.0f}s: "
                    + " ".join(f"{s.value}={remaining[s.value]}" for s in _WAITED_FOR)
                    + f" queues={json.dumps(remaining['queues'], sort_keys=True)}"
                )
                if waited >= timeout:
                    _progress("timed out")
                    return _result("timeout", waited, remaining, orphan)
                await asyncio.sleep(min(poll, max(timeout - waited, 0.0)))
        finally:
            try:
                await asyncio.wait_for(connection.close(), timeout=5)
            except Exception:
                connection.terminate()
    except asyncio.CancelledError:
        if not state["aborted"]:
            raise
        _progress("aborted by signal")
        return _result("aborted", clock() - started, remaining, orphan)
    finally:
        for sig in handled:
            loop.remove_signal_handler(sig)
        await close_redis()


class ArgumentError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):
        raise ArgumentError(message)


def _positive(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected a number") from None
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("expected a finite number > 0")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="python -m scripts.sleep_drain",
        description="Wait until every consumed task and queue is drained; one JSON result.",
    )
    parser.add_argument("--timeout", type=_positive, required=True, help="seconds to wait at most")
    parser.add_argument("--poll", type=_positive, default=DEFAULT_POLL_SECONDS,
                        help="seconds between checks (default 5)")
    return parser


def _emit(result: dict) -> None:
    sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def exit_code_for(result: dict) -> int:
    if result["outcome"] == "drained":
        return EXIT_DRAINED
    if result["outcome"] == "failed":
        return EXIT_FAILED
    return EXIT_NOT_DRAINED


def main(argv: Sequence[str] | None = None) -> int:
    logs_to_stderr()
    started = time.monotonic()
    try:
        args = build_parser().parse_args(argv)
    except ArgumentError as exc:
        result = _result("failed", 0.0, None, None, f"invalid arguments: {exc}")
        _emit(result)
        return EXIT_FAILED
    try:
        result = asyncio.run(drain(args.timeout, args.poll))
    except Exception as exc:  # the drain could not observe the work: fail, never "drained"
        _progress(f"failed: {safe_error(exc)}")
        result = _result("failed", time.monotonic() - started, None, None, safe_error(exc))
    _emit(result)
    return exit_code_for(result)


if __name__ == "__main__":
    sys.exit(main())
