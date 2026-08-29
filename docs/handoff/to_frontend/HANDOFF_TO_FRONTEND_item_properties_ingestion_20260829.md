# HANDOFF_TO_FRONTEND_item_properties_ingestion_20260829

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_properties_ingestion_20260829`
- Created at (UTC): `2026-08-29T09:45:00Z`
- Owner agent: `Claude`
- Source plan: owner-ratified direct implementation (item-properties ingestion on the write path)
- This is an **addendum** to `HANDOFF_TO_FRONTEND_item_properties_complexity_20260829.md`. That document stays published as written; this one supersedes exactly one sentence in it — see "Correction to the parent handoff" below. Everything else in it, and in every contract it lists as a parent, remains true.

## Correction to the parent handoff

The parent says:

> ingestion from the external app ships separately, so **all signatures are NULL in production until then and every payload is byte-identical to today**

The first half is no longer true as of this change. The write path now accepts a `properties` object, so items can carry a signature as soon as a client starts sending one. The second half still holds: **read payloads are byte-identical until someone actually sends properties**, and none of the read contracts changed here. If no client sends `properties`, nothing about production behaviour differs from the parent handoff's description.

## What changed

Three creation endpoints now accept an optional `properties` object on the item:

| Endpoint | Where |
| --- | --- |
| `PUT /api/v1/tasks` | `item.properties` |
| `PUT /api/v1/items` | `properties` (top level) |
| `POST /api/v1/items/find-or-create` | `properties` (top level) |

`properties` is a free-form JSON object owned by the ingesting app — the backend does not interpret, normalize, or validate its contents beyond requiring that it be an object. From it the backend derives and stores, atomically with the item:

- `properties` — the blob, verbatim,
- `properties_signature` — a SHA-256 over the structurally canonicalized blob,
- `properties_snapshot_at` — when *this profile* was established.

**Never send `properties_signature` or `properties_snapshot_at`.** They are derived server-side and are not accepted as input; a signature that disagrees with its blob would silently mis-group the item's history.

Example:

```json
PUT /api/v1/tasks
{
  "task_type": "pre_order",
  "title": "Carved oak armchair",
  "item": {
    "article_number": "ART-1042",
    "properties": { "wood": "oak", "carving": { "back": "heavy", "legs": "none" } }
  }
}
```

## Rules that will bite if you don't know them

1. **Empty is not a snapshot.** Omitting the key, sending `null`, and sending `{}` are all treated identically: "ingestion had nothing to say". None of them writes, and — critically — **none of them clears an existing profile**. A form that always serializes the whole item object cannot wipe an item's properties just by defaulting the field. There is deliberately no way to un-snapshot an item through these endpoints.
2. **Values are compared verbatim; only key order is canonicalized.** `{"wood":"oak"}` and `{"wood":"Oak"}` are two different profiles. So are `90` and `"90"`, and so are `["wax","stain"]` and `["stain","wax"]` — list order is significant. Semantic normalization (casing, units, synonyms) is the ingesting app's job, not the backend's. Reordering object keys is safe.
3. **Re-sending the same profile is a no-op.** On the link path (`PUT /api/v1/tasks` or find-or-create matching an existing item by `article_number`/`sku`), an incoming profile whose signature equals the stored one writes nothing at all — `properties_snapshot_at` keeps meaning "when this profile was established", not "when ingestion last spoke".
4. **A changed profile re-snapshots the item, and that regroups its history.** This is intended, and matches the "no versioning by design" note in the parent handoff: after a re-snapshot, the item's typical times resolve against the *new* signature's cohort, so a read before and a read after may legitimately differ.
5. **Linking updates the item globally.** Sending `properties` alongside an `article_number` that matches an existing item mutates that item for every task it is attached to, not just the one being created. That is how every other field on this path already behaves; properties is not special.

## Frontend action required

**None is forced.** `properties` is optional everywhere and omitting it preserves today's behaviour exactly.

If you are the surface that ingests item properties:

1. Send the object under `item.properties` (tasks) or `properties` (items) at creation time.
2. Send `null`/omit rather than `{}` when you have nothing — though all three behave the same, omitting states the intent.
3. Do not round-trip a previously-read blob through a normalizing layer that reorders lists or changes value casing; it would read as a new profile and regroup the item's history.

Widening the read-side enums described in the parent handoff becomes load-bearing once you start sending properties — `typical_basis` can now genuinely return `item_properties_narrowed` in production.

## Not in this change

- No read endpoint exposes `properties`, `properties_signature`, or `properties_snapshot_at` yet. They are write-only from the client's point of view.
- `PATCH`/update-item does **not** accept `properties`. Re-snapshotting today happens only through the three creation endpoints above.
- No new endpoint, flag, event, or socket.

## Validation notes

- Backend: 24 new tests (13 unit over the snapshot helper, 11 integration across all three write paths). Mutation-tested — nine mutants covering "helper never writes", "empty treated as a real snapshot", "unchanged signature still rewrites", "signature not derived from the blob", "timestamp never recorded", and each of the four call sites dropping the payload; **all nine were caught, no survivors**.
- Regression: `tests/unit` and the items + tasks command integration suites show only pre-existing failures, each verified to fail identically on a clean HEAD (`test_items_router.py` ×2, `test_batch_update_item_positions_integration.py` ×2, plus the standing unit baseline).
- Migration `b9d0e1f2a3c4` (the three columns and their indexes) must be applied before this ships.

## Trace links

- Parent (partially corrected above): `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_properties_complexity_20260829.md`
- Signature definition: `app/beyo_manager/domain/items/properties_signature.py`
- Write-path helper (single owner of the three columns): `app/beyo_manager/services/commands/items/_properties_snapshot.py`
