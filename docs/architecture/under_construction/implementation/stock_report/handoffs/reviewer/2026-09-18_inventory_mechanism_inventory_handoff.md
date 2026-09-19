---
plan: (pre-plan, project-level — no master plan and no phase plans exist yet)
role: reviewer (mechanism-inventory gate)
round: inventory
date: 2026-09-18
verdict: OWNER_DECISIONS_PENDING — all cards answered 2026-09-18 (9→C, 10→A, 11→A, 9a/9b/10a/11a→A); pending only the shaper fold + owner re-ratification
actor: Claude Opus 5 (1M context), mechanism-inventory session
---

# Mechanism-inventory handoff: `stock_report`

## Opening summary

The gate was run against the intention at `2ee6f5b`. The first check was on `f89a3fa`. A
concurrent shaper session added §8A and published the Scanner v1 handoff mid-session; the owner
committed that work, and the gate was re-checked clean before any write. **Twenty mechanism
contracts** (MC-1…MC-20) are now written into the intention as lettered sections (§4A, §4B, §5A,
§5B, §6A, §7A, §8B, §9C, §9D, §9E, §12A). They are registered against M1–M9 in §13A, and a
37-row supersession ledger (§14C) states which sentence ships wherever an earlier section and a
contract disagree. Every mechanism the prompt listed now has a contract-grade definition, or a
card where the definition needs the owner.

Source reading turned up five things the ratified text had wrong or missing:
1. **Three §2.3 absence claims are false.** A task can be *created* `stalled`, `ready` or
   `resolved`. A terminal task, even a deleted one, returns to `pending` when its last step is
   removed. §2.3's caller list omits three drivers of the step core.
2. **A second writer of an item's category exists** (`find_or_create_item`, reached from task
   creation), which B6's guard does not cover. This is card 10.
3. The §6.2 floor and the §4.1 `>= 0` check point opposite ways; a floor can only ever hide
   drift. This is card 9.
4. The **workspace reset** hard-deletes tasks, items and categories, and would fail on the new
   tables' RESTRICT FKs. Added as a must-ship (§12A).
5. The **arrival-order hazard** the prompt flagged is real, and it writes permanent phantom goal
   records. This is card 11, and option B is material.

Every contract fits inside the published v1 Scanner handoff: no v1 field changes. Two things
would ship as a v2 file at closeout: the processed `reason` codes, and card 11's option B.

**Gate verdict: `OWNER_DECISIONS_PENDING`.** Cards 9–11 were answered the same day. Card 9's
answer (self-healing repair, with the repair tool now must-ship) is a **material change**: the
intention returns to COLLABORATING when the shaper folds it. The four follow-up cards (9a, 9b,
10a, 11a) are open.

## Owner decisions, round 6: answered 2026-09-18 (3). The cards as presented:

**Card 9: the board's numbers are already wrong when a task moves**
- **Question:** Should that task action fail (A), or go through with the count stopped at zero (B)?
- **Story:** A bug leaves "in queue" at 0 on the Teak chairs row while a set of 4 is queued. Anna starts the set. Under A her start fails until a developer repairs the row, so the bug shows at once. Under B it works, the count sticks at 0 instead of −4, and the bug's trace can vanish while planners read wrong numbers.
- **Branches:** A: wrong counts never persist; a worker can be blocked until repaired (the repair tool is deferred). B: nothing blocks; drift can hide from everyone but the consistency report.
- **Recommendation:** A. Only a code defect causes drift, and finding it on day one beats months of a misleading board.
- **On silence:** the gate holds.
- **Trace:** §5A MC-1, §6A MC-5, §4.1, §6.2, M1, M5.

**Card 10: a category change through a new task**
- **Question:** When a new task names an item that is on the board with a different category, should Manager refuse (A), keep the item's category (B), or change it (C)?
- **Story:** A teak side table is on the "Side Tables · Teak" row. A seller opens a return task for the same article number, and the form sends "Coffee Tables". Today the backend silently re-categorises the item, so the row now holds a coffee table: the case you ruled out for item edits, arriving through a second door.
- **Branches:** A: the task is refused ("unassign it from the stock report first"). B: the task is created and the item keeps its category silently. C: the board holds a wrong item.
- **Recommendation:** A. It is your round-5 rule, applied to the other door into the same field.
- **On silence:** the gate holds.
- **Trace:** §14B B6, §5B MC-14, §14C C30, M8.

**Card 11: an old demand message arriving late**
- **Question:** Should Manager skip a Scanner demand message older than one it already applied (B), or accept whatever arrives last (A)?
- **Story:** At 10:00 Scanner sends "Teak chairs: 5 missing". The call is slow, and Scanner retries at 10:01 with the fresh 3, which lands first. Then the 10:00 call finishes: the board says 5, and because 5 > 3 the history gains a goal that never existed. The next push fixes the 5; the phantom goal stays forever.
- **Branches:** A: as published; rare, the number self-heals, phantom goals can stay. B: Scanner adds a send-time header and Manager skips older messages. That means a v2 handoff, one column, a small Scanner change, and re-ratification.
- **Recommendation:** B. The Scanner sender is not built yet, so this is the cheapest moment.
- **On silence:** the gate holds.
- **Trace:** §8B MC-9, §6.1, M3, M5, the v1 handoff §6.3.

---

## Owner answers — 2026-09-18 (owner: David, in this session)

Recorded verbatim, then how each lands. **The intention is not edited by this session.** The
owner routes these answers to the intention-shaper, who folds them.

| Card | Owner's words | Resolution | Folds into |
|---|---|---|---|
| 9 | "I will actually prefere for the repair tool to be build and in those cases where negative values are trying to be recorded the repair tool runs first to then allow the transaction. so the repair tool is improtant to have it working in this implemtnation already ( which will be used already for tests technically )" | **Neither A nor B: a third branch, C (self-heal).** When a move would write a negative value, the repair runs for that row inside the same transaction, and the move then proceeds. The repair tool moves from *deferred* (§12, a settled item) to **must-ship**. That reopens a settled scope decision, so it is a **material change**: the status must go back to COLLABORATING and the owner re-ratifies. | §12 scope ladder; §5A MC-1 counter statement; §6A MC-5 floor; §12A MC-20 (check → check + repair); §14C C10 |
| 10 | "yes that is correct that category re-assignment should not happen also on that task creation situation." | The category must not change through `find_or_create_item` / `create_task` while the item has an active assignment. **Which branch (refuse = A, or keep the category = B) is not yet certain**, so it is asked as card 10a. | §5B MC-14 last row; §14C C30 |
| 11 | "i have already resolve this type of situations on the scanner handoff, the scanner will read the current requested values so it will not have stall payloads that can fabricate those types of issues. the transaction thus continues to be indepotent." | **A**: no send-time stamp and no contract change; v1 stands. One residual case needs no Scanner change and is asked as card 11a. | §8B MC-9 last bullet; §14C C37 |

**Mechanism under 9 → C**, settled by this gate and to be written by the shaper as part of MC-1,
MC-5 and MC-20:
- *Trigger:* inside `move_assignment`, before a counter UPDATE whose result would be `< 0`. It is
  checked under the row lock: `SELECT` the current value, or use `UPDATE … WHERE col + :d >= 0`
  and treat 0 rows as the trigger. The same applies to a goal-record subtraction.
- *Repair, same transaction, same lock:*
  - the row's three counters are set to the sums of stored `quantity` over its non-deleted
    assignments, **after** the moving assignment's new state is written (the absolute values
    replace the delta);
  - a goal record's total is set to the sum over the assignments credited to it (MC-5
    recomputation).
- The DB checks `>= 0` stay. They are now reachable only by a defect in the repair itself.
- Inline repair only fires on the *downward* case. Drift upward (a count too high) never triggers
  it. Only the check / repair tool finds that case, which is why the tool itself must ship (card
  9b).
- The tool is the MC-20 check with a write mode. The check stays read-only; repair is a separate
  command that uses the same recomputation. That single recomputation is the one definition of
  "correct".

## Follow-up owner decisions: answered 2026-09-18 (4). The owner's words: "9a A , 9b A , 10a A , 11a A". The cards as presented:

**Card 9a: does an automatic repair leave a trace?**
- **Question:** When Manager repairs a wrong count by itself, should it write a permanent repair record and a warning (A), or repair silently (B)?
- **Story:** A bug makes "in queue" drift on the Teak chairs row every time a set is unassigned. With B, each of Anna's actions quietly fixes it; the numbers look right, and nobody learns the bug exists until it corrupts something repair cannot fix. With A, the first repair lands in a list (which row, which number, what it was, what it became, which action triggered it) and the bug gets found.
- **Branches:** A: one small table plus a log warning; defects stay visible. B: nothing extra, and the defects stay invisible.
- **Recommendation:** A. Self-healing without a trace hides exactly what the consistency check exists to find.
- **On silence:** the gate holds.
- **Trace:** card 9, §5A MC-1, §12A MC-20, M1.

**Card 9b: what the repair tool fixes, and who runs it**
- **Question:** Beyond the automatic trigger, should admins and managers be able to run a full repair of a workspace, fixing counts, goal totals, the task "is on the board" mark, and order gaps, with rule signatures only reported (A), or should repair run only automatically (B)?
- **Story:** A count that drifts *upward* (the board says 6 in queue, really 4) never goes negative, so the automatic repair never fires. Under A a manager sees it in the consistency report and presses repair. Under B it stays wrong until a developer steps in. Signatures are only reported, because re-signing a rule can merge it into another row.
- **Branches:** A: an admin/manager repair command, also used by the tests. B: automatic only; upward drift stays until someone codes a fix.
- **Recommendation:** A. It is the tool you asked for, and the tests need it anyway.
- **On silence:** the gate holds.
- **Trace:** card 9, §12A MC-20, §9E MC-18, M1, M5, M6.

**Card 10a: refuse the task, or keep the category?**
- **Question:** When a new task sends a different category for an item on the board, should the whole task creation be refused (A), or should the task be created and the item simply keep its current category (B)?
- **Story:** A seller creates a return task for the teak side table on the "Side Tables · Teak" row, and the form sends "Coffee Tables". Under A she gets "unassign it from the stock report first" and no task exists until someone does. Under B the task is created at once, the item stays a side table, and nothing tells her the category she picked was not applied.
- **Branches:** A: loud, blocks task creation, and matches how item edits behave. B: never blocks; the category she chose is silently dropped.
- **Recommendation:** A. It matches your round-5 rule for edits, and silent drops confuse people.
- **On silence:** the gate holds.
- **Trace:** card 10, §14B B6, §5B MC-14, M8.

**Card 11a: close the last gap for a slow first call**
- **Question:** Should Manager give each demand call a time limit shorter than Scanner's patience, so a call Scanner has given up on can never finish later (A), or accept that rare case (B)?
- **Story:** Scanner now builds fresh numbers for every send, so a retry never carries old data. One gap remains. The 10:00 call (5 missing) is slow; Scanner gives up after 8 seconds and sends 3 at 10:01. If the 10:00 call is still running inside Manager, it can finish *after* the 3 and write 5 back, plus a phantom goal. Under A, Manager abandons any demand call that runs past about 5 seconds, so the late finish cannot happen.
- **Branches:** A: a Manager-side limit and no Scanner change; a very slow call fails as 5xx and Scanner simply retries. B: nothing changes; the rare phantom goal remains possible.
- **Recommendation:** A. It costs one setting and keeps the published contract untouched.
- **On silence:** the gate holds.
- **Trace:** card 11, §8B MC-9, M3, M5, the v1 handoff §3.4 (5xx = retry).

---

## Final owner answers: what the intention-shaper folds (2026-09-18)

| Card | Answer | Fold |
|---|---|---|
| 9 | **C: self-heal** | §5A MC-1 and §6A MC-5: when a move would write a negative counter or goal total, recompute that row (or goal record) from assignments in the same transaction and under the same lock, then proceed. The DB checks `>= 0` stay. §12: the repair tool moves to must-ship. **Material: the status returns to COLLABORATING; the owner re-ratifies.** |
| 9a | **A: a trace** | A new append-only table (name registered by the planner, e.g. `stock_report_repair_records`): `workspace_id`, target kind (`stock_report_item` / `history_record` / `task` / `group`), target `client_id`, field, stored value, recomputed value, trigger (`inline:<operation>` or `manual`), `created_by_id` (NULL for inline), `created_at`. Plus a warning log per repair. M1 gains an observable: every inline repair leaves exactly one record per corrected field. |
| 9b | **A: a manual repair command** | §12A MC-20 grows a write mode: an ADMIN/MANAGER command (MC-18 gains 4 cells: ADMIN ✓, MANAGER ✓, WORKER ✗, SELLER ✗). It fixes `counter_*`, `goal_total`, `task_flag`, `order_density` and `priority_order_nullness`. Order density is repaired by renumbering 1..n, keeping the current relative order with ties broken by `client_id`. `signature` is **reported only**. It uses the same recomputation as the check, runs in one transaction, and takes locks in MC-1 order (advisory lock first, because it renumbers groups). It writes one repair record per corrected field and emits `:updated` events per MC-19. Tests use it. |
| 10 | **A: guard task creation too** | §5B MC-14 last row: `find_or_create_item`'s existing-item branch refuses the category change with the same 409 as `update_item` when the item has an active assignment, so `create_task` fails as a whole. §14C C30 is resolved. |
| 10a | **A: refuse** | (same as above) |
| 11 | **A: no stamp** | §8B MC-9 last bullet: no `x-sent-at`; the sender builds payloads at send time (v1 §6.3). No v2 is needed for this. |
| 11a | **A: a Manager time limit** | §8B MC-9: the demand webhook's transaction runs under `SET LOCAL statement_timeout` and `lock_timeout` so that the whole request aborts before Scanner's 8 s client timeout (`outbound-webhook-worker.ts:DISPATCH_TIMEOUT_MS`). The budget is 5 s, a named setting with that default. An abort rolls back and answers 5xx, which Scanner retries (v1 §3.4). Charter rule 10: a criterion must show the shipped default is actually applied. If the Scanner sender uses a different timeout, the setting must stay below it (a sender note for the closeout handoff, additive, no v2). |

**After the fold and re-ratification**, this gate re-checks only MC-1, MC-5, MC-9, MC-14, MC-18
and MC-20, plus the new repair-record table, and then answers `PASS`.

## 1. Inventory table

Risk: **S** = silent (plausible wrong number or row, nothing crashes); **L** = loud. "Before" is
the state in the ratified text at `2ee6f5b`.

| MI | Mechanism | Risk | Contract before | After | Lives in | Ledger |
|---|---|---|---|---|---|---|
| 1 | transition op + unit counters; lock order; `>=0` behaviour | S | adjectives ("atomic", "same transaction") | total move table, one column-referencing UPDATE with RETURNING, a 6-class global lock order; the floor question → card 9 | §5A MC-1 | M1 |
| 2 | task-state sync | S | a site table (callers incomplete); "guard proven able to fail" | command-level sync on net change, 9 sync sites + 4 registered no-sync, an AST registry guard with 6 planted probes | §5B MC-2 | M2 |
| 3 | row identity normalization | S | B1 prose (4 bullets); P30 | per-type table incl. blank/empty/mixed; keys untouched; idempotence; stored = normalized, echo = raw; golden vectors instead of a version column | §4A MC-3 | M4 |
| 4 | one active assignment per item | S | index named, predicate implicit | exact predicates; a second per-task index; race tested on the lock path with the reason code asserted | §4A MC-4 | M4 |
| 5 | goal-record running total | S | §6.2 prose + floor | total event table (9 rows); recompute incl. deleted; worked 6-step sequence; floor → card 9 | §6A MC-5 | M5 |
| 6 | history write rules | S | §6.1 table | previous-stored comparison under lock; 5→3→4 row; timing (after all mutations, the op's `now`) | §6A MC-6 | M5 |
| 7 | dense ordering | S | "enforced by the commands" | before/after tables for 10 operations; workspace advisory lock + ascending row locks; race table | §7A MC-7 | M6 |
| 8 | webhook boundary | L/S | "auth before parsing"; str `compare_digest` precedent | a 9-step order with a status per step; bytes compare; identical 401 bodies; entry-defect tables; exact-then-unique category match; workspace passed explicitly | §8B MC-8 | M7, M3 |
| 9 | idempotency | S | "replays change nothing" | zero INSERT/UPDATE/DELETE + zero events, via a statement-count instrument; arrival order → card 11 | §8B MC-9 | M3 |
| 10 | processed resolution | S | "no-op, not an error" | outer-trim + exact match; 4-value closed decision order; duplicates evaluated in order | §8B MC-10 | M3 |
| 11 | concurrent writers on one assignment | S | B5 semantics, no mechanism | lock + re-read after lock; a two-row interleaving table with counters and goal | §5A MC-11 | M1, M2 |
| 12 | criteria matcher mirror | S | §9A prose, E7–E9 | bag construction (6 steps, mirrors `toPropertyValue`, `normalizeStoredProperties`, the excluded keys); per-key decision table; 4-code closed enum | §9C MC-12 | M8 |
| 13 | creation checks + override | S/L | 3-item list | 6 phases, 8 ordered reasons, 2 batch-duplicate reasons, 422 vs 409 precedence, structured envelope, retry-from-scratch contract | §9C MC-13 | M8, M1, M4 |
| 14 | task-/item-side removals + category guard | S | B4/B6 prose | 5-row hook table with exact placement and lock order; second category writer → card 10 | §5B MC-14 | M2, M8 |
| 15 | `Task.is_stock_assignment` | S | truth condition | 2 writers; a Core UPDATE with a self-assigned `updated_at` so `onupdate` cannot fire; not read by the sync | §4B MC-15 | M1 |
| 16 | soft-delete interplay | S | "exclude deleted rows" | 10-row predicate table; row-deletion cascade order | §5A MC-16 | M1, M4, M6 |
| 17 | authorship | S | 3-row table | 11 operations × 3 tables; performer not credited worker; no `onupdate=` anywhere | §4B MC-17 | M9 |
| 18 | roles | L | 4-row matrix | 28 cells; refusal in `require_roles` (403) before the service | §9E MC-18 | M9 |
| 19 | events | S | §9B table + "no event on no-op" | a net-change rule (per-entity snapshot), one event per entity per request, a 9-row operation table, typed payloads from committed values | §9D MC-19 | MC-19 (mechanism contract) |
| 20 | consistency check | S | "recomputes counters and flags" | 8 divergence kinds, output shape, read-only via statement count, 8 planted-drift probes | §12A MC-20 | M1 |
| 21 *(added)* | workspace reset vs the new RESTRICT FKs | L | absent | 3 new reset phases, ordered before tasks/items/categories/users | §12A | M1 |

## 2. Contradiction list

Authoritative in the intention: **§14C, 37 rows (C1–C37)**. Each row quotes the earlier sentence,
names the later source, the side that ships, and what the other side would have shipped. It is
not duplicated here, so it has one home (charter artifact map). By class:
- **Superseded by §14B:** C1, C2 (identity), C3, C4 (scoped, no conflict).
- **Absence claims false at source:** C5, C6, C7, C8.
- **Inside §1–§13:** C10 (card 9), C11 (units in the §3 diagram), C12, C15, C17, C18, C19, C20, C21, C22, C27.
- **Against §8A / the v1 handoff:** C13, C25, C26, C36 (confirmed), C37 (card 11).
- **Unilateral mechanism readings:** C9, C14, C16, C23, C28, C29, C33, C34, C35 (and see §4).
- **New must-ship:** C32 (reset).

## 3. Matcher hand-walk (MC-12)

**Grounding.** Criteria shapes are the output of `normalizeCriteria`
(`apps/backend/src/modules/stock/domain/property-criteria.ts:29-55`), which is what `LocationStock`
stores (`repositories/location-stock.repository.ts:105-112`). The rule *values* come from the rule
labels in `LC-STOCK-REPORT.md` (Scanner repo root, generated from the live DB 2026-09-08), with
the labels mapped to keys through `shared/item-properties/item-property-options.ts:ITEM_PROPERTY_OPTIONS`:
"Set size" → `quantity`, "Wood group" → `wood_group`, "Wood type" → `wood_type`. The exact
criteria JSON was **not** read from Scanner's DB (see §7 N7). Manager item shapes are the output of
`bm/services/queries/items/lookup/purchase_api.py:parse_purchase_api_attributes`: string values
stripped, non-string values kept as they are. Set size is `bm/models/tables/items/item.py:Item.quantity`
(`int`). Scanner's verdict comes from the report's counted / "why not counted" columns.

| # | Rule (report line) → stored criteria | Manager item (properties; `quantity`) | Arithmetic | Manager | Scanner (report) |
|---|---|---|---|---|---|
| H1 | Armchairs "Wood group: Dark" (:51) → `{"wood_group":["dark"]}` | Ch9-250326 `{"wood_type":"Walnut"}`; 4 | first token `walnut` → Dark → bag `wood_group:"Dark"` → tokens {dark} ∋ dark | match | counted ✓ |
| H2 | Coffee "Wood group: Light" (:92) → `{"wood_group":["light"]}` | Ct2-110326 `{"wood_type":"Elm, Beech"}`; 1 | first token `elm` → Light | match | counted ✓ |
| H3 | Coffee "Wood group: Teak" (:98) | St1-030726 `{"wood_type":"Teak, Oak"}`; 1 | first `teak` → Teak ✓; against the Light rule: Teak ∌ light → `wood_group: value_not_accepted` | match / mismatch | counted under Teak only ✓ |
| H4 | Dining Chairs "Set size: 4 · Upholstery: Down · Wood group: Teak" (:111) → `{"quantity":["4"],"upholstery":["down"],"wood_group":["teak"]}` | Ch3-200826 `{"wood_type":"Teak","upholstery":"Down"}`; 4 | `"4"`∋4 ✓, {down} ✓, Teak ✓ | match | counted ✓ |
| H4′ | same rule | same item **without** `upholstery` (a Shopify-only key, E10) | `upholstery: missing_on_item` | 409 → override | Scanner counts it (it has Shopify) — the accepted §9A limit |
| H5 | "Set size: 4 · Upholstery: Up & Down · Wood group: Light" (:117) | Ch2-130826 `{"wood_type":"Oak","upholstery":"Up & Down"}`; 4 | tokenizer keeps `up & down` whole (no split on `&`) ✓ | match | counted ✓ |
| H6 | "Set size: 8 · Upholstery: Up & Down · Wood group: Teak" (:123) | Ch4-010926 `{"wood_type":"Teak","upholstery":"Up & Down"}`; 8 | `"8"` ✓ | match | counted ✓ |
| H7 | H4's rule | Ch7-200826 `{"wood_type":"Teak, Beech","upholstery":"Down"}`; 2 | `quantity`: {2} ∌ 4 → `value_not_accepted`; the rest ✓ | mismatch [quantity] | "Set size is 2, but the rule tracks 4" ✓ |
| H8 | H4's rule | Ch4 19.09 `{}`; 1 | failures sorted by key: `quantity: value_not_accepted`, `upholstery: missing_on_item`, `wood_group: missing_on_item` | mismatch ×3 | set size 1 / no upholstery / no wood type ✓ |
| H9 | Dining Tables "Shape: Oval · Wood group: Light" (:131) → `{"shape":["oval"],"wood_group":["light"]}` | T4-200526 `{"wood_type":"Oak","shape":"Oval"}`; 1; variant `"shape":"Oval/Rectangular"` | {oval} ✓; variant {oval, rectangular} ∋ oval ✓ (any-of) | match / match | counted ✓ |
| H10 | "Shape: Round · Wood group: Dark" (:139) | T1 11.06 `{"wood_type":"Santos Rosewood","shape":"Round"}`; 1 | first token `santos rosewood` → Dark | match | counted ✓ |
| H11 | Sofas "Wood type: any" (:250) → `{"wood_type":null}` | Malmsten sofa `{"wood_type":"Elm"}`; 1 / variant `{}` | present with ≥1 token → wildcard passes / absent → `missing_on_item` | match / mismatch | counted ✓ / (n/a) |
| H12 | H1's rule | an item `{"wood_type":"Other"}` (the one wood in no group, `wood-groups.ts` header) | present, derives no group → `no_group_for_value` | mismatch | "no wood group applies" ✓ |
| H13 | `{"drawers_range":["3-5"]}` (no live rule yet; `drawer-ranges.ts:28-32`) | `{"drawers_qty": 4}` (an **int**, kept by Manager's parser) | coerced `"4"` (`toPropertyValue`) → `[0-9]+` → 4 ∈ 3-5 | match | `drawerRangeOf("4")` = `3-5` ✓ |
| H14 | same | `{"drawers_qty":"0"}` / `{"drawers_qty":"4.0"}` / `{"drawers_qty":4.0}` (float) | 0 in no range / not `[0-9]+` / coerced `"4"` | `no_group_for_value` / `no_group_for_value` / match | same three verdicts (`drawer-ranges.ts:77-90`; JS `String(4.0)` is `"4"`) |
| H15 | `{"wood_group":[]}` (only a hand-made or non-Scanner payload can hold this) | any | not understood | `criterion_not_understood` | Scanner would reject the rule at `normalizeCriteria` |
| H16 | `{"quantity":["4"]}` | `properties = NULL`; 4 | relocated key present (C16, unilateral) | match | n/a (Scanner items without metafields have no set size) |

## 4. Unilateral resolutions: listed for owner ratification

Each is decided by this gate as a consequence of ratified text. The right-hand column is what the
other reading would have shipped.

| # | Resolution | Where | Other side would have shipped |
|---|---|---|---|
| U1 | The sync runs once per command, on **net** task-state change, not inside the three helpers | MC-2 | `remove_task_step`'s ready→pending→ready moving an assignment twice, un-crediting and re-crediting (possibly to a different goal record), and two spurious events |
| U2 | The sync's skip is an assignment query; the stored flag is not read | MC-2, C9 | a skip on a flag loaded before a concurrent creation committed: an assignment stuck `in_queue` behind a `working` task |
| U3 | A flag flip never moves `tasks.updated_at` / `updated_by_id` | MC-15 | every assign/unassign bumping the task's `updated_at` (and reordering any list sorted by it) with a stale `updated_by` |
| U4 | Criteria keys are not normalized; blank strings and empty lists are "not understood" and stored as received | MC-3 | keys case-folded (splitting nothing Scanner sends, but inventing a rule Scanner lacks), or Scanner's throw becoming a rejected batch, against P30 |
| U5 | No version column; the algorithm is frozen, pinned by golden vectors, and any change needs a re-signing migration | MC-3 | a new column and a mixed-version table |
| U6 | Category: exact match first, then case-insensitive only if unique, else `category_not_found` | MC-8, C14 | an arbitrary pick between case-variant categories (the `.limit(1)` precedent) |
| U7 | Unknown keys in webhook entries are ignored | MC-8 | a Scanner that adds a field breaking all demand with 422s (v1 forbids nothing) |
| U8 | Article number: outer trim, exact, case-sensitive; no inner folding | MC-10 | folded numbers colliding under Manager's uniqueness |
| U9 | The relocated `quantity` key is evaluated even when `properties` is NULL | MC-12, C16 | a set-size-only rule refusing every property-less item on set size |
| U10 | Item values are coerced to Scanner's string forms, and the Scanner-excluded keys (incl. stored `wood_group`/`drawers_range`/`quantity`) are dropped before derivation | MC-12 | a Manager `int` value, or a stored derived key, silently disagreeing with Scanner (e.g. `drawers_qty: 4` failing) |
| U11 | Task delete, PRIMARY unlink and item delete remove assignments in **any** state | MC-14, C23 | resolved rows of deleted tasks still listed on the board |
| U12 | Assignment `updated_*` is NULL at creation; deletion stamps only `deleted_*`; a row deletion stamps `updated_*` as well | MC-17, C29 | — (unstated before) |
| U13 | The actor of a synced move is the performer (`ctx.user_id`) | MC-17, C28 | a credited worker recorded for a manager's action |
| U14 | The consistency check also covers order density, null⇔null, goal totals and signatures | MC-20, C18 | M4/M5/M6 fields without an instrument |
| U15 | A per-task partial unique index on active assignments | MC-4, C34 | "one per task" holding only while every hook fires |
| U16 | New locks: `remove_item_from_task` locks the Task; `delete_item` locks the Item; the category guard locks the Item | MC-14, C33 | creation racing an unlink/delete/category edit and leaving a broken pairing |
| U17 | A created row emits `:created` only | MC-19, C35 | two events per new row |
| U18 | Creation: hard failures 422 (`stock_assignment_refused`) take precedence over the 409 property mismatch; the local API errors carry `code` + `details` | MC-13 | offering an override for a batch that would fail anyway; an override the frontend cannot parse |
| U19 | All webhook 401s share one body | MC-8 | telling a prober which setting is missing |
| U20 | Workspace-reset phases for the three tables | §12A, C32 | a reset that fails on the first stock row |
| U21 | §8A's two shaper additions confirmed (empty array → 422; processed duplicates not an error) | C36 | — |

## 5. Write-site audit (MC-2)

- **Search.** Run 2026-09-18 on the tree at `2ee6f5b`. Scope: `app/beyo_manager/**/*.py` and
  `app/scripts/**/*.py`, excluding `app/tests/**` and `app/migrations/**`. Terms:
  `\.state\s*=[^=]`, `\.state\s*=\s*TaskStateEnum`, `setattr\(`, `update\(\s*Task\b`,
  `(^|[^A-Za-z_])Task\(`, `state\s*=\s*TaskStateEnum\.`, `UPDATE tasks` / `text(` with `tasks`,
  plus callers of `maybe_advance_task_to_working|maybe_reopen_task_to_working|maybe_evaluate_task_ready`
  and `_apply_step_transition\(`.
- **Proof the search can observe a hit** (charter rule 15): `\.state\s*=[^=]` returned 50 raw
  hits. 8 are `Task.state` writes, 38 are other-model writes (execution tasks, schedulers, steps,
  cases, requirements, post-handling, coordination, orders), and 4 are prose (3 comments or
  docstrings, plus the SQL text in `scripts/apply_db_triggers.py:29`). `setattr\(` returned 18
  sites. The guard's registry classifies them all; the counts are from the command, not typed.
- **`Task.state` writes (8 + 1 constructor):**
  - `_task_state_transitions.py`: `maybe_advance_task_to_working`, `maybe_reopen_task_to_working`, `maybe_evaluate_task_ready`
  - `resolve_task.py:resolve_task`
  - `fail_task.py:fail_task`
  - `cancel_task.py:cancel_task`
  - `add_task_steps.py:add_task_steps` (:158)
  - `remove_task_step.py:_remove_task_steps_in_session` (:225)
  - `create_task.py:create_task`, the constructor (vacuous for the sync)
- **Per-site feasibility** (session, transaction owner, actor, event path): the table S1–S9 in
  intention §5B. Every site has an ORM session in scope and a loaded-state capture already. The
  only one without `ctx` is S9 (the deferred-completion worker, dormant), which is why the sync
  takes explicit arguments.
- **Core drivers that cannot change task state:** `declare_worker_state`,
  `_clock_worker_shift.clock_out_shift_for_user` and
  `_case_created_step_pause.pause_task_working_steps_for_case`. Each passes the literal
  `new_state=TaskStepStateEnum.PAUSED`, which the guard asserts.

## 6. Absence-claim ledger

| Claim (source) | Search | Scope | Result |
|---|---|---|---|
| "No single place where task state changes" (§2.3) | §5 terms | §5 scope | **true**: 8 writes in 6 files (+ the `create_task` constructor) |
| §2.3 table lists every `Task.state` write | same | same | **true** for writes |
| §2.3 lists every caller of the helpers | `_apply_step_transition\(`, helper names | `app/beyo_manager` | **false**: 3 drivers missing (C8) |
| "`stalled` is never written by any command today" (§2.3) | `TaskStateEnum.STALLED` (2 hits, both read-only sets in `commit_item_cost_evaluation.py:69`, `cancel_upholstery_requirements.py:36`) + `request.state` in `create_task.py` | `app/beyo_manager` | **false**: `create_task` accepts any `TaskStateEnum` (C5) |
| "Terminal tasks never reopen" (§2.3) | writers whose precondition admits a terminal state | same | **false**: `remove_task_step(s)` → `pending`, with no terminal or deleted guard (C6) |
| "`maybe_evaluate_task_ready` is the only entry into `ready`" (§2.3; graph node `helper-task-state-transitions`) | `READY` writes + `request.state` | same | **false** for task creation (C7) |
| "`delete_item` touches no task" (§14B B4) | read `delete_item.py` | the file | **true** |
| Only `remove_item_from_task` ends a `TaskItem`; roles never change | `removed_at\s*=[^=]`, `\.role\s*=[^=]`, `TaskItem\(` | `app/beyo_manager/services` | **true** (other `removed_at` hits are memberships and dependencies) |
| `update_item` is the one item command that changes `item_category_id` (implied by B6) | `item_category_id\s*=` | `app/beyo_manager/services/commands` | **false**: `find_or_create_item.py` existing branch (C30, card 10) |
| No command soft-deletes an `ItemCategory` | `\.is_deleted\s*=\s*True` | `app/beyo_manager/services` | **true** (the reset hard-deletes; the bootstrap deletes upholstery categories only) |
| "Exactly two derived keys" (E8) | read `best-match.ts:deriveItemProperties` | Scanner, commit `0d80bf2` | **true** |
| No default-workspace setting exists (§2.5) | `workspace` in `config.py` | the file | **true** (only `BOOTSTRAP_WORKSPACE_*`) |
| The only category match-by-name precedent is case-insensitive (§2.2) | `func\.lower\(ItemCategory\.name\)`, `ilike` | `app/beyo_manager` | **true** (`purchase_api.py:_find_category_id_by_name`, which picks with `.limit(1)`) |
| No Stock Report graph nodes (§15) | `archgraph_search_nodes("stock report")` | graph revision `fa1c510e…` | **true** (0 results) |

## 7. What could not be settled from source

| # | Question | Evidence that would settle it |
|---|---|---|
| N1 | Are Manager's stored article numbers spelled like Scanner's barcodes (`04 2 001 0034`, `87392074 / 17733559`)? | `SELECT article_number FROM items WHERE article_number ~ '[ /]'` on Manager prod, joined against a Scanner barcode export |
| N2 | Do live Manager items carry non-string property values (U10 matters only if they do)? | `SELECT DISTINCT jsonb_typeof(value) FROM items, jsonb_each(properties)` |
| N3 | Do case-variant category names exist in any workspace (U6)? | `SELECT workspace_id, lower(name), count(*) FROM item_categories GROUP BY 1,2 HAVING count(*) > 1` |
| N4 | Will the Scanner sender reuse the outbound worker's 4xx-drop and at-enqueue payload behaviour (v1 §6.2–6.3)? | the Scanner sender design (not built) |
| N5 | Does Manager's `Item.quantity` hold the set size for chair sets, as MC-12's relocated key assumes? | Manager rows for Ch3-200826, Ch4-010926, Ch2-130826: `quantity` should be 4 / 8 / 4 |
| N6 | Is any other process writing `tasks.state` outside the Python code (DB triggers, manual SQL)? | `scripts/apply_db_triggers.py:16-30` was read: its only trigger is `trg_task_open` on `execution_tasks`; a `pg_trigger` listing on prod would close it |
| N7 | The exact stored criteria JSON of the live rules used in §3 | `SELECT itemCategory, properties FROM LocationStock WHERE location LIKE 'LC%'` on Scanner |

## 8. Findings outside this project's perimeter (reported, not fixed)

| # | Finding | Evidence | Stock Report effect |
|---|---|---|---|
| X1 | `remove_task_step(s)` resets a terminal **or soft-deleted** task to `pending` when its last step is removed | `remove_task_step.py:_remove_task_steps_in_session` (the task select has no `is_deleted`/terminal filter; `:224-227`) | handled: MC-1 allows `awaiting → in_queue`, and failed assignments stay final |
| X2 | `create_task` accepts any initial `state`, including `ready`/`resolved`, bypassing `maybe_evaluate_task_ready`'s side effects | `create_task.py:109-113`; `requests/__init__.py:CreateTaskRequest.state` | none (no assignment exists at creation) |
| X3 | The Connecteam webhook verifier compares `str` with `hmac.compare_digest`, which raises `TypeError` → 500 on a non-ASCII header | `webhook_verifier.py:23` | not copied (MC-8) |
| X4 | `ItemCategory` name uniqueness is case-sensitive while lookups are case-insensitive with `.limit(1)` | `item_category.py`, `purchase_api.py:_find_category_id_by_name` | handled (U6) |

## 9. Architecture graph

Oriented: `archgraph_status` (valid; 211 nodes / 327 edges; 14 pending reviews), node
`helper-task-state-transitions` read, and a search for "stock report" (0). **Nothing was
recorded**, per the prompt ("never promote, reject or edit review items"). This session **would
have** filed through `archgraph-discrepancies`:
- `helper-task-state-transitions`: its description claims `maybe_evaluate_task_ready` "is the ONLY
  sanctioned way into READY", which `create_task` contradicts (X2).
- The same node's incoming `calls` edges list only `command-transition-step-state` and
  `task-finalize-pending-step-completion`. Missing: `_step_transition_core._apply_step_transition`,
  `force_task_ready`, `add_task_steps`, and `remove_task_step._remove_task_steps_in_session`.

No Stock Report nodes are due before implementation.

## 10. Write perimeter

Generated from `git status --porcelain` and `git diff --name-only` after this session's writes (see
the verification block appended below):
- `docs/architecture/under_construction/implementation/stock_report/planning/intention.md` (modified: §4A, §4B, §5A, §5B, §6A, §7A, §8B, §9C, §9D, §9E, §12A, §13A, §14C inserted; header round line; top owner-decisions section; §17 Open; §18 round 6)
- `docs/architecture/under_construction/implementation/stock_report/handoffs/reviewer/2026-09-18_inventory_mechanism_inventory_handoff.md` (new — this file)
- `docs/archgraph-anchor-observations.md` (modified: one appended entry, owner's standing log)
- Tool-recorded state: **none** (no archgraph writes; no DB access; no test runs).
- Verified: `git status --porcelain` shows exactly these three paths (the handoff is under the new
  untracked `handoffs/` directory).
- Scratch (outside the repo): session scratchpad `delta/` drafts.

## 11. Gate verdict

**`OWNER_DECISIONS_PENDING`**, with no open questions left. Every card is answered (see "Final owner
answers"). What remains is procedural:
1. The intention-shaper folds the table above into the intention. Card 9 → C is material, so the
   status goes to COLLABORATING.
2. The owner re-ratifies, and ratifies or strikes the unilateral list (§4) in the same pass.
3. This gate re-checks the changed contracts and answers `PASS`. Then the implementation-planner
   starts.
