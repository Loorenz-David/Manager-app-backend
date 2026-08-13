# Item economics tables

These tables hold the versioned production-cost configuration, immutable valuation
history, and the snapshots used to calculate an item's economics. The models are a
schema boundary only: commands and the canonical calculator own their write rules.

- `production_cost_groups` and `production_cost_group_sections` identify the
  workspace's production grouping and its active working-section memberships.
- `production_cost_basis_versions` and `cost_model_versions` are effective-dated,
  soft-deletable configuration chains. Their open-row partial indexes are the database
  arbiters of chain uniqueness.
- `cost_model_terms` describes an immutable allocation rule. Its soft-delete fields
  exist for house-style compatibility; v1 commands do not use them to edit a version.
- `item_valuations` is immutable price/cost history; a change creates a superseding row.
- `item_cost_evaluations`, their term snapshots, and `item_cost_results` preserve the
  inputs and outputs needed to explain a single task episode without re-reading live
  configuration.

The group category column reuses the PostgreSQL `item_major_category_enum` type owned by
`item_categories.major_category`; it must use `create_type=False` here. The four currency columns use three PostgreSQL enum types: `item_valuations.currency`
and `item_cost_evaluations.currency` share `item_valuation_currency_enum`, owned by
`item_valuations`; `production_cost_basis_versions.currency` and
`cost_model_versions.currency` own their respective types. Evaluation and result task
snapshots reuse the enum types owned by `tasks`; migrations must not create or drop
those reused types.
