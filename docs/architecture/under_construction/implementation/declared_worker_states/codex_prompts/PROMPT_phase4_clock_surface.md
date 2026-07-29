# Codex prompt — Declared Worker States, Phase 4: in-app clock surface + current-state endpoint + handoff

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`. Process this work as: implement → validate → review-log entry → STOP for independent review. Summary/archive happen ONLY after the reviewer approves (see Definition of done).
2. Read the master plan first: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`. Decisions D8 and D10 are the spine of this phase.
3. Your implementation plan is: `backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase4_clock_surface_20260729.md`. Read it fully before touching code.
4. Prerequisite check: the master plan's phase table must show **Phases 1–3 archived**. If not, STOP and report.
5. Clarification-first: if you hit ambiguity the plan does not resolve, STOP and ask the operator. Do not invent requirements.
6. Respect the plan's "File read intent" section. One verify-first item: check whether `list_pause_reasons` already supports a `pause_type` filter before adding one.

## Hard constraints for this phase

- Wire the EXISTING commands `clock_in_worker_shift` / `clock_out_worker_shift` — do not rewrite them. `clock_out_at` must NOT be exposed over HTTP (internal parameter for the midnight safeguard only).
- `POST /clock` (toggle) stays and must keep working unchanged.
- Connecteam handlers, webhook pipeline, and the midnight safeguard are UNTOUCHED (D8).
- `GET /current` is read-only — no `FOR UPDATE`. Access matrix mirrors the clock actions (worker = self only; admin/manager must name a worker). Legacy free-text `reason` values must serialize gracefully (`pause_reason: null` + `reason_text`), never error.
- Reasons-listing change, if needed, is additive-only (existing response contract unchanged).
- The handoff `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` already exists (written ahead of implementation; the frontend builds against it). Your job is CONFORMANCE: implement to match it field-for-field. The handoff is operator-owned — you do not edit it; its liveness table is flipped by the operator after review approval. If you believe the handoff shape is wrong, STOP and ask — never deviate silently.

## Definition of done

- Every acceptance criterion in the plan is verified with evidence (test output).
- Full validation plan executed and green; `ruff check` clean.
- Handoff conformance verified (evidence in the Review log; liveness flip is the operator's post-approval step).
- Plan's Review log updated with your implementer entry. Then STOP: the phase now goes to an INDEPENDENT reviewer. Do NOT write the implemented summary, do NOT archive the plan, do NOT flip the master phase table, and do NOT edit the frontend handoff's liveness table — those steps happen ONLY after the reviewer returns APPROVED (this review-first gate overrides the lifecycle skill's implement->summary->archive sequence; three premature archives have already been unwound in this feature set). Report completion to the operator and wait.
