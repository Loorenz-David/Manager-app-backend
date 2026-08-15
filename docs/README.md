# ManagerBeyo — Backend

Workshop management for a furniture manufacturing and upholstery business: tasks and their steps
move through working sections, workers clock in and record what they are doing, items carry issues
and upholstery requirements, and orders synchronise with Shopify.

**If you are an agent picking this up cold, read the domain document for the area you are touching
before you read its code.** The domain docs describe what the system does now and where its files
are; the code tells you how, but not why or what else depends on it.

---

## Domain map

| Domain | Owns | Docs |
|---|---|---|
| **Worker shifts** | Clock in/out, declared off-task states, the worker's daily timeline | [domains/worker_shifts/](domains/worker_shifts/) |
| **Item economics** | Item valuations, production cost configuration, committed evaluations and projections, the worker-minute allowance and the episode's actuals | [domains/item_economics/](domains/item_economics/) |
| Tasks & steps | Tasks, task steps, step state transitions, working-section routing | *not yet documented* |
| Items | Items, issues, categories, SKU templates | *not yet documented* |
| Upholstery | Requirements, inventory, orders, order needs | *not yet documented* |
| Cases | Customer coordination cases and case types | *not yet documented* |
| Pause reasons | Workspace catalog of pause/off-task reasons | *not yet documented* |
| Working sections | Sections and membership | *not yet documented* |
| Users & auth | Users, workspaces, memberships, roles, JWT, app scopes | *not yet documented* |
| Notifications | Real-time and push notifications | *not yet documented* |
| Emails | Connections, templates, threads | *not yet documented* |
| Customers | Customer records | *not yet documented* |
| Analytics | Aggregate reporting models | *not yet documented* |
| Audit & history | Audit log and entity history records | *not yet documented* |
| Files & images | Uploads, storage, image links | *not yet documented* |

Undocumented domains are a backlog, not a statement that they do not exist. When you make a change
that would have been easier with a domain doc, write it.

---

## Integrations

| System | Purpose |
|---|---|
| Shopify | Product, order and inventory synchronisation |
| Connecteam | External clock in/out source, running in parallel with in-app clocking |
| Email (SMTP/IMAP) | Outbound templates and inbound thread ingestion |

---

## Where to go

| I want to… | Go to |
|---|---|
| Understand a subsystem before changing it | `docs/domains/<domain>/` |
| Know how to *write* code here — layering, models, commands, queries, migrations | `architecture/` (numbered contracts at the repo root) |
| See what is currently being built | `docs/architecture/under_construction/` |
| See the contract with the frontend | `docs/handoff/to_frontend/` |
| Find why something was built a certain way | `docs/architecture/archives/` |

**`architecture/` (contracts) vs `docs/domains/` (maps).** A contract tells you *how to write* a
command, a query, a migration. A domain doc tells you *what exists* in a subsystem and where. If you
are asking "how should I shape this new query", read the contract. If you are asking "what happens to
a worker's timeline at clock-out", read the domain doc. Reading a neighbouring implementation file
to learn style is discouraged — that is what the contracts are for.

---

## Documentation discipline

Documents here fall into two kinds, and mixing them is what makes documentation rot:

| Kind | Location | Rule |
|---|---|---|
| **Living** — what is true now | `docs/domains/` | Updated **in the same change** that makes it out of date |
| **Historical** — what was done once | `docs/architecture/` (plans, summaries, archives) | Frozen once archived; never edited |

**Any change that alters the logic of a domain must update that domain's docs in the same change.**
Adding or changing a state, a field, an invariant, an endpoint, a request or response shape, who may
do what, or moving a file listed in a domain's file table — all require the doc to move with the
code. Behaviour-preserving refactors, performance work and test-only changes do not.

Domain docs must **not** reference implementation plans, summaries, migrations, or the history of how
something came to be. They answer *what is true* and *where to look*. History lives in the archives
and stays there.

---

## Plan lifecycle

Delivery work is tracked as plans under `docs/architecture/`.

- `under_construction/intention/` — goal-driven intention plans
- `under_construction/implementation/` — implementation plans being drafted, reviewed or built
- `implemented_summaries/` — completion summaries
- `archives/` — archived plans and their archive records
- `handoff/to_frontend/`, `handoff/from_frontend/` — cross-team contracts
- `debugging/` — debug plans raised after implementation defects

Lifecycle: create → review until approved → implement → summarise → archive. A plan is archived only
after independent review approves it, and archived plans are never edited afterwards.

Naming: `PLAN_<slug>_<YYYYMMDD>.md`, `SUMMARY_<slug>_<YYYYMMDD>.md`,
`ARCHIVE_<slug>_<YYYYMMDD_HHMM>.md`, `DEBUG_<parent_slug>_<issue>_<YYYYMMDD>.md`.
Feature sets with several phases keep their plans in a subfolder and move the whole folder on
archive.

Traceability: every summary references its plan; every archive record references plan and summary;
every debug plan references its parent; handoffs reference their source plan.

Templates: `architecture/under_construction/TEMPLATE_PLAN.md`,
`architecture/under_construction/intention/TEMPLATE_INTENTION_PLAN.md`,
`architecture/implemented_summaries/TEMPLATE_SUMMARY.md`,
`architecture/archives/TEMPLATE_ARCHIVE_RECORD.md`, `debugging/TEMPLATE_DEBUG_PLAN.md`,
`handoff/to_frontend/TEMPLATE_HANDOFF_TO_FRONTEND.md`,
`handoff/from_frontend/TEMPLATE_HANDOFF_FROM_FRONTEND.md`.
