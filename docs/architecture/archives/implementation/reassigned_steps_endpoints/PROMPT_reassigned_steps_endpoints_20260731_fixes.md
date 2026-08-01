# Fix brief — Reassigned steps endpoints, review round 1

You are resuming a partially delivered backend change after an independent review returned
`NEEDS_CHANGES`. Read, in order:

1. `PROMPT_reassigned_steps_endpoints_20260731.md` (same folder) — the full brief; still binding.
2. `PROMPT_reassigned_steps_endpoints_20260731_continuation.md` — the corrected baseline and the
   Step 2 gate. Both survived review; do not re-derive them.
3. The Review log in `PLAN_reassigned_steps_endpoints_20260731.md` — the findings, verbatim.

## What the review established — do not redo this work

- **The extraction (Step 2) is clean.** Byte-identical move, all five preservation hazards intact,
  characterization test untouched and proven to discriminate. Leave commits `a747939`, `1204916`
  alone.
- **`list_reassigned_steps.py` is written and reviewed-correct** — it is sitting untracked. The
  review probed it with 14 cases and measured a constant statement count (14 for a 1-item page, 14
  for a 10-item page). Commit it as-is unless a finding below forces an edit; do not rewrite it.
- Suite state: **26 failed / 1409 passed / 0 errors**, no new failure nodes. The one
  acknowledgment-adjacent failure (`ix_roles_name` fixture collision) is pre-existing — not yours.

## Finding 1 (blocking) — the delivery stops mid-Step 5. Finish Steps 5–9.

Commits 1–4 of 9 exist. Missing: the `list_reassigned_steps` commit, `count_reassigned_steps.py`,
both routes, the entire `tests/integration/services/queries/task_step_acknowledgments/` directory,
and the conformance evidence. The two invariants the plan is built around — list/count Agreement
and stable pagination — are currently untestable because the count and the tests do not exist.

Resume at Step 5 (commit the untracked service), then Steps 6–9 per the plan. The continuation
prompt's guidance on Steps 3–9 stands, including: the count takes **no parameters** and must not
gain the search joins; contract 55's completion gate has two router-layer boxes that can only close
in Step 7.

## Finding 2 (blocking) — the ack serializer landed in the wrong file. Relocate it.

`serialize_task_step_acknowledgment` went into `domain/tasks/serializers.py:181`. The plan (Step 3)
names `domain/task_steps/serializers.py` — which exists and was left untouched. Worse than a naming
miss: the parallel feature set's commit `867b8fb` added `serialize_step_pause_reason` at the
immediately adjacent line of the same file, so every future edit by either feature risks a merge
collision in a file only one of them is supposed to own.

Fix:

- Move the function (and its imports) to `domain/task_steps/serializers.py`.
- Update the import in `list_pending_step_acknowledgments.py` — and in `list_reassigned_steps.py`,
  which imports it too.
- `domain/tasks/serializers.py` must end this commit with **no trace of your feature** — the diff
  against `867b8fb`'s version of that file should be empty.
- **New commit on top; do not amend or rebase `241eee5`.** Two parallel-feature commits
  (`2f96915`, `b2c5a18`) now sit above it; rewriting history under another feature set's commits is
  a worse defect than the one you are fixing. Message:
  `fix(task-steps): relocate acknowledgment serializer to its domain`.

## Finding 3 (medium) — prefix mismatch in the handoff: already fixed, nothing to do.

The review found the handoff documenting `tstp_` / `task_` where the models say `tsp` / `tsk`. The
operator has corrected the handoff (six wrong prefixes, not two). It remains **operator-owned** —
do not edit it, and note your Step 9 conformance check now has the corrected values to check
against: `tsp` (step), `tsk` (task), `itm` (item), `itc` (item category), `iup` (item upholstery),
`iev` (image event), `tsa` (acknowledgment), `wsec` (working section), `par` (pause reason).

## Measurement notes carried from review

- The reviewer hit `-p no:logging` manufacturing ~19 phantom errors (it kills `caplog`). Run the
  suite with default plugins, from `backend/app/`. Any non-zero *error* count means the
  measurement is broken, not the code.
- Baseline stands at 26 failed / 0 errors (main tree, base commit). Anything materially different
  is your environment.

## Definition of done

As the main prompt, plus:

- All nine findings-era commits present: the original 4, the relocation fix, and Steps 5–9's
  remaining commits in plan order.
- `grep -rn "serialize_task_step_acknowledgment" app/beyo_manager/domain/tasks/` returns nothing.
- The Agreement test, the stable-pagination test, and the full Step 8 exclusion tables exist and
  pass.
- Review log entry recording: findings 1 and 2 closed with commit hashes, finding 3 acknowledged
  as operator-resolved, suite node-set comparison against the recorded baseline. Then **STOP** for
  re-review — no summary, no archive, no liveness flip, no handoff edit.
