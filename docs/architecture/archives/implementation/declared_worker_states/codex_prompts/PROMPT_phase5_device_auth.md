# Codex prompt — Declared Worker States, Phase 5: floor device auth (non-expiring token)

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`. Process this work as: implement → validate → review-log entry → STOP for independent review. Summary/archive happen ONLY after the reviewer approves (see Definition of done).
2. Read the master plan first: `backend/docs/architecture/under_construction/implementation/declared_worker_states/MASTER_PLAN_declared_worker_states_20260729.md`. Decision D11 is the spine of this phase.
3. Your implementation plan is: `backend/docs/architecture/under_construction/implementation/declared_worker_states/PLAN_declared_worker_states_phase5_device_auth_20260729.md`. Read it fully before touching code.
4. Prerequisite check: NONE — this phase is independent of Phases 1–4 and may run at any point, **including in parallel with another phase** (operator-sanctioned; file sets are disjoint). Parallel-run discipline: stage and edit ONLY auth-surface files and your own phase plan's Review log — never the master plan, the handoff, or any worker-shifts file.
5. Clarification-first: ambiguity the plan does not resolve → STOP and ask. Do not invent requirements.
6. Respect the plan's "File read intent". Two verify-first items are mandatory before coding: (a) PyJWT accepts tokens without `exp` (pin with a unit test), (b) how the logout blocklist TTL is currently derived.

## Hard constraints for this phase

- Existing scopes (`manager`, `worker`, `seller`, `admin`) must remain byte-identical: same TTLs, same refresh cookies, same logout semantics. Regression tests are part of the deliverable.
- Floor tokens: no `exp` claim, `jti` retained, NO refresh token and NO refresh cookie.
- Logout of an `exp`-less token writes a blocklist entry with NO TTL (assert `TTL == -1` in the test).
- Credential errors stay opaque ("Invalid credentials.") — do not leak whether the scope or the role failed.
- Response shapes must match `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` §2 — the frontend builds against it in parallel. Conflicts → STOP and ask.

## Definition of done

- Every acceptance criterion verified with evidence (test output; decoded-token dump showing no `exp`; Redis TTL assertion).
- Full validation plan green; `ruff check` clean.
- Plan's Review log updated with your implementer entry. Then STOP: the phase now goes to an INDEPENDENT reviewer. Do NOT write the implemented summary, do NOT archive the plan, do NOT flip the master phase table, and do NOT edit the frontend handoff's liveness table — those steps happen ONLY after the reviewer returns APPROVED (this review-first gate overrides the lifecycle skill's implement->summary->archive sequence; three premature archives have already been unwound in this feature set). Report completion to the operator and wait.
