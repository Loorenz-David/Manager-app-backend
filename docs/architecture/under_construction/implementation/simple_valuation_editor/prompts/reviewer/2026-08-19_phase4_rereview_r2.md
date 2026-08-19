---
plan: 4
role: reviewer
round: 2
date: 2026-08-19
project: simple_valuation_editor
kind: re-review — delta-scoped
---

# Session prompt — re-review r2, phase 4 (`simple_valuation_editor`)

## 1. Review history — what r1 settled

**Review r1 returned `CHANGES_REQUESTED`: 3 blocking, 4 should-fix, 3 notes, 0 owner cards.**
Every finding was a text correction the coordinator owns; none reopened a ratified decision.
**All ten have been applied, using r1's verbatim replacement text.**

r1 established the following as **settled — do not re-derive:**

- **C1 holds.** All six of master plan §8's obligations present and traceable, with obligation
  6 carrying the silent-omission framing.
- **C2 holds**, verified against `git log --name-status` rather than the working tree: plan 4's
  footprint under `docs/handoff/` is two `A`s and one `M` of a file plan 4 itself created. No
  published handoff was edited.
- **C4 holds.** Every literal re-checked at source; the four values §8A retired appear nowhere.
- **C5 holds.** The expiry notice is correctly present in the production-time reply and
  correctly absent from the price-scenario handoff, verified structurally against the
  live-clock intention's own §2.6 and §4.1.
- **C6 holds.**
- **§4's BigInt transcription was re-executed independently** (612 cases, 0 mismatches) and the
  worked example recomputed (`855 000 → 188 100 → 14 469 → 8 681`). **Both correct.**
- **P2's `can_commit` diff**: seven conditions in the prose, seven in the code, none missing,
  none inverted. `_ADMITTED_STATES` enumerated correctly, all five, no extras.
- **The key walk**: 46 keys ship, 46 documented, zero undocumented, zero phantom.

**Your scope is the delta**, plus the charter's passing-glance clause — anything seen wrong in
passing is reported, which is not decorative and has caught real defects in this project.

## 2. What changed, and what to attack

Ten corrections. The three blocking ones changed structure, not just wording, and are where
this round's weight belongs.

### B1 — the block rule (§5.2, and a new §7.4)

§5.2's first paragraph was replaced by r1's four-condition enumeration, the "One qualification"
paragraph deleted as instructed (its content is now item 4), and a **new §7.4** added carrying
intention §9.2A's non-`bound` payload table.

**Probe:** does §7.4's table match §9.2A and the shipped code? Specifically — `item` `null` on
`detached` and populated on `mismatched`; `typical` populated on **both**; `can_commit` `false`
on `detached` and **as resolved on `mismatched`**, which r1 reproduced as `true` with no model
on screen. And does §5.2 item 1's forward reference to §7.4 land where a reader will follow it?

### B2 — nullability (§2)

Four annotations added in place, plus a summary line. **Probe:** are there *others*? r1's walk
found four; the corrections address exactly those four. Walk the serializer once more for a
fifth — `purchase_cost_minor`, `created_by`, `domain`'s members, `anchors`' members — and say
whether the set is now complete or still partial.

### B3 — the staleness boundary (§6.3)

§6.3's final paragraph was replaced with r1's text: what the fingerprint covers, what it does
not, and the refetch instruction.

**Probe:** is the refetch instruction *actionable*? It names "item-changed and step-transition
events for this task". Confirm those are events the frontend actually receives — the 2026-08-18
handoff names `task:step-state-changed` — and that the sentence does not imply a subscription
they do not have.

### S1 — the false absence claim (production-time reply §1 and §6)

Replaced with the narrower claim that actually holds, and **§6 now carries a visible
retraction** naming the failed search rather than silently correcting it.

**Probe, and it matters:** the replacement asserts *"the read family is not clock-free in
general: version applicability and the typical's 90-day window both read the clock."* Verify
that sentence is now true and complete enough — are there clock reads in that family beyond
`today_utc()` at `get_economics_configuration_status.py:38` and
`get_task_budget_allocations.py:188`, and the two transitive ones? **Do not repeat the
coordinator's mistake: search for wrappers, not literals.**

### S2, S3, S4 and N1–N3

The `n`-conflation, §8.1's over-broad deduction claim, the "inert" wording, `max(1, quantity)`,
the search-cap case, and `can_commit`'s conservative direction. All applied verbatim except N3,
which was expanded into two paragraphs in §6.1 — **check that expansion says what N3 meant and
no more.**

## 3. The one question the delta raises on its own

r1's B1 correction tells the reader **"treat `model === null` as the switch, never `status`"**.
That is now the load-bearing instruction of the whole document.

**Is it sufficient?** A frontend that branches only on `model === null` gets the blocks right.
Does it also get `saved`, `currency` and `item` right — or does §2's new summary line
("a brand-new item's first render is `saved: null`, `currency: null` and a fully populated
`model`") establish that those three vary *independently* of the model, such that a
single-switch reader still has a gap? If so, that is a finding.

## 4. Environment

- No code changed in either round. `tests/unit/docs/` re-verified green after the corrections
  (59 passed) — the docs guards are the only automated check these documents have.
- **Note for your perimeter check:** plan 3 is running in parallel under `app/` with its own
  implementer session, and `implementation/live_clock_for_working_time_economics/` is a
  different project. Neither is yours.
- If you run the full suite, expect **2425 / 26 / 1** unless plan 3 has landed by then; a
  disagreement in the count is repeated and **ID-diffed** before any conclusion.

## 5. Closing protocol

Deposit at `handoffs/reviewer/2026-08-19_phase4_rereview_r2_handoff.md`, charter frontmatter:

- verdict `APPROVED` or `CHANGES_REQUESTED`;
- `⚠ OWNER DECISIONS REQUIRED (n)` — one line if none;
- **explicitly whether each of B1, B2, B3, S1–S4 and N1–N3 is closed**;
- findings by severity, each quoting the sentence at fault and proposing its replacement
  **verbatim**;
- a carry-forward dispositions table if you approve with open notes;
- your full write perimeter. **You write no handoff** — a document needing change is a finding,
  not an edit.

Do not update the master plan tracker or plan 4's Review log.

---

**One note on how this round came about.** Every blocking finding in r1 was a coordinator
error, and r1 found them by asking for something the *plan* did not nominate — the plan's own
"what to attack" section named three places, and all three were clean. That is the same lesson
this project has now earned at four levels: **an artifact's own account of where it is weakest
is a hypothesis by its author.** Treat this prompt's §2 and §3 the same way.
