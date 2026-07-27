# PLAN_slide_background_color_20260723

## Metadata

- Plan ID: `PLAN_slide_background_color_20260723`
- Status: `archived`
- Owner agent: `claude`
- Implementer: `codex`
- Created at (UTC): `2026-07-23T00:00:00Z`
- Last updated at (UTC): `2026-07-23T07:07:59Z`
- Related issue/ticket: frontend presentation editor — per-slide background color
- Intention plan: n/a (small additive extension of the existing app_update_presentations composition system)

## Goal and intent

- Goal: Add an optional, per-slide **background color** to app update presentation slides, so the frontend editor can set a solid background behind a slide's timeline composition and the backend persists/serves it.
- Business/user intent: Authors want to place a solid color behind a slide (text-only slides, captions over color, brand backgrounds) without faking it via a full-bleed image asset. Text elements already carry `style.background_color`, but that only fills a text block's box — there is no slide-level background today.
- Non-goals:
  - Gradients, background images, opacity layers, or a multi-field `background` config. (Explicitly deferred — see Risks. A single solid `background_color` is the scope. The `composition_schema_version` already on the slide lets a richer `background` config be added later without breaking stored slides.)
  - Slide-to-slide transitions, element animations, or any change to media/text elements.
  - Any change to consumer eligibility, publishing rules, view-state, or audience.

## Scope

- In scope:
  - New nullable column `background_color` on `app_update_presentation_slides`.
  - Validation (hex `#RRGGBB` or `#RRGGBBAA`, or `null`).
  - Accept/set it in: `create_slide`, `update_slide`, and `replace_slide_composition` (composition endpoint).
  - Include it in `serialize_slide` (so it appears everywhere slides are serialized: `/active`, `/history`, `/preview`, admin `get`, and every command response).
  - Copy it on `create_presentation_version` (new-version snapshot).
  - Reversible Alembic migration.
  - Tests + docs.
- Out of scope: everything under Non-goals.
- Assumptions:
  - `background_color` is nullable; `null` means "no slide background" (frontend applies its own default/transparent).
  - Value is stored exactly as provided (validated hex string); the frontend renders it.
  - Alembic head at authoring time is `b58cdffb5ccc`. **Confirm with `alembic current` before writing the migration** and set `down_revision` to whatever it reports (more migrations may land before implementation).

## Clarifications required

- [ ] None blocking. (Solid color only is confirmed by product. If a richer `background` config is later wanted, it is a separate plan.)

## Acceptance criteria

1. `AppUpdatePresentationSlide` has a nullable `background_color` column; migration applies and downgrades cleanly (`upgrade → downgrade → upgrade` round-trip with no drift on this table).
2. `POST /{id}/slides` and `PATCH /{id}/slides/{slide_id}` accept an optional `background_color`; a valid hex is stored, an invalid value returns `422`, and omitting it leaves it unchanged (PATCH) / `null` (create).
3. `PUT /{id}/slides/{slide_id}/composition` accepts `background_color` and sets it on the slide atomically with the rest of the composition; invalid hex → `422`.
4. `serialize_slide` includes `"background_color": <hex|null>` in every slide payload (`/active`, `/history`, `/preview`, admin `GET /{id}`, and command responses).
5. `create_presentation_version` copies `background_color` into the new draft's slides.
6. All edits are draft-only (published/archived slide edits still `409`) — no new authorization surface.
7. Backward compatible: existing slides read back `background_color: null`; existing clients unaffected.
8. `ruff check` clean on changed files; full app_update test suite green; new tests cover valid/invalid/round-trip/version-copy.

## Contracts and skills

### Contracts loaded

- `backend/architecture/03_models.md`: adding a column to an existing SQLAlchemy 2.x model (`Mapped`/`mapped_column`, nullable rules).
- `backend/architecture/30_migrations.md`: additive, reversible Alembic migration; never modify an applied migration.
- `backend/architecture/06_commands.md` + `backend/architecture/06_commands_local.md`: command shape + `maybe_begin` (the edited commands already use it — do not change transaction structure).
- `backend/architecture/09_routers.md`: request body model shape; path-param merge into `incoming_data`.
- `backend/architecture/46_serialization.md` + `_local`: plain serializer functions over ORM instances.
- `backend/architecture/15_testing.md`: unit (domain, no DB) + integration (real DB, function-scoped `db_session`) tiers.
- `backend/architecture/21_naming_conventions.md`: column/field naming (`background_color`, snake_case).

### Local extensions loaded

- `backend/architecture/06_commands_local.md`: `maybe_begin` — already in use by the edited commands; no change.
- `backend/architecture/40_identity_local.md`: no new table/prefix — not needed.

### File read intent — pattern vs. relational

Permitted relational reads (understand what exists — do these):
- `app/beyo_manager/models/tables/app_update_presentations/presentation_slide.py` — exact current slide columns/`__table_args__`.
- `app/beyo_manager/domain/app_update_presentations/composition_schemas.py` — the existing hex validation (`_HEX_COLOR` regex + `_hex_color`); reuse it, do not reinvent.
- `app/beyo_manager/domain/app_update_presentations/serializers.py` — `serialize_slide` (where to add the field).
- `app/beyo_manager/services/commands/app_update_slides/requests/__init__.py`, `create_slide.py`, `update_slide.py` — where slide fields are parsed/set.
- `app/beyo_manager/services/commands/app_update_slide_composition/requests/__init__.py`, `replace_slide_composition.py` — composition request + command.
- `app/beyo_manager/services/commands/app_update_presentations/_copy_presentation_children_in_session.py` — new-version copy.
- `app/beyo_manager/routers/api_v1/app_update_presentations.py` — `SlideBody`, `SlideCompositionBody`.
- Latest migration under `app/migrations/versions/` for the enum/column idiom, and `alembic current` for the head.

Prohibited pattern reads: do not open unrelated commands/routers/serializers to learn shape — the contracts above define it.

### Skill selection

- Routing entry: `backend/task_system/backend_contract_goal_mapping_guide.md` (backend-local contract selection).
- This is a CRUD-field extension of an existing domain; no realtime/worker/socket triggers apply.
- Excluded: file-storage/S3, events/sockets, migrations-with-enums (no enum here) — not triggered.

## Implementation plan

Reuse hex validation — do **not** duplicate the regex.

1. **Domain — expose a reusable hex validator.**
   In `domain/app_update_presentations/composition_schemas.py`, add a public helper that raises the domain `ValidationError` on bad hex and returns the value (or `None`):
   ```python
   def validate_background_color(value: str | None) -> str | None:
       if value is None:
           return None
       if not _HEX_COLOR.match(value):
           raise ValidationError("background_color must be a hex color like '#RRGGBB' or '#RRGGBBAA'.")
       return value
   ```
   (Keep it next to `_HEX_COLOR`. Import `ValidationError` is already present in that module.)

2. **Model — add the column.**
   In `models/tables/app_update_presentations/presentation_slide.py`, add after the timeline fields:
   ```python
   background_color: Mapped[str | None] = mapped_column(String(9), nullable=True)
   ```
   (`String(9)` fits `#RRGGBBAA`. No index; not filtered on.)

3. **Migration — additive, reversible.**
   Confirm head with `alembic current`. Hand-write a migration (single nullable column — avoid autogenerate drift):
   - `down_revision = "b58cdffb5ccc"` (or whatever `alembic current` reports at implementation time).
   - `upgrade`: `op.add_column("app_update_presentation_slides", sa.Column("background_color", sa.String(length=9), nullable=True))`
   - `downgrade`: `op.drop_column("app_update_presentation_slides", "background_color")`
   - No enum, no data backfill. Verify `upgrade → downgrade → upgrade`.

4. **Serializer — expose it.**
   In `serializers.py::serialize_slide`, add `"background_color": slide.background_color` to the returned dict (alongside `playback_mode`/`duration_ms`/`composition_schema_version`). The legacy adapter needs no change (this is a direct slide field, always serialized).

5. **create_slide / update_slide.**
   - `services/commands/app_update_slides/requests/__init__.py`: add `background_color: str | None = None` to `CreateSlideRequest` and `UpdateSlideRequest`.
   - `create_slide.py`: after the other optional setters, `if request.background_color is not None: slide.background_color = validate_background_color(request.background_color)`. (Validate even on set so bad hex → 422.)
   - `update_slide.py`: add `"background_color"` to `_SETTABLE`, and validate before the loop when present: `if "background_color" in provided: validate_background_color(request.background_color)`. (The value is applied by the existing `_SETTABLE` loop; validation just guards it. To allow clearing, PATCH with explicit `background_color: null` is honored by the existing `model_dump(exclude_unset=True)` + loop — confirm `null` is settable; if the loop skips `None`, keep clear-to-null working by setting it explicitly.)

6. **Composition endpoint.**
   - `services/commands/app_update_slide_composition/requests/__init__.py`: add `background_color: str | None = None` to `SlideCompositionReplaceRequest`.
   - `replace_slide_composition.py`: validate up front with the other config validation (`validate_background_color(request.background_color)`), and set `slide.background_color = request.background_color` alongside `slide.playback_mode` / `slide.duration_ms` / `slide.composition_schema_version`.

7. **Router bodies.**
   In `routers/api_v1/app_update_presentations.py`, add `background_color: str | None = None` to `SlideBody` and `SlideCompositionBody`. (No other router change; path-param merge already forwards it into `incoming_data`.)

8. **new-version copy.**
   In `_copy_presentation_children_in_session.py`, add `background_color=slide.background_color` to the `AppUpdatePresentationSlide(...)` construction for the copied slide.

9. **Docs.**
   - `docs/handoff/presentation_system/09_slide_composition.md`: add `background_color` to the "slide shape (now)" JSON and to the composition body; one line describing it (nullable hex; `null` = no background).
   - `docs/handoff/presentation_system/05_admin_slides_media.md`: mention `background_color` in the slide timeline fields note.
   - `docs/handoff/presentation_system/04_admin_presentations.md`: include `background_color` in the slide shape if the full slide is shown there.

## Risks and mitigations

- Risk: Scope creep into gradients/background images.
  Mitigation: Ship only a solid `background_color` string. The slide already has `composition_schema_version`; a future `background` JSON config is a separate, versioned plan and does not block this.
- Risk: Inconsistent validation (hex allowed in one path, not another).
  Mitigation: Single shared `validate_background_color` helper called in create/update/composition paths.
- Risk: PATCH cannot clear the color back to `null`.
  Mitigation: Ensure the update path honors an explicit `background_color: null` (test it). If the `_SETTABLE` loop skips `None`, set it explicitly when the key is present in `model_dump(exclude_unset=True)`.
- Risk: Migration enum/drift issues.
  Mitigation: Plain `String(9)` column, no enum, hand-written migration; verify round-trip and that `alembic check` shows no NEW drift on this table.
- Risk: Published immutability bypass.
  Mitigation: All three write paths already call `load_presentation_for_write` (draft guard) — do not add any path that mutates a published slide.

## Validation plan

- `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head`: clean round-trip; head advances by one revision.
- `ruff check <changed files>`: clean (models keep only the pre-existing forward-ref `F821`, consistent with the rest of the repo).
- New tests (all under `tests/…/app_update_presentations/`):
  - Unit (domain, no DB): `validate_background_color` accepts `#RRGGBB`, `#RRGGBBAA`, and `None`; rejects `"red"`, `"#FFF"`, `"#GGGGGG"`.
  - Integration:
    - `create_slide` with `background_color` → serialized slide carries it; invalid hex → `ValidationError`/`422`.
    - `update_slide` sets it; setting explicit `null` clears it; not-draft → `409` (existing guard).
    - `replace_slide_composition` with `background_color` → set atomically; invalid → `422`.
    - `create_presentation_version` copies `background_color`.
    - Existing slide (no value) serializes `background_color: null`.
- Full suite: `pytest tests/unit/domain/app_update_presentations/ tests/unit/test_app_update_presentations_router.py tests/integration/services/commands/app_update_presentations/ tests/integration/services/queries/app_update_presentations/ -q` → all green.
- Global collection unaffected: `pytest --collect-only -q` succeeds.

## Review log

- 2026-07-23 claude: Authored plan. Solid-color-only scope confirmed with product; gradient/image deferred.
- 2026-07-23 codex: Implemented the feature, added focused unit/integration/router coverage and the requested handoff documentation, and completed migration/test/lint validation.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `Codex`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_slide_background_color_20260723.md`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_slide_background_color_20260723.md`
