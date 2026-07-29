# Declared Worker States — implementation package

In-app clock in/out (replacing Connecteam as the interface) + worker-declared states backed by the
`pause_reasons` catalog, so the daily timeline has no unexplained idle time.

Read `MASTER_PLAN_declared_worker_states_20260729.md` first — it holds the goal, the binding
cross-phase decisions (D1–D10), and the phase status table.

## Contents

| File | Purpose |
|---|---|
| `MASTER_PLAN_declared_worker_states_20260729.md` | Goal, decisions, phase orchestration + status table |
| `PLAN_..._phase1_model_20260729.md` | `user_declared_state_records` table (inert) |
| `PLAN_..._phase2_derivation_20260729.md` | State machine + reconcile + clock-out rebuild read the table |
| `PLAN_..._phase3_commands_20260729.md` | Declare/close commands + routes; retire `/pause`+`/resume` |
| `PLAN_..._phase4_clock_surface_20260729.md` | `/clock-in`, `/clock-out`, `GET /current`, handoff conformance |
| `PLAN_..._phase5_device_auth_20260729.md` | `floor` app scope + non-expiring device token + revocation |
| `PLAN_..._phase6_kiosk_flow_20260729.md` | `clock_in_code`, floor-scoped roster exposure, clock-out `analytics: null` envelope |
| `PLAN_..._phase7_clockout_analytics_20260729.md` | Populated clock-out `analytics`: day timeline + segments + insights |
| `codex_prompts/PROMPT_phase<N>_*.md` | Paste to Codex to implement phase N |
| `review_prompts/REVIEW_phase<N>_*.md` | Paste to the review agent after Codex reports phase N done |

The frontend for the shop-floor app is built **in parallel** against
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_worker_shift_floor_app_20260729.md` — that handoff is
the authoritative API contract; every phase implements to match it.

## Operating loop (per phase, order 1 → 4 strict; phase 5 may run any time; phase 6 last)

1. Give Codex `codex_prompts/PROMPT_phase<N>_*.md`.
2. When Codex reports done, give the review agent `review_prompts/REVIEW_phase<N>_*.md`.
3. `NEEDS_CHANGES` → hand the findings back to Codex (they are also in the phase plan's Review log); repeat step 2.
4. `APPROVED` → Codex finalizes lifecycle (summary, archive preserving this subfolder, master table update). Start phase N+1.
