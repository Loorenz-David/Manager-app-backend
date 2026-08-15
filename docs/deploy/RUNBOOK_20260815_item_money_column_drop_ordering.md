# Deploy ordering — the item money column drop (`be9dfe42a035`)

**Deploy the code first. Run the migration second. Never the other way round.**

## The hazard

`be9dfe42a035_drop_legacy_item_money_columns` drops three columns from `items`:

- `item_value_minor`
- `item_cost_minor`
- `item_currency`

The previous release's ORM model still declares those columns, so **every** query it
issues against `items` names them in its `SELECT` list. The moment the migration lands,
any process still running the old code raises `UndefinedColumnError` on every item read —
item lists, task detail, upholstery reads, customer detail. Not a degraded response: a
500 on the whole surface, for as long as that process lives.

A rolling deploy is exactly the window where an old process is still serving traffic while
the schema has already moved.

## The required order

1. **Deploy the new code and let every serving process restart onto it.** The new ORM does
   not declare the three columns, so it is correct against both the old schema (columns
   present, unread) and the new one (columns gone).
2. **Then run `alembic upgrade head`.**

Step 1 is safe to sit at for as long as you like — the columns are simply ignored. There
is no window in which the new code needs the columns dropped.

Reversing the order gives you an outage whose length is however long the slowest old
process takes to cycle.

## Verifying before the migration

Confirm no serving process is on the previous release. On a rolling platform that means
every instance reports the new build; on this repository's deploy, it means the push has
completed its restart of all services before the migration step runs.

## The general rule

This is not specific to these three columns. **A destructive schema change (drop column,
drop table, rename) is deployed in two steps, code first.** An additive change (add
nullable column, add table) is the mirror image: migrate first, deploy second. Both orders
exist so that at every instant, the code that is running is valid against the schema that
is live.
