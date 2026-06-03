# HANDOFF_TO_FRONTEND_step_dependency_working_sections_contract_20260602

## Metadata

- Handoff ID: HANDOFF_TO_FRONTEND_step_dependency_working_sections_contract_20260602
- Created at (UTC): 2026-06-02T14:22:56Z
- Owner agent: copilot
- Source plan: backend/docs/architecture/archives/implementation/PLAN_step_dependency_working_sections_20260602.md
- Source summary: backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_step_dependency_working_sections_20260602.md

## Backend delivery context

- What backend implemented:
  - Extended working-section step listing with per-dependency working-section entries for each step.
  - Added prerequisite step current state per dependency entry.
  - Kept existing aggregate dependency counters unchanged (total_dependencies, completed_dependencies).
  - Implemented with one batch dependency query for the page (no per-step query loop).
- API or contract changes:
  - Additive response change: each step item now includes dependency_working_sections.
- Feature flags/toggles:
  - None.

## Frontend action required

1. Read and render dependency_working_sections on each step item.
2. Treat dependency_working_sections as an array that may be empty.
3. Render one row/chip per dependency entry (do not deduplicate by working section).
4. Use prerequisite_step_state to decide visual state (for example: pending/working/completed/failed).
5. Keep existing usage of total_dependencies and completed_dependencies for summary indicators.

## Interface details

- Endpoint: GET /api/v1/working-sections/{working_section_id}/steps
- Roles allowed: ADMIN, MANAGER, WORKER

### Request shape

No request payload changes.

Supported query params remain unchanged:
- q
- upholstery_search
- limit
- offset
- record_step_state

### Response shape delta (additive)

New field added inside each item in steps_pagination.items:

- dependency_working_sections: array of dependency entries

Dependency entry shape:

{
  "working_section": {
    "client_id": "wsec_...",
    "name": "Upholstery",
    "image": "https://... or null",
    "order_list": 2
  },
  "prerequisite_step_state": "pending"
}

Example item excerpt:

{
  "steps_pagination": {
    "items": [
      {
        "client_id": "stp_...",
        "state": "working",
        "total_dependencies": 3,
        "completed_dependencies": 1,
        "dependency_working_sections": [
          {
            "working_section": {
              "client_id": "wsec_cutting",
              "name": "Cutting",
              "image": null,
              "order_list": 1
            },
            "prerequisite_step_state": "completed"
          },
          {
            "working_section": {
              "client_id": "wsec_upholstery",
              "name": "Upholstery",
              "image": "https://cdn/.../uph.png",
              "order_list": 2
            },
            "prerequisite_step_state": "working"
          },
          {
            "working_section": {
              "client_id": "wsec_upholstery",
              "name": "Upholstery",
              "image": "https://cdn/.../uph.png",
              "order_list": 2
            },
            "prerequisite_step_state": "pending"
          }
        ]
      }
    ],
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}

### Behavioral notes

- Removed dependency edges are excluded.
- Dependencies pointing to deleted prerequisite steps are excluded.
- Dependencies pointing to deleted working sections are excluded.
- All prerequisite states are returned (no state filter), including terminal states.
- Two prerequisites in the same working section appear as two separate entries.
- Entry ordering is stable by working_section.order_list ASC NULLS LAST, then working_section.client_id ASC.

### Error cases

No new error cases introduced.

Existing behavior remains:
- 404 when working_section_id is not found in workspace.

## Validation notes

- Backend validation run:
  - Query file compile check: no errors after import fix.
  - npm run typecheck passed in frontend/apps/managers-app/ManagerBeyo-app-managers.
- Suggested frontend validation:
  - Step with zero dependencies returns dependency_working_sections as [].
  - Step with multiple dependencies returns one entry per dependency edge.
  - Two dependencies from same working section remain separate entries.
  - prerequisite_step_state values drive expected UI badges/icons.

## Trace links

- Parent plan: backend/docs/architecture/archives/implementation/PLAN_step_dependency_working_sections_20260602.md
- Parent summary: backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_step_dependency_working_sections_20260602.md
- Related archive record: backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_step_dependency_working_sections_20260602_1422.md
