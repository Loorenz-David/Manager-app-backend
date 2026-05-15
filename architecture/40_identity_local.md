# Identity - Local Extensions
> Extends: 40_identity.md

<!-- Scope: identity resolution, public ID strategy -->
<!-- Add app-specific fields, overrides, and decisions below. -->
<!-- Do NOT modify the canonical 40_identity.md directly. -->

## Added Fields

<!-- Example:
- `field_name: Type` - purpose and nullability
-->

## Overridden Behaviour

<!-- Document any behaviour that differs from the canonical contract. -->

## Local Decisions

<!-- Document app-specific design choices and the reasoning behind them. -->

- Added table prefix reservations for new domain models (PLAN_models_tables_20260515):
	- `uwp`: `UserWorkProfile`
	- `uss`: `UserShiftStateRecord`
	- `wsec`: `WorkingSection`
	- `wsme`: `WorkingSectionMembership`
	- `wsd`: `WorkingSectionDependency`
	- `wsic`: `WorkingSectionItemCategory`
	- `wsit`: `WorkingSectionSupportedIssueType`
	- `cus`: `Customer`
	- `chr`: `CustomerHistoryRecord`
	- `ist`: `IssueType`
	- `iss`: `IssueSeverity`
	- `icc`: `IssueCategoryConfig`
	- `itc`: `ItemCategory`
	- `itm`: `Item`
	- `iti`: `ItemIssue`
	- `iup`: `ItemUpholstery`
	- `iur`: `ItemUpholsteryRequirement`
	- `uph`: `Upholstery`
	- `uin`: `UpholsteryInventory`
	- `utp`: `UpholsteryInventoryThresholdPolicy`
	- `scst`: `StaticCost`
	- `tsk`: `Task`
	- `thr`: `TaskHistoryRecord`
	- `tev`: `TaskEvent`
	- `tno`: `TaskNote`
	- `tim`: `TaskItem`
	- `tsp`: `TaskStep`
	- `tsd`: `TaskStepDependency`
	- `ssr`: `StepStateRecord`
	- `tsar`: `TaskStepAssignmentRecord`

- Prefix conflict avoidance decisions:
	- `working_sections` uses `wsec` (not `ws_sec`) to satisfy no-underscore rule.
	- `working_section_memberships` uses `wsme` to avoid collision with existing `workspace_memberships` prefix `wsm`.
	- `working_section_supported_issue_types` uses `wsit` to avoid ambiguity with `wsic`.
