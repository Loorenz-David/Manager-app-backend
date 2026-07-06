# HANDOFF_TO_FRONTEND_email_templates_20260704

## Metadata

- Handoff ID: `HANDOFF_TO_FRONTEND_email_templates_20260704`
- Created at (UTC): `2026-07-04T00:00:00Z`
- Owner agent: `codex`
- Source plan: `backend/docs/architecture/archives/implementation/PLAN_email_templates_crud_20260704.md`
- Source summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_email_templates_crud_20260704.md`

## Backend delivery context

- What backend implemented: Workspace-scoped email template CRUD with topic and type enums, hard delete, and audit logging.
- API or contract changes: Added `/api/v1/email-templates` routes for create, list, get, update, and delete.
- Feature flags/toggles (if any): None.

## Frontend action required

1. Add a template management UI that calls the five email template endpoints with the enum-backed `topic` and `template_type` fields.
2. Support list filtering by passing a comma-separated `topic` query param such as `task,case`.

## Interface details

- Endpoint(s):
  - `PUT /api/v1/email-templates`
  - `GET /api/v1/email-templates`
  - `GET /api/v1/email-templates/{template_id}`
  - `PATCH /api/v1/email-templates/{template_id}`
  - `DELETE /api/v1/email-templates/{template_id}`
- Request shape:
  - Create: `{"name": str, "subject": str, "content": str, "topic": "task|task_customer_coordination|case|customer", "template_type": "txt|html"}`
  - Update: any subset of the same mutable fields.
- Response shape:
  - Create/get/update: `{"template": {...}}`
  - List: `{"templates_pagination": {"items": [...], "has_more": bool, "limit": int, "offset": int}}`
  - Delete: `{}`
- Error cases:
  - `404` when a template does not exist in the caller workspace.
  - `422` when request payloads are invalid or `topic` query values are unsupported.

## Validation notes

- Backend validation run: model/request parsing, workspace scoping, and migration generation were verified in this implementation turn.
- Suggested frontend validation: enforce non-blank `name`, `subject`, and `content`; constrain topic/type to enum choices.

## Trace links

- Parent plan: `backend/docs/architecture/archives/implementation/PLAN_email_templates_crud_20260704.md`
- Parent summary: `backend/docs/architecture/implemented_summaries/SUMMARY_PLAN_email_templates_crud_20260704.md`
- Related debug plan (optional): none
