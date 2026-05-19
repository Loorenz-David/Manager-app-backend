# SUMMARY_client_id_injection_20260518

## Metadata

- Summary ID: `SUMMARY_client_id_injection_20260518`
- Status: `summarized`
- Owner agent: `GitHub Copilot (GPT-5.3-Codex)`
- Created at (UTC): `2026-05-18T19:46:00Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_client_id_injection_20260518.md`
- Related debug plan: none

## What was implemented

- Added shared `client_id` format validator utility for prefixed ULID checks.
- Added optional `client_id` fields across all in-scope create request models and nested create inputs.
- Implemented create-path validation and duplicate checks in item, customer, task, task-step, task-note, case, conversation, message, working section, item upholstery, and upholstery inventory commands.
- Implemented `find_or_create_*` semantics: client-provided `client_id` is validated before lookup and used only on create path.
- Updated all in-scope router body models to accept optional `client_id` and pass-through to commands.
- Added cases request module to formalize create command parsing and validation.
- Added executable end-to-end validation script for the 20 acceptance scenarios.

## Files changed

- `backend/app/beyo_manager/services/commands/utils/client_id.py`: new shared validator `validate_provided_client_id`.
- `backend/app/beyo_manager/services/commands/items/requests/__init__.py`: added `client_id` to create and nested upholstery inputs.
- `backend/app/beyo_manager/services/commands/customers/requests/__init__.py`: added `client_id` to create/find-or-create requests.
- `backend/app/beyo_manager/services/commands/tasks/requests/__init__.py`: added `client_id` to create task and nested inputs.
- `backend/app/beyo_manager/services/commands/task_steps/requests/__init__.py`: added `client_id` to add-step request.
- `backend/app/beyo_manager/services/commands/working_sections/requests/create_working_section_request.py`: added `client_id`.
- `backend/app/beyo_manager/services/commands/upholstery/requests/__init__.py`: added `client_id` to create inventory request.
- `backend/app/beyo_manager/services/commands/cases/requests/__init__.py`: new request models/parsers for case, conversation, message create paths.
- `backend/app/beyo_manager/services/commands/items/create_item.py`: validate, duplicate-check, kwargs injection.
- `backend/app/beyo_manager/services/commands/items/find_or_create_item.py`: fail-fast validation, create-path duplicate-check, kwargs injection.
- `backend/app/beyo_manager/services/commands/customers/create_customer.py`: validate, duplicate-check, kwargs injection.
- `backend/app/beyo_manager/services/commands/customers/find_or_create_customer.py`: fail-fast validation, create-path duplicate-check, kwargs injection.
- `backend/app/beyo_manager/services/commands/tasks/create_task.py`: task/nested-step validation and injection; note/upholstery helper propagation.
- `backend/app/beyo_manager/services/commands/tasks/create_task_note.py`: helper and command support for optional `client_id`.
- `backend/app/beyo_manager/services/commands/task_steps/add_task_step.py`: validation and kwargs injection.
- `backend/app/beyo_manager/services/commands/items/create_item_upholstery.py`: helper/command validation, duplicate-check, kwargs injection.
- `backend/app/beyo_manager/services/commands/working_sections/create_working_section.py`: validation and kwargs injection.
- `backend/app/beyo_manager/services/commands/upholstery/create_upholstery_inventory.py`: validation and kwargs injection.
- `backend/app/beyo_manager/services/commands/cases/create_case.py`: request parsing and client_id injection.
- `backend/app/beyo_manager/services/commands/cases/create_conversation.py`: request parsing and client_id injection.
- `backend/app/beyo_manager/services/commands/cases/send_message.py`: request parsing and client_id injection.
- `backend/app/beyo_manager/routers/api_v1/items.py`: create/find-or-create body models accept `client_id`.
- `backend/app/beyo_manager/routers/api_v1/customers.py`: create/find-or-create body models accept `client_id`.
- `backend/app/beyo_manager/routers/api_v1/tasks.py`: create and nested create body models accept `client_id`.
- `backend/app/beyo_manager/routers/api_v1/cases.py`: create body models accept `client_id`.
- `backend/app/beyo_manager/routers/api_v1/working_sections.py`: create body model accepts `client_id`.
- `backend/app/beyo_manager/routers/api_v1/item_upholsteries.py`: create body model accepts `client_id`.
- `backend/app/beyo_manager/routers/api_v1/upholstery_inventories.py`: create body model accepts `client_id`.
- `backend/tests/client_id_injection/test_client_id_injection.sh`: executable validation script covering all 20 acceptance scenarios.

## Contract adherence

- `backend/architecture/40_identity.md`: caller-provided `client_id` accepted and validated for create commands.
- `backend/architecture/40_identity_local.md`: prefixes respected (`itm`, `cus`, `tsk`, `tno`, `tsp`, `ca`, `ccv`, `ccm`, `wsec`, `iup`, `uin`).
- `backend/architecture/06_commands.md` and `backend/architecture/06_commands_local.md`: command-local parsing, `maybe_begin` usage preserved where already established.
- `backend/architecture/05_errors.md`: typed `ValidationError` and `ConflictError` used for invalid and duplicate IDs.
- `backend/architecture/09_routers.md`: routers remain thin pass-through layers.

## Validation evidence

- `cd backend/app && .venv/bin/python -m py_compile <all changed python files>`: pass (no syntax errors).
- `cd backend/app && git ls-files -m -o -- beyo_manager | rg '\.py$' | xargs .venv/bin/python -m py_compile`: pass.
- `cd backend && bash tests/client_id_injection/test_client_id_injection.sh`: pass (`RESULT: 20 passed, 0 failed`).

## Known gaps or deferred items

- None.

## Handoff notes

- None required.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_client_id_injection_20260518.md`
