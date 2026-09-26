# ManagerBeyo backend — orientation

Read this first. It is the things that cost time to rediscover, not a description of the
codebase. Keep it short; if a section stops being true, fix it rather than adding a caveat.

## Running the app

The server is **not** run in Docker. `docker compose` is used for **postgres and redis only** —
the `backend` and `worker` services sit behind `profiles: [app]`, have **no bind mount** (code is
`COPY`'d into the image), and the backend container has been stopped since July 2026. Running
`docker compose logs -f backend` tails a dead container's frozen history, which looks exactly
like a live server producing no output.

```bash
cd app && python run.py 2>&1 | tee server.log   # logs go to THIS terminal; nothing writes a log file
```

`run.py` silently hunts for a free port if `PORT` (8000) is taken — it will start on 8001 and
say so in one line that is easy to miss. Kill the old process rather than letting it slide.

## Logging

stdlib `dictConfig` → one StreamHandler → **stdout, as JSON**. No file, no Sentry, no OTel.
`core/logging/formatter.py` passes through any `extra=` field a caller sets. (It used to keep a
seven-key whitelist and silently drop the rest; if you see old code passing fields that never
appeared in output, that was why.)

`RequestContextMiddleware` exists at `core/logging/middleware.py` but **is never registered**, so
`correlation_id` and `request_id` are `null` on every line.

SQL echo is on whenever `environment == "development"` (`models/database.py:31`), which is the
default because `.env` sets `APP_ENV`, not `ENVIRONMENT`. Expect a log line per statement; filter
with `grep stock_webhook` or `jq`.

## Tests

```bash
cd app && BEYO_TEST_SLOT=<unique> python3 -m pytest -q
```

- **Run from `app/`**, not the repo root — conftest imports `beyo_manager` and fails otherwise.
- **`BEYO_TEST_SLOT` on every invocation.** It picks the worker-database set. `pytest.ini` carries
  `-n 6 --dist loadfile`, so even a single-file run claims six databases.
- **One run per slot at a time.** Two concurrent runs on one slot produce hundreds of spurious
  failures that look like real breakage (measured: 959 failures on a comment-only tree).

### The baseline — 23 known failures

`main` does not have a green suite. The expected failure set is checked in:

`docs/architecture/under_construction/implementation/stock_report/handoffs/implementer/2026-09-21_batch_D1_baseline_ids.txt`

**Diff failure IDs both ways against it** rather than comparing counts — the pass count drifts.
Two of the 23 are stale references owned by a foreign project; three are
`A transaction is already begun on this Session`.

## Lint

`ruff check` passes on well-kept files but reports ~109 pre-existing errors repo-wide, and
`ruff format --check` already fails on ~16 files at HEAD. **Check only the files you touched, and
confirm a failure is yours** (stash and re-check) before "fixing" it.

## Git

- Stage with **explicit paths**, never `git add -A` — the tree often carries unrelated work.
- **Never push.** The branch is ~189 commits ahead of origin by design.

## Architecture graph (`.archgraph/`)

Useful for orientation, **not a specification.** As of 2026-09-22: 246 nodes, and **105 pending
reviews** — the stock-report tier is 22 nodes of which 20 are `ai_inferred` / `reviewState:
pending`, with empty `sourceLinks`, so staleness detection does not cover them. Descriptions
spot-check as accurate and are unusually rich on *why*, but nothing there has been human-confirmed.
When the graph and the code disagree, the code wins; when the graph and a ratified plan disagree,
the plan wins.

Evidence is anchored `path` + `symbol`, **no line spans** — see `.archgraph/agent-operating-policy.md`.
Do not add `startLine`/`endLine`, and do not report line drift as staleness.

## Stock report

Shipped and closed 2026-09-22 (16 phases). It is the Scanner webhook integration plus the
priority board.

- **Contract for the frontend:** `docs/architecture/under_construction/implementation/stock_report/handoffs/to_frontend/`
- **Spec:** `.../stock_report/planning/intention.md` (RATIFIED) and `.../master_plan.md`
- **Known open items:** `.../REMAINING_WORK.md` — five, deliberately carried out of the pipeline.
  The largest is **S3**, a lock-order window in the deleted-webhook path.
- Archived batch prompts/handoffs live at `archive/batch_<X>/<same relative path>`; citations were
  not rewritten. See `.../archive/README.md`.

**Snapshot layer (2026-09-26):** the board is a snapshot read. A manager opens a *version*
(`POST /api/v1/stock-report/snapshots/versions`) that freezes every live row's
`quantity_requested` into `stock_report_item_snapshots`; `priority`/`priority_order` and
`quantity_missing` live on the snapshot, **not** on `stock_report_items` (the columns are gone).
`GET /items` shows only rows with an active snapshot unless `live_stock=true`. A snapshot's
wire `quantity_awaiting` keeps counting units Scanner has resolved (`quantity_resolved`,
credited by the processed webhook) — completion never goes backwards;
`GET /snapshots/versions/active` and each row of `GET /snapshots/versions` carry a
`progress` object over the prioritised snapshots. Contract:
`.../handoffs/to_frontend/HANDOFF_TO_FRONTEND_stock_report_snapshots_v3_20260926.md`
(v2 added `priority=all` on `GET /items`, v3 fixed `missing_only` hiding fully missing
rows; earlier versions are in `archived/`).

The three Scanner webhooks are `POST /api/v1/location-tracker/webhooks/{stock-demand,
items-processed,stock-demand-deleted}`, all key-authenticated by `X-API-KEY` against
`MANAGER_API_KEY_TO_LOCATION_TRACKER_APP`. All five distinct 401 causes render an identical body
on purpose; the cause is in the log as `stock_webhook.auth_refused`.

## Error handling

Every service goes through `run_service` (`services/run_service.py`), the single error boundary.
A `DomainError` is a refusal and is returned, not raised; anything else is logged with a traceback
and rendered as a generic 500. There are **no FastAPI exception handlers** anywhere.
