# Implementer prompt — Reassigned steps endpoints

You are implementing a planned backend change in the ManagerBeyo backend (`backend/`).

Two new read-only endpoints give a worker a "Reassigned to me" page: a paginated list of every task
step reassigned into one of their current working sections that is not yet finished, and a cheap
count for the navigation badge. No new table, no new column, **no migration** — both endpoints read
existing tables and existing indexes.

**The frontend is already building against the published handoff.** That document is the contract;
your job is to match it field-for-field, not to design a response shape.

## Protocol

1. Load and follow the skill `backend/skills/cross_cutting/plan_lifecycle_orchestrator/SKILL.md`.
   Process as: implement → validate → review-log entry → **STOP for independent review**.
   Summary/archive only after the reviewer approves.
2. Read, in order:
   - Your plan:
     `docs/architecture/under_construction/implementation/PLAN_reassigned_steps_endpoints_20260731.md`
     — decisions D1–D7, the ten implementation steps, and the commit-hygiene section.
   - **The contract**:
     `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`
     — §3.1 params, §3.5 `q`, §3.6 response, §4 count, §5 field tables, §6 enums, §10 errors.
     Read it before writing the serialization, not after.
   - The intention, for the reasoning:
     `docs/architecture/under_construction/intention/making_endpoint_for_getting_reasign_tasks.md`
   - The contracts named in the plan's "Contracts and skills" section. `55_query_filters_local.md`
     is **mandatory** before you implement `q` — it has a completion gate you must walk.
3. **Clarification-first.** The plan records no open clarifications; D1–D7 are decided. If you find
   a case none of them cover, escalate in the Review log and **stop** rather than choosing.

## Hard constraints

- **The handoff outranks the plan.** Where they disagree on a request or response shape, the
  handoff wins (acceptance criterion #9). A needed deviation is an **operator decision**: write the
  proposal in the Review log and STOP. The frontend has already built against the documented shape.
- **Do not edit any `docs/handoff/to_frontend/` file.** Operator-owned. That includes the liveness
  table at the top — an implementer never flips a ⏳ to ✅.
- **Do not write a second handoff.** Step 9 is *conformance evidence in the Review log*, not a new
  document. The handoff already exists.
- **No migration.** If a file appears under `app/migrations/versions/`, something has gone wrong.
- **Do not touch `transition_reason` anywhere.** A separate feature set (`system_transition_reasons`
  phase 2) is live in this same tree and you will see that column throughout the diff. It is not
  your scope. The one place your work depends on it — `serialize_step_state_record_light` in
  `domain/tasks/serializers.py` — belongs to that phase; consume it, do not modify it.
- **Do not touch `docs/domains/`.** It is that other phase's active deliverable. Your change adds no
  domain documentation; do not create a folder for one speculatively.
- **Stage explicit paths, never `git add -A`.** The plan's commit-hygiene section lists your exact
  working set and the parallel feature set's. They are disjoint — keep them that way. Nine commits,
  in order, each independently revertible.

## The failure shape to avoid — read before Step 2

Step 2 moves ~290 lines out of `list_working_section_steps` into a shared builder. That endpoint is
the worker app's main section-list screen and it has **zero test coverage today**. This is the
highest-impact risk in the plan.

It is a **move, not a rewrite.** No logic edits, no statement reordering, no "while I'm here"
cleanups. Specifically, preserve all of these even where they look wrong:

- the `try/except Exception: case_summary_by_task = {}` swallow around the case-summary query — it
  is deliberate defensive behaviour, not a bug to fix in a refactor commit;
- the first-image-rich / rest-light treatment, including `first_image.pop("image_annotations", None)`;
- the `step_map.get(step_id)` / `continue` skip for a missing step;
- the dependency-section ordering (`order_list ASC NULLS LAST, client_id ASC`);
- key order in the assembled dict.

Step 1 writes the characterization test **first** and Step 2 must leave it byte-identical. If you
find yourself editing that test to make Step 2 pass, Step 2 is wrong.

**One caveat on writing that test:** assert **key sets**, not nested values, for
`last_state_record.pause_reason`. The parallel feature set is actively changing what that field
resolves to. Pinning its value produces a failure that looks like your extraction broke something
it did not.

## `q` — the contract conflicts with the neighbouring file, and the contract wins

`55_query_filters_local.md` mandates `apply_string_filter` and its completion gate declares a query
INCOMPLETE if "inline `.ilike` calls appear in the query body". `list_working_section_steps.py`
does exactly that — a hand-built `select(distinct(...))` subquery with `or_()` and `.ilike`.

Follow the contract (D6). What "same principles as `list_working_section_steps`" means here is
*which columns are searchable* — the primary item's `article_number` and `sku` — and that is
preserved exactly.

- **Do not "fix" `list_working_section_steps` to match the contract.** Separate change, and it
  would break your own Step 1 test.
- Join `TaskItem` (primary, `removed_at IS NULL`) and `Item` with **`isouter=True`**, into the base
  statement, always — not conditionally on `q`. An inner join silently drops every step whose task
  has no primary item, a filter nobody asked for that would apply even with no search term.
- No `DISTINCT` is needed: `uix_task_items_primary_active` guarantees at most one active primary
  item per task, so the joins add at most one row per step. Verify that index still exists rather
  than trusting this sentence.
- `q` is **not** a parameter on the count endpoint, and the count must not gain those joins (D7).

## Two invariants the tests exist to protect

- **The list and the count can never disagree.** They share one filter definition
  (`_reassigned_steps_filters.py`, Step 4). The "Agreement" test must page the list to exhaustion
  and compare — written as a real loop, not a hardcoded number. If you find yourself inlining a
  clause into either service, stop: that is the exact drift Step 4 exists to prevent.
- **Pagination must be stable.** Acks created by one manager action share `created_at` to the
  microsecond, so `created_at DESC` alone lets rows swap between pages. The `TaskStep.client_id DESC`
  tiebreak is load-bearing; assert no id appears on two pages.

## Definition of done

- All nine acceptance criteria met with evidence.
- Step 1's characterization test passes **unedited** after Step 2. Run the full
  `app/tests/integration/services/queries/working_sections/` module between commits 1 and 2 before
  going further.
- Every exclusion case in the plan's Step 8 tables asserted: membership removed, no membership,
  each of the four terminal states, soft-deleted ack / step / task / section, wrong worker, wrong
  workspace.
- `q` cases asserted: partial mixed-case match, `sku`-only match, no match, a step with `item: null`
  excluded under `q` but present without it, `q` + pagination.
- The list/count Agreement test and the no-id-on-two-pages test both present and passing.
- `55_query_filters_local.md`'s Completion gate walked, all seven boxes clear.
- Statement count on a 50-item page is constant, not ~50 × N — verify with query logging, do not
  assume. Do **not** copy the per-step loading loop from the neighbouring
  `list_pending_step_acknowledgments`; improving that file is out of scope.
- Handoff conformance: every key, nullability and enum value in §3.1/§3.5/§3.6/§4/§5/§6/§10 checked
  against a real response, evidence in the Review log.
- Full suite: no new failure nodes vs. baseline. **Capture the baseline before you start.** Compare
  **node sets**, not counts, and **run-2 vs run-2** — the test DB and Redis are shared and not
  reset, so several nodes fail on any second consecutive run including in an unmodified tree. Copy
  `app/.env*` into any baseline worktree; without `.env` the app cannot start. A second feature set
  is landing commits in this tree concurrently — a failure you did not cause is not yours to fix
  (T8: do not absorb baseline debt).
- `ruff check` clean on touched files.
- `git log --stat` shows no file outside the plan's declared working set, and the handoff unmodified.
- Review log entry with the conformance evidence and the Step 2 preservation checklist. Then STOP —
  no summary, no archive, no liveness flip, no handoff edit.
