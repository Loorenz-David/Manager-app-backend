---
plan: 4
role: review
round: 2
verdict: CHANGES_REQUESTED
date: 2026-08-19
actor: Opus 5 (re-review r2)
---

# Phase 4 re-review r2 — delta-scoped

**Verdict: CHANGES_REQUESTED.** 1 blocking, 4 should-fix, 3 notes.

**Seven of the ten r1 findings are closed outright.** S1's correction survived the strongest
probe this round could run — a wrapper-aware transitive import walk over all 82 modules
reachable from `services/queries/item_economics/` — and its replacement sentence is not merely
true but **complete**: the only two read-path clock reads in that family are exactly the two it
names. S2, S3, S4, N2 and N3 are clean. B1's substance is right: §5.2's four conditions and
§7.4's table both match intention §9.2A and the shipped code, row for row.

The three that are not closed all failed the same way, and it is the way a *correction* fails
rather than the way a draft does: **each fix was applied where r1 pointed, and not where the
same defect also lived.** B2 annotated §2 and left §3 — the table a developer actually builds
the render from — untouched, still dereferencing `saved.created_by.username` on the one payload
where `saved` is `null`. That is the single blocking finding, and it is also the concrete answer
to this prompt's §3 question.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner. Every finding is a text correction the coordinator owns; no ratified
decision is touched.

---

## Disposition of every r1 finding

| r1 | Status | |
|---|---|---|
| **B1** — block rule stated over `status` alone | **CLOSED (substance)** | §5.2's four conditions and the new §7.4 both verified against §9.2A and the code. Placement is a new finding (R5). |
| **B2** — four undocumented nullabilities | **NOT CLOSED** | The four are annotated correctly. A **fifth** exists, and §2's new summary line asserts a closed set that excludes it (R2). §3 was never updated (R1). |
| **B3** — fingerprint's staleness boundary | **PARTIALLY CLOSED** | The boundary statement is correct and complete. The refetch instruction it ends with is under-scoped and names an event with no live documentation (R4). |
| **S1** — false absence claim | **CLOSED** | Verified exhaustively; see below. The visible retraction in §6 is the right form. |
| **S2** — the `n` conflation | **CLOSED** | Now gives both figures with their own `n`: 1 öre ⇒ 0.046 s, 1.5 öre ⇒ 0.07 s. Matches intention §3.2A exactly. |
| **S3** — §8.1's over-broad deduction claim | **CLOSED** | "it subtracts one thing this screen does not: `charged_seconds` … Time worked on ordinary steps is subtracted by neither" — correct against `budget_division.py:308-315` and `EXCLUDED_STEP_STATES` `:19-25`. |
| **S4** — "inert" | **CLOSED** | Now states the tie rule never fires *and* that the rounding still must be called, with the `−1n → −1n / 0n` counterexample. |
| **N1** — `max(1, quantity)` | **CLOSED in §5.4, CONTRADICTED in §3** | §5.4 now reads `max(1, quantity)` with a pointer to §8.2. §3 still divides by `quantity` in three rows (folded into R1). |
| **N2** — the search-cap case | **CLOSED** | "or when no representable price funds it … your handling is the same in all three cases." |
| **N3** — `can_commit`'s conservative direction | **CLOSED, but the expansion introduced R3** | The two new paragraphs say what N3 meant and no more — the direction is stated correctly ("conservative rather than wrong"). The expansion sits three paragraphs below a sentence it contradicts (R3). |

---

## Findings

### BLOCKING

#### R1 — §3, the render blueprint, was never touched, and now contradicts three of the ten corrections

**Where.** §3 *What the screen renders, key by key* — the one table a developer builds the
screen from, unchanged since r1.

| Row | What it says | What the corrections established |
|---|---|---|
| `Marta Lind · saved version · 14 Aug, 10:24` | `saved.created_by.username`, `saved.created_at` | **`saved` is `null`** on the unpriced item (§2's new annotation) and on every non-`bound` binding (§7.4). `created_by` is independently nullable. Two levels of null, no mark. |
| `1 425 SEK` per piece | draft price ÷ `item.quantity` | N1 corrected §5.4 to **`max(1, quantity)`**. `item` is also `null` on `detached` (§7.4). |
| `× 6 pieces · 8 550 SEK total` | `item.quantity` | idem |
| `suggested 2 025/piece` | `anchors.suggested_price_minor ÷ quantity` | idem |
| slider ends `700` / **`2 700`** | `domain.min_minor` / `max_minor` ÷ quantity — but read §5.4 | §5.4 says the top end **is `2 750`**, ratified as D10. The table prints the number the document elsewhere calls wrong. |

**This is the answer to the prompt's §3 question, and it is a yes.** "Treat `model === null` as
the switch" is sufficient for the four blocks and **not** for `saved`, `currency` or `item`,
which vary independently — §2's summary line says so outright ("a brand-new item's first render
is `saved: null`, `currency: null` and a fully populated `model`"). A developer who takes the
single switch, passes it, and then builds the byline row from §3 dereferences
`saved.created_by.username` where `saved` is `null`. **That is the screen's very first render
for a brand-new item — the case §5.2 exists to celebrate.**

B2's annotations are correct and land in §2. They never reach §3, which is where the render is
specified, and a developer reading §3 has no reason to go back.

**Proposed replacement** — §3's table, plus one sentence above it (verbatim):

> **`model === null` gates the four numeric blocks and nothing else.** `saved`, `currency` and
> `item` are independently nullable — a brand-new item renders with a full `model` and none of
> the three. Every row below marked ⚠ needs its own null check.

| On screen | From |
|---|---|
| `1 425 SEK` per piece | draft price ÷ `max(1, item.quantity)`, your side — ⚠ `item` is `null` on `detached` |
| `× 6 pieces · 8 550 SEK total` | `max(1, item.quantity)`, draft price — ⚠ as above |
| `AT PRICE 2h 25m` | `allowance_seconds(P)` — §4 — ⚠ needs `model`, so gate on `model !== null` |
| `TYPICAL 3h 25m` | `typical.total_seconds` — always present |
| chip `Below typical work` | draft price vs `anchors.break_even_price_minor` — §5.3 — ⚠ `anchors` null with `model`; the member is independently nullable |
| `suggested 2 025/piece` | `anchors.suggested_price_minor ÷ max(1, quantity)` — ⚠ as above |
| slider ends `700` / `2 750` | `domain.min_minor` / `max_minor` ÷ `max(1, quantity)` — ⚠ `domain` null with `model`; **and note `2 750`, not the mockup's `2 700` — see §5.4** |
| `Marta Lind · saved version · 14 Aug, 10:24` | `saved.created_by.username`, `saved.created_at` — ⚠⚠ **`saved` is `null` for an item nobody has priced and on any non-`bound` binding; `created_by` is separately nullable. Two checks, not one.** |

Also update **Frontend action required item 6**, which currently says only "Handle
`model: null`":

> 6. **Handle `model: null` *and* `saved: null` — they are different absences.** `model: null`
>    means no slider and no numbers (§5.2). `saved: null` means nobody has priced this item
>    yet, and it arrives **with a full `model`** — that is the screen's main use case, not an
>    error state (§2, §3).

---

### SHOULD-FIX

#### R2 — there is a fifth undocumented nullability, and §2's new summary line asserts a closed set that excludes it

**Where.** §2's added line:

> **Every `…_minor` field, `currency` and both `item` string fields are nullable.**

I re-walked the serializer field by field as the probe asked, including the four the prompt
named. `purchase_cost_minor` is self-documenting (the example shows `null`), `created_by` is
annotated, `anchors`' members are covered by the block comment plus §5.3, and `domain`'s members
are non-null whenever the block is. **One field is nullable, undocumented, and excluded by the
summary line's own enumeration:**

`saved.created_by.profile_picture` — `String(512) NULL` (`models/tables/users/user.py:35`), and
intention §6B states it explicitly: *"`profile_picture` is `String(512) NULL` and travels as
`null`, not as an empty string."* §2 shows `"profile_picture": "https://…"` unannotated.

A closed-set sentence that is wrong is worse than an omission: it tells a reader to stop
looking. **The set is otherwise complete** — this is the last one.

**Proposed replacement** (verbatim):

```jsonc
    "created_by": {                  // null only if the user row cannot be loaded
      "client_id": "usr_…",
      "username": "Marta Lind",
      "profile_picture": "https://…"   // nullable — null, never an empty string
    }
```

> **Nullable: `currency`, `config_fingerprint`, `item` and both its string fields, `saved` and
> every one of its members except `valuation_id` and `created_at`, `profile_picture`, all four
> numeric blocks, and `break_even_price_minor` / `suggested_price_minor` within `anchors`.**
> Non-null on every response: `task_id`, `status`, `item_binding`, `can_commit`,
> `calculation_version`, `typical` and all seven of its members, and
> `anchors.is_fundable` / `anchors.infeasible_at_or_below_minor` when `anchors` is present.

---

#### R3 — §6.1 says `can_commit` and the `model` block "always move together" and, three paragraphs later, that they are "unrelated"

**Where.** §6.1, two sentences that cannot both be true:

> **The same split governs the `model` block** (§5.2 item 3); the two always move together.

> **`can_commit` is unrelated to whether the blocks are present.** Under
> `item_binding: "mismatched"` it can read `true` with no model on screen …

The second is right. The first is r1's own wording, and it is wrong as a general claim: the two
predicates share `selection_ready` and `currency_agrees` but nothing else. `can_commit` also
requires a valuation row and an admitted task state; the blocks also require `item_binding ==
"bound"` and a collapsing model. **`item_unvalued` is the counterexample and it is the flagship
case** — reproduced in r1: `model` fully populated, `can_commit: false`. `mismatched` is the
inverse, as §6.1's own second sentence says.

The same phrase appears in §5.2 item 3, where nothing corrects it.

**Proposed replacement** — in §6.1, replace the first sentence with:

> **The same live/displayed split governs the `model` block** (§5.2 item 3): both are computed
> from the live configuration, so an expired cost model version empties the blocks and turns
> `can_commit` false together. **That shared cause is the only thing they share** — see the two
> paragraphs below.

and in §5.2 item 3, replace *"and the two always move together"* with:

> — an expired cost model version empties these blocks and turns `can_commit` false at the same
> time. Beyond that shared cause the two are independent (§6.1).

---

#### R4 — the refetch instruction is scoped to "this task", but the mechanism it defends against is workspace-wide, and one of its two events appears in no live handoff

**Where.** §6.3's closing instruction:

> **So: refetch the scenario on item-changed and step-transition events for this task**, not
> only on a fingerprint mismatch. The screen is short-lived, so in practice this is one refetch
> on the events you already receive …

Three problems, all in one sentence, and it is r1's own text:

1. **"for this task" under-covers the mechanism the paragraph just described.** The same
   paragraph correctly says the typical "moves when *any* task in the workspace completes a
   step". Filtering step transitions to this task therefore misses most of the moves. The events
   are workspace broadcasts (`build_workspace_event`), so no filter is needed — dropping the
   scope is the fix, not adding a subscription.
2. **Neither event is named**, in a document that names every other identifier it asks the
   client to act on.
3. **"the events you already receive" is verified for one half and not the other.**
   `task:step-state-changed` is real (`services/infra/events/worker_shift_realtime.py:41`) and
   named in **four** live frontend handoffs. The item half is `item:updated`
   (`services/commands/items/update_item.py:116`, and several other item commands) — it exists
   and is broadcast, but **it appears in no live handoff**; the only documents naming it are two
   under `docs/handoff/to_frontend/archived/`. Asserting they "already receive" an event we have
   never published to them is the assumption class this project has been burned by.

**Proposed replacement** (verbatim):

> **So: refetch the scenario on `task:step-state-changed` for *any* task in the workspace, and
> on `item:updated` for this item** — not only on a fingerprint mismatch. Both are workspace
> broadcasts you already have a socket for; do not filter the step event to this task, because
> the typical is a workspace-wide median and any task's step transition can move it.
> `item:updated` is emitted on item edits (quantity, category) and, to our knowledge, has not
> been named in a handoff to you before — if your client does not handle it yet, this is the
> screen that needs it. The window also slides with time alone, which no event covers; a screen
> left open for a long session should refetch on reopen regardless.

---

#### R5 — §7.4 sits inside "Amendments to [another document]" and orphans the apology paragraph

**Where.** §7 opens *"That file is not edited. **These three amendments** live here and supersede
it by reference"*, then lists items 1–3, then `### 7.4 The payload when item_binding is not
"bound"`, and only then:

> **On the last one, an apology and a process change.** §9.1 was corrected by editing the
> 2026-08-15 file **in place** …

"The last one" means amendment 3. It is now separated from its referent by a section heading, a
six-row table and three paragraphs, and the text immediately above it is *"Both states mean the
task lost or swapped its primary item."* A reader meeting "On the last one" there attaches the
apology to §7.4.

Two further consequences of the same placement:

- **§7.4 is not an amendment to the 2026-08-15 handoff.** It is this endpoint's own payload
  contract (intention §9.2A). §5.2 item 1 and §6.1 both send readers to "(§7.4.)", and they land
  under a header saying everything below supersedes a different, older document.
- §7's parts are a numbered list (`1.` `2.` `3.`) with no `§7.1`–`§7.3` headings, so a
  subsection numbered `7.4` reads as a fourth amendment.

**Proposed correction.** Move the §7.4 block **out of §7 entirely** and place it as **§5.5, "The
payload when `item_binding` is not `bound`"**, immediately after §5.4 — inside "The blocks, and
when they are null", which is what it is about and where §5.2 item 1's reader is already
standing. Retarget the three cross-references (§5.2 item 1, §6.1's third paragraph, §7.4's own
closing line) to §5.5. Restore the apology paragraph to its position directly beneath amendment
3. No wording inside the block changes — its table is correct (verified below).

---

### NOTES

**R6 — §7 item 3's guard sentence names a check that does not cover this document.** It says
*"A backend guard asserts that no live document names an unregistered error identity."* That is
`test_no_document_names_an_unregistered_error_identity`
(`tests/unit/docs/test_item_economics_handoff_accuracy.py:190`), parametrized over exactly four
documents — the configuration handoff, the operational handoff, and two domain docs. **Neither
phase-4 handoff is among them.** The guard that actually forced the omission is
`test_retired_inline_refusal_identity_is_absent_from_live_sources` (`:220`), which sweeps every
`.md` under `docs/handoff/` for that one retired string. Suggested: *"A backend guard sweeps
every live document for retired error identities, so that nobody codes against an error that can
no longer occur."*

**R7 — a dangling reference created by the B1 fix.** §7 amendment 1 still reads "(subject to
§5.2's **collapsibility qualification**)". The paragraph carrying that name was deleted as
instructed and its content is now §5.2 item 4. Suggested: "(subject to §5.2 item 4 — the model
must collapse)".

**R8 — neither phase-4 handoff is registered with the accuracy arbiter that exists for exactly
these documents.** `tests/unit/docs/test_item_economics_handoff_accuracy.py` is a hand-written
arbiter for routes, error identities, status values and envelope keys, and its docstring calls
itself "the accuracy arbiter for the two frontend handoffs". It covers `_OPERATIONAL` and
`_CONFIGURATION`. **Of the 59 tests in `tests/unit/docs/`, exactly one reads either phase-4
document, and it only asserts one string's absence.** So "59 passed" is close to silent about
these two files — which is consistent with r1 finding five nullability defects in a document
that was green. Not a defect in the documents; routed as a lesson below.

---

## What I verified correct this round

### S1's replacement — probed as instructed, wrappers not literals

I did not grep for `datetime.now`. I walked the **transitive import graph** from every file in
`services/queries/item_economics/` (82 modules reached) and matched every clock primitive:
`datetime.now`, `datetime.utcnow`, `date.today`, `func.now`, `func.current_date`,
`func.current_timestamp`, `time.time()`. 41 raw hits. Classified:

| Class | Count | On a read path? |
|---|---|---|
| ORM column `default=` / `onupdate=` lambdas | 30 | **No** — INSERT/UPDATE only |
| Write-side helpers (`write_audit`, `audit_handler`, `_create_history_record_in_session`, `task_factory`, `commit_item_cost_evaluation.py:270`, `_common.py:129`, `connection_meta`) | 9 | **No** |
| **`_common.py:48` `today_utc()`** — version applicability, reached by `_load_preview_inputs:203` and directly at `get_economics_configuration_status.py:38` and `get_task_budget_allocations.py:188` | 1 | **Yes** |
| **`get_working_section_typical_times.py:23`** — the 90-day window cutoff | 1 | **Yes** |

**Exactly two read-path clock reads, and the correction names exactly those two:** *"version
applicability and the typical's 90-day window both read the clock."* The sentence is true **and
complete**. §6's visible retraction names the failed search honestly ("matched the literals
`datetime.now` and `func.now` and missed the wrapper") and correctly states the verdict is
unaffected. **S1 closed.**

### §7.4's table — every row against §9.2A and the code

| Row | §9.2A | Code | |
|---|---|---|---|
| `item`: `null` on `detached`, populated on `mismatched` | matches | `detached` ⟺ `item is None` (`get_task_budget_status.py:111`) | ✓ |
| `saved`, `currency` `null` on both | matches | `:238-240`, then `currency` derives from `valuation` (`:259`) | ✓ |
| `model`, `anchors`, `domain`, `config_fingerprint` `null` on both | matches | `:238-243`, `:247-252` | ✓ |
| `typical` populated on both | matches | computed before the binding branch (`:154`), never nulled | ✓ |
| `status` "always `ok` or `infeasible`" on `mismatched` | matches | `mismatched` requires `evaluation is not None`, so `_build_evaluated_status` always runs (`:111`, `:150`) | ✓ |
| `can_commit` `false` on `detached`, "as resolved — may be `true`" on `mismatched` | matches | verified twice — see below | ✓ |

**The `can_commit` row was re-verified against plan 3's pending change, which touches this
exact line.** Plan 3's uncommitted diff deletes `if budget_status.item_binding == "detached":
can_commit = False` (`:244-245`). That branch is dead: `detached` ⟺ `item is None`, and
`can_commit` already requires `item is not None` (`:185`). **§7.4's `detached → false` guarantee
therefore survives the deletion**, and `test_c9_non_bound_binding_governs_the_full_payload`
still passes on the current working tree. Stated explicitly because a reader of §7.4 could
otherwise think its guarantee was just removed.

### §7 amendment 3's new factual claims — none of which r1 reviewed

Commit `cf034fe` rewrote this amendment out-of-band (a docs guard broke a parallel session's
baseline). It added four claims about the inline re-pricing contract. All four verified against
`services/commands/tasks/create_task.py:315-364`:

| Claim | Code | |
|---|---|---|
| "no longer fails" | no refusal branch remains | ✓ |
| "a new valuation version credited to whoever created the task" | `created_by_id=ctx.user_id` (`:363`) | ✓ |
| "**nothing written at all** when they match" | `should_write_valuation` is a triple inequality (`:347-355`); false ⇒ no chain write, no audit row | ✓ |
| "a field you omit keeps its current value rather than being nulled" | `request.item.X if … is not None else current_valuation.X` (`:337-346`) | ✓ |
| "a currency change counts as a difference" | `request.item.currency` is in the compared triple (`:350`, `:354`) | ✓ |

Correctly scoped, too: the inherit/no-op path is guarded by `if not item_was_created` and a
non-null current valuation, and the amendment's own sentence says "an item that already has a
valuation." The instruction "search your own codebase for the identity" is workable — the
frontend holds the 2026-08-15 handoff that named it. Only the *guard* sentence is inaccurate
(R6).

### S2, S3, S4, N1, N2, N3 — each re-derived, not read

- **S2** now matches intention §3.2A term for term: `n` defined as percentage terms, 1 öre ⇒
  0.046 s, 1.5 öre ⇒ 0.07 s. Recomputed: `60/1300 = 0.0462`, `1.5 × 0.0462 = 0.069`. ✓
- **S3** matches `distributable_seconds = max(0, budget_seconds − charged_seconds)`
  (`budget_division.py:314-315`) with `charged_seconds` over excluded steps only (`:308`,
  `EXCLUDED_STEP_STATES` `:19-25`), and the new "subtracted by neither" clause is right. ✓
- **S4**'s counterexample checked: `allowed_centimin = −1n` ⇒ `round_half_even(−3, 5) = −1`
  (`divmod(−3,5) = (−1,2)`, `2·2 = 4 < 5`), BigInt `−3n/5n = 0n`. The document's `−1n → −1n`
  half-even / `0n` truncated is exactly right. ✓
- **N1** §5.4 now reads `max(1, quantity)` and cites §8.2 — matching `divisor = max(1, quantity)`
  (`price_scenario.py:193`) and intention §7A.1's `Q`. ✓ (§3 is R1.)
- **N2** the search-cap third case is `_least_price_for_seconds` returning `None` above
  `SEARCH_CAP_MINOR` (`:126-129`), and "your handling is the same in all three cases" is
  correct — all three yield `is_fundable: false`. ✓
- **N3**'s expansion says what N3 meant and no more: it states the direction ("conservative
  rather than wrong"), the reason ("a GET cannot" know the price), and the trigger (Save
  extended to send a purchase cost). It does not overclaim. ✓ (Its neighbour is R3.)

### §5.2's four conditions

Re-derived against `get_task_price_scenario.py:196-207`. Condition 1 = `binding_is_bound`,
2 = `budget_status.status in _MODEL_STATUSES` (the five at `:52-60`), 3 = `selection_ready and
currency_agrees` (`:168-183`), 4 = `collapsed is not None` (`:207`). **Four in the prose, four in
the code, in the same order, none missing.** Item 3's worked example ("reports `ok` after its
cost model version expires — with every block `null`") is the case r1 reproduced. The deleted
"One qualification" paragraph is fully absorbed into item 4. ✓

### Perimeter

`git log --name-status bb63372..HEAD`: three commits, **documentation only**. `cf034fe` and
`9a9c4ed` touch the two handoffs, the master plan, plan 4 and prompt/handoff rows; `b181abc`
adds this round's prompt. **No application file was changed by phase 4 in either round.** The
one `M` under `docs/handoff/` outside r1's finding set is `cf034fe`, reviewed above.

**Not mine, and declared:** the working tree carries plan 3's in-flight edits to
`get_task_price_scenario.py` and `test_price_scenario_query.py`. Running that test file whole on
the current tree gives **48 passed / 1 failed** — the failure is plan 3's own new
`test_phase3_c2_deleted_purchase_term_is_ignored_by_admission_and_model`, red in an unfinished
session. Every phase-2 test in the file, including `test_c9`, passes. `tests/unit/docs/`: **59
passed**, matching the prompt.

---

## Mutation-probe declaration

**No file in the repository was modified by this session.** No probe was applied, so none needed
reverting. Verification was by reading, by a static import-graph walk run from an out-of-tree
script, and by running two existing test targets read-only. No database write occurred and no
state needed restoring.

**Full write perimeter — one file:**

- `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/reviewer/2026-08-19_phase4_rereview_r2_handoff.md` (this file)

**I wrote no handoff to the frontend, no application file, no plan and no tracker row.** Every
correction above is a finding with proposed text.

---

## Lessons for the plans

1. **A fix prompt must name every site of the defect, not the site the finding quoted.** All
   three unclosed findings failed identically: the correction landed exactly where r1 pointed and
   nowhere else. B2 said "§2's payload block" and §2 was fixed; §3 renders from the same payload
   and still crashes on it. N1 said "§5.4" and §5.4 was fixed; §3 divides by `quantity` three
   more times. **Standing consequence: when a finding is about a field, the fix perimeter is
   every section that names that field** — a `grep` for the field name, run before the fix is
   called done, would have caught both.

2. **A closed-set sentence needs its own verification step.** §2's summary line ("Every `…_minor`
   field, `currency` and both `item` string fields are nullable") was added *by* the B2 fix and is
   the only new sentence in the document that can be falsified by a single counterexample —
   which it has (R2). Enumerations are already this project's named failure cluster; an
   enumeration **written by a correction** inherits the same risk and gets no scrutiny because it
   arrives labelled as the fix.

3. **A document that ships into a guarded folder should be registered with its guard in the same
   phase.** `test_item_economics_handoff_accuracy.py` is precisely the mechanism that would have
   caught r1's B2 and this round's R2 — it exists, it is hand-written against the shipped
   surface, and it covers the two 2026-08-15 handoffs. Phase 4 shipped the most arithmetic-dense
   handoff this project has produced into the same folder and outside that arbiter. **A closeout
   phase's file table should carry the guard registration as a row**, and its criteria should
   include "the new document is under the accuracy arbiter" — otherwise "the docs guards are
   green" reports on documents other than the one being reviewed (R8).

4. **Reviewer-authored replacement text is not pre-verified text.** Three of this round's five
   findings (R1's `2 700` row aside) are defects *in r1's own proposed wording*: "the two always
   move together" (R3) is false, and the refetch instruction (R4) under-covers the mechanism r1
   itself had just described one paragraph earlier. Verbatim application is the right protocol —
   it is what made this round cheap — but it means **the reviewer's prose enters the document
   with no second reader**, exactly the exposure the r1 prompt identified for coordinator-authored
   handoffs. A re-review must attack the replacement text as adversarially as the original, and
   this prompt's §2 was right to send the round there.

5. **The out-of-band commit is the one this round nearly missed.** `cf034fe` changed the document
   under review for a reason unrelated to any finding, and added five factual claims about a
   *different* pipeline's contract. It was legible only from `git log --name-status`, not from the
   fix prompt's finding list. **The re-review prompt's "what changed" section should be generated
   from the commit range, not from the findings** — the two are not the same set, and the
   difference is where an unreviewed claim hides.
