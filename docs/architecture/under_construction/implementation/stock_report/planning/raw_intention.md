Stock Report Capability — Initial Implementation Intention

1. Purpose of This Document

This document describes the initial implementation intention for a new Stock Report capability in the Manager application.

The purpose of this document is to establish:

* the business and domain goal;
* system ownership boundaries between the Manager and Scanner applications;
* proposed database models;
* domain invariants;
* state transitions;
* persisted projections;
* history semantics;
* proposed services;
* local Manager API endpoints;
* Scanner → Manager webhook endpoints;
* serialization requirements;
* testing philosophy;
* and known open questions.

This document should not be treated as an unquestionable implementation specification.

The behavioral intention, domain rules, invariants, and desired outcomes described here are the primary source of truth. The proposed tables, services, endpoints, and orchestration structure are an initial architectural proposal.

Before implementation, investigate the existing Manager repository and determine how this capability should fit its current architectural patterns.

In particular:

1. Inspect existing models, migrations, command/query services, transaction boundaries, task state transitions, serializers, authentication patterns, and tests.
2. Reuse existing infrastructure and conventions wherever appropriate.
3. Identify places where this proposal conflicts with, duplicates, or unnecessarily bypasses existing architecture.
4. Challenge implementation details where a stronger solution already exists in the repository.
5. Ask clarification questions whenever the intended domain behavior is ambiguous.
6. Establish a reliable implementation plan before modifying production code.

The goal is to preserve the intention and domain semantics, not blindly reproduce the exact implementation structure proposed below.

⸻

2. High-Level Goal

We will develop a Stock Report capability in the Manager application.

The purpose of this capability is to transform stock shortages and stock requirements into meaningful work for Manager workers.

The Scanner application currently owns knowledge about:

* item placement;
* stock locations/zones;
* desired stock thresholds;
* item categories;
* item properties;
* and the quantity of a particular item category/property combination that a stock location currently requires.

The Manager application owns the workflow required to act upon that demand.

Therefore, at this stage:

Scanner owns stock demand and placement truth. Manager owns the work-execution workflow used to satisfy that demand.

Eventually, the Manager application is expected to take over functionality that currently belongs to Scanner. Until that migration happens, Manager will replicate the minimum required models/semantics and consume the Scanner backend as an upstream system.

⸻

3. Implementation Scope

This phase is backend-only.

No frontend implementation is required yet.

The implementation will be performed as a multi-phase implementation using the existing agentic development flow.

The intention is to first establish strong domain understanding, architecture, invariants, and tests before implementing the complete feature.

Tests should primarily validate observable feature/domain behavior given controlled data.

Avoid unnecessarily coupling tests to internal implementation details. Tests should prove that the capability behaves correctly rather than merely proving that a particular function happened to be called or that the implementation happens to have a specific internal structure.

⸻

4. Core Ownership Model

There are two distinct concerns.

Scanner responsibility

Scanner determines:

* what stock is required;
* where stock is required;
* how much is required;
* and when a produced/repaired item has been processed by Scanner and should no longer be considered awaiting placement.

Scanner therefore remains authoritative over quantity_requested.

Manager responsibility

Manager determines:

* which existing items/tasks are being used to address the stock requirement;
* whether those items are queued;
* whether work is currently in progress;
* whether Manager has completed its work and the item is awaiting Scanner processing;
* and whether Scanner has acknowledged that the item has completed the stock-side lifecycle.

This distinction is fundamental to the design.

⸻

5. Core Domain Model

The proposed models should be created under:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/stock_report

The proposed tables are:

1. StockReportItem
2. StockTaskAssignment
3. StockReportHistoryRecord

Naming may be adjusted to repository conventions after investigation, but the semantics described below should remain intact.

⸻

6. StockReportItem

Proposed model:

StockReportItem (IdentityMixin, Base)

Fields:

item_category_id: int
item_major_category: ItemMajorCategoryEnum
properties: JSONB
properties_signature: str
quantity_requested: int
quantity_in_queue: int
quantity_in_progress: int
quantity_awaiting: int
priority: Priority | null
priority_order: int | null
stock_task_assignments
stock_report_history_records

All quantity_* values:

>= 0
default = 0

⸻

6.1 Item Category

item_category_id is a foreign key/relationship to:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items/item_category.py

The incoming Scanner itemCategory should map to this item_category_id.

Earlier versions of this proposal called this field item_type_id. Do not introduce that column.

The intention is to preserve the existing ItemCategory semantics until the broader Item Domain migration explicitly changes them.

The Scanner and Manager applications currently derive their item categories from the same source, so a legitimate Scanner request is expected to map to an existing Manager ItemCategory.

The associated major category can be derived from ItemCategory.major_category.

The enum currently exists at:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/domain/items/enums.py

⸻

7. StockReportItem Identity

A StockReportItem represents one unique combination of:

(item_category_id, normalized properties)

There may therefore be multiple StockReportItems using the same item_category_id as long as their properties differ.

For example:

{
  "itemCategory": "...",
  "properties": {
    "color": "red",
    "width": 100
  }
}

is a different stock requirement from the same category with different properties.

JSON key ordering must not affect identity.

For example:

{"color": "red", "width": 100}

and:

{"width": 100, "color": "red"}

must resolve to the same StockReportItem.

Properties may contain nested objects, lists, and other JSON-compatible structures.

⸻

7.1 Properties Signature

Introduce a properties_signature adjacent to properties.

This should provide a stable/canonical representation suitable for efficient matching and uniqueness.

The current Item implementation already contains similar functionality through Item.properties_signature.

Investigate that implementation before creating anything new and reuse the existing signature-generation logic if appropriate.

The important invariant is:

Equivalent normalized properties must produce the same signature regardless of JSON object key ordering.

⸻

8. StockReportItem as a Live Projection

StockReportItem is the Manager-side live projection of a Scanner stock requirement with Manager workflow state layered on top.

Scanner provides:

itemCategory
properties
quantityRequested

which map to:

item_category_id
properties
quantity_requested

Scanner may continuously update quantity_requested.

Manager must reflect that authoritative value.

A decrease in quantity_requested does not imply deletion of the StockReportItem.

If:

quantity_requested = 0

the StockReportItem continues to exist.

Deletion is a separate explicit/destructive operation.

⸻

9. Persisted Workflow Projections

The following fields are persisted cached projections:

quantity_in_queue
quantity_in_progress
quantity_awaiting

They exist to support efficient reads.

They are not the authoritative source of workflow state.

The authoritative source is:

StockTaskAssignment.state

Therefore:

StockTaskAssignment.state is source-of-truth workflow state. The quantity_* columns on StockReportItem are denormalized persisted projections maintained transactionally from assignment state.

These counters must always be reconstructable from the underlying assignments.

This is an important reliability invariant and should influence:

* service design;
* concurrency handling;
* backfill/recovery tools;
* migrations;
* and tests.

⸻

10. StockTaskAssignment

Proposed model:

StockTaskAssignment (IdentityMixin, Base)

Fields:

task_id: int
item_id: int
state: StockTaskAssignmentState
stock_report_item_id: int

task_id is a foreign key to:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task.py

item_id is a foreign key to:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items/item.py

Proposed enum:

StockTaskAssignmentState:
    in_queue
    in_progress
    awaiting
    resolved

Default on creation:

in_queue

⸻

11. Assignment Cardinality and Uniqueness

A StockReportItem can contain many StockTaskAssignment records.

Each StockTaskAssignment references exactly:

* one StockReportItem;
* one Task;
* one Item.

In the current Manager architecture, a Task can only have one Item.

The same Item may participate in different Tasks over its lifetime.

However:

The same unique Item must not have more than one StockTaskAssignment in an active state at the same time.

Active assignment states are:

in_queue
in_progress
awaiting

resolved is not considered active.

Therefore, historical/resolved assignments do not prevent that Item from participating in a future StockTaskAssignment.

Claude should investigate how best to enforce this invariant using the existing persistence architecture.

⸻

12. Assignment State Machine

The normal lifecycle is:

in_queue
    ↓
in_progress
    ↓
awaiting
    ↓
resolved

These transitions represent different ownership stages of the work.

⸻

13. in_queue

A StockTaskAssignment begins as:

state = in_queue

when an Item and its associated Task are assigned to a StockReportItem requirement.

quantity_in_queue represents the number of linked StockTaskAssignments currently in this state.

Importantly:

quantity_in_queue > quantity_requested

is valid.

This can happen when the storage/work environment contains more pieces requiring repair/work than the current Scanner demand.

Therefore, Manager workflow quantities must not be artificially capped by Scanner quantity_requested.

⸻

14. in_progress

A StockTaskAssignment enters:

state = in_progress

when its associated Task transitions into:

working

quantity_in_progress represents the number of linked assignments currently in this state.

⸻

15. awaiting

A StockTaskAssignment enters:

state = awaiting

when Manager considers its work complete.

This happens when the associated Task transitions into:

ready

or:

resolved

quantity_awaiting represents the number of linked assignments currently in this state.

The meaning of awaiting is important:

Manager has completed its responsibility for the Item, but Scanner has not yet confirmed the Item’s completion from the stock/location perspective.

The Item might subsequently:

* be placed in the requested location;
* be placed in another location;
* be sold through the webshop before placement;
* or otherwise be processed by Scanner.

Until Scanner communicates this outcome, the assignment remains awaiting.

⸻

16. resolved

Scanner can transition an awaiting assignment into:

resolved

This means the Item is no longer awaiting Scanner-side processing.

The corresponding StockReportItem projection changes from:

quantity_awaiting -= 1

because the assignment no longer contributes to the awaiting count.

⸻

17. Task State Synchronization

StockTaskAssignment state is strongly connected to Task state.

The existing Task transition architecture must be investigated before implementation.

Relevant services include:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py

and:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/task_steps/transition_step_state_batch.py

Do not build a parallel Task state mechanism without first understanding these services and their shared transition core.

⸻

17.1 Forward Transitions

Expected synchronization includes:

Task pending
→ StockTaskAssignment in_queue
Task working
→ StockTaskAssignment in_progress
Task ready/resolved
→ StockTaskAssignment awaiting

A Task does not necessarily pass through every intermediate state.

For example:

pending → ready

or:

pending → resolved

must still place the StockTaskAssignment into the correct resulting state.

The implementation must therefore synchronize based on resulting domain state rather than assuming every intermediate transition occurred.

⸻

18. Backward Task Transitions

Task state transitions are not strictly forward-only.

For example, a Task may move:

ready → working

or:

resolved → working

when work is reopened.

The corresponding StockTaskAssignment must reflect this change.

For example:

awaiting → in_progress

and the cached projections must change accordingly:

quantity_awaiting -= 1
quantity_in_progress += 1

The exact integration with the existing Task transition engine should be determined after repository investigation.

⸻

19. Cancelled and Failed Tasks

Tasks may also enter states such as:

cancelled
failed

These states jump outside the normal StockTaskAssignment workflow.

When this happens, the assignment must no longer contribute to:

quantity_in_queue
quantity_in_progress
quantity_awaiting

Claude should inspect the existing Task lifecycle and determine the cleanest representation for this condition.

Do not invent a new assignment state without first determining whether one is necessary.

The invariant is:

Cancelled or failed work must no longer contribute to active StockReportItem workflow quantities.

⸻

20. Projection Arithmetic

The projection is determined entirely by assignment state.

Conceptually:

quantity_in_queue =
    count(active assignments where state == in_queue)
quantity_in_progress =
    count(active assignments where state == in_progress)
quantity_awaiting =
    count(active assignments where state == awaiting)

State transitions therefore produce projection changes.

Example:

in_queue → in_progress

means:

quantity_in_queue -= 1
quantity_in_progress += 1

Example:

in_progress → awaiting

means:

quantity_in_progress -= 1
quantity_awaiting += 1

Example:

awaiting → resolved

means:

quantity_awaiting -= 1

These mutations and the assignment state transition must occur atomically.

⸻

21. Atomicity and Concurrency

A state transition and its corresponding StockReportItem projection update form one domain operation.

For example:

StockTaskAssignment.in_progress → awaiting

and:

StockReportItem.quantity_in_progress -= 1
StockReportItem.quantity_awaiting += 1

must succeed or fail together.

Concurrent transitions must not produce lost updates or corrupted counters.

Investigate the repository’s existing transaction conventions and determine the appropriate implementation mechanism.

Do not prematurely prescribe row locking, atomic SQL updates, or another strategy until existing repository patterns have been inspected.

⸻

22. Idempotency

Scanner webhook operations must be idempotent.

The domain naturally provides much of this behavior.

Requested quantity

Scanner sends the authoritative resulting value:

quantity_requested = N

It does not send:

quantity_requested += N

Therefore retrying the same request results in the same final value.

Awaiting resolution

Scanner resolution operates only on assignments currently eligible for resolution.

Once:

awaiting → resolved

has happened, retrying the same operation must not decrement quantity_awaiting again.

State transitions, rather than blind arithmetic, must therefore drive projection changes.

⸻

23. StockReportHistoryRecord

Proposed model:

StockReportHistoryRecord (IdentityMixin, Base)

Fields:

type: StockReportHistoryType
quantity_requested: int
quantity_awaiting: int
priority
priority_order
created_at: DateTime
stock_report_item_id: int

Proposed enum:

StockReportHistoryType:
    quantity_requested_change
    priority_change
    priority_order_change

The purpose of this table is not to record every mutation.

Its purpose is to preserve meaningful snapshots of a StockReportItem’s evolving goal.

⸻

24. Quantity History Semantics

A new history record is created when:

new quantity_requested > previous quantity_requested

The record captures the relevant StockReportItem state at that moment.

If:

new quantity_requested < previous quantity_requested

no new quantity-requested history record is created.

This is intentional.

A decrease in requested quantity can mean that Scanner has observed fulfillment of some of the demand—for example, an Item has reached the location that created the requirement.

Creating a new goal record on every decrease would distort the original goal and mix Scanner-side fulfillment semantics with Manager-side work history.

If:

quantity_requested = 0

the StockReportItem remains.

No automatic deletion occurs.

⸻

25. Historical Awaiting Quantity

Within a quantity-requested history record, quantity_awaiting behaves additively.

As StockTaskAssignments transition into:

awaiting

the relevant history record’s quantity_awaiting increases.

When Scanner subsequently resolves those assignments:

awaiting → resolved

the historical quantity_awaiting value is not decreased.

This is intentional.

The history record answers a question closer to:

Given this stock-demand goal, how much Manager work reached completion/awaiting during this goal period?

It is therefore historical accumulation, not a live projection.

The live StockReportItem.quantity_awaiting, by contrast, does decrease when Scanner resolves assignments.

Task state history already provides more precise completion timing for individual pieces of work, so we do not need to create a new StockReportHistoryRecord for every awaiting increment.

⸻

26. Priority History

Priority and priority order are also historically meaningful.

A new StockReportHistoryRecord should therefore be created whenever either:

priority changes

or:

priority_order changes

The new history record carries the relevant quantity values with it so that the state of the StockReportItem at that priority transition can later be understood.

Claude should investigate whether the proposed type model is sufficient for representing simultaneous changes without producing misleading duplicate history records.

⸻

27. Priority

Introduce:

Priority:
    high
    medium
    low

A StockReportItem may also have:

priority = null

Default:

null

Priority is controlled by Manager, not Scanner.

⸻

28. Priority Order

priority_order represents the ordering of StockReportItems within a priority group.

It is user-controllable.

When an Item changes priority, it should automatically be inserted at the end of the destination priority group:

max(priority_order in destination priority) + 1

Changing priority_order explicitly should recalculate ordering within that priority group as required.

The implementation should preserve deterministic ordering.

The following details should be clarified before implementation:

* whether ordering must always remain contiguous;
* whether removing/moving an Item causes remaining order values to compact;
* whether priority = null always implies priority_order = null.

⸻

29. Proposed Services

The exact service structure should follow existing Manager architecture after repository investigation.

Conceptually, however, the following responsibilities are required.

⸻

29.1 StockTaskAssignment Transition Services

We need domain services responsible for allowed StockTaskAssignment transitions.

These services must:

1. validate the current assignment state;
2. validate the requested transition;
3. transition the assignment;
4. update the linked StockReportItem cached projections;
5. update relevant history semantics where required;
6. perform the operation atomically.

These should expose reusable atomic domain operations that can be called by:

* Task lifecycle orchestration;
* Scanner webhook orchestration;
* creation services;
* deletion services;
* recovery/backfill tooling.

Avoid duplicating transition arithmetic across callers.

⸻

30. StockTaskAssignment Creation

Creating a StockTaskAssignment requires:

* an existing Task;
* an existing Item;
* an existing StockReportItem;
* validation of assignment uniqueness.

Normally, creation begins with:

state = in_queue

However, the associated Task may already be in another state.

The creation service must inspect the current Task state and bring the StockTaskAssignment to the correct corresponding state using the same domain transition logic used elsewhere.

Do not directly fake the final counters.

For example, if the Task is already:

working

the resulting assignment should correctly become:

in_progress

through the appropriate domain behavior.

⸻

31. Task is_stock_assignment

Add a new column to:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task.py

Field:

is_stock_assignment: bool

Default:

false

Creating a StockTaskAssignment sets:

Task.is_stock_assignment = true

Deleting the relevant StockTaskAssignment restores:

Task.is_stock_assignment = false

This field exists primarily to support efficient Task queries later.

⸻

32. StockTaskAssignment Deletion

A StockTaskAssignment delete service must:

1. locate and validate the assignment;
2. determine its current state;
3. remove its contribution from the appropriate StockReportItem projection;
4. delete the assignment;
5. set the linked Task’s is_stock_assignment appropriately;
6. perform the operation atomically.

Projection correctness must be preserved.

⸻

33. StockReportItem Find-or-Create / Update Orchestration

We need a high-level StockReportItem orchestration service.

Given:

itemCategory
properties

it should resolve identity through:

item_category_id
properties_signature

If the StockReportItem exists, delegate the requested operation.

For Scanner stock-demand updates, this normally means updating:

quantity_requested

If the StockReportItem does not exist, create it using the incoming authoritative Scanner data.

This orchestration should not duplicate lower-level transition or history logic.

⸻

34. StockReportItem Deletion

Deleting a StockReportItem is explicitly destructive.

The delete operation should remove:

* the StockReportItem;
* linked StockReportHistoryRecords;
* linked StockTaskAssignments.

StockTaskAssignments must be removed through the appropriate domain deletion behavior so that:

* cached projections remain valid during the operation;
* linked Task is_stock_assignment values are updated correctly;
* domain invariants are preserved.

The complete destructive operation should follow repository transaction conventions.

⸻

35. Priority Services

Provide independent domain operations for:

change StockReportItem.priority

and:

change StockReportItem.priority_order

These are intentionally separate concerns and should have independent high-level endpoints.

Priority changes must also trigger the appropriate StockReportHistoryRecord behavior.

⸻

36. Local Manager API

Create a new endpoint family under:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/routers/api_v1

Proposed file:

stock_report.py

The exact router structure should follow existing repository conventions.

⸻

37. StockReportItem Mutation Endpoints

Provide local Manager endpoints for:

create StockReportItem
delete StockReportItem
change StockReportItem.priority
change StockReportItem.priority_order

Manager-local creation/deletion should be reviewed against Scanner ownership during planning to ensure there is no accidental conflict between administrative Manager actions and Scanner’s authority over stock demand.

⸻

38. StockTaskAssignment Mutation Endpoints

Provide endpoints for:

create one or multiple StockTaskAssignments
delete one or multiple StockTaskAssignments

Batch semantics should follow existing Manager conventions where possible.

⸻

39. Scanner → Manager Webhooks

Create a dedicated endpoint file:

location_tracker_webhooks.py

This endpoint family represents communication from Scanner/Location Tracker to Manager.

These endpoints must use API-key header authentication.

Scanner sends the configured API key through the protected request headers.

Manager validates it against:

MANAGER_API_KEY_TO_LOCATION_TRACKER_APP

Before implementing this authentication mechanism, inspect whether the repository already contains a reusable API-key authentication dependency/pattern.

⸻

40. Scanner Stock Demand Webhook

Create a webhook for Scanner to send authoritative StockReportItem demand.

Payload:

[
  {
    "itemCategory": "string",
    "properties": {
      "key": "value"
    },
    "quantityRequested": 0
  }
]

The endpoint uses the StockReportItem find-or-create/update orchestration.

For each entry:

itemCategory
→ resolve item_category_id
properties
→ normalize/sign
→ properties_signature
quantityRequested
→ quantity_requested

quantityRequested is authoritative state, not a delta.

Therefore:

quantity_requested = incoming quantityRequested

not:

quantity_requested += incoming quantityRequested

This provides natural idempotency for retries.

⸻

41. Scanner Awaiting-Resolution Webhook

Awaiting resolution is a separate concern and therefore uses a separate webhook.

Payload:

[
  {
    "article_number": "string"
  }
]

Scanner only needs to communicate article_number.

Manager is responsible for querying its own domain and finding the relevant eligible StockTaskAssignment.

Only assignments currently eligible for Scanner resolution should transition.

Conceptually:

awaiting → resolved

which consequently removes that assignment from the live:

quantity_awaiting

projection.

If the same Scanner operation is retried after the assignment has already become resolved, it must not decrement the projection again.

Claude should inspect the Item identity/cardinality semantics around article_number and confirm that the lookup can resolve the intended active assignment unambiguously.

⸻

42. Scanner Webhook Open Questions

Before implementation, clarify:

1. What should happen when Scanner provides an unknown itemCategory?
2. What should happen when article_number cannot resolve an eligible awaiting assignment?
3. What should happen if an article_number resolves ambiguously?
4. Are webhook batches atomic/all-or-nothing?
5. Or should valid entries succeed while invalid entries return per-item failures?

Prefer existing repository conventions where they already establish these semantics.

⸻

43. GET StockReportItems

Create a local GET endpoint for retrieving StockReportItems.

The endpoint accepts a comma-separated priority filter such as:

priority=high,medium,low

Priority sorting should conceptually be:

high
medium
low

and then:

priority_order

within each priority.

One behavior remains to clarify:

When the priority query parameter is omitted, should the endpoint return only priority IS NULL StockReportItems, or should it return all StockReportItems?

Do not infer this behavior during implementation without clarification.

⸻

44. StockReportItem Response Shape

Each StockReportItem should return approximately:

{
  "client_id": "...",
  "quantity_requested": 0,
  "quantity_in_queue": 0,
  "quantity_in_progress": 0,
  "quantity_awaiting": 0,
  "priority": "high",
  "priority_order": 1,
  "item_type": {
    "client_id": "...",
    "type_name": "...",
    "major_category": "..."
  }
}

The naming of item_type in the response should be reviewed now that persistence intentionally uses item_category_id.

Avoid introducing semantic confusion between ItemCategory and future ItemType concepts.

⸻

45. GET StockTaskAssignments

Create a GET endpoint for StockTaskAssignments.

It requires:

StockReportItem.client_id

and returns assignments belonging to that StockReportItem.

Proposed shape:

{
  "client_id": "...",
  "state": "in_progress",
  "stock_report_item_id": "...",
  "item": {},
  "task": {}
}

The Item and Task objects should use new compact serializers.

⸻

46. Compact Task Serializer

Create:

serialize_task_compact

Proposed fields:

client_id
task_type
priority
state
title
return_source
ready_by_at
return_method
created_at
updated_at
closed_at
completed_at

This serializer is intended eventually to replace existing oversized Task serialization used for list views.

For reference, investigate:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/queries/tasks/tasks.py

That broader migration is not part of this implementation.

Only create and use the compact serializer where required by the Stock Report capability.

⸻

47. Compact Item Serializer

Create:

serialize_item_compact

Proposed fields:

client_id
article_number
sku
quantity
item_category_snapshot
item_major_category_snapshot
item_images

For images, reuse the existing lightweight image serialization technique used by the Task query service:

"item_images": [serialize_image_light(img) for img in item_images]

The difference is that the Item compact serializer itself should own this image serialization responsibility.

⸻

48. Recovery and Reconstructability

A major architectural property of this system is that cached workflow quantities can be reconstructed.

For every StockReportItem:

quantity_in_queue
quantity_in_progress
quantity_awaiting

must be derivable from its StockTaskAssignments.

This should make it possible to build future:

* consistency checks;
* repair scripts;
* backfills;
* migration validation;
* operational diagnostics.

Do not make the cached projection itself the only record of workflow truth.

⸻

49. Testing Philosophy

Tests should primarily validate domain behavior.

Examples of meaningful tests include:

creating an assignment for a pending Task
→ assignment becomes in_queue
→ quantity_in_queue increases
Task begins working
→ assignment becomes in_progress
→ quantity_in_queue decreases
→ quantity_in_progress increases
Task becomes ready
→ assignment becomes awaiting
→ quantity_in_progress decreases
→ quantity_awaiting increases
Scanner resolves awaiting Item
→ assignment becomes resolved
→ quantity_awaiting decreases
Scanner retries the same resolution
→ no second decrement occurs
Task is reopened
→ assignment returns to the appropriate active state
→ projections are corrected
Scanner sends same quantity_requested twice
→ resulting quantity remains correct
quantity_requested decreases
→ no new quantity-requested history goal is created
quantity_requested increases
→ new history record is created
quantity_requested becomes zero
→ StockReportItem remains
equivalent properties with different JSON key order
→ resolve to the same StockReportItem

Tests should not become unnecessarily coupled to private implementation structure.

⸻

50. Repository Investigation Requirements

Before creating the final implementation plan, investigate at minimum:

Item models

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items/item.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items/item_category.py

Item enums

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/domain/items/enums.py

Task model

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task.py

Task query/serialization behavior

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/queries/tasks/tasks.py

Task state transitions

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/task_steps/transition_step_state_batch.py

Also investigate:

* Item.properties_signature;
* how property signatures are generated;
* existing transaction helpers;
* Task state derivation from TaskStep transitions;
* existing command/query separation;
* existing domain enum organization;
* API-key authentication patterns;
* batch endpoint conventions;
* migration conventions;
* event/realtime behavior;
* model relationship conventions;
* soft-delete conventions;
* existing serializers;
* existing test organization and fixtures.

⸻

51. Architectural Principle for Task Integration

Do not bolt Stock Report synchronization independently onto every endpoint that happens to change a Task.

Task state may be changed indirectly through TaskStep transitions and other domain workflows.

The existing Task state transition architecture must first be understood.

Determine the central authoritative integration point where a Task’s effective state change can reliably trigger StockTaskAssignment synchronization regardless of which API/service initiated the Task transition.

The two known transition services are:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/task_steps/transition_step_state.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/task_steps/transition_step_state_batch.py

Investigate their shared lower-level architecture before deciding where Stock Report behavior belongs.

⸻

52. Key Domain Invariants

The implementation should preserve these invariants:

1. Scanner is authoritative for quantity_requested.
2. Manager is authoritative for work execution state.
3. StockTaskAssignment.state is authoritative for Manager workflow quantities.
4. quantity_in_queue, quantity_in_progress, and quantity_awaiting are persisted cached projections.
5. Those projections must always be reconstructable from assignment state.
6. Projection changes and assignment state changes must be atomic.
7. Scanner retries must not double-apply state transitions or arithmetic.
8. quantity_requested = 0 does not delete a StockReportItem.
9. Decreasing quantity_requested does not create a new quantity-requested history goal.
10. Increasing quantity_requested creates a new quantity-requested history goal.
11. Historical awaiting accumulation does not decrease when Scanner resolves live awaiting assignments.
12. StockReportItem identity is (item_category_id, normalized properties).
13. JSON object key ordering must not affect StockReportItem identity.
14. A unique Item may have only one active StockTaskAssignment at a time.
15. Cancelled/failed Tasks must not contribute to active StockReportItem workflow projections.
16. Task reopening/backward transitions must be reflected in StockTaskAssignment state.
17. Manager workflow quantities may exceed Scanner quantity_requested.
18. Direct counter mutation should not bypass the StockTaskAssignment state-transition domain logic.

⸻

53. Open Questions Before Implementation

After investigating the repository, present findings and ask clarification questions before implementation where necessary.

At minimum resolve:

Priority ordering

Should priority orders always be contiguous?

For example:

1, 2, 3, 4

if 2 leaves the group, should the result become:

1, 2, 3

?
OWNER ANSWER =  ues it should be contiguous.

Should:

priority = null

always imply:

priority_order = null

?
OWNER ANSWER =  yes it means to priority_order also.

GET filtering

When no priority query parameter is provided, should the StockReportItem GET endpoint return:

only priority IS NULL

or:

all StockReportItems

?
OWNER ANSWER = only priority is null, and there is no default of priority when creating it, that is the point of returning null, for the user to understand what is missing to assign a priority. 

Scanner batch semantics

Should Scanner webhook batches be:

atomic / all-or-nothing

or support:

partial success with per-item errors

?
OWNER ANSWER =  atomic / all-or-nothing


Article-number resolution

Confirm how article_number maps to Items and whether the Scanner awaiting-resolution webhook can always unambiguously identify the intended eligible StockTaskAssignment.

OWNER ANSWER = this is map by Item.article_number

Cancelled/failed assignment representation

Determine how StockTaskAssignment should represent Tasks that leave the active workflow through cancelled or failed, while preserving the invariant that they contribute to none of the active quantity projections.

OWNER ANSWER = for this we can actually add one more state to the StockTaskAssignment.state which is failed for representing the task.state failed and cancelled ( i belive in this backend i only use the failed state no cancelled either way ), and marking that state on the StockTaskAssigment as failed should remove the quantiy_* that it was contributing on the StockReportItems instance

⸻

54. Expected Output Before Coding

Do not immediately implement this entire document.

First:

1. investigate the referenced repository architecture;
2. map this intention onto the existing architecture;
3. identify reusable components;
4. identify contradictions or unnecessary proposed structures;
5. identify missing domain cases;
6. explain any architectural changes you recommend;
7. ask the clarification questions necessary to remove ambiguity;
8. produce a phased implementation plan;
9. define the behavioral tests that establish completion criteria for each phase.

Once the intention and implementation plan are aligned, implementation can proceed phase by phase.

The goal is not simply to add three tables and several endpoints.

The goal is to establish a reliable Stock Report domain in which:

Scanner communicates demand, Manager coordinates the work required to satisfy that demand, assignment state remains the workflow source of truth, cached quantities provide efficient live projections, and history preserves the meaningful evolution of the stock goal.