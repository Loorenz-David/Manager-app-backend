# PLAN_shopify_metafield_preferences_delete_capability_20260713

## Metadata

- Plan ID: `PLAN_shopify_metafield_preferences_delete_capability_20260713`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-13T15:00:00Z`
- Last updated at (UTC): `2026-07-13T10:44:52Z`
- Related issue/ticket: `n/a`
- Intention plan: none separate — this is a new capability requested directly by the user on top of the already-shipped create/query capability. Source context: `backend/docs/architecture/archives/implementation/PLAN_shopify_metafield_preferences_20260713.md` (the original feature), `backend/docs/architecture/under_construction/intention/pulling_and_storing_metafields.md` (original intention doc, which explicitly listed "an admin preference-management page" and any delete/disable capability as non-goals for phase 1 — this plan is the deliberate phase-2 addition of the delete half of that).

## Goal and intent

- Goal: add the ability to delete one or more previously-created Shopify metafield preferences, given a list of their own `client_id`s, via a new dedicated router and service.
- Business/user intent: the create/query capability exists (`POST` + `GET /metafield-preferences`), but there is currently no way to remove a saved preference short of a manual DB operation. The frontend needs this to let users un-select a metafield they'd previously chosen for a category (e.g. they picked the wrong definition, or no longer want it surfaced on product creation for that shop/category).
- Non-goals: no bulk "delete all preferences for a category" or "delete all preferences for a shop" shortcut — the caller must supply explicit `client_id`s (matches the user's literal ask: "given a list of client_ids"); no restore/undo endpoint (restoring a soft-deleted preference already happens implicitly via the existing create command — see "Relationship to the existing create command" below, so a separate restore endpoint would be a duplicate code path); no hard delete; no cascading side effects on Shopify itself (this only ever touched the local preference relationship, never Shopify's own metafield definitions, and deleting a preference does not call Shopify at all).

## Scope

- In scope:
  - New command `delete_shopify_metafield_preferences` — batch soft-delete by `client_id` list, workspace-scoped, all-or-nothing.
  - New request parser (`DeleteShopifyMetafieldPreferencesRequest`).
  - New route `DELETE /api/v1/integrations/shopify/metafield-preferences` on the existing `routers/api_v1/shopify.py` router (collection-level, not a path-parameterized single-resource delete — this is a batch operation by design, matching the user's ask).
  - Unit tests for the request parser and router wiring/role-gating.
  - **Integration test against a real DB, written and run as part of this same plan** — not deferred. The prior create/query implementation shipped without integration tests despite the original plan requiring them, which was flagged and separately corrected; this plan does not repeat that gap.
- Out of scope: any change to the create or query commands/routes (both already correct and already serialize internally, post-correction); any change to the model or a new migration (the table already has `is_deleted`/`deleted_at`/`deleted_by_id` — nothing to add); any frontend work; any `ShopifyIntegrationEvent` emission (consistent with the create command's own documented default of not emitting one for this table — see Assumptions).
- Assumptions:
  - **Request shape is a flat list of strings**, `{"client_ids": ["shpmfp_...", "shpmfp_..."]}`, not the per-item-object shape `delete_issue_types` uses (`{"issues": [{"issue_type_id": "..."}]}`). The object-wrapping in that precedent exists to leave room for additional per-item fields; there are none needed here, and the user's own phrasing ("given a list of client_ids") is literally a flat list — using the simpler shape is not a deviation from convention so much as picking the right-sized version of it.
  - **Authorization matches the create/query routes**: `[ADMIN, MANAGER, SELLER, WORKER]`, not the stricter `[ADMIN, MANAGER]` `delete_issue_types` uses or the `[ADMIN]`-only `DELETE /shops/{shop_integration_id}` uses. Reasoning: a metafield preference is a low-stakes, per-category UI selection created by all four of those roles already (the create route uses the same four) — restricting who can delete it more tightly than who can create it would be an inconsistent, unrequested policy choice, not a safety improvement (deleting a Shopify shop integration or an issue type has much larger blast radius than deleting one preference row).
  - **Deletion is workspace-scoped, not creator-scoped** — any of the four roles can delete any preference in the workspace, not just ones they personally created. This matches how the create/query commands are already workspace-scoped rather than creator-scoped (`only_my_preferences` on the query is opt-in filtering for reads, not an ownership restriction on writes). If this is wrong, it's a one-line addition (an extra `created_by_id == ctx.user_id` filter) — flagged as a clarification below rather than assumed silently past the point of no return.
  - **All-or-nothing, like `delete_issue_types`**: if any requested `client_id` doesn't resolve (wrong workspace, doesn't exist, already deleted), the whole batch fails with `NotFound` and nothing is deleted — not "delete what's found, report what's missing." Matches this codebase's only existing batch-delete-by-ids precedent exactly.
  - **Response is `{}`** (empty ack), matching `delete_issue_types`' return shape and `46_serialization.md`'s "computed results/acks with no natural resource shape return a plain dict" exemption — no serializer needed at all for this command.
  - **No Shopify API call of any kind** — deleting a preference is purely a local operation; nothing about a `ShopifyMetafieldPreference` row requires confirming anything against Shopify.

### Relationship to the existing create command — no separate restore endpoint needed

`create_shopify_metafield_preferences` already restores a soft-deleted row (`is_deleted=False, deleted_at=None, deleted_by_id=None`) when a selection matching an existing soft-deleted row's `(shop_integration_id, item_category_id, shopify_metafield_definition_id)` is submitted again. This means "undo a delete" already works today, for free, by re-submitting the same selection through the create route — deleting via `client_id` and restoring via the four-value business key are two different addressing schemes for the same underlying row, which is intentional and requires no reconciliation: a delete command doesn't need to know or care that a future create call might resurrect the row it just soft-deleted.

## Clarifications required

- [ ] Should deletion be restricted to preferences the requesting user created (`created_by_id == ctx.user_id`), or workspace-wide as currently assumed? Default: workspace-wide (see Assumptions). This is a one-line change if wrong — flagged so it isn't silently baked in as unreviewable.
- [ ] Should a `client_id` that refers to an *already soft-deleted* preference be treated as "not found" (current default, consistent with `delete_issue_types`' `is_deleted.is_(False)` filter) or as a silent no-op success? Default: not-found/all-or-nothing failure, for consistency with the only existing precedent in this codebase.

## Acceptance criteria

1. `DELETE /api/v1/integrations/shopify/metafield-preferences` accepts `{"client_ids": [...]}`, requires role `admin`/`manager`/`seller`/`worker`, and soft-deletes every referenced `ShopifyMetafieldPreference` row (`is_deleted=True`, `deleted_at=<now>`, `deleted_by_id=ctx.user_id`).
2. Every `client_id` must belong to the authenticated workspace and must not already be soft-deleted; if any one fails this check, the entire request fails (`NotFound`) and **zero rows are modified**, not just the invalid ones excluded.
3. `workspace_id` is never read from `incoming_data` — only from `ctx.workspace_id`, matching every other command in this codebase.
4. The command is atomic (single `maybe_begin` block, validation before any write) and returns `{}` on success.
5. A soft-deleted preference can be recreated via the existing `create_shopify_metafield_preferences` route without any change to that route — proven by an integration test that deletes a preference and then re-creates the same selection, asserting the row is restored (not duplicated).
6. Role gating is enforced (a role outside the four allowed is rejected) and workspace isolation is enforced (a `client_id` belonging to another workspace is rejected as not-found, not silently skipped).
7. An integration test against the real local Postgres DB exists and passes for: successful batch delete, all-or-nothing rejection on one invalid ID, workspace isolation, and the delete-then-recreate restore path (acceptance criterion 5).

## Contracts and skills

### Contracts loaded

- `backend/architecture/04_context.md`: `ServiceContext` shape, `ctx.workspace_id`/`ctx.user_id` never from `incoming_data`.
- `backend/architecture/05_errors.md`: `NotFound` for the all-or-nothing rejection.
- `backend/architecture/06_commands.md` + `06_commands_local.md`: `maybe_begin` — this command is a single, simple transaction (validate, then mutate ORM attributes directly, no explicit `session.add`/`delete` needed since nothing is being removed from the table).
- `backend/architecture/09_routers.md`: standard skeleton, plus the **`DELETE` with a JSON body** pattern — this is not explicitly documented in `09_routers.md`'s HTTP-method table (which shows `DELETE /api/v1/records/{record_client_id}` as path-param-only), but it is an established, working pattern in this exact codebase (`DELETE ""` on `routers/api_v1/issue_types.py`, `_DeleteIssueTypesBody` declared as a route parameter) — followed here rather than re-deriving a different shape.
- `backend/architecture/21_naming_conventions.md`: file/function naming.
- `backend/architecture/24_multi_tenancy.md`: workspace_id as the first/only filter.
- `backend/architecture/25_soft_delete.md`: soft-delete pattern (`is_deleted=True, deleted_at=<now>`) — this plan additionally sets `deleted_by_id`, which the canonical contract's example doesn't show but the model already has as a column (mirrors `created_by_id`/`updated_by_id`).
- `backend/architecture/28_roles_permissions.md`: role constants, `require_roles([...])`.
- `backend/architecture/46_serialization.md`: the "empty ack" exemption — no serializer needed for this command, so the service-layer-serializes convention (confirmed and already applied to the create/query commands) doesn't come into play here at all.
- `backend/architecture/57_shopify_integration.md`: confirms this table's domain conventions (`shpmfp_` prefix, no Shopify API calls needed for a purely-local delete).

### File read intent — pattern vs. relational

- **How to write** → `services/commands/issue_types/delete_issue_types.py` + `routers/api_v1/issue_types.py`'s `route_delete_issue_types`/`_DeleteIssueTypesBody` are the direct pattern for this entire plan (batch delete by ID list, all-or-nothing, `DELETE ""` with body) — do not re-derive from a single-resource delete like `disconnect_shopify_shop.py`, which is a different shape (one resource, no body, path param).
- **What exists** (relational reads, already done during planning):
  - `beyo_manager/models/tables/shopify/shopify_metafield_preference.py` — exact column names for the soft-delete write.
  - `beyo_manager/services/commands/shopify/create_shopify_metafield_preferences.py` — the restore logic this plan's acceptance criterion 5 exercises; confirms current file already imports `serialize_shopify_metafield_preference` internally (post-correction state) — not directly relevant to a `{}`-returning command, but confirms the router file's current import block shape before editing it.
  - `routers/api_v1/shopify.py` — current route list and import block, to insert the new route/import correctly.
  - `services/commands/issue_types/requests/__init__.py` — `DeleteIssueTypeInput`/`DeleteIssueTypesRequest`/`parse_delete_issue_types_request` exact shape, adapted (not copied) to this plan's flat-list request.

### Skill selection

- Primary skill: none — this follows an existing in-repo pattern closely enough that no new design skill is needed.

## Implementation plan

1. **Request parser** — `services/commands/shopify/requests/delete_shopify_metafield_preferences_request.py`:
   ```python
   class DeleteShopifyMetafieldPreferencesRequest(BaseModel):
       client_ids: list[str] = Field(min_length=1)
   ```
   `parse_delete_shopify_metafield_preferences_request(data: dict) -> DeleteShopifyMetafieldPreferencesRequest`, raising `beyo_manager.errors.validation.ValidationError` on a `PydanticValidationError`, mirroring the exact try/except shape used by `parse_create_shopify_metafield_preferences_request` (same feature, same file's sibling module) rather than `issue_types`' `_raise_validation_error` helper — stay consistent with this feature's own established idiom first. No per-item GID-shape validation (these are this app's own `client_id`s, not Shopify GIDs — no format contract to enforce beyond "non-empty string," same as `DeleteIssueTypeInput.issue_type_id: str`).

2. **Command** — `services/commands/shopify/delete_shopify_metafield_preferences.py`:
   ```python
   async def delete_shopify_metafield_preferences(ctx: ServiceContext) -> dict:
       request = parse_delete_shopify_metafield_preferences_request(ctx.incoming_data)
       requested_ids = set(request.client_ids)
       now = datetime.now(timezone.utc)

       async with maybe_begin(ctx.session):
           result = await ctx.session.execute(
               select(ShopifyMetafieldPreference).where(
                   ShopifyMetafieldPreference.workspace_id == ctx.workspace_id,
                   ShopifyMetafieldPreference.client_id.in_(requested_ids),
                   ShopifyMetafieldPreference.is_deleted.is_(False),
               )
           )
           preferences = result.scalars().all()

           found_ids = {preference.client_id for preference in preferences}
           if found_ids != requested_ids:
               missing_ids = sorted(requested_ids - found_ids)
               raise NotFound(f"Shopify metafield preference(s) not found: {', '.join(missing_ids)}")

           for preference in preferences:
               preference.is_deleted = True
               preference.deleted_at = now
               preference.deleted_by_id = ctx.user_id

       return {}
   ```
   Directly mirrors `delete_issue_types.py`'s shape (set-based dedup, `found_ids != requested_ids` all-or-nothing check, `sorted(...)` for a deterministic error message, mutate-in-place inside one `maybe_begin` block, no explicit `session.add`/`flush` needed since these are already-persistent ORM instances being mutated, not new inserts). Unlike `delete_issue_types`, there is no related-table cleanup step — no other table has a foreign key onto `shopify_metafield_preferences.client_id`, so the loop is the entire body.

3. **Router** — edit `routers/api_v1/shopify.py`:
   ```python
   class ShopifyMetafieldPreferencesDeleteBody(BaseModel):
       client_ids: list[str] = Field(min_length=1)


   @router.delete("/metafield-preferences")
   async def delete_shopify_metafield_preferences_route(
       body: ShopifyMetafieldPreferencesDeleteBody,
       claims: dict = Depends(require_roles([ADMIN, MANAGER, SELLER, WORKER])),
       session: AsyncSession = Depends(get_db),
   ):
       outcome = await run_service(
           delete_shopify_metafield_preferences,
           ServiceContext(identity=claims, incoming_data=body.model_dump(), session=session),
       )
       if not outcome.success:
           return build_err(outcome.error)
       return build_ok(outcome.data)
   ```
   Add the import (`from beyo_manager.services.commands.shopify.delete_shopify_metafield_preferences import delete_shopify_metafield_preferences`), alphabetically grouped with the other `shopify.*` command imports. Place the route directly after `get_shopify_metafield_preferences_route` (group by resource, matching this router's existing organization) — since `DELETE /metafield-preferences` shares no path-parameter ambiguity with any other route (no `{...}` segment at all), there is no route-declaration-ordering concern per `09_routers.md`.

4. **Unit tests**:
   - `tests/unit/services/commands/shopify/test_delete_shopify_metafield_preferences_request.py`: empty `client_ids` rejected (`Field(min_length=1)`); non-list/wrong-type rejected; a valid list of one or several IDs parses correctly; duplicate IDs in the input list are accepted at the parser level (dedup happens in the command via `set(...)`, not rejected here — unlike the create command's duplicate-selection rejection, there is no reason to reject a duplicate delete target).
   - Extend `tests/unit/services/shopify/test_metafield_preference_routes.py`: forwarding test (mocked `run_service`, assert `ctx.incoming_data == body_dict`, assert `response.json()["data"] == {}` on success) and a role-rejection case (mirroring whatever pattern is landed for the create/query routes' own role-rejection tests — check their current state first, since a sibling correction plan may have already added that pattern to this file).

5. **Integration test** — `tests/integration/services/commands/shopify/test_delete_shopify_metafield_preferences.py` (real DB, mirror `test_shopify_admin_commands.py`'s `_seed_workspace_and_user`/`_seed_integration` and a local `_seed_item_category`/`_seed_preference` helper — check whether the sibling test-coverage-correction plan already introduced a reusable `_seed_item_category` helper somewhere in `tests/integration/` before writing a new one):
   - Seed a workspace, user, active shop integration, item category, and 2–3 `ShopifyMetafieldPreference` rows directly (no need to go through the create command or mock Shopify — this command never calls Shopify, so rows can be constructed and flushed directly).
   - Test "batch delete": delete 2 of 3 rows by `client_id`; assert those 2 are `is_deleted=True` with `deleted_at`/`deleted_by_id` set, and the 3rd is untouched.
   - Test "all-or-nothing on one invalid id": request includes one real ID plus one nonexistent ID; assert `NotFound`; re-query and assert the real one is **still not deleted** (the valid one was not partially processed).
   - Test "workspace isolation": a `client_id` belonging to a different workspace's preference row is rejected as not-found (seed a second workspace + preference row); assert the other workspace's row is untouched.
   - Test "already-deleted id rejected" (or "silently no-ops," depending on how the second open clarification resolves): delete a row, then attempt to delete it again by the same `client_id`; assert the documented behavior.
   - Test "delete then recreate restores, doesn't duplicate" (acceptance criterion 5): call `delete_shopify_metafield_preferences` on a row, then call `create_shopify_metafield_preferences` with a selection matching that exact row's `(shop_integration_id, item_category_id, shopify_metafield_definition_id)` (mock `fetch_shopify_metafield_definition_by_id` for this call, same pattern as the sibling command's own tests); assert exactly one row exists afterward with `is_deleted=False` and the *same* `client_id` as before the delete (i.e. it was restored, not recreated as a new row with a new `client_id`).

6. Run `PYTHONPATH=. pytest backend/app/tests/unit/services/commands/shopify/test_delete_shopify_metafield_preferences_request.py backend/app/tests/unit/services/shopify/test_metafield_preference_routes.py -q` and `PYTHONPATH=. pytest backend/app/tests/integration/services/commands/shopify/test_delete_shopify_metafield_preferences.py -m integration -q`. `ruff check` on every new/changed file.

## Risks and mitigations

- Risk: `DELETE` requests with a JSON body are non-standard enough that some HTTP clients, proxies, or API-gateway layers silently strip the body, causing every request to look like "empty `client_ids`" from the backend's point of view even when the frontend sent one correctly.
  Mitigation: this is an accepted, already-working pattern in this exact codebase (`DELETE ""` on `issue_types.py`) — if it works there today in production, the same client stack supports it here. Not a new risk this plan introduces.
- Risk: the "all-or-nothing" default (open clarification 2) turns out to be the wrong UX — a frontend batch-deleting 10 preferences where 1 was already removed by another tab/user would fail the entire batch rather than deleting the other 9.
  Mitigation: flagged as an open clarification with a stated default and a one-line reasoning for why that default was chosen (consistency with the only existing precedent); trivial to change to a partial-success mode later if it proves annoying in practice — not baked in as an irreversible design choice.
- Risk: a future table gets a foreign key onto `shopify_metafield_preferences.client_id` and this command's lack of cascade-cleanup (unlike `delete_issue_types`) becomes a real gap.
  Mitigation: none needed today — no such table exists. Noted here so a future implementer extending this table's relationships knows to revisit this command, not because it's an issue now.

## Validation plan

- `PYTHONPATH=. pytest backend/app/tests/unit/services/commands/shopify/test_delete_shopify_metafield_preferences_request.py -q`
- `PYTHONPATH=. pytest backend/app/tests/unit/services/shopify/test_metafield_preference_routes.py -q`
- `PYTHONPATH=. pytest backend/app/tests/integration/services/commands/shopify/test_delete_shopify_metafield_preferences.py -m integration -q`
- `PYTHONPATH=. pytest backend/app/tests -q` (full suite, no regressions)
- `ruff check` on every new/changed file.

## Review log

- `2026-07-13` `claude`: Plan drafted from user request for a batch delete-by-`client_id` capability, modeled directly on `delete_issue_types.py` (the only existing batch-delete-by-ids precedent in this codebase), adapted to a flat-list request shape and this feature's own role/error idioms. Sequenced to include real integration test coverage from the start, per the lesson from the sibling test-coverage-correction plan.
- `2026-07-13` `codex`: Implemented the flat-list delete parser, workspace-scoped atomic soft-delete command, DELETE route, role/request/integration tests, and delete-then-recreate restoration coverage. Focused tests, integration tests, lint, and migration-head checks passed; full unit validation reported 396 passed and 12 unrelated existing failures.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
