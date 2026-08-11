High-Level Intention — Item Cost Calculation, Production Budgeting, and Worker-Time Economics

Objective

Design and implement a complete item-cost and production-budgeting system for the ManagerBeyo application.

The system should allow managers to understand the expected and actual economic cost of restoring/working on an item, experiment with pricing and cost assumptions, and make better operational decisions.

It should also give workers meaningful production-time targets so they can understand:

* how much productive time an item can economically support,
* how much of that allowance has already been consumed,
* how their working time affects the remaining budget available to later workers or working sections,
* and when an item is approaching or exceeding its expected restoration cost.

The costing system must integrate with the application’s existing task, task-step, working-section, worker-time, item, and workspace architecture rather than creating a parallel operational model.

⸻

1. Existing Domain Context

The implementation must first be grounded against the live repository.

Relevant current concepts include:

Items

Item represents the physical/business item being worked on.

Tasks currently appear to operate with one item in normal use, but the task-item relationship already allows multiple items and the costing architecture must not assume permanently that a task contains exactly one item.

Existing item monetary fields should be reviewed rather than assumed to remain the authoritative location for the new costing model.

The new costing system should avoid turning Item itself into a large mutable economic-state object.

⸻

Tasks

A Task represents the business workflow involving one or more items.

Tasks have TaskItem relationships and contain multiple TaskStep records.

The costing implementation must understand how task type and task lifecycle relate to economic episodes such as:

* original restoration,
* return work,
* rework,
* or other future item-related production episodes.

Do not assume that one item can only pass through the production system once during its lifetime.

The task_type of the task model already defines why the item is passing through this pipe line. taks type "internal" is restoration in this document. task type "return" is the return referenced in this document. task type "pre-order" counts as restoration but it will be nice to have some difference when it comes to understanding the cost for granularity porpuses. keep in mind there is different types of task_type= return those types are enums at return_type, that granularity it will be nice also to have when it comes to looking at where the working cost came from.

⸻

Task Steps

Each TaskStep belongs to a WorkingSection.

Task steps represent the operational stages through which work passes.

Workers perform work against these task steps.

⸻

Step State Records

StepStateRecord records state transitions and time intervals for work performed against a task step.

These records are expected to be an important authoritative source for reconstructing actual worker time.

The costing system should derive actual production-time consumption from the existing operational records wherever possible rather than creating another independent time-tracking mechanism.

Research carefully:

* how WORKING intervals are currently represented,
* how pauses and ended-shift periods are represented,
* how worker attribution works,
* how inaccurate or corrected records are handled,
* how aggregate metrics on TaskStep are currently derived,
* and whether existing analytics already calculate worker-time totals that can safely be reused.

⸻

Working Sections

WorkingSection represents a production/work area.

Workers are linked to sections through WorkingSectionMembership.

The costing model needs the concept of a production-cost basis associated with either:

* a working section,
* a logical group of working sections,
* or another existing organizational concept if the repository already contains one more appropriate than introducing a new grouping entity.

Research this before selecting the model.

The original spreadsheet model refers to a fixed monthly production cost associated with a pipeline/group of workers.

Eventually this fixed cost may be derived from the application’s future compensation system, but that compensation implementation is explicitly outside the scope of this implementation.

For now, the costing system must support an independently configured production-cost basis.

⸻

User Work Profile

UserWorkProfile currently contains:

* salary_per_hour_before_tax
* salary_per_hour_after_tax

These fields are scheduled to be completely removed by another implementation.

They must NOT become dependencies of this costing implementation.

A separate compensation-domain implementation will eventually provide the inputs needed to derive working-section fixed cost.

Design this system so that such a future source can replace or feed the configured fixed-cost basis without requiring a redesign of the item-cost domain.

⸻

2. Economic Model

The initial costing model comes from an existing production spreadsheet.

The conceptual calculation is:

expected selling price
→ subtract/allocate non-production economic terms
→ determine the amount available for restoration/production
→ determine the productive-time cost basis from fixed production cost and utilization
→ convert the available restoration/production budget into total allowable worker-minutes
→ compare allowable worker-minutes against actual worker-minutes consumed.

Example:

Expected sale price:

3,500 SEK

Configured economic allocations might reserve:

* purchase cost ( this value will actually be stored in the same table as the expected sold price )
* materials,
* logistics,
* packaging,
* VAT,
* desired profit margin,
* and future cost categories.

If those consume 75% of the expected selling price, the remaining 25% represents the amount economically available for restoration.

For a 3,500 SEK item:

3,500 × 25% = 875 SEK

That 875 SEK becomes the production/restoration allowance.

The production system then determines the monetary cost of productive time from its configured fixed production cost and utilization assumptions.

Example:

400,000 SEK fixed monthly production cost

with:

160 paid hours per month

and:

80% assumed productive utilization

means the cost model treats 80% of the paid monthly time as productive capacity available to restoration work.

The number of workers must not be required to derive the item’s underlying total allowable worker-minute budget.

In the original spreadsheet, worker count appeared inside an intermediate calculation and was then multiplied back into the result, causing it to cancel mathematically. The implementation should therefore model the economically meaningful output directly: the aggregate worker-minute allowance that the item can consume.

The number of workers or working sections becomes relevant only after that total allowance has been calculated, when the system needs to present or allocate the available time operationally.

Initially, the UI may divide the total allowance into simple illustrative fractions across the participating workers or working sections. This division is not part of the underlying economic calculation and must not imply that every working section inherently requires the same amount of time.

For example:

If an item has:

80 allowable worker-minutes

and currently passes through four working sections, an initial simple representation could display:

20 minutes per working section

for orientation.

However, this is only a temporary equal distribution of the total allowance.

A later implementation should introduce working-section ratios so that the total worker-minute allowance can be distributed according to the actual expected effort of each stage given the item and the item issues recorded.

For example, if historical or configured ratios eventually establish:

* woodworking: 15%
* sanding: 20%
* preparation: 10%
* upholstery: 55%

then the same 80 worker-minute item allowance could be represented as:

* woodworking: 12 expected worker-minutes
* sanding: 16 expected worker-minutes
* preparation: 8 expected worker-minutes
* upholstery: 44 expected worker-minutes

Total:

80 worker-minutes

These ratios may eventually be configured explicitly, derived from historical production data, or use a combination of both. The ratio implementation is a later concern; the current architecture should simply avoid assuming that equal division is the economic model.

Actual worker-minutes consumed by the item’s workflow must always be measured against the aggregate item allowance regardless of how that allowance is visually or analytically distributed between workers or working sections.

This distinction is important:

The aggregate worker-minute allowance is the economic constraint.

The working-section allocation is an operational distribution of that constraint.

⸻

3. Worker-Minutes vs Elapsed Time

The implementation must explicitly distinguish between:

Elapsed time

Clock time during which work is being performed.

Worker-minutes

The aggregate amount of worker capacity consumed.

For example:

4 workers × 10 minutes = 40 worker-minutes.

1 worker × 40 minutes = 40 worker-minutes.

The economic resource being consumed should primarily be modeled as worker-minutes unless repository research demonstrates that the current business process requires another basis.

Avoid reproducing misleading spreadsheet terminology such as treating aggregate worker-minutes as “minutes per worker.”

⸻

4. Cost Configuration

Managers must be able to configure the economic assumptions used by the calculator.

Do not model this as a single hard-coded set of percentage columns.

The configuration should be extensible enough to support different economic term types such as:

* percentage of expected sale price,
* fixed monetary amount,
* actual item-specific cost,
* per-item amount,
* per-worker-minute cost,
* or other future calculation bases.

Examples include:

* purchase cost,
* materials,
* logistics,
* packaging,
* tax/VAT allocation,
* desired profit,
* production/restoration allocation,
* future operational costs.

Research existing repository conventions for:

* money,
* currency,
* enums,
* effective-dated records,
* auditability,
* immutable snapshots,
* configuration,
* and workspace ownership.

The user must be able to modify these assumptions over time without retroactively changing the economics of already committed item evaluations.

⸻

5. Effective-Dated Cost Configuration

Changes to committed costing assumptions must be versioned/effective-dated.

Conceptually:

effective_from
effective_to

with only the appropriate current version remaining open.

Do not blindly implement global “one open row” semantics.

Determine the correct uniqueness scope from the domain being modeled.

Historical items must remain explainable using the exact assumptions that were active when their economic evaluation was committed.

Changing a configuration must not silently rewrite historical item economics.

⸻

6. Utilization

Utilization must be treated as an explicit concept.

There are potentially two different values:

Planning utilization

A manager-controlled assumption such as:

80%

meaning that only 80% of paid capacity is expected to become productive task work.

Observed utilization

A metric reconstructed from real operational data such as:

productive working time / available paid working time.

The existing application already records worker shifts and actual working periods.

Research whether observed utilization can be reconstructed reliably from current records.

Do not collapse assumed utilization and observed utilization into the same value.

The costing model may initially use configured planning utilization while allowing observed utilization to be surfaced analytically and potentially become a future source for projections.

⸻

7. Item Economic Episodes

An item’s economic history should not be stored directly as mutable columns on Item.

The item may pass through multiple independent production/cost episodes during its lifetime.

Examples:

* original restoration,
* customer return,
* rework,
* warranty work,
* future other operational episodes.

The architecture should therefore distinguish the physical Item from its economic episodes.

Research whether these episodes should:

* map onto existing Task / TaskType semantics,
* be their own entity linked to Task and Item,
* or use another existing lifecycle concept.

Avoid duplicating business concepts that the repository already represents.

⸻

8. Restoration and Return Economics

Restoration work and return work need to remain analytically distinguishable.

For example:

Item lifetime:

Original restoration:

* expected cost,
* actual cost,
* worker-minutes,
* variance.

Return #1:

* expected cost,
* actual cost,
* worker-minutes,
* variance.

Return #2:

* expected cost,
* actual cost,
* worker-minutes,
* variance.

Analytics should then be able to aggregate these into:

lifetime production cost

while still preserving the separation for drill-down analysis.

Do not assume that RESTORATION and RETURN necessarily require physically separate database tables.

Research whether they share the same lifecycle and data structure and could instead be represented as typed economic episodes.

If their domain behavior is materially different, subtype-specific structures may be justified.

⸻

9. Item Cost Evaluation / Snapshot

When an economic projection is committed for an item episode, the system must preserve the exact inputs and derived values used at that moment.

The snapshot may conceptually include values such as:

* expected sale price,
* purchase cost/value used,
* cost configuration/version,
* fixed production-cost basis,
* utilization basis,
* relevant currency,
* available restoration/production budget,
* calculated cost per worker-minute,
* allowed worker-minutes,
* calculation timestamp,
* calculation/model version.

Exact schema should be determined after repository research.

The important invariant is:

Historical evaluation must remain understandable even if its source configuration or current item values later change.

⸻

10. Actual Cost Result

While work is running, the application should derive current actual consumption from authoritative task/task-step/state records.

The system should support current calculations such as:

* worker-minutes consumed,
* monetary production cost consumed,
* percentage of allowed production budget consumed,
* remaining worker-minutes,
* remaining production budget,
* projected overrun,
* current variance.

When the relevant item episode completes, the system should preserve an appropriate final result.

Research whether this should:

* complete fields on the committed evaluation,
* create an immutable result record,
* or reuse an existing analytics/snapshot convention.

The architecture must keep expected values and actual values distinguishable.

⸻

11. Reconstruction

The system should be as reconstructible as practical.

Authoritative operational facts such as actual worker time should remain in the existing work-record system.

Cost snapshots should preserve the assumptions necessary to reproduce the economic calculation.

Derived analytics should not become the only source of truth if they can safely be recomputed.

Research the repository’s current aggregate/recompute conventions before deciding what values are stored versus derived.

⸻

12. Cost Projections / What-If Scenarios

Managers need to be able to experiment with an item’s economics without polluting committed version history.

For example, an item may be taking longer than anticipated.

The manager should be able to test:

* expected sale price 3,500 SEK,
* expected sale price 3,800 SEK,
* expected sale price 4,200 SEK,

and immediately see the resulting:

* restoration budget,
* allowed worker-minutes,
* expected margin,
* remaining capacity,
* profitability consequences.

These experiments should NOT automatically create new effective versions.

Introduce a clear distinction between:

Projection / scenario

“What if we used these assumptions?”

and:

Committed economic version

“These are the assumptions we actually decided to operate against.”

The user should be able to create/retain useful projections, compare them, and select one.

Selecting/promoting a projection should create the next committed economic evaluation/version according to the final architecture.

Research whether projections should be persisted, temporary, or support both saved and ephemeral scenarios.

⸻

13. Expected Sale Price

Expected sale price should be a first-class input to the economic evaluation.

The manager may intentionally raise the expected sale price if restoration requires more work.

Changing expected sale price changes the amount economically available for production according to the active cost model.

This must support interactive scenario calculations.

Do not assume expected sale price belongs permanently as a mutable field directly on the canonical Item.

Research existing item-value semantics such as item_value_minor and determine whether they represent the same concept or something distinct.

Avoid introducing duplicate semantic fields without understanding the existing model.

⸻

14. Purchase Cost

Likewise, investigate existing Item.item_cost_minor.

Determine:

* what it currently means,
* where it is written,
* where it is read,
* whether it represents actual purchase/acquisition cost,
* whether it is historical or mutable,
* and whether it can safely feed the new cost calculation.

The costing snapshot should preserve the purchase-cost value actually used by the evaluation regardless of where the live/current value originates.

⸻

15. Working-Section Cost Basis

The spreadsheet currently models a fixed monthly cost for a production pipeline.

The application already has working sections and working-section memberships.

Research how best to represent the economic cost basis.

Possible eventual concepts include:

* cost per working section,
* cost shared across multiple working sections,
* a production cost group containing several working sections,
* calculated employee compensation totals,
* additional fixed overhead.

Do not choose one before inspecting existing architecture.

The design should make it possible for a future compensation implementation to feed these values automatically.

For this implementation, managers must still be able to configure the required cost values independently.

Note: at the moment the one that weights the most is the capability of grouping working sections and assigning a fixed cost to that group. but as it is mentioned in this document later adaptations will change this and they should not influence the item cost domain, this should be a flexible and scalable piece in the domain.

⸻

16. Multiple Workers and Multiple Working Sections

Do not assume each item uses exactly one worker or that all sections deserve equal time.

An item’s total allowed worker-minute budget may be consumed unevenly.

Example:

Total allowance:
67 worker-minutes

Actual:

* preparation: 8
* woodworking: 22
* sanding: 14
* upholstery: 28

Total:
72 worker-minutes

The economic concern is the aggregate consumption.

However, analytics should allow managers to identify which sections or workers contributed to an overrun.

Do not automatically divide total allowed worker-minutes equally between workers or sections.

If section-level expected allocations are introduced, they should be explicit configuration or derived historical expectations rather than an accidental consequence of worker count.

⸻

17. Multiple Items per Task

Although current workflow commonly has one item per task, the existing relationship allows multiple items.

The design must establish how actual task-step work is attributed when a task contains multiple items.

Research current TaskItem, batch-working, and task-step behavior.

Questions that must be answered include:

* Is a step performed for the whole task or individually per item?
* Can one state record represent work performed simultaneously on several items?
* Does allows_batch_working already affect this?
* Are aggregate seconds currently divided, duplicated, or assigned another way?
* How should production cost be allocated between items during batch work?

Do not design the costing system around the current one-item happy path if the schema already permits multi-item tasks.

⸻

18. Worker Experience

The resulting APIs/domain should eventually support worker-facing information such as:

* expected worker-minute allowance for the item,
* time consumed so far,
* percentage consumed,
* time remaining,
* whether the item is within target,
* whether current work is consuming budget expected by later stages,
* possibly section-specific guidance if such allocation exists.

The goal is not to punish individual workers based on simplistic timing.

The metric should help workers understand how their work contributes to the total production economics of the item and how overruns propagate through the remaining workflow.

⸻

19. Manager Experience

Managers should eventually be able to see:

At item level:

* current expected sale price,
* expected production budget,
* actual production cost,
* expected vs actual worker-minutes,
* variance,
* profitability impact,
* projections/scenarios,
* restoration vs return costs,
* lifetime cost.

At working-section level:

* worker-minutes consumed,
* expected vs actual consumption,
* cost contribution,
* utilization,
* recurring overruns.

At aggregate level:

* cost by section,
* cost by item category,
* restoration cost,
* return cost,
* total lifetime work cost,
* expected vs actual,
* utilization trends,
* profitability impact.

This intention does not require all analytics UI to ship immediately, but the domain model must not prevent these views.

⸻

20. Currency and Money

Follow the repository’s established money conventions.

Current item models appear to use integer minor units with an item currency enum.

Do not introduce floating-point monetary storage.

Research existing money/currency patterns across the repository and use the canonical convention.

Percentages/rates should likewise follow existing Numeric/Decimal conventions rather than binary floats.

⸻

21. Auditability

Important costing decisions must be attributable.

Research existing conventions for:

* created_at
* created_by_id
* updated_at
* updated_by_id
* effective-dated records
* soft deletion
* immutable snapshots
* supersession
* correction workflows.

A future reader should be able to answer:

* What cost model was active?
* Which assumptions were used?
* Who committed them?
* When did they take effect?
* Was this a scenario or an applied decision?
* What did we originally expect?
* What actually happened?
* Was the calculation later corrected/recomputed?

⸻

22. Versioning Semantics

Do not use “version” as a generic solution for every change.

The implementation should distinguish at least:

Configuration version

Changes to workspace/production economic assumptions.

Economic episode

A real item lifecycle event such as restoration or return.

Committed evaluation version

A change in the economic decision applied to an existing episode.

Projection/scenario

An exploratory calculation that has not been committed.

Actual result

The operational outcome.

These concepts should not collapse into a single generic version table unless repository research demonstrates a clean and explicit representation.

⸻

23. Derived vs Stored Values

For every proposed field, determine whether it is:

* authoritative input,
* immutable snapshot input,
* derived live value,
* cached aggregate,
* final historical result,
* or reconstructible analytics.

Avoid persisting values merely because the UI needs them.

At the same time, preserve historical snapshots where recomputation from today’s mutable configuration would produce a different answer.

⸻

24. Integration With Existing Aggregates

TaskStep already contains aggregate metric mixins, including cost-related aggregate fields.

Research those structures thoroughly.

Determine:

* what costs they currently represent,
* how they are recalculated,
* whether they use user salary fields,
* whether they are operational analytics or authoritative data,
* and whether the new item-cost model should consume, replace, extend, or remain separate from them.

Do not build duplicate aggregate machinery without understanding the existing pipeline.

⸻

25. Out of Scope / Boundary Conditions

For this implementation:

* do NOT implement the future compensation system,
* do NOT make the current UserWorkProfile.salary_per_hour_before_tax or salary_per_hour_after_tax part of the new architecture,
* assume those salary fields will be removed separately,
* do not redesign the whole task/work-record system unless costing exposes a real architectural gap,
* do not prematurely build every possible analytics screen,
* do not hard-code the spreadsheet literally into the domain.

The spreadsheet defines the initial economic intention, not necessarily the final schema.

⸻

26. Required Repository Research

Before producing the implementation plan, perform a thorough architecture exploration.

At minimum inspect:

* Item
* TaskItem
* Task
* TaskStep
* StepStateRecord
* task-step aggregate metric mixins
* working-section models
* working-section membership
* shift/work-time models
* worker-time aggregation services
* item creation/update flows
* task creation flows
* return task flows
* batch-working behavior
* item monetary fields and all usage sites
* existing cost analytics
* workspace configuration patterns
* effective-dated/versioned tables
* partial unique index conventions
* money/currency conventions
* Numeric/Decimal conventions
* enums
* migrations
* serializers/schemas
* API endpoints
* frontend item/task/worker/manager views that would be impacted.

Also search every usage of:

* item_value_minor
* item_cost_minor
* salary fields
* aggregate cost fields
* aggregate working seconds
* task item relationships
* allows_batch_working
* return task types
* task completion/closure
* task-step completion/closure.

⸻

27. Deliverable From This Exploration

Do NOT begin implementation yet.

Produce a grounded implementation intention/architecture plan based on the actual repository.

The response should identify:

1. Existing architecture that can be reused.
2. Existing architecture that conflicts with or constrains this intention.
3. The proposed domain boundaries.
4. Proposed entities and relationships.
5. What remains on Item versus what moves into cost/evaluation structures.
6. Cost configuration and effective-dating strategy.
7. Economic episode strategy.
8. Projection/scenario strategy.
9. Actual worker-time reconstruction strategy.
10. Multi-item task allocation strategy.
11. Batch-work implications.
12. Working-section cost-basis strategy.
13. Money/rate representation.
14. Expected vs actual snapshot strategy.
15. Recalculation and correction semantics.
16. Database invariants and uniqueness constraints.
17. Migration implications.
18. Backend/service/API impact.
19. Frontend impact.
20. Analytics/recompute impact.
21. Compatibility with the future compensation implementation.
22. Risks, ambiguous domain decisions, and questions that genuinely need a product decision.

For important design choices, explicitly state:

* what the repository currently does,
* what implementation you recommend,
* why,
* and what alternative you rejected.

The final plan should preserve the central domain distinction:

Projections answer “what if?”

Committed evaluations answer “what did we decide to operate against?”

Operational work records answer “what actually happened?”

Analytics answer “what does that mean across items, workers, working sections, and time?”