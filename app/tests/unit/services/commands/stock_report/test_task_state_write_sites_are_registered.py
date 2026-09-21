"""Plan 10 — C4: the MC-2 write-site guard (master plan §6.8, §9 rule 4; intention
§5B "The guard").

An AST sweep of `app/beyo_manager/**/*.py` and `app/scripts/**/*.py` (excluding
`app/tests/**` and `app/migrations/**`) collects every site MC-2 names — a `.state`
attribute write, a `setattr()` call, an `update(Task)`/`insert(Task)` call, a
`Task(...)` constructor carrying `state=`, and a call to one of the four sync-adjacent
helpers — and checks it against the checked-in registry
(`task_state_write_site_registry.py`). C4(a) is this file's own control row: on the
current tree, every collected site has a registry entry, every registry entry is
still produced by the collector, every `task_write`'s named sync function(s) really
call `sync_task_stock_assignments`, and every `paused_driver`'s `new_state=` is
literally `TaskStepStateEnum.PAUSED`.

C4(b)-(h), the six required probes plus the staleness check, are the tester's
arming work (master plan §3B: named mutations move to the tester); this file proves
only that the instrument is correctly wired on the tree as shipped.
"""

from __future__ import annotations

import pytest

from tests.unit.services.commands.stock_report._task_state_write_scanner import (
    call_keyword_value_repr,
    collect_write_sites,
    function_contains_call,
    function_exists,
)
from tests.unit.services.commands.stock_report.task_state_write_site_registry import (
    NOT_TASK,
    NO_SYNC,
    PAUSED_DRIVER,
    REGISTRY,
    TASK_WRITE,
)

pytestmark = pytest.mark.unit

_VALID_CLASSIFICATIONS = {TASK_WRITE, NO_SYNC, PAUSED_DRIVER, NOT_TASK}


def test_c4a_every_collected_site_has_a_registry_entry():
    scanned_keys = {site.key for site in collect_write_sites()}
    registry_keys = set(REGISTRY.keys())

    unregistered = scanned_keys - registry_keys
    assert not unregistered, f"unregistered site(s): {sorted(unregistered)}"


def test_c4a_every_registry_entry_is_still_produced_by_the_scanner():
    scanned_keys = {site.key for site in collect_write_sites()}
    registry_keys = set(REGISTRY.keys())

    stale = registry_keys - scanned_keys
    assert not stale, f"stale registry entry/entries: {sorted(stale)}"


def test_c4a_every_registry_entry_has_a_recognized_classification():
    for key, entry in REGISTRY.items():
        assert entry["classification"] in _VALID_CLASSIFICATIONS, (
            f"{key}: unrecognized classification {entry['classification']!r}"
        )


def test_c4a_every_task_write_sync_function_exists_and_calls_the_sync():
    for key, entry in REGISTRY.items():
        if entry["classification"] != TASK_WRITE:
            continue
        sync_functions = entry["sync_functions"]
        assert sync_functions, f"{key}: task_write with no sync_functions listed"
        for function_name in sync_functions:
            assert function_exists(function_name), (
                f"{key}: sync_functions names {function_name!r}, which does not "
                "exist anywhere in the scanned corpus (stale registry entry)"
            )
            assert function_contains_call(
                key[0], function_name, "sync_task_stock_assignments"
            ), (
                f"{key}: {function_name!r} does not call "
                "sync_task_stock_assignments anywhere in its body"
            )


def test_c4a_every_paused_driver_passes_the_literal_paused_state():
    for (relpath, lineno), entry in REGISTRY.items():
        if entry["classification"] != PAUSED_DRIVER:
            continue
        value = call_keyword_value_repr(relpath, lineno, "new_state")
        assert value == "TaskStepStateEnum.PAUSED", (
            f"{relpath}:{lineno}: paused_driver's new_state= is {value!r}, not the "
            "literal TaskStepStateEnum.PAUSED"
        )


def test_c4a_no_sync_and_not_task_entries_carry_their_required_field():
    for key, entry in REGISTRY.items():
        if entry["classification"] == NO_SYNC:
            assert entry.get("reason"), f"{key}: no_sync entry with no reason"
        if entry["classification"] == NOT_TASK:
            assert entry.get("model"), f"{key}: not_task entry with no model"


# C4(i) — MC-2's "why command level" rule, made checkable (owner, 2026-09-21, batch
# C2 review card 2). A helper-level sync would move an assignment through an
# intermediate state the transaction never settles on (e.g.
# `ready -> in_queue -> ready` inside one `remove_task_step` save), un-crediting and
# re-crediting a goal for no net task change, possibly onto a *different* goal
# record. The positive checks above prove every registered command-level site is
# wired; this is the mirror negative: none of the three helpers, nor the shared
# step-transition core, may carry the call themselves. The reviewer planted exactly
# this call inside `maybe_evaluate_task_ready` and the guard passed without it
# (finding F-3) — this assertion is what makes that plant fail.
_NO_SYNC_INSIDE_HELPERS = (
    "maybe_advance_task_to_working",
    "maybe_reopen_task_to_working",
    "maybe_evaluate_task_ready",
    "_apply_step_transition",
)


def test_c4i_no_sync_call_inside_the_task_state_helpers_or_the_shared_core():
    for helper in _NO_SYNC_INSIDE_HELPERS:
        assert not function_contains_call(None, helper, "sync_task_stock_assignments"), (
            f"{helper}: calls sync_task_stock_assignments directly — the sync runs "
            "once, at command level, after the command's last Task.state write, "
            "never inside a helper that flips an intermediate state (§5B "
            "'why command level')"
        )
