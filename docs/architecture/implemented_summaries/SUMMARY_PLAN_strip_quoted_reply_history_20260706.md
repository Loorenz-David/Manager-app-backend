# SUMMARY_PLAN_strip_quoted_reply_history_20260706

## Metadata

- Summary ID: `SUMMARY_PLAN_strip_quoted_reply_history_20260706`
- Status: `summarized`
- Owner agent: `codex`
- Created at (UTC): `2026-07-06T06:48:39Z`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_strip_quoted_reply_history_20260706.md`
- Related debug plan (optional): `—`

## What was implemented

- Added inbound quoted-reply stripping behind a dedicated `quote_stripper.py` boundary, with `email-reply-parser` declared as the preferred dependency and a local fallback path for environments where the package has not yet been installed.
- Extended the inbound email pipeline so `MimeParser` derives `text_body_clean`, `InboundMessage` carries it, `process_inbound_messages` persists it, and `serialize_email_message` exposes it additively.
- Switched inbound `body_preview` generation to prefer `text_body_clean` when it contains non-whitespace content and fall back to the raw `text_body` when the clean result is empty.
- Added a nullable `email_messages.text_body_clean` column through a migration that also collapses the current email-related Alembic heads into a single descendant revision.
- Added focused email-core tests covering quote stripping, preview fallback, and serializer exposure.

## Files changed

- `backend/app/requirements.txt`: added `email-reply-parser==0.5.12`.
- `backend/app/beyo_manager/services/infra/email_providers/smtp_imap/quote_stripper.py`: added the isolated quote-stripping boundary.
- `backend/app/beyo_manager/services/infra/email_providers/smtp_imap/mime_parser.py`: now computes `text_body_clean` and derives `body_preview` from clean text first.
- `backend/app/beyo_manager/services/infra/email_providers/base.py`: extended `InboundMessage` with `text_body_clean`.
- `backend/app/beyo_manager/services/infra/email_providers/message_processor.py`: persists `text_body_clean` on inbound saves.
- `backend/app/beyo_manager/models/tables/emails/email_message.py`: added the ORM column and fixed the forward reference for linting.
- `backend/app/beyo_manager/domain/emails/serializers.py`: exposed `text_body_clean`.
- `backend/app/migrations/versions/f6e7d8c9b0a1_add_text_body_clean_to_email_messages.py`: adds the nullable DB column.
- `backend/tests/emails/test_email_core.py`: added parser and serializer coverage for the new behavior.

## Contract adherence

- `backend/architecture/30_migrations.md`: schema change is additive and nullable, with symmetric upgrade/downgrade functions.
- `backend/architecture/46_serialization.md`: serializer change is additive and stays in the domain serializer layer instead of the service layer.
- `backend/skills/_shared/plan_lifecycle_contract.md`: implementation moved from code change to summary + archive workflow in the required order.

## Validation evidence

- `./.venv/bin/python -m pytest ../tests/emails/test_email_core.py`: passed (`9 passed`).
- `./.venv/bin/python -m ruff check beyo_manager/services/infra/email_providers/smtp_imap/quote_stripper.py beyo_manager/services/infra/email_providers/smtp_imap/mime_parser.py beyo_manager/services/infra/email_providers/base.py beyo_manager/services/infra/email_providers/message_processor.py beyo_manager/models/tables/emails/email_message.py beyo_manager/domain/emails/serializers.py ../tests/emails/test_email_core.py`: passed.
- `python3 -m py_compile app/beyo_manager/services/infra/email_providers/smtp_imap/quote_stripper.py app/beyo_manager/services/infra/email_providers/smtp_imap/mime_parser.py app/beyo_manager/services/infra/email_providers/base.py app/beyo_manager/services/infra/email_providers/message_processor.py app/beyo_manager/models/tables/emails/email_message.py app/beyo_manager/domain/emails/serializers.py tests/emails/test_email_core.py app/migrations/versions/f6e7d8c9b0a1_add_text_body_clean_to_email_messages.py`: passed.

## Known gaps or deferred items

- I did not run `alembic upgrade head` against a live dev database in this turn, so the migration is validated structurally and by code review, not by an applied DB run.
- The plan’s linked intention document path (`backend/docs/architecture/under_construction/intention/INTENTION_strip_quoted_reply_history_20260706.md`) does not exist in the repo, so there was no intention-plan progress table to update.
- The summary references a dependency that is now declared in `requirements.txt`, but the package is not installed in the checked-in local `.venv` yet; the wrapper’s fallback kept local tests runnable.

## Handoff notes

- Frontend/API consumers can start reading `text_body_clean` immediately, but no frontend adoption was included in this implementation.

## Lifecycle transition

- Current state: `summarized`
- Next state: `archived`
- Archive target record: `backend/docs/architecture/archives/implementation/PLAN_strip_quoted_reply_history_20260706.md`
