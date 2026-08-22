# Plan 1 — inline valuation versioning on task creation

```
plan: 1
state: IMPLEMENTED (fix round 2)
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
| C9 | `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` is absent from every `*.py` and `*.md` file under `app/` (excluding `app/.venv/`) and under `docs/handoff/` — the extension and `.venv` narrowings are stated here deliberately, per review r1's rule that a narrowing lives in the criterion and not silently in the test; the full docs-accuracy suite is green, `test_no_document_names_an_unregistered_error_identity[operational]` included. Its surviving occurrences in `item_cost_calculation`'s planning/archive are provenance and expected |
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

  **(c) The `reads_from → table-item` evidence summary was corrected too** — owner, same
  session: *"i don't want to leave things half done."* Its summary said the item is loaded
  *"before applying the inline-price refusal predicate"* and its `inferenceReason` said the
  read decides *"whether inline valuation is permitted"*; neither describes anything that
  still exists. **Evidence summaries and inferenceReasons are immutable through review and
  maintenance alike**, so the only remedy is delete-and-re-record, which costs the
  `human_confirmed` origin. Done as a complete three-step sequence rather than accepting the
  loss: `dryRun` confirmed the identity triple (reported `exact-duplicate`) → delete →
  re-record with an accurate summary naming the `was_created` flag the inline branch keys on
  → **promote back to `human_confirmed`**. Promotion is honest here rather than
  rubber-stamping: the coordinator read `create_task.py:236-248` and stated what it does
  **before** opening the stored claim, which is the graph policy's own definition of
  independent re-derivation.

  Records: `.archgraph/changes/2026-08-19T10-46-32-317Z--0ed5e7.yml` (delete) and
  `.archgraph/reviews/2026-08-19T10-46-53-673Z--bda7ab.yml` (promote). Final revision
  `0f36b07a…`. **Post-state verified: 183 nodes / 275 edges — unchanged counts — pending
  reviews still 4, 0 diagnostics, 0 stale.** The graph carries no stale claim from this
  phase.

- **review r1 (2026-08-19, Opus 5)** — **CHANGES_REQUIRED**: 1 should-fix, 5 notes, 0
  blocking. M1 verified faithful, including three traps the reviewer checked and cleared:
  the falsy-zero case (inheritance keys on `is not None`, so a request price of `0` is kept,
  not treated as omitted); a `NULL` field on the current row inheriting correctly; and no
  enum-vs-string coercion across the persistence boundary, which would have made every
  triple compare "different". **S1** — C9's standing guard does not cover the perimeter C9
  states; demonstrated by planting the identity in `app/scripts/` and
  `docs/handoff/from_frontend/` and watching the docs-accuracy suite stay green at 51
  passed. The identity is genuinely absent today — what fails is the tripwire, not the
  state. **Card 1 answered** (owner: *"yes we should maintin it correctly, we don't want to
  leave it half way"*): `node:command-task-create`'s whole-function anchor widened
  **72-580 → 72-594**, the true span verified by AST rather than by reading; lines 581-594
  assemble the response and sat outside the map. Pre-existing drift from 2026-08-15,
  invisible to staleness detection because that keys on where a claim *starts*. Record
  `.archgraph/changes/2026-08-19T11-10-47-193Z--a635cc.yml`, revision `50b39402…`.

  **N1 rename mapping, recorded so archived evidence stays followable:**
  `test_c1_inline_birth_writes_valuation_and_handles_exact_auto_statuses` →
  `test_c7_inline_birth_writes_valuation_and_handles_exact_auto_statuses`, and its parameter
  ids **`C1-row-*` → `C7-row-*`**. Cited under the old names in
  `item_cost_calculation/archive/plan_8b/2026-08-15_phase8b_implement_r1_handoff.md:49` and
  `…/2026-08-15_phase8b_review_r1_handoff.md:187`. Deliberately **not** reverted — that
  would break this plan's citations instead, and archives are not rewritten.

- **fix r2 (2026-08-19, Codex) — IMPLEMENTED.** Resolved review-r1 S1 by widening
  `test_retired_inline_refusal_identity_is_absent_from_live_sources` from the package,
  tests and `docs/handoff/to_frontend/` subsets to all Python/Markdown files under `app/`
  and `docs/handoff/`. The only explicit exclusion is `app/.venv/`, which is the installed
  dependency environment rather than a live source root; `app/scripts/`, `app/migrations/`,
  top-level app modules, and every handoff subfolder remain covered. The final-form P6
  probe went red first on `app/scripts/_reviewer_probe_c9.py` and then, after that plant was
  removed, on `docs/handoff/from_frontend/_reviewer_probe_c9.md`; both probes were removed
  and the docs-accuracy suite returned to 51 passed. Full suite: 2346 selected / 2320 passed
  / 26 inherited failures / 1 deselected, with failure-ID diff added `[]`, removed `[]`;
  changed-file Ruff lint passed. **N1 decision record:** r1b renamed
  `test_c1_inline_birth_writes_valuation_and_handles_exact_auto_statuses` →
  `test_c7_inline_birth_writes_valuation_and_handles_exact_auto_statuses` and parameter ids
  `C1-row-*` → `C7-row-*`; the mapping is retained rather than rewriting the two archived
  phase-8b citations.

- **fix r2 (2026-08-19, Codex) — S1 closed, verified independently.** Checkpoint
  `e9531dc`, two files, perimeter exact. The guard now scans all `*.py`/`*.md` under
  `app/` and `docs/handoff/`, excluding only `app/.venv/`. **Coordinator re-planted both
  probes separately on the final tree** — `app/scripts/_coord_probe.py` and
  `docs/handoff/from_frontend/_coord_probe.md` each turn the guard red **on their own**,
  which is stronger than a combined plant because it proves each root independently. Both
  removed; tree clean. Suite re-run 2320/26/1, IDs byte-identical.

  **F1 (coordinator-found, for re-review to adjudicate — note-level).** The guard filters
  to `*.py` and `*.md`. C9 says the identity is absent from **`app/`** and
  **`docs/handoff/`**, with no extension qualifier. Probed: `app/_coord_probe.yml`
  containing the literal leaves the guard **green** (`1 passed`). This is S1's exact shape
  one layer out — the criterion names trees, the guard narrows them — but with three
  differences that argue for note, not should-fix: the extension filter is **pre-existing**
  module behaviour rather than something this round introduced; the realistic carriers of a
  Python error constant are `.py` and `.md`, both covered; and widening to all file types
  would sweep lockfiles and binaries. **Per review r1's own rule — "if any root is
  deliberately left out, say so in the criterion, not silently in the test" — the narrowing
  belongs in C9's text.** C9 is therefore restated below rather than left implicit.

- **re-review r3 (2026-08-19, Opus 5) — APPROVED.** **S1 closed**, and verified by
  *extending* rather than repeating the plant set: P7 `app/migrations/_rev_probe.py` and P8
  `docs/handoff/presentation_system/_rev_probe.md`, each planted **alone**, turn the guard
  red and name the path — the two roots the fix handoff claimed but never demonstrated. P9
  confirms `app/.venv/` is the only exclusion and correctly stays green. Across three rounds
  all four newly-covered roots are proven independently.
  **F1 ruled note, not should-fix**, on a fact the coordinator's argument missed: the guard's
  own root contains `docs/handoff/to_frontend/archived/beyo_partner_api (1).docx`, whose
  `read_text()` raises `UnicodeDecodeError` — so removing the extension filter would pin C9
  red forever for a reason unrelated to the identity. Recorded refinement: widen the
  allowlist, never remove the filter.
  All three implementer DECISIONS ruled correct, including declining `ruff format`:
  reformatting an HC-1 file mid-fix would have destroyed the perimeter diff the round runs on.
- **N2 closed at closeout (coordinator, 2026-08-19).** The reviewer left it as the
  coordinator's call — accept as permanent debt, or add a banner. Added: the test file now
  opens with a docstring naming which C-range belongs to which plan and pointing at the
  `C1-row-* → C7-row-*` mapping here. Comment only; the file's 27 tests and the full suite
  (2320/26/1) were re-verified unchanged **before** the approval-gate commit, so the approved
  tree is the verified tree.
