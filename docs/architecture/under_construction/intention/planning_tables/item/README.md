# Item Domain Planning Contracts

Status: DRAFT - Initial Structured Split
Domain: item
Created: 2026-05-14
Updated: 2026-05-14

## Objective

Transform first-pass operational scratch planning into stable, focused planning contracts that preserve:
- registry vs runtime separation
- replay-safe lifecycle modeling
- workspace ownership boundaries
- future integration compatibility (task runtime, inventory, ordering, analytics)

## Loaded Contract Intent

Primary:
- 01 architecture
- 03 models
- 08 domain
- 21 naming conventions
- 24 multi tenancy
- 40 identity
- 42 event

Supporting:
- 46 serialization
- 25 soft delete
- 36 audit log

## Planning Files

- item_models.md
- item_issue_models.md
- item_upholstery_models.md
- item_category_models.md
- issue_type_models.md
- issue_category_config_models.md
- upholstery_requirement_models.md

## Relationship to Existing Working Section Plan

The working-section capability bridges were already planned in:
- planning/working_sections/working_section/working_section_models.md

This item domain planning references those bridges and does not duplicate them.

## Scope Positioning

In scope:
- registry entities and lifecycle entities for item operations
- configuration entities for category and issue timing behavior
- stable relational ownership boundaries

Out of scope:
- implementation code
- migration files
- runtime orchestration and queue systems
- analytics materialization pipelines
