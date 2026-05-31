# HANDOFF_TO_FRONTEND_working_section_steps_enhancements_20260529

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_working_section_steps_enhancements_20260529`
- Created at (UTC): `2026-05-29T00:00:00Z`
- Owner agent: `claude-sonnet-4-6`
- Source plan: `—`
- Source summary: `—`

## Backend delivery context

- What backend implemented:
  - Extended the `last_state_record` shape in the step list response with two new fields: `last_action_by` (user who created the latest state record) and `first_started_at` (earliest `entered_at` across all state records for the step).
  - Changed default sort order from `created_at DESC` to `ready_by_at ASC NULLS LAST, client_id DESC` (soonest deadline first; ties broken by newest record first).
  - Added a new query filter `record_step_state` (comma-separated string) to filter steps by their current `state`.
  - `user_last_active_step_record` has been extracted into its own dedicated endpoint — see [HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529.md](HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529.md).

- API or contract changes:
  - `last_state_record` shape extended (additive — no removed fields).
  - New query parameter `record_step_state`.
  - Default sort order changed — frontend lists will now render in a different order without any client changes.

- Feature flags/toggles: none

## Frontend action required

1. Update step-list rendering to consume the new `last_action_by` field inside `last_state_record` (display avatar / username of who last moved the step).
2. Consume `first_started_at` inside `last_state_record` to show when work on the step first began.
3. Adapt to the new sort order: steps now arrive sorted by task deadline (soonest first). Update any client-side sort assumptions accordingly.
4. Pass `record_step_state=<comma,separated,values>` in the query string when filtering the step list by state.
5. For the user's last active step record, call the dedicated endpoint — see [HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529.md](HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529.md).

## Interface details

- Endpoint: `GET /api/v1/working-sections/{working_section_id}/steps`
- Roles allowed: `ADMIN`, `MANAGER`, `WORKER`

### Request shape (query parameters)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `q` | `string \| null` | `null` | Free-text search on item article number / SKU (+ upholstery fields when `upholstery_search=true`) |
| `upholstery_search` | `boolean` | `false` | Extend `q` to also match upholstery name/code |
| `limit` | `integer` | `50` | Max 200 |
| `offset` | `integer` | `0` | Pagination offset |
| `record_step_state` | `string \| null` | `null` | **New.** Comma-separated list of `TaskStep.state` values to include, e.g. `working,paused`. Omit to return all states. |

### Response shape

```jsonc
{
  "steps_pagination": {
    "items": [
      {
        // ... existing step fields unchanged ...

        "last_state_record": {           // latest state record for the step (any user)
          "state": "working",
          "entered_at": "2026-05-20T08:00:00",
          "exited_at": null,
          "last_action_by": {            // NEW — user who created this record; null if unknown
            "client_id": "<uuid>",
            "username": "jane.doe",
            "profile_picture": "<url | null>"
          },
          "first_started_at": "2026-05-01T07:30:00"  // NEW — earliest entered_at across all records for this step; null if none
        }
      }
    ],
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

#### Active state values (for `record_step_state` filter reference)

| Value | Terminal? |
|---|---|
| `pending` | — (excluded from `user_last_active_step_record`) |
| `working` | No |
| `paused` | No |
| `ended_shift` | No |
| `blocked` | No |
| `completed` | Yes |
| `skipped` | Yes |
| `failed` | Yes |
| `cancelled` | Yes |

### Sort order (changed)

Steps are now ordered by:
1. `task.ready_by_at ASC NULLS LAST` — soonest deadline first; steps with no deadline appear at the end.
2. `step.client_id DESC` — tie-breaker; newer records first.

### Error cases

| Status | Condition |
|---|---|
| `404` | `working_section_id` not found or does not belong to the workspace |

## Validation notes

- Backend validation run: manual code review; no automated test run.
- Suggested frontend validation:
  - Verify `last_action_by` renders correctly when `null` (no avatar / fallback).
  - Verify `first_started_at` renders correctly when `null`.
  - Test `record_step_state` with a single value, multiple comma-separated values, and omitted entirely.
  - Confirm the list order matches the new sort (soonest deadline first).

## Trace links

- Parent plan: `—`
- Parent summary: `—`
- Related handoff: [HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529.md](HANDOFF_TO_FRONTEND_user_last_active_step_record_20260529.md)
