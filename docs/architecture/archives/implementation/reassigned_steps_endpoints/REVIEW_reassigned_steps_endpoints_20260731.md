# Review prompt — Reassigned steps endpoints

You are performing an independent, adversarial code review. Work from the repo files; assume no
prior conversation. Do not fix anything — report.

Two new read-only endpoints, no migration. The risk is not in the new code — it is in the **290-line
extraction out of `list_working_section_steps`**, which is the worker app's main section-list screen
and had zero test coverage before this change. So the central question is narrow and testable:
**did the extraction change any observable behaviour of an endpoint nobody was testing, and do the
two new endpoints match a contract the frontend has already built against?**

## Inputs

- Plan under review:
  `docs/architecture/under_construction/implementation/PLAN_reassigned_steps_endpoints_20260731.md`
  — decisions D1–D7 and the Review log.
- Implementer prompts: `.../PROMPT_reassigned_steps_endpoints_20260731.md` and
  `.../PROMPT_reassigned_steps_endpoints_20260731_continuation.md`
- **Published contract** (authoritative over the plan):
  `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_reassigned_steps_endpoints_20260731.md`
- Contracts: `architecture/07_queries.md` + `_local`, `09_routers.md`, `46_serialization.md` +
  `_local`, **`55_query_filters_local.md`** (has a completion gate), `24_multi_tenancy.md`,
  `25_soft_delete.md`, `22_performance.md`

## Checklist — the extraction (highest risk)

- [ ] **Diff Step 2 as a move, not as a rewrite.** Every line that left
      `list_working_section_steps.py` should appear in `steps_list_payload.py` unchanged. Any edited
      logic is a finding unless the Review log justifies it.
- [ ] These five are preserved verbatim. Each looks like something worth "improving"; each is a
      finding if it changed:
      - the `try/except Exception: case_summary_by_task = {}` swallow around the case-summary query;
      - the first-image-rich / rest-light treatment, including `first_image.pop("image_annotations", None)`;
      - the `step_map.get(step_id)` / `continue` skip for a missing step;
      - dependency-section ordering (`order_list ASC NULLS LAST, client_id ASC`);
      - key order in the assembled dict.
- [ ] **The characterization test is byte-identical to its pre-Step-2 state.** `git log -p` on that
      file. An edit to make the extraction pass inverts the point of the test and is a blocking
      finding.
- [ ] **The characterization test actually discriminates.** Verify, do not assume: break the
      extraction deliberately — drop one of the three `upholstery_group_*` maps on the builder call
      — and confirm the test fails. If it still passes, the test is decorative.
- [ ] `list_working_section_steps` still returns its own early-empty envelope
      (`{"steps_pagination": {"items": [], ...}}`), not the builder's bare `[]`.
- [ ] Unused imports removed from `list_working_section_steps.py`; nothing else in that file changed.

## Checklist — visibility and scoping

A step must appear **only** when all of: a live ack for (workspace, step, caller); an **active**
membership for the step's section; a non-terminal step state; live step, task and section.

- [ ] All four join conditions carry `workspace_id` explicitly. Three different soft-delete idioms
      are in play (`is_deleted`, `removed_at`, `deleted_at`) — confirm each table uses its own.
- [ ] Membership is re-checked **at read time**, not inherited from the ack row. Probe: create the
      ack, then remove the membership, and confirm the step disappears. The ack fan-out in
      `add_task_steps` writes one row per *section member*, so this join is load-bearing, not
      redundant — a reviewer who assumes otherwise will pass a leak.
- [ ] All four terminal states excluded (`COMPLETED`, `SKIPPED`, `FAILED`, `CANCELLED`) — test each,
      not just one. `ENDED_SHIFT` is **not** terminal and must still appear.
- [ ] Another worker's acks and another workspace's acks are both invisible. Grep for any clause
      that scopes by only one of the two.
- [ ] The filter set lives in **one** module used by both services. A clause inlined into either
      service is a finding even if the behaviour currently matches.

## Checklist — `q` (contract 55 has a completion gate)

- [ ] Walk `55_query_filters_local.md`'s "Completion gate" — all seven boxes. `apply_string_filter`
      used, no inline `.ilike`, no credential columns, router `max_length=200`, `string_filters` not
      parsed inline, both keys present in `query_params`, joins present before the call.
- [ ] **`isouter=True` on both `TaskItem` and `Item` joins.** An inner join silently drops every step
      whose task has no primary item — including when `q` is absent. Probe it: seed a task with no
      primary item and confirm the step is returned with no `q`, and dropped with one.
- [ ] Joins are added **unconditionally**, not only when `q` is set, so the statement shape is stable.
- [ ] No `DISTINCT` — and confirm the reason still holds by checking
      `uix_task_items_primary_active` exists on `TaskItem`. If that index is gone, absence of
      `DISTINCT` becomes a fan-out bug.
- [ ] `list_working_section_steps` was **not** "fixed" to use `apply_string_filter`. That is a
      separate change and would break the characterization test (D6).
- [ ] The **count endpoint takes no `q`** and did not gain the search joins (D7).

## Checklist — the two invariants

- [ ] **List and count cannot disagree.** The Agreement test pages the list to exhaustion and
      compares against the count — written as a real loop, not a hardcoded number. Verify it would
      fail if a clause were inlined into one service: temporarily add one and re-run.
- [ ] **Pagination is stable.** Acks from one manager action share `created_at` to the microsecond;
      the `TaskStep.client_id DESC` tiebreak is what makes the order total. Probe: seed three acks
      with an identical `created_at`, page with `limit=1`, assert no id appears twice and none is
      skipped.

## Checklist — contract conformance

The frontend has already built against the handoff. **The handoff outranks the plan.**

- [ ] Item key set equals `list_working_section_steps`'s exactly, **plus** `acknowledgment` — no
      more, no less. Compare against the characterization test's key set.
- [ ] `working_sections` is an object keyed by `client_id` (not an array), covering exactly the
      sections referenced by the page's items — no more.
- [ ] `is_reassigned` is `true` on every item; the four `upholstery_group_*` keys are present and
      `null` (handoff §5.1 / D4).
- [ ] Count returns `{"reassigned_steps_count": {"total": int, "unacknowledged": int}}`, both `0`
      rather than `null` when empty, from **one** SQL statement with no ORM entities loaded.
- [ ] Empty page returns `working_sections: {}` and the full envelope, not a bare object.
- [ ] Error behaviour matches handoff §10: no `404` on either endpoint; `422` for `limit > 200`,
      `offset < 0`, and `q` over 200 characters.
- [ ] **The handoff file is unmodified and no liveness row was flipped.** A needed contract change
      appears as a *proposal* in the Review log, nothing else.

## Checklist — performance

- [ ] Statement count on a 50-item page is **constant, not ~50 × N**. Measure with a SQLAlchemy
      event listener — the shared `count_queries` fixture is known broken. Do not accept "batch
      loaded" as an assertion.
- [ ] The per-step loading loop from the neighbouring `list_pending_step_acknowledgments`
      (`load_step_with_latest_record` + `build_step_record_payload` per row) was **not** copied — and
      that file was **not** "improved" either. Both are findings.

## Checklist — scope and commit hygiene

A second feature set (`system_transition_reasons`) lands commits in this tree concurrently.

- [ ] **No file outside the plan's declared working set was touched.** Read the full diff, not the
      Review log. Specifically: no `transition_reason` anywhere, no `docs/domains/` edit, no
      `domain/tasks/serializers.py` or `domain/users/serializers.py` change.
- [ ] **No migration.** A file under `app/migrations/versions/` is a blocking finding.
- [ ] Nine commits, in plan order, each independently revertible. Commits 1 and 2 separable — the
      refactor must be revertible without losing the test.
- [ ] `ruff check` clean on touched files. 149 pre-existing errors in untouched files are not this
      change's to fix (T8).

## Suite comparison

- [ ] Failure **node sets**, not counts. Run from `backend/app/`.
- [ ] **Reject any baseline showing hundreds of failures or a non-zero *error* count.** A worktree
      lacks both `app/.env*` and `app/.venv`; the previous session reported 334/995/38 for a tree
      that actually measures **26 failed / 1398 passed / 0 errors**. Reproducing a bad number twice
      does not validate it. Simplest check: measure at the base commit in the main tree.
- [ ] A failure node that passes in isolation and sits outside the diff is a measurement artefact —
      verify it, do not make the implementer absorb it (T8).

## Adversarial probes

- Delete one of the three `upholstery_group_*` arguments at the builder call site; the
  characterization test must fail.
- Same fixture through `list_working_section_steps` before and after the extraction — responses
  byte-identical.
- Ack exists, membership removed afterwards → step invisible.
- Step transitioned to each terminal state in turn → leaves the list without any acknowledgment action.
- Three acks sharing an identical `created_at`, paged with `limit=1`.
- Task with no primary item, with and without `q`.
- `q` matching an upholstery name/code → must **not** match (upholstery search is out of scope).
- `q` matching a step that fails the membership or terminal check → must stay invisible; `q` narrows,
  never widens.
- An admin token calling both endpoints → sees their **own** obligations, not a workspace-wide view.

## Verdict

End with exactly one of `APPROVED` or `NEEDS_CHANGES` (findings with file:line, violated criterion,
severity). Record findings in the plan's Review log; that should be the only file you modify.






Round 2 — the round-1 findings and their closure evidence are in the plan's Review log. Verify findings 1 and 2 are closed (commits dccdb7a..213cac7, 1ad796c), and take the suite figures from the operator entry dated 2026-07-31 rather than re-measuring in a worktree.