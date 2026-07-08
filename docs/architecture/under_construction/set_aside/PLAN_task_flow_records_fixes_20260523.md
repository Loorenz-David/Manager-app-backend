# PLAN_task_flow_records_fixes_20260523

## Metadata

- Plan ID: `PLAN_task_flow_records_fixes_20260523`
- Status: `archived`
- Owner agent: `copilot`
- Created at (UTC): `2026-05-23T00:00:00Z`
- Last updated at (UTC): `2026-05-23T13:08:42Z`
- Related issue/ticket: —
- Intention plan: `PLAN_task_flow_records_20260523` (post-review fixes)

## Goal and intent

- **Goal:** Fix two minor bugs found in the review of `PLAN_task_flow_records_20260523`: a trailing-space in the step flow record description, and a non-deterministic sort order when two records share an identical `created_at` timestamp.
- **Business/user intent:** The activity timeline must produce a clean description string and a stable page order across repeated requests at the same offset.
- **Non-goals:** Any structural change. No new files, no new routes, no migration. Only the two lines called out below are touched.

## Scope

- **In scope:**
  - Fix trailing space in `serialize_step_flow_record` in `domain/tasks/serializers.py`
  - Fix non-deterministic sort in `get_task_flow_records` in `services/queries/tasks/task_flow_records.py`

- **Out of scope:** Everything else in both files.

- **Assumptions:**
  - Both `HistoryRecord` and `StepStateRecord` have `client_id` via `IdentityMixin`. The secondary sort key `x[2].client_id` is safe to use on both record types (x[2] is `row_a`, the first ORM object in the tuple).

## Clarifications required

*(none)*

## Acceptance criteria

1. A step flow record whose `working_section_name_snapshot` is `None` or `""` produces a description with no trailing whitespace.
2. A step flow record whose `working_section_name_snapshot` is populated produces an unchanged description (e.g. `"Alice marked in_progress on working section Upholstery"`).
3. When two records share the same `created_at`, their relative order is the same on every request at the same `offset`.

## Implementation plan

Two independent edits. Either order is fine.

---

### Fix 1 — Trailing space in step description

**File:** `backend/app/beyo_manager/domain/tasks/serializers.py`

Locate `serialize_step_flow_record`. Find this line:

```python
description = f"{username} marked {ssr.state.value} on working section {working_section_name}"
```

Replace it with:

```python
description = f"{username} marked {ssr.state.value} on working section {working_section_name}".rstrip()
```

**That is the only change in this file.**

---

### Fix 2 — Non-deterministic sort tiebreaker

**File:** `backend/app/beyo_manager/services/queries/tasks/task_flow_records.py`

Locate the sort call:

```python
raw.sort(key=lambda x: x[0], reverse=True)
```

Replace it with:

```python
raw.sort(key=lambda x: (x[0], x[2].client_id), reverse=True)
```

`x[2]` is `row_a` (the first ORM object in each tuple — `HistoryRecord` for history rows, `StepStateRecord` for step rows). Both have `.client_id` via `IdentityMixin`. The secondary key makes the sort stable and deterministic when two records share the same timestamp.

**That is the only change in this file.**

---

## Validation plan

- Step record with no `working_section_name_snapshot` set → description does not end with a space.
- Step record with `working_section_name_snapshot = "Upholstery"` → description is `"Alice marked in_progress on working section Upholstery"` (unchanged).
- Two records with the same `created_at`: same page order on repeated requests.

## Review log

*(none yet)*

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `copilot`
