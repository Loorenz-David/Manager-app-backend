# Codex prompt — Declared Worker States, Phase 4: in-app clock surface + current-state endpoint + handoff

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`. Process this work as a full plan lifecycle: implement → validate → review-log entry → implemented summary → archive.
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
- The handoff `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` already exists (written ahead of implementation; the frontend builds against it). Your job is CONFORMANCE: implement to match it field-for-field and mark Phases 1–4's endpoints live in its status line. If you believe the handoff shape is wrong, STOP and ask — never deviate silently.

## Definition of done

- Every acceptance criterion in the plan is verified with evidence (test output).
- Full validation plan executed and green; `ruff check` clean.
- Handoff conformance verified; its status line updated (Phases 1–4 live).
- Plan's Review log updated; plan archived per the master plan's archiving note (preserve subfolder); implemented summary written; master plan phase table updated. (Phases 5–6 remain — do NOT archive the master plan or the folder.)
