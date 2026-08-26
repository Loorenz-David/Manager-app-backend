# Span-only entries (no symbol) — separate judgment pass, NOT in the batches

For each: open the file. If the cited region has a name (function, class, method),
re-anchor to path + that symbol with no range. If it is genuinely nameless
(config block, migration body, one branch), leave it — the span is the sanctioned exception.

- `node:domain-task-execution` evidence[0] — `app/beyo_manager/domain/task_steps/enums.py` lines 4-12
  summary: TaskStepStateEnum defines PENDING, WORKING, PAUSED, BLOCKED, COMPLETED, SKIPPED, FAILED, CANCELLED.
- `node:domain-work-analytics` evidence[0] — `app/beyo_manager/domain/analytics/concurrency.py` lines 35-76
  summary: Sweep-line algorithm dividing each instant of real time among concurrently open intervals.
- `node:concept-terminal-vs-time-bearing` evidence[0] — `app/beyo_manager/domain/task_steps/constants.py` lines 4-20
  summary: Frozensets TERMINAL_STEP_STATES, TIME_BEARING_STATES and TERMINAL_TASK_STATES.
- `node:concept-terminal-vs-time-bearing` evidence[1] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 65-79
  summary: Time recomputation is gated on `closing_state in TIME_BEARING_STATES`.
- `node:concept-credited-user-vs-performer` evidence[1] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 143-168
  summary: Analytics attributes via COALESCE(credited_user_id, created_by_id).
- `node:concept-one-active-step-per-user` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 233-291
  summary: On a WORKING transition for a non-batch step, fetches any conflicting open record and force-pauses it with OTHER_TASK_PRIORITY.
- `node:concept-one-active-step-per-user` evidence[1] — `app/beyo_manager/models/tables/tasks/step_state_record.py` lines 100-106
  summary: Partial unique index uix_step_state_records_active on (workspace_id, step_id) where exited_at IS NULL.
- `node:decision-mirrored-transition-body` evidence[0] — `app/beyo_manager/services/commands/task_steps/_step_transition_core.py` lines 3-11
  summary: DRIFT NOTE docstring stating the core MIRRORS transition_step_state and any change to either MUST be evaluated for the other, kept in sync by convention (Option B).
- `node:decision-mirrored-transition-body` evidence[1] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 116-121
  summary: The mirrored DRIFT NOTE on the single-step side pointing back at the core.
- `node:decision-code-owned-transition-reasons` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 267-274
  summary: Comment: 'System transition: typed from the code-owned vocabulary, never resolved from the workspace catalog, so this works in a workspace holding zero pause reasons.'
- `node:decision-undo-window-disabled` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 193-234
  summary: A large commented-out block scheduling PENDING_STEP_COMPLETION, prefaced by a NOTE that undo-window scheduling is temporarily disabled and should be kept for future re-enablement.
- `node:decision-credited-user-no-fk` evidence[0] — `app/beyo_manager/models/tables/tasks/step_state_record.py` lines 84-91
  summary: credited_user_id column declared for analytics attribution with a comment noting the deliberate absence of a FK.
- `node:vocab-step-state-constants` evidence[0] — `app/beyo_manager/domain/task_steps/constants.py` lines 4-20
  summary: Three frozensets partitioning the step and task state enums.
- `node:domain-concurrency-sweep` evidence[0] — `app/beyo_manager/domain/analytics/concurrency.py` lines 35-105
  summary: _sweep at 35, averaged_seconds_by_record at 79, wasted_seconds_by_record at 96.
- `node:domain-user-shift-state-machine` evidence[0] — `app/beyo_manager/domain/users/shift_state_machine.py` lines 4-30
  summary: DURATIONFUL_STATES and BOUNDARY_MARKERS frozensets plus the target-state derivation.
- `node:endpoint-transition-step-state` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 1109-1127
  summary: Route handler building a ServiceContext and calling transition_step_state through run_service.
- `node:endpoint-transition-step-state-batch` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 1128-1144
  summary: Route handler dispatching to transition_step_state_batch.
- `node:endpoint-cancel-pending-step-completion` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 1145-1162
  summary: Route handler dispatching to cancel_pending_step_completion.
- `node:endpoint-mark-step-time-inaccurate` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 1163-1180
  summary: Route handler dispatching to mark_step_time_inaccurate.
- `node:endpoint-assign-worker-to-step` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 1012-1030
  summary: Route handler dispatching to assign_worker_to_step.
- `node:endpoint-list-task-steps` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 933-952
  summary: Route handler dispatching to the list_task_steps query.
- `node:endpoint-count-task-step-states` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 953-972
  summary: Route handler dispatching to the count_task_step_states query.
- `node:endpoint-list-workers-totals` evidence[0] — `app/beyo_manager/routers/api_v1/worker_stats.py` lines 52-79
  summary: Route handler dispatching to list_workers_totals.
- `node:endpoint-worker-daily-step-breakdown` evidence[0] — `app/beyo_manager/routers/api_v1/worker_stats.py` lines 130-164
  summary: Route handler dispatching to get_worker_daily_step_breakdown.
- `node:endpoint-worker-linear-timeline-breakdown` evidence[0] — `app/beyo_manager/routers/api_v1/worker_stats.py` lines 165-200
  summary: Route handler dispatching to get_worker_linear_timeline_breakdown.
- `node:endpoint-list-working-section-steps` evidence[0] — `app/beyo_manager/routers/api_v1/working_sections.py` lines 145-175
  summary: Route handler dispatching to list_working_section_steps.
- `node:task-finalize-pending-step-completion` evidence[1] — `app/beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py` lines 217-220
  summary: TODO noting section side effects are not fired from this path.
- `node:event-process-step-transition` evidence[0] — `app/beyo_manager/domain/execution/enums.py` lines 43-43
  summary: TaskType.PROCESS_STEP_TRANSITION = 43.
- `node:event-create-notifications` evidence[0] — `app/beyo_manager/domain/execution/enums.py` lines 22-22
  summary: TaskType.CREATE_NOTIFICATIONS = 22.
- `node:event-delayed-step-completion` evidence[0] — `app/beyo_manager/domain/execution/enums.py` lines 30-30
  summary: TaskType.DELAYED_STEP_COMPLETION = 30.
- `node:ws-task-step-state-changed` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 471-490
  summary: Builds state_changed_items including the auto-paused step, then dispatches a BatchWorkspaceEvent.
- `node:ws-task-state-changed` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 491-494
  summary: Conditional dispatch guarded on task.state != old_task_state.
- `node:ws-task-step-readiness-changed` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 495-503
  summary: Iterates readiness_changes from the cascade and emits a WorkspaceEvent per dependent step.
- `node:ws-worker-shift-state-changed` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 99-110
  summary: Comment explains this is the only place that can announce the shift change; emit_worker_shift_state is called only when shift_reconcile.changed is true.
- `node:infra-pg-notify-task-open` evidence[0] — `app/scripts/apply_db_triggers.py` lines 17-30
  summary: DDL creating the trigger and its notify function.
- `node:infra-queue-analytics` evidence[0] — `app/beyo_manager/services/infra/execution/task_router.py` lines 34-34
  summary: QUEUE_MAP entry TaskType.PROCESS_STEP_TRANSITION: 'queue:analytics'.
- `node:infra-queue-notifications` evidence[0] — `app/beyo_manager/services/infra/execution/task_router.py` lines 19-19
  summary: QUEUE_MAP entry TaskType.CREATE_NOTIFICATIONS: 'queue:notifications'.
- `node:infra-queue-tasks` evidence[0] — `app/beyo_manager/services/infra/execution/task_router.py` lines 27-27
  summary: QUEUE_MAP entry TaskType.DELAYED_STEP_COMPLETION: 'queue:tasks'.
- `node:infra-analytics-worker` evidence[0] — `app/beyo_manager/workers/analytics_worker.py` lines 10-20
  summary: HANDLER_MAP mapping PROCESS_STEP_TRANSITION to the analytics handler, then run_worker on queue:analytics.
- `node:infra-notification-worker` evidence[0] — `app/beyo_manager/workers/notification_worker.py` lines 11-25
  summary: HANDLER_MAP with CREATE_NOTIFICATIONS at line 13 and the run_worker call.
- `node:infra-tasks-worker` evidence[0] — `app/beyo_manager/workers/tasks_worker.py` lines 26-40
  summary: HANDLER_MAP with DELAYED_STEP_COMPLETION at line 27 and the run_worker call.
- `node:infra-delayed-scheduler-runner` evidence[0] — `app/beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py` lines 30-80
  summary: Polls due scheduler rows and creates execution tasks from their payload snapshots.
- `node:infra-event-bus` evidence[0] — `app/beyo_manager/services/infra/events/event_bus.py` lines 21-60
  summary: Dispatcher iterating registered handlers for each event.
- `node:infra-worker-shift-realtime` evidence[0] — `app/beyo_manager/services/infra/events/worker_shift_realtime.py` lines 39-70
  summary: Defines the worker-shift event names and the emit helper used across processes.
- `node:projection-list-workers-totals` evidence[0] — `app/beyo_manager/services/queries/worker_stats/list_workers_totals.py` lines 39-80
  summary: Query joining UserDailyWorkStats and UserSectionDailyWorkStats with StepStateRecord and TaskStep.
- `node:projection-worker-daily-step-breakdown` evidence[0] — `app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py` lines 83-130
  summary: Query over StepStateRecord, TaskStep, Task, User and the two daily stat tables.
- `node:projection-worker-linear-timeline-breakdown` evidence[0] — `app/beyo_manager/services/queries/worker_stats/get_worker_linear_timeline_breakdown.py` lines 325-380
  summary: Loads records, items, pause reasons and shift records, then applies the timeline collapse.
- `node:projection-worker-clock-out-analytics` evidence[0] — `app/beyo_manager/services/queries/worker_stats/get_worker_clock_out_analytics.py` lines 199-240
  summary: Query aggregating records, items, issues and images for a shift, taking (ctx, user_id, clock_out_at).
- `node:projection-worker-clock-out-analytics` evidence[1] — `app/beyo_manager/routers/api_v1/worker_shifts.py` lines 117-152
  summary: Routes call the analytics query directly at lines 117 and 150 inside try/except rather than through run_service.
- `node:projection-list-workers-insights` evidence[0] — `app/beyo_manager/services/queries/analytics/compute_worker_insights.py` lines 25-60
  summary: Loads daily rows into DailyStats and delegates to the pure evaluate().
- `node:domain-estimation-strategies` evidence[0] — `app/beyo_manager/domain/analytics/estimation/strategies.py` lines 11-60
  summary: TimeEstimationStrategy with iqr_trimmed_mean and estimate_fill.
- `node:script-backfill-completed-count` evidence[0] — `app/scripts/backfill/backfill_completed_count.py` lines 71-160
  summary: _collect_counts at 71 and _write_counts at 132 rebuild completion counters absolutely.
- `node:concept-attribution-split` evidence[2] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 65-79
  summary: reconcile_user_day_time and apply_reconcile_deltas are both called with payload.credited_user_id, not with any id derived from the closing record.
- `node:concept-attribution-split` evidence[4] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 269-281
  summary: The auto-pause record DOES set credited_user_id explicitly, unlike the ordinary new record.
- `node:decision-idempotent-completion-counters` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 88-117
  summary: The COMPLETED branch now calls reconcile_user_day_completions + apply_completion_reconcile_deltas + _recompute_step_completion_totals instead of incrementing.
- `node:decision-idempotent-completion-counters` evidence[1] — `app/beyo_manager/services/infra/execution/worker_base.py` lines 84-108
  summary: _process_task runs the handler in one session then marks the task COMPLETED in a separate _finalize_task session; failure in between routes to _fail_task and retries.
- `node:rule-issue-counting-ignores-marked-wrong` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 92-99
  summary: The COMPLETED branch is commented 'Applies regardless of recorded_time_marked_wrong: inaccurate time does not suppress the fact that the step completed or that it carried issues.' and is gated only on state, never on the flag.
- `node:finding-completion-counting-golive` evidence[0] — `docs/architecture/implemented_summaries/completion_counting_gap_20260811.md` lines 1-50
  summary: Dated measurement document records a 497-completion historical rollup gap, identifies 2026-07-16 as the final partial day, and states that every day from 2026-07-17 onward is exact.
- `node:domain-item-economics` evidence[0] — `app/beyo_manager/domain/item_economics/calculator.py` lines 1-52
  summary: The module declares itself as the pure canonical calculator, defines the calculation-version contract, and exposes a named re-derivation skip marker.
- `node:domain-item-economics` evidence[1] — `app/beyo_manager/domain/item_economics/calculator.py` lines 131-242
  summary: The calculator validates term shape and computes percentage, fixed, and purchase-cost snapshot amounts through the canonical term functions.
- `node:domain-item-economics` evidence[2] — `app/beyo_manager/domain/item_economics/calculator.py` lines 375-547
  summary: Re-derivation reads the evaluation and term snapshot fields, recomputes rate, term amounts, budget, and allowance, and rejects mismatched stored values without reading foreign keys.
- `node:endpoint-item-economics-post-cost-groups` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 92-98
  summary: ADMIN/MANAGER route for creating a production-cost group.
- `node:endpoint-item-economics-get-cost-groups` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 101-108
  summary: ADMIN/MANAGER route for listing workspace-scoped production-cost groups with limit-plus-one pagination.
- `node:endpoint-item-economics-patch-cost-group` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 111-118
  summary: ADMIN/MANAGER route for renaming a production-cost group.
- `node:endpoint-item-economics-delete-cost-group` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 121-127
  summary: ADMIN/MANAGER route for guarded soft deletion of a production-cost group.
- `node:endpoint-item-economics-post-section` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 130-137
  summary: ADMIN/MANAGER route for adding a working section to a group.
- `node:endpoint-item-economics-delete-section` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 140-147
  summary: ADMIN/MANAGER route for removing an active group-section membership.
- `node:endpoint-item-economics-post-basis` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 150-158
  summary: ADMIN/MANAGER route for creating a production-cost basis version.
- `node:endpoint-item-economics-get-basis` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 161-169
  summary: ADMIN/MANAGER route for listing basis versions for a group.
- `node:endpoint-item-economics-delete-basis` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 172-178
  summary: ADMIN/MANAGER route for guarded soft deletion of a basis version.
- `node:endpoint-item-economics-post-model` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 181-187
  summary: ADMIN/MANAGER route for creating a complete cost-model version.
- `node:endpoint-item-economics-get-model` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 190-197
  summary: ADMIN/MANAGER route for listing cost-model versions and their terms.
- `node:endpoint-item-economics-delete-model` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 200-206
  summary: ADMIN/MANAGER route for guarded soft deletion of a cost-model version.
- `node:endpoint-item-economics-status` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 209-214
  summary: ADMIN/MANAGER route for the pure ordered configuration-status projection.
- `node:table-item` evidence[0] — `app/beyo_manager/models/tables/items/item.py` lines 1-87
  summary: The Item model post-phase-6: identity, category snapshot at :46 (String(64), nullable), no money columns.
- `node:source-file-item-economics-price-scenario` evidence[0] — `app/beyo_manager/domain/item_economics/price_scenario.py` lines 14-211
  summary: The module defines SEARCH_CAP_MINOR, the CostModelTermInput Protocol, the PriceModel and SliderDomain carriers, integer half-even rounding, term collapse, the price-to-allowance conversion, capped lower-bound searches, exact rational step helpers and slider-band derivation. Its imports are dataclasses, decimal, fractions, typing, item_economics.enums and errors.validation only.
- `node:decision-item-economics-production-budget-cap-v1` evidence[7] — `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_budget_cap_20260820.md` lines 11-41
  summary: The dated frontend handoff documents the 25 percent cap, version-2 historical behavior, wire field, replay formula, and AT-PRICE consequence.
- `node:configuration-shipped-pytest-parallel-default` evidence[0] — `app/pytest.ini` lines 1-2
  summary: The shipped pytest addopts include -n 6 and --dist loadfile alongside the strict runner settings.
- `edge:endpoint-transition-step-state--accepts-->command-transition-step-state` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 1109-1127
  summary: Route builds a ServiceContext and passes transition_step_state to run_service.
- `edge:endpoint-transition-step-state-batch--accepts-->command-transition-step-state-batch` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 1128-1144
  summary: Route dispatches to transition_step_state_batch.
- `edge:endpoint-cancel-pending-step-completion--accepts-->command-cancel-pending-step-completion` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 1145-1162
  summary: Route dispatches to cancel_pending_step_completion.
- `edge:endpoint-mark-step-time-inaccurate--accepts-->command-mark-step-time-inaccurate` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 1163-1180
  summary: Route dispatches to mark_step_time_inaccurate.
- `edge:endpoint-assign-worker-to-step--accepts-->command-assign-worker-to-step` evidence[0] — `app/beyo_manager/routers/api_v1/tasks.py` lines 1012-1030
  summary: Route dispatches to assign_worker_to_step.
- `edge:endpoint-list-workers-totals--calls-->projection-list-workers-totals` evidence[0] — `app/beyo_manager/routers/api_v1/worker_stats.py` lines 52-79
  summary: Route dispatches to the list_workers_totals query.
- `edge:endpoint-worker-daily-step-breakdown--calls-->projection-worker-daily-step-breakdown` evidence[0] — `app/beyo_manager/routers/api_v1/worker_stats.py` lines 130-164
  summary: Route dispatches to get_worker_daily_step_breakdown.
- `edge:endpoint-worker-linear-timeline-breakdown--calls-->projection-worker-linear-timeline-breakdown` evidence[0] — `app/beyo_manager/routers/api_v1/worker_stats.py` lines 165-200
  summary: Route dispatches to get_worker_linear_timeline_breakdown.
- `edge:command-transition-step-state--writes_to-->table-step-state-record` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 316-348
  summary: Closes the open record by setting exited_at and adds a new StepStateRecord.
- `edge:command-transition-step-state--writes_to-->table-task-step` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 353-364
  summary: Updates step.state, latest_state_record_id, updated_at and closed_at on terminal states.
- `edge:command-transition-step-state--writes_to-->table-task` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 366-385
  summary: Advances the task to WORKING or evaluates it READY as a side effect of the step transition.
- `edge:command-transition-step-state--reads_from-->table-pause-reason` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 170-182
  summary: Loads the pause reason and enforces requires_description before proceeding.
- `edge:command-transition-step-state--reads_from-->table-task-item` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 244-265
  summary: Reads the PRIMARY task item and its item to build the auto-pause description.
- `edge:command-transition-step-state--writes_to-->table-task-step-acknowledgment` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 369-376
  summary: On a WORKING transition, bulk-acknowledges the step's pending obligations.
- `edge:command-transition-step-state--produces-->event-process-step-transition` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 413-417
  summary: Unconditionally enqueues PROCESS_STEP_TRANSITION with the closing interval payload.
- `edge:command-transition-step-state--produces-->event-process-step-transition` evidence[1] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 294-314
  summary: A second PROCESS_STEP_TRANSITION is enqueued for the auto-paused conflicting step.
- `edge:command-transition-step-state--produces-->event-create-notifications` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 429-469
  summary: Enqueues task_step_state_changed and, when task state changed, task_state_changed notifications.
- `edge:command-transition-step-state--produces-->ws-task-step-state-changed` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 471-490
  summary: Builds the batched state-changed items and dispatches after the transaction closes.
- `edge:command-transition-step-state--produces-->ws-task-state-changed` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 491-494
  summary: Conditionally appends the task state event when the task state actually changed.
- `edge:command-transition-step-state--produces-->ws-task-step-readiness-changed` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 495-503
  summary: Emits one readiness event per dependent step changed by the cascade.
- `edge:command-transition-step-state--calls-->helper-cascade-step-completion` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 387-390
  summary: On COMPLETED, calls cascade_step_completion and keeps the readiness changes for dispatch.
- `edge:command-transition-step-state--calls-->helper-fetch-open-user-working-record` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 234-237
  summary: Queries for a conflicting open WORKING record before entering WORKING.
- `edge:command-transition-step-state--calls-->helper-task-state-transitions` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 366-385
  summary: Calls maybe_advance_task_to_working and maybe_evaluate_task_ready.
- `edge:command-transition-step-state--calls-->command-mark-step-obligations-acknowledged` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 371-376
  summary: Acknowledges step obligations when the step enters WORKING.
- `edge:command-transition-step-state--calls-->src-create-instant-task` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 413-417
  summary: Uses create_instant_task to publish the outbox event inside the transaction.
- `edge:command-transition-step-state-batch--calls-->helper-apply-step-transition` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state_batch.py` lines 50-120
  summary: Applies each validated item through the shared core inside one transaction.
- `edge:command-pause-task-working-steps-for-case--calls-->helper-apply-step-transition` evidence[0] — `app/beyo_manager/services/commands/cases/_case_created_step_pause.py` lines 100-150
  summary: Pauses each open WORKING step through the shared core with CASE_CREATED.
- `edge:helper-apply-step-transition--calls-->helper-cascade-step-completion` evidence[0] — `app/beyo_manager/services/commands/task_steps/_step_transition_core.py` lines 57-160
  summary: The core cascades dependency completion just as the single-step command does.
- `edge:helper-apply-step-transition--calls-->helper-fetch-open-user-working-record` evidence[0] — `app/beyo_manager/services/commands/task_steps/_step_transition_core.py` lines 84-95
  summary: The core performs the same one-active-step conflict lookup and auto-pause.
- `edge:helper-apply-step-transition--produces-->event-process-step-transition` evidence[0] — `app/beyo_manager/services/commands/task_steps/_step_transition_core.py` lines 145-240
  summary: Enqueues PROCESS_STEP_TRANSITION at line 145 and again at 233 for the auto-paused step.
- `edge:helper-apply-step-transition--writes_to-->table-step-state-record` evidence[0] — `app/beyo_manager/services/commands/task_steps/_step_transition_core.py` lines 57-160
  summary: Closes and opens interval records identically to the single-step command.
- `edge:helper-apply-step-transition--writes_to-->table-task-step` evidence[0] — `app/beyo_manager/services/commands/task_steps/_step_transition_core.py` lines 57-160
  summary: Updates step state and latest record pointer.
- `edge:task-finalize-pending-step-completion--produces-->event-process-step-transition` evidence[0] — `app/beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py` lines 183-190
  summary: Enqueues PROCESS_STEP_TRANSITION with closing_state from the closing record and new_state COMPLETED.
- `edge:task-finalize-pending-step-completion--writes_to-->table-step-state-record` evidence[0] — `app/beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py` lines 100-180
  summary: Closes the record at completion_requested_at and opens a COMPLETED record inline.
- `edge:task-finalize-pending-step-completion--calls-->helper-task-state-transitions` evidence[0] — `app/beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py` lines 159-162
  summary: Delegates to maybe_evaluate_task_ready with a comment explaining why it is not reimplemented.
- `edge:helper-cascade-step-completion--calls-->src-recalculate-readiness` evidence[0] — `app/beyo_manager/services/commands/task_steps/_cascade_completion.py` lines 40-45
  summary: Recomputes readiness for each dependent after incrementing its counter.
- `edge:helper-cascade-step-completion--reads_from-->table-task-step-dependency` evidence[0] — `app/beyo_manager/services/commands/task_steps/_cascade_completion.py` lines 10-40
  summary: Selects dependent steps via the dependency edge table.
- `edge:command-assign-worker-to-step--writes_to-->table-task-step-assignment-record` evidence[0] — `app/beyo_manager/services/commands/task_steps/assign_worker_to_step.py` lines 98-140
  summary: Closes the active assignment interval and opens a new one.
- `edge:command-mark-step-time-inaccurate--writes_to-->table-step-state-record` evidence[0] — `app/beyo_manager/services/commands/task_steps/mark_step_time_inaccurate.py` lines 17-45
  summary: Sets recorded_time_marked_wrong and taken_from_average on the record.
- `edge:command-cancel-pending-step-completion--writes_to-->table-delayed-scheduler` evidence[0] — `app/beyo_manager/services/commands/task_steps/cancel_pending_step_completion.py` lines 14-40
  summary: Flips the active scheduler row to CANCELED.
- `edge:command-transition-step-state--implements-->concept-step-state-machine` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 147-155
  summary: Rejects terminal states and validates the requested transition against _ALLOWED_TRANSITIONS.
- `edge:command-transition-step-state--implements-->concept-one-active-step-per-user` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 233-291
  summary: Auto-pauses a conflicting WORKING record using the deduplicated performer/credited user set.
- `edge:helper-apply-step-transition--implements-->concept-one-active-step-per-user` evidence[0] — `app/beyo_manager/services/commands/task_steps/_step_transition_core.py` lines 84-95
  summary: The core enforces the same auto-pause rule.
- `edge:src-recalculate-readiness--implements-->concept-readiness-gating` evidence[0] — `app/beyo_manager/domain/task_steps/readiness.py` lines 7-19
  summary: The pure derivation of readiness from the two counters.
- `edge:helper-cascade-step-completion--implements-->concept-readiness-gating` evidence[0] — `app/beyo_manager/services/commands/task_steps/_cascade_completion.py` lines 10-45
  summary: Maintains the counters the readiness rule reads.
- `edge:command-mark-step-time-inaccurate--implements-->concept-inaccurate-time-flagging` evidence[0] — `app/beyo_manager/services/commands/task_steps/mark_step_time_inaccurate.py` lines 17-45
  summary: Applies the flag at record and step level.
- `edge:contract-step-transition-payload--implements-->concept-credited-user-vs-performer` evidence[0] — `app/beyo_manager/domain/execution/payloads/step_transition.py` lines 19-20
  summary: Carries performed_by_user_id and credited_user_id as separate fields.
- `edge:command-transition-step-state--governed_by-->decision-mirrored-transition-body` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 116-121
  summary: DRIFT NOTE requiring changes here to be evaluated for the core.
- `edge:helper-apply-step-transition--governed_by-->decision-mirrored-transition-body` evidence[0] — `app/beyo_manager/services/commands/task_steps/_step_transition_core.py` lines 3-11
  summary: The reciprocal DRIFT NOTE naming Option B.
- `edge:task-finalize-pending-step-completion--governed_by-->decision-mirrored-transition-body` evidence[0] — `app/beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py` lines 100-220
  summary: A third copy of the transition body with a known TODO gap and a missing credited_user_id.
- `edge:src-create-instant-task--governed_by-->decision-transactional-outbox` evidence[0] — `app/beyo_manager/services/infra/execution/task_factory.py` lines 10-50
  summary: Flushes without committing so the outbox row shares the caller's transaction.
- `edge:vocab-transition-reason-enum--governed_by-->decision-code-owned-transition-reasons` evidence[0] — `app/beyo_manager/domain/transitions/enums.py` lines 4-38
  summary: A code-owned enum separate from the workspace pause catalog.
- `edge:command-cancel-pending-step-completion--governed_by-->decision-undo-window-disabled` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 190-231
  summary: The scheduling block that would make this command reachable is commented out.
- `edge:table-step-state-record--governed_by-->decision-credited-user-no-fk` evidence[0] — `app/beyo_manager/models/tables/tasks/step_state_record.py` lines 84-91
  summary: credited_user_id deliberately declared without a foreign key.
- `edge:src-create-instant-task--writes_to-->table-execution-task` evidence[0] — `app/beyo_manager/services/infra/execution/task_factory.py` lines 10-45
  summary: Inserts an ExecutionTask row in state OPEN.
- `edge:src-create-instant-task--writes_to-->table-execution-payload` evidence[0] — `app/beyo_manager/services/infra/execution/task_factory.py` lines 10-45
  summary: Inserts the paired JSON payload row.
- `edge:event-process-step-transition--persists_in-->table-execution-payload` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 413-417
  summary: The StepTransitionPayload is serialized with asdict() into the execution payload.
- `edge:infra-pg-notify-task-open--depends_on-->table-execution-task` evidence[0] — `app/scripts/apply_db_triggers.py` lines 17-30
  summary: Trigger defined on the execution_tasks table.
- `edge:infra-task-router--depends_on-->infra-pg-notify-task-open` evidence[0] — `app/beyo_manager/services/infra/execution/task_router.py` lines 56-74
  summary: Holds a dedicated LISTEN task_open connection with a 30s fallback poll.
- `edge:infra-task-router--reads_from-->table-execution-task` evidence[0] — `app/beyo_manager/services/infra/execution/task_router.py` lines 113-135
  summary: Selects OPEN tasks, pushes ids to Redis and flips them to PENDING.
- `edge:infra-task-router--links_to-->infra-queue-analytics` evidence[0] — `app/beyo_manager/services/infra/execution/task_router.py` lines 34-34
  summary: QUEUE_MAP routes PROCESS_STEP_TRANSITION to queue:analytics.
- `edge:infra-task-router--links_to-->infra-queue-notifications` evidence[0] — `app/beyo_manager/services/infra/execution/task_router.py` lines 19-19
  summary: QUEUE_MAP routes CREATE_NOTIFICATIONS to queue:notifications.
- `edge:infra-task-router--links_to-->infra-queue-tasks` evidence[0] — `app/beyo_manager/services/infra/execution/task_router.py` lines 27-27
  summary: QUEUE_MAP routes DELAYED_STEP_COMPLETION to queue:tasks.
- `edge:infra-analytics-worker--depends_on-->infra-queue-analytics` evidence[0] — `app/beyo_manager/workers/analytics_worker.py` lines 15-20
  summary: Runs the worker loop against queue:analytics.
- `edge:infra-analytics-worker--depends_on-->infra-worker-base` evidence[0] — `app/beyo_manager/workers/analytics_worker.py` lines 15-20
  summary: Delegates to the shared run_worker loop.
- `edge:infra-analytics-worker--consumes-->event-process-step-transition` evidence[0] — `app/beyo_manager/workers/analytics_worker.py` lines 10-13
  summary: HANDLER_MAP binds PROCESS_STEP_TRANSITION to the analytics handler.
- `edge:infra-analytics-worker--calls-->analytics-process-step-transition` evidence[0] — `app/beyo_manager/workers/analytics_worker.py` lines 10-13
  summary: Maps the task type directly to handle_process_step_transition.
- `edge:infra-notification-worker--consumes-->event-create-notifications` evidence[0] — `app/beyo_manager/workers/notification_worker.py` lines 11-19
  summary: HANDLER_MAP binds CREATE_NOTIFICATIONS to handle_create_notifications.
- `edge:infra-tasks-worker--consumes-->event-delayed-step-completion` evidence[0] — `app/beyo_manager/workers/tasks_worker.py` lines 26-34
  summary: HANDLER_MAP binds DELAYED_STEP_COMPLETION to the finalizer.
- `edge:infra-tasks-worker--calls-->task-finalize-pending-step-completion` evidence[0] — `app/beyo_manager/workers/tasks_worker.py` lines 26-34
  summary: Maps the task type to handle_finalize_pending_step_completion.
- `edge:infra-delayed-scheduler-runner--produces-->event-delayed-step-completion` evidence[0] — `app/beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py` lines 26-80
  summary: Converts due PENDING_STEP_COMPLETION rows into execution tasks.
- `edge:infra-delayed-scheduler-runner--reads_from-->table-delayed-scheduler` evidence[0] — `app/beyo_manager/services/infra/schedulers/delayed_scheduler_runner.py` lines 30-80
  summary: Polls ACTIVE scheduler rows for due entries.
- `edge:infra-event-bus--consumes-->ws-task-step-state-changed` evidence[0] — `app/beyo_manager/services/infra/events/event_bus.py` lines 21-60
  summary: Dispatches each event to registered socket, audit and webhook handlers.
- `edge:command-transition-step-state--depends_on-->infra-event-bus` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 504-504
  summary: Calls event_bus.dispatch after the transaction block has closed.
- `edge:analytics-process-step-transition--consumes-->event-process-step-transition` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 37-40
  summary: Rehydrates the payload as the handler's first action.
- `edge:analytics-process-step-transition--depends_on-->contract-step-transition-payload` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 39-39
  summary: StepTransitionPayload(**raw) raises TypeError on any field mismatch.
- `edge:analytics-process-step-transition--implements-->concept-terminal-vs-time-bearing` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 65-94
  summary: Time work gated on closing_state in TIME_BEARING_STATES; completion counters gated separately on new_state == COMPLETED.
- `edge:analytics-process-step-transition--depends_on-->vocab-step-state-constants` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 12-12
  summary: Imports TIME_BEARING_STATES from the domain constants module.
- `edge:analytics-process-step-transition--calls-->analytics-recompute-step-time-totals` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 65-79
  summary: Invoked inside the time-bearing branch.
- `edge:analytics-process-step-transition--calls-->analytics-reconcile-user-day-time` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 65-79
  summary: Reconciles the credited user's day inside the time-bearing branch.
- `edge:analytics-process-step-transition--calls-->analytics-apply-reconcile-deltas` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 65-79
  summary: Applies the returned deltas to the sum tables.
- `edge:analytics-process-step-transition--calls-->analytics-apply-step-completed` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 91-94
  summary: Called only when new_state is COMPLETED.
- `edge:analytics-process-step-transition--calls-->analytics-apply-issues-at-completion` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 91-94
  summary: Called alongside completion counting under the same gate.
- `edge:analytics-process-step-transition--calls-->command-reconcile-worker-shift-state` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 80-88
  summary: Reconciles shift state on every transition with a credited user, independent of closing_state.
- `edge:analytics-process-step-transition--produces-->ws-worker-shift-state-changed` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 99-110
  summary: Emits the shift event only when the reconcile reports changed, with a comment explaining this is the only place that can announce it.
- `edge:analytics-process-step-transition--reads_from-->table-step-state-record` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 42-46
  summary: Fetches the closing record by id and warns/no-ops if absent.
- `edge:analytics-recompute-step-time-totals--writes_to-->table-task-step` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 138-211
  summary: SETs the step's time, count, inaccurate and cost columns absolutely.
- `edge:analytics-recompute-step-time-totals--calls-->src-compute-record-contributions` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 138-211
  summary: Re-runs the shared sweep over the step's window.
- `edge:analytics-recompute-step-time-totals--governed_by-->decision-recompute-not-increment` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 138-211
  summary: Absolute SET from recomputed contributions rather than incremental accrual.
- `edge:analytics-reconcile-user-day-time--calls-->src-compute-record-contributions` evidence[0] — `app/beyo_manager/services/queries/analytics/reconcile_user_time.py` lines 256-337
  summary: Uses the shared primitive over the day window.
- `edge:analytics-reconcile-user-day-time--writes_to-->table-user-daily-work-stats` evidence[0] — `app/beyo_manager/services/queries/analytics/reconcile_user_time.py` lines 256-337
  summary: SETs the user's daily row for the reconciled date.
- `edge:analytics-reconcile-user-day-time--writes_to-->table-user-section-daily-work-stats` evidence[0] — `app/beyo_manager/services/queries/analytics/reconcile_user_time.py` lines 256-337
  summary: SETs per-section rows and zeroes sections dropped from the day.
- `edge:analytics-reconcile-user-day-time--reads_from-->table-user-work-profile` evidence[0] — `app/beyo_manager/services/queries/analytics/reconcile_user_time.py` lines 256-337
  summary: Derives cost from salary_per_hour_before_tax.
- `edge:analytics-reconcile-user-day-time--governed_by-->decision-recompute-not-increment` evidence[0] — `app/beyo_manager/services/queries/analytics/reconcile_user_time.py` lines 256-345
  summary: SETs recomputable tables and returns deltas for the sums.
- `edge:analytics-apply-reconcile-deltas--writes_to-->table-user-lifetime-stats` evidence[0] — `app/beyo_manager/services/queries/analytics/reconcile_user_time.py` lines 338-350
  summary: Adds deltas onto the lifetime row.
- `edge:analytics-apply-reconcile-deltas--writes_to-->table-working-section-daily-work-stats` evidence[0] — `app/beyo_manager/services/queries/analytics/reconcile_user_time.py` lines 338-350
  summary: Adds deltas onto the section-daily row.
- `edge:analytics-apply-step-completed--writes_to-->table-user-daily-work-stats` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 291-330
  summary: Increments total_completed_count on the user's daily row.
- `edge:analytics-apply-step-completed--writes_to-->table-user-lifetime-stats` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 291-330
  summary: Increments the lifetime completion counter.
- `edge:analytics-apply-step-completed--writes_to-->table-user-section-daily-work-stats` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 291-330
  summary: Increments the per-section daily completion counter.
- `edge:analytics-apply-step-completed--writes_to-->table-working-section-daily-work-stats` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 291-330
  summary: Increments the section-wide daily completion counter.
- `edge:analytics-apply-step-completed--writes_to-->table-task-step` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 291-330
  summary: Also increments total_completed_count on the step row.
- `edge:analytics-apply-issues-at-completion--reads_from-->table-item-issue` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 245-290
  summary: Counts non-deleted issues for the completing step.
- `edge:src-compute-record-contributions--reads_from-->table-step-state-record` evidence[0] — `app/beyo_manager/services/queries/analytics/averaged_time.py` lines 69-140
  summary: Loads WORKING/PAUSED records overlapping the window joined to TaskStep.
- `edge:src-compute-record-contributions--calls-->domain-concurrency-sweep` evidence[0] — `app/beyo_manager/services/queries/analytics/averaged_time.py` lines 69-140
  summary: Runs both the trusted and wasted sweeps from the domain module.
- `edge:src-compute-record-contributions--implements-->concept-concurrency-averaged-time` evidence[0] — `app/beyo_manager/services/queries/analytics/averaged_time.py` lines 69-140
  summary: Joins allows_batch_working so non-batchable steps never enter the divisor.
- `edge:domain-concurrency-sweep--implements-->concept-concurrency-averaged-time` evidence[0] — `app/beyo_manager/domain/analytics/concurrency.py` lines 35-76
  summary: Divides each boundary segment equally among open intervals.
- `edge:src-bucket-for--implements-->concept-ended-shift-collapse` evidence[0] — `app/beyo_manager/domain/analytics/time_buckets.py` lines 20-34
  summary: Derives the ended_shift bucket from PAUSED plus the SHIFT_ENDED reason.
- `edge:command-reconcile-worker-shift-state--writes_to-->table-user-shift-state-record` evidence[0] — `app/beyo_manager/services/commands/users/reconcile_worker_shift_state.py` lines 270-330
  summary: Closes the current shift record and inserts a new one when the derived target differs.
- `edge:command-reconcile-worker-shift-state--reads_from-->table-step-state-record` evidence[0] — `app/beyo_manager/services/commands/users/reconcile_worker_shift_state.py` lines 270-330
  summary: Loads open WORKING/PAUSED step records since shift start to derive the target state.
- `edge:command-reconcile-worker-shift-state--depends_on-->domain-user-shift-state-machine` evidence[0] — `app/beyo_manager/services/commands/users/reconcile_worker_shift_state.py` lines 270-330
  summary: Calls derive_target_state from the shift state machine module.
- `edge:projection-list-workers-totals--reads_from-->table-user-daily-work-stats` evidence[0] — `app/beyo_manager/services/queries/worker_stats/list_workers_totals.py` lines 39-80
  summary: Aggregates the daily rollup rows for the dashboard.
- `edge:projection-worker-daily-step-breakdown--reads_from-->table-step-state-record` evidence[0] — `app/beyo_manager/services/queries/worker_stats/get_worker_daily_step_breakdown.py` lines 83-130
  summary: Reads raw interval records alongside the rollups.
- `edge:projection-worker-linear-timeline-breakdown--calls-->domain-linear-timeline` evidence[0] — `app/beyo_manager/services/queries/worker_stats/get_worker_linear_timeline_breakdown.py` lines 325-380
  summary: Applies the timeline collapse to the loaded records.
- `edge:projection-list-workers-insights--calls-->domain-analytics-insights-engine` evidence[0] — `app/beyo_manager/services/queries/analytics/compute_worker_insights.py` lines 25-60
  summary: Delegates to the pure evaluate() after a bounded read.
- `edge:script-backfill-averaged-time--calls-->analytics-reconcile-user-day-time` evidence[0] — `app/scripts/backfill/backfill_averaged_time.py` lines 59-180
  summary: Re-runs the same reconciler per user and day.
- `edge:script-backfill-completed-count--writes_to-->table-user-daily-work-stats` evidence[0] — `app/scripts/backfill/backfill_completed_count.py` lines 132-160
  summary: Writes absolute recounted completion values.
- `edge:script-backfill-completed-count--implements-->concept-credited-user-vs-performer` evidence[0] — `app/scripts/backfill/backfill_completed_count.py` lines 71-130
  summary: Recounts using COALESCE(credited_user_id, created_by_id), duplicating the worker's attribution rule.
- `edge:table-task--owns-->table-task-step` evidence[0] — `app/beyo_manager/models/tables/tasks/task_step.py` lines 35-60
  summary: task_steps.task_id foreign key to tasks.
- `edge:table-task-step--owns-->table-step-state-record` evidence[0] — `app/beyo_manager/models/tables/tasks/step_state_record.py` lines 29-60
  summary: step_state_records.step_id foreign key to task_steps; the reverse latest_state_record_id pointer uses use_alter to break the cycle.
- `edge:table-execution-task--owns-->table-execution-payload` evidence[0] — `app/beyo_manager/models/tables/execution/execution_payload.py` lines 16-39
  summary: Unique foreign key execution_task_id enforcing a 1:1 relation.
- `edge:table-step-state-record--depends_on-->table-pause-reason` evidence[0] — `app/beyo_manager/models/tables/tasks/step_state_record.py` lines 60-80
  summary: pause_reason_id foreign key to the workspace catalog, mutually exclusive with transition_reason.
- `edge:domain-task-execution--contains-->concept-step-state-machine` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 54-70
  summary: The transition legality map.
- `edge:domain-task-execution--contains-->concept-readiness-gating` evidence[0] — `app/beyo_manager/domain/task_steps/readiness.py` lines 7-19
  summary: Readiness derivation.
- `edge:domain-task-execution--contains-->concept-one-active-step-per-user` evidence[0] — `app/beyo_manager/services/commands/task_steps/_user_working_record.py` lines 11-40
  summary: The conflict lookup behind the invariant.
- `edge:domain-task-execution--contains-->table-task-step` evidence[0] — `app/beyo_manager/models/tables/tasks/task_step.py` lines 35-60
  summary: The step table.
- `edge:domain-work-analytics--contains-->concept-concurrency-averaged-time` evidence[0] — `app/beyo_manager/domain/analytics/concurrency.py` lines 35-76
  summary: The averaging sweep.
- `edge:domain-work-analytics--contains-->analytics-process-step-transition` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 37-110
  summary: The analytics worker handler.
- `edge:domain-work-analytics--contains-->table-user-daily-work-stats` evidence[0] — `app/beyo_manager/models/tables/analytics/user_daily_work_stats.py` lines 17-50
  summary: The primary daily rollup.
- `edge:domain-work-analytics--contains-->concept-terminal-vs-time-bearing` evidence[0] — `app/beyo_manager/domain/task_steps/constants.py` lines 11-14
  summary: TIME_BEARING_STATES gates all duration accounting.
- `edge:concept-attribution-split--links_to-->concept-credited-user-vs-performer` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 165-172
  summary: The COALESCE fallback is where the performer/credited distinction actually resolves.
- `edge:command-transition-step-state--implements-->concept-attribution-split` evidence[0] — `app/beyo_manager/services/commands/task_steps/transition_step_state.py` lines 336-345
  summary: Opens records without credited_user_id while sending it in the payload.
- `edge:analytics-process-step-transition--implements-->concept-attribution-split` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 65-172
  summary: Consumes payload credit for day/completion work and record credit for the time sweep.
- `edge:domain-work-analytics--contains-->concept-attribution-split` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 65-172
  summary: Attribution determines which worker every rollup lands on.
- `edge:script-backfill-completed-count--links_to-->concept-attribution-split` evidence[0] — `app/scripts/backfill/backfill_completed_count.py` lines 71-130
  summary: Recounts completions from records using COALESCE(credited_user_id, created_by_id) — the RECORD-side rule, not the payload-side rule the live worker uses for completions.
- `edge:analytics-process-step-transition--calls-->analytics-reconcile-user-day-completions` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 104-107
  summary: Called in the COMPLETED branch, gated on payload.credited_user_id.
- `edge:analytics-process-step-transition--calls-->analytics-apply-completion-reconcile-deltas` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 108-111
  summary: Applies the returned completion deltas to the Σ tables.
- `edge:analytics-process-step-transition--calls-->analytics-recompute-step-completion-totals` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 115-117
  summary: Refreshes the step's own completion counters after the day reconcile.
- `edge:domain-work-analytics--contains-->decision-idempotent-completion-counters` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 88-117
  summary: The decision governs how the analytics tier books completions.
- `edge:analytics-process-step-transition--implements-->rule-issue-counting-ignores-marked-wrong` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_step_transition.py` lines 88-117
  summary: The completion branch gates on state and credited user, never on recorded_time_marked_wrong.
- `edge:rule-issue-counting-ignores-marked-wrong--links_to-->concept-inaccurate-time-flagging` evidence[0] — `app/beyo_manager/domain/analytics/concurrency.py` lines 86-105
  summary: The flag routes duration into a separate wasted sweep.
- `edge:table-production-cost-group--owns-->table-production-cost-basis-version` evidence[0] — `app/beyo_manager/models/tables/item_economics/production_cost_basis_version.py` lines 18-42
  summary: The child model's foreign key carries the parent reference.
- `edge:table-production-cost-group--owns-->table-production-cost-group-section` evidence[0] — `app/beyo_manager/models/tables/item_economics/production_cost_group_section.py` lines 14-22
  summary: The child model's foreign key carries the parent reference.
- `edge:table-cost-model-version--owns-->table-cost-model-term` evidence[0] — `app/beyo_manager/models/tables/item_economics/cost_model_term.py` lines 18-37
  summary: The child model's foreign key carries the parent reference.
- `edge:table-item-cost-evaluation--owns-->table-item-cost-evaluation-term` evidence[0] — `app/beyo_manager/models/tables/item_economics/item_cost_evaluation_term.py` lines 18-25
  summary: The child model's foreign key carries the parent reference.
- `edge:table-task--owns-->table-item-cost-evaluation` evidence[0] — `app/beyo_manager/models/tables/item_economics/item_cost_evaluation.py` lines 20-55
  summary: The child model's foreign key carries the parent reference.
- `edge:table-task--owns-->table-item-cost-result` evidence[0] — `app/beyo_manager/models/tables/item_economics/item_cost_result.py` lines 18-35
  summary: The child model's foreign key carries the parent reference.
- `edge:domain-item-economics--configured_by-->endpoint-item-economics-status` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 209-214
  summary: The item-economics domain has a registered configuration-status endpoint.
- `edge:endpoint-item-economics-post-cost-groups--accepts-->command-item-economics-create-production-cost-group` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 98-98
  summary: The route delegates to the registered configuration command.
- `edge:endpoint-item-economics-patch-cost-group--accepts-->command-item-economics-update-production-cost-group` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 118-118
  summary: The route delegates to the registered configuration command.
- `edge:endpoint-item-economics-delete-cost-group--accepts-->command-item-economics-delete-production-cost-group` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 127-127
  summary: The route delegates to the registered configuration command.
- `edge:endpoint-item-economics-post-section--accepts-->command-item-economics-add-section-to-cost-group` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 137-137
  summary: The route delegates to the registered configuration command.
- `edge:endpoint-item-economics-delete-section--accepts-->command-item-economics-remove-section-from-cost-group` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 147-147
  summary: The route delegates to the registered configuration command.
- `edge:endpoint-item-economics-post-basis--accepts-->command-item-economics-create-production-cost-basis-version` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 157-158
  summary: The route delegates to the registered configuration command.
- `edge:endpoint-item-economics-delete-basis--accepts-->command-item-economics-delete-production-cost-basis-version` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 178-178
  summary: The route delegates to the registered configuration command.
- `edge:endpoint-item-economics-post-model--accepts-->command-item-economics-create-cost-model-version` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 187-187
  summary: The route delegates to the registered configuration command.
- `edge:endpoint-item-economics-delete-model--accepts-->command-item-economics-delete-cost-model-version` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 206-206
  summary: The route delegates to the registered configuration command.
- `edge:command-item-economics-create-production-cost-group--writes_to-->table-production-cost-group` evidence[0] — `app/beyo_manager/services/commands/item_economics/create_production_cost_group.py` lines 30-32
  summary: The command mutates the corresponding configuration ORM table.
- `edge:command-item-economics-update-production-cost-group--writes_to-->table-production-cost-group` evidence[0] — `app/beyo_manager/services/commands/item_economics/update_production_cost_group.py` lines 27-30
  summary: The command mutates the corresponding configuration ORM table.
- `edge:command-item-economics-delete-production-cost-group--writes_to-->table-production-cost-group` evidence[0] — `app/beyo_manager/services/commands/item_economics/delete_production_cost_group.py` lines 36-39
  summary: The command mutates the corresponding configuration ORM table.
- `edge:command-item-economics-add-section-to-cost-group--writes_to-->table-production-cost-group-section` evidence[0] — `app/beyo_manager/services/commands/item_economics/add_section_to_cost_group.py` lines 43-45
  summary: The command mutates the corresponding configuration ORM table.
- `edge:command-item-economics-remove-section-from-cost-group--writes_to-->table-production-cost-group-section` evidence[0] — `app/beyo_manager/services/commands/item_economics/remove_section_from_cost_group.py` lines 28-30
  summary: The command mutates the corresponding configuration ORM table.
- `edge:command-item-economics-create-production-cost-basis-version--writes_to-->table-production-cost-basis-version` evidence[0] — `app/beyo_manager/services/commands/item_economics/create_production_cost_basis_version.py` lines 33-47
  summary: The command mutates the corresponding configuration ORM table.
- `edge:command-item-economics-delete-production-cost-basis-version--writes_to-->table-production-cost-basis-version` evidence[0] — `app/beyo_manager/services/commands/item_economics/delete_production_cost_basis_version.py` lines 32-35
  summary: The command mutates the corresponding configuration ORM table.
- `edge:command-item-economics-create-cost-model-version--writes_to-->table-cost-model-version` evidence[0] — `app/beyo_manager/services/commands/item_economics/create_cost_model_version.py` lines 53-55
  summary: The command mutates the corresponding configuration ORM table.
- `edge:command-item-economics-delete-cost-model-version--writes_to-->table-cost-model-version` evidence[0] — `app/beyo_manager/services/commands/item_economics/delete_cost_model_version.py` lines 31-34
  summary: The command mutates the corresponding configuration ORM table.
- `edge:endpoint-item-economics-get-cost-groups--reads_from-->table-production-cost-group` evidence[0] — `app/beyo_manager/services/queries/item_economics/list_production_cost_groups.py` lines 15-23
  summary: The query endpoint loads the workspace-scoped configuration rows.
- `edge:endpoint-item-economics-get-basis--reads_from-->table-production-cost-basis-version` evidence[0] — `app/beyo_manager/services/queries/item_economics/list_production_cost_basis_versions.py` lines 15-27
  summary: The query endpoint loads the workspace-scoped configuration rows.
- `edge:endpoint-item-economics-get-model--reads_from-->table-cost-model-version` evidence[0] — `app/beyo_manager/services/queries/item_economics/list_cost_model_versions.py` lines 16-28
  summary: The query endpoint loads the workspace-scoped configuration rows.
- `edge:endpoint-item-economics-status--reads_from-->table-production-cost-group` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_economics_configuration_status.py` lines 12-19
  summary: The query endpoint loads the workspace-scoped configuration rows.
- `edge:endpoint-item-economics-status--reads_from-->table-production-cost-basis-version` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_economics_configuration_status.py` lines 20-27
  summary: The query endpoint loads the workspace-scoped configuration rows.
- `edge:endpoint-item-economics-status--reads_from-->table-cost-model-version` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_economics_configuration_status.py` lines 28-35
  summary: The query endpoint loads the workspace-scoped configuration rows.
- `edge:command-item-economics-create-cost-model-version--writes_to-->table-cost-model-term` evidence[0] — `app/beyo_manager/services/commands/item_economics/create_cost_model_version.py` lines 68-69
  summary: ctx.session.add_all(terms) followed by await ctx.session.flush() inserts the CostModelTerm rows built for the new version.
- `edge:endpoint-item-economics-get-model--reads_from-->table-cost-model-term` evidence[0] — `app/beyo_manager/services/queries/item_economics/list_cost_model_versions.py` lines 32-32
  summary: select(CostModelTerm) in the query module backing GET /cost-model-versions.
- `edge:command-item-economics-delete-item-valuation--writes_to-->table-item-valuation` evidence[0] — `app/beyo_manager/services/commands/item_economics/delete_item_valuation.py` lines 39-42
  summary: The command updates is_deleted and deletion metadata on item_valuations.
- `edge:endpoint-item-economics-get-valuations--reads_from-->table-item-valuation` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_item_valuation_history.py` lines 23-31
  summary: The history query selects workspace-scoped non-deleted ItemValuation rows and orders them by created_at and client_id descending.
- `edge:command-item-economics-set-item-valuation--reads_from-->table-production-cost-group` evidence[0] — `app/beyo_manager/services/commands/item_economics/set_item_valuation.py` lines 39-44
  summary: select(ProductionCostGroup) scoped to the workspace in _load_preview_inputs.
- `edge:command-item-economics-set-item-valuation--reads_from-->table-production-cost-basis-version` evidence[0] — `app/beyo_manager/services/commands/item_economics/set_item_valuation.py` lines 47-52
  summary: select(ProductionCostBasisVersion) in _load_preview_inputs.
- `edge:command-item-economics-set-item-valuation--reads_from-->table-cost-model-version` evidence[0] — `app/beyo_manager/services/commands/item_economics/set_item_valuation.py` lines 55-60
  summary: select(CostModelVersion) in _load_preview_inputs.
- `edge:command-item-economics-set-item-valuation--reads_from-->table-cost-model-term` evidence[0] — `app/beyo_manager/services/commands/item_economics/set_item_valuation.py` lines 72-78
  summary: select(CostModelTerm) for the selected model version in _load_preview_inputs.
- `edge:command-item-economics-set-item-valuation--reads_from-->table-item` evidence[0] — `app/beyo_manager/services/commands/item_economics/set_item_valuation.py` lines 55-65
  summary: select(Item) by workspace + item client_id resolves the item the valuation attaches to.
- `edge:endpoint-item-economics-task-budget-status--accepts-->projection-item-economics-task-budget-status` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 344-383
  summary: The budget-status endpoint delegates to the task budget query and serializer.
- `edge:endpoint-item-economics-lifetime--accepts-->projection-item-economics-lifetime` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 386-400
  summary: The lifetime endpoint delegates to the item lifetime query.
- `edge:projection-item-economics-task-budget-status--reads_from-->table-task` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py` lines 41-58
  summary: The query loads the task and its primary item binding.
- `edge:projection-item-economics-task-budget-status--reads_from-->table-item-cost-evaluation` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py` lines 101-113
  summary: The query filters the current committed evaluation for the task.
- `edge:projection-item-economics-task-budget-status--reads_from-->table-task-step` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py` lines 130-150
  summary: The query sums non-deleted task-step total_working_seconds for the task.
- `edge:projection-item-economics-task-budget-status--reads_from-->table-item-cost-result` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py` lines 157-166
  summary: The query loads the durable result row for the task.
- `edge:projection-item-economics-lifetime--reads_from-->table-item-cost-evaluation` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_item_lifetime_economics.py` lines 36-56
  summary: The query lists current committed evaluations scoped to the item.
- `edge:projection-item-economics-lifetime--reads_from-->table-item-cost-result` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_item_lifetime_economics.py` lines 59-67
  summary: The query attaches result rows by task and totals only attached results.
- `edge:domain-item-economics--contains-->projection-item-economics-task-budget-status` evidence[0] — `app/beyo_manager/domain/item_economics/serializers.py` lines 229-268
  summary: The item-economics serialization module defines manager and worker budget-status representations.
- `edge:domain-item-economics--contains-->projection-item-economics-lifetime` evidence[0] — `app/beyo_manager/domain/item_economics/serializers.py` lines 269-285
  summary: The item-economics serializer family defines the lifetime projection envelope.
- `edge:command-process-item-cost-result--consumes-->event-process-item-cost-result` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_item_cost_result.py` lines 39-43
  summary: The handler rehydrates ItemCostResultPayload from the task payload.
- `edge:command-process-item-cost-result--writes_to-->table-item-cost-result` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_item_cost_result.py` lines 105-137
  summary: The handler upserts the durable item_cost_results row using the task unique constraint.
- `edge:command-process-item-cost-result--reads_from-->table-item-cost-evaluation` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_item_cost_result.py` lines 55-70
  summary: The handler resolves the current committed evaluation for the task.
- `edge:command-process-item-cost-result--reads_from-->table-task-step` evidence[0] — `app/beyo_manager/services/tasks/analytics/process_item_cost_result.py` lines 72-82
  summary: The handler sums non-deleted task-step working seconds at execution time.
- `edge:infra-analytics-worker--calls-->command-process-item-cost-result` evidence[0] — `app/beyo_manager/workers/analytics_worker.py` lines 10-14
  summary: The analytics worker maps PROCESS_ITEM_COST_RESULT to the result handler.
- `edge:endpoint-item-economics-task-budget-status--accepts-->projection-item-economics-task-budget-status-worker` evidence[0] — `app/beyo_manager/routers/api_v1/item_economics.py` lines 344-383
  summary: route_get_task_budget_status computes worker_view = not include_monetary_step_fields(role_name) at :134-region of the handler body and dispatches get_task_budget_status_worker for worker_view.
- `edge:projection-item-economics-task-budget-status-worker--reads_from-->table-item-cost-evaluation` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_task_budget_status_worker.py` lines 27-40
  summary: select(ItemCostEvaluation) filtered kind=COMMITTED, superseded_at IS NULL, is_deleted=false, task-scoped.
- `edge:domain-item-economics--contains-->projection-item-economics-task-budget-allocations` evidence[0] — `app/beyo_manager/services/queries/item_economics/get_task_budget_allocations.py` lines 100-283
  summary: The new batched allocation read model is implemented beside the existing item-economics query projections.
- `edge:domain-item-economics--contains-->projection-working-section-typical-times` evidence[0] — `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py` lines 21-83
  summary: The typical-time query is a read-only projection used by item-economics allocation and exposed independently.
- `edge:domain-item-economics--contains-->source-file-item-economics-price-scenario` evidence[0] — `app/beyo_manager/domain/item_economics/price_scenario.py` lines 1-11
  summary: The module sits in beyo_manager/domain/item_economics/ beside budget_division.py and calculator.py, and imports only that package's enums plus the shared validation error.
- `edge:infrastructure-test-database-isolation--configured_by-->configuration-shipped-pytest-parallel-default` evidence[0] — `app/pytest.ini` lines 1-2
  summary: The default runner invokes xdist with six workers and loadfile distribution.
- `edge:domain-item-economics--contains-->domain-item-economics-typical-filters` evidence[0] — `app/beyo_manager/domain/item_economics/typical_filters.py` lines 1-333
  summary: The pure typical-time rules are implemented inside the item-economics domain package.
