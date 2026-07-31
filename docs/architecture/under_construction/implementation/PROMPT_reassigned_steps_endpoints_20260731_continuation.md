# Implementer prompt — Reassigned steps endpoints, continuation (Steps 2–9)

You are continuing a partially implemented backend change in the ManagerBeyo backend (`backend/`).
A previous session completed Step 1 and stopped. **Steps 2 through 9 remain.**

**Read `PROMPT_reassigned_steps_endpoints_20260731.md` (same folder) first.** It is the full brief —
protocol, hard constraints, the `q` contract conflict, the invariants, and the definition of done.
Everything in it still applies. This document records only what changed since it was written.

## State on handover

**Step 1 is complete and verified.**
`app/tests/integration/services/queries/working_sections/test_list_working_section_steps_payload_characterization.py`
exists and passes (6 passed, including the 4 pre-existing tests in that module). It locks:

- the `steps_pagination` envelope key set;
- the full 38-key item key set;
- nested `last_state_record` / `task` / `item` key sets;
- **the `upholstery_group_*` values** — the grouped run asserts them equal to the seeded
  upholstery's `name` / `image_url` / `client_id`, the ungrouped run asserts all three `None`;
- `pause_reason` by **key set only** — deliberately, so the concurrent `system_transition_reasons`
  work cannot flip it.

**This test is the contract for Step 2. It must pass byte-identical afterwards.** If you find
yourself editing it to make the extraction pass, the extraction is wrong — not the test.

## ⚠️ The baseline in the previous session's report is WRONG — do not use it

The previous session recorded **334 failed / 995 passed / 38 errors**. That figure is invalid.

The real figure for this tree, measured directly:

```
26 failed, 1398 passed, 2 warnings in 44.87s
```

**Cause:** the baseline worktrees under `~/.vscode/tmp/tmp_vscode_20/` have `app/.env*` copied in
correctly but **no `app/.venv`**. Pytest ran against a different interpreter, producing 38
collection errors and ~300 spurious failures. The "second run matched the first" check did not
catch it — a broken environment reproduces itself perfectly.

**What you must do:**

- Discard 334/995/38 entirely. Do not compare anything against it.
- If you take a fresh baseline, the worktree needs **both** `app/.env*` **and** a working `.venv` —
  or skip the worktree and check the base commit out in the main tree.
- Smoke-test any baseline environment before trusting a full-suite number from it: run one small
  module and confirm it collects and passes.
- Run tests from `backend/app/` (that is where `pytest.ini` lives); `python -m pytest tests -q`
  from the repo root fails to import `beyo_manager`.

Sanity anchor: anything in the 20s-of-failures range is plausible for this tree. Anything in the
hundreds means your environment is broken, not the code.

## Step 2 — the bounded refactor. Do this alone, then verify, then continue.

This is the highest-risk commit in the plan: ~290 lines moved out of `list_working_section_steps`
into `services/queries/working_sections/steps_list_payload.py`. That endpoint is the worker app's
main section-list screen.

**It is a move, not a rewrite.** Re-read the "failure shape to avoid" section of the main prompt
before you start. Preserve, even where it looks wrong:

- the `try/except Exception: case_summary_by_task = {}` swallow around the case-summary query;
- the first-image-rich / rest-light image treatment, including
  `first_image.pop("image_annotations", None)`;
- the `step_map.get(step_id)` / `continue` skip for a missing step;
- the dependency-section ordering (`order_list ASC NULLS LAST, client_id ASC`);
- key order in the assembled dict;
- the `if not page_ids` early exit.

**Hard gate before writing any new endpoint code:** commit Step 2, then run

```
cd backend/app && python -m pytest tests/integration/services/queries/working_sections/ -q
```

Expect `6 passed`. If it is anything else, fix Step 2 before proceeding — do not carry a failing
characterization forward into Steps 3–9.

## Steps 3–9

Proceed per the plan once the gate above is green. Nothing about them has changed. The three that
most often go wrong:

- **Step 4** — the shared filter module is what makes the list and the count unable to disagree.
  Do not inline a clause into either service.
- **Step 5** — `q`: contract shape (`apply_string_filter`), `isouter=True` on both joins, joins
  added unconditionally, no `DISTINCT`. See the main prompt's `q` section for why.
- **Step 6** — the count takes no parameters at all and must not gain the search joins.

## Definition of done

As in the main prompt, with two amendments:

- The full-suite comparison is against a **valid** baseline (see above), not 334/995/38. Record the
  figure you actually used and how you obtained it.
- The Review log entry must state explicitly that the Step 1 characterization test passed unedited
  after Step 2, and note the corrected baseline so the next reader does not inherit the bad number.

Then STOP — no summary, no archive, no liveness flip, no handoff edit.
