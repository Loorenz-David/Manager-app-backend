# Plan 4 — the frontend handoff and the production-time reply

```
plan: 4
state: CHANGES_REQUESTED r1 -> applied; r2 -> applied; awaiting re-review r3
date: 2026-08-19
gate: projection WAIVED — documentation only, no code, no mechanism
runs in parallel with: plan 3 (the carried repairs). No shared files — plan 4 touches only
      docs/handoff/, plan 3 only app/.
```

## 1. Goal

Tell the outside world what this feature is, and pay two debts. Without this the endpoint ships
and nobody can build the screen it exists for.

**Authored by the coordinator rather than an implementer session**, per the precedent of
`HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`: a handoff is a coordination
artifact compiled from shipped code and the decision record, and the coordinator holds both.

## 2. Files — both new, nothing edited

| Path | |
|---|---|
| `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_price_scenario_20260819.md` | new |
| `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819.md` | new |

**No published handoff is edited.** Both amend by reference. This is the rule the frontend
asked for after the 2026-08-15 file was rewritten in place, and it is enforced by C2.

## 3. What was delivered

### 3.1 The price-scenario handoff

Written **from the shipped serializer and query service**, not from the intention's §8 example
— which mattered, because that example carried four values §8A had to correct. Carries master
plan §8's six obligations:

1. **The M1 arithmetic for a second language** (§4) — the three operations, the BigInt
   `roundHalfEven` reference with the negative-operand correction, `Number` forbidden with the
   overflow arithmetic shown, `Math.round` named as the likely failure, display rounding to
   nearest minute, and the `(n+1)/2` bound with what it buys.
2. **The gross-of-progress divergence named** (§8.1) — the two screens differ by exactly the
   excluded-step time, deliberately, with the reason.
3. **The Save flow** (§6) — one call; `can_commit: false` disables the button; reconciliation
   mandatory.
4. **§8.4's display prohibition lifted**, its contract kept (§7.2).
5. **§6's status→treatment table amended** for this endpoint (§7.1), with §5.2 item 4's
   collapsibility condition.
6. **Save cannot create the first valuation row** (§6.2) — D9's precondition, flagged as the
   one omission that would be silent.

Plus what the code says and no decision document did: the twelve-status behaviour, the null
blocks, the anchor-driven chip, the derived band **including the `2 750` divergence from the
mockup**, `is_estimated`'s empty-set case, and `quantity`'s missing CHECK constraint.

### 3.2 The production-time reply

Answers all three questions — settled-only by design with D16's rationale and why options A and
B are declined; `worked_seconds` settled-only for every consumer, because it is
`total_working_seconds` and nothing else (the stronger *no clock in the layer* form of this
claim was false and was corrected at r1 — see the Review log); and the `allowance_i / typical_i` ratio as a true
consequence of the current allocation method but **not a contract**, with the two conditions
that break it today.

Carries the correction we owe: §*Live time* instructs the client to tick the number while the
verdict stays settled, manufacturing in the client the contradiction D16 forbids in the
payload.

**And it carries an expiry.** The `live_clock_for_working_time_economics` pipeline reverses the
answer on this endpoint. Shipping "settled-only, adapt your UI" without that notice would hand
the frontend a contract that expires — the same failure as the in-place rewrite. The reply tells
them to build the suppression behind one flag, and that its removal is signalled by that
pipeline's own handoff.

## 4. Acceptance criteria

| C | Criterion |
|---|---|
| C1 | All six of master plan §8's obligations appear in the price-scenario handoff, each traceable to its decision (D1, D4, D5, D8, D9, HC-5). |
| C2 | **No published handoff is edited.** `git diff` under `docs/handoff/` shows **additions only**. |
| C3 | Every payload key in §2 of the handoff matches the shipped serializer and query service — verified against `serializers.py:serialize_task_price_scenario` and `get_task_price_scenario.py:139-231`, not against the intention's example. |
| C4 | Every literal is the corrected one: `break_even 1_211_335`, `max_minor 1_650_000`, `infeasible 29`, `ival_` prefix, `allowance_seconds(855_000) = 8_681`. None of the four values §8A retired appears. |
| C5 | The production-time reply carries the expiry notice, and the price-scenario handoff **does not** — the two have different shelf lives and must not be written as though they share one. |
| C6 | Both files carry the amend-by-reference statement and name what they amend. |

## 5. Review

**Wanted, and light-scoped.** Documentation cannot be verified by a suite; the reviewer's job
is (a) C3 and C4 against the shipped code — every key and every literal — and (b) whether
anything in either document is *true but misleading*, which is the failure mode a handoff has.

Specifically worth attacking: §4's BigInt transcription (it is executable code in a document
nobody runs), §5.2's list of the five statuses carrying a model, and §6.1's `can_commit`
conditions against `commit_item_cost_evaluation`.

## 6. Review log

**review r1 — 2026-08-19, Opus 5 — `CHANGES_REQUESTED`. 3 blocking, 4 should-fix, 3 notes,
0 owner cards.** Every finding a text correction the coordinator owns; no ratified decision
reopened. **All corrections applied 2026-08-19 with the reviewer's verbatim replacements.**

The two things the plan nominated as riskiest — §4's BigInt transcription and the worked
example — were **re-executed independently** (612 cases, 0 mismatches; `855 000 → 188 100 →
14 469 → 8 681`) and are correct. C1, C2, C4, C5 and C6 held. **Every failure was in C3**, and
they shared one root: the handoff described the payload's nullability as a function of `status`
while the shipped query gates it on **five** conditions.

- **B1 — the block rule.** §5.2 listed `status` alone; the code requires `item_binding ==
  "bound"` **and** the status **and** `selection_ready` **and** `currency_agrees` **and** a
  collapsible model (`get_task_price_scenario.py:196-207`). Two were absent entirely.
  Reproduced against the shipped service: a committed task with an expired live cost model
  version reports `status: "ok"` with every block `null`. **Fixed**: §5.2 now enumerates all
  four with "treat `model === null` as the switch, never `status`", and a new **§7.4** carries
  intention §9.2A's non-`bound` payload table — including that `mismatched` always reports
  `ok`/`infeasible` and `can_commit` may be `true` with nothing to show.
- **B2 — four nullable fields documented as always present**: `currency`,
  `item.article_number`, `item.label`, `saved.expected_sale_price_minor`. All 46 keys were
  right; the nullability was not. **Three of the four were already recorded in intention §8A.**
  **Fixed**: annotated in place, plus a line stating that a brand-new item's first render is
  `saved: null`, `currency: null`, `model` populated.
- **B3 — `config_fingerprint` was the only staleness signal and is blind to the typical.**
  `typical_times_statement` uses a rolling 90-day window off `datetime.now`
  (`get_working_section_typical_times.py:23`), so the typical moves when any task in the
  workspace completes a step **and with time alone** — and `break_even`, `suggested` and all
  three `domain` values derive from it. The commit-response reconciliation cannot see it
  either: budget and allowance are functions of the price and the model, never the typical.
  **Fixed**: §6.3 now states the coverage boundary and instructs refetch on item-changed and
  step-transition events.
- **S1 — a false absence claim, published as verified.** See master plan §5's extended
  verification-scope rule. **Fixed** in both places, with the retraction left visible in §6 of
  the reply rather than silently corrected.
- **S2** (the `n`-conflation intention §3.2A had already corrected), **S3** (§8.1 read as
  though the production-time screen deducts *all* elapsed work), **S4** ("treat that rounding
  as inert" — tie-free is not inert, and BigInt `/` truncates on negatives): all **fixed**
  verbatim. **N1** (`max(1, quantity)`), **N2** (the cap case), **N3** (`can_commit`'s
  conservative direction): all **folded**.

**Verified green after the corrections:** `tests/unit/docs/` 59 passed; the only remaining
occurrence of the false absence claim is inside the sentence retracting it.

**Coordinator verification before folding:** S1's two `today_utc()` call sites read at the
line; B3's rolling window read at the line; B1's five-condition gate read at
`get_task_price_scenario.py:168-207`. Nothing accepted on the handoff's word.

**re-review r2 — 2026-08-19, Opus 5 — `CHANGES_REQUESTED`. 1 blocking, 4 should-fix, 3 notes,
0 owner cards. All eight applied.**

**Seven of r1's ten findings closed outright.** S1's correction survived the strongest probe of
the round — a **wrapper-aware transitive import walk over all 82 modules** reachable from
`services/queries/item_economics/`, matching seven clock primitives: 41 raw hits, 39 write-side,
**exactly two on a read path — the two the correction names.** True *and* complete.

**All three unclosed findings failed the same way, and it is how a correction fails rather than
how a draft does: each fix landed where r1 pointed and not where the same defect also lived.**

- **R1 (blocking)** — §3, the render table a developer actually builds from, was never touched.
  It still dereferenced `saved.created_by.username` on the one payload where `saved` is `null` —
  **the brand-new item, the flagship case §5.2 exists to celebrate** — divided by `quantity`
  three times after N1 corrected §5.4 to `max(1, quantity)`, and printed `2 700` where §5.4 calls
  that number wrong. **Fixed**: the table now carries ⚠ markers per row, a gating sentence above
  it, and `2 750`; action item 6 now names both absences.
- **R2** — a **fifth** nullability (`profile_picture`), excluded by the closed-set summary line
  the B2 fix itself introduced. **Fixed** with the full enumeration, both directions.
- **R3** — r1's own replacement text asserted `can_commit` and the model block "always move
  together"; three paragraphs later the document says they are "unrelated". The second is right —
  `item_unvalued` has a full model and `can_commit: false`. **Fixed at both sites.**
- **R4** — the refetch instruction was scoped "for this task" while the mechanism is
  workspace-wide, and asserted the frontend "already receives" `item:updated`. **Verified: that
  event exists as a workspace broadcast and appears in NO live handoff** — only two archived
  ones. **Fixed**: both events named, the scope corrected, and the fact that we have never
  published `item:updated` to them stated plainly.
- **R5** — §7.4 sat inside "Amendments to [another document]" and orphaned the apology
  paragraph. **Fixed**: moved to **§5.5**, apology restored beneath amendment 3, three
  cross-references retargeted.
- **R6, R7** — the guard sentence named the wrong test; a dangling reference to the deleted
  "collapsibility qualification". **Both fixed.**
- **R8** — neither phase-4 document is registered with the accuracy arbiter. **Routed to
  plan 5.**

**Coordinator verification before folding**: `item:updated`'s publication status checked
directly (3 emit sites, 0 live handoffs, 2 archived); the arbiter's coverage read at
`test_item_economics_handoff_accuracy.py:27-28, 159, 169, 175`. Guards green after every
correction: `tests/unit/docs/` 59 passed. **This time the fix perimeter was found by grep
before editing**, per r2's lesson 1 — all three R1 defects were confirmed to live in §3 and
nowhere else.

**Awaiting re-review r3** — delta-scoped, and it must attack r2's replacement text as
adversarially as r1's, because three of r2's five findings were defects *in r1's own proposed
wording*.
