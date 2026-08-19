# Plan 4 — the frontend handoff and the production-time reply

```
plan: 4
state: IMPLEMENTED — authored by the coordinator 2026-08-19; awaiting review
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
5. **§6's status→treatment table amended** for this endpoint (§7.1), with §5.2's collapsibility
   qualification.
6. **Save cannot create the first valuation row** (§6.2) — D9's precondition, flagged as the
   one omission that would be silent.

Plus what the code says and no decision document did: the twelve-status behaviour, the null
blocks, the anchor-driven chip, the derived band **including the `2 750` divergence from the
mockup**, `is_estimated`'s empty-set case, and `quantity`'s missing CHECK constraint.

### 3.2 The production-time reply

Answers all three questions — settled-only by design with D16's rationale and why options A and
B are declined; `worked_seconds` settled-only for every consumer, enforced structurally by
there being **no clock in the layer**; and the `allowance_i / typical_i` ratio as a true
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

*(empty)*
