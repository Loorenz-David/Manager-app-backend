# Plan 1 — inline valuation versioning on task creation

```
plan: 1
state: IMPLEMENTED (round 1b)
date: 2026-08-19
```

## Goal

Implement intention §3 (M1) completely: the compare-inherit-version branch in
`create_task`, the retirement of `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM`, and the nine
acceptance rows. No migration, no new module, no second valuation writer.

## Read first

1. `../planning/intention.md` — all of it; §3 is the mechanism, §2 the grounding.
2. `../planning/owner_decisions.md` — D-AUTH, **D17** (inherit), **D18** (currency counts).
3. `../master_plan.md` — §4 naming, §5 standing rules, §6 environment and baseline, §7 gates.
4. Code, read before writing:
   - `services/commands/tasks/create_task.py:317-370` — the trigger, the guard being
     replaced, and the `auto_commit` call that follows it
   - `services/commands/item_economics/_common.py:117-169` — the writer; note it stores
     `None` verbatim, which is what D17 exists to prevent
   - `services/commands/item_economics/set_item_valuation.py:71-80` — the wholesale
     replace this path deliberately does **not** copy
   - `services/commands/tasks/requests/__init__.py:39-61` — the request fields and the
     validator that makes `item.currency` mandatory alongside a price
   - `tests/unit/docs/test_item_economics_handoff_accuracy.py:97` and its
     `test_every_literal_identity_is_greppable_in_the_package`

## Tasks

- **T1 — the branch.** Replace `create_task.py:324-342`. When the trigger fires and the
  item was not created by this request: load the current valuation; if none, write as
  today; else build the effective triple per D17 (request value if not `None`, else the
  current value; currency from the request) and compare against the current row's triple
  including currency (D18). Identical → **write nothing at all** (no row, no supersede,
  no audit). Different → call the existing writer with the effective triple and
  `created_by_id = ctx.user_id`.
- **T2 — retire the identity.** Remove the raise and remove the entry at
  `test_item_economics_handoff_accuracy.py:97`.
- **T2b — the published document (added round 2, HC-1 corrected 3 → 4).** Rewrite §9.1 and
  validation step 4 of
  `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md`
  **exactly as intention §3.1 specifies** — a rewrite stating the new behaviour, not a
  deletion of the two lines. After T2 + T2b the identity must appear nowhere in `app/` and
  nowhere in `docs/handoff/`. It **remains** in `item_cost_calculation`'s planning and
  archive documents, which are provenance and must not be touched.
- **T3 — tests.** The nine rows below, in
  `test_phase8b_inline_task_prices.py`. The existing rejection test is replaced; say in
  the handoff which new row covers each behaviour it used to pin (deleted-assertion rule).

## Acceptance criteria

Exact literals. Fixtures own their teardown (rule 11½).

| # | Criterion |
|---|---|
| C1 | Existing item + current valuation + both prices sent, different → new version; old row `superseded_at` set and `superseded_by_id` = the new id; new row's `created_by_id` is the task creator |
| C2 | Identical values → **no-op**: valuation row count for the item is the same integer before and after, `client_id` unchanged, `superseded_at` still `NULL`. **Named mutation: delete the equality check → red** |
| C3 | Partial request: current 400/1200, send purchase 450 only → new row is 450 / **1200**. **Named mutation: pass the request value through unmerged → red** (stores `None`) |
| C4 | Partial request, effectively identical: current 400/1200, send purchase **400** only → no-op. Neither C2 nor C3 can fail in this shape — that is why it exists |
| C5 | Currency-only change → new version. **Named mutation: compare amounts only → red** |
| C6 | Existing item, no current valuation → first valuation written |
| C7 | Item created by this request + prices → unchanged behaviour |
| C8 | No inline price on an existing priced item → zero valuation rows touched |
| C9 | `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` is absent from `app/` and from `docs/handoff/`; the full docs-accuracy suite is green, `test_no_document_names_an_unregistered_error_identity[operational]` included. Its surviving occurrences in `item_cost_calculation`'s planning/archive are provenance and expected |
| C10 | The rewritten §9.1 states the new behaviour — re-prices, inherits an omitted field, no-ops on identical values — and no longer asserts the retired refusal anywhere in the document |

## Out of scope

`set_item_valuation`'s wholesale-replace semantics (intention §5). `auto_commit`. Every
document other than the operational handoff — in particular `item_cost_calculation`'s
planning and archive files, which record a decision that was true when written.

## Review log

(empty — plan authored 2026-08-19)

- **implement r1 (2026-08-19) — BLOCKED, correctly.** The implementer stopped rather than
  exceed the perimeter: retiring the identity turned
  `test_no_document_names_an_unregistered_error_identity[operational]` red, because the
  identity is published in the operational handoff at `:682` and `:725`. Root cause was the
  coordinator's: the verification grep behind HC-1 was run from `backend/app/`, so
  `backend/docs/` was never searched. No owner card was warranted — D-AUTH already covers
  the document edit. HC-1 corrected to FOUR files, T2b and C10 added, and the edit
  specified in intention §3.1 rather than left open. No code was written in r1.

- **implement r1b (2026-08-19) — IMPLEMENTED.** Replaced the priced-item refusal with
  the contracted compare/inherit/version decision in front of the existing shared writer;
  identical effective triples now write no valuation row, supersession, or valuation audit.
  Retired the identity from live application/test/document surfaces, rewrote operational
  handoff §9.1 and validation step 4, and added automated C1–C10 coverage. Focused suite:
  78 passed. Full suite: 2320 passed / 26 inherited failures / 1 deselected (2346 selected),
  with an empty failure-ID diff against the 26-test baseline. Ruff check passed on all
  changed Python files. Named C2/C3/C5 mutations each went red at the production decision
  site and reverted byte-identically to pre-probe SHA-256
  `63f5a81fafed0a248c75e7428c8b4086aa95ae16f0c1feca072766efc57c3447`.
  C10 also required mechanically replacing the validation overview's remaining generic
  `inline-pricing refusal` wording with `inline-pricing versioning`; this stayed in the
  authorized handoff file and added no semantics beyond intention §3.1. No semantic
  decisions or scope deviations were required. Architecture Graph additive delta was
  zero; a description-only maintenance preview for the existing human-confirmed
  `command-task-create` node was rejected by the approval channel, so no graph mutation was
  attempted again and the stale refusal wording is routed for separately authorized follow-up.

- **implement r1b (2026-08-19, Codex)** — IMPLEMENTED, checkpoint `6f82579`. Four HC-1
  files plus the two pipeline-state records; perimeter generated from `git`, nothing
  undeclared. Suite 2346 selected / 2320 passed / 26 failed / 1 deselected with the
  arithmetic stated (2 removed, 8 added). Coordinator consumption re-verified the identity
  retirement, re-applied C2's mutation **on the post-Ruff final file** (reddens C2 and C4),
  confirmed the revert against the declared SHA, and re-ran the suite. **Graph corrected by the coordinator 2026-08-19**, owner-authorized ("can we correct that
  stall claim"), before review: (a) `node:command-task-create`'s description **edited** — it
  claimed an inline amount on an already-valued item is *refused*; it now states the
  inherit/compare/version-or-no-op behaviour. (b)
  `edge:command-task-create--writes_to-->table-item-valuation` **re-anchored** 317-353 →
  316-367: the block grew when the branch replaced the guard, so the stored range stopped
  before the writer call at `:358` and the audit at `:367` that its own summary describes.
  Records `.archgraph/changes/2026-08-19T10-34-47-091Z--d52860.yml` and
  `…T10-35-34-680Z--adbe44.yml`; revision → `f823271e…`. Code read before the stored claim,
  per the graph policy's anti-pattern rule.

  **Residual, deliberately not actioned (for the reviewer to note, not to fix):** the
  `reads_from → table-item` evidence summary still says the command loads the item *"before
  applying the inline-price refusal predicate"*, and its `inferenceReason` says the read
  decides *"whether inline valuation is permitted"*. Both are stale wording. **Evidence
  summaries and inferenceReasons are immutable through review and maintenance alike**, so
  the only remedy is deleting and re-recording the edge — which would destroy a
  `human_confirmed` origin over a phrase, while the claim itself (`reads_from table-item`)
  remains true and correctly anchored. Recorded rather than repaired.
