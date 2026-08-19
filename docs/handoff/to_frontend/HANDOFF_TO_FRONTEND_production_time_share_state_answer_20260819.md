# HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819`
- Created at (UTC): `2026-08-19T18:15:00Z`
- **Status: draft until phase approval — the approval commit is first delivery.** Revised once
  pre-delivery (review r1); the correction is recorded visibly in §6.
- Owner agent: `Claude Opus 5` (backend pipeline coordinator)
- **Answers:** `HANDOFF_TO_BACKEND_production_time_live_share_state_20260819` (frontend repo,
  `docs/handoff/to_backend/`)
- **Amends by reference:** `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`
  §*Live time* — **that file is not edited** (§5)

---

## Backend delivery context

- **What backend implemented:** nothing. You asked for a decision, not necessarily a change,
  and the decision is that no change is warranted. **Option C.**
- **API or contract changes:** none. Endpoint, response shape, error cases, role gates,
  ordering and socket events all unchanged.
- **What you are owed and are getting here:** the answer, its reasoning, a correction to a
  section of ours that caused the problem you found, and **notice that this answer expires —
  certainly, but on no date we can give you yet** (§4).

---

## Frontend action required

1. **Suppress or mark provisional the `share_state` verdict while `state == "working"`.**
   Keep rendering `share_state` as received — you are gating its *display*, not deriving it.
2. **Build that suppression behind one flag, removable in a single change** — see §4. **Its
   expiry is certain; its date is not yet knowable**, so make the removal cheap rather than
   scheduled.
3. **Amend your plan's criterion 5 explicitly** rather than relaxing it. The verdict stays a
   rendered backend value.
4. **Do not ship the `allowance_i / typical_i` ratio** as an item-level figure without the
   gate in §3.

---

## 1. Is `share_state` settled-only by design? — Yes. Option C.

Your trace was correct: `budget_division.py:364` compares the settled `worked_seconds` against
`allowance_seconds`, and the open interval is excluded until the step transitions out.

**The rule exists on purpose.** It was ratified as **D16** during the budget-division pipeline:
`share_state` compares the section's `worked_seconds` against `allowance_seconds` *specifically
so that `share_state`, `worked_seconds` and `left_seconds` can never contradict each other on
one card*. The intention records why — an earlier implementation built the two fields on
different bases and shipped `left_seconds: -100` beside `share_state: "on_track"`. Someone
found it, and it cost a fix round.

### Why not Option A

Making `share_state` live while `worked_seconds` and `left_seconds` stay settled would print,
on your own example, `"over_share"` beside `worked_seconds: 0, left_seconds: 186`. That is the
same contradiction inverted — moved out of your UI and into the payload, where every other
consumer inherits it.

Making all three live cascades further than it looks. `worked_seconds` on this endpoint is
`TaskStep.total_working_seconds` and nothing else (`budget_division.py:134`, `:266`) — a stored
column, never a clock difference — and `share_state` compares it against an allowance derived
from the same settled column, which is why two calls a minute apart return the same verdict.
(The read family is not clock-free in general: version applicability and the typical's 90-day
window both read the clock. What is clock-free is the worked-seconds basis itself, which is the
invariant that matters here.) Option A would put the first *worked-time* clock into this layer
to serve a verdict whose provisionality you can already detect.

### Why not Option B

You already have the discriminator. `state` and `state_entered_at` are on every section and
step row, and `state == "working"` ⟺ an open interval exists ⟺ the verdict is provisional. A
`share_state_basis` field would be derivable from `state` in every case — a second
representation of one fact, which is precisely how the `left_seconds` bug happened. What was
missing was not a field. It was the rule written down, which is §2.

---

## 2. The correction we owe you

**You implemented our guidance correctly and got an incoherent row.** §*Live time* of the
2026-08-18 handoff tells the client to add `now − state_entered_at` to `worked_seconds`
locally, while `share_state` stays settled. So our own document instructs you to manufacture,
in the client, exactly the contradiction D16 forbids in the payload.

**Amendment, superseding that section by reference:**

> `share_state` is a **settled verdict**. It describes completed work only and cannot become
> `over_share` while a step is `working`. Client-side ticking of `worked_seconds` and the
> progress bar remains correct and is still recommended — but the verdict must be **suppressed
> or marked provisional** whenever the row's `state == "working"`. Smoothing from
> time-of-receipt stays legitimate; deriving or overriding the verdict client-side does not.

---

## 3. `allowance_i / typical_i` — true, exact up to rounding, and not a contract

Your algebra is right. Under `static_proportional_section_v1` the allocation weights **are** the
typicals, so `allowance_i / typical_i = distributable / Σ weights` for every section — the same
constant. Your measured `0.560` across eight sections is that identity showing through
largest-remainder rounding, which shifts individual allowances by at most one second.

**Two conditions break it today, not hypothetically:**

1. **A section whose typical is `NULL` or `0` gets the median substituted as its weight**
   (`budget_division.py:327-335`). Its allowance is proportional to the median, not to its own
   typical — so the ratio differs, or is undefined because its `typical_worker_seconds` is
   `null`. Your eight sections all had samples (86 on disassembly), which is why it held so
   cleanly.
2. **The constant is `distributable / Σ weights`, and `distributable = budget − charged`**,
   where `charged` is time already logged on skipped, cancelled or failed steps. So the ratio
   moves when a step is excluded after work was logged, with no typical changing.

**And `allocation_method` is in the payload as the declared swap hook.** Deriving a number from
the *shape* of the current method is what that label exists to warn against.

**If you want the item-level ratio, ask for it as a field** — you cannot compute it directly
today anyway, since `distributable_seconds` and `charged_seconds` are not in the payload. If
you ship the derivation meanwhile, gate it on
`allocation_method === "static_proportional_section_v1"` **and** on every section having a
non-null typical.

---

## 4. ⚠ This answer has a known expiry — build the suppression to be removed

**A backend pipeline is already shaped that reverses §1 on this very endpoint.**
`live_clock_for_working_time_economics` makes the worked-seconds basis live — settled work plus
the concurrency-averaged share of any open `working` interval, computed once in the backend and
consumed by every present-tense surface. Under it, `share_state`, `worked_seconds` and
`left_seconds` all go live on `production-time`, and the section 25 minutes into a 3-minute
allowance reports `over_share` in the same payload as the figures that justify it.

Its intention is resolved; it has not passed its mechanism-inventory gate, so **it has no
date.** But it is real, and you should not learn about it after building against §1.

**What this means concretely:**

- **§1 is correct and current.** Ship the suppression.
- **Build it behind one flag, in one place**, not baked into the component. Its removal should
  be a single change.
- **Its removal is signalled by that pipeline's own dated handoff**, not by this one. That
  document is already obliged to carry the go-live statement that retires your interim gate.
- **§2's correction and §3's warning do not expire.** The rule that a client must not derive
  the verdict, and the ratio caveats, hold in both worlds.

We are telling you now because the alternative is handing you a contract that expires silently
— which is the thing your own document asked us to stop doing, and which we did to you four
days ago.

---

## 5. On the document convention

**Adopted.** Your request — *"do not rewrite this file in place if the answer changes later;
issue a new dated handoff"* — is now the rule on our side. This file amends the 2026-08-18
handoff **by reference and does not touch it**, and the same convention governs
`HANDOFF_TO_FRONTEND_price_scenario_20260819.md`, which amends three sections of the 2026-08-15
operational handoff without editing it.

Your account of the cost was accurate: the 2026-08-15 file was rewritten under its original
filename and date, five of your artifacts cited the stale copy in good faith for four days, and
a shipped feature was built around a refusal that no longer existed. A new filename is cheaper
than a mirror digest for both of us.

---

## 6. Validation notes

- **Backend validation run:** none required — no code changed. The facts above were verified
  against source at the line: `budget_division.py:364` (the comparison), `:134` and `:266`
  (**`worked_seconds` is `total_working_seconds` and nothing else** — the claim §1 actually
  rests on), and `:327-335` (the median substitution).

  **A correction to an earlier draft of this document, kept visible because you were nearly
  told it.** A draft asserted "no clock read anywhere in `services/queries/item_economics/`".
  That is **false** — `today_utc()` is called in two files there, and it wraps
  `datetime.now(timezone.utc)`. The original search matched the literals `datetime.now` and
  `func.now` and missed the wrapper. The verdict is unaffected, because it never depended on
  the directory being clock-free — only on the worked-seconds basis being a stored column,
  which it is. Recorded so you do not inherit a structural guarantee we cannot make.
- **Suggested frontend validation:** one test that the verdict is not rendered as a verdict
  while `state === "working"`, and one that `share_state` is still rendered as received when it
  is not. Keep your mutation-tested rule that no file compares `worked_seconds` to
  `allowance_seconds` to decide a verdict — it stays correct under both the current and the
  future behaviour.

## 7. Trace links

- Question: `HANDOFF_TO_BACKEND_production_time_live_share_state_20260819` (frontend repo)
- D16's authority: `backend/docs/architecture/under_construction/implementation/simple_production_budget_division/planning/intention.md`
- The pipeline that will reverse §1: `backend/docs/architecture/under_construction/implementation/live_clock_for_working_time_economics/planning/intention.md`,
  with the coordinator's pre-gate review beside it
- Amended by reference: `HANDOFF_TO_FRONTEND_production_time_and_worker_cards_20260818.md`
  §*Live time*
