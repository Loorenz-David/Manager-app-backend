---
plan: 4
role: review
round: 3
verdict: CHANGES_REQUESTED
date: 2026-08-19
actor: Opus 5 (re-review r3)
---

# Phase 4 re-review r3 — delta-scoped, narrow

**Verdict: CHANGES_REQUESTED.** 0 blocking, 3 should-fix, 3 notes.

**All seven r2 findings are closed, and P1 passes cleanly.** The grep-first discipline worked:
I re-grepped the document independently for every corrected field and found **no second site
missed** — no surviving `§7.4` reference, no surviving "always move together", every division
now `max(1, quantity)` at all four sites, the only `saved.`/`created_by.` chain in the document
is the byline row and it carries the ⚠⚠ marker, and every remaining `2 700` is a deliberate
contrast against `2 750`. That is the first round of this review where a correction did not
leak.

**P2 is where the round paid.** Attacking r2's own replacement text as instructed produced two
findings, and one of them is a **confirmed false statement that predates r2** and that neither
r1 nor r2 caught: `domain` is *not* published with `model` — it is `null` whenever there is no
usable band, which §5.4 says correctly two subsections after §5.2 says the opposite. I
reproduced it against the shipped service. The other is the operational cost of r2's own
refetch correction, which the prompt suspected and which is real.

**P4 also paid**, on its first end-to-end read since r1: the action list promises "a known end
date" for something §4 says explicitly has **no date**.

This is one edit pass from done. Nothing here reopens a decision, a mechanism or a verified
claim, and no finding requires more than replacing a sentence.

## ⚠ OWNER DECISIONS REQUIRED (0)

Nothing needs the owner.

---

## Disposition of every r2 finding

| r2 | Status | |
|---|---|---|
| **R1** (blocking) — §3 never touched | **CLOSED** | Table rebuilt, gating sentence added, `max(1, quantity)` in four rows, `2 750` replacing `2 700`, byline carries a two-check warning, action item 6 names both absences. One ⚠ marker in the new table is wrong → **F1**. |
| **R2** — fifth nullability, closed-set line | **CLOSED** | `profile_picture` annotated ("null, never an empty string"). The closed set replaced with a two-direction enumeration; `config_fingerprint` correctly nullable, `anchors.is_fundable` correctly conditioned on `anchors` being present. Incomplete but not wrong → note **N1**. |
| **R3** — "always move together" | **CLOSED** | Replaced at **both** sites, verbatim. Zero occurrences remain. |
| **R4** — refetch instruction | **CLOSED as written** | Both events named, scope corrected to workspace-wide, and the `item:updated` disclosure is stated plainly and honestly. The corrected scope has an operational consequence → **F2**. |
| **R5** — §7.4's placement | **CLOSED** | Now §5.5, at line 363, inside "The blocks, and when they are null", directly after §5.4. All three cross-references retarget. The apology sits directly beneath amendment 3 again, and §7's "these three amendments" is now true. |
| **R6** — the guard sentence | **CLOSED** | Now "sweeps every live document for retired error identities", which is `test_retired_inline_refusal_identity_is_absent_from_live_sources` (`:220`) — the check that actually fired. |
| **R7** — dangling reference | **CLOSED** | "(subject to §5.2 item 4 — the model must collapse)". |
| **R8** | **Routed, not mine** | `plans/plan_5.md` exists, scoped to one additive test file, blocked on plan 3. Correctly routed. |

---

## Findings

### SHOULD-FIX

#### F1 — `domain` is not published with `model`, and the document says it is, at two sites

**Where.** §5.2's opening sentence — the first line of the section, and the frame for the whole
four-condition rule:

> `model`, `anchors`, `domain` and `config_fingerprint` are published together or not at all.

and §3's slider row, in r2's new table:

> ⚠ `domain` null with `model`

**Both are false for `domain`.** `domain = slider_domain(break_even, item.quantity, infeasible)`
(`get_task_price_scenario.py:221`) returns `None` whenever `break_even_price_minor` is `None` —
no typical evidence, a residual of zero or less, or a break-even above the search cap — and also
when `min_minor >= max_minor` (`price_scenario.py:188-207`). The other three blocks are present
throughout.

**Reproduced against the shipped service**, with the typical carrying no usable sample — the
state §5.1 describes in its own words ("When **no** section has a usable typical,
`total_seconds` is `0`, `is_estimated` is `true`, and `anchors.break_even_price_minor` is
`null`"):

```
model    : PRESENT
anchors  : {is_fundable: False, break_even_price_minor: None,
            suggested_price_minor: None, infeasible_at_or_below_minor: 29}
domain   : None
```

The shipped suite asserts the same shape —
`test_c6_no_evidence_keeps_null_anchor_members_and_no_domain`
(`test_price_scenario_query.py:497-522`).

**Why it bites.** §3's ⚠ marker is the instruction telling a developer *which* null check to
write, and it names the wrong one: `model !== null` passes while `domain` is `null`, and
`domain.min_minor` throws. The state is not exotic — a workspace whose sections have fewer than
`min_sample_size: 5` completed samples reaches it, which is every new workspace and every newly
added working section. **`anchors` is genuinely published with `model`** (both are assigned
inside the same `if collapsed is not None` block, `:203-231`), so the chip row's identical
phrasing is correct — `domain` is the only one of the four that breaks the pattern, which is
exactly what makes the blanket sentence dangerous.

§5.4 states the truth in its first line — *"`domain` is `null` when there is no usable band.
Disable the slider and say why"* — 54 lines after §5.2 asserts the opposite.

**Proposed replacement, §5.2's opening sentence** (verbatim):

> `model`, `anchors` and `config_fingerprint` are published together or not at all. **Four
> things must hold at once**; `status` is only one of them. `domain` needs all four **and** a
> usable band on top — it is the one block that can be `null` while the others are present
> (§5.4).

**Proposed replacement, §3's slider row** (verbatim):

| slider ends `700` / `2 750` | `domain.min_minor` / `max_minor` ÷ `max(1, quantity)` — ⚠⚠ **`domain` can be `null` while `model` is present** — no usable typical means no band (§5.4); **and note `2 750`, not the mockup's `2 700` — see §5.4** |

---

#### F2 — the corrected refetch scope is right about the mechanism and wrong about the cost: it asks for an unbounded workspace aggregate on every step transition

**Where.** §6.3's closing instruction, as corrected at r2:

> **So: refetch the scenario on `task:step-state-changed` for *any* task in the workspace, and
> on `item:updated` for this item** … do not filter the step event to this task, because the
> typical is a workspace-wide median and any task's step transition can move it.

The reasoning is sound and the scope is the correct scope for *correctness*. The cost was never
checked, and it is worse than it looks.

**What one refetch runs.** `get_task_price_scenario` calls `get_task_budget_status`,
`_load_task_and_item`, `_typical_block`, `_current_valuation`, a `User` load and
`_load_preview_inputs`. `_typical_block` executes `typical_times_statement`, and that statement's
grouping subquery carries **no date predicate at all**
(`get_working_section_typical_times.py:24-39`): it groups **every** completed, non-deleted,
not-marked-wrong `TaskStep` in the workspace, for all time, by `(working_section_id, task_id)`.
The 90-day window is applied afterwards, as a `FILTER` on the outer aggregates (`:40-46`), and a
`percentile_cont` runs per working section.

So the per-refetch cost **grows with the workspace's entire history**, and the instruction fires
it once per step transition anywhere in the workspace, from every open price screen. On a floor
transitioning steps every few seconds, one open modal issues a continuous stream of full-history
aggregates.

**And the benefit is small per event.** The typical is a median over ≥ 5 samples in a 90-day
window; one more completed section total moves it slightly or not at all, and moves the
break-even proportionally. What the frontend needs is to not be *minutes* stale at the moment
the manager commits — not to be current to the second.

This is r2's own correction, and the honest fix is a debounce, exactly as the prompt suspected.

**Proposed replacement** (verbatim):

> **So: refetch the scenario on `task:step-state-changed` for *any* task in the workspace, and
> on `item:updated` for this item** — not only on a fingerprint mismatch. Both are workspace
> broadcasts you already have a socket for; do not filter the step event to this task, because
> the typical is a workspace-wide median and any task's step transition can move it.
>
> **Debounce it — trailing edge, 10–15 seconds, and coalesce.** This request is not cheap on our
> side (the typical is an aggregate over the workspace's completed-step history), and a busy
> floor emits step transitions continuously. You are guarding against a screen that is *minutes*
> stale at the moment of commit, not against being a second behind: one refetch after the events
> stop is worth as much as fifty during them. **Always refetch immediately before enabling Save
> after a long idle**, which is the moment the number actually has to be right.
>
> `item:updated` is emitted on item edits (quantity, category) and, to our knowledge, has not
> been named in a handoff to you before — if your client does not handle it yet, this is the
> screen that needs it. The window also slides with time alone, which no event covers; a screen
> left open for a long session should refetch on reopen regardless.

---

#### F3 — the production-time reply's action list promises "a known end date" for something §4 says has no date

**Where.** `HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819.md`, *Frontend
action required*, item 2:

> **Build that suppression behind one flag, removable in a single change** — see §4. **It has a
> known end date.**

§4, the section it points at, says the opposite in bold:

> Its intention is resolved; it has not passed its mechanism-inventory gate, so **it has no
> date.**

What item 2 means is that the *expiry* is known, not the date. But the action list is the part
read first and skimmed hardest, and "a known end date" is what a planner reads before deciding
whether the interim flag needs a removal ticket with a target sprint. A reader who never reaches
§4 schedules against a date that does not exist; a reader who does reach §4 has to work out
which of the two sentences is loose.

The whole point of §4 is that this answer expires *without* a date, and that the frontend should
build for a removal they cannot schedule.

**Proposed replacement** (verbatim):

> 2. **Build that suppression behind one flag, removable in a single change** — see §4. **Its
>    expiry is certain; its date is not yet knowable**, so make the removal cheap rather than
>    scheduled.

---

### NOTES

**N1 — §2's new enumeration is a two-direction partition with 14 keys in neither direction.**
It is not wrong — I walked all 46 keys against the serializer again and every claim in it holds,
including the two the prompt named (`config_fingerprint` correctly nullable; `anchors.is_fundable`
correctly qualified "when `anchors` is present"). But `item.client_id`, `item.quantity`,
`created_by.client_id`, `created_by.username`, all six `model` members and all four `domain`
members appear in neither list, and the sentence's shape invites a reader to conclude a field's
nullability from its absence. The `anchors` clause already models the right fix. Suggested
closing clause: *"Within a block that is present, every member not named above is non-null."*

**N2 — both documents have now been revised in place under an unchanged `Created at`, in a
document set whose §5 adopts the opposite convention.** The price-scenario handoff has changed
across three rounds and the production-time reply once, both keeping
`Created at (UTC): 2026-08-19T18:00:00Z` / `18:15:00Z` with no revision marker. This is **not**
the failure §5 retires — that one was about an *answer* changing after the frontend had cited it
for four days, and these corrections are pre-delivery, inside the authoring window, with the one
substantive reversal recorded visibly in §6. But both files are on `main`, at the path the
frontend pulls from, and a reader who fetched at 19:47 and again now cannot tell the two apart.
One line each closes it: a `Revised (UTC)` field, or `Status: draft until phase approval — first
delivery is the approval commit`. Cheap insurance in the one project that has already paid for
this exact ambiguity.

**N3 — two lines from this round's commit break the document's wrap.** §7 amendment 1's
"(subject to §5.2 item 4 — the model must collapse). Other endpoints are unchanged." and
amendment 3's guard sentence both now run well past the ~95-column wrap the rest of the document
keeps. Cosmetic only, but this document is otherwise meticulously formatted and the two long
lines are the visible seam of a hurried edit.

---

## What I verified correct this round

### P1 — the grep-first discipline, checked independently

I did not take the coordinator's greps on trust; I ran my own against the shipped file.

| Probe | Result |
|---|---|
| Surviving `§7.4` references | **none** — all three retargeted to §5.5 |
| Surviving "always move together" | **none** — both sites replaced |
| Divisions by a bare `quantity` | **none** — four sites, all `max(1, quantity)` (§3 ×3, §5.4 ×1); §8.2 unchanged and consistent |
| `saved.` / `created_by.` dereference chains | **exactly one** — the byline row, carrying ⚠⚠ and "Two checks, not one" |
| Superseded literals (`2 700`, `1211364`, `1635000`, `ivl_`) | **none used as a value** — the three `2 700` hits are all explicit contrasts against `2 750` |

**No site was missed a second time.** r2's lesson 1 was applied and it held. The one defect in
§3's new table (F1) is a fresh error in new text, not a leaked instance of an old one.

### P2 — r2's replacement text, read as if the coordinator had written it

- **§3's ⚠ markers, one by one.** `item` null on `detached` ✓ (`get_task_budget_status.py:111`).
  `TYPICAL` "always present" ✓ — computed before the binding branch (`:154`) and never nulled,
  including on both non-`bound` bindings. `AT PRICE` "gate on `model !== null`" ✓ — **correct and
  sufficient**: `allowance_seconds(P)` consumes only the three `model` members, so `model` is
  exactly the right gate for that row. Chip row "`anchors` null with `model`; the member is
  independently nullable" ✓ — both halves true (`:222-231`, and `break_even_price_minor` is
  `int | None`). Byline row ✓ — both nulls real and independent. Slider row ✗ → **F1**.
- **§2's enumeration**, walked against `serialize_task_price_scenario` a third time. Every
  positive claim holds; `config_fingerprint` belongs in the nullable list (`:247-252`);
  `anchors.is_fundable` and `anchors.infeasible_at_or_below_minor` are correctly qualified by
  "when `anchors` is present" — `is_fundable` is a plain bool and `infeasible_at_or_below_minor`
  returns an `int` on every path (`price_scenario.py:150-154`), so neither is nullable *within*
  a present block. **The prompt's two suspicions were both unfounded.** Incompleteness only → N1.
- **§6.3's refetch paragraph** → **F2**. The prompt's suspicion was well founded, and the cost is
  larger than a per-event GET because of the unbounded grouping subquery.
- **§5.2 item 3 and §6.1's R3 replacements.** Both now say the two share a *cause* (the live
  configuration) and are otherwise independent. Verified: `can_commit` (`:184-191`) and the block
  gate (`:196-207`) share `selection_ready and currency_agrees` and nothing else. §6.1's three
  paragraphs — shared cause, conservative direction, "unrelated to whether the blocks are
  present" — are now mutually consistent. ✓
- **Action item 6's rewrite** — "`model: null` *and* `saved: null` … they are different
  absences … `saved: null` … arrives **with a full `model`** — that is the screen's main use
  case, not an error state" ✓, matching the r1 reproduction exactly.

### P3 — §5.5's new home

| Check | |
|---|---|
| §5.5 sits inside §5 "The blocks, and when they are null", directly after §5.4 (line 363), before §6 | ✓ |
| §5.2 item 1's forward reference now reads "(§5.5.)" and lands one subsection later | ✓ |
| §6.1's third paragraph reads "See §5.5." | ✓ |
| §5.5's own closing line still references §5.2 item 2 correctly | ✓ |
| The apology paragraph sits directly beneath amendment 3, with nothing between | ✓ |
| §7's "These three amendments live here" is now true — three items, no fourth subsection | ✓ |
| §5.5's table unchanged from the version verified row-for-row at r2 | ✓ |

**The `can_commit` row was re-checked against plan 3's still-uncommitted change**, which deletes
`if budget_status.item_binding == "detached": can_commit = False`. That branch is dead —
`detached` ⟺ `item is None`, and `can_commit` already requires `item is not None` (`:185`) — so
§5.5's `detached → false` guarantee survives, and `test_c9_non_bound_binding_governs_the_full_payload`
still passes on the current tree.

### P4 — the production-time reply, end to end

Read in full for the first time since r1. It holds together: the Option C answer, the D16
rationale, the two rejected options, §2's amendment, §3's ratio caveats and §4's expiry are
mutually consistent, and §6's visible retraction is the right form — it names the failed search
("matched the literals `datetime.now` and `func.now` and missed the wrapper"), states the fact
("`today_utc()` is called in two files there"), and is explicit that the verdict never depended
on it. §3's two breaking conditions re-checked at source: the median substitution
(`budget_division.py:325-337`) and `distributable = budget − charged` with `charged` over
excluded steps only (`:308`, `:314-315`). One defect found → **F3**.

### The delta's perimeter

`git log --name-status b181abc..HEAD`: two commits, **documentation only**. `d747238` touches the
price-scenario handoff, the master plan, plan 4, adds plan 5 and my r2 handoff; `51261d5` adds
this round's prompt and touches plan 4. **The production-time reply was not edited this round**,
matching the prompt's statement. **No application file has been changed by phase 4 in any of the
three rounds.**

`tests/unit/docs/`: **59 passed**, matching the prompt — with r2's N-note standing that only one
of those 59 reads either phase-4 document, which is what plan 5 exists to fix.

**Not mine, and declared:** plan 3's in-flight edits to `get_task_price_scenario.py` and
`test_price_scenario_query.py` remain uncommitted in the working tree. I did not touch them; I
ran that test file read-only to check §5.5's `can_commit` row.

---

## Mutation-probe declaration

**No file in the repository was modified by this session.** No probe was applied, so none needed
reverting. Verification was by reading, by grep against the shipped document, and by one
read-only reproduction that called the shipped service through the existing phase-2 integration
fixture from an out-of-tree script, with `monkeypatch` substitutes restored on the same call
stack. No database write occurred; no state needed restoring.

**Full write perimeter — one file:**

- `docs/architecture/under_construction/implementation/simple_valuation_editor/handoffs/reviewer/2026-08-19_phase4_rereview_r3_handoff.md` (this file)

**I wrote no handoff to the frontend, no application file, no plan and no tracker row.**

---

## What approval will mean

For the record, since this is the third round and the remaining work is three sentences: with
F1, F2 and F3 applied, this document set is **correct and usable**, and the frontend gets — the
endpoint and its role gate; the exact payload with every one of 46 keys and its nullability; a
BigInt rounding function executed against the server's own implementation over 612 cases; the
three integer operations and the display-rounding rule; a bound on the approximation with its
correct arithmetic; the anchor-driven chip rule; the derived band with its ratified divergence
from the mockup; the four conditions that empty the numeric blocks and the binding rule that
overrides all of them; the Save flow with `can_commit`'s seven conditions and D9's unenforceable
precondition written down; the staleness boundary with what the fingerprint does and does not
cover; two named divergences; and, on the second document, a settled-only answer with an honest
expiry. That is a screen a team can build without asking us a question.

---

## Lessons for the plans

1. **A blanket "these N are published together" sentence needs one probe per member, not one per
   sentence.** F1 survived two rounds because the claim is true for three of its four subjects,
   and both r1 and r2 read it as a unit. The claim's *shape* — an enumeration asserting a shared
   property — is this project's named failure cluster, and it fails the same way each time: the
   member that differs is invisible inside a list of members that don't. **A criterion over a
   grouped claim enumerates one row per member**, which is charter rule 2 applied to prose rather
   than to tests.

2. **A correctness fix to a client instruction needs a cost line.** R4's correction was right
   about the mechanism and silent about what it asks the client to run — and the answer is an
   unbounded aggregate over the workspace's history, once per workspace step transition (F2).
   When a handoff tells a client *when* to call an endpoint, the sentence should carry the call's
   cost, because the reviewer who fixed the correctness has no reason to look and the frontend
   has no way to.

3. **The grep-first discipline works and should be standing, not a round's remedy.** This is the
   first round where no correction leaked to a second site, and P1 confirmed it independently
   across five probes. It cost the coordinator three greps. It should be written into the
   coordinator's fix protocol: **before a field-level fix is called done, grep the artifact for
   the field name and confirm the perimeter.**

4. **Reviewer prose still needs a round.** Two of this round's three findings are against text
   authored by a reviewer — F2 is r2's, and F1's §3 row is r2's while its §5.2 half is r1's. Three
   rounds in, the pattern is settled enough to state as a rule: **verbatim replacement text is
   the right protocol and it is unreviewed on arrival**, so a re-review's scope is always the
   corrections *and* the correcting sentences. This prompt's P2 was the reason both were found;
   it should be a standing section in every re-review prompt, not one earned by a lesson.

5. **An end-to-end read of the untouched document earned its place.** F3 sits in a file nothing
   changed this round, in the four-line action list, and it contradicts the section it points
   at. Neither r1 nor r2 read that list against §4 because neither had reason to. **A final round
   should read every document in the phase end to end once**, regardless of delta — the
   passing-glance clause is the mechanism, and this is the third time in this project it has
   returned something.
