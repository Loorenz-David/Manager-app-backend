---
plan: (pre-plan, project-level — no master plan and no phase plans exist yet)
role: reviewer (mechanism-inventory gate)
round: inventory
date: 2026-09-18
project: stock_report
---

# Session prompt — mechanism-inventory gate, `stock_report`

## 1. Role and workspace

You are running the **mechanism-inventory** gate. You are adversarial to the intention's author:
treat every mechanism description as hiding an ambiguity an implementer will resolve silently in
code. This feature is **denormalized counters, a state derived from another aggregate's state, an
identity hash over externally-owned JSON, a dense ordering, and a mirrored matcher from another
codebase** — every one of them produces a plausible number or a plausible row when it is wrong.
Almost nothing here fails loudly.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (tooling runs from here: `make test` = `PYTHONPATH=. pytest -m 'not e2e'`,
xdist `-n 6 --dist loadfile`, one isolated database per process)
Project folder: `backend/docs/architecture/under_construction/implementation/stock_report/`
Upstream repository (read-only, never modified by this project):
`/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/Item-Scanner-Shopify` (`apps/backend`)

**Read these two files first and follow them as this session's doctrine** (absolute paths):

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/mechanism-inventory.md`

If you are a Claude session, invoking the `mechanism-inventory` skill loads (2); read (1)
regardless.

## 2. Gate check — stop and report if any of these is false

- `planning/intention.md` status header reads **`RATIFIED`** and its §18 carries both a
  "Ratification" and a "Re-ratification" entry dated 2026-09-18.
- `planning/scanner_source_evidence.md` exists (E1–E10 + the sender contract notes).
- The project folder contains **no** `master_plan.md` and **no** `plans/` directory. This gate
  runs before the implementation-planner by design; if either exists, stop — someone planned early.
- `git status --porcelain` shows the intention committed (a dirty intention is not a stable
  authority to write contracts into — report it and stop).

## 3. Read order

1. `planning/intention.md` — **in full, and §14B last but with the most weight**: it is a ratified
   amendment that **wins over every earlier section it contradicts** (row identity, no-op actions,
   item deletion, category guard, concurrent writers). §14A is the question list §14B answers;
   read them as a pair. §16 lists every shaper proposal (P1–P32, two struck) — all ratified.
2. `planning/scanner_source_evidence.md` — then **open the Scanner files it cites** and check each
   claim at source. It was written by the same author as the intention.
3. Manager source the intention grounds itself on — read, not assumed:
   - task state writers, all of them (intention §2.3 table):
     `app/beyo_manager/services/commands/tasks/_task_state_transitions.py`,
     `resolve_task.py`, `fail_task.py`, `cancel_task.py`, `force_task_ready.py`, `create_task.py`,
     `delete_task.py`, `add_item_to_task.py`, `remove_item_from_task.py`;
     `app/beyo_manager/services/commands/task_steps/transition_step_state.py`,
     `_step_transition_core.py`, `transition_step_state_batch.py`, `add_task_steps.py`,
     `remove_task_step.py`; `app/beyo_manager/services/tasks/task_steps/finalize_pending_step_completion.py`
   - `app/beyo_manager/domain/tasks/enums.py`, `app/beyo_manager/domain/task_steps/constants.py`
   - `app/beyo_manager/models/tables/tasks/task.py`, `task_item.py`;
     `app/beyo_manager/models/tables/items/item.py`, `item_category.py`
   - `app/beyo_manager/domain/items/properties_signature.py`
   - `app/beyo_manager/services/commands/items/update_item.py`, `delete_item.py` (§14B B4, B6)
   - counter and ordering precedents: `app/beyo_manager/services/commands/cases/message_writes.py`,
     `soft_delete_message.py`; `app/beyo_manager/services/commands/working_sections/set_user_working_sections_order.py`,
     `_membership_ordering.py`; `app/beyo_manager/models/tables/working_sections/working_section_membership.py`
   - webhook precedents: `app/beyo_manager/services/infra/connecteam/webhook_verifier.py`,
     `app/beyo_manager/routers/api_v1/connecteam_webhooks.py`, `app/beyo_manager/services/context.py`,
     `app/beyo_manager/config.py`
   - contracts: `architecture/06_commands_local.md`, `11_infra_events.md`, `24_multi_tenancy.md`,
     `25_soft_delete.md`, `32_concurrency.md`, `46_serialization_local.md`
4. Scanner source for the mirrored matcher:
   `apps/backend/src/modules/stock/domain/property-criteria.ts`, `best-match.ts`
   (`deriveItemProperties`), `apps/backend/src/shared/item-properties/wood-groups.ts`,
   `drawer-ranges.ts`, `item-property-options.ts`, `item-properties.ts`;
   `apps/backend/prisma/schema.prisma` (`LocationStock`); `src/workers/outbound-webhook-worker.ts`.
5. `.archgraph/` via the archgraph MCP — orient with `archgraph_status` and a search around the
   task-transition branch (`helper-task-state-transitions`, `decision-mirrored-transition-body`,
   `command-transition-step-state`). No Stock Report nodes exist yet. **You never promote, reject
   or edit review items.** Record in your handoff what you would have recorded.

## 4. What this gate must produce

Every mechanism below leaves this gate with a **contract-grade definition written into the
intention itself** (lettered sections), or with an owner decision card explaining why it cannot be
defined without one. Contract-grade per the skill: inputs and every type they may arrive as
(what the ORM / Pydantic / JSON decoder actually returns, not what a test would build); per-type
canonicalization; per-field order/case/precision semantics; the invariant a test must prove on
the production code path; and its registration against the measurement ledger (M1–M9) so planner
criteria have a trace target.

### The mechanisms in scope — all of them

| # | Mechanism | Where | Ledger |
|---|---|---|---|
| MI-1 | **Transition operation + unit counters.** The one operation that moves an assignment A→B and the counters by the stored `quantity`. Allowed-move set as a total table (5 states × 5 states + create + delete); what "atomic" is made of (row lock vs conditional atomic UPDATE vs both, and on which row first — lock order across StockReportItem / assignment / Task); what the `>= 0` check does on violation; whether `func.greatest(…, 0)` flooring is allowed at all, since a floor **hides** drift that M1 exists to detect | HC-2, HC-2a, HC-3, §5.5 | M1 |
| MI-2 | **Task-state sync.** The §5 mapping is total over 8 states — verify against the enum. For **each** of the write sites in §2.3: is a session in scope, is it sync or async (`maybe_advance_task_to_working` is a plain `def` with no session), which transaction owns it, how pending events get back to the dispatching command. Then the guard of §5 rule 4: define the instrument that fails when a new `Task.state` writer appears without sync, **and the planted defect that proves it can fail** (charter rule 15). Verify the site list is complete — by a search whose scope and term set you record (assignment, `setattr`, bulk `update(Task)`, constructor) | §2.3, §5, HC-4 | M2 |
| MI-3 | **Row identity.** §14B B1 normalization: exact algorithm per value type, as the JSON decoder delivers them (str, list, None, int, float, bool, dict, nested/mixed list, empty list, empty string, whitespace-only, duplicates differing by case, non-ASCII, keys differing by case or whitespace — are **keys** normalized?). Relationship to Scanner's `normalizeCriteria` (which throws on an empty list — Manager's P30 says never reject: reconcile). Whether the normalized form or the received form is what `properties` stores and what the GET returns. A version constant if the algorithm may change. Find-or-create under two concurrent first deliveries (partial unique index predicate; insert-conflict handling) | §4.1, §14B B1, P30 | M4 |
| MI-4 | **One active assignment per item.** Partial unique index predicate exactly (states, `is_deleted`), its behaviour when a terminal assignment is followed by a new one, and the error surfaced on the race the index guards (charter rule 2: the error contract is tested on the race path, not the pre-check) | §4.2 | M4 |
| MI-5 | **Goal-record running total.** §6.2 as a total event table: every exit from and entry to `awaiting` × {credited record exists, none, credited record soft-deleted, goal record changed since credit}. Floor-at-0 again: legitimate or drift-hiding? Reconcile the §10 recomputation sentence for this field against §6.2 by doing the arithmetic on a sequence (credit → demand increase → reopen → re-finish → Scanner resolve → row delete) | §6, §10, P26 | M5 |
| MI-6 | **History write rules.** "Greater than the previous one" — previous **stored** value, including 5→3→4; creation at 0; what each record snapshots and **when** in the transaction; one record for priority change; none for shifted neighbours; none on a no-op (§14B B2) | §6.1 | M5 |
| MI-7 | **Dense ordering.** Group = (workspace, priority) over non-deleted rows. Gap closing, append at max+1, single-item move, delete — each as a before/after table. Concurrent operations in one group (two moves; a move racing a priority change; a delete racing a move) — what serializes them. 1-based; target bounds; null ⇔ null | §7 | M6 |
| MI-8 | **Webhook boundary.** Validation order (auth → configuration → shape → duplicates → references → writes) and what each failure returns; constant-time compare; both settings and every absent/invalid combination; the split between "malformed rejects all" and "unknown category skips one" as a total table over entry defects; response envelope per entry; `ctx.workspace_id` is `""` on this path and must never be read — how the workspace reaches commands that read it from `ctx` | §8, §2.5, P27 | M3, M7 |
| MI-9 | **Idempotency.** For each webhook: the exact sense in which a replay "changes nothing" — rows, history, authorship stamps, `updated_at`/`onupdate`, events. An `onupdate=` column defeats a naive no-op (see the comment in `models/tables/tasks/task.py` on `updated_at`) | HC-5, §8, §9B | M3 |
| MI-10 | **Processed webhook resolution.** article_number → item → active assignment: soft-deleted items, null article numbers, whitespace/case in the number as Scanner sends it (evidence E5/E6 and the live report show values like `04 2 001 0034`), and the per-entry outcome vocabulary as a closed enum | §8.2 | M3 |
| MI-11 | **Concurrent writers on one assignment.** §14B B5 fixes the semantics; you fix the mechanism and show both interleavings produce exactly the stated outcomes, including counters and the goal record | §14B B5, P32 | M1, M2 |
| MI-12 | **Criteria matcher mirror.** Do the match by hand for real rules in Scanner's `LC-STOCK-REPORT.md` against Manager-shaped items. Tokenizer, wildcard `null`, any-of, first-token wood group, drawer range parsing, relocated `quantity` key (criteria are **strings** like `"4"`; `Item.quantity` is an int — state the comparison), unknown-shape criterion (P30), item with `properties = NULL`, non-string item values (Manager stores values verbatim; Scanner's bag is string-only — what does a Manager int or list value do?). The mismatch reason vocabulary as a closed enum. **Charter rule 17 binds here**: every fixture shape owned by Scanner is grounded at `file:symbol`, never plausible | §9A, E7–E10 | M8 |
| MI-13 | **Assignment creation checks + override.** Order of checks, which are per-entry vs per-batch, what the dedicated error carries, flag semantics on matching entries, duplicates inside one batch (same item twice; same task twice) | §9A, P23 | M8 |
| MI-14 | **Task-side and item-side removals.** `delete_task`, `remove_item_from_task`, `delete_item` hooks (B4) and the `update_item` category guard (B6): transaction ownership, what "active" means for the guard, events | §5.6, §14B B4/B6, P25, P31 | M2, M8 |
| MI-15 | **`Task.is_stock_assignment`.** Exact truth condition; recomputation on every assignment create/delete/row-delete; interaction with the task's `updated_at` `onupdate` (does flipping the flag bump the task's `updated_at` and reorder task lists?) | §4.4, §14B B3 | M1 |
| MI-16 | **Soft-delete interplay.** Every uniqueness, counter, ordering, history and lookup rule restated with its deleted-row predicate; row delete cascade order so counters never go negative mid-transaction | §4, §9, P2 | M1, M4, M6 |
| MI-17 | **Authorship.** §4.5 as a table of (operation × table × column) → value, including who is recorded when a **worker's step transition** moves an assignment, and `updated_at` behaviour when only system fields move | §4.5, P29 | M9 |
| MI-18 | **Roles.** §9 matrix as enumerated (operation × role) cells; where the refusal happens | §9 | M9 |
| MI-19 | **Event emission.** §9B: exact trigger set per event, payload fields and types, "no event on no-op" made decidable, one-per-shifted-row, pending-events hand-up through every task-state command in MI-2 | §9B, P28, §14 item 8 | mechanism contract (not in the ledger — register it) |
| MI-20 | **Consistency check.** What it recomputes (counters, flag, ordering density, null⇔null, goal totals?), its output shape, and that it is read-only. It is the instrument for M1 — prove the instrument can observe a planted drift | §12 item 8, P20 | M1 |

**Do not scope yourself by this table or by the intention's §14.** Both were written by the
mechanisms' author. In this lineage the defects worth a round have repeatedly sat in sections
nobody flagged. Sweep the prose sections — §3, §10, §11, §12, Appendix A — at the same depth.

### Method rules for this sweep

1. **Contradiction hunt between §1–§13 and §14B.** The amendment was appended, not woven in. List
   every earlier sentence §14B supersedes (known: §2.2 "list order is significant" vs B1; §8.1
   "must be a JSON object" vs P30; §9A "checked once, at creation" vs B6). For each, say which
   side ships. One was already found post-ratification (§10) — assume there are more.
2. **Charter rule 5 — no adjectives.** "Atomic", "safe under concurrent deliveries", "serialized",
   "cheap skip", "reusable", "verbatim" are doing specification work. Each becomes a mechanism or a
   finding.
3. **Charter rule 2 — totality.** The §5 mapping, the allowed-move table, the webhook entry-defect
   table, the role matrix, the mismatch-reason and outcome vocabularies: each must be a complete
   enumeration with every cell decidable.
4. **Every named mutation: both sides computed, site named** (file, definition vs call site).
5. **Absence claims carry their scope and term set.** "No single integration point", "`stalled` is
   never written", "terminal tasks never reopen", "nothing else writes `Task.state`": state the
   search, run it, record it beside the claim.
6. **Two-codebase contracts.** The sender notes in `scanner_source_evidence.md` are executed by a
   different team in a different repo, and the frontend executes the override retry. Per rule:
   precise enough that the other side cannot misread it? That text ships in the closeout handoffs.
7. **The ledger holds nine entries against a 3–7 guideline**, by the owner's acceptance. Do not
   merge or renumber them. You may find an entry too weak to be a trace target — that is a finding.

## 5. Constraints

- **You write documents, never code.** Nothing under `app/` changes. Read-only queries and reading
  either repository are fine; no test runs are required.
- **The delta goes into `planning/intention.md`**, as lettered sections (`§5A`, `§8A`, `§9C` …).
  **Never renumber.** §14B is itself cited — do not fold it away. Citations are `path:symbol`.
- **Add a changelog entry** to §18 (round 6).
- **Material semantic change re-opens the gate**: if a contract you need changes product behaviour
  the owner ratified, set the header back to COLLABORATING, card it, and do not hand off.
- **Owner decisions** are decision cards in the charter's format, all together in ONE section
  `⚠ OWNER DECISIONS REQUIRED (n)` right after your handoff's opening summary; zero cards is said
  in one line. Cards are the only owner-facing prose in the handoff.
- **Unilateral resolutions are listed separately for ratification**, each with what the other side
  would have shipped.
- **Settled, do not reopen:** units not assignments; location-free identity; PRIMARY item only;
  category hard refusal + overridable property mismatch; history option C; unknown category
  skipped-and-reported; realtime events ship; repair mode deferred; the role matrix; the Shopify
  property gap as an accepted limit. A wrongly-folded *consequence* of one of these is a finding.

## 6. Closing protocol

1. Write the intention delta (lettered sections + §18 round-6 entry).
2. Deposit your report at
   `handoffs/reviewer/2026-09-18_inventory_mechanism_inventory_handoff.md` with charter
   frontmatter: `plan`, `role`, `round`, `date`, `state`/`verdict`, `actor`.
3. The handoff **declares your full write perimeter**, generated from `git status` /
   `git diff --name-only`, never from memory — documents, and any tool-recorded state.
4. Your final chat message follows the charter's owner layer: what I did → what I found and what
   it means for you → what happens next → what needs you (cards verbatim, or "nothing needs you").

## 7. Report back — what the handoff must contain

- Opening summary, then the owner-cards section (or its one-line "none").
- **Inventory table**: one row per MI-1…MI-20 plus any you added — *mechanism / silent-failure
  risk / contract status before / after / where the contract now lives / ledger ID*.
- **Contradiction list** (§1–§13 vs §14B and anything else), both sides quoted, side chosen, what
  the other would have shipped.
- **Matcher hand-walk**: per real Scanner rule tried, the item, the expected verdict, the
  arithmetic, and the `file:symbol` grounding each fixture shape.
- **Write-site audit**: the complete `Task.state` writer list with search scope and terms, and per
  site the sync hook's feasibility (session, transaction owner, event path).
- **Absence-claim ledger**: claim / search / scope / result.
- **What you could not settle from source**, with the evidence that would settle it.
- **Gate verdict**: `PASS` | `OWNER_DECISIONS_PENDING` | `FAIL`. The implementation-planner starts
  on nothing but `PASS`.
