# Opus prompt — Phase 4 POST-APPROVAL POLISH (R8 + R10)

Phase 4 was **APPROVED** by the independent reviewer at round 2 (implementation `20b11c7`, fixes
`ccdffa9`). R4–R6 are closed. This is a small polish pass for the two low findings the reviewer
raised that require code; the phase archives immediately after. Findings are in the Review log of
`.../declared_worker_states/PLAN_declared_worker_states_phase4_clock_surface_20260729.md`.

**Parallel-run discipline:** Phase 5's round-2 fix cycle is active in this tree. Touch ONLY the
worker-shift access/query/serializer files and your own plan. Stage explicitly — never `git add -A`.

## R8 — relocate the shared access helper (contract placement)

`app/beyo_manager/services/worker_shift_access.py` sits at the top level of `services/`, which is
reserved for service-framework primitives (`context.py`, `outcome.py`, `run_service.py`,
`work_context.py`). **Move it to `app/beyo_manager/services/queries/users/worker_shift_access.py`.**

Reviewer-verified rationale (do not substitute another destination):
- `services/infra/` is NOT valid — `architecture/01_architecture.md:43` forbids `services/queries/`
  from importing `services/infra/` at all, and `get_current_worker_shift_state` is a query.
- `services/queries/users/` is contract-clean and has precedent: `_clock_worker_shift.py` already
  imports `services/queries/pause_reasons/get_system_pause_reason`.

Keep the existing `services/commands/users/_worker_shift_access.py` shim re-exporting the symbol so
all five writer call sites stay untouched. The function body must remain byte-identical (the
reviewer proved the current file is blob-identical to its pre-image; keep that property).
**Gate:** no behavior change; all worker-shift/current-state suites green; ruff clean.

## R10 — log the unresolvable-reason branch (observability)

The R5 fix nulls out an unresolvable `par_…` reason so it never reaches the client — correct, but
currently **silent**. A dangling or cross-tenant reason reference is a data-integrity signal, and
nulling it makes it invisible to operators too. (The reviewer noted R5 actually closed a real
cross-tenant identifier leak: the reason join is workspace-scoped, so a foreign-workspace `par_…`
was previously shipped to the client.)

Add a **WARNING** log at that branch — `architecture/17_logging.md:23` classes this shape
(non-fatal integrity/validation issue) as WARNING, and the sibling write path already logs its
analogous clamp. Include enough to act on: workspace_id, user_id, the shift record id, and the
unresolved reason id. Follow the repo's structured-log style used elsewhere in this feature
(`worker_shift.*` event names).
**Gate:** a test asserting the warning fires on the unresolvable-id path (and does NOT fire on the
legacy free-text path or the normal resolved path).

## Not in scope

- R9 (handoff `reason_text` three-way variance) — already done by the operator; do not edit the handoff.
- R1/R7 — closed/retired by the reviewer.

## Protocol

1. Fix on top of HEAD. Tests first for R10.
2. Re-run the worker-shift/current-state/router suites plus a QUIET-tree full suite (canonical
   baseline: 27 failed / 1275 passed at `ccdffa9` — see the master plan's baseline note); ruff on
   touched files.
3. Append a polish entry to the plan's Review log (per finding: change + gate evidence).
4. Do NOT archive/summarize/flip anything — the operator finalizes Phase 4 immediately after this.
5. One commit referencing R8/R10, staging only your own files.
