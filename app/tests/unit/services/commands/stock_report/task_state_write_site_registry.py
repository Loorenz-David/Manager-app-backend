"""The checked-in registry for the MC-2 write-site guard (plan 10 task 3; master
plan §6.8, §9 rule 4).

Every site `_task_state_write_scanner.collect_write_sites()` finds must have exactly
one entry here, keyed by `(relpath, lineno)` (relative to `app/`). Four
classifications, per plan 10 task 3:

- `task_write`: this site writes `Task.state` (or triggers a helper that does) on a
  path this project's sync must cover. `sync_functions` names every function whose
  body must contain a call to `sync_task_stock_assignments` for this site to be
  considered synced (a helper-internal write is covered by its **callers**, never by
  adding the sync call inside the shared helper itself — §5B "why command level").
- `no_sync`: a real `Task` write (or a candidate one) that is deliberately not
  synced, with the reason.
- `paused_driver`: a call to `_apply_step_transition` that always passes
  `new_state=TaskStepStateEnum.PAUSED` literally, so neither task-state helper it
  wraps can ever fire.
- `not_task`: the site's target is not a `Task` instance at all — `model` names what
  it actually is, for a human auditing the registry.

A site missing here is an **unregistered site** (fails the guard); a registry key no
longer produced by the scanner is a **stale entry** (also fails it) — this is
intentional: touching code near one of these sites is meant to force a fresh look.
"""

from __future__ import annotations

TASK_WRITE = "task_write"
NO_SYNC = "no_sync"
PAUSED_DRIVER = "paused_driver"
NOT_TASK = "not_task"

REGISTRY: dict[tuple[str, int], dict] = {
    # ------------------------------------------------------------------
    # attr_state — the 8 real Task.state assignments (master plan §5B audit)
    # ------------------------------------------------------------------
    ("beyo_manager/services/commands/tasks/fail_task.py", 60): {
        "classification": TASK_WRITE,
        "sync_functions": ["fail_task"],
        "note": "S5",
    },
    ("beyo_manager/services/commands/tasks/cancel_task.py", 60): {
        "classification": TASK_WRITE,
        "sync_functions": ["cancel_task"],
        "note": "S6",
    },
    ("beyo_manager/services/commands/tasks/resolve_task.py", 60): {
        "classification": TASK_WRITE,
        "sync_functions": ["resolve_task"],
        "note": "S4",
    },
    ("beyo_manager/services/commands/task_steps/add_task_steps.py", 162): {
        "classification": TASK_WRITE,
        "sync_functions": ["add_task_steps"],
        "note": "S7 (pending -> assigned)",
    },
    ("beyo_manager/services/commands/task_steps/remove_task_step.py", 228): {
        "classification": TASK_WRITE,
        "sync_functions": ["remove_task_step", "remove_task_steps"],
        "note": "S8 (-> pending, no remaining steps); both public callers of "
        "_remove_task_steps_in_session carry the sync call",
    },
    ("beyo_manager/services/commands/tasks/_task_state_transitions.py", 28): {
        "classification": NO_SYNC,
        "reason": "shared helper (maybe_advance_task_to_working) — the sync runs "
        "at each call site, never inside the helper (§5B 'why command level')",
    },
    ("beyo_manager/services/commands/tasks/_task_state_transitions.py", 52): {
        "classification": NO_SYNC,
        "reason": "shared helper (maybe_reopen_task_to_working) — same as above",
    },
    ("beyo_manager/services/commands/tasks/_task_state_transitions.py", 109): {
        "classification": NO_SYNC,
        "reason": "shared helper (maybe_evaluate_task_ready) — same as above",
    },
    # ------------------------------------------------------------------
    # attr_state — not a Task instance (45 sites)
    # ------------------------------------------------------------------
    ("beyo_manager/operations/connecteam_dead_letter.py", 58): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/operations/connecteam_dead_letter.py", 83): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/outbound.py", 73): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/task_router.py", 142): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/task_router.py", 166): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/task_router.py", 185): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/task_router.py", 208): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/worker_base.py", 136): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/worker_base.py", 156): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/worker_base.py", 185): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/worker_base.py", 222): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/worker_base.py", 236): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/execution/worker_base.py", 243): {"classification": NOT_TASK, "model": "ExecutionTask"},
    ("beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py", 87): {"classification": NOT_TASK, "model": "DelayedScheduler"},
    ("beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py", 96): {"classification": NOT_TASK, "model": "DelayedScheduler"},
    ("beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py", 120): {"classification": NOT_TASK, "model": "DelayedScheduler"},
    ("beyo_manager/services/commands/task_steps/cancel_pending_step_completion.py", 46): {"classification": NOT_TASK, "model": "DelayedScheduler"},
    ("beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py", 132): {"classification": NOT_TASK, "model": "TaskStep"},
    ("beyo_manager/services/commands/task_customer_coordination/complete_task_customer_coordination.py", 66): {"classification": NOT_TASK, "model": "TaskCustomerCoordination"},
    ("beyo_manager/services/commands/task_customer_coordination/fail_task_customer_coordination.py", 89): {"classification": NOT_TASK, "model": "TaskCustomerCoordination"},
    ("beyo_manager/services/commands/task_customer_coordination/_transition_coordination_to_coordinating_in_session.py", 28): {"classification": NOT_TASK, "model": "TaskCustomerCoordination"},
    ("beyo_manager/services/commands/task_steps/_upholstery_installation_side_effect.py", 160): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/task_steps/transition_step_state.py", 305): {"classification": NOT_TASK, "model": "TaskStep"},
    ("beyo_manager/services/commands/task_steps/transition_step_state.py", 388): {"classification": NOT_TASK, "model": "TaskStep"},
    ("beyo_manager/services/commands/task_steps/remove_task_step.py", 135): {"classification": NOT_TASK, "model": "TaskStep"},
    ("beyo_manager/services/commands/task_steps/_step_transition_core.py", 156): {"classification": NOT_TASK, "model": "TaskStep"},
    ("beyo_manager/services/commands/task_steps/_step_transition_core.py", 231): {"classification": NOT_TASK, "model": "TaskStep"},
    ("beyo_manager/services/commands/task_post_handling/_sync_post_handling_state_in_session.py", 54): {"classification": NOT_TASK, "model": "TaskPostHandling"},
    ("beyo_manager/services/commands/task_post_handling/complete_task_post_handling.py", 134): {"classification": NOT_TASK, "model": "TaskPostHandling"},
    ("beyo_manager/services/commands/cases/update_case_state.py", 29): {"classification": NOT_TASK, "model": "Case"},
    ("beyo_manager/services/commands/stock_report/_move_assignment.py", 214): {"classification": NOT_TASK, "model": "StockTaskAssignment"},
    ("beyo_manager/services/commands/stock_report/_move_assignment.py", 221): {"classification": NOT_TASK, "model": "StockTaskAssignment"},
    ("beyo_manager/services/commands/stock_report/_move_assignment.py", 337): {"classification": NOT_TASK, "model": "StockTaskAssignment"},
    ("beyo_manager/services/commands/upholstery/set_current_stored_amount_inventory.py", 184): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/upholstery/receive_upholstery_order.py", 64): {"classification": NOT_TASK, "model": "UpholsteryOrder"},
    ("beyo_manager/services/commands/items/complete_single_and_reallocate.py", 50): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/items/complete_single_and_reallocate.py", 91): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/items/apply_surplus_to_requirement.py", 76): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/items/update_requirement_quantity.py", 95): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/items/update_requirement_quantity.py", 107): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/items/update_requirement_quantity.py", 134): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/items/cancel_upholstery_requirements.py", 104): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/items/_allocation_algorithm.py", 48): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/items/mark_requirements_in_use.py", 69): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/items/mark_requirements_completed.py", 86): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    # ------------------------------------------------------------------
    # setattr — 2 real Task writers (both excluded from the direct-field set) +
    # 16 non-Task targets
    # ------------------------------------------------------------------
    ("beyo_manager/services/commands/tasks/update_task.py", 70): {
        "classification": NO_SYNC,
        "reason": "_DIRECT_FIELDS excludes state (§6.1b) — update_task writes no Task.state",
    },
    ("beyo_manager/services/commands/task_post_handling/update_task_post_handling.py", 80): {
        "classification": NO_SYNC,
        "reason": "_DIRECT_FIELDS excludes state, same guarantee as update_task.py",
    },
    ("beyo_manager/services/commands/app_update_presentations/update_presentation.py", 36): {"classification": NOT_TASK, "model": "Presentation"},
    ("beyo_manager/services/commands/app_update_slide_media/update_slide_media.py", 46): {"classification": NOT_TASK, "model": "SlideMedia"},
    ("beyo_manager/services/commands/app_update_slides/update_slide.py", 53): {"classification": NOT_TASK, "model": "Slide"},
    ("beyo_manager/services/commands/customers/update_customer.py", 42): {"classification": NOT_TASK, "model": "Customer"},
    ("beyo_manager/services/commands/emails/update_email_connection.py", 44): {"classification": NOT_TASK, "model": "EmailConnection"},
    ("beyo_manager/services/commands/items/_allocation_algorithm.py", 50): {"classification": NOT_TASK, "model": "ItemUpholsteryRequirement"},
    ("beyo_manager/services/commands/items/find_or_create_item.py", 127): {"classification": NOT_TASK, "model": "Item"},
    ("beyo_manager/services/commands/items/update_item.py", 99): {"classification": NOT_TASK, "model": "Item"},
    ("beyo_manager/services/commands/pause_reasons/update_pause_reason.py", 81): {"classification": NOT_TASK, "model": "PauseReason"},
    ("beyo_manager/services/commands/sku_templates/update_sku_template.py", 40): {"classification": NOT_TASK, "model": "SkuTemplate"},
    ("beyo_manager/services/commands/task_steps/_settle_step_time.py", 142): {"classification": NOT_TASK, "model": "TaskStep"},
    ("beyo_manager/services/commands/task_steps/_settle_step_time.py", 143): {"classification": NOT_TASK, "model": "TaskStep"},
    ("beyo_manager/services/commands/task_steps/_settle_step_time.py", 144): {"classification": NOT_TASK, "model": "TaskStep"},
    ("beyo_manager/services/queries/analytics/reconcile_user_time.py", 154): {"classification": NOT_TASK, "model": "worker-stats accumulator (not an ORM row)"},
    ("beyo_manager/services/queries/analytics/reconcile_user_time.py", 155): {"classification": NOT_TASK, "model": "worker-stats accumulator (not an ORM row)"},
    ("beyo_manager/services/queries/analytics/reconcile_user_time.py", 161): {"classification": NOT_TASK, "model": "worker-stats accumulator (not an ORM row)"},
    # ------------------------------------------------------------------
    # update(Task) / Task(state=...) — the constructor and the phase-3 flag writer
    # ------------------------------------------------------------------
    ("beyo_manager/services/commands/stock_report/_task_flag.py", 8): {
        "classification": NO_SYNC,
        "reason": "writes is_stock_assignment, not state (phase 3, APPROVED, "
        "master plan §6.5 _task_flag.py row)",
    },
    ("beyo_manager/services/commands/tasks/create_task.py", 115): {
        "classification": NO_SYNC,
        "reason": "creation — no assignment can reference a task that does not exist yet (§5B)",
    },
    # ------------------------------------------------------------------
    # helper_call — calls to the 4 named functions (13 sites)
    # ------------------------------------------------------------------
    ("beyo_manager/services/commands/task_steps/transition_step_state.py", 413): {
        "classification": TASK_WRITE,
        "sync_functions": ["transition_step_state"],
        "note": "S1 (maybe_advance_task_to_working call)",
    },
    ("beyo_manager/services/commands/task_steps/transition_step_state.py", 424): {
        "classification": TASK_WRITE,
        "sync_functions": ["transition_step_state"],
        "note": "S1 (maybe_evaluate_task_ready call)",
    },
    ("beyo_manager/services/commands/task_steps/transition_step_state_batch.py", 176): {
        "classification": TASK_WRITE,
        "sync_functions": ["transition_step_state_batch"],
        "note": "S2 (_apply_step_transition call)",
    },
    ("beyo_manager/services/commands/task_steps/add_task_steps.py", 186): {
        "classification": TASK_WRITE,
        "sync_functions": ["add_task_steps"],
        "note": "S7 (maybe_reopen_task_to_working call)",
    },
    ("beyo_manager/services/commands/task_steps/remove_task_step.py", 232): {
        "classification": TASK_WRITE,
        "sync_functions": ["remove_task_step", "remove_task_steps"],
        "note": "S8 (maybe_evaluate_task_ready call inside the shared helper)",
    },
    ("beyo_manager/services/commands/task_steps/_step_transition_core.py", 255): {
        "classification": TASK_WRITE,
        "sync_functions": ["force_task_ready", "transition_step_state_batch"],
        "note": "the shared core's maybe_advance_task_to_working call — covered by "
        "its two non-paused callers' own sync calls (S3, S2); the three "
        "paused-driver callers never reach this branch (new_state=PAUSED is "
        "neither WORKING nor terminal)",
    },
    ("beyo_manager/services/commands/task_steps/_step_transition_core.py", 260): {
        "classification": TASK_WRITE,
        "sync_functions": ["force_task_ready", "transition_step_state_batch"],
        "note": "the shared core's maybe_evaluate_task_ready call — same as above",
    },
    ("beyo_manager/services/commands/tasks/force_task_ready.py", 165): {
        "classification": TASK_WRITE,
        "sync_functions": ["force_task_ready"],
        "note": "S3 (_apply_step_transition call, new_state=SKIPPED)",
    },
    ("beyo_manager/services/commands/tasks/force_task_ready.py", 220): {
        "classification": TASK_WRITE,
        "sync_functions": ["force_task_ready"],
        "note": "S3 (maybe_evaluate_task_ready call, allow_stepless=True)",
    },
    ("beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py", 178): {
        "classification": TASK_WRITE,
        "sync_functions": ["handle_finalize_pending_step_completion"],
        "note": "S9 (maybe_evaluate_task_ready call)",
    },
    ("beyo_manager/services/commands/cases/_case_created_step_pause.py", 133): {
        "classification": PAUSED_DRIVER,
    },
    ("beyo_manager/services/commands/users/_clock_worker_shift.py", 204): {
        "classification": PAUSED_DRIVER,
    },
    ("beyo_manager/services/commands/users/declare_worker_state.py", 143): {
        "classification": PAUSED_DRIVER,
    },
}
