

Raw Intention: Temporal Worker Compensation & Cost Model

Introduce a compensation domain that separates the worker’s operational profile from their employment compensation, preserves historical compensation changes, normalizes different contract payment models into a common hourly basis, and exposes a stable estimated_cost_per_hour for downstream cost analytics.

The primary analytics contract should be:

worker + point in time
        ↓
applicable UserCompensation
        ↓
estimated_cost_per_hour
        ↓
worked duration
        ↓
labor cost attributed to analytics AggregateMetricsCostMixin for all the analytics table as part of the workers cost. ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/analytics )

1. Separate compensation from UserWorkProfile 

UserWorkProfile should remain focused on the worker’s workspace/operational identity.

Move compensation-specific concepts ( columns: salary_per_hour_before_tax and salary_per_hour_after_tax ) out of it and introduce:

UserWorkProfile
    │
    └── UserCompensation [1:N over time]

A worker may therefore have multiple compensation records historically, but normally only one compensation record applicable at a given point in time.

Each UserCompensation represents one effective version of the worker’s compensation arrangement.

Core concepts:

UserCompensation
    user_work_profile_id
    effective_from
    effective_to
    compensation_type
    base_compensation_amount
    currency
    contracted_hours_per_week / normalization inputs
    gross_hourly_equivalent
    estimated_cost_per_hour
    created_at
    created_by
    ...

The implementation research should determine whether existing temporal/versioning conventions in the codebase should be reused rather than introducing a new pattern.
I know we already have a function which the analitics worker uses to calculate the states and hours for those states into the analitcs table, we will be expaning the function used for calculating the cost analitics for worker cost ( in the future i will add other costs which will be added as separate cost from the worker hourly cost, like static cost per hour )

2. Preserve the compensation exactly as contractually defined

Do not force every worker’s contract to be represented as hourly.

base_compensation_amount + compensation_type represent the actual gross compensation agreement.

Initial types should likely support at least:

HOURLY
MONTHLY
ANNUAL

For example:

Hourly employee:
type   = HOURLY
amount = 200 SEK
Monthly employee:
type   = MONTHLY
amount = 35,000 SEK
Annual employee:
type   = ANNUAL
amount = 480,000 SEK

The stored contractual value is gross compensation (bruttolön), before employee income-tax withholding.

Employee preliminary income tax is not part of estimated_cost_per_hour; it concerns how gross compensation is divided between payment to the employee and payment to Skatteverket.

3. Normalize all compensation into gross_hourly_equivalent

Create a domain calculation that translates each supported compensation model into a normalized gross hourly rate.

Conceptually:

compensation_type
+
base_compensation_amount
+
normalization parameters
        ↓
gross_hourly_equivalent

Examples:

HOURLY:
200 SEK/hour
→ 200 SEK/hour
MONTHLY:
35,000 SEK/month
+ 40 contracted hours/week
→ normalized hourly equivalent
ANNUAL:
480,000 SEK/year
+ 40 contracted hours/week
→ normalized hourly equivalent

The implementation plan should explicitly define and test the normalization conventions rather than scattering formulas through services.

gross_hourly_equivalent becomes the common input to employer-cost calculations, regardless of contract type.

4. Model additional worker costs as compensation components

A UserCompensation should have zero or more associated cost components.

Conceptually:

UserCompensation
    │
    ├── UserCompensationComponent
    ├── UserCompensationComponent
    └── UserCompensationComponent

A component represents an additional employer cost or cost rule.

It should be capable of representing different calculation mechanisms, for example:

PERCENTAGE_OF_GROSS
FIXED_PER_HOUR
FIXED_PER_MONTH
FIXED_PER_YEAR

Potential components include:

arbetsgivaravgift
vacation / semester cost
occupational pension
insurance
contractual employer costs
company-policy costs
other relevant employment costs

Do not assume every component is manually configured.

The model should distinguish the origin/rule source where useful:

STATUTORY
CONTRACT
COMPANY_POLICY
MANUAL

In particular, statutory costs such as arbetsgivaravgift should eventually be resolved from applicable rules and worker context rather than treated as a permanently hard-coded percentage. 

5. Normalize every component into hourly cost

Every component must ultimately expose an hourly equivalent.

The calculation pipeline should therefore be:

base compensation
        ↓
gross_hourly_equivalent
        │
        ├── component A → hourly equivalent
        ├── component B → hourly equivalent
        ├── component C → hourly equivalent
        └── ...
        ↓
estimated_cost_per_hour

Formally:

estimated_cost_per_hour
    =
gross_hourly_equivalent
    +
sum(component_hourly_costs)

The compensation domain owns this calculation.

Downstream analytics should not need to understand monthly salaries, pensions, employer-contribution percentages, vacation calculations, etc.

6. Make estimated_cost_per_hour the analytics boundary

Other domains should consume:

estimated_cost_per_hour

rather than reconstruct worker compensation themselves.

For example:

Worker A
estimated_cost_per_hour = 200 SEK
worked = 1 hour
Worker B
estimated_cost_per_hour = 200 SEK
worked = 1 hour
item labor cost = 400 SEK

This allows task, item, production, working-section, profitability, and other analytics to share one consistent labor-cost abstraction.

7. Make compensation effective-dated

A compensation record represents a set of terms applicable over an interval:

effective_from <= time < effective_to

with effective_to = NULL representing the currently open version.

Example:

Compensation v1
2026-01-01 → 2026-08-31
35,000 SEK/month
Compensation v2
2026-09-01 → open
38,000 SEK/month

Analytics for a historical activity must resolve the compensation applicable when the activity occurred, not simply use the worker’s current compensation.

The implementation should enforce the invariant that compensation periods for the same work profile cannot unintentionally overlap.
the UserWorkProfile should have a quick rel to the current active UserCompensation to obtain that instance fast during the live adquisition for processing analytics

8. Distinguish contract changes from corrections

The system needs two intentionally different mutation semantics.

Contract change

A genuine change in compensation:

old compensation
effective_to = change date
new compensation
effective_from = change date

Past analytics remain based on the previous compensation.

Historical correction

The recorded compensation was wrong but the actual contract had not changed.

Example:

stored: 35,000
actual: 36,000

The correction may apply retroactively and require recalculation of affected historical analytics.

The implementation research should identify how recalculation/invalidation is currently handled elsewhere in the application before deciding the exact mechanism.

9. Snapshot calculated cost when work becomes historical

Historical work-cost records should not depend exclusively on dynamically reading the current compensation calculation.

When labor cost is materialized, retain both:

reference to UserCompensation
+
cost values actually used

For example:

WorkerCostSnapshot / existing appropriate work record
user_compensation_id
gross_hourly_equivalent_snapshot
estimated_cost_per_hour_snapshot
worked_duration
total_labor_cost

The reference provides provenance.

The snapshot preserves the historical calculation.

This prevents future changes to formulas, statutory rules, compensation components, rounding rules, or data corrections from silently rewriting historical analytics.

A deliberate recalculation operation may replace those snapshots when explicitly requested.

10. Treat derived values as caches, not source-of-truth inputs

These fields:

gross_hourly_equivalent
estimated_cost_per_hour

are derived values.

The authoritative inputs are:

base compensation
compensation type
normalization terms
components
worker/statutory context
effective date

It is acceptable to persist the derived values for fast analytics access, but there should be one canonical calculation path that produces them.

Avoid allowing ordinary API consumers to independently modify the cached values.

11. Keep statutory rules separate from employment contracts

Do not encode Swedish statutory payroll logic directly into UserCompensation rows where avoidable.

The eventual conceptual separation should be:

Worker compensation
    contractual facts
Worker/work profile
    relevant worker context
Statutory payroll rules
    effective-dated government rules
Cost calculator
    combines all of the above

This allows a statutory rate to change without pretending the worker signed a new employment contract.

For the first implementation, Claude should investigate how much of this abstraction is justified now versus what can remain an extension point.

12. Migration and compatibility intent

The current model contains:

salary_per_hour_before_tax
salary_per_hour_after_tax

The implementation plan should research every read/write/use of those fields before proposing migration.

Desired semantic destination:

salary_per_hour_before_tax
    → migrate into the appropriate initial UserCompensation,
      probably as HOURLY gross compensation where existing semantics support it
salary_per_hour_after_tax
    → do not blindly migrate to estimated_cost_per_hour;
      first determine its actual current meaning and usage

Existing historical data must not be assigned new semantics without evidence from the codebase.

This columns are known to be referenced  in mutliple parts of the application but none of them are surfaced to the frontend, this was an old implementation with some idea of what it could be, we are now developing what it actually should be.

⸻

Implementation-maker objective

The Claude implementation-maker should not implement directly from this document. It should first inspect the current models, migrations, schemas, services, payroll/worker calculations, work-time records, item/task costing, analytics pathways, and existing temporal/versioning conventions.

Its resulting re-make of this intention plan should answer:

1. What existing code owns worker compensation today?
2. Where are the two current salary fields read and written?
3. What records currently represent worked duration and historical labor?
4. Where should UserCompensation and components live in the domain structure?
5. What existing enum / money / temporal patterns should be reused?
6. How should effective-period overlap be prevented?
7. What should be computed dynamically versus persisted?
8. Where should historical cost snapshots live?
9. What must be migrated?
10. What APIs/schemas/frontend consumers will break or need transition?
11. What tests establish the normalization and temporal invariants?
12. What should belong to this implementation versus a later statutory
    payroll-rule engine?

The central invariant for the whole implementation is:

Contractual compensation
        +
applicable cost rules
        ↓
normalized worker cost/hour
        ↓
snapshot when consumed by historical work

