# PLAN_shopify_dimension_migration_20260714

## Metadata

- Plan ID: `PLAN_shopify_dimension_migration_20260714`
- Status: `archived`
- Owner agent: `claude`
- Created at (UTC): `2026-07-14T00:00:00Z`
- Last updated at (UTC): `2026-07-14T12:12:11Z`
- Related issue/ticket: `n/a`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_shopify_dimension_migration_20260714.md`

## Goal and intent

- Goal: Add a standalone, manually-run script (`app/scripts/backfill/migrate_shopify_dimensions.py`) that migrates legacy free-text Shopify product dimension metafields (`height`, `width`, `depth`) into the new structured metafields (`height_dimension`, `width_dimension`, `depth_dimension`, `extensions_quantity`, `extension_dimension`), while reading legacy `extension_quantity`, normalized to centimeters, with a mandatory reviewable dry run before any Shopify write.
- Business/user intent: ~5,000 products currently carry inconsistent legacy dimension text. The target structured metafield definitions already exist in Shopify but are unpopulated. The business needs this backfilled safely and observably, without guessing on ambiguous legacy data, and without building new recurring infrastructure.
- Non-goals: deleting legacy metafields/definitions, altering themes, updating frontend forms, a new HTTP endpoint, a scheduled/recurring job, a generic Shopify Bulk Operations framework.

## Scope

- In scope:
  - A pure parsing/decision domain module (`domain/shopify/dimension_migration.py`).
  - A new Shopify infra client for this migration's specific GraphQL needs (`services/infra/shopify/dimension_migration_client.py`).
  - One new query function to resolve the active integration by shop domain (`services/queries/shopify/get_active_shopify_integration_by_domain.py`).
  - The Typer CLI script itself, dry-run and execute modes, preflight validation, reports, verification phase.
  - Unit tests for parsing/decision logic and the infra client (mocked transport — no live Shopify calls).
- Out of scope: any change to `product_sync_client.py`'s existing `set_shopify_product_metafields` (namespace-hardcoded, used by the live product-create/update flow — left untouched), any DB schema/migration (no new tables — Shopify itself plus the run's own reports are the source of truth), any change to `shopify_worker.py`/`HANDLER_MAP` (this never touches the task-queue system per contract [57_shopify_integration.md](../../../../architecture/57_shopify_integration.md)'s "never call Shopify's API inline from an HTTP request handler" rule — moot here since there is no HTTP request at all, this is an offline terminal script).
- Assumptions (see also "Clarifications required"): the real source namespace/keys for legacy `height`/`width`/`depth` are not yet confirmed against the live store and must be discovered during the first `--dry-run`; target definitions' Shopify-side `validations` (min/max) are unknown until queried live.

## Clarifications required

- [ ] Exact source namespace + keys for legacy `height`/`width`/`depth` in the live store — blocks producing a meaningful first dry run; mitigated by making them required CLI options with no hardcoded default guess.
- [ ] Whether `extension_dimension` should be **deleted** when a rerun finds zero extensions where a stale value previously existed — decided below as "gate deletion behind `--overwrite-existing`," but this is a judgment call the user should confirm before `--execute` is ever run for real.
- [ ] Whether the store's target metafield definitions currently have Shopify `validations` (min/max) configured — affects whether local pre-validation against limits is exercised at all on the first run.

## Acceptance criteria

1. `python -m app.scripts.backfill.migrate_shopify_dimensions --shop-domain <domain> --dry-run --limit 100` performs zero Shopify mutations, and produces `summary_<ts>.json`, `products_<ts>.csv`, `invalid_<ts>.csv`, and `proposed_mutations_<ts>.jsonl` under `migration_reports/shopify_dimensions/`.
2. Running without either `--dry-run` or `--execute` exits non-zero before any Shopify call (ambiguous invocation rejected).
3. `--execute` refuses to proceed (exits non-zero, zero mutations) if target metafield definitions are missing, have the wrong Shopify type, or `--confirm-shop-domain` does not match `--shop-domain`.
4. A product whose existing target metafield already holds a non-empty value is never overwritten unless `--overwrite-existing` is passed; dry run always reports each product's action as one of `created`/`skipped_existing`/`overwritten`/`rejected`/`unchanged`.
5. Width values with inconsistent extension sizes (e.g. `100 + 50 + 40`) never produce a written `width_dimension`/`extension_*` for that product — they are reported as `invalid` with the original value and reason, never guessed/averaged/summed.
6. After `--execute`, a verification pass re-queries Shopify and a product is only counted `migrated` once its written values are confirmed to match the proposed values; the run's final summary reports `proposed`/`written`/`verified`/`already_correct`/`no_legacy_value`/`skipped`/`invalid`/`conflicting_target`/`mutation_failed`/`verification_failed` counts. A product whose requested legacy fields are all absent (no metafield present at all, as opposed to malformed text) is counted under `no_legacy_value`, never under `invalid`.
7. No log line at any level ever contains the decrypted access token, an authorization header, or `FIELD_ENCRYPTION_KEY`.
8. `pytest app/tests/unit/domain/shopify/test_dimension_migration.py app/tests/unit/services/infra/shopify/test_dimension_migration_client.py app/tests/unit/scripts/test_migrate_shopify_dimensions.py` passes with no network access required.

## Contracts and skills

### Contracts loaded

- [`architecture/27_cli_scripts.md`](../../../../architecture/27_cli_scripts.md): governs script location/structure, mandatory `--dry-run`, idempotency, batching, progress output — but this repo's actual scripts (`app/scripts/backfill/cleanup_expired_uploads.py`) use `argparse`+plain functions rather than the contract's `typer.Typer()` example; per the "pattern vs relational" test below, the **contract wins** for a brand-new script, not the pre-existing non-compliant file (see Risks).
- [`architecture/53_operational_cli.md`](../../../../architecture/53_operational_cli.md): mandates Typer, explicit command groups (`backfill`), `--dry-run`/`--confirm` safeguards for destructive/irreversible operations, structured start/end log events, non-interactive/deterministic execution — directly shapes the `--dry-run`/`--execute`/`--confirm-shop-domain` CLI surface below.
- [`architecture/17_logging.md`](../../../../architecture/17_logging.md): `logging.getLogger(__name__)` per module, `INFO` for normal ops, `WARNING` for expected/handled failures, structured `key=value` fields, external-call latency logging, and the explicit "never log raw third-party responses / secrets" rule — directly governs the "never log the decrypted token" requirement.
- [`architecture/19_integrations.md`](../../../../architecture/19_integrations.md): adapter pattern (`services/infra/<integration>/`), explicit timeouts on every external call, mapper pattern (raw GraphQL response never passed to domain code un-mapped) — the new `dimension_migration_client.py` maps raw product/metafield nodes into plain dicts before handing them to the pure domain module.
- [`architecture/57_shopify_integration.md`](../../../../architecture/57_shopify_integration.md): the authoritative map of existing Shopify file structure/conventions (`services/infra/shopify/graphql_client.py` transport, `access_token_encrypted` handling, `ShopifyShopIntegration` model, `metafield_definition_client.py`) — read for **what exists**, not copied as a new webhook/task-queue flow (this script deliberately bypasses the worker/queue layer, which is correct here since it is not triggered by any webhook or admin route).
- [`architecture/05_errors.md`](../../../../architecture/05_errors.md): reuse of `ShopifyGraphQLRetryableError`/`ShopifyGraphQLNonRetryableError` (`app/beyo_manager/errors/external_service.py`) for the script's own retry-vs-abort branching, rather than inventing new exception types.

### Local extensions loaded

- None found specific to Shopify scripts (`27_cli_scripts_local.md` does not exist) — the base contract applies unmodified.

### File read intent — pattern vs. relational

- **How to write** (contract, not code, is the reference): CLI structure → `27_cli_scripts.md`/`53_operational_cli.md`; logging format → `17_logging.md`; retry/timeout shape → `19_integrations.md`.
- **What exists** (legitimate direct reads, already performed during investigation): `graphql_client.py` (transport signature/error classes), `product_sync_client.py` (existing `SET_METAFIELDS_MUTATION` string and why it can't be reused as-is — namespace hardcoded), `metafield_definition_client.py` (existing paginated definition fetch to reuse), `shopify_shop_integration.py` (exact columns/indexes), `field_encryption.py` (decrypt boundary), `config.py` (env/settings access), `app/scripts/backfill/cleanup_expired_uploads.py` (existing script's actual shape, for contrast with the contract).

### Skill selection

- Primary skill: none required — this is a backend Python implementation plan, not a UI/dataviz/config task.
- Router trigger terms: n/a
- Excluded alternatives: n/a

## Implementation plan

1. **Domain module** — `app/beyo_manager/domain/shopify/dimension_migration.py` (pure, no Shopify/DB imports, `Decimal`-based):
   - `parse_dimension_to_centimeters(raw: str | None) -> ParsedDimension | ParsedInvalid | ParsedMissing`: a source metafield that does not exist at all (Shopify returns `null` for that aliased field — the product simply never had that dimension recorded) or is present but blank/whitespace-only is **not** the same outcome as malformed text. `None`/empty/whitespace-only input short-circuits to `ParsedMissing` *before* any numeric parsing is attempted; only a genuinely non-empty-but-unparseable string (`N/A`, `100-120`, `100 x 50`, etc.) becomes `ParsedInvalid`. This distinction matters because the intention doc requires "products with no legacy values" to be counted and reported separately from "products rejected" — a product that never had a width recorded is not a data-quality problem, it's simply nothing to migrate for that field.
   - `parse_width_and_extensions(raw: str) -> ParsedWidthWithExtensions | ParsedInvalid`: splits on `+`, parses each part via `parse_dimension_to_centimeters`, first part = base width, remaining parts must all normalize to the **same** centimeter value (else `ParsedInvalid` with reason `"inconsistent_extension_dimensions"`); zero remaining parts → `extension_quantity=0`, `extension_dimension=None`.
   - `serialize_shopify_dimension(value_cm: Decimal) -> str`: emits exactly `'{"value":100,"unit":"CENTIMETERS"}'` (integer-looking values unquoted per Shopify's `dimension` scalar JSON shape; `json.dumps({"value": ..., "unit": "CENTIMETERS"}, separators=(",", ":"))` with the numeric value coerced to `int` when it has no fractional part, else `float`).
   - `build_product_migration(input: ProductMigrationInput, *, config: MigrationConfig) -> ProductMigrationDecision`: parses height/width/depth independently. A `ParsedMissing` field is treated as "nothing to do for this field" — it is skipped silently (contributes to a `no_legacy_value` counter, not to `invalid`/`rejected`) and, critically, **does not** trigger strict-product-mode's skip-the-whole-product rule, since there is no bad data to strict-mode against. Strict-product-mode (default **on** per the intention doc) only fires on `ParsedInvalid` fields — if any requested field is genuinely malformed, the whole product is skipped with per-field reasons recorded, no partial writes. (A product where every requested field resolves to `ParsedMissing` simply has nothing proposed at all — it is counted as a "no legacy values" product and does not appear in `invalid_<ts>.csv`.) Existing-target protection is a three-way comparison per field, not a binary populated/empty check — this is what makes reruns idempotent rather than merely "safe":
     - existing target **empty** → action `created`;
     - existing target **non-empty and equal** to the newly parsed/serialized value → action `unchanged` (`already_correct`; no mutation sent — a rerun over already-migrated products must not re-send an identical `metafieldsSet` call);
     - existing target **non-empty and different** → action `target_already_populated`/`conflicting_target` unless `--overwrite-existing`, in which case action `overwritten`.
     Stale `extension_dimension` cleanup follows the same rule: a delete is only proposed when the new parsed result has zero extensions, an existing non-empty `extension_dimension` value is present, **and** `--overwrite-existing` is set (deletion is itself an overwrite, so it is never implied by the empty-extensions case alone) — otherwise it is reported for manual review, never deleted.
   - Dataclasses: `ParsedDimension(value_cm: Decimal)`, `ParsedInvalid(reason: str)`, `ParsedMissing()` (sentinel, no payload), `ParsedWidthWithExtensions(base_cm: Decimal, extension_quantity: int, extension_cm: Decimal | None)`, `ProductMigrationInput` (gid, title, handle, sku, raw legacy values, existing target values), `ProductMigrationDecision` (per-field actions + overall status + reasons), `MigrationSummary` (all the counters from Acceptance Criterion 6, including `no_legacy_value`).

2. **Target-definition validation + product/metafield fetch** — `app/beyo_manager/services/infra/shopify/dimension_migration_client.py`:
   - `async def fetch_target_metafield_definitions(*, shop_domain, access_token_encrypted, target_namespace, target_keys) -> dict[str, dict | None]`: reuses `metafield_definition_client.fetch_shopify_product_metafield_definitions_page` (existing cursor-pagination loop) filtering nodes where `namespace == target_namespace and key in target_keys` (mirroring `get_shopify_metafield_preferences.py::_is_product_metafield_definition`'s `ownerType == "PRODUCT"` check). Parses each definition's `validations` (name/value pairs) into a `{"min": Decimal | None, "max": Decimal | None}` shape for later local pre-validation.
   - `PRODUCT_DIMENSION_PAGE_QUERY`: a new paginated `products(first:, after:)` query (none exists yet anywhere in the codebase — confirmed) that aliases exactly the required metafields per product: `legacyHeight: metafield(namespace: $sourceNamespace, key: $sourceHeightKey) { value }` (and width/depth), plus `existingHeight: metafield(namespace: $targetNamespace, key: $targetHeightKey) { value }` (and the other four targets), `title`, `handle`, `variants(first: 1) { edges { node { sku } } }`. This satisfies "query only required metafields" without a bulk operation. Page size starts at 50 and the client reads Shopify's per-request query-cost extension (if present in the raw HTTP response) to shrink the page size on a `MAX_COST_EXCEEDED`-style error rather than hardcoding a single fixed page size.
   - `async def set_dimension_metafields_batch(...)`: imports the existing `SET_METAFIELDS_MUTATION` string from `product_sync_client.py` (not the hardcoded-namespace `set_shopify_product_metafields` function) and builds `MetafieldsSetInput` entries itself with the configurable `target_namespace`, batching up to 25 entries per call (Shopify's documented `metafieldsSet` limit) potentially spanning multiple products in one call; calls the existing `raise_for_graphql_user_errors`, and additionally maps each returned `userErrors[].field` index back to the originating `(product_gid, key)` pair for per-row reporting.
   - `async def delete_stale_extension_dimension_batch(...)`: new `metafieldsDelete` mutation (none exists yet) using `MetafieldIdentifierInput { ownerId, namespace, key }`, only ever called for rows the domain module marked as `delete_stale_extension` (which — per the decision above — only happens when `--overwrite-existing` is set).
   - All calls go through the existing `execute_shopify_graphql` transport unchanged; the client wraps each call in the script's own bounded exponential backoff (max 5 attempts, base 1s, capped at 30s) that retries only on `ShopifyGraphQLRetryableError`, re-raising immediately on `ShopifyGraphQLNonRetryableError` — since `graphql_client.py` itself has no retry loop today (confirmed), this is new code, not a duplicate of existing retry logic.

3. **Active integration lookup** — `app/beyo_manager/services/queries/shopify/get_active_shopify_integration_by_domain.py`:
   - `async def get_active_shopify_integration_by_domain(session: AsyncSession, shop_domain: str) -> ShopifyShopIntegration | None`, filtering `shop_domain == ..., is_deleted.is_(False), status == ShopifyIntegrationStatusEnum.ACTIVE` — modeled on `handle_shopify_process_products.py`'s strict-ACTIVE check and `_linking.py::_active_conflict_stmt`'s domain-only filter (no existing single function does exactly this by domain alone, confirmed). The domain-scoped partial unique index on `shopify_shop_integrations` guarantees at most one row.

4. **CLI entrypoint** — `app/scripts/backfill/migrate_shopify_dimensions.py`, Typer-based per `27_cli_scripts.md`/`53_operational_cli.md` (not argparse — see Risks for why this departs from `cleanup_expired_uploads.py`'s shape):
   - Command group `backfill migrate-shopify-dimensions` with options: `--shop-domain` (required), `--source-namespace`, `--source-height-key`, `--source-width-key`, `--source-depth-key` (all required, no guessed defaults), `--target-namespace` (default `custom`), `--dry-run`/`--execute` (mutually exclusive, exactly one required — reject ambiguous invocation), `--limit` (applies to products *processed*, enforced by stopping the paginated fetch generator once `limit` products have been yielded, not just capping page count), `--overwrite-existing` (default off), `--strict-product/--no-strict-product` (default strict), `--report-directory` (default `migration_reports/shopify_dimensions/`), `--confirm-shop-domain` (required with `--execute`, must string-match `--shop-domain`), `--log-level`.
   - Preflight (logged and printed before any product processing): resolve integration via step 3's query, decrypt boundary untouched (only `graphql_client.py` calls `decrypt_field`, per existing boundary — the script never calls it directly), validate target definitions via step 2's function and abort with a non-zero exit before any product fetch if a definition is missing/wrong-type.
   - Main loop: stream pages from `PRODUCT_DIMENSION_PAGE_QUERY`, stop once `--limit` products have been yielded (deterministic order via Shopify's default `id` sort, so repeated dry runs see the same first N), call `build_product_migration` per product, accumulate `ProductMigrationDecision`s, batch the resulting `set_dimension_metafields_batch`/`delete_stale_extension_dimension_batch` calls only when `--execute` (never in `--dry-run`).
   - Reports: `write_reports(...)` emits `summary_<ts>.json`, `products_<ts>.csv` (columns exactly as listed in the intention doc), `invalid_<ts>.csv`, and — dry-run only — `proposed_mutations_<ts>.jsonl`, or — execute only — `mutation_errors_<ts>.csv`. No existing CSV/JSONL helper exists in the codebase (confirmed) — plain stdlib `csv`/`json`.
   - Exit codes: non-zero on preflight failure, non-zero if any mutation error occurred (unless `--allow-partial-success`), non-zero on report-write failure — per Acceptance Criteria 2–3.

5. **Verification phase** (execute mode only): after all batches complete, re-fetch the same products via step 2's query and compare each written field against the proposed value; a product only counts as `verified`/fully migrated once this matches (Acceptance Criterion 6).

6. **Tests**:
   - `app/tests/unit/domain/shopify/test_dimension_migration.py`: the full parsing matrix from the intention doc (valid: `100`, `100cm`, `100 cm`, `100.5cm`, `100,5 cm`, `1m`, `500mm`, `100cm + 50cm`, `100cm + 50cm + 50cm`, `1m + 500mm + 500mm`; invalid: empty, `N/A`, `100-120`, `100 x 50`, `100 + 50 + 40`, `100 + bad`, negatives, disallowed zero, above-max) plus the target-protection matrix (absent/matches/differs × overwrite on/off) and the exact serialization strings (`{"value":100,"unit":"CENTIMETERS"}`, `"2"`), following the existing `test_metafield_preferences.py`/`test_product_sync_payloads.py` style (plain `pytest`, no async needed — pure functions).
   - `app/tests/unit/services/infra/shopify/test_dimension_migration_client.py`: `monkeypatch.setattr(dimension_migration_client, "execute_shopify_graphql", _fake_execute_shopify_graphql)` exactly like `test_product_sync_client.py`, asserting the exact `variables`/mutation strings sent for `metafieldsSet`/`metafieldsDelete`, and the retry-backoff behavior on a simulated `ShopifyGraphQLRetryableError`.
   - `app/tests/unit/scripts/test_migrate_shopify_dimensions.py` (new directory — no prior test coverage exists for anything under `app/scripts/`, confirmed): CLI argument validation (ambiguous dry-run/execute rejected, `--confirm-shop-domain` mismatch rejected), report-writing given a canned list of `ProductMigrationDecision`s, using Typer's `CliRunner`.

## Risks and mitigations

- Risk: `27_cli_scripts.md`/`53_operational_cli.md` mandate Typer, but the one existing precedent script (`app/scripts/backfill/cleanup_expired_uploads.py`) uses `argparse` and is not contract-compliant.
  Mitigation: follow the contracts (Typer) for this new script per the plan template's own "pattern vs relational" rule — contracts describe how to write new code; an old non-compliant script is not a reason to repeat the deviation. Flagged here for reviewer visibility, not silently resolved.
- Risk: Shopify GraphQL query-cost limits could make the 8-aliased-metafields-per-product page query more expensive per node than existing paginated queries in this codebase (which only page metafield *definitions*, not products with nested metafields).
  Mitigation: start with a conservative page size (50) and shrink it dynamically on a Shopify cost-related throttle error, per step 2 above; this is a genuinely new capability being added, not a duplicate of `metafield_definition_client.py`'s definition pager.
- Risk: `metafieldsSet`'s `userErrors` for a batched, multi-product call must be correctly correlated back to the originating product/key by array index — getting this wrong would misattribute errors in reports.
  Mitigation: unit-test this mapping explicitly against a canned multi-error response in `test_dimension_migration_client.py`.
- Risk: real source namespace/keys and target `validations` are unconfirmed against live store data (see Clarifications).
  Mitigation: the first invocation is always `--dry-run --limit 100`; nothing above assumes real data shape beyond what's already visible in Shopify's definition metadata, which is queried live during preflight.
- Risk: deleting `extension_dimension` is destructive even though gated by `--overwrite-existing` (a flag whose name suggests "overwrite," not "delete").
  Mitigation: this exact behavior (explicit cleanup only under `--overwrite-existing`) is called out as an open clarification above and must be confirmed by the user before the first real `--execute` run against production data — the plan does not treat this as fully resolved.

## Validation plan

- `pytest app/tests/unit/domain/shopify/test_dimension_migration.py -v`: full parsing/decision matrix passes, zero network access.
- `pytest app/tests/unit/services/infra/shopify/test_dimension_migration_client.py -v`: mocked-transport assertions on exact GraphQL variables/queries and retry behavior.
- `pytest app/tests/unit/scripts/test_migrate_shopify_dimensions.py -v`: CLI validation + report-writing, via Typer's `CliRunner`.
- Manual dry run against a real (non-production or carefully chosen production) shop: `PYTHONPATH=. APP_ENV=production python -m app.scripts.backfill.migrate_shopify_dimensions --shop-domain <domain> --source-namespace <ns> --source-height-key <key> --source-width-key <key> --source-depth-key <key> --dry-run --limit 100`, then manually review `products_<ts>.csv`, `invalid_<ts>.csv`, and `proposed_mutations_<ts>.jsonl` before ever running `--execute`.
- Confirm no log line at any level contains the string `access_token` value itself (grep the run's captured log output for the known encrypted/decrypted token value as a smoke check).

## Review log

- `2026-07-14` `claude`: initial plan drafted from the user-supplied intention plan and direct inspection of `graphql_client.py`, `product_sync_client.py`, `metafield_definition_client.py`, `shopify_shop_integration.py`, `field_encryption.py`, `config.py`, `app/scripts/backfill/cleanup_expired_uploads.py`, and contracts `27_cli_scripts.md`/`53_operational_cli.md`/`17_logging.md`/`19_integrations.md`/`57_shopify_integration.md`/`05_errors.md`.
- `2026-07-14` `codex`: implemented the pure parser/decision module, Shopify dimension migration client, active-integration query, Typer backfill CLI, reports, verification pass, and focused unit tests. Validation passed locally; no live Shopify call was made.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `Codex`
- Summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_shopify_dimension_migration_20260714.md`
- Archive record: `backend/docs/architecture/archives/implementation/ARCHIVE_RECORD_PLAN_shopify_dimension_migration_20260714.md`
