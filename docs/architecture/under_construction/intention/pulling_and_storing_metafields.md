Intention: Shopify Metafield Preference Creation and Query Capability

Objective

Develop a backend capability that remembers which Shopify product metafield definitions users previously selected for a given internal item category and Shopify shop integration.

The purpose is to allow the Shopify product creation form to automatically load the metafields that are normally relevant to the selected item category.

The preference-learning process should remain transparent to the user. The user will not explicitly configure category-to-metafield mappings. Instead, the frontend will persist the selected metafield definitions while the user completes the Shopify product creation workflow.

The local database must store only the preference relationship.

Shopify remains the source of truth for the current metafield-definition characteristics, including:

* Name
* Namespace
* Key
* Description
* Type
* Validations
* Predefined choices
* Any other Shopify-controlled definition metadata required by the frontend

The application must not duplicate these Shopify-controlled characteristics in the preference table.

The capability consists of:

preference table
+
create preference command service
+
targeted preference query service
+
serialization
+
create and read routes

⸻

Effective Preference Scope

A metafield preference belongs to the combination of:

workspace
+ Shopify shop integration
+ internal item category
+ Shopify metafield definition

The Shopify integration must be part of the preference scope because different Shopify stores can have different metafield definitions, even when the same internal item category is used.

Example:

Shop A
Item category: Dining Chair
Selected definition: custom.seat_height
Shop B
Item category: Dining Chair
Selected definition: dimensions.seat_height

These are separate preferences.

⸻

1. Persistence Model

New Table

Create a new table named:

shopify_metafield_preferences

The model should inherit from the project’s standard base, identity, auditing, and soft-deletion mixins where applicable.

The table should contain:

id
workspace_id
item_category_id
shop_integration_id
shopify_metafield_definition_id
sequence_order
is_enabled
created_at
created_by_id
updated_at
updated_by_id
is_deleted
deleted_at
deleted_by_id

The implementation plan should inspect the existing model mixins and avoid declaring fields manually when they are already inherited.

⸻

Field Meanings

workspace_id

Identifies the workspace that owns the preference.

The workspace must match:

* The item category’s workspace
* The Shopify integration’s workspace
* The authenticated user’s workspace

item_category_id

Foreign key to the internal item category table.

Existing model:

backend/app/beyo_manager/models/tables/items/item_category.py

shop_integration_id

Foreign key to the Shopify shop integration table.

Existing model:

backend/app/beyo_manager/models/tables/shopify/shopify_shop_integration.py

shopify_metafield_definition_id

Stores the Shopify GraphQL global ID of the selected metafield definition.

Example:

gid://shopify/MetafieldDefinition/123456789

This field must identify a Shopify MetafieldDefinition.

It must not store a product-specific metafield value ID such as:

gid://shopify/Metafield/987654321

sequence_order

Stores the preferred frontend display order for the selected metafield definition within the item category.

The sequence order is supplied by the frontend when the preference is created.

is_enabled

Allows a preference to remain persisted while being excluded from normal query results.

created_by_id

Identifies the user who originally created the preference.

This field is also used by the optional only_my_preferences query filter.

⸻

Database Constraints

Create a uniqueness constraint covering:

workspace_id
shop_integration_id
item_category_id
shopify_metafield_definition_id

The same Shopify metafield definition must not exist more than once as an active preference for the same workspace, Shopify integration, and item category.

The implementation should follow the project’s existing soft-deletion conventions when deciding whether the uniqueness constraint:

* Includes deleted records
* Uses a partial unique index
* Restores an existing deleted record rather than inserting a new one

Add indexes supporting the main lookup paths:

workspace_id
+ shop_integration_id
+ item_category_id

and, where useful:

workspace_id
+ shop_integration_id
+ item_category_id
+ created_by_id

⸻

2. Create Preference Command Service

Purpose

Create a Shopify command service responsible for persisting a metafield preference selected by the frontend.

Suggested service name:

create_shopify_metafield_preference

Suggested location:

backend/app/beyo_manager/services/commands/shopify/create_shopify_metafield_preference.py

The service must follow the project’s existing:

* ServiceContext
* ServiceOutcome
* Transaction
* Error
* Authorization
* Repository or query-helper conventions

⸻

Command Input

The frontend will send:

item_category_id
shop_integration_id
shopify_metafield_definition_id
sequence_order

The service receives these through:

ServiceContext.incoming_data

Example request payload:

{
  "item_category_id": "icat_001",
  "shop_integration_id": "shpint_001",
  "shopify_metafield_definition_id": "gid://shopify/MetafieldDefinition/123456789",
  "sequence_order": 1
}

⸻

Input Validation

item_category_id

Required non-empty internal item category ID.

The referenced category must belong to the authenticated workspace.

shop_integration_id

Required non-empty Shopify integration ID.

The integration must:

* Exist
* Belong to the authenticated workspace
* Be active
* Be usable for Shopify GraphQL requests

shopify_metafield_definition_id

Required Shopify GraphQL global ID.

The service should reject values that do not use the expected shape:

gid://shopify/MetafieldDefinition/...

String-shape validation alone is not sufficient. The service must also confirm through Shopify that the ID resolves to a current product metafield definition.

sequence_order

Required integer.

It should be greater than or equal to zero unless the project already uses a different sequence-order convention.

⸻

Authorization and Workspace Isolation

The command service must derive the authenticated workspace and user from:

ctx.identity

Before creating a preference, the service must verify:

1. The item category belongs to the authenticated workspace.
2. The Shopify integration belongs to the authenticated workspace.
3. The Shopify integration is active and usable.
4. The authenticated role is allowed to use the Shopify product creation capability.
5. The preference being created is scoped to the same workspace as both resources.

The frontend must never be allowed to supply or override:

workspace_id
created_by_id

These values must be derived from the authenticated context.

⸻

Shopify Definition Validation

Before persisting the preference, the service must confirm that the supplied Shopify definition ID exists in the selected Shopify shop.

Use the project’s existing Shopify GraphQL client and encrypted-token boundary.

The command service must not manually decrypt or expose the Shopify access token outside the existing integration infrastructure.

Conceptual GraphQL query:

query SelectedMetafieldDefinition($id: ID!) {
  node(id: $id) {
    ... on MetafieldDefinition {
      id
      ownerType
    }
  }
}

The service must reject:

* A null result
* A node that is not a MetafieldDefinition
* A definition whose ownerType is not PRODUCT
* A definition that is inaccessible in the selected shop
* Shopify authorization failures
* Shopify GraphQL transport failures

This Shopify request is only a validation step.

The command service must not persist:

* Name
* Namespace
* Key
* Description
* Type
* Validations
* Choices

⸻

Create Command Execution Flow

The command service should perform the following sequence.

1. Validate the payload

Validate:

item_category_id
shop_integration_id
shopify_metafield_definition_id
sequence_order

2. Resolve authenticated identity

Derive:

workspace_id
created_by_id

from ctx.identity.

3. Validate local ownership

Confirm that:

* The item category belongs to the workspace.
* The Shopify integration belongs to the workspace.
* The Shopify integration is active.

4. Validate the Shopify definition

Query Shopify using the stored integration credentials and confirm that the definition:

* Exists
* Is a MetafieldDefinition
* Has ownerType = PRODUCT

5. Detect an existing preference

Look for an existing row with the same:

workspace_id
shop_integration_id
item_category_id
shopify_metafield_definition_id

6. Create, restore, or update

The operation must be idempotent.

No existing row

Create a new preference.

Existing active row

Do not create a duplicate.

Update sequence_order if the supplied value differs.

Existing disabled row

Re-enable it and update sequence_order.

Existing soft-deleted row

Restore it according to the project’s existing soft-deletion conventions and update sequence_order.

7. Persist the transaction

Use the project’s normal service transaction pattern.

8. Return the preference

Return the persisted preference through the standard preference serializer.

⸻

Create Command Idempotency

Repeated submissions with the same:

workspace_id
shop_integration_id
item_category_id
shopify_metafield_definition_id

must not create duplicate active rows.

Example:

First request:
sequence_order = 2
Second request:
sequence_order = 4

Expected result:

one preference row
sequence_order = 4

⸻

3. Create Preference Router

Add a new route to:

backend/app/beyo_manager/routers/api_v1/shopify.py

Recommended route:

POST /metafield-preferences

Full route under the existing Shopify router prefix may become:

POST /api/v1/integrations/shopify/metafield-preferences

The final route path should follow the existing Shopify router conventions.

⸻

Request Body Model

Add a Pydantic request model near the existing Shopify request-body models.

Suggested name:

ShopifyMetafieldPreferenceCreateBody

Conceptual model:

class ShopifyMetafieldPreferenceCreateBody(BaseModel):
    item_category_id: str
    shop_integration_id: str
    shopify_metafield_definition_id: str
    sequence_order: int = Field(ge=0)

The implementation should align:

* Field aliases
* Casing
* Validation style
* Error handling
* Model placement

with the existing router conventions.

⸻

Create Route Behavior

The route should:

1. Require the authenticated roles allowed to use the Shopify product creation form.
2. Accept the request body.
3. Pass body.model_dump() through ServiceContext.incoming_data.
4. Execute create_shopify_metafield_preference through run_service.
5. Return build_ok or build_err consistently with existing Shopify routes.

Suggested role access:

ADMIN
MANAGER
SELLER
WORKER

The implementation plan must verify the exact role list against the current Shopify product-processing route.

Conceptual route:

@router.post("/metafield-preferences")
async def create_shopify_metafield_preference_route(
    body: ShopifyMetafieldPreferenceCreateBody,
    claims: dict = Depends(
        require_roles([ADMIN, MANAGER, SELLER, WORKER])
    ),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        create_shopify_metafield_preference,
        ServiceContext(
            identity=claims,
            incoming_data=body.model_dump(),
            session=session,
        ),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)

This is conceptual. The implementation should follow the existing router’s actual naming, imports, role constants, formatting, and response structure.

⸻

4. Query Preference Service

Purpose

Create a Shopify query service responsible for returning the current Shopify metafield definitions associated with the saved preferences.

Suggested service name:

get_shopify_metafield_preferences

Suggested location:

backend/app/beyo_manager/services/queries/shopify/get_shopify_metafield_preferences.py

The service must follow the existing service-context and service-outcome conventions.

⸻

Query Service Inputs

The service receives inputs through ServiceContext.

Required input

shop_integration_id

A Shopify integration must be explicitly selected because Shopify metafield definition IDs belong to a specific Shopify shop.

Required query parameter

item_category_ids

A comma-separated list of internal item category IDs.

Example:

item_category_ids=icat_001,icat_002,icat_003

At least one valid item category ID must be supplied.

The service should normalize the values by:

* Splitting on commas
* Trimming whitespace
* Removing empty values
* Removing duplicate IDs
* Preserving the original category order

Optional query parameter

only_my_preferences

Boolean value.

Default:

false

When true, only preference rows whose created_by_id matches the authenticated user ID should be returned.

When false, all matching enabled preferences within the workspace should be considered, regardless of which user originally created them.

⸻

Query Authorization and Workspace Isolation

The query service must derive the authenticated workspace and user identity from:

ctx.identity

Before querying Shopify, the service must verify:

1. The Shopify integration belongs to the authenticated workspace.
2. The Shopify integration is active and usable.
3. Every requested item category belongs to the authenticated workspace.
4. Every returned preference belongs to the same workspace.
5. Every returned preference belongs to the selected Shopify integration.
6. Deleted preferences are excluded.
7. Disabled preferences are excluded.
8. The authenticated role is allowed to use the Shopify product creation form.

The service must never use Shopify credentials from an integration belonging to another workspace.

⸻

Query Execution Flow

1. Validate the request

Validate:

shop_integration_id
item_category_ids
only_my_preferences
workspace ownership
Shopify integration availability

2. Load local preference rows

Query shopify_metafield_preferences using:

workspace_id
shop_integration_id
item_category_id IN requested item category IDs
is_enabled = true
is_deleted = false

When:

only_my_preferences = true

also apply:

created_by_id = authenticated user ID

Order preference rows deterministically by:

item_category_id
sequence_order
created_at

3. Extract Shopify definition IDs

Build a deduplicated list of:

shopify_metafield_definition_id

The same definition may be selected for several item categories, but it should only be requested once from Shopify.

4. Perform a targeted Shopify GraphQL query

Use the stored Shopify definition IDs to fetch current definition metadata.

Prefer a batched nodes(ids:) query instead of one Shopify request per preference.

Conceptual query:

query SelectedMetafieldDefinitions($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on MetafieldDefinition {
      id
      name
      namespace
      key
      description
      ownerType
      type {
        name
      }
      validations {
        name
        value
      }
    }
  }
}

Use the project’s existing Shopify GraphQL client and encrypted-token boundary.

5. Merge Shopify data with preference data

Shopify provides the current definition characteristics:

id
name
namespace
key
description
ownerType
type
validations

The local database provides the preference metadata:

item_category_id
sequence_order
is_enabled
created_at
created_by_id

Merge the records by:

shopify_metafield_definition_id

The final order must follow the locally stored sequence_order, not the order returned by Shopify.

6. Serialize the result

Return frontend-ready records grouped by item category.

⸻

5. Query Response Shape

The response should preserve the relationship between each item category and its selected definitions.

Suggested structure:

{
  "shopIntegrationId": "shpint_001",
  "itemCategories": [
    {
      "itemCategoryId": "icat_001",
      "metafieldPreferences": [
        {
          "shopifyMetafieldDefinitionId": "gid://shopify/MetafieldDefinition/123456789",
          "name": "Material",
          "namespace": "custom",
          "key": "material",
          "description": null,
          "type": "single_line_text_field",
          "validations": [
            {
              "name": "choices",
              "value": "[\"Oak\",\"Teak\",\"Walnut\"]"
            }
          ],
          "sequenceOrder": 1,
          "isEnabled": true,
          "createdAt": "2026-07-13T08:30:00Z",
          "createdBy": {
            "...": "serialized user working-section member"
          }
        }
      ]
    }
  ],
  "unavailableDefinitionIds": []
}

The exact field casing should follow the project’s established serializer and API conventions.

⸻

6. Preference Serialization

Add a serializer for the merged local preference and Shopify definition result.

Suggested location:

backend/app/beyo_manager/domain/shopify/serializers.py

The read serializer should include:

shopify_metafield_definition_id
item_category_id
name
namespace
key
description
type
validations
sequence_order
is_enabled
created_at
created_by

Use the existing user serializer for created_by:

serialize_user_working_section_member

Existing location:

backend/app/beyo_manager/domain/users/serializers.py

Do not duplicate user serialization logic inside the Shopify serializer.

The serializer should accept:

* The local preference row
* The current Shopify definition payload

as separate explicit inputs or through a dedicated merged domain structure.

⸻

Create Response Serialization

The create command should return the persisted preference.

Because the create command does not persist Shopify definition characteristics, the implementation plan should choose one of these patterns based on existing project conventions:

Option A: Return preference identity only

{
  "id": "shpmfp_001",
  "itemCategoryId": "icat_001",
  "shopIntegrationId": "shpint_001",
  "shopifyMetafieldDefinitionId": "gid://shopify/MetafieldDefinition/123456789",
  "sequenceOrder": 1,
  "isEnabled": true
}

Option B: Return the preference plus the validated Shopify definition

The create service may reuse the Shopify definition obtained during validation and return a frontend-ready merged object without persisting that metadata.

The implementation plan should inspect existing command-response conventions before deciding.

⸻

7. Handling Predefined Choices

Predefined choices must be obtained from the current Shopify metafield definition’s validations.

Example Shopify validation:

{
  "name": "choices",
  "value": "[\"Oak\",\"Teak\",\"Walnut\"]"
}

The backend may:

1. Return Shopify’s raw validation representation; or
2. Return both the raw representation and a normalized parsed form.

The implementation plan should inspect the existing API and frontend conventions before deciding.

The preference table must not store predefined choices.

⸻

8. Handling Missing or Deleted Shopify Definitions

A saved preference may reference a Shopify metafield definition that was later deleted or became inaccessible.

A Shopify nodes(ids:) query may return null for that definition ID.

This must not fail the entire query request.

The query service should:

1. Exclude unavailable definitions from the normal metafieldPreferences result.
2. Return their IDs through unavailableDefinitionIds.
3. Log the stale preference with sufficient context.
4. Avoid deleting or disabling the local preference during the read operation.

Any cleanup should occur through a separate command or reconciliation process, not as an implicit side effect of a query.

Example:

{
  "itemCategories": [],
  "unavailableDefinitionIds": [
    "gid://shopify/MetafieldDefinition/456"
  ]
}

⸻

9. Handling Shopify Failures

If the Shopify GraphQL request fails entirely, the service should return the project’s normal integration error response.

The query must not return incomplete preference objects without current Shopify definition metadata because Shopify is the source of truth for that metadata.

The services should distinguish, where existing error conventions allow, between:

* Invalid request
* Missing item category
* Missing Shopify integration
* Unauthorized workspace access
* Inactive Shopify integration
* Malformed Shopify definition ID
* Missing Shopify scope
* Shopify GraphQL transport failure
* Shopify GraphQL authorization failure
* Shopify GraphQL response errors
* Individual definition IDs that no longer exist

⸻

10. Query Router

Add a new route to:

backend/app/beyo_manager/routers/api_v1/shopify.py

Recommended route:

GET /shops/{shop_integration_id}/metafield-preferences

Query parameters:

item_category_ids
only_my_preferences

Example:

GET /api/v1/integrations/shopify/shops/shpint_001/metafield-preferences?item_category_ids=icat_001,icat_002&only_my_preferences=true

The route should:

1. Require the appropriate authenticated roles.
2. Pass shop_integration_id through incoming_data.
3. Pass request query parameters through query_params.
4. Execute the query service through run_service.
5. Return build_ok or build_err consistently with existing Shopify routes.

Suggested role access:

ADMIN
MANAGER
SELLER
WORKER

The implementation plan should verify this against the existing Shopify product-processing route.

Conceptual route:

@router.get("/shops/{shop_integration_id}/metafield-preferences")
async def get_shopify_metafield_preferences_route(
    shop_integration_id: str,
    request: Request,
    claims: dict = Depends(
        require_roles([ADMIN, MANAGER, SELLER, WORKER])
    ),
    session: AsyncSession = Depends(get_db),
):
    outcome = await run_service(
        get_shopify_metafield_preferences,
        ServiceContext(
            identity=claims,
            incoming_data={
                "shop_integration_id": shop_integration_id,
            },
            query_params=dict(request.query_params),
            session=session,
        ),
    )
    if not outcome.success:
        return build_err(outcome.error)
    return build_ok(outcome.data)

The implementation should align naming, imports, formatting, and response construction with the existing router instead of copying this example mechanically.

⸻

11. Relevant Existing Files

Item category model

backend/app/beyo_manager/models/tables/items/item_category.py

Shopify integration model

backend/app/beyo_manager/models/tables/shopify/shopify_shop_integration.py

Shopify router

backend/app/beyo_manager/routers/api_v1/shopify.py

Shopify serializers

backend/app/beyo_manager/domain/shopify/serializers.py

User working-section-member serializer

backend/app/beyo_manager/domain/users/serializers.py

Service context and execution conventions

backend/app/beyo_manager/services/context.py
backend/app/beyo_manager/services/run_service.py

Claude should also inspect:

* Existing Shopify command services
* Existing Shopify query services
* Shopify GraphQL client boundaries
* Encrypted token access
* Shopify integration status validation
* Model identity and audit mixins
* Soft-deletion conventions
* Migration conventions
* Router request models
* Serializer conventions
* Service unit tests
* Router integration tests

The implementation plan should reuse established abstractions rather than introducing parallel ones.

⸻

12. Non-Goals

This phase does not include:

* Persisting metafield values belonging to individual Shopify products
* Mirroring Shopify metafield names locally
* Mirroring Shopify metafield namespaces or keys locally
* Mirroring Shopify metafield types locally
* Mirroring Shopify metafield validations locally
* Mirroring predefined choices locally
* Creating Shopify metafield definitions
* Updating Shopify metafield definitions
* Deleting Shopify metafield definitions
* Automatically deleting stale preferences during read operations
* Building the frontend metafield selector
* Persisting the product metafield values entered by the user
* Assigning metafield definitions directly to Shopify taxonomy categories
* Conditionally displaying metafields inside Shopify Admin
* Creating an administrative preference-management page
* Bulk replacing all preferences for a category unless required by the later frontend workflow

This phase focuses only on:

preference persistence
+
single-preference create or restore
+
targeted preference retrieval
+
current Shopify definition hydration
+
create and read API routes

⸻

13. Required Tests

The implementation plan should include tests covering at least the following.

Persistence and Migration

1. Creating the shopify_metafield_preferences table.
2. Enforcing the required foreign keys.
3. Enforcing the active-record uniqueness constraint.
4. Confirming that Shopify definition characteristics are not persisted.
5. Confirming the primary lookup indexes exist.

Create Command

6. Creating a preference using valid input.
7. Deriving workspace_id from authenticated identity.
8. Deriving created_by_id from authenticated identity.
9. Rejecting a missing item_category_id.
10. Rejecting a missing shop_integration_id.
11. Rejecting a missing shopify_metafield_definition_id.
12. Rejecting an invalid sequence_order.
13. Rejecting a malformed Shopify metafield definition GID.
14. Rejecting an item category outside the authenticated workspace.
15. Rejecting a Shopify integration outside the authenticated workspace.
16. Rejecting an inactive Shopify integration.
17. Rejecting a Shopify node that does not exist.
18. Rejecting a Shopify node that is not a MetafieldDefinition.
19. Rejecting a metafield definition whose ownerType is not PRODUCT.
20. Handling a Shopify GraphQL failure during validation.
21. Confirming that repeated create requests are idempotent.
22. Confirming that a repeated request updates sequence_order.
23. Confirming that a disabled preference is re-enabled.
24. Confirming that a soft-deleted preference is restored according to project conventions.
25. Confirming that a duplicate active row is not inserted.
26. Returning the created or restored preference through the correct serializer.
27. Confirming that Shopify definition metadata returned during validation is not persisted.

Query Service

28. Querying preferences for one item category.
29. Querying preferences for multiple item categories.
30. Rejecting an empty item_category_ids parameter.
31. Normalizing duplicate category IDs.
32. Normalizing whitespace-separated category IDs.
33. Preserving requested item-category order where required.
34. Rejecting item categories outside the authenticated workspace.
35. Rejecting a Shopify integration outside the authenticated workspace.
36. Rejecting an inactive Shopify integration.
37. Applying only_my_preferences=true.
38. Returning all users’ preferences when only_my_preferences=false.
39. Excluding disabled preferences.
40. Excluding soft-deleted preferences.
41. Preserving sequence_order.
42. Deduplicating Shopify definition IDs before the GraphQL request.
43. Fetching several Shopify definitions through one batched request.
44. Returning the same Shopify definition under multiple item categories when both categories reference it.
45. Serializing created_by using serialize_user_working_section_member.
46. Returning validation metadata.
47. Returning predefined choices validations.
48. Handling one missing Shopify definition without failing the request.
49. Reporting missing definitions through unavailableDefinitionIds.
50. Handling a complete Shopify GraphQL failure.
51. Confirming that Shopify metadata is merged by definition ID.
52. Confirming that Shopify response ordering does not override local sequence_order.

Router Tests

53. Accepting a valid create request.
54. Rejecting an invalid create request body.
55. Enforcing allowed roles on the create route.
56. Enforcing allowed roles on the query route.
57. Passing create input through ServiceContext.incoming_data.
58. Passing shop_integration_id through the query service’s incoming_data.
59. Passing query parameters through ServiceContext.query_params.
60. Returning errors through build_err.
61. Returning successful results through build_ok.

⸻

14. Acceptance Criteria

The capability is complete when:

1. The shopify_metafield_preferences model and migration exist.
2. Preference rows are scoped to workspace, Shopify integration, item category, and Shopify definition.
3. The required uniqueness constraint exists.
4. The required lookup indexes exist.
5. A command service can create a preference using:
    * item_category_id
    * shop_integration_id
    * shopify_metafield_definition_id
    * sequence_order
6. The create command derives workspace and user identity from authentication.
7. The create command validates item-category workspace ownership.
8. The create command validates Shopify-integration workspace ownership and active status.
9. The create command confirms that the Shopify definition exists.
10. The create command confirms that the Shopify definition has ownerType = PRODUCT.
11. Repeated create requests do not create duplicate active rows.
12. Repeated create requests update sequence_order when needed.
13. Disabled or soft-deleted preferences can be restored according to project conventions.
14. The create route follows existing Shopify router conventions.
15. The query service accepts one or more item category IDs.
16. The query service optionally filters preferences to the authenticated user.
17. The query service performs a targeted batched Shopify GraphQL query using the stored definition IDs.
18. Shopify remains the source of truth for definition metadata.
19. The application does not persist Shopify definition characteristics.
20. Query results are grouped by item category.
21. Query results preserve locally stored sequence order.
22. created_by is serialized through the existing user serializer.
23. Predefined choices are returned from Shopify validations.
24. Missing individual Shopify definitions do not fail the entire query.
25. Missing definition IDs are reported through unavailableDefinitionIds.
26. The read route follows existing Shopify router conventions.
27. Workspace isolation is enforced for create and read operations.
28. Role authorization is enforced for create and read operations.
29. Tests cover creation, idempotency, restoration, targeted retrieval, filtering, stale definitions, authorization, and Shopify failures.

## Implementation lifecycle

| Implementation plan | Status | Summary |
|---|---|---|
| `PLAN_shopify_metafield_preferences_20260713.md` | archived | `SUMMARY_PLAN_shopify_metafield_preferences_20260713.md` |

Progress note: the backend implementation now supports atomic multi-shop preference creation, per-shop category hydration and live name search, grouped read responses, and the corresponding Shopify routes. Frontend selector UI and product metafield values remain outside this implementation cycle.
