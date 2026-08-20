---
plan: 4
role: reviewer
round: 1
date: 2026-08-19
project: simple_valuation_editor
kind: documentation review — light-scoped
---

# Session prompt — review r1, phase 4 (`simple_valuation_editor`)

## 1. Role and workspace

You review **two handoff documents**, not code. Nothing in this phase changed `app/`.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` — run commands from here if you run any.

Doctrine, by absolute path: `/Users/davidloorenz/agent-skills/pipeline-charter.md` and
`/Users/davidloorenz/agent-skills/plan-reviewer.md`. You never fix; you report and rule.

**These documents were written by the coordinator.** Review them as adversarially as you would
an implementer's code — more so, because a handoff has no suite behind it and the coordinator
has no second pair of eyes by default.

## 2. Why this round is light-scoped, and where the weight goes instead

Master plan §7 withholds the light review for rule-6 surface. **This phase has none** — it
ships prose. The MVP calibration's condition is finally satisfied.

So: do **not** re-derive the feature. Phases 1 and 2 are APPROVED, 105 tests, 34 mutations at
review r1 with none producing a wrong-but-green payload. Spend the round on whether these two
documents are **true, complete and not misleading**.

## 3. Read order

1. `plans/plan_4.md` — the six criteria and §5's statement of what this review is for.
2. `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_price_scenario_20260819.md`
3. `docs/handoff/to_frontend/HANDOFF_TO_FRONTEND_production_time_share_state_answer_20260819.md`
4. `master_plan.md` §8 — the six closeout obligations the first document must discharge.
5. `planning/intention.md` — §3.1A, §3.2A, §4.2A, §4.4B, §5.3A, §6B, §7A.1, §9.2A, §9A.1
   (**with its `†`**), §9A.2 (**with its retraction**), §9A.3.
6. The shipped code the first document claims to describe:
   `domain/item_economics/serializers.py:serialize_task_price_scenario`,
   `services/queries/item_economics/get_task_price_scenario.py`,
   `services/commands/item_economics/commit_item_cost_evaluation.py`,
   `domain/item_economics/price_scenario.py`.

## 4. Already verified by the coordinator — do not re-spend these

- **C2 — nothing edited.** `git status docs/handoff/` shows two additions and zero
  modifications. Both documents amend by reference.
- **C4 — the retired literals are absent.** No `1211364`, no `1635000`, no `ivl_`. The single
  occurrence of `ITEM_COST_INLINE_PRICE_ON_PRICED_ITEM` is the sentence retiring it.
- **§4's BigInt transcription is EXECUTED, not merely written.** Run in Node against the
  shipped `round_half_even` over **612 cases** — divisors `2, 3, 5, 100_000, 13_000_000`,
  numerators `−60…+60`, plus the exact operands of all three published operations at
  `P = 855_000`. **Zero mismatches**, every negative tie included.
- **The worked example is real**: `855_000` → budget `188_100` → `14_469` centimin →
  **`8_681` s** → `144.68` min → `2h25m` nearest-minute, `2h24m` truncated. Computed against
  the shipped module.

**Re-run any of these if you doubt them** — but they are recorded so the round is not spent
there.

## 5. Named probes — this is where the round goes

### P1 — is anything **true but misleading**?

The characteristic failure of a handoff is not a false sentence; it is a true one a hurried
reader will act on wrongly. This project has already shipped one: a correct claim placed under
a three-row table so it read as applying to all three rows.

Hunt specifically for:

- **§5.2's "the screen works for an item nobody has priced yet"** — the amendment with the
  widest blast radius. It carries a qualification (the model must *collapse*; a purchase-cost
  term with no purchase cost still yields nulls). Is that qualification placed where a reader
  who skims will meet it, or two paragraphs later?
- **§7.1's amendment to the operational handoff's §6 table.** It says "for this endpoint only".
  Is that unambiguous, and is the reader told what *other* endpoints still do?
- **§8.1's divergence.** Told plainly — but does the document make clear it is *ratified* and
  not a bug, in the sentence a manager's screenshot would land next to?

### P2 — `can_commit`'s seven conditions, diffed against the code

§6.1 lists the conditions in prose, written from intention §9A.2. **Nobody has diffed that
prose against `commit_item_cost_evaluation`.** Read the admission path and confirm each
condition is real, none is missing, and none is stated more strongly than the code enforces.
Note especially the asymmetry §9A.2 records: `effective` is `None` whenever no valuation row
exists, *regardless of the price in the request body*.

### P3 — every payload key against the serializer (C3)

Walk §2's JSON key by key against `serialize_task_price_scenario` and the query service's
`typical` (`:139-145`) and `anchors` (`:223-230`) blocks. A key that does not ship, a key that
ships and is undocumented, or a nullability stated wrongly are each a finding. **The document
claims it was written from the serializer rather than the intention's example — verify that
claim.**

### P4 — are the divergences complete?

§8 names two things the frontend should hear from us rather than discover: the gross-of-progress
difference, and `quantity`'s missing CHECK. **Is there a third?** A reviewer looking for one is
the point of this probe. Candidates worth checking rather than assuming: `is_estimated`'s
empty-set case, `infeasible_at_or_below_minor` being non-zero, `config_fingerprint`'s
null-coupling, and the `final`-style question of whether any published number can *decrease*
between two polls.

### P5 — the second document's expiry notice

The production-time reply answers "settled-only by design" and then §4 states that the
`live_clock_for_working_time_economics` pipeline **reverses that answer on the same endpoint**.
Assess: is the expiry stated strongly enough that a frontend dev builds a removable flag rather
than a baked-in suppression? Is it honest about having no date? And is the price-scenario
handoff correctly **free** of any such caveat — its payload is gross-of-progress, so the live
clock cannot move a number on it (C5).

**Do not review the live-clock pipeline itself.** It is a separate project with its own gates;
its intention and a coordinator review sit under
`implementation/live_clock_for_working_time_economics/`. Read them only far enough to judge
whether §4's claim about it is accurate.

### P6 — the obligations, counted (C1)

Master plan §8 lists six closeout obligations. Confirm each appears, each is traceable to its
decision (D1, D4, D5, D8, D9, HC-5), and that **obligation 6** — Save cannot create the first
valuation row — is stated as the one whose omission would be *silent*, because that is the only
one the backend cannot enforce.

## 6. What a finding looks like here

Severity as usual: **blocking** (the document would cause the frontend to build the wrong
thing), **should-fix** (a real inaccuracy, contained), **note** (judgment, placement, tone).

A handoff-specific rule: **"this is true but I had to read it three times" is a should-fix, not
a note.** The audience is a developer under time pressure who will implement from a skim.

## 7. Closing protocol

Deposit at `handoffs/reviewer/2026-08-19_phase4_review_r1_handoff.md`, charter frontmatter
(`plan`, `role`, `round`, `verdict`, `date`, `actor`):

- verdict `APPROVED` or `CHANGES_REQUESTED`;
- `⚠ OWNER DECISIONS REQUIRED (n)` after the opening summary — one line if none;
- findings by severity, each quoting the sentence at fault and proposing its replacement
  **verbatim**, since the correction here is text;
- **what you verified correct**, specifically — including your key-by-key result for P3;
- lessons for the plans;
- your **full write perimeter** by path. **You write no application file and no handoff** — if
  a document needs changing, that is a finding, not an edit.

Do not update the master plan tracker or plan 4's Review log — the coordinator owns both.

**Note on the working tree:** plan 3 is running in parallel under `app/` with its own
implementer session, and the untracked `live_clock_for_working_time_economics/` folder is a
different project. Neither is yours; expect both in `git status` and declare them as not
written by you.
