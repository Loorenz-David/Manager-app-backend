# PURCHASE_API_ITEM_ATTRIBUTES_LOOKUP_FOR_JS_20260831

Porting notes for implementing the purchase-API item lookup in a Node/JS app,
scoped to what that app actually needs: fetching an item by article number and
extracting its `attributes` into a plain properties object. Everything else
the Python backend does with the response (category matching, price
normalization, quantity, images) is out of scope here and not described.

Python reference: `app/beyo_manager/services/queries/items/lookup/purchase_api.py`

## 1. Env var

Define one env var in the JS app to hold the partner API key:

```
BEYO_VINTAGE_API_KEY=<the key>
```

(Same name as the Python backend uses, for consistency across the two apps —
not a requirement, just avoids confusion if anyone compares configs.)

## 2. Making the request

```
GET https://api.beyovintage.se/api/partner/items/{articleNumber}
Header: X-Partner-Key: <BEYO_VINTAGE_API_KEY>
```

- URI-encode `articleNumber` when building the path (`encodeURIComponent`,
  equivalent to Python's `quote(article_number, safe='')`) — it can contain
  characters that aren't URL-safe.
- Use a request timeout; the Python side uses 8s total / 3s connect.

### Status codes to handle

| Status | Meaning | Action |
| --- | --- | --- |
| 200 | OK | parse body (see below) |
| 404 | No item for that article number | treat as "not found", not an error |
| 401 / 403 | Bad or missing API key | log/report as a config problem, don't retry |
| 400 | Article number is invalid/unsupported format | treat as "not found" |
| 503 | Partner API not configured on the remote server | treat as temporarily unavailable |
| anything else non-2xx | Unexpected | throw/surface as an error |

### Response envelope

```json
{ "success": true, "data": { ... }, "error": null }
```

If `success` is `false`, there is no usable data — treat the same as "not
found" (the Python side logs `body.error` and returns nothing).

## 3. The field you need: `data.attributes`

`data.attributes` is a **JSON-encoded string**, not a JSON array/object
directly, e.g.:

```
"[{\"key\":\"wood_type\",\"label\":\"Type of Wood\",\"value\":\"Teak\"}]"
```

It needs to be `JSON.parse`d, then projected into a plain object keyed by
`key`, e.g. `{ "wood_type": "Teak" }`. `label` is display text owned by the
purchase app and is **deliberately dropped** — folding it in would mean a
purely cosmetic rename upstream changes the stored value.

### Parsing rules (port of `parse_purchase_api_attributes` / `has_attributes_payload`)

1. **No payload → empty object `{}`.** Treat `attributes` as "nothing to
   report" when it is: `undefined`/`null`, an empty string `""`, the literal
   string `"[]"`, or an empty array `[]`. Be defensive about the type — code
   defensively against the field ever arriving as an already-parsed
   array/object rather than a string, though today it's always a string.
2. **Malformed JSON → empty object, log a warning, don't throw.** A bad
   attributes blob must not cost you the rest of the item lookup.
3. **Decoded value must be a list.** If `JSON.parse` succeeds but the result
   isn't an array, log a warning and treat as empty.
4. **Skip non-object entries** in the list (log a warning).
5. **Key**: `String(entry.key ?? "").trim()`. Skip the entry if this is empty
   (log a warning).
6. **Dedup by key, keep the first occurrence.** If a key repeats, skip the
   later entry (log a warning) rather than overwriting.
7. **Value**: skip the entry if `entry.value` is `null`/`undefined`, or is a
   string that is blank after trimming. Otherwise store it — trim it if it's
   a string, store as-is otherwise (numbers, booleans, etc. pass through
   unchanged).
8. Order of the resulting object's keys doesn't matter for storage purposes.

### JS sketch

```js
function hasAttributesPayload(raw) {
  if (typeof raw === "string") return raw.trim() !== "" && raw.trim() !== "[]";
  if (Array.isArray(raw)) return raw.length > 0;
  return raw !== null && raw !== undefined;
}

function parsePurchaseApiAttributes(raw) {
  if (!hasAttributesPayload(raw)) return {};

  let decoded = raw;
  if (typeof raw === "string") {
    try {
      decoded = JSON.parse(raw);
    } catch {
      console.warn("Purchase API sent attributes that are not valid JSON:", raw);
      return {};
    }
  }

  if (!Array.isArray(decoded)) {
    console.warn("Purchase API sent attributes that are not a list:", decoded);
    return {};
  }

  const properties = {};
  for (const entry of decoded) {
    if (typeof entry !== "object" || entry === null || Array.isArray(entry)) {
      console.warn("Skipping a non-object attributes entry:", entry);
      continue;
    }

    const key = String(entry.key ?? "").trim();
    if (!key) {
      console.warn("Skipping an attributes entry with no key:", entry);
      continue;
    }
    if (key in properties) {
      console.warn(`Skipping a duplicate attributes key "${key}"; keeping the first value`);
      continue;
    }

    const value = entry.value;
    if (value === null || value === undefined) continue;
    if (typeof value === "string" && value.trim() === "") continue;

    properties[key] = typeof value === "string" ? value.trim() : value;
  }

  return properties;
}
```

## 4. What this app should store

Just the resulting object (e.g. `{"wood_type": "Teak"}`), the same free-form
shape the Python backend's `properties` field expects on its write path
(`app/beyo_manager/services/commands/items/_properties_snapshot.py` /
`docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_properties_ingestion_20260829.md`).
An empty object `{}` from step 3 above should be stored/sent as "no
attributes" (omit or send `{}`/`null`, all equivalent on the receiving end) —
never invent placeholder values.

## Not covered here

- Category/subcategory matching, price currency normalization, image URL
  handling, quantity — none of these are needed for the attributes-only use
  case and are intentionally left out. See the Python reference file if a
  future need requires them.
