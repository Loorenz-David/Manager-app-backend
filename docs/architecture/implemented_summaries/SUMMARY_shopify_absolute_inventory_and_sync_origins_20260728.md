# Shopify Absolute Inventory and Product-Sync Origins

## Delivered behavior

- Every supplied Shopify location quantity is authoritative and absolute. The worker enables
  tracking, activates a missing level, and batches `inventorySetQuantities(name: "available")`.
- Quantity `0` is preserved and clears the selected location. Omitted locations are untouched.
- The sync-item ID supplies the stable Shopify idempotency key on retries.
- `inventoryAdjustQuantities` and the additive ledger service are no longer runtime code. The
  `shopify_inventory_adjustments` table and its model remain for read-only historical audit.
- Product creation/update remains one shared command/worker pipeline.
- Each row persists `sync_origin`, `source_entity_type`, and `source_entity_id` at enqueue time:
  standard requests use `standard_product_sync`; pre-orders use `preorder_task`, `task`, and the
  ManagerBeyo task ID.
- Completion audit events and socket events dispatch from `sync_origin`, never inventory mode.
  An unknown origin fails the entire batch before any Shopify mutation so a compatible worker can
  retry it after deployment.

## Compatibility bridge

- The HTTP boundary accepts `inventory_quantities[].quantity` canonically.
- For one release it also accepts `inventory_adjustments[].quantity_to_add`, interprets the value
  as absolute, rejects mixed shapes, and emits a structured deprecation warning.
- The worker converts any missed persisted legacy `inventory.adjustments` payload to canonical
  quantities before execution and never runs an additive mutation.
- Frontend form/wire state uses quantities, preserves selected zero values, migrates version-one
  local drafts, and accepts both historical `adjustments` and canonical `quantities` socket
  results.

## Migration and deployment order

1. Gracefully stop the Shopify worker and let its in-flight task rescue logic requeue active
   `SHOPIFY_PROCESS_PRODUCTS` work.
2. Apply migration `d8e4f1a2c6b7`. It adds origin/source columns, backfills pre-orders from
   PREORDER events or matching PRE_ORDER tasks, converts unfinished legacy payloads, and changes
   the compatibility `inventory_mode` default to `set`.
3. Deploy the backend and frontend from the same release, then restart the Shopify worker.
4. Monitor `deprecated_inventory_request_converted`,
   `legacy_persisted_inventory_converted`, `unknown_sync_origin`,
   `inventory_location_invalid`, and Shopify inventory user errors.
5. After one stable release with zero legacy conversions, remove the legacy HTTP/result bridge,
   `inventory_mode`, its PostgreSQL enum, and unused additive runtime enums/models. Preserve the
   historical ledger table.

Do not run step 2 while an old Shopify worker can still claim work: old code can interpret legacy
fields additively and does not understand the new origin contract.

## Verification

- Backend focused unit tests: 104 passed, including migration-contract coverage.
- Backend Shopify unit slice: 344 passed; two unrelated pre-existing dimension-migration
  assertions still fail on `extensions_quantity: "0"`.
- Focused PostgreSQL integration tests: 18 passed.
- Alembic downgrade/upgrade cycle: passed. `alembic check` reports only pre-existing unrelated
  drift in email-sync and step-state indexes.
- Frontend Shopify suite: 35 files and 103 tests passed.
- Shopify and realtime TypeScript checks: passed.
- Changed backend files pass Ruff.

No live merchant Shopify mutation was run in this implementation pass.
