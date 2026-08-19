# Plan 3 — closeout: the frontend contract, and the review's carried repairs

```
plan: 3
state: NOT_STARTED — blocked on plan 2 APPROVED (satisfied 2026-08-19)
date: 2026-08-19
gate: projection — WAIVABLE (see §5)
```

## 1. Goal

Two jobs that belong together because they are the same act — telling the outside world what
this feature is, and repairing what two review rounds found but deliberately did not spend a
fix cycle on.

1. **The frontend contract.** Master plan §8's six closeout obligations. Without them the
   endpoint ships and nobody can build the screen it exists for.
2. **The carried repairs.** Seven notes from phase 2's review, each a real gap in evidence
   rather than a defect in behaviour, batched here because batching them costs one review
   round instead of seven.

## 2. Files

**The frontend deliverable** — a **new dated handoff**, never an edit of a published file:

| Path | |
|---|---|
| `backend/docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_price_scenario_<date>.md` | new |
| `backend/docs/handoff/to_backend/…_production_time_live_share_state_<date>_REPLY.md` | new — the frontend's three questions, answered |

**The code repairs**, each one line or one row:

| Path | Change |
|---|---|
| `app/beyo_manager/services/queries/item_economics/get_task_price_scenario.py` | F3 (`is_deleted` in `_has_purchase_term`), F6 (comment or remove the dead override), F9 (collapse duplicated loads — **or** record the acceptance) |
| `app/tests/integration/services/queries/item_economics/test_price_scenario_query.py` | F2 (delete the duplicate C16 literal), F4, F5, F8 rows; F8's marker decision |

**No change to `price_scenario.py`, `calculator.py`, `cases/serializers.py` or any phase-1
file.** Both phases are APPROVED.

### The rule that governs the handoff, and why it is not negotiable

`HANDOFF_TO_FRONTEND_item_economics_operational_20260815.md` was **rewritten in place** on
2026-08-19 to retire an error identity. Five frontend artifacts cited the stale copy in good
faith for four days and a shipped feature was built around a refusal that no longer existed.
The frontend raised it themselves and asked for the convention. **Master plan §8's obligations
4 and 5 name that file: they are discharged by a NEW dated handoff that supersedes by
reference, never by editing it.**

## 3. Tasks

### 3.1 The six closeout obligations (master plan §8)

1. **The M1 arithmetic, specified for a second language** — per operation: integer arithmetic
   both sides, BigInt, no float, never a language `round()` (half-away-from-zero). The client
   executes this every slider frame; an ambiguity makes two screens disagree at the chip's
   flip point.
2. **Name the accepted divergence** (D5): on a task carrying excluded-step time this screen's
   `AT PRICE` exceeds the production-time screen's distributable total by exactly
   `charged_seconds`.
3. **The Save flow** (D4): Save is `POST …/evaluations/commit`; `can_commit: false` **disables**
   the button; reconciliation against the commit response is mandatory.
4. **§8.4's display prohibition** amended — its contract (per item, never per unit) stands.
5. **§6's status→treatment table** amended: D8 publishes `model`/`anchors`/`domain` under
   `item_unvalued` and `item_missing_expected_price`, where that table says numerics are `null`.
6. **Save cannot create a valuation row** — D9's precondition. With no current valuation the
   commit path refuses regardless of the price in the body, so `can_commit` is `false` and the
   purchase price must be set first through `PUT /items/{id}/valuation`. **This is the one
   obligation whose omission is silent**: it is the written form of an assumption about
   another codebase, and unwritten it is a defect waiting for the first optimisation that
   skips the prompt.

### 3.2 The production-time reply (owed, unblocked)

The frontend's `HANDOFF_TO_BACKEND_production_time_live_share_state_20260819.md` asked three
questions and has had only a conversational answer. Ship them as a dated file:
`share_state` is **settled-only by design** (D16's rationale, and Option A would reintroduce
the `left_seconds: -100` defect in the payload); `worked_seconds` is settled-only for every
consumer, structurally — there is **no clock read anywhere** in
`services/queries/item_economics/`; and `allowance_i / typical_i` is a true consequence of
`static_proportional_section_v1`, exact up to largest-remainder rounding, **but not a
contract** — it breaks for a section whose typical is null or `0`, and the constant moves with
`charged_seconds`.

**Correction owed with it:** the 2026-08-18 handoff's §Live time instructs the client to tick
`worked_seconds` locally while `share_state` stays settled — manufacturing in the client
exactly the contradiction D16 forbade in the payload. It must say `share_state` is a settled
verdict, suppressed or marked provisional while `state == "working"`. **New dated file.**

> **MANDATORY: this answer has a known expiry, and the reply must say so.**
> The `live_clock_for_working_time_economics` pipeline (intention RESOLVED 2026-08-19, gate
> pending) **reverses this answer**: its §4.1 makes `share_state`, `worked_seconds` and
> `left_seconds` live on this very endpoint, and its §5.4 obliges its own closeout handoff to
> carry "the go-live statement that deletes their interim verdict-suppression gate".
>
> Shipping "settled-only by design, adapt your UI" **without that forward notice** hands the
> frontend a contract that expires and makes them build a permanent suppression they will be
> told to unbuild. That is the same failure as the in-place rewrite of the 2026-08-15
> handoff — a stale contract consumed in good faith — and it is the failure this team wrote
> us a document about.
>
> **The reply therefore states, in the same breath as the answer:** settled-only is correct
> **and current**; a backend pipeline is in flight that will make it live on this endpoint;
> the suppression they build should be **removable behind one flag, not baked into the
> component**; and its removal is signalled by that pipeline's own dated handoff, not by this
> one. Everything else in the answer — the D16 rationale, the no-clock-in-the-layer fact, the
> `allowance_i / typical_i` warning — stands unchanged and is not expiring.
>
> **The price-scenario handoff (§3.1) carries no such caveat**: that payload has no progress
> block (D5, gross-of-progress), so the live clock cannot move a number on it. The two
> deliverables of this phase have different shelf lives and must not be written as though
> they share one.

### 3.3 The carried repairs

| id | change |
|---|---|
| F2 | delete `test_c16_discriminating_literal_is_exact`; `test_price_scenario.py` owns the guard |
| F3 | `_has_purchase_term` skips `term.is_deleted is True`, mirroring `collapse_terms` |
| F4 | criterion + fixture: two chain rows for one item, one superseded, asserting `saved.valuation_id` is the current one |
| F5 | add usable typicals `{11, 12}` to C4 (median `11.5` → half-even `12`, truncation `11`) |
| F6 | comment the dead `detached` override as belt-and-braces for §9.2A, or remove it |
| F8 | either move the marker or give the file a session; record which, and whether the two redundant workspace predicates get rows or a recorded acceptance |
| F9 | collapse the duplicated task/item/configuration loads, **or** record the acceptance with its reason |

## 4. Acceptance criteria

| C | Criterion |
|---|---|
| C1 | Every one of §3.1's six obligations appears in the new handoff, each traceable to its decision (D1, D4, D5, D8, D9, HC-5). A checklist test is not required; the reviewer reads it. |
| C2 | **No published handoff is edited.** `git diff` shows zero modifications under `docs/handoff/` — only additions. This is the criterion that enforces §2's rule. |
| C3 | F3: a row where a **deleted** purchase term is present — `can_commit` is `true` and the model collapses. **Named mutation:** restore the unfiltered `any(...)` → this row red. |
| C4 | F4: the supersession row. **Named mutation:** delete `superseded_at.is_(None)` from `_current_valuation` → this row red. It currently leaves the whole file green. |
| C5 | F5: the `{11, 12}` median row. **Named mutation:** `int(resolved)` in place of `round_half_even(...)` → this row red. It currently reddens nothing. |
| C6 | F2's duplicate is gone and the phase-1 mutation's observed-red set is **one** test again — measured across the **suite**, per master plan §5's widened rule. |
| C7 | F8's decision is recorded and, if tenant rows are added, each asserts its own predicate alone. |
| C8 | Suite green at or above the phase-2 baseline **2425 / 26 / 1**; failure IDs diffed, not counted. |

## 5. Gates

**Projection: waivable, and here is the justification to record if it is waived.** This phase
ships no new mechanism — no derivation, no rounding rule, no search, no statistic. §3.3's
repairs are one-line guards and test rows whose expected values the review already computed
and published; §3.1 is prose. Charter rule 6 has no trigger. *If the implementer finds one,
that is a STOP, not a judgement call.*

**Review: one round, light-scoped.** The MVP calibration's condition is finally satisfied
here and nowhere earlier in this project: most of this surface is not rule-6.

## 6. Review log

*(empty)*
