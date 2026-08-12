# ⚠ OWNER DECISIONS REQUIRED — item_cost_calculation intention

```
role: owner-decision ledger (companion to intention.md §17)
date: 2026-08-11
state: CLOSED — shaping cards 1–4 answered 2026-08-11 (folded as changelog round 1,
       R1-1…R1-5); mechanism-gate cards 1–2 answered 2026-08-11 (folded as changelog
       round 4, R4-1…R4-2); phase-1 projection card 1 answered 2026-08-12 (folded as
       R5-2); round-6 owner correction + 2 pins answered 2026-08-12 (folded as
       R6-1…R6-3, new §8B). Nothing open.
```

Answers recorded below verbatim in spirit; the authoritative folded form is
intention.md rounds 1–2 (shaping cards) and round 4 (mechanism-gate cards). The R1-1
veto point (`item_currency` removal, a shaping extension of the owner's wording) was
**owner-confirmed 2026-08-11** — folded as round 2, R2-1. Nothing remains open.

---

## Card 1 — What the two item money fields mean

**Question:** Ratify: `item_value_minor` = current expected sale price,
`item_cost_minor` = purchase/acquisition cost (with non-negativity and
amount-requires-currency validation added)?

**Story:** An item shows value 3,500 kr and cost 800 kr. Nothing in the app today says
whether that 3,500 is what you expect to sell it for or what someone once guessed it
was worth — no calculation has ever read either number. The budget calculator is about
to treat 3,500 as the sale price and 800 as what you paid, and every committed
evaluation will freeze those meanings into history.

**Branches:**
- yes — both fields get their meaning, validation, and become the evaluation's inputs;
- no, different meaning — name the intended semantics; new fields may be needed;
- keep undefined — the domain adds its own price/cost fields and ignores these.

**Recommendation:** yes — the raw intention itself describes them this way, and zero
existing consumers means no breakage.

**On silence:** gate holds — no evaluations can be specified; §10.2 migration blocked.

**Trace:** intention §2.1, §4.7, §10.2, R-2.

**ANSWER (2026-08-11):** Neither ratify nor keep — **remove the columns from the item
model**; the new table system takes over item valuation and cost as an independent,
item-linked table. Folded as R1-1/R1-2 (new §4.7A `ItemValuation`; §10.2 rewritten to
journaled migrate-and-drop).
**Follow-up (same day):** the extension to `item_currency` was questioned, evidenced
(the upholstery requirement's currency/value columns are dormant; only PG
type-creation couples them), and **confirmed by the owner** — R2-1.

---

## Card 2 — Who may write item money

**Question:** Restrict writing `item_value_minor` / `item_cost_minor` to
ADMIN + MANAGER (removing today's WORKER task-creation and SELLER item-PATCH write
paths)?

**Story:** Today a worker creating a task can type an item price, and find-or-create
will silently overwrite the existing item's price with it — no record of the old
number survives. Once budgets derive from these fields, that stray write changes what
every later evaluation defaults to, invisibly.

**Branches:**
- restrict to ADMIN+MANAGER — cleanest; task-creation forms stop sending money for
  workers/sellers;
- keep SELLER write, drop WORKER — sellers may legitimately price incoming items;
- keep today's paths — the silent-overwrite hazard stays, mitigated only by snapshots.

**Recommendation:** restrict to ADMIN+MANAGER — committed snapshots protect history
either way, but live defaults should not be worker-writable.

**On silence:** gate holds on the item write-path role gates; everything else proceeds.

**Trace:** intention §2.1, §11, card 1.

**ANSWER (2026-08-11):** Yes — ADMIN and MANAGER only. Items will commonly be created
WITHOUT value/cost and priced later; provide a **specialized endpoint** backed by the
item-economics services (calculation + time projection) so pricing stays separate and
scalable from generic item CRUD. Folded as R1-3 (§11 "Set item valuation" with
economic preview).

---

## Card 3 — When the first evaluation happens

**Question:** Auto-commit an initial evaluation at task creation (whenever the
workspace is configured and the item has a price), or only ever by explicit manager
commit?

**Story:** A restorer picks up a chair task the morning after it was created. With
auto-commit, the budget existed the moment the task did — the worker sees "84 minutes
allowed" without anyone doing anything. With explicit-only, every task shows "no
budget" until a manager opens it and commits — reliable coverage depends on a human
ritual per item.

**Branches:**
- auto + explicit supersede — full coverage by default; managers refine when needed;
- explicit only — every budget is a deliberate act; coverage will be partial;
- auto, but marked "system-committed" until a manager confirms — extra state to keep
  honest.

**Recommendation:** auto + explicit supersede — the worker-facing value depends on
budgets simply existing.

**On silence:** gate holds on the §7.2 auto path; explicit commit ships regardless.

**Trace:** intention §3 step 2, §7.2 step 6, §11.

**ANSWER (2026-08-11):** Recommendation accepted — auto-commit at task creation +
explicit supersede. Folded as R1-4 (pinned: auto-path failure never fails task
creation).

---

## Card 4 — What workers see

**Question:** Do worker-facing surfaces show money, or only minutes and percentages
(and should the existing step `total_cost_minor` leak to workers be closed in the same
change)?

**Story:** A worker opens their step card: "38 of 84 minutes used, 46 remaining" tells
them everything the metric is for. Showing "873 kr budget, 395 kr consumed" also
reveals item pricing and margins — and today two worker-reachable endpoints already
return each step's salary-derived cost, which nobody has decided workers should see.

**Branches:**
- minutes/percent only for workers; money ADMIN+MANAGER; close the total_cost_minor
  leak — tightest, matches the "inform, not punish" intent;
- minutes + money for workers — full transparency, exposes margins;
- minutes/percent for workers, leave the existing leak as-is — inconsistent surface.

**Recommendation:** minutes/percent only + close the leak — the worker metric is time,
not price.

**On silence:** gate holds on worker-visible payload shapes (§10.4, §11).

**Trace:** intention §2.3, §10.4, §11.

**ANSWER (2026-08-11):** Recommendation accepted — minutes/percentages only for
workers; money ADMIN/MANAGER; close the existing `total_cost_minor` leak. Folded as
R1-5 (moved into must-ship, test 14).

---

# Mechanism-inventory gate cards (round 3 → answered round 4)

Cards carried verbatim in
`handoffs/mechanism_inventory/2026-08-11_mechanism-inventory_r1_handoff.md`
(charter format). Questions repeated here one-line; answers verbatim.

## Gate card 1 — Does time logged after a task closes still count?

**Question:** When a worker closes a step *after* the task was already resolved,
should the item's final cost result pick that time up (re-emit), or stay frozen at
the moment of closing?

**ANSWER (2026-08-11):** "The recommendation provided is correct" — **re-emit**
(branch A). Folded as R4-1: §8A.5 is the binding contract (guarded emit of
`PROCESS_ITEM_COST_RESULT` in `handle_process_step_transition` iff the step's task is
terminal); branch B recorded as rejected; the operational CLI re-emit stays in §13
"only if cheap"; §14 test 18 builds the branch-A row only.

---

## Gate card 2 — Is a 25 % VAT term entered as 25 or as 20?

**Question:** Confirm that percentage terms are a percentage **of the sale price you
type in** (the gross expected sale price) — so a statutory Swedish 25 % VAT-on-net is
entered as 20.00, not 25.00?

**ANSWER (2026-08-11, verbatim):** Percentage terms are planning allocations, not
statutory tax calculations. `percentage_of_expected_sale_price` always means exactly
`expected_sale_price_minor × configured percent`. The percentage is a
manager-controlled economic allocation used for production planning. For example, the
workspace may configure a term named "VAT reserve" with `percent_value = 15.00`; on
an expected sale price of 4,000 SEK, the calculator reserves 600 SEK. The term name
does not change the calculation semantics — a term named "VAT reserve" is therefore
not a statutory VAT engine and must not be presented as calculating the legally
payable VAT amount. This distinction is intentional: the item-economics domain
answers "how much of the expected selling price does management want to reserve for
this economic category?", not "what tax amount must be declared for this sale?".
Actual VAT treatment, including Swedish margin taxation (VMB) for qualifying
second-hand goods, is a separate accounting concern and outside this implementation.
Therefore no VAT-specific conversion is performed by
`percentage_of_expected_sale_price`: if management configures 15.00, exactly 15 % of
the expected sale price is reserved. A future accounting integration may introduce
legally derived tax amounts or additional calculation types without changing the
semantics of this planning allocation.

Folded as R4-2: §6A.4 rewritten — gross base confirmed; planning-allocation
semantics; binding presentation rule (never present a percentage term as legally
payable tax); VMB out of scope; the 25→20 translation kept as documentation guidance.

---

# Phase-1 projection card (round 0 → answered 2026-08-12)

Card carried verbatim in
`handoffs/reviewer/2026-08-12_phase1_projection_r0_handoff.md`.

## Projection card 1 — Do workers keep seeing item prices until phase 6?

**Question:** Close the item-price exposure (`item_value_minor` / `item_cost_minor` /
`item_currency` via `serialize_item` on worker-reachable task payloads) now in
phase 1 too, or leave it to phase 6 as currently sequenced?

**ANSWER (2026-08-12):** "The recommendation is correct" — **leave it to phase 6**.
No worker screen renders the numbers; phase 6 removes the columns rather than hiding
them, so nothing is written twice. Folded as R5-2: phase 1's "money absent" stays
scoped to `total_cost_minor`; recorded in the phase-1 plan's Notes.

---

# Round-6 owner correction (2026-08-12) — results at every episode boundary

Owner-initiated (not a session card): reading the plans, the owner corrected the
result boundary — READY on the task (all steps terminal) is the machine-detectable
completion; RESOLVED/FAILED/CANCELLED are manual and may lag, so terminal-only
results would never fire at actual completion. Reopens (READY → WORKING on step
addition/reassignment) must re-converge the result; and an item added to a future
task (return / pre_order, matched by article/SKU) keeps accumulating economics
across episodes — the item is decoupled from any single task.

Folded as R6-1…R6-3 (new intention §8B; §4.6/§8A.3/§8A.5 amended). The
cross-episode accumulation was verified already structural — recorded, no change.

## Pin 1 — How does a result row mark provisional vs final?

**ANSWER (2026-08-12):** state snapshot + nullable closed_at (recommendation
accepted) — `task_state_snapshot` enum copy + `task_closed_at` NULL until terminal.

## Pin 2 — Refresh the stored result at reopen, or leave until next READY?

**ANSWER (2026-08-12):** refresh at reopen too (recommendation accepted) — the row
flips to `working` immediately and never claims READY during ongoing work.

---

# Phase-2 review card (round 1 → answered 2026-08-12)

Card carried verbatim in
`handoffs/reviewer/2026-08-12_phase2_review_r1_handoff.md`.

## Review card 1 — Who owns the from-scratch migration stall, and when?

**Question:** Root-cause the migration-chain stall (a from-scratch
`alembic upgrade` on an empty database hangs at `CREATE TABLE alembic_version` —
pre-existing, predates this project) now as its own maintenance item, or defer it to
phase 9's drift batch?

**ANSWER (2026-08-12):** "The recommendation made is correct" — **own it now as a
separate maintenance item.** Coordinator authored the maintenance-session prompt at
`prompts/maintenance/2026-08-12_migration-chain-stall_r1.md` (parallel-safe:
read-only against the pipeline's files; destructive verification on disposable DBs
only). Master plan §10 caveat updated with the disposition.

---

# Maintenance card (shim follow-up r1 → answered 2026-08-12)

Card carried in
`handoffs/maintenance/2026-08-12_migration-shim-followup_r1_handoff.md` (session
BLOCKED/ESCALATE — correctly refused to rewrite an applied migration alone).

## Maintenance card 1 — Authorize the only durable graph correction

**Question:** Authorize a one-line historical metadata correction in applied
migration `8cf57fa23110_improve_task_notes_and_image_links.py`
(`down_revision: 'a3b5c7d9e1f2'` → `'183fb6115bd3'`) — a rule-7 exception — so the
revision graph becomes acyclic on disk and the private-internals shim can be
removed? And which replacement for the cold-build workspace anchor?

**ANSWER (2026-08-12):** **Yes — the edit is authorized** as an owner-authorized
one-time correction (metadata only; no DDL; databases at head unaffected; makes
durable what the runtime shim already does on every invocation). Anchor
replacement: **transient environment-only anchor**, inserted only during a
genuinely cold build and deleted before `upgrade head` returns — fresh databases
end with zero synthetic rows; mechanism documented in env.py.
