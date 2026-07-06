# PLAN_strip_quoted_reply_history_20260706

## Metadata

- Plan ID: `PLAN_strip_quoted_reply_history_20260706`
- Status: `archived`
- Owner agent: `codex`
- Created at (UTC): `2026-07-06T08:00:00Z`
- Last updated at (UTC): `2026-07-06T06:48:39Z`
- Related issue/ticket: `n/a — noticed reviewing emsg_01KWS4FFSTQR3MV74CAZVNXJJ1: inbound text_body contains the full quoted prior message`
- Intention plan: `backend/docs/architecture/under_construction/intention/INTENTION_strip_quoted_reply_history_20260706.md`

## Goal and intent

- Goal: When parsing an inbound email's MIME body, derive a clean version of the message text with the quoted-reply trailer (the "On ... wrote: > ..." block and everything after it) removed, and store it alongside the existing raw body — so previews, future AI features, and any UI reading message content get just the new content, not a duplicate of history already stored as separate `EmailMessage` rows in the thread.
- Business/user intent: Reduce noise in message previews/content and avoid quadratic duplication of conversation history inside `text_body` (each reply currently re-embeds the entire prior chain verbatim), while keeping the original raw body intact for cases where thread linking is incomplete and the quote is the only record of prior context.
- Non-goals:
  - Do NOT backfill or reprocess historical `email_messages` rows in this pass — this plan covers new inbound messages going forward only. Backfill is an explicit candidate for a later addition to this plan (owner has stated more will be added).
  - Do NOT touch outbound message storage (`send_email.py` / `send_email_batch.py`) — outbound bodies are persisted as typed by the composing user, not parsed from raw MIME, and are out of scope here.
  - Do NOT remove or mutate the raw `text_body` column — it remains the fallback/audit source of truth exactly as today.
  - Do NOT attempt HTML-body quote stripping in this pass — scope to `text/plain` (`text_body`) only; `html_body` is stored and displayed as-is.

## Scope

- In scope:
  - Add a quote-stripping step to the inbound MIME parsing path (`smtp_imap/mime_parser.py`), producing a new `text_body_clean` value.
  - Extend `InboundMessage` (`services/infra/email_providers/base.py`) with `text_body_clean: str | None`.
  - Persist it via `process_inbound_messages` (`services/infra/email_providers/message_processor.py`) into a new `email_messages.text_body_clean` column (new Alembic migration).
  - Derive `body_preview` from the clean text when non-empty (falling back to the raw text if stripping yields nothing usable), so thread-list previews stop showing quote noise.
  - Expose `text_body_clean` in `serialize_email_message` (`domain/emails/serializers.py`) additively, alongside existing `text_body`/`html_body`/`body_preview` fields (non-breaking).
  - Choose and add a quote-stripping library dependency (see Clarifications).
- Out of scope:
  - Historical backfill (Non-goals).
  - Outbound message bodies (Non-goals).
  - HTML body stripping (Non-goals).
  - Any frontend change to consume `text_body_clean` — this plan only ships the backend field; frontend adoption is separate.
- Assumptions:
  - `mime_parser.py::MimeParser.parse()` is the single choke point where every inbound message's body is derived (confirmed: `_extract_bodies` is the only body-extraction path, feeding `InboundMessage`), so stripping added there covers both the full-inbox sync (`EMAIL_INBOX_SYNC`) and targeted sync (`EMAIL_SYNC_TARGETED`) task types without duplicating logic.
  - `email_messages.text_body` (`Text`, nullable) and `body_preview` (`String(300)`, nullable) columns are unaffected in shape; only a new nullable column is added, requiring no data migration for existing rows (they'll simply have `text_body_clean = NULL`).

## Clarifications required

None outstanding — all three resolved by the owner on 2026-07-06 (see Decisions log below).

### Decisions log

- **Quote-stripping library:** `email-reply-parser` ([PyPI](https://pypi.org/project/email-reply-parser/)) — small, dependency-free, purpose-built for stripping "On ... wrote:" / "-----Original Message-----" / `>`-quoted patterns across common mail clients. Rejected `talon` (heavier, ML-assisted, more than this need justifies) and hand-rolled regex (brittle across client quoting conventions).
- **`body_preview` derivation:** switches to `text_body_clean`-derived, falling back to raw `text_body` when the clean result is empty/whitespace-only (e.g. an all-quote forward with no new content). This directly fixes the noisy-preview problem that prompted this plan.
- **Column name:** `text_body_clean` (as originally proposed) — short, reads naturally next to `text_body`/`html_body`, and names the field by its content rather than mechanism.

## Acceptance criteria

1. A new inbound message whose raw MIME `text/plain` part contains a quoted-reply trailer (the pattern seen in `emsg_01KWS4FFSTQR3MV74CAZVNXJJ1`: new content followed by `On <date>, <name> <email> wrote:` and `>`-prefixed quoted lines) is stored with `text_body` unchanged (raw, as today) AND `text_body_clean` containing only the new content ("yes yes fast" for that example, with no quoted trailer).
2. A message with no quoted trailer (a fresh, non-reply email) stores `text_body_clean` equal to `text_body` (stripping is a no-op when there's nothing to strip).
3. A message that is entirely quoted content with no new text (e.g. a bare forward) stores a `text_body_clean` that is empty/whitespace, and `body_preview` falls back to the raw text truncation in that case per the Clarification default (never an empty preview when raw text exists).
4. `body_preview` for a normal reply-with-quote message reflects only the new content, not quote noise — directly observable by re-syncing a thread with a message like the reported example and checking the stored `body_preview`.
5. `serialize_email_message` includes `text_body_clean` in its output dict; existing fields (`text_body`, `html_body`, `body_preview`) remain present and unchanged in meaning (aside from `body_preview`'s new derivation source per Clarification decision).
6. The new column is nullable and the migration applies cleanly against the existing `email_messages` table without requiring a backfill; existing rows read back with `text_body_clean = NULL` without error.
7. Both `EMAIL_INBOX_SYNC` (full inbox sync) and `EMAIL_SYNC_TARGETED` (targeted sync) task types populate `text_body_clean` identically, since both flow through the same `MimeParser`/`process_inbound_messages` path.

## Contracts and skills

### Contracts loaded

- `backend/docs/architecture/.../models/*.md` or migration contract (if present): reason — confirm the correct Alembic migration authoring convention for this project (naming, upgrade/downgrade symmetry, nullable-column addition pattern).
- `backend/docs/architecture/.../46_serialization.md`: reason — confirm the convention for additively exposing a new field on an existing serializer without breaking consumers.

### Local extensions loaded

- None expected.

### File read intent — pattern vs. relational

Relational reads already performed and sufficient:
- `services/infra/email_providers/smtp_imap/mime_parser.py` — the exact extraction/construction logic to extend.
- `services/infra/email_providers/base.py` — `InboundMessage` dataclass fields to extend.
- `services/infra/email_providers/message_processor.py` — where `InboundMessage` fields are mapped onto the `EmailMessage` model at persistence time.
- `models/tables/emails/email_message.py` — exact existing column definitions/types to match for the new column.
- `domain/emails/serializers.py::serialize_email_message` — existing field exposure to extend additively.
- `services/commands/emails/send_email.py` — confirmed outbound path is unrelated/out of scope (stores composed text directly, no MIME parsing).

Do NOT pattern-read other MIME/serializer files beyond what's listed — the above is sufficient to implement end-to-end.

### Skill selection

- Primary skill: n/a (a scoped parsing + migration + serializer change).
- Router trigger terms: `MIME parsing, quoted reply stripping, email_reply_parser, migration, serializer field`.
- Excluded alternatives: `talon` — excluded as heavier than needed for the current requirement (see Decisions log).

## Implementation plan

1. **Add dependency.** Add `email-reply-parser` to `requirements.txt` (and `requirements-dev.txt`'s constraint file if pinned versions are tracked there too).
2. **Isolate the stripping logic.** Add `services/infra/email_providers/smtp_imap/quote_stripper.py` with a single function, e.g. `strip_quoted_reply(text: str | None) -> str | None`, wrapping the chosen library so the dependency is isolated to one file (mirrors how `reply_matcher.py` already isolates thread-matching logic in the same directory). Handle `None`/empty input by returning it unchanged.
3. **Extend `InboundMessage`.** In `services/infra/email_providers/base.py`, add `text_body_clean: str | None` next to `text_body`/`html_body`.
4. **Wire into parsing.** In `mime_parser.py::MimeParser.parse()`, after `text_body, html_body = _extract_bodies(parsed)`, compute `text_body_clean = strip_quoted_reply(text_body)`. Update `body_preview` computation to use `(text_body_clean or text_body or "")[:300] or None` (clean-first, raw fallback, per decisions log).
5. **Persist the new field.** In `message_processor.py`, add `text_body_clean=inbound.text_body_clean` to the `EmailMessage(...)` construction alongside the existing `text_body`/`html_body`/`body_preview` mapping.
6. **Add the column.** New Alembic migration adding `email_messages.text_body_clean` (`Text`, `nullable=True`) — mirror the style of the existing migration `dd861a418d9d_add_send_delivery_fields_to_email_.py` for additive nullable-column conventions in this codebase. Add the corresponding `Mapped[str | None]` column to `models/tables/emails/email_message.py`.
7. **Expose in serializer.** Add `"text_body_clean": message.text_body_clean` to `serialize_email_message` in `domain/emails/serializers.py`.
8. **Validate against the reported example.** Manually construct (or replay) a MIME message matching the `emsg_01KWS4FFSTQR3MV74CAZVNXJJ1` shape (new content + "On ... wrote:" + `>`-quoted Swedish text) and confirm `text_body_clean` yields just the new content.

## Risks and mitigations

- Risk: The chosen library's heuristics fail on some quoting styles used by senders in practice (e.g. mobile-client signatures, non-English "wrote:" phrasing — note the example thread includes Swedish quoted content, though the quote-header line itself was in English "On ... wrote:" from a Gmail-style client).
  Mitigation: `text_body` (raw) is always retained unchanged as a fallback; stripping failures degrade gracefully to "no stripping happened" for that message rather than losing data. Treat imperfect stripping as acceptable since the raw source of truth is untouched.
- Risk: Switching `body_preview`'s derivation source changes existing observed behavior for any code/frontend relying on its exact current content.
  Mitigation: Owner accepted this tradeoff explicitly (see Decisions log) — it's the intended fix for the noisy-preview problem that motivated this plan. No further sign-off needed before merging.
- Risk: New dependency (`email-reply-parser`) could have its own maintenance/security posture to consider.
  Mitigation: It's a small, widely-used, MIT-licensed library with minimal transitive dependencies; acceptable risk for the value delivered. Document the choice in the Review log for future reference.
- Risk: Adding a nullable column via migration on a table that may have significant existing row volume could still take a lock/time in production depending on Postgres version and table size.
  Mitigation: Adding a nullable column with no default is a metadata-only change in Postgres (fast, no table rewrite) as long as no `DEFAULT` value requiring a rewrite is specified — ensure the migration does not set a non-null default.

## Validation plan

- Static: `ruff check` + type check on all touched files.
- Unit/manual: feed the exact reported MIME structure (new content "yes yes fast" + English "On Sun, Jul 5, 2026 at 2:34 PM ... wrote:" header + Swedish `>`-quoted body) through `MimeParser.parse()` directly and assert `text_body_clean == "yes yes fast"` (modulo whitespace trimming).
- Migration: run `alembic upgrade head` against a dev DB copy; confirm the new column exists, is nullable, and existing rows are unaffected; run `alembic downgrade -1` to confirm the downgrade path is clean.
- End-to-end: trigger a real (or sandbox) inbound sync for a thread with a known quoted reply and confirm the resulting `EmailMessage` row has both `text_body` (raw, unchanged) and `text_body_clean` (stripped) populated as expected, and that `GET /{thread_id}/messages` returns both fields via the serializer.
- Edge cases: verify a fresh (non-reply) message round-trips `text_body_clean == text_body`, and an all-quote/no-new-content message produces the documented `body_preview` fallback behavior.

## Review log

- `2026-07-06` `claude`: Drafted after the owner noticed inbound `text_body` stores the full quoted-reply history verbatim (e.g. `emsg_01KWS4FFSTQR3MV74CAZVNXJJ1`), which duplicates data already available as separate `EmailMessage` rows in the thread. Confirmed via `mime_parser.py` that no stripping currently happens anywhere in the pipeline. Owner has indicated more scope will be added to this plan later — kept intentionally narrow (new messages only, `text/plain` only, no frontend change) for this first pass.
- `2026-07-06` `david`: Settled all three clarifications — `email-reply-parser` for stripping, `body_preview` derives from clean text with raw fallback, column name stays `text_body_clean`. Plan is unblocked for implementation.
- `2026-07-06` `codex`: Implemented inbound `text_body_clean` derivation and persistence, updated `body_preview` to prefer stripped text with raw fallback, added the nullable `email_messages.text_body_clean` migration, and covered the new behavior with focused email parser/serializer tests.

## Lifecycle transition

- Current state: `archived`
- Next state: `—`
- Transition owner: `codex`
