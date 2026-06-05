# HANDOFF_TO_FRONTEND_item_lookup_by_article_number_20260603

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_item_lookup_by_article_number_20260603`
- Created at (UTC): `2026-06-03T00:00:00Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/under_construction/implementation/PLAN_item_lookup_by_article_number_20260603.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_item_lookup_by_article_number_20260603.md`

## Backend delivery context

- What backend implemented:
  - New read-only endpoint that accepts an article number and fans out to multiple item sources in parallel (internal database + Beyo Vintage partner API), returning all matches as a unified list.
  - Results carry an `external_source` discriminator so the frontend can tell where each result came from.
- API or contract changes:
  - `GET /api/v1/items/lookup` — new endpoint, no existing routes changed.
- Feature flags/toggles (if any):
  - The partner API source is silently skipped when `BEYO_VINTAGE_API_KEY` is not set in the backend environment. The endpoint still returns internal DB results normally. The frontend receives no indication that a source was skipped — it simply sees fewer results.

## Frontend action required

1. Add a DTO / type for the unified item lookup result shape (see Interface details).
2. Call `GET /api/v1/items/lookup?article_number=<value>` to pre-fill or resolve an article number before creating or importing an item.
3. Use `external_source` to differentiate results and render them with appropriate context:
   - `null` → item already exists in this workspace's database.
   - `"purchase_api"` → item comes from the Beyo Vintage purchase catalogue (not yet in the workspace).
4. Handle the case where `items` is an empty array — no source found a match for that article number. Do not treat this as an error.
5. Handle the case where `items` contains two entries for the same article number — one from each source. Both are valid and the frontend should surface them (e.g., show an "already exists" badge on the internal result).
6. `images` for internal DB results is always `[]` — the internal item model does not store photo URLs. Do not show an image slot for those entries.
7. `item_category_id` may be `null` even for purchase API results when the external subcategory name has no matching local category. Render gracefully (e.g., "Unknown category").

## Interface details

- Endpoint: `GET /api/v1/items/lookup`
- Auth: Bearer JWT required. Allowed roles: `admin`, `manager`, `seller`. Workers receive HTTP 403.

- Request shape:

| Parameter | Location | Type | Required | Constraints |
|---|---|---|---|---|
| `article_number` | query | string | yes | min length 1, max length 128 |

Example:
```
GET /api/v1/items/lookup?article_number=0000420
```

- Response shape (success):

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "article_number": "0000420",
        "sku": "SKU-001",
        "item_category_id": "itc_01JXABCDEF1234567890ABCDEF",
        "quantity": 2,
        "external_id": null,
        "external_source": null,
        "images": []
      },
      {
        "article_number": "0000420",
        "sku": null,
        "item_category_id": "itc_01JXABCDEF1234567890ABCDEF",
        "quantity": 1,
        "external_id": null,
        "external_source": "purchase_api",
        "images": [
          "https://api.beyovintage.se/uploads/beyo/items/5b1251bd-f842-4e3f-9c0d-93c456107464/photo.jpg"
        ]
      }
    ]
  },
  "warnings": []
}
```

When no source finds a match:

```json
{
  "ok": true,
  "data": {
    "items": []
  },
  "warnings": []
}
```

- Item field reference:

| Field | Type | Notes |
|---|---|---|
| `article_number` | `string` | The matched article number |
| `sku` | `string \| null` | Set for internal DB items; always `null` for `purchase_api` |
| `item_category_id` | `string \| null` | Local `item_categories.client_id`. `null` if no category match was found |
| `quantity` | `number` | Integer ≥ 1 |
| `external_id` | `string \| null` | Reserved for future sources; always `null` currently |
| `external_source` | `"purchase_api" \| null` | `null` = internal DB; `"purchase_api"` = Beyo Vintage catalogue |
| `images` | `string[]` | Fully-qualified URLs ready for `<img src>`. Always `[]` for internal DB results |

- Error cases:

| HTTP | `ok` | Condition |
|---|---|---|
| 422 | `false` | `article_number` query param is missing or empty |
| 422 | `false` | `article_number` exceeds 128 characters |
| 403 | `false` | JWT role is not `admin`, `manager`, or `seller` |
| 401 | `false` | JWT missing or invalid |

Error response shape:

```json
{
  "ok": false,
  "error": "Human-readable message"
}
```

There is **no 404** from this endpoint. A valid request that finds nothing returns HTTP 200 with `items: []`.

## Validation notes

- Backend validation run:
  - Import smoke test passed (no `ImportError` on startup).
  - Route ordering confirmed: `/lookup` resolves before `/{client_id}` in FastAPI's router — the string "lookup" is never mistakenly treated as a client ID.
- Suggested frontend validation:
  - Confirm the DTO handles `items: []` (empty array, not null).
  - Confirm the DTO handles `item_category_id: null` without crashing the category label renderer.
  - Confirm `images: []` renders gracefully (no broken image slot).
  - Test with a `seller` JWT — should receive results (HTTP 200).
  - Test with a `worker` JWT — should receive HTTP 403.

## Trace links

- Parent plan: `backend/docs/architecture/under_construction/implementation/PLAN_item_lookup_by_article_number_20260603.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_item_lookup_by_article_number_20260603.md`
- Related debug plan (optional): `—`
