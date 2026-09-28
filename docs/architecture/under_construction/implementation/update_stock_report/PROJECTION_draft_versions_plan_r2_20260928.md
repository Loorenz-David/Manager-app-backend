---
plan: docs/architecture/under_construction/implementation/update_stock_report/draft_versions_plan.md (revision 5)
role: projection
round: 0
projection_pass: r2 (third projection; r0 and r1 were 2026-09-27)
verdict: AMENDMENTS_REQUIRED
date: 2026-09-28
actor: Claude Opus 5.5 (projection session, fresh context)
---

# Projection r2 — `draft_versions_plan.md` revision 5

**For the owner.** The plan is close. Most of it matches the code, and the hard parts hold up:
the lock orders, the live membership, the rule for which of several due drafts wins. But I found
**five things that would break during implementation**. Two of them are internal contradictions.
Activation writes two columns in an order that the plan's own new database check forbids, so
every activation would fail. And a skipped scheduled activation is meant to clear the draft's
schedule, but the plan implements the skip as an error, and an error rolls the clear back. The
other three: the documentation test cannot point at the v8 file as planned, the Scanner webhook
would exceed a statement budget that a test enforces, and one schedule-time comparison can fail
silently. Each has a fix of a paragraph or less, listed below. **Three small decisions need you**
(cards below). Nothing else waits on you. When the cards are answered and the amendments are
folded in, the plan can be implemented as the single unit you chose.

## ⚠ OWNER DECISIONS REQUIRED (3)

**Card 1 — Two drafts scheduled for exactly the same moment: which one becomes the board?**
- **Story:** On Friday one manager schedules "Monday upholstery push" for Monday 06:00, and a
  colleague schedules "Monday frames" for 06:00 as well. Both fire at 06:00. The plan's rule is
  "the later plan wins", but neither is later, so both run. Whichever the worker happens to
  process second becomes the board, and the other is closed a second after it went live. Next
  Monday they could come out the other way round.
- **Branches:** (a) the draft **created later** wins, and the other is skipped and stays a draft
  with its schedule cleared. This is deterministic. · (b) refuse a second schedule at an identical
  moment (422). No tie can exist, but users must pick another minute. · (c) leave it to
  processing order, so the board is unpredictable.
- **Recommendation:** (a). It extends the rule you already chose ("later plan wins") to the one
  case it did not decide, and the frontend gets no new refusal.
- **On silence:** the gate holds for the scheduling step only (plan §12 step 4).
- **Trace:** plan §4.2 step 2, §5.3 · v8 §5.21 · ledger Q-6.

**Card 2 — A user types the number Scanner already shows. Is that a pin or a no-op?**
- **Story:** On a draft, Scanner asks for 10 dining chairs. A manager wants to plan for exactly
  10 even if Scanner later asks for 14, so they type 10. The plan stores it as a manual value:
  the row shows "manual" and stays at 10 when Scanner moves. The contract already with the
  frontend says "already the value in force → no-op": nothing is stored, and when Scanner sends
  14 the draft follows to 14.
- **Branches:** (a) **pin**: compare against the stored manual value, so a typed 10 is stored
  and shows "manual". The frontend gets a one-line correction in the ship-time delta. · (b)
  **no-op**: compare against the value in force. The contract stands, but nobody can pin the
  current value.
- **Recommendation:** (a). A manual value exists to stop a draft following Scanner, and "manual"
  on the row tells the user it worked.
- **On silence:** the gate holds for the requested-quantity route's no-op rule only.
- **Trace:** plan §4.11 step 3 · v8 §5.22 · ledger Q-7.

**Card 3 — May each Scanner push run up to 11 database statements instead of the ratified 8?**
- **Story:** Every Scanner push today runs exactly 8 statements, whatever the batch size. That
  number was fixed when the stock report was ratified, and a test holds it. Letting new rows join
  every draft adds up to 3 more: find the drafts, add the rows, update their counts. The count
  still does not grow with the batch or with the number of drafts. Without a decision, that test
  fails the first time a Scanner push creates a row.
- **Branches:** (a) raise the bound to **11**, kept constant in batch size and draft count, with
  a new drafts-present case in the test. · (b) fold the three into one intricate SQL statement,
  giving a bound of 9. 8 cannot hold either way.
- **Recommendation:** (a). The ratified promise was "does not grow with the batch", and that is
  kept. Plain statements are easier to review.
- **On silence:** the gate holds for the webhook's draft insert (plan §12 step 2).
- **Trace:** plan §4.9 · stock_report intention §8B D6 · `test_apply_stock_demand.py`
  `test_c6a`/`test_c6b` · ledger Q-4.

### Owner rulings — 2026-09-28

The owner accepted all three recommendations the same day, in their words: "for the three owner
cards the recommendation is actually the correct choice".

| Card | Ruling | Fold into |
|---|---|---|
| 1 | **(a)** On an equal `scheduled_activation_at`, the draft **created later** wins. The tie is broken on `(scheduled_activation_at, created_at, client_id)`, in either processing order. The loser is skipped and stays a draft with its schedule cleared (Q-2's return path). | plan §4.2 step 2 rule 3, §5.3, a §9 row. The ship-time consolidated file (Q-3) states it. |
| 2 | **(a) Pin.** The no-op compares against the **stored manual value** (`quantity_requested_manual`), not the effective one. Typing the value already shown stores it and sets source `manual`. Only `null` on a snapshot with no override is a no-op among reverts. | plan §4.11 step 3, a §9 row. The ship-time consolidated file (Q-3) corrects v8 §5.22's sentence. v8 is never edited. |
| 3 | **(a)** Raise the demand-webhook statement bound from 8 to **11**. It stays constant in batch size and in draft count. Keep three plain statements before the deadline check. | plan §4.9. C6a/C6b become `<= 11`, with cases for 0 and ≥ 2 drafts present. |

With these rulings, **every ledger row is routable without the owner**: Q-4, Q-6 and Q-7 are
decided, and the rest are plan amendments or explicit delegations. The plan's author session
folds Q-1..Q-18 before implementing.

---

## Inputs and scope

Read only what the implementer gets: the plan (994 lines), v7 and v8 handoffs, and the code at
`438c4f7` + working tree (no code changes since; `git status` shows docs only). The plan is
owner-shaped, not a pipeline intention (plan header). **The trace chain and the intention gate
therefore do not apply.** There is no measurement ledger to trace rows to, and I record that
rather than flag it. The prior projection handoffs (r0, r1) are no longer in this folder. I
projected revision 5 on its own terms and did not re-open any folded P-/R-/O- item or the
single-unit ruling (R-13).

The skeleton I derived (per-command statement sequences, lock graphs, the guard's view of each
serializer) is discarded, as doctrine requires. Only the findings it produced are below.

## Decision ledger

Severity: **B** = blocks implementation (fails at runtime or is a contradiction the implementer
must resolve by guessing) · **H** = a silent-failure or undecidable row · **L** = wording or
local clarity.

| ID | Sev | Decision point | Class | Proposed routing |
|---|---|---|---|---|
| Q-1 | B | Activation freezes the Scanner column (step 5) **before** stamping `active_at` (step 7), and says this order is *required* by `ck_…_scanner_iff_activated`. It is the reverse. The check is `(scanner IS NULL) = (active_at IS NULL)`: after step 5 alone, a draft snapshot has scanner set and active_at NULL, so false = true and the check is violated. Stamping first violates it the other way. **Every activation of a non-empty draft fails.** | plan gap | Amend §4.2 steps 5–7 and the sentence in step 7: **one** `UPDATE stock_report_item_snapshots s SET quantity_requested_scanner = r.quantity_requested, active_at = :now, <three counters from r> FROM stock_report_items r WHERE s.version_id = :v AND r.client_id = s.stock_report_item_id`. The version UPDATE (active_at + clear schedule) stays its own statement. §7 (ii)/(iii) already say "same statement" and are correct. |
| Q-2 | B | "Superseded" is a raised `ValidationError` (`STOCK_REPORT_SCHEDULE_SUPERSEDED`) that the handler catches, **and** the draft's schedule is "cleared and its scheduler row `CANCELED` in the same transaction". `maybe_begin` rolls back on exception (`services/commands/utils/transaction.py:11`), so the clear and the cancel never land. The draft keeps a past schedule with no `ACTIVE` row, `schedule_scheduler_mismatch` (b) reports it, repair recreates the row, and it fires and is skipped again. v8 §5.21 also promises a `stock_report_snapshot_version:updated` for the skipped draft, which §4.2 step 9 does not list. | plan gap | Amend §4.2 step 2 / §5.1: when `expected_scheduled_activation_at` is present and a supersede rule holds, the command **returns** a skip result (e.g. `{"skipped": "<reason>"}`) instead of raising. For rules 2–3 it commits the clear + `CANCELED` and emits `:updated` (`extra`: `title`, `scheduled_activation_at: null`). For rule 1 (moved/cleared) it touches nothing and emits nothing. The handler logs the reason at info, using the token `STOCK_REPORT_SCHEDULE_SUPERSEDED:` so the identity stays scannable (v7 §8 lists it as "never in an HTTP response"; the docs guard's `_message_identities` regex needs it in api.md too). "Not a draft" and 404 remain raised refusals that change nothing. Add a criterion: a superseded fire leaves `scheduled_activation_at` NULL **after commit**, emits one `:updated`, and `GET /consistency` is clean. |
| Q-3 | B | The docs guard cannot point at v8 (plan §8) **and** the checkpoint cannot be "identical". (i) The guard's c1b/c1c/c1d search `_CURRENT_HANDOFF` for every event name, error identity and all six assignment states, and c2a needs a nullability table for six serializers. v8 has two of the six tables, no assignment states, and a §6.6 table of computed fields with a `Meaning` column (c2a reads column 3 as nullability). (ii) v7's tables no longer match the shipped code: its snapshot table lists `quantity_requested` (now a call, so absent from the shipped side), and its version table lists `scheduled_activation_refreshes_requested` (gone). (iii) v8 §0 says "pointed at **v7 + v8**", while the plan says v8 alone with v7 archived. (iv) At the step-1 checkpoint the guard still reads v6. Making `active_at` nullable (migration step 1) and turning `quantity_requested` into a call makes `test_c2a…[serialize_stock_report_item_snapshot]` and `[serialize_stock_report_snapshot_version]` fail, and v6 may not be edited. | plan gap | Amend §8: at ship, write a **consolidated reference file** as a new file, never an edit: v7 + v8 merged, full tables, computed keys outside the tables as today. Point `_CURRENT_HANDOFF` at it, and move v6/v7/v8 to `archived/` unedited. This is the only option that leaves the guard's logic untouched. The alternative (teaching the guard an ordered document list with override semantics) is test-code redesign for a one-off. Amend §12 step 1: the checkpoint's expected delta is **exactly** those two c2a IDs newly failing, which go green at step 5, and nothing else. Drop "those two tests are updated in this step". |
| Q-4 | B | §4.9 adds 1–3 statements to `apply_stock_demand`. The drafts `SELECT … FOR UPDATE` runs whenever rows were created, and the insert + count update run when drafts exist. `test_c6a_statement_count_equal_across_batch_sizes_all_new` asserts `<= 8`, and the all-new path is **exactly 8** today (set_config, workspace, categories, discovery, insert, lock, update, history). So c6a fails even with no drafts. The plan does not mention C6. | intention-level constant → **owner card 3** | Once card 3 is answered: amend §4.9 with the new bound and "constant in batch size **and** draft count". Add C6 rows with 0 and ≥2 drafts present, and keep the three statements before the deadline check (step 9 stays last). |
| Q-5 | H | The payload carries `scheduled_for` "as an ISO string", and activation compares it to the stored `scheduled_activation_at` (a `timestamptz` read back as UTC). If compared as strings, or written from a client offset (`+02:00`, which is v8's own example), **every** scheduled activation is judged "moved" and silently skipped at info level. The e2e test would not catch it if it builds its own payload from the stored value. | plan gap (time, charter rule 6) | Amend §4.1/§4.5/§5.1: normalise to UTC at write. The payload's `scheduled_for` is `scheduled_activation_at.astimezone(timezone.utc).isoformat()`. Activation compares `datetime.fromisoformat(expected)` to the stored aware value as datetimes, and §7's `schedule_scheduler_mismatch` compares datetimes too. Criterion: a schedule set **through the API with a `+02:00` offset** fires and activates (it is not skipped). |
| Q-6 | H | Supersede rule 3 ("another draft … **later** … and `<= now`") has no tie-break. Two drafts with an equal `scheduled_activation_at` both activate, in processing order, which is the nondeterminism card 4 was ruled to remove. | owner semantics → **owner card 1** | Once answered: add the tie-break to §4.2 step 2 rule 3 (recommended: `(scheduled_activation_at, created_at, client_id)` compared as a tuple). Add an integration row "equal schedules → the later-created wins in either order". |
| Q-7 | H | No-op rule for the requested route. Plan §4.11 step 3: "same value **already held**" (the stored manual column). v8 §5.22: "already the **value in force**" (effective). The two diverge when a user sends the effective value on a snapshot with no override: the plan stores a manual value and emits an event, v8 does nothing. | contract divergence → **owner card 2** | Once answered: state the comparison operand in §4.11 step 3. If (a), the ship-time consolidated file (Q-3) carries the corrected sentence, and v8 is never edited. |
| Q-8 | H | §9 activate row "a body → 422 (request validation)", repeated in v8 §5.17 as a contract promise. **Unproducible as planned:** FastAPI 0.115.12 (installed) ignores the body of a route that declares no body parameter. Reproduced: POST with `{"refresh":true}` returns 200, and so does non-JSON. v7 told the frontend the body is `{"refresh_quantity_requested": false}`, so a v7-built client would be silently accepted. | plan gap (charter rule 17, externally owned behaviour) | Amend §4.2 / router: declare `body: _ActivateSnapshotVersionBody \| None = None` with an **empty** model, `extra="forbid"`. Reproduced on 0.115.12: no body → 200, `{}` → 200, `{"refresh_quantity_requested": true}` → 422, non-JSON → 422. Rewrite the row as "v7's activate body → 422; no body and `{}` → 200". |
| Q-9 | L | Requested body `{"quantity_requested": int ≥ 0 \| null}`. Two undetermined points: is the key required (`{}` → 422 or a revert?), and "strict int ≥ 0" needs an explicit bound, since `StrictInt` alone accepts `-1` (reproduced: 200). | plan gap | Amend §4.11: `quantity_requested: Annotated[StrictInt, Field(ge=0)] \| None`, **required, no default**. Reproduced: `{}` → 422, `null` → 200, `"3"` → 422. Router rows: `{}` → 422, `-1` → 422. |
| Q-10 | H | History `quantity_requested` / `quantity_requested_source` for the **existing** snapshot-driven writers is not decided. `set_…priority.py:193-203`, `set_…priority_order.py:139-147` and `apply_…priorities.py:189-197` write `row.quantity_requested` (MC-6: "its quantities the row's live ones"). Activation (§4.2 step 8) and override records write the **effective** value. With an override on the active version, a priority change would record the row's Scanner value with source `scanner` (server default), while activation's `priority_change` records the manual value. One record type would then carry two meanings. | plan gap (free choice, needs writing down) | Recommended amendment to §3.5: every record written **against a snapshot** (priority, order, apply-priorities onto the active version, activation, override) carries the effective value + its source via one helper. Scanner's `quantity_requested_change` stays row/`scanner`. Nothing reads these columns except goal credit, which filters by type (`_goal_credit.py:26-27`), so the choice is safe either way, but it must be one rule. If adopted, do it in step 2, not step 1: with no override, effective = the frozen Scanner value, which differs from the live row whenever Scanner has moved, so step 1's "identical" claim would not hold. |
| Q-11 | H | Scheduler-test hygiene, in three parts. (i) The precedent wrapper (`test_finalize_pending_step_completion_integration.py:46-59`) remaps only `begin()`, but `_fire_due_schedulers` and `_route_open_tasks` call `session.commit()` directly (`delayed_scheduler_runner.py:99`, `task_router.py:137`). On the shared `db_session` (`tests/conftest.py:107`, plain session) that **commits the whole fixture**. (ii) Both queries are global, with `limit(50)` / `limit(BATCH_SIZE)` and no `ORDER BY`. (iii) This plan's own tests (schedule, skip causes, repair (b)) create `ACTIVE` scheduler rows, some past due, and `purge_stock_report_workspace` does not delete them (they are not workspace-scoped). So the plan's docstring claim "no other test creates `DelayedScheduler` rows" becomes false as soon as these tests exist, and leaked due rows fire inside the e2e test. | plan gap | Amend §9 e2e fixture: (a) extend `purge_stock_report_workspace` to delete `delayed_schedulers` whose `event_client_id` is one of the workspace's versions, plus the execution tasks/payloads whose `origin_id` is one of those schedulers, **before** the versions are deleted. Every scheduler-creating test purges in `finally`. (b) The e2e wrapper maps `commit()` to `flush()`, or the test runs on its own committed workspace and purges. (c) Replace the docstring claim with the purge guarantee. |
| Q-12 | L | Overdue fixtures: the API refuses past times (422), so skip-cause, repair (b) and "moved after fire" rows need a construction path the plan does not name. | free choice | Delegate explicitly in §9: "an overdue schedule is built by writing `scheduled_activation_at` and a matching `ACTIVE` scheduler row directly (both, so consistency stays clean)". |
| Q-13 | H | Divergence rows for the renamed and new consistency kinds are unspecified. `GET …/consistency` returns `{kind, client_id, field, stored, expected}` (api.md:78), and api.md:135-137 enumerates the kinds. §7/§4.12 give neither the four fields for `snapshot_version_state_mismatch` (ii)/(iii), `draft_membership_mismatch` (what is `client_id` for a snapshot that does not exist: the version, or the row?) or `schedule_scheduler_mismatch` (a)/(b)/(c), nor the repair record's `target_id`. The scheduler kind also has no workspace scoping: `delayed_schedulers` has no workspace column, and `payload_snapshot` is `JSON`. §8 does not list the api.md kind list. | plan gap | Amend §7 with one table: kind → `client_id` / `field` / `stored` / `expected` / repair `target_kind` + `target_id`. Recommended: membership rows name the **version** as `client_id` and the row id in `expected`/`stored`. Scope scheduler rows by `event_client_id ∈ the workspace's version ids`, and state that orphans (version already deleted) are out of scope and harmless (handler 404 → skip). Add api.md:135 to §8. |
| Q-14 | L | The step-1 perimeter is undercounted. Renaming the ORM attribute breaks `tests/helpers/stock_report.py:202` (seeds snapshots with `quantity_requested=`) and a mechanical set of test references (≈20 files mention a snapshot's `quantity_requested`). The plan says only two tests change. | plan gap | Amend §12 step 1: tests that construct or read the renamed attribute are renamed **mechanically, with no expected value changing**, and `test_schema_contract` is updated. The checkpoint's expected delta is stated by ID (Q-3 (iv)). |
| Q-15 | L | Appendix B row `get_stock_report_missing_summary` ("the column → effective") and §6's "both already have the row" are false. The query reads only `quantity_missing` and joins no row (`get_stock_report_missing_summary.py:16-31`). Only its predicate changes (Appendix A). | reality | Delete the Appendix B row and fix the §6 sentence, so no implementer adds a join. |
| Q-16 | L | §3.4 "`outstanding_quantity` and `missing_quantity_ceiling` … signatures gain the row". `missing_quantity_ceiling` takes `quantity_requested=` as a keyword, not a snapshot (`snapshot_rules.py:77-90`). Its signature is unchanged; callers pass the effective value. Only `outstanding_quantity` changes. | reality | One-word fix. |
| Q-17 | L | `serialize_stock_report_item(row, category, snapshot)` (`serializers.py:28-60`) must thread `active_quantity_missing` to the snapshot serializer. The `live_stock=true` read (which joins the active snapshot) passes that snapshot's own `quantity_missing`. The items read joins `StockReportItemSnapshot` twice, so it needs an `aliased` entity. | free choice | Delegate explicitly in §6. |
| Q-18 | L | §4.12 membership repair "deletes the stray ones with the cascade's gap-closing". A draft snapshot of a deleted row can hold a priority. Repair must close its gap and decrement `snapshot_count`, under repair's lock sequence (versions, then schedulers last). Stated, but the §7 lock sentence covers only scheduler rows. | plan gap (small) | Add "draft snapshots and their versions are locked in repair's sequence before the scheduler rows". |

## Reality checks — verified, no finding

- **Appendix A is complete.** Every `closed_at` predicate in `services/` and `domain/` that
  touches snapshots or versions maps to a row. No site is missing (checked
  `consistency.py:186,203`, `delete_stock_report_item.py:72,83`, `repair_stock_report.py:65,177,277`
  and 24 others). `_move_assignment.py`, `_priority_filter.py` and `_locks.py` touch no predicate.
- **Appendix B is complete for readers** apart from Q-15, and the history writers are covered in
  Q-10. `_move_assignment.py:51` and `_row_values.py:21` read the **row's** value and correctly
  stay out.
- `ON CONFLICT (version_id, stock_report_item_id)` has its target:
  `uq_stock_report_item_snapshots_version_row`.
- **Lock graphs, no cycle found.** Webhook (rows → draft versions) against activation (adv →
  rows → snapshots → version), delete-draft (adv → version → snapshots), PATCH version (adv →
  version → scheduler), apply-priorities onto a draft, and the requested PATCH (row →
  snapshot). When a draft activates while a webhook waits on its version row, the webhook's
  `WHERE active_at IS NULL … FOR UPDATE` re-check after the lock drops it, so the new row does
  not join the newly active version. That matches §4.9.
- **Supersede rules for distinct times**, walked in both orders: Monday/Tuesday overdue; a hand
  activation before and after the scheduled time; an earlier scheduled draft processed late.
  Deterministic in each. The only hole is the tie (card 1).
- **Citations resolve:** `create_stock_report_snapshot_version.py:129-130,153-154`
  (`active_at = created_at`) · `services/commands/task_steps/transition_step_state.py:211-251`
  (commented-out producer; no production caller of `create_delayed_scheduler` exists) ·
  `Procfile` (`delayed-scheduler`, `task-router`, `tasks-worker`) ·
  `DELAYED_TYPE_TO_TASK_TYPE`, `QUEUE_MAP`, `HANDLER_MAP` and the handler signature
  `(payload: dict, task_client_id: str)` · `_retry_errored_schedulers` retries only
  `scheduled_for > now` (true) · `create_delayed_scheduler(…, event_client_id=…)` exists ·
  `ServiceContext(identity, incoming_data, session, now=…)` fits the handler sketch · reset
  order (snapshots 157, versions 158) leaves version ids available for the cancel phase ·
  `f4a1c9d8e2b0` precedent exists.
- **Counts derived:** route count 19 → 28 = 9 new `(method, path)` pairs (activate, refresh,
  PATCH / DELETE / GET version, and four versioned row routes). Event names 13 = 6 + 7, which
  matches v8 §7.
- The goal credit (`_goal_credit.py:19-36`) and `goal_total` consistency filter by
  `QUANTITY_REQUESTED_CHANGE`, so the new `quantity_requested_override` type can never be
  credited.

## Criteria decidability

§9 is prose, not lettered rows. This is the owner's format for this plan and I do not re-open
it. Read as rows, every bullet is decidable from the artifacts once Q-1 to Q-14 are folded,
**except**: the activate "body → 422" row (Q-8, unproducible as written); the e2e scheduler row
(Q-11, its fixture claim is false once sibling tests exist); the checkpoint's "identical failure
set" (Q-3 (iv), Q-14); and the no-op row of the requested route (Q-7). Externally owned shapes
were grounded by controlled reproduction on the installed FastAPI 0.115.12 / Pydantic 2.11.3
(Q-8, Q-9) and by reading the installed runner/router source (Q-11). The one Postgres-owned
claim (per-statement, non-deferrable CHECK evaluation) is the premise of Q-1 and of the plan's
own R-2 reasoning, and it is standard behaviour for a non-deferrable CHECK.

## Write perimeter of this session

- **New:** this file.
- **Appended:** `docs/archgraph-anchor-observations.md` (standing owner brief, one entry).
- **Memory:** `project_stock_report_draft_versions.md` updated (r2 pointer).
- **No** code, plan, handoff (v7/v8) or graph change. No `archgraph_*` call. The two FastAPI
  reproductions ran inline in the shell and left no files.
