# PLAN_image_annotations_batch_20260522

## Metadata

- Plan ID: `PLAN_image_annotations_batch_20260522`
- Status: `archived`
- Owner agent: `Copilot`
- Created at (UTC): `2026-05-22T00:00:00Z`
- Last updated at (UTC): `2026-05-22T10:25:00Z`
- Related issue/ticket: `batch image annotations payload support`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_image_annotations_batch_20260522.md`

## Goal and intent

- Goal:
  - Extend backend image annotation creation to accept batch payloads (`data.items[]`) from frontend drawing tools while preserving current single-annotation behavior.
- Business/user intent:
  - Frontend drawing UX sends multi-shape overlays in one save action; backend should accept and persist all submitted shapes/text without forcing per-shape API calls.
- Non-goals:
  - No redesign of image storage/S3 flow.
  - No migration of existing annotation records.
  - No changes to unrelated image endpoints.

## Scope

- In scope:
  - Update request parsing/validation for `POST /api/v1/images/{image_client_id}/annotations`.
  - Support `data.items[]` batch format with per-item tool validation (`draw`, `arrow`, `circle`, `rectangle`, `text`, `measurement`, `highlight`).
  - Persist one `ImageAnnotation` row per batch item.
  - Return deterministic response payload for batch operation.
  - Keep backward compatibility for existing single-annotation payload.
- Out of scope:
  - Frontend code changes.
  - New endpoint creation unless required by contract constraints.
  - Realtime events for annotation creation (unless already required by current domain patterns).
- Assumptions:
  - Frontend may continue sending `annotation_type` at top-level even when items have mixed `tool` types.
  - In batch mode (`data.items[]` present), top-level `annotation_type` is ignored.
  - `ImageAnnotation.annotation_type` maps directly to each item tool.
  - Existing auth/permission path remains unchanged.

## Clarifications required

- [x] Should top-level `annotation_type` be ignored in batch mode (`data.items[]`) or enforced to match every item tool? — **Resolved:** ignore top-level `annotation_type` in batch mode; use each `items[].tool` as source of truth.
- [x] What is the preferred batch success response contract: created IDs list only, count only, or full serialized annotations? — **Resolved:** return created IDs list (`created_annotation_client_ids`).

## Acceptance criteria

1. `POST /api/v1/images/{image_client_id}/annotations` accepts both:
   - legacy single payload (`annotation_type` + `data`), and
   - batch payload (`data.items[]` with per-item `tool` + tool fields).
2. For batch payloads, backend creates one `ImageAnnotation` per valid item in one request and returns HTTP 200 with explicit created result metadata.
  - Batch 200 response includes `data.created_annotation_client_ids[]`.
3. Validation errors identify the failing batch item index and missing keys (for example `items[2] missing required keys for text: ['x', 'y', 'text']`).
4. Existing single-annotation clients remain functional without payload changes.
5. Routers README image annotation section is updated to document both payload modes and response shape.

## Contracts and skills

### Selected contracts

- `../architecture/01_architecture.md`: enforce layer boundaries and avoid leaking router logic into command internals.
- `../architecture/04_context.md`: preserve ServiceContext usage and identity/session propagation.
- `../architecture/05_errors.md`: consistent domain validation/not-found error behavior.
- `../architecture/06_commands.md`: command transaction, session usage, and write orchestration.
- `../architecture/07_queries.md`: read-side compatibility and no query-side regressions.
- `../architecture/09_routers.md`: keep router thin and delegate behavior to command layer.
- `../architecture/21_naming_conventions.md`: naming for request models, response keys, and command internals.
- `../architecture/40_identity.md`: preserve client_id identity behavior.
- `../architecture/41_user.md`: maintain actor/audit consistency via `created_by_id`.
- `../architecture/42_event.md`: respect event model conventions (no unintended event shape changes).
- `../architecture/48_presence.md`: ensure no side effects on presence paths.

### Added from guide

- `../architecture/03_models.md`: annotation model field/type constraints and persistence compatibility.
- `../architecture/08_domain.md`: domain enums/tool mapping semantics.
- `../architecture/11_infra_events.md`: verify whether annotation writes require event dispatch integration.
- `../architecture/13_sockets.md`: check if annotation creation should emit realtime updates.
- `../architecture/15_testing.md`: test coverage expectations for command and router payload modes.
- `../architecture/30_migrations.md`: confirm no migration is needed for this change.

Trigger + justification:
- Trigger `CRUD + realtime`: image annotation write behavior and potential websocket update expectations.

### Local extensions loaded

- `../architecture/06_commands_local.md`: local `maybe_begin` transaction utility and session safety rules.
- `../architecture/07_queries_local.md`: local query behavior constraints (offset model) for any annotation reads touched by tests.

Applied precedence:
- Local extension overrides baseline only for this app.

### Excluded contracts

- `../architecture/16_background_jobs.md`: no worker/retry job behavior in scope.
- `../architecture/12_infra_redis.md`: no redis workflow changes required.
- `../architecture/52_replayability.md`: no replay/runtime pipeline changes.
- `../architecture/54_ci_cd_runtime.md`: no deployment pipeline change in scope.

### File read intent — pattern vs. relational

Before reading any implementation file outside this plan's scope, apply the test:

> "Am I reading this to understand **how to write** my new code — or to understand **what this existing code does**?"

- **How to write** → read the contract instead (`06_commands.md`, `09_routers.md`, `46_serialization.md`).
- **What exists** → reading is legitimate (existing endpoint behavior, serializer output shape, model fields, command wiring).

Prohibited (pattern reads — contract already covers these):
- Reading unrelated commands only to copy transaction/error skeleton.
- Reading unrelated routers only to copy handler shape.

Permitted (relational reads — understanding what exists):
- Current image router and annotation command behavior.
- Current image serializer response contract.
- Current `ImageAnnotation` model and enum mappings.

### Skill selection

- Primary skill: `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`
- Router trigger terms: `images`, `annotations`, `batch`, `draw`, `text`, `shapes`
- Excluded alternatives: `worker runtime skills` — not relevant to synchronous API write path.

## Implementation plan

1. Contract alignment and behavior decision
   - Decide and document batch semantics: top-level `annotation_type` handling in batch mode, mixed-tool acceptance, and response shape contract.
2. Request schema updates
   - Add/extend request models for batch item objects and optional batch wrapper (`data.items[]`).
   - Maintain compatibility with legacy single-annotation payload.
3. Command validation redesign
   - Refactor annotation validation to operate per item with indexed error messages.
   - Reuse tool-required key map while supporting both single and batch modes.
4. Persistence implementation
   - In one command invocation/transaction, create one `ImageAnnotation` row per valid item.
   - Preserve existing `created_by_id`, `image_id`, and enum mapping behavior.
5. Router/service response contract
  - Return deterministic batch response with created IDs list (`created_annotation_client_ids`) while keeping legacy compatibility where needed.
6. Documentation updates
   - Update images router README annotation endpoint request/response shapes for both single and batch payload forms.
7. Testing
   - Add/update unit/integration tests for:
     - single payload success,
     - batch payload success with mixed tools,
     - item-indexed validation failures,
     - backward compatibility behavior.

## Risks and mitigations

- Risk: Breaking existing single-annotation clients.
  Mitigation: Keep legacy payload path intact and add explicit compatibility tests.

- Risk: Ambiguous batch contract (top-level `annotation_type` vs item `tool`).
  Mitigation: lock one documented rule before implementation and enforce it consistently.

- Risk: Partial writes in malformed batches.
  Mitigation: validate all items before insert or rely on single transaction rollback semantics.

- Risk: Frontend/backed response mismatch after batch support.
  Mitigation: publish final response shape in router README and add API contract tests.

## Validation plan

- `pytest tests/unit -k "image and annotation"`: batch and single annotation unit coverage passes.
- `pytest tests/integration -k "images and annotations"`: endpoint integration validates both payload modes.
- Manual API check:
  - `POST /api/v1/images/{id}/annotations` with legacy single payload returns 200.
  - `POST /api/v1/images/{id}/annotations` with `data.items[]` mixed tools returns 200 and `data.created_annotation_client_ids[]`.
  - Invalid batch item returns 422 with indexed error field.
- Docs check:
  - `backend/app/beyo_manager/routers/README.md` reflects new annotation payload and response shapes.

## Review log

- `2026-05-22` `Copilot`: initial implementation plan drafted from template and contract mapping guide.
- `2026-05-22` `Copilot`: implemented batch annotation support (single + batch modes), updated router docs, and added unit tests.
- `2026-05-22` `Copilot`: lifecycle transition completed to archived after summary and archive record generation.

## Lifecycle transition

- Current state: `archived`
- Next state: `none`
- Transition owner: `Copilot`
