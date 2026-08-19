---
plan: (pre-plan, project-level — no phase plans exist yet)
role: reviewer (mechanism-inventory gate)
round: inventory
date: 2026-08-19
project: simple_valuation_editor
---

# Session prompt — mechanism-inventory gate, `simple_valuation_editor`

## 1. Role and workspace

You are running the **mechanism-inventory** gate. You are adversarial to the intention's
author — treat every mechanism description as hiding an ambiguity an implementer will
resolve silently in code, and treat "obvious" as the strongest warning sign in the
document.

Workspace root: `/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend`
Application root: `backend/app/` (this is where `.env` resolves; commands run from here)
Project folder:
`backend/docs/architecture/under_construction/implementation/simple_valuation_editor/`

**Read these two files first and follow them as this session's doctrine** (they are plain
markdown; read them by absolute path):

1. `/Users/davidloorenz/agent-skills/pipeline-charter.md`
2. `/Users/davidloorenz/agent-skills/mechanism-inventory.md`

If you are a Claude session, invoking the `mechanism-inventory` skill loads (2); read (1)
regardless.

## 2. Gate check — stop and report if any of these is false

- `planning/intention.md` reads `status: RESOLVED (round 2, …)`.
- `planning/owner_decisions.md` reads **Ledger empty**.
- `plans/` is empty. **No phase plans exist yet, by design** — this gate runs *before* the
  implementation-planner. If you find plan files, stop: someone ran the planner early and
  the gate's whole purpose is defeated.
- `master_plan.md` §3 shows this gate as the only tracker row.

## 3. Read order

1. `master_plan.md` — §4 naming registry, §5 standing rules, §6 environment, §7 gates.
   §7 tells you which mechanisms the coordinator already classified as rule-6 surface.
2. `planning/intention.md` — **in full**. It is the artifact you are auditing.
3. `planning/owner_decisions.md` — D1–D7 with their rejected branches. A decision recorded
   here is settled; you do not reopen it. You may find that a decision's *consequence* was
   folded into the intention incorrectly — that is a finding, and a different thing.
4. The source it grounds itself on, **read, not assumed** — every path in intention §2
   carries a line range and every one of them is checkable:
   - `app/beyo_manager/domain/item_economics/calculator.py`
   - `app/beyo_manager/domain/item_economics/budget_division.py`
   - `app/beyo_manager/domain/item_economics/configuration.py`
   - `app/beyo_manager/domain/item_economics/enums.py`
   - `app/beyo_manager/domain/item_economics/serializers.py`
   - `app/beyo_manager/services/queries/working_sections/get_working_section_typical_times.py`
   - `app/beyo_manager/services/queries/item_economics/get_task_budget_status.py`
   - `app/beyo_manager/services/commands/item_economics/_common.py`
   - `app/beyo_manager/services/commands/item_economics/commit_item_cost_evaluation.py`
   - `app/beyo_manager/models/tables/item_economics/` (column types and precisions)
5. `.archgraph/` via the archgraph MCP if available — orient with `archgraph_status` and a
   search for `domain-item-economics`. **You never promote, reject or edit review items**;
   the human adjudicates. Record what you would have recorded, in your handoff.

## 4. What this gate must produce

The skill's procedure, applied to this intention. Concretely: **every mechanism below
leaves this gate with a contract-grade definition written into the intention itself**, or
with an owner decision card explaining why it cannot be defined without one.

Contract-grade, per the skill, means: inputs and every type they may arrive as (including
what the ORM and the serializer actually return, not just what a test would construct);
per-type canonicalization; per-field semantics wherever order, case, precision or rounding
mode matters; the contract's identity if behaviour changes must be detectable; and the
invariant a test must prove **on the production code path**.

### The mechanisms in scope — all of them, in this order

| # | Mechanism | Where |
|---|---|---|
| M1 | price → budget → allowance, the collapsed affine form and its rounding | §3.1 |
| M1b | the declared `(n+1)/2` error bound against the persisted per-term path | §3.2 |
| M2 | break-even price, the search, and its monotonicity precondition | §4.1–§4.2 |
| M2b | suggested price and its ceiling-to-step | §4.4 |
| M3 | typical total: participating-section set, the median substitution, the no-evidence case | §5.1–§5.3 |
| M4 | the saved-version byline and its three named cases | §6 |
| M5 | the slider domain: band ends, step, and the floor applied to `min_minor` | §7.1–§7.4 |
| M6 | `config_fingerprint` — a fingerprint is a rule-6 mechanism by name; what goes into it, in what order, and what must change it | §8, §9.3, §9.5 |

**Do not scope yourself by the intention's own self-assessment.** §14's closing line
nominates two claims as "most worth attacking". That line was written by the same author
as the mechanisms, in the same session, and it is a hypothesis about where the weakness
is — never a scope. Sweep all eight rows at equal depth. Where the document sounds most
confident, be most suspicious: a mechanism the author worried about got attention, and a
mechanism nobody flagged got none.

### Method rules that apply to this sweep specifically

1. **A worked example is a test, not an illustration.** This intention reproduces a
   mockup's numbers from its own rules in several places, which is a claim that the rules
   *are* rules and not a fit to the pixels. **Do the arithmetic of every worked example by
   hand and say whether it follows the rule it claims to check.** This is cheap now and
   costs an implementer round later. (Master plan §5.)
2. **Charter rule 5 — no adjectives for mechanisms.** Hunt them explicitly. Any word doing
   specification work without a definition ("nice", "near", "sensible", "stable",
   "reasonable") is a gate failure, not a wording preference.
3. **Every symbol that appears in the payload contract (§8) must be defined somewhere in
   the document.** Walk §8's JSON key by key and point each key at the section that
   derives it. A key with no derivation is a mechanism with no contract.
4. **Charter rule 4 — check ranked rules are total.** The twelve-value status vocabulary
   drives §9.1's degradation table; verify the mapping is complete over the real enum and
   that each state's treatment is decidable, including the states the document treats as
   exceptions to their own rule.
5. **Two-language contracts — a specification obligation, not a scope extension.** This
   pipeline ships **backend code only**; no frontend file is in any perimeter. But D2's
   whole design is that the backend publishes constants and the *client* evaluates M1 on
   every slider frame, so M1 is a rule this repo authors and another codebase executes.
   A rounding rule that is exact in Python and ambiguous in JavaScript is not contracted:
   `Math.round` is half-away-from-zero, and a client that reaches for it disagrees with
   the server at exactly the boundary the chip flips on. Say explicitly, **per operation**,
   what the client must do — integer arithmetic on both sides, no float, no language
   `round()`. That text is written into the intention now and carried to the frontend
   handoff at closeout; it produces no code in this repo.
6. **Cross-screen agreement is a mechanism, not a nicety.** M3 must produce numbers that
   agree with `divide_production_budget`'s own fallback. Read that code and state whether
   the intention's description of it is accurate, including the case where a section's
   typical is `NULL` and the case where none is usable.

## 5. Constraints

- **You write documents, never code.** No file under `app/` changes. No test runs are
  required, though you may read anything.
- **The delta goes into `planning/intention.md`** — that is its home per the artifact map,
  and a contract patched into a downstream document is how document sets diverge.
- **Never renumber a section.** Other artifacts and this prompt cite §3.1, §5.3, §7.2,
  §9.1, §12. Insert **lettered** sections (`§7A`, `§3.1A`) so every existing citation stays
  true. Amend in place only when the amendment does not move a number.
- **Add a changelog entry** to §14 recording round 3, what you added, and what you
  changed and why.
- **Owner decisions.** Anything you cannot define without a product call becomes a
  **decision card** in the charter's format — question, story in the owner's world,
  branches with lived consequences, one recommendation with its reason, on-silence
  behaviour, trace line. All cards live together in ONE section headed
  `⚠ OWNER DECISIONS REQUIRED (n)` placed immediately after your handoff's opening
  summary. If there are none, say so in one line. Cards are the only owner-facing prose in
  the handoff; everything else is written for the coordinator and stays technical.
- **Unilateral resolutions get listed separately for ratification.** Where you resolve an
  internal contradiction by picking a side, that choice can carry product consequence even
  when no sentence looks like a decision. List every one, with what you chose and what the
  other side would have produced.
- **Do not reopen D1–D7.** They are settled with their rejected branches recorded.

## 6. Closing protocol

1. Write the intention delta (lettered sections + §14 changelog entry).
2. Deposit your report at
   `handoffs/reviewer/2026-08-19_inventory_mechanism_inventory_handoff.md`, with charter
   frontmatter: `plan`, `role`, `round`, `date`, `state`/`verdict`, `actor`.
3. The handoff **declares your full write perimeter** — every document touched, by path,
   generated from `git status` / `git diff --name-only`, never retyped from memory. The
   coordinator diffs your declaration against the tree and treats any undeclared write as
   a finding, whoever made it.
4. Do **not** update the master plan tracker row — the coordinator owns it.

## 7. Report back — what the handoff must contain

- **Opening summary**, then the owner-cards section (or its one-line "none").
- **The inventory table**: one row per mechanism — *mechanism / silent-failure risk /
  contract status before / contract status after / where the contract now lives*. Cover
  all eight rows of §4 even where the answer is "already contract-grade, verified against
  source at `path:line`".
- **The worked-example audit**: one row per worked example in the intention, with the
  arithmetic you did and whether it follows its own rule.
- **The §8 key walk**: every payload key mapped to the section that derives it, with
  undefined keys named.
- **Contradictions found**, each with both sides quoted by section, which side you chose,
  and what the other side would have produced in shipped behaviour.
- **What you could not settle from the source**, with what evidence would settle it.
- **Gate verdict**: `PASS` (every rule-6 mechanism now has a contract) or
  `OWNER_DECISIONS_PENDING` (cards outstanding — the gate holds) or `FAIL` with what is
  missing. The planner does not start on anything but `PASS`.

The exit gate is the skill's: every silent-failure mechanism has a contract-grade
definition in the intention. Then, and only then, this project hands to the
implementation-planner.
