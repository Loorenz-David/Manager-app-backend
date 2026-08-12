---
plan: phase 4
role: reviewer
round: 0
date: 2026-08-12
state: OWNER_DECISIONS_PENDING
verdict: AMENDMENTS_REQUIRED
actor: reviewer (Claude), plan-projection doctrine
---

# Projection handoff — phase 4: configuration services (round 0)

## Opening summary

I did the implementer's first hour of phase 4 on paper, from the plan and its cited
authorities alone, and the plan is not yet buildable. The economics of the phase are
right and the schema it builds on is solid, but I found one defect that would quietly
corrupt real numbers: when a manager types a figure with more decimals than the field
stores, the database trims it while the cost-per-minute rate is still calculated from
the untrimmed number, so a stored basis and its stored rate stop agreeing. I confirmed
this against the shipped calculator — the same setup produces a rate of 12.0107 when
the entry is used and 12.0105 when the saved value is used. One question needs the
owner personally: whether an over-precise entry should be quietly rounded or refused.
Beyond that, sixteen further points need the plan or the shared registry amended before
an implementer prompt is compiled — chiefly three error names that do not exist yet,
two test criteria that describe a concurrency test the repository has no way to write
today, and two forward items that were filed into the plan but never turned into work.

---

## ⚠ OWNER DECISIONS REQUIRED (1)

### Card 1 — Over-precise configuration entries: round them, or refuse them?

**Question.** When a manager enters more decimals than a configuration field stores
(e.g. 173.456 monthly paid hours in a field that keeps two decimals), should the system
round the entry and use the rounded number for everything, or refuse it and ask for a
rounded figure?

**Story.** A manager sets up the sewing group's cost basis and types 173.456 monthly
paid hours, copied straight out of a payroll export. The database quietly keeps 173.46.
As the plan stands, the group's cost per worker-minute is still calculated from the
number they typed, so the saved rate no longer matches the saved hours. Months later
someone recomputing the rate from that stored basis gets 12.0105 where the row says
12.0107, and every budget built on it becomes unexplainable — with no error anywhere to
point at.

**Branches.**
- *Round, then derive* — the entry is accepted, trimmed to 173.46, and every derived
  number comes from the trimmed value; the basis and its rate always agree.
- *Refuse* — the manager sees an error naming the field and its allowed decimals, and
  retypes 173.46 themselves; nothing is ever silently changed.

**Recommendation.** Round, then derive — it is how this codebase already handles fabric
meters, and it never blocks a manager mid-setup over one spare digit from a payroll
export.

**On silence.** The gate holds: phase 4 is not compiled. Either answer changes both the
request schemas and the acceptance criteria, so it cannot be guessed.

**Trace.** Intention §6A.1, §6A.11; phase-4 plan tasks 2/6 and C4; master plan §6.1.

---

## Decision ledger

Severity: **B** = blocking (implementer cannot proceed, or proceeds into a silent
defect); **S** = should-fix; **N** = note / explicit delegation.

| # | Decision point the artifacts do not determine | Classification | Proposed routing |
|---|---|---|---|
| B1 | Request numerics whose scale exceeds the column's are silently rounded by PostgreSQL, while Q2 is derived from the unrounded value | intention gap | §6A.1 amendment + plan task/criterion; **owner card 1** |
| B2 | Where `IntegrityError` becomes `ConflictError`, and how a multi-index command tells its conflicts apart | plan gap | task 3 rewrite + criterion |
| B3 | Three DB-conflict error identities are unregistered | plan gap (master §6.4) | registry amendment by the coordinator |
| B4 | C3/C6 concurrency harness: second session, committed seeds, interleaving, timeout, target database | plan gap | plan harness section + per-criterion DB target |
| B5 | C6's named mutation bundles two mutations; the `FOR UPDATE` half has no arbiter | plan gap | split into two named mutations |
| B6 | Forward items N3 and N7 never became a task or a criterion | plan gap | tasks 5/2 + criteria |
| S1 | C5 samples 5 of §6A.4's 9 invalid cells, and names none of them | plan gap | enumerate all 9 |
| S2 | C1's "no open version" rows have two realizations; neither is pinned | plan gap | pin one row to the soft-deleted-open realization + mutation |
| S3 | C2 asserts through `applicable(v, D)`, which has no registered name | plan gap (master §6.5) | register the name; pin C2's carrier |
| S4 | C9 does not say which of the two pydantic layers carries the P-D field docs | plan gap | pin the router body model |
| S5 | C9's OpenAPI-mirror half is a manual criterion with no generator in the repo | plan gap | relabel as a doc task (phase 9 C4 backstops) |
| S6 | Three list queries + `update_production_cost_group` + group-name uniqueness have no criterion | plan gap | add criteria |
| S7 | No criterion covers role gates or audit; audit event names unregistered | plan gap + registry | add criteria; register the audit vocabulary |
| S8 | `domain/item_economics/serializers.py` missing from "Files expected to change" | plan gap | add the file |
| S9 | New-version term semantics (full replacement vs carry-forward; empty set legal?) unstated | plan gap | state + criterion |
| N1 | `resolve_economics_configuration` signature, and how "today" is injected | free choice | explicit delegation |
| N2 | `first_failure` for the evaluable fixture is unpinned | plan gap | pin `None` on C8's sixth row |
| N3 | Delete-guard reference predicate: do soft-deleted evaluations / projections block? | plan gap | pin the exact WHERE clause |
| N4 | C4's derived-never-accepted row has no pinned outcome (ignore vs 422) | plan gap | pin "succeeds, persisted == derived" |
| N5 | Route notation and create-verb convention | free choice | explicit delegation |
| N6 | Config commands emit no workspace event — a deliberate absence, unstated | plan gap | state it |
| N7 | Test file placement | free choice | explicit delegation |
| N8 | `ITEM_COST_RATE_UNDERFLOW` is raised inside the calculator, not the command | note | state it in the prompt |
| N9 | §7A.4 row 1 applied to a chain whose open row was soft-deleted | note | record, no change |

---

## Blocking findings

### B1 — PostgreSQL silently rounds over-scale config inputs; the rate is derived from the unrounded value

`create_production_cost_basis_version` (plan task 2) derives Q2 from the request's
`monthly_paid_hours` and `planning_utilization_percent`, then persists both those inputs
and the derived rate. The columns are `Numeric(8,2)` and `Numeric(5,2)`
(`models/tables/item_economics/production_cost_basis_version.py:24-25`); PostgreSQL
rounds on scale overflow rather than raising. Verified in the running dev container
(read-only literal casts, no table touched):

```
SELECT 173.456::numeric(8,2), 80.005::numeric(5,2), 12.34565::numeric(12,4);
 173.46 | 80.01 | 12.3457
```

Verified against the **shipped** calculator (`domain/item_economics/calculator.py:261`):

```
calculate_cost_per_worker_minute(100000, Decimal('173.456'), Decimal('80.00')) -> 12.0107
calculate_cost_per_worker_minute(100000, Decimal('173.46'),  Decimal('80.00')) -> 12.0105
```

The row would store `monthly_paid_hours = 173.46` beside
`cost_per_worker_minute_minor = 12.0107`. §6A.11's theorem — re-deriving Q2 from
`monthly_paid_hours_snapshot`, `planning_utilization_percent_snapshot` and
`fixed_monthly_cost_minor_snapshot` reproduces the stored rate — is then false for that
basis version, and phase 7 snapshots those columns from the stored row. The CHECK
constraints do not catch it (all inputs stay positive), and the phase-3 `rederive()`
contract returns a mismatch marker rather than raising, so the corruption surfaces as
an unexplained integrity marker months later.

Nothing owns this seam: §6A.1 governs the *module* boundary (types), §6A.3 governs the
five quantization sites, and neither covers request → column scale. The repo already
solves the identical problem one domain over —
`services/commands/upholstery/requests/__init__.py:12-17` quantizes meters to the
`Numeric(14,3)` column scale inside the request model before anything derives from it.

Also note: **the routed forward item S4 does not close this.** S4 asks to prove
`Decimal(str(v))` "on a value with more decimals than target scale". I verified that
pydantic v2 already yields `Decimal('173.4567891234')` from a JSON float without any
help, so that row goes green while this defect ships. The two must not be conflated.

**Routing:** intention amendment (a §6A.1 row for persisted configuration numerics:
canonicalize to the column's scale before any derivation, or reject), then a plan task
and a criterion. Owner card 1 chooses round vs reject. Charter rule 6 — this is a
money/derivation mechanism with no contract, which is a gate failure.

### B2 — The `IntegrityError → ConflictError` conversion site is undetermined, and `run_service` cannot do it

`run_service` catches `DomainError` at `services/run_service.py:43` and everything else
at `:45`, returning `"An unexpected internal error occurred."`. A raw SQLAlchemy
`IntegrityError` is not a `DomainError`, so §7A.2's "surfaces as `ConflictError` with
the chain's identity" **requires an explicit catch inside the command** — which plan
task 3 forbids in the same sentence ("never caught, retried, or logged-and-continued").
The intention means never *swallowed*; the plan reads as never *caught*, and an
implementer following it literally ships a 500 where C3 expects
`ITEM_COST_CONCURRENT_BASIS_VERSION`.

Two repo idioms exist and they are not interchangeable:

- `services/commands/emails/create_email_template.py:40-41` — wrap the whole block, map
  **any** `IntegrityError` to one `ConflictError`.
- `services/commands/users/update_user_admin.py:115-123` — flush inside the command and
  **discriminate on the index name** (`if CLOCK_IN_CODE_INDEX_NAME in str(exc.orig)`),
  re-raising anything else.

Phase 4 needs the second. `create_cost_model_version` can violate three partial uniques
in one flush — `uix_cost_model_versions_open` (the chain race),
`uix_cost_model_terms_purchase_cost` (A5, which C5 *requires* be exercised on the DB
path) and `uix_cost_model_terms_name_active`. Under the blanket idiom, a manager who
submits two `item_purchase_cost` terms is told the version was concurrently modified.

**Proposed amendment:** task 3 names the index-name discrimination idiom with its
precedent, names the re-raise default, and pins the flush inside `maybe_begin`; a
criterion asserts that each of the three indexes yields its own identity (which
presupposes B3), with the named mutation "collapse the index discrimination to a single
`except IntegrityError` → the A5 row must redden".

### B3 — Three DB-conflict identities are unregistered

Master plan §6.4 registers no identity for:

| Index | Path | Registered? |
|---|---|---|
| `uix_cost_model_terms_purchase_cost` | second `item_purchase_cost` term, DB path (C5 requires it) | **no** |
| `uix_cost_model_terms_name_active` | duplicate term name within one version (task 2 requires it) | **no** |
| `uix_production_cost_groups_name_active` | duplicate group name (task 1 requires it) | **no** |

`ITEM_COST_SECTION_ALREADY_GROUPED` *is* registered for both paths, so INV-G1 is fine.
`ITEM_COST_TERM_SHAPE_INVALID` exists but is the calculator's re-validation identity,
raised as `ValidationError` from the pure module — it is not the command's DB-conflict
carrier. This is P-P exactly: a criterion mandates an outcome without naming its
carrier, so the implementer authors one and it ships unregistered.

**Routing:** master plan §6.4 amendment by the coordinator, before the prompt compiles.

### B4 — C3 and C6's concurrency rows have no harness and no precedent in this repo

`tests/conftest.py:46-50` provides exactly one session fixture (`db_session`, rolled
back at teardown). The repo's **only** existing "race" test monkeypatches `flush` to
raise a hand-built `IntegrityError`
(`tests/integration/services/commands/users/test_update_user_admin_clock_in_code.py:261-286`)
— precisely the shape C3 forbids ("the application pre-check alone does NOT satisfy
this row").

A genuine two-session conflict needs all of: a second session from `_session_factory()`
(precedent: `tests/integration/services/commands/items/test_create_item_sku_template.py:133-135`);
seed rows **committed** so both sessions see them; an interleaving in which the loser's
INSERT is issued while the winner's is still uncommitted (otherwise the loser blocks on
the index entry and nothing is proven about "both past S1"); teardown deleting the
committed rows (charter rule 11½); and a timeout, because a blocked INSERT otherwise
hangs the suite indefinitely. None of it is in the plan.

C6 is harder still: it requires a pause *inside* the delete command's transaction,
between the `FOR UPDATE` and the in-lock re-check, so a second session can commit a
referencing row in that window. No seam exists for that in the command as specified.

Separately, master plan §10 states "Plans must say per criterion which database it runs
against"; phase 4 says it for none of C1–C9, and the concurrency rows are exactly where
it matters (they commit).

**Proposed amendment:** a harness subsection in the plan pinning the second-session
factory, the committed-seed/teardown pattern, the interleaving mechanism and its
timeout, plus a per-criterion database column.

### B5 — C6's named mutation bundles two mutations; the lock half has no arbiter

C6 names one mutation: "removing the `FOR UPDATE` + in-lock re-check at its definition
site (`delete_production_cost_basis_version.py`) must turn this row red." If the command
holds only one reference check (inside the lock), deleting that check reddens the
ordinary guard row — the compound mutation "bites" while proving nothing about the lock.
Removing **only** `FOR UPDATE` and keeping the re-check leaves every serial row green,
so the lock itself is unarbitrated. Charter rule 11 requires the named mutation to name
what must redden and why; P-I requires per-row declarations.

Worth stating plainly in the plan: in phase 4 the `FOR UPDATE` has **no counterparty**.
§7A.6's other half — the commit path resolving versions `FOR SHARE` (§7B.1 step 3) —
ships in phase 7, so the only session that can contend with the lock is the test itself.

**Proposed amendment:** split into two named mutations, each with its own reddening row
(drop the in-lock re-check → the ordinary guard row reddens; drop `FOR UPDATE` → the
interleaved row reddens), or record explicitly that the lock's real arbiter lands in
phase 7 and carry a forward item.

### B6 — Forward items N3 and N7 were routed into the plan but never became work

Both appear under "Forward items routed here (coordinator, 2026-08-12)"; neither appears
in the tasks or the criteria.

**N3 (enum order).** Verified as shipped (`domain/item_economics/enums.py`):
`EconomicsStatusEnum` declares the four `NOT_CONFIGURED_*` members first, then
`ITEM_UNVALUED` … `NOT_EVALUATED`, then `INFEASIBLE`, then `OK`. §11A.4 evaluates
`infeasible`/`ok` **first**. The divergence is real — but it is **invisible to C8's
fixtures**, because the first four declared members happen to sit in §7A.5's order, so a
classifier that iterates the enum passes all five rows. A behavioural arbiter is
therefore impossible inside phase 4; the guard must be structural (an explicit ordered
sequence in `configuration.py`, plus a probe that permuting the enum's declaration
changes no C8 outcome). The plan must say so, or the forward item is closed on paper
only.

Related registry defect: master plan §6.3 states `EconomicsStatusEnum`'s "members = the
11 ordered values of §11A.4". As shipped they are 11 members in a **different** order.
That sentence is what invites the defect — it should be corrected to name the members
and state that declaration order carries no precedence.

**N7 (persisted-rate arbiter).** C4 has no row for it. Note that
`calculate_cost_per_worker_minute` already returns the quantized 4-dp Decimal
(`calculator.py:261-283`), so in phase 4 the whole of N7 is "persist the return value
verbatim" — and the half that matters (later reads consuming the persisted value rather
than re-dividing) cannot bite here, because nothing in phase 4 divides a budget. The
plan should carry the in-phase half (persisted column equals the calculator's return,
exactly 4 dp, on a fixture whose unrounded quotient differs from the quantized one) and
forward the consumption half explicitly to phase 5.

---

## Should-fix findings

**S1 — C5 samples where §6A.4 enumerates.** §6A.4 is total over `calculation_type` ×
column presence: 3 types × 4 NULL/NOT-NULL combinations = 12 cells, **3 valid and 9
invalid**. C5 says "3 valid, 5 invalid" and names none of the five. Charter rule 2, and
the same shape as phase-2's B4. The DB CHECK `ck_cost_model_terms_value_by_type` already
covers all 12 (phase 2); the command path should mirror all 9.

**S2 — C1's "no open version" rows have two realizations and the plan pins neither.**
Three of §7A.4's ten rows are "Open version: none". That state is reachable by an empty
chain *or* by a chain whose open row was soft-deleted (§7A.5 row 4's exact fixture). If
all three use an empty chain, deleting `is_deleted = false` from the open-row lookup
leaves all 20 rows green — the predicate clause has no arbiter. Rule 2's sole-predicate
companion and P-M. Proposed: at least one "none" row reached via a soft-deleted open
row, with the named mutation "drop `is_deleted = false` from the open-row lookup at its
definition site".

**S3 — C2 asserts through `applicable(v, D)`, which has no registered carrier.** §6.5
registers `configuration.py` as "pure §7A.5 ordered classifier over loaded rows" and
nothing else; no name exists for §7A.3's predicate. It is genuinely phase-4 code —
§7A.5 row 4 ("versions exist but none applicable today") cannot be evaluated without it
— but the registry rule ("a session needing an unlisted name routes it back to the
coordinator") means the implementer may not name it. Pin the name in §6.5 and state
whether C2's boundary rows assert through it or directly on stored
`effective_from`/`effective_to`.

**S4 — C9 does not say which schema carries the P-D field docs, and the candidates
diverge.** This repo runs two pydantic layers per endpoint: a router body model
(`routers/api_v1/working_sections.py:39-47`) and a command request model
(`services/commands/working_sections/requests/create_working_section_request.py`), with
`body.model_dump()` between them (`working_sections.py:68`). OpenAPI — and therefore the
`routers/README.md` mirror that C9's second half checks — renders **only the router
model's** field descriptions. A description placed on the command request model
satisfies C9's string assertion while the API surface carries none of the P-D wording.
Pin the router body model (or both, with the criterion asserting both).

**S5 — C9's second half is a manual criterion.** `routers/README.md:3` claims
"Autogenerated from FastAPI OpenAPI", but no generator exists anywhere in the repo — the
string occurs only in the README itself. "(reviewer-checked)" is therefore a manual
criterion, which charter rule 1 permits only for environment-lifecycle checks. Phase 9's
C4 already sweeps every phase's mirror rows, so the fix is labelling: make it a doc task
with phase 9 as the backstop, not an acceptance criterion.

**S6 — Four shipped files have no criterion.** `list_production_cost_groups.py`,
`list_production_cost_basis_versions.py` and `list_cost_model_versions.py` appear only in
"Files expected to change"; C1–C9 touch none of them, so workspace scoping,
`is_deleted` filtering, ordering and the `limit + 1` pagination idiom
(`services/queries/working_sections/list_working_sections.py:18-38`) all ship untested.
Same for `update_production_cost_group` and for the group-name uniqueness pair
(happy path + `uix_production_cost_groups_name_active` conflict).

**S7 — No criterion covers role gates or audit.** Task 1 says "ADMIN/MANAGER; audit";
§6.5 says "everything ADMIN/MANAGER except budget-status". No criterion asserts either.
P-G(a) was earned on exactly this shape (phase-1 S1: five ADMIN criteria rows untested)
and mandates a retention mutation ("removing MANAGER from the allow-list must redden
every MANAGER row"). Additionally, the audit **event names are unregistered**:
`write_audit` takes a free-form `event: str`
(`services/infra/audit/write_audit.py:12-22`; repo example `"email_template.created"`),
and §6.5 registers no audit vocabulary for this domain — same unregistered-name hazard
as B3.

**S8 — `domain/item_economics/serializers.py` is missing from "Files expected to
change".** Four queries ship this phase and this repo serializes at the query layer
(master plan §5's standing divergence record) via `domain/<x>/serializers.py`
(`list_working_sections.py:5,136`). §6.5 registers the module but describes it as
evaluation/status serializers only; the phase-4 config serializers have no home.

**S9 — New-version term semantics unstated.** The plan does not say whether
`create_cost_model_version` carries the complete term set or copies terms forward from
the version it closes. A6/INV-M2 (terms immutable with their version; removal = new
version) implies full replacement, but left unstated a manager changing one term silently
drops the rest and every later evaluation reprices. Also unstated: whether an empty term
list is legal (§6A.5's "empty term set ⇒ budget = expected price" suggests yes). State
both, with a criterion asserting the closed version's terms are not copied.

---

## Citation and reality-check verification

**Files expected to change** — all verified against the tree:

| Path | Status |
|---|---|
| `domain/item_economics/configuration.py` | absent — correctly marked new |
| `services/commands/item_economics/` | absent — new (directory + `requests/__init__.py`) |
| `services/queries/item_economics/` | absent — new |
| `routers/api_v1/item_economics.py` | absent — correctly marked new |
| `routers/api_v1/__init__.py` | exists (registration block at `:77-114`) |
| `routers/README.md` | exists (`app/beyo_manager/routers/README.md`) |
| `domain/item_economics/serializers.py` | **absent from the plan's list** — see S8 |

**Intention citations** — every section resolves and says what the plan claims: §7A.1
(S1/S2, no S3 for config chains — confirmed, config close columns are `effective_to`
only), §7A.2 (identities and the "index is the only arbiter" contract), §7A.3
(predicate, UTC frame, theorem), §7A.4 (10 rows, both chains), §7A.5 (6 rows, rows 3+4
share an identity), §7A.6 (`FOR UPDATE` + in-lock re-check), §6A.4 (percentage base and
the binding presentation rule), §6A.6 (underflow), §11A.4 (ordered vocabulary), §14
tests 8/10/16. §7.5's group guard ("no non-deleted basis versions and no active section
memberships") matches the plan's task 4 wording.

**Master-plan citations** — §6.1/§6.2 names match the shipped models exactly
(`cmvt` prefix, all nine index/CHECK names present in `__table_args__`). §6.4's
admission-identity shorthand (`…_EFFECTIVE_FROM_FUTURE` / `_REQUIRED` /
`_NOT_AFTER_OPEN` × two chains) expands unambiguously. §6.5's calculator public API
lists `calculate_cost_per_worker_minute`; verified present and exported in `__all__`.
One defect: §6.3's claim that `EconomicsStatusEnum`'s members are "the 11 ordered values
of §11A.4" is false as shipped (B6).

**Prior-phase dependencies verified in code, not assumed:** the two config chains'
partial uniques (`uix_production_cost_basis_versions_open`,
`uix_cost_model_versions_open`), the A5 and term-name uniques, the per-type nullability
CHECK, `ProductionCostGroupSection`'s membership-interval shape (no `is_deleted` — the
group-delete guard's "active membership" is `removed_at IS NULL`), and
`item_cost_evaluations.production_cost_basis_version_id` / `cost_model_version_id` (C6's
fixture target — the table exists).

**Criteria decidability** — could I write each test today, with one exact expected
outcome per case?

| Criterion | Decidable now? |
|---|---|
| C1 (20 admission rows) | mostly — blocked by S2 (which realization of "none") |
| C2 (adjacency, both chains) | **no** — S3: no registered carrier for `applicable` |
| C3 (conflict path, both chains) | **no** — B2 (conversion site) + B4 (harness) |
| C4 (rate rows) | partly — N4 unpinned; B1 unowned; N8 worth stating |
| C5 (term validation) | **no** — S1 (which 5 of 9) + B3 (unregistered identity) |
| C6 (guard race) | **no** — B4 (interleaving seam) + B5 (mutation split) |
| C7 (INV-G1 & group guards) | yes — three rows, exact outcomes, fixtures unambiguous |
| C8 (classifier via status query) | mostly — N2 (`first_failure` when evaluable) |
| C9 (P-D docs proxy) | **no** — S4 (which schema) + S5 (manual half) |

**Archgraph (read-only orientation, no delta):** initialized and valid, revision
`e1d96eaf…`, 126 nodes / 161 edges, **0 pending**, 0 stale, 0 diagnostics. The
item-economics domain node and the phase-2 table nodes (e.g.
`table-production-cost-basis-version`) are `human_confirmed` and agree with the shipped
code; no discrepancy to file. This session recorded no graph change.

---

## Explicit delegation list

Freedoms granted on purpose, so the implementer does not take them silently. Each is a
free choice **only** if the coordinator records it in the prompt:

1. **Classifier signature (N1).** The parameter set of
   `resolve_economics_configuration(...)` is the implementer's, subject to two
   constraints: the module stays pure (no I/O, no `datetime.now` inside), so the
   evaluation date is an injected parameter per §7A.3; and precedence comes from an
   explicit ordered structure, never from iterating `EconomicsStatusEnum` (B6).
2. **Route notation (N5).** §6.5 pins paths and verbs; its `<client_id>` brackets are
   notation, not Flask syntax — this repo is FastAPI (`/{...}`). The create verb is not
   uniform in the repo (`working_sections` uses `PUT ""`, `cases` uses `POST`); §6.5's
   `POST` is authoritative for this domain.
3. **Test placement (N7).** `tests/integration/services/commands/item_economics/`,
   `tests/integration/services/queries/item_economics/`, and
   `tests/unit/domain/item_economics/` (already exists from phase 3) — mirroring the
   existing layout per §6.5.
4. **Internal helper decomposition.** Shared chain-construction helpers inside
   `services/commands/item_economics/` are the implementer's to shape, provided every
   name that crosses a module boundary is in the registry (charter: unlisted names route
   back to the coordinator).

Points that are **not** delegated and must be pinned by amendment before the prompt
compiles: B1–B6, S1–S4, S9, N2, N3, N4, N6.

---

## Notes

- **N3 — delete-guard reference predicate.** §7.5 says config versions are deletable
  "while no evaluation references them". Projections *are* evaluations
  (`kind = 'projection'`) and are freely soft-deletable; soft-deleted evaluations still
  hold the FK. Pin the exact WHERE clause (all rows? non-deleted only? committed only?)
  — it decides whether a manager can ever delete a mistaken version after any scenario
  was drafted against it.
- **N4 — C4's derived-never-accepted row.** Verified: pydantic v2's default is
  `extra='ignore'` and neither layer overrides it, so a request smuggling
  `cost_per_worker_minute_minor` is silently dropped and the command succeeds with the
  derived value. The row must assert exactly that; an implementer who chooses
  `extra='forbid'` would produce a rejection instead, and both readings currently satisfy
  the prose.
- **N6 — deliberate absence.** Config commands emit **no** workspace event: §6.5
  registers only `item_economics:evaluation-committed` (phase 7). This diverges from the
  repo's habit (`create_working_section` dispatches `working_section:created`), so state
  it or it will be "fixed".
- **N8 — underflow is the calculator's.** `ITEM_COST_RATE_UNDERFLOW` is raised inside
  `calculate_cost_per_worker_minute` (`calculator.py:277-280`), so C4's command-path row
  passes with zero command-side code. State it so the implementer does not add a
  duplicate guard and the reviewer knows the row does not discriminate command logic.
- **N9 — recorded, no change.** §7A.4's row 1 ("no open version / NULL requested →
  accept, unbounded-past first version") also matches a chain whose open row was
  soft-deleted; accepting NULL there creates an unbounded-past open row overlapping the
  closed rows' windows. Harmless under §7A.3's today-only resolution (closed rows all
  carry `effective_to ≤ today`, so exactly one row is applicable), and §7A.5 row 4
  already accepts broken contiguity. Recorded so no future reviewer reads it as a defect.
- **Skeleton discarded.** The paper skeleton (command signatures, S1/S2 statement
  sketches, classifier shape) was built to produce this ledger and is deliberately not
  attached — the implementer must derive it from the amended plan.

---

## Verdict

**AMENDMENTS_REQUIRED.** Six blocking rows, nine should-fix rows, nine notes. One owner
decision (card 1) gates B1. The implementer prompt compiles only after the coordinator
routes every ledger row — amendment applied, upstream change made, or delegation
recorded — per the projection exit gate.

## Write perimeter (full)

- **Documents written:** this file only —
  `docs/architecture/under_construction/implementation/item_cost_calculation/handoffs/reviewer/2026-08-12_phase4_projection_r0_handoff.md`.
- **Code written:** none. No file under `app/` was created, edited or deleted.
- **Tool-recorded state:** none. Archgraph was read-only (`status`, `search_nodes`);
  zero changes applied, zero review items touched.
- **Database:** one read-only `psql` statement casting numeric literals
  (`SELECT 173.456::numeric(8,2), …`) against the running dev container — no table read,
  no row written, no schema touched. The configured database is untouched and at head.
- **Other side effects:** none. No commit, no branch change; the working tree is as it
  was at session start.
