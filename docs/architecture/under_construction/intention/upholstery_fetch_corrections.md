Intention Plan: Expand Fargotex Fabric Search Results into Upholstery Variants

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/infra/upholstery_providers/fargotex.py

1. Objective

Correct the Fargotex external upholstery provider so that a search for a fabric collection does not return only the parent WooCommerce product.

When a matching Fargotex product is found, the provider should inspect that product’s detail page, extract its WooCommerce variations, and return each valid upholstery variation as an independent external upholstery candidate.

For example, a search matching Neon should return its individual colors rather than only the parent Neon product.

⸻

2. Current Behavior

The current Fargotex integration:

1. Requests the Fargotex upholstery category pages.
2. Parses each product card from the category listing.
3. Matches the query against the parent product information.
4. Normalizes and returns the parent product candidate.

This works for locating fabric collections, but category listing cards do not contain the complete WooCommerce variation data.

As a result, a product such as Neon is returned only once even though its product page contains several upholstery color variants.

⸻

3. Source of Variant Data

Fargotex exposes WooCommerce variation data on each variable product page through the following HTML attribute:

<form
    class="variations_form cart"
    data-product_variations="[...]"
>

The data-product_variations value contains an HTML-encoded JSON array.

Each variation may include:

* variation_id
* sku
* attributes
* image
* variation_is_active
* variation_is_visible
* stock and availability information

The color value is currently represented by an attribute such as:

{
  "attribute_pa_kolory": "antracyt"
}

The implementation should treat this embedded WooCommerce JSON as the authoritative source for the product’s variants.

⸻

4. Intended Search Flow

Update the Fargotex provider to use a two-stage search process.

Stage A: Discover matching parent products

Continue using the current category-listing parser to:

* paginate through Fargotex upholstery category pages;
* identify product names, parent product IDs, listing images, and product URLs;
* match the user’s query against the parent product;
* avoid requesting every Fargotex product page unnecessarily.

Stage B: Expand matched products

For each matching parent product:

1. Request its product detail page.
2. Locate the WooCommerce variation form.
3. Extract data-product_variations.
4. Decode HTML entities.
5. Parse the decoded JSON.
6. Convert each valid variation into an independent upholstery candidate.
7. Return the expanded candidates instead of the parent candidate when variants are available.

If a matching product is simple or no valid variation data can be extracted, preserve the current parent-product candidate as a fallback.

⸻

5. Client Responsibility

Extend the Fargotex HTTP client with a product-page fetch capability.

The client should:

* accept a validated Fargotex product URL;
* use the same headers and timeout behavior as the existing category request;
* raise HTTP errors consistently;
* return the raw product-page HTML;
* avoid embedding parser or normalization logic inside the HTTP client.

The existing category-page client behavior should remain unchanged.

⸻

6. Parser Responsibility

Extend the Fargotex parser with a dedicated product-variation parser.

The parser should:

* find a form whose class includes variations_form;
* read the complete data-product_variations attribute;
* rely on HTML parsing rather than a broad regular expression for the JSON attribute;
* HTML-decode the attribute value;
* JSON-decode the result;
* tolerate malformed, absent, or unexpected variation payloads;
* return an empty collection when no usable variation data exists;
* avoid raising an uncaught exception that would fail the entire provider search.

The variation parser should remain separate from the category-listing parser because the two HTML structures have different responsibilities.

⸻

7. Variant Candidate Mapping

Each valid WooCommerce variation should become one external upholstery candidate.

The candidate should include enough information to preserve both the variation identity and its relationship to the parent fabric.

Expected semantic mapping:

name
    Parent fabric name combined with the variation label.
code
    Unique WooCommerce variation ID.
image
    Best available variation image.
external_url
    Parent Fargotex product page.
variant_name
    Variation color or upholstery label.
parent_name
    Parent fabric collection name.
sku
    WooCommerce SKU when available.
variation_id
    WooCommerce variation ID.

Example:

{
  "name": "Neon antracyt",
  "code": "66747",
  "sku": "074572c53b3f",
  "variation_id": "66747",
  "variant_name": "antracyt",
  "parent_name": "Neon",
  "image": "https://fargotex.pl/...",
  "external_url": "https://fargotex.pl/produkt/neon/"
}

⸻

8. Unique Identity and Deduplication

The WooCommerce variation_id must be the unique candidate code for expanded variants.

Do not use the SKU as the primary external identity.

The provided Fargotex page demonstrates that multiple color variations can share the same SKU. If the SKU is used as code, the provider’s existing deduplication logic will collapse all variants into a single result.

The provider should therefore deduplicate expanded candidates using:

origin + variation_id

The SKU should be retained as supplemental supplier metadata only.

Parent products that do not expose usable variations may continue using their existing parent product code.

⸻

9. Variation Eligibility

Only return variations that are usable search candidates.

At minimum, exclude variations that are explicitly:

* inactive;
* invisible;
* missing a variation ID;
* missing the required upholstery attribute;
* missing all usable image information.

Do not assume that is_purchasable must be true because Fargotex operates in catalogue mode and its products may intentionally be non-purchasable through WooCommerce.

Do not reject a variation merely because the displayed price is zero.

⸻

10. Variation Attribute Resolution

The initial implementation should support Fargotex’s current color attribute:

attribute_pa_kolory

The parser should nevertheless avoid unnecessarily coupling the complete parsing mechanism to one exact product.

The implementation should isolate attribute resolution so it can later support:

* renamed color attributes;
* additional variation attributes;
* translated values;
* products with more than one variation dimension.

For the current correction, the color attribute remains the expected primary upholstery variant label.

⸻

11. Image Resolution

Prefer variation-specific images in the following order, based on availability:

1. image.full_src
2. image.url
3. image.src
4. parent listing image as a controlled fallback

Use the dedicated gallery image resolver to extract the ordered gallery assets, but do not assign those assets to semantic variations unless a reliable shared identifier or explicit source relationship exists.

Some Fargotex products may assign the same parent image to every variation. That should not prevent the variants from being returned, provided the variation itself contains a usable image reference or the parent image fallback is available.

Image quality limitations from the source page should remain distinct from variation identity correctness.

⸻

11A. Gallery Image Resolver

In addition to parsing the WooCommerce variation data, the Fargotex product-page parser should extract the ordered product gallery contained inside:

<div class="woocommerce-product-gallery__wrapper">

Each child element whose class includes woocommerce-product-gallery__image should be treated as one gallery image candidate.

For every gallery item, extract:

* gallery position;
* full-resolution image URL;
* thumbnail URL;
* image alt text;
* optional image code derived from the filename;
* whether the image is the main parent product image.

Image URL resolution should prefer:

1. the enclosing anchor href;
2. img[data-large_image];
3. img[data-src];
4. img[src].

The first gallery item is normally the parent product image and should be marked as the main image rather than treated automatically as a numbered upholstery image.

Subsequent gallery images may represent individual upholstery samples. Their filenames commonly contain a numeric code, for example:

neon-01-w-1200.webp
neon-02-w-1200.webp
49neon-03-w-1200.webp

The gallery resolver should extract the relevant numeric segment as an optional gallery image code:

01
02
03

The filename parser should remain generic and tolerate:

* prefixes before the fabric name;
* upper- and lower-case filenames;
* hyphen and underscore separators;
* one-, two-, or three-digit image codes;
* generated WordPress size suffixes such as -100x100 or -600x600.

The resolver should preserve the gallery order rendered by the product page.

Expected internal gallery representation:

{
  "position": 1,
  "image_code": "01",
  "image_url": "https://fargotex.pl/wp-content/uploads/2024/12/neon-01-w-1200.webp",
  "thumbnail_url": "https://fargotex.pl/wp-content/uploads/2024/12/neon-01-w-1200-100x100.webp",
  "alt": "Neon - obrazek 2",
  "is_main": false
}

Gallery extraction and WooCommerce variation extraction should remain separate parsing responsibilities.

The variation payload provides semantic variation identity, including:

* variation_id;
* SKU;
* attribute_pa_kolory;
* active and visible status.

The gallery wrapper provides the actual ordered image assets and any image code that can be derived from their filenames.

The implementation must not assume that gallery position equals variation position.

The implementation must also not automatically assign a numbered gallery image to a semantic variation such as antracyt or czerwony unless the source page provides a reliable relationship between them.

A valid automatic relation may be created only when a shared identifier is available, for example:

* the variation attribute contains the same numeric code as the gallery image;
* the variation image URL matches a gallery image URL;
* explicit page metadata maps a variation ID to a gallery image;
* another stable Fargotex field provides the same code on both sides.

When no reliable relationship exists:

1. preserve the semantic WooCommerce variations;
2. preserve the ordered gallery images separately;
3. use the variation-specific image when WooCommerce provides one;
4. otherwise use the parent image as the controlled fallback;
5. do not create an inferred semantic-color-to-gallery-image mapping.

The gallery resolver should make the extracted image collection available to the provider expansion layer so that future mapping strategies can be added without reparsing the product page.

Add parser tests verifying that the gallery resolver:

* finds the woocommerce-product-gallery__wrapper;
* extracts every woocommerce-product-gallery__image entry;
* resolves the full image URL using the expected priority;
* extracts the thumbnail URL;
* marks the first image as the main image;
* derives 01 from neon-01-w-1200.webp;
* derives 03 from 49neon-03-w-1200.webp;
* ignores WordPress dimensions such as 100x100 as the upholstery image code;
* preserves gallery order;
* handles missing optional attributes;
* returns an empty gallery collection when the wrapper is absent;
* does not assign gallery images to semantic variations without a reliable mapping key.
⸻

12. Normalization Contract

Update the Fargotex normalizer so it can preserve the new optional variation metadata without changing the existing shared upholstery response contract unexpectedly.

The normalizer should continue producing the standard external upholstery fields:

* client_id
* name
* code
* image_url
* external_url
* favorite
* list_order
* inventory defaults
* upholstery_category
* origin

Where the external upholstery contract permits provider metadata, preserve:

* variant_name
* variation_id
* parent_name
* sku

Before exposing new fields publicly, inspect the external-provider response aggregation and frontend consumers to confirm whether unknown provider-specific fields are already retained or filtered.

Avoid silently adding response properties that violate a declared Pydantic model or frontend contract.

⸻

13. Provider Orchestration

Update the Fargotex external provider so that expansion happens only after parent-product query matching.

The provider should:

1. fetch category pages with the current bounded concurrency;
2. parse and normalize listing candidates;
3. filter parent candidates against the search query;
4. fetch product pages only for matching parents;
5. expand those parents concurrently using a bounded semaphore;
6. normalize expanded variants;
7. deduplicate by variation identity;
8. stop once the requested result limit is satisfied.

Do not fetch the detail page for every product in every category page before checking the query.

This protects request volume and search latency.

⸻

14. Query Matching Semantics

The query should primarily discover the parent fabric collection.

For example:

Query: Neon
Parent match: Neon
Expanded results:
- Neon antracyt
- Neon czerwony
- Neon pomarancz
- ...

After variants are expanded, variant metadata may also participate in matching where appropriate.

Candidate matching may consider:

* parent product name;
* variant name;
* SKU;
* variation ID;
* external URL.

However, do not re-filter expanded variants only against the original full candidate name in a way that removes valid siblings.

A query for Neon should return all Neon variations, not only variants whose color happens to contain the word Neon.

If direct color searches must be supported, define the behavior deliberately:

Query: antracyt
Possible intended behavior:
- discover parent products containing an antracyt variation;
- return matching antracyt variants.

Do not introduce this broader color-search behavior accidentally as part of the initial correction unless the current endpoint contract expects it.

⸻

15. Result Limit Semantics

Apply the endpoint limit to the final expanded upholstery candidates, not only to parent products.

For example, if one parent product expands to six variants and the requested limit is seven, those six variants should count as six returned results.

Ensure the provider does not stop after finding one parent merely because the unexpanded parent count reached the limit.

Preserve deterministic ordering:

1. category-page order;
2. parent-product order;
3. variation order from data-product_variations.

Concurrency should not make the result order nondeterministic.

⸻

16. Failure and Fallback Behavior

A failure to fetch or parse one product page should not fail the complete multi-provider upholstery search.

For each matched parent product:

* HTTP failure: log provider context and return the parent candidate as fallback;
* missing variation form: return the parent candidate;
* malformed variation JSON: log diagnostic context and return the parent candidate;
* empty valid variation set: return the parent candidate;
* unexpected parser error: isolate the failure to that product.

Do not expose raw Fargotex HTML or parsing exceptions in the public API response.

Logging should include enough context to diagnose:

* product URL;
* parent name;
* failure stage;
* number of raw variations;
* number of accepted variations.

Avoid logging the entire HTML document or full variation payload at normal log levels.

⸻

17. Security and URL Boundaries

The new product-page fetch must not become an unrestricted URL fetcher.

Before requesting a product URL, ensure that:

* the URL belongs to the configured Fargotex domain;
* the path represents a Fargotex product page;
* redirects do not allow requests to arbitrary external hosts.

Use the category parser’s discovered URL rather than accepting arbitrary URLs from the public API.

⸻

18. Tests

Add focused tests around each architectural boundary.

Parser tests

Verify that the product parser:

* extracts multiple variations from HTML-encoded JSON;
* decodes Polish characters correctly;
* extracts attribute_pa_kolory;
* uses variation_id as the unique code;
* retains a shared SKU without collapsing records;
* resolves image fields in the correct priority;
* excludes inactive variations;
* excludes invisible variations;
* handles missing attributes;
* handles malformed JSON;
* handles missing data-product_variations;
* returns an empty list rather than raising for unsupported pages.

Use a compact HTML fixture containing the relevant variations_form structure rather than storing the entire supplied page.

Normalizer tests

Verify that:

* required standard fields remain unchanged;
* variation metadata is preserved where allowed;
* relative image and product URLs are normalized;
* malformed candidates are skipped;
* variation IDs remain strings.

Provider tests

Verify that:

* only query-matching parent products trigger detail-page requests;
* one matching parent expands into multiple returned candidates;
* final results are deduplicated by variation ID;
* shared SKUs do not collapse variants;
* parent fallback occurs when expansion fails;
* the final limit applies to variants;
* result ordering remains deterministic;
* simple products continue to work;
* category pagination behavior remains intact.

Regression example

Given a Neon product fixture containing six active and visible color variations with one shared SKU, the provider should return six candidates with six distinct codes.

⸻

19. Files to Inspect

Codex should inspect and align changes with the existing responsibilities in:

beyo_manager/services/infra/fargotex/client.py
beyo_manager/services/infra/fargotex/parser.py
beyo_manager/services/infra/fargotex/normalizer.py
beyo_manager/services/infra/upholstery_providers/fargotex.py
beyo_manager/services/queries/upholstery/list_external_upholsteries.py
beyo_manager/routers/api_v1/upholsteries.py

Also inspect:

* the external upholstery provider protocol or base class;
* provider aggregation and deduplication logic;
* response serialization;
* existing Fargotex tests;
* frontend consumers of /api/v1/upholsteries/external;
* any shared external upholstery schema.

The current visible router does not declare a response model, so Codex should trace the service outcome and serialization path before deciding whether provider-specific fields can safely be exposed.

⸻

20. Non-Goals

This correction should not:

* scrape every Fargotex product detail page in advance;
* store Fargotex products or variants in the database;
* redesign the shared external upholstery provider interface;
* add a browser automation dependency;
* execute Fargotex JavaScript;
* infer a gallery-image-to-color mapping without source evidence;
* modify the Nevotex provider;
* change authentication or endpoint routing;
* change the existing inventory defaults;
* use SKU as the unique variation identity.

⸻

21. Acceptance Criteria

The correction is complete when:

1. Searching for a Fargotex fabric collection expands a matching variable parent product into its individual upholstery variants.
2. Each returned variant has a distinct WooCommerce variation ID as its candidate code.
3. Variants sharing the same SKU are all preserved.
4. Variant names combine the parent fabric name with the Fargotex color label.
5. Detail pages are requested only for query-matching parent products.
6. Simple products and products without usable variation data continue to return the parent candidate.
7. A failed product-page expansion does not fail the complete external search.
8. The requested result limit applies to final expanded candidates.
9. Existing Fargotex category pagination remains operational.
10. The implementation includes parser, normalizer, provider, fallback, deduplication, and regression tests.