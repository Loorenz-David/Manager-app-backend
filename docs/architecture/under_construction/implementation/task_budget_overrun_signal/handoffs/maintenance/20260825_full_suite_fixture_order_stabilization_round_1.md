---
plan: plan_2
role: maintenance
round: 1
state: COMPLETE
date: 2026-08-25
actor: Codex
---

# Full-suite fixture-order stabilization — maintenance round 1

The bounded maintenance repair is complete. The two affected test files now own their
prerequisites and assertions, all required order-variation checks pass, and the cycle's single
L4 stamp matches the durable 21-ID baseline exactly. This report makes no claim about Plan 2's
state; the coordinator decides whether this evidence unblocks its checkpoint.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner in this maintenance cycle.

## Gate and perimeter

The Task Budget Signal intention remained `RATIFIED`, Plan 1 remained `APPROVED`, Plan 2
remained `PROMPT_READY`, and the maintenance prompt records the owner's stabilization
authorization. This cycle did not edit the intention, master plan, Plan 2 plan/prompt/handoffs,
Task Budget Signal code/tests, application code, migrations, or Architecture Graph state.

Authorized maintenance write perimeter:

1. `app/tests/integration/models/users/test_user_work_profile_clock_in_code.py` — changed;
2. `app/tests/integration/services/queries/item_economics/test_narrowed_task_economics.py` — changed;
3. `app/tests/integration/services/queries/item_economics/_narrowing_fixture.py` — inspected and
   left byte-identical because no shared-fixture change was needed;
4. this maintenance handoff — added.

No mutation probe was declared by the prompt and none was applied. The probe-only file list is
therefore empty. No checkpoint was made, as required.

## Root cause and repair

### Clock-code index tests

`_two_workspaces` selected the first two ambient `Workspace` rows but seeded none. The file
therefore failed all three tests when it was the first file to reach a fresh worker database and
passed only when some earlier test happened to leave suitable rows.

The repair replaces that ambient query with a unique two-workspace seed owned by each test. Each
test tracks its own users, deletes its profiles/users/workspaces in `finally`, and the expected
duplicate insert runs inside a nested transaction so the constraint failure does not poison the
session before cleanup.

### C10 batch-economics test

The fixture was already self-contained and its cleanup was already scoped to its unique
workspace. The order-sensitive seam was the test's tuple equality: production loads tasks with
an unordered SQL query, so the three valid deduplicated specs can arrive in any order. The test
passed alone before editing, matching the captured full-suite-only symptom.

The repair asserts the exact three-spec set and then proves category-index preservation at the
observable result boundary: representative chair, table, and stool tasks must retain sample
counts 7, 9, and 11 respectively. This preserves the intended behavior without requiring or
pretending that SQL row order is contractual.

## Coverage map

| Obligation | Test ID | Assertion-shape assessment |
|---|---|---|
| Duplicate non-null code is rejected within one workspace | `tests/integration/models/users/test_user_work_profile_clock_in_code.py::test_duplicate_clock_in_code_in_one_workspace_is_rejected` | Exact: the test seeds its workspace/users and asserts the named unique-index violation from the real database. |
| The same non-null code is allowed in two workspaces | `tests/integration/models/users/test_user_work_profile_clock_in_code.py::test_same_clock_in_code_in_two_workspaces_is_allowed` | Exact: the test seeds both workspaces/users and asserts both owned workspace IDs were stored. |
| Null codes do not participate in the partial unique index | `tests/integration/models/users/test_user_work_profile_clock_in_code.py::test_index_is_partial_so_unassigned_codes_never_collide` | Exact: two owned users in one owned workspace flush with null codes and both rows are selected back. |
| C10 deduplicates category specs once and preserves the category-to-result index without relying on SQL order | `tests/integration/services/queries/item_economics/test_narrowed_task_economics.py::test_c10_batch_dedupes_specs_once_and_preserves_category_index` | Exact: one spy call, exact unordered three-spec set, 50 result rows, literal 7/9/11 category sample mappings, and broad fallback for the five uncategorized tasks. |

No new test ID was authored. Every changed assertion belongs to the existing obligation named by
its test.

## Evidence and tree identity

Pre-edit identity:

- base `HEAD`: `bd83950355fc5f70806ad2a5971317a7815c6485`;
- tracked binary-diff SHA-256: `f4ddda08ef4e7cc6bcfd55e816273202e36c3c90451044409d7f820a55a698bc`;
- clock-code test SHA-256: `7ccc9115b5b7c447b238aed8199b80cd0169c4a7775c13c92c821ff52df1facc`;
- narrowed-economics test SHA-256: `951e172d3bb0a9f9dc120952d024b3f48401ee1c815699ac7b788d74ce39e5b6`;
- shared narrowing fixture SHA-256: `707fd4ced98165aa88fd8514f09b093dfedb7eb722ebe850be76a265311faa66`.

L4 measurement identity, after all executable edits and before adding this report:

- base `HEAD`: `bd83950355fc5f70806ad2a5971317a7815c6485`;
- tracked binary-diff SHA-256: `782efd4df5372805dfa08e11752222712aebaf4fd510826f7d09b1b79b33a349`;
- porcelain-inventory SHA-256: `a2e04062e6bfff9d07eb5d54b2865e677b24ff4323bd3afdee0d9319cc83d86c`;
- clock-code test SHA-256: `88eddcc5bddb026968eba1fff19c5b9255f36b2e61837bdddbc51afdedc8c800`;
- narrowed-economics test SHA-256: `6aab3cfe55b620632a3f7a4adfba313f13d4a8f9f59c157b77d251818d96a8b1`;
- shared narrowing fixture SHA-256 remained
  `707fd4ced98165aa88fd8514f09b093dfedb7eb722ebe850be76a265311faa66`.

This report is the only post-stamp write. No executable, test, plan, prompt, or graph file changed
after the stamp; the three hashes above therefore identify the exact repaired test surface the
L4 run exercised.

| Scope | Exact command | Result |
|---|---|---|
| Pre-edit L1 | `PYTHONPATH=. pytest tests/integration/models/users/test_user_work_profile_clock_in_code.py -q` | **3 failed**: all three named tests found zero of two ambient workspaces. |
| Pre-edit L1 | `PYTHONPATH=. pytest tests/integration/services/queries/item_economics/test_narrowed_task_economics.py -q` | **16 passed**; C10's captured symptom was full-suite-only. |
| Post-edit L1 | `PYTHONPATH=. pytest tests/integration/models/users/test_user_work_profile_clock_in_code.py -q` | **3 passed**. |
| Post-edit L1 | `PYTHONPATH=. pytest tests/integration/services/queries/item_economics/test_narrowed_task_economics.py -q` | **16 passed**. |
| Serial order A→B | `PYTHONPATH=. pytest -n 0 tests/integration/models/users/test_user_work_profile_clock_in_code.py tests/integration/services/queries/item_economics/test_narrowed_task_economics.py -q` | **19 passed**. |
| Serial order B→A | `PYTHONPATH=. pytest -n 0 tests/integration/services/queries/item_economics/test_narrowed_task_economics.py tests/integration/models/users/test_user_work_profile_clock_in_code.py -q` | **19 passed**. |
| Static | `ruff check` on the clock-code file; `ruff check --ignore F401,E731` on the narrowed-economics file; `git diff --check` | Passed. The ignored rules are pre-existing debt in unrelated lines of the older file. |
| Redis preflight | Settings-resolved Redis client `PING` | `True`. |
| L4, sole cycle stamp | `PYTHONPATH=. pytest -m 'not e2e'` | **21 failed / 2786 passed / 1 skipped** in 52.68s. |

The L4 failing-ID set equals the durable 21-ID comparator: additions `∅`, removals `∅`.
Neither C10 nor any `test_user_work_profile_clock_in_code.py` ID appears in the set. No anomaly
recovery run was needed or taken.

## Remaining blocker and coordinator action

This maintenance cycle has no remaining fixture-order blocker. The coordinator can consume this
handoff, decide whether the exact baseline match unblocks Plan 2, and if so dispatch the separate
Plan 2 close/checkpoint step. This session deliberately does not make that decision or checkpoint.

## Owner-layer final response

**What I did:** Made the four unstable tests create and remove their own data, and changed the
batch test to verify category mapping without relying on database row order.

**What I found and what it means for you:** The earlier extra failures were test-order noise, not
a Task Budget Signal defect. The complete suite now returns exactly to the known 21-test baseline.

**What happens next:** The coordinator can use this evidence to resume Plan 2 closeout and decide
whether to create its checkpoint.

**What needs you:** Nothing needs you.
