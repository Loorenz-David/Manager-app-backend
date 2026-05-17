# `maybe_begin` Transaction Utility — Implementation Summary

Plan ID: `PLAN_maybe_begin_transaction_utility_20260517`
Status: Completed
Completion Date: 2026-05-17
Owner Agent: Claude Sonnet 4.6

## Overview

Introduced a `maybe_begin` async context manager that makes item-level commands composable inside parent transactions without triggering SQLAlchemy's nested-begin error. In owner mode (no active transaction) it behaves identically to `async with ctx.session.begin()`. In subordinate mode (transaction already open) it yields bare — no begin, no commit, no rollback — so the parent's single commit covers all writes from the full call chain.

## Delivered Changes

### New files

- `backend/app/beyo_manager/services/commands/utils/__init__.py` — empty package init
- `backend/app/beyo_manager/services/commands/utils/transaction.py` — `maybe_begin` async context manager
- `backend/architecture/06_commands_local.md` — local contract companion documenting the propagation-aware transaction pattern, session call safety table, event emission rule for subordinate commands, and invariants

### Updated files

- `backend/app/beyo_manager/services/commands/items/create_item_upholstery.py` — import added, `ctx.session.begin()` replaced
- `backend/app/beyo_manager/services/commands/items/update_and_delete_item_upholstery.py` — import added, both occurrences replaced
- `backend/app/beyo_manager/services/commands/items/mark_requirements_in_use.py` — import added, replaced
- `backend/app/beyo_manager/services/commands/items/mark_requirements_completed.py` — import added, replaced
- `backend/app/beyo_manager/services/commands/items/mark_requirements_ordered.py` — import added, replaced
- `backend/app/beyo_manager/services/commands/items/resolve_requirements_after_stock.py` — import added, replaced
- `backend/app/beyo_manager/services/commands/items/apply_surplus_to_requirement.py` — import added, replaced
- `backend/app/beyo_manager/services/commands/items/set_requirement_quantity.py` — import added, replaced
- `backend/app/beyo_manager/services/commands/items/complete_single_and_reallocate.py` — import added, both occurrences replaced
- `backend/task_system/backend_contract_goal_mapping_guide.md` — core contracts section updated to pair `06_commands_local.md` alongside `06_commands.md` (same pattern as `07_queries_local.md`)

## Behavior and Contract Compliance

- `session.in_transaction()` (SQLAlchemy 2.0.40, stable API) is used to detect owner vs. subordinate mode.
- Owner mode: `async with session.begin()` opened internally; commit fires on normal block exit; rollback fires on exception — identical behavior to the canonical contract's `ctx.session.begin()` pattern.
- Subordinate mode: bare `yield`; no session call made; transaction stays open; parent's `maybe_begin` is the single commit point.
- All existing `flush()` calls preserved — they are needed to obtain `client_id` before linking related rows.
- No business logic changed in any of the 9 refactored files.
- Local contract `06_commands_local.md` extends canonical `06_commands.md` without modifying it; opens with `> Extends: 06_commands.md` per the app-specific extension protocol.

## Validation Results

- `grep -rn "ctx.session.begin" backend/app/beyo_manager/services/commands/items/` → zero matches.
- Import smoke test: `.venv/bin/python -c "from beyo_manager import create_app; create_app()"` → `OK`.
