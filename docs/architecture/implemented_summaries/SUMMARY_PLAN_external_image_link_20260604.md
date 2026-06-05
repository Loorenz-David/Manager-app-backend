# SUMMARY_PLAN_external_image_link_20260604

## Metadata

- Summary ID: `SUMMARY_PLAN_external_image_link_20260604`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-06-04T13:07:04Z`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_external_image_link_20260604.md`
- Related debug plan (optional): `—`

## What was implemented

- Added `POST /api/v1/images/from-url` to create and link external images in one call without using the upload flow.
- Added external image support in the image domain via `external_url` source type and `link_external_image` event type.
- Added a new image command that validates single and batch payloads, creates `Image`, `ImageLink`, `ImageEvent`, and optional `ImageAnnotation` rows in one transaction, and returns serialized image data.
- Added an Alembic migration that extends the existing Postgres image enums with the new values.

## Files changed

- `backend/app/beyo_manager/domain/images/enums.py`: added `ImageSourceTypeEnum.EXTERNAL_URL` and `ImageEventTypeEnum.LINK_EXTERNAL_IMAGE`.
- `backend/app/beyo_manager/services/commands/images/create_from_url.py`: added the new write command for external image linking.
- `backend/app/beyo_manager/routers/api_v1/images.py`: added `CreateFromUrlBody`, imported the new command, and exposed `POST /from-url` for `admin` and `manager` roles.
- `backend/app/migrations/versions/0f935423c845_add_external_url_and_link_external_.py`: added the enum migration.
- `backend/app/tests/unit/test_image_create_from_url.py`: added command coverage for happy path and validation failures.
- `backend/app/tests/unit/test_images_router_from_url_route.py`: added router coverage for top-level array payload wrapping.

## Contract adherence

- `backend/architecture/06_commands.md`: the new write flow lives in a dedicated command and owns a single transaction.
- `backend/architecture/09_routers.md`: the router remains thin and only validates payload shape, injects auth/session, and delegates to the command.
- `backend/architecture/30_migrations.md`: the enum change was generated through Alembic, reviewed, and corrected to remove unrelated drift before upgrade.
- `backend/architecture/43_image.md`: the command preserves the polymorphic image-link pattern and stores external URLs without re-hosting.

## Validation evidence

- `PYTHONPATH=. .venv/bin/python -c "from beyo_manager.services.commands.images.create_from_url import create_from_url; print(create_from_url.__name__)"` in `backend/app`: passed.
- `PYTHONPATH=. .venv/bin/pytest tests/unit/test_image_create_from_url.py tests/unit/test_images_router_from_url_route.py -q` in `backend/app`: passed (`4 passed`).
- `APP_ENV=development PYTHONPATH=. .venv/bin/alembic upgrade head` in `backend/app`: passed after correcting the migration to target the real enum name `image_events_type_enum`.
- `APP_ENV=development PYTHONPATH=. .venv/bin/alembic current` in `backend/app`: returned `0f935423c845 (head)`.
- `npm run typecheck` in `frontend/apps/managers-app/ManagerBeyo-app-managers`: passed.

## Known gaps or deferred items

- The endpoint accepts absolute `http://` and `https://` URLs to match the existing serializer behavior and the plan’s validation contract; it does not verify remote reachability at write time.
- No broader integration test suite was run beyond the focused unit coverage and migration validation above.

## Handoff notes (if needed)

- To frontend: use `POST /api/v1/images/from-url` for already-hosted images instead of the upload/confirm-upload flow.
- From frontend dependency: `—`

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/ARCHIVE_RECORD_PLAN_external_image_link_20260604.md`
