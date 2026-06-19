# SUMMARY_case_participant_added_event_20260619

## Metadata

- Summary ID: `SUMMARY_case_participant_added_event_20260619`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-19T11:15:10Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_case_participant_added_event_20260619.md`
- Related debug plan (optional): none

## What was implemented

- Added per-user `case:participant-added` realtime dispatches to `create_case`, while preserving the existing workspace `case:created` broadcast.
- Added per-user `case:participant-added` realtime dispatches to `add_participant`, with unread count derived from the current sum of `CaseConversation.last_message_seq`.
- Updated both realtime handoff catalog copies so `case:participant-added` is documented as a `UserEvent` with an `unread_count` payload and revised frontend handler guidance.

## Files changed

- `backend/app/beyo_manager/services/commands/cases/create_case.py`: emits one `UserEvent` per participant with case-scoped unread count semantics for creation.
- `backend/app/beyo_manager/services/commands/cases/add_participant.py`: computes current unread total inside the transaction and emits one `UserEvent` per newly added participant after commit.
- `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`: corrects event scope and payload for `case:participant-added`.
- `frontend/docs/handoff/from_backend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`: mirrors the backend handoff catalog update.

## Contract adherence

- `11_infra_events.md`: all new user-targeted realtime events are built with `build_user_event` and dispatched only after the transaction commits.
- `06_commands.md`: DB reads needed for side-effect payloads remain inside the transaction block; event dispatch remains outside it.
- `56_realtime_layer.md`: payloads keep the required `{ client_id, ...extra }` shape and route `case:participant-added` through `user:{id}` rooms.
- `23_documentation.md`: both handoff catalog copies were updated together.

## Validation evidence

- `python3 -m py_compile backend/app/beyo_manager/services/commands/cases/create_case.py backend/app/beyo_manager/services/commands/cases/add_participant.py`: passed.
- `rg -n "case:participant-added|unread_count" backend/app/beyo_manager/services/commands/cases/create_case.py backend/app/beyo_manager/services/commands/cases/add_participant.py`: confirmed the new user event dispatches and payload fields.
- `rg -n "case:participant-added|unread_count" backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md frontend/docs/handoff/from_backend/HANDOFF_TO_FRONTEND_realtime_event_catalog_20260619.md`: confirmed both catalog copies were updated.

## Known gaps or deferred items

- No frontend handler implementation was added in this turn; this work only emits and documents the new event.
- No end-to-end Socket.IO runtime check was run in a live app session.

## Handoff notes (if needed)

- Frontend should handle `case:participant-added` as a user-scoped event by adding the case to "my cases" and seeding that case's unread badge from `payload.unread_count`.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_case_participant_added_event_20260619.md`
