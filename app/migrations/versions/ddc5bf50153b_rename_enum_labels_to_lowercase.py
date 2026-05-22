"""Rename all PostgreSQL enum labels from UPPERCASE member names to lowercase values.

Every SAEnum column now uses values_callable so SQLAlchemy persists .value
(e.g. "pending") instead of .name (e.g. "PENDING").  This migration aligns the
existing DB types with that convention, and also corrects the two constraints
that compared against the old uppercase literals.

Revision ID: ddc5bf50153b
Revises: 7d92a90e6282
Create Date: 2026-05-15 12:30:44.696978
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'ddc5bf50153b'
down_revision: Union[str, None] = '7d92a90e6282'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename(type_name: str, old: str, new: str) -> None:
    op.execute(f"ALTER TYPE {type_name} RENAME VALUE '{old}' TO '{new}'")


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # business_task_type_enum
    # ------------------------------------------------------------------ #
    _rename("business_task_type_enum", "RETURN", "return")
    _rename("business_task_type_enum", "PRE_ORDER", "pre_order")
    _rename("business_task_type_enum", "INTERNAL", "internal")

    # ------------------------------------------------------------------ #
    # case_link_entity_type_enum
    # ------------------------------------------------------------------ #
    _rename("case_link_entity_type_enum", "TASK", "task")
    _rename("case_link_entity_type_enum", "CUSTOMER", "customer")

    # ------------------------------------------------------------------ #
    # case_link_role_enum
    # ------------------------------------------------------------------ #
    _rename("case_link_role_enum", "ORIGIN", "origin")
    _rename("case_link_role_enum", "SUBJECT", "subject")
    _rename("case_link_role_enum", "CONTEXT", "context")
    _rename("case_link_role_enum", "ACTOR", "actor")
    _rename("case_link_role_enum", "RESOLUTION", "resolution")

    # ------------------------------------------------------------------ #
    # case_state_enum
    # ------------------------------------------------------------------ #
    _rename("case_state_enum", "OPEN", "open")
    _rename("case_state_enum", "RESOLVING", "resolving")
    _rename("case_state_enum", "RESOLVED", "resolved")

    # ------------------------------------------------------------------ #
    # content_mention_link_entity_type_enum
    # ------------------------------------------------------------------ #
    _rename("content_mention_link_entity_type_enum", "CASE_CONVERSATION_MESSAGE", "case_conversation_message")
    _rename("content_mention_link_entity_type_enum", "TASK_DETAILS_MENTION", "task_details_mention")
    _rename("content_mention_link_entity_type_enum", "TASK_NOTE_MENTION", "task_note_mention")

    # ------------------------------------------------------------------ #
    # customer_history_change_type_enum
    # ------------------------------------------------------------------ #
    _rename("customer_history_change_type_enum", "CREATED", "created")
    _rename("customer_history_change_type_enum", "PROFILE_UPDATED", "profile_updated")
    _rename("customer_history_change_type_enum", "CONTACT_UPDATED", "contact_updated")
    _rename("customer_history_change_type_enum", "ADDRESS_UPDATED", "address_updated")
    _rename("customer_history_change_type_enum", "STATUS_UPDATED", "status_updated")
    _rename("customer_history_change_type_enum", "SOFT_DELETED", "soft_deleted")
    _rename("customer_history_change_type_enum", "RESTORED", "restored")
    _rename("customer_history_change_type_enum", "MERGED", "merged")
    _rename("customer_history_change_type_enum", "REDACTED", "redacted")
    _rename("customer_history_change_type_enum", "ANONYMIZED", "anonymized")
    _rename("customer_history_change_type_enum", "CORRECTION", "correction")
    _rename("customer_history_change_type_enum", "RETRACTION", "retraction")

    # ------------------------------------------------------------------ #
    # customer_status_enum
    # ------------------------------------------------------------------ #
    _rename("customer_status_enum", "ACTIVE", "active")
    _rename("customer_status_enum", "INACTIVE", "inactive")

    # ------------------------------------------------------------------ #
    # customer_type_enum
    # ------------------------------------------------------------------ #
    _rename("customer_type_enum", "PERSON", "person")
    _rename("customer_type_enum", "COMPANY", "company")
    _rename("customer_type_enum", "UNKNOWN", "unknown")

    # ------------------------------------------------------------------ #
    # delayed_scheduler_type_enum
    # ------------------------------------------------------------------ #
    _rename("delayed_scheduler_type_enum", "NOTIFY_TO_CUSTOMER", "notify_to_customer")
    _rename("delayed_scheduler_type_enum", "SEND_REPORT", "send_report")
    _rename("delayed_scheduler_type_enum", "REMINDER", "reminder")
    _rename("delayed_scheduler_type_enum", "BATCH_NOTIFICATION", "batch_notification")

    # ------------------------------------------------------------------ #
    # event_record_state_enum
    # ------------------------------------------------------------------ #
    _rename("event_record_state_enum", "REQUESTED", "requested")
    _rename("event_record_state_enum", "IN_PROGRESS", "in_progress")
    _rename("event_record_state_enum", "COMPLETED", "completed")
    _rename("event_record_state_enum", "FAILED", "failed")

    # ------------------------------------------------------------------ #
    # event_task_origin_source_enum
    # ------------------------------------------------------------------ #
    _rename("event_task_origin_source_enum", "DELAYED_SCHEDULER", "delayed_scheduler")
    _rename("event_task_origin_source_enum", "RECURRING_SCHEDULER", "recurring_scheduler")
    _rename("event_task_origin_source_enum", "INSTANT", "instant")

    # ------------------------------------------------------------------ #
    # execution_task_state_enum
    # ------------------------------------------------------------------ #
    _rename("execution_task_state_enum", "OPEN", "open")
    _rename("execution_task_state_enum", "PENDING", "pending")
    _rename("execution_task_state_enum", "IN_PROGRESS", "in_progress")
    _rename("execution_task_state_enum", "RETRYING", "retrying")
    _rename("execution_task_state_enum", "RETRY_SCHEDULED", "retry_scheduled")
    _rename("execution_task_state_enum", "COMPLETED", "completed")
    _rename("execution_task_state_enum", "FAIL", "fail")
    _rename("execution_task_state_enum", "CANCEL", "cancel")

    # ------------------------------------------------------------------ #
    # image_annotation_type_enum
    # ------------------------------------------------------------------ #
    _rename("image_annotation_type_enum", "DRAW", "draw")
    _rename("image_annotation_type_enum", "ARROW", "arrow")
    _rename("image_annotation_type_enum", "CIRCLE", "circle")
    _rename("image_annotation_type_enum", "RECTANGLE", "rectangle")
    _rename("image_annotation_type_enum", "TEXT", "text")
    _rename("image_annotation_type_enum", "MEASUREMENT", "measurement")
    _rename("image_annotation_type_enum", "HIGHLIGHT", "highlight")

    # ------------------------------------------------------------------ #
    # image_events_error_enum
    # ------------------------------------------------------------------ #
    _rename("image_events_error_enum", "UPLOAD_FAILED", "upload_failed")
    _rename("image_events_error_enum", "INVALID_CONTENT_TYPE", "invalid_content_type")
    _rename("image_events_error_enum", "STORAGE_UNAVAILABLE", "storage_unavailable")
    _rename("image_events_error_enum", "FILE_TOO_LARGE", "file_too_large")
    _rename("image_events_error_enum", "VIRUS_DETECTED", "virus_detected")

    # ------------------------------------------------------------------ #
    # image_events_type_enum
    # ------------------------------------------------------------------ #
    _rename("image_events_type_enum", "UPLOAD_ITEM_IMAGE", "upload_item_image")
    _rename("image_events_type_enum", "UPLOAD_CASE_IMAGE", "upload_case_image")
    _rename("image_events_type_enum", "UPLOAD_MESSAGE_IMAGE", "upload_message_image")

    # ------------------------------------------------------------------ #
    # image_link_entity_type_enum
    # ------------------------------------------------------------------ #
    _rename("image_link_entity_type_enum", "ITEM", "item")
    _rename("image_link_entity_type_enum", "CASE", "case")
    _rename("image_link_entity_type_enum", "CASE_CONVERSATION_MESSAGE", "case_conversation_message")

    # ------------------------------------------------------------------ #
    # image_source_reference_enum
    # ------------------------------------------------------------------ #
    _rename("image_source_reference_enum", "S3_IMAGE_URL", "s3_image_url")
    _rename("image_source_reference_enum", "SHOPIFY_IMAGE_URL", "shopify_image_url")

    # ------------------------------------------------------------------ #
    # image_source_type_enum
    # ------------------------------------------------------------------ #
    _rename("image_source_type_enum", "UPLOADED", "uploaded")
    _rename("image_source_type_enum", "SHOPIFY_SYNC", "shopify_sync")
    _rename("image_source_type_enum", "GENERATED", "generated")

    # ------------------------------------------------------------------ #
    # image_storage_provider_enum
    # ------------------------------------------------------------------ #
    _rename("image_storage_provider_enum", "S3", "s3")
    _rename("image_storage_provider_enum", "SHOPIFY", "shopify")
    _rename("image_storage_provider_enum", "EXTERNAL", "external")

    # ------------------------------------------------------------------ #
    # inventory_warning_tier_enum
    # ------------------------------------------------------------------ #
    _rename("inventory_warning_tier_enum", "NORMAL", "normal")
    _rename("inventory_warning_tier_enum", "LOW_STOCK_WARNING", "low_stock_warning")
    _rename("inventory_warning_tier_enum", "URGENT_REORDER", "urgent_reorder")

    # ------------------------------------------------------------------ #
    # issue_source_enum
    # ------------------------------------------------------------------ #
    _rename("issue_source_enum", "INTERNAL_INSPECTION", "internal_inspection")
    _rename("issue_source_enum", "CUSTOMER", "customer")
    _rename("issue_source_enum", "SUPPLIER", "supplier")
    _rename("issue_source_enum", "IMPORTED", "imported")

    # ------------------------------------------------------------------ #
    # item_currency_enum
    # ------------------------------------------------------------------ #
    _rename("item_currency_enum", "SWEDISH_KRONA", "swedish_krona")
    _rename("item_currency_enum", "DANISH_KRONA", "danish_krona")
    _rename("item_currency_enum", "EURO", "euro")

    # ------------------------------------------------------------------ #
    # item_issue_state_enum
    # ------------------------------------------------------------------ #
    _rename("item_issue_state_enum", "PENDING", "pending")
    _rename("item_issue_state_enum", "FIXING", "fixing")
    _rename("item_issue_state_enum", "BLOCKED", "blocked")
    _rename("item_issue_state_enum", "DEFERRED", "deferred")
    _rename("item_issue_state_enum", "SKIPPED", "skipped")
    _rename("item_issue_state_enum", "RESOLVED", "resolved")

    # ------------------------------------------------------------------ #
    # item_major_category_enum
    # ------------------------------------------------------------------ #
    _rename("item_major_category_enum", "WOOD", "wood")
    _rename("item_major_category_enum", "SEAT", "seat")

    # ------------------------------------------------------------------ #
    # item_state_enum
    # ------------------------------------------------------------------ #
    _rename("item_state_enum", "PENDING", "pending")
    _rename("item_state_enum", "STALLED", "stalled")
    _rename("item_state_enum", "FIXING", "fixing")
    _rename("item_state_enum", "READY", "ready")

    # ------------------------------------------------------------------ #
    # item_upholstery_requirement_source_enum
    # ------------------------------------------------------------------ #
    _rename("item_upholstery_requirement_source_enum", "INVENTORY", "inventory")
    _rename("item_upholstery_requirement_source_enum", "SURPLUS", "surplus")

    # ------------------------------------------------------------------ #
    # item_upholstery_requirement_state_enum
    # ------------------------------------------------------------------ #
    _rename("item_upholstery_requirement_state_enum", "AVAILABLE", "available")
    _rename("item_upholstery_requirement_state_enum", "NEEDS_ORDERING", "needs_ordering")
    _rename("item_upholstery_requirement_state_enum", "ORDERED", "ordered")
    _rename("item_upholstery_requirement_state_enum", "IN_USE", "in_use")
    _rename("item_upholstery_requirement_state_enum", "COMPLETED", "completed")
    _rename("item_upholstery_requirement_state_enum", "FAILED", "failed")

    # ------------------------------------------------------------------ #
    # item_upholstery_source_enum
    # ------------------------------------------------------------------ #
    _rename("item_upholstery_source_enum", "INTERNAL", "internal")
    _rename("item_upholstery_source_enum", "CUSTOMER", "customer")

    # ------------------------------------------------------------------ #
    # pending_upload_status_enum
    # ------------------------------------------------------------------ #
    _rename("pending_upload_status_enum", "PENDING", "pending")
    _rename("pending_upload_status_enum", "CONFIRMED", "confirmed")
    _rename("pending_upload_status_enum", "EXPIRED", "expired")

    # ------------------------------------------------------------------ #
    # recurring_scheduler_interval_value_enum
    # ------------------------------------------------------------------ #
    _rename("recurring_scheduler_interval_value_enum", "SECONDS", "seconds")
    _rename("recurring_scheduler_interval_value_enum", "MINUTES", "minutes")
    _rename("recurring_scheduler_interval_value_enum", "DAYS", "days")
    _rename("recurring_scheduler_interval_value_enum", "MONTHS", "months")

    # ------------------------------------------------------------------ #
    # recurring_scheduler_type_enum
    # ------------------------------------------------------------------ #
    _rename("recurring_scheduler_type_enum", "SEND_REPORT", "send_report")
    _rename("recurring_scheduler_type_enum", "REMINDER", "reminder")
    _rename("recurring_scheduler_type_enum", "PIN_TASK", "pin_task")

    # ------------------------------------------------------------------ #
    # role_name_enum
    # ------------------------------------------------------------------ #
    _rename("role_name_enum", "ADMIN", "admin")
    _rename("role_name_enum", "MEMBER", "member")
    _rename("role_name_enum", "FIELD", "field")

    # ------------------------------------------------------------------ #
    # scheduler_origin_source_enum
    # ------------------------------------------------------------------ #
    _rename("scheduler_origin_source_enum", "COMMAND", "command")
    _rename("scheduler_origin_source_enum", "WORKER", "worker")

    # ------------------------------------------------------------------ #
    # scheduler_state_enum
    # ------------------------------------------------------------------ #
    _rename("scheduler_state_enum", "ACTIVE", "active")
    _rename("scheduler_state_enum", "FIRED", "fired")
    _rename("scheduler_state_enum", "PAUSED", "paused")
    _rename("scheduler_state_enum", "CANCELED", "canceled")
    _rename("scheduler_state_enum", "ERROR", "error")

    # ------------------------------------------------------------------ #
    # sourcing_escalation_policy_enum
    # ------------------------------------------------------------------ #
    _rename("sourcing_escalation_policy_enum", "NONE", "none")
    _rename("sourcing_escalation_policy_enum", "RECOMMEND_REORDER", "recommend_reorder")
    _rename("sourcing_escalation_policy_enum", "ESCALATE_TO_PROCUREMENT", "escalate_to_procurement")

    # ------------------------------------------------------------------ #
    # static_cost_currency_enum
    # ------------------------------------------------------------------ #
    _rename("static_cost_currency_enum", "SWEDISH_KRONA", "swedish_krona")
    _rename("static_cost_currency_enum", "DANISH_KRONA", "danish_krona")
    _rename("static_cost_currency_enum", "EURO", "euro")

    # ------------------------------------------------------------------ #
    # step_event_reason_enum
    # ------------------------------------------------------------------ #
    _rename("step_event_reason_enum", "WAITING_FOR_UPHOLSTERY", "waiting_for_upholstery")
    _rename("step_event_reason_enum", "PAUSE_LUNCH_BREAK", "pause_lunch_break")
    _rename("step_event_reason_enum", "PAUSE_COFFEE_BREAK", "pause_coffee_break")
    _rename("step_event_reason_enum", "PAUSE_ENDED_SHIFT", "pause_ended_shift")
    _rename("step_event_reason_enum", "PAUSE_MEETING", "pause_meeting")
    _rename("step_event_reason_enum", "PAUSE_OTHER_TASK_PRIORITY", "pause_other_task_priority")

    # ------------------------------------------------------------------ #
    # step_state_record_accuracy_measured_by_enum
    # ------------------------------------------------------------------ #
    _rename("step_state_record_accuracy_measured_by_enum", "USER", "user")
    _rename("step_state_record_accuracy_measured_by_enum", "AI", "ai")

    # ------------------------------------------------------------------ #
    # task_domain_event_lifecycle_state_enum
    # ------------------------------------------------------------------ #
    _rename("task_domain_event_lifecycle_state_enum", "RECORDED", "recorded")
    _rename("task_domain_event_lifecycle_state_enum", "SUPERSEDED", "superseded")
    _rename("task_domain_event_lifecycle_state_enum", "COMPENSATED", "compensated")
    _rename("task_domain_event_lifecycle_state_enum", "IGNORED", "ignored")

    # ------------------------------------------------------------------ #
    # task_event_error_code_enum
    # ------------------------------------------------------------------ #
    _rename("task_event_error_code_enum", "VALIDATION_FAILED", "validation_failed")
    _rename("task_event_error_code_enum", "ORCHESTRATION_CONFLICT", "orchestration_conflict")
    _rename("task_event_error_code_enum", "DEPENDENCY_BLOCKED", "dependency_blocked")
    _rename("task_event_error_code_enum", "UNKNOWN", "unknown")

    # ------------------------------------------------------------------ #
    # task_event_type_enum
    # ------------------------------------------------------------------ #
    _rename("task_event_type_enum", "TASK_CREATED", "task_created")
    _rename("task_event_type_enum", "TASK_STATE_CHANGED", "task_state_changed")
    _rename("task_event_type_enum", "TASK_STEP_STATE_CHANGED", "task_step_state_changed")
    _rename("task_event_type_enum", "TASK_ASSIGNMENT_CHANGED", "task_assignment_changed")
    _rename("task_event_type_enum", "TASK_RESOLVED", "task_resolved")

    # ------------------------------------------------------------------ #
    # task_fulfillment_method_enum
    # ------------------------------------------------------------------ #
    _rename("task_fulfillment_method_enum", "PICKUP_AT_STORE", "pickup_at_store")
    _rename("task_fulfillment_method_enum", "DELIVERY", "delivery")

    # ------------------------------------------------------------------ #
    # task_item_location_enum
    # ------------------------------------------------------------------ #
    _rename("task_item_location_enum", "STORE", "store")
    _rename("task_item_location_enum", "CUSTOMER", "customer")

    # ------------------------------------------------------------------ #
    # task_item_role_enum
    # ------------------------------------------------------------------ #
    _rename("task_item_role_enum", "PRIMARY", "primary")
    _rename("task_item_role_enum", "RELATED", "related")

    # ------------------------------------------------------------------ #
    # task_note_type_enum
    # ------------------------------------------------------------------ #
    _rename("task_note_type_enum", "USER_NOTE", "user_note")
    _rename("task_note_type_enum", "SYSTEM_NOTE", "system_note")
    _rename("task_note_type_enum", "CORRECTION_NOTE", "correction_note")
    _rename("task_note_type_enum", "RETRACTION_NOTE", "retraction_note")

    # ------------------------------------------------------------------ #
    # task_priority_enum
    # ------------------------------------------------------------------ #
    _rename("task_priority_enum", "LOW", "low")
    _rename("task_priority_enum", "NORMAL", "normal")
    _rename("task_priority_enum", "HIGH", "high")
    _rename("task_priority_enum", "URGENT", "urgent")

    # ------------------------------------------------------------------ #
    # task_return_method_enum
    # ------------------------------------------------------------------ #
    _rename("task_return_method_enum", "DROP_OFF_BY_CUSTOMER", "drop_off_by_customer")
    _rename("task_return_method_enum", "PICKUP", "pickup")

    # ------------------------------------------------------------------ #
    # task_return_source_enum
    # ------------------------------------------------------------------ #
    _rename("task_return_source_enum", "AFTER_PURCHASE", "after_purchase")
    _rename("task_return_source_enum", "BEFORE_PURCHASE", "before_purchase")
    _rename("task_return_source_enum", "STORE_RETURN", "store_return")

    # ------------------------------------------------------------------ #
    # task_state_enum
    # ------------------------------------------------------------------ #
    _rename("task_state_enum", "PENDING", "pending")
    _rename("task_state_enum", "ASSIGNED", "assigned")
    _rename("task_state_enum", "WORKING", "working")
    _rename("task_state_enum", "STALLED", "stalled")
    _rename("task_state_enum", "READY", "ready")
    _rename("task_state_enum", "RESOLVED", "resolved")
    _rename("task_state_enum", "FAILED", "failed")
    _rename("task_state_enum", "CANCELLED", "cancelled")

    # ------------------------------------------------------------------ #
    # task_step_readiness_status_enum
    # ------------------------------------------------------------------ #
    _rename("task_step_readiness_status_enum", "BLOCKED", "blocked")
    _rename("task_step_readiness_status_enum", "PARTIAL", "partial")
    _rename("task_step_readiness_status_enum", "READY", "ready")

    # ------------------------------------------------------------------ #
    # task_step_state_enum
    # ------------------------------------------------------------------ #
    _rename("task_step_state_enum", "PENDING", "pending")
    _rename("task_step_state_enum", "WORKING", "working")
    _rename("task_step_state_enum", "PAUSED", "paused")
    _rename("task_step_state_enum", "ENDED_SHIFT", "ended_shift")
    _rename("task_step_state_enum", "BLOCKED", "blocked")
    _rename("task_step_state_enum", "COMPLETED", "completed")
    _rename("task_step_state_enum", "SKIPPED", "skipped")
    _rename("task_step_state_enum", "FAILED", "failed")
    _rename("task_step_state_enum", "CANCELLED", "cancelled")

    # ------------------------------------------------------------------ #
    # task_type_enum  (execution task — pre-existing)
    # ------------------------------------------------------------------ #
    _rename("task_type_enum", "NOTIFICATION", "notification")
    _rename("task_type_enum", "UPLOAD_IMAGE", "upload_image")
    _rename("task_type_enum", "DELIVER_WEBHOOK", "deliver_webhook")
    _rename("task_type_enum", "CREATE_NOTIFICATIONS", "create_notifications")
    _rename("task_type_enum", "SEND_PUSH_NOTIFICATION", "send_push_notification")
    _rename("task_type_enum", "DELAYED_NOTIFY_TO_CUSTOMER", "delayed_notify_to_customer")
    _rename("task_type_enum", "DELAYED_SEND_REPORT", "delayed_send_report")
    _rename("task_type_enum", "DELAYED_REMINDER", "delayed_reminder")
    _rename("task_type_enum", "DELAYED_BATCH_NOTIFICATION", "delayed_batch_notification")
    _rename("task_type_enum", "RECURRING_SEND_REPORT", "recurring_send_report")
    _rename("task_type_enum", "RECURRING_REMINDER", "recurring_reminder")
    _rename("task_type_enum", "RECURRING_PIN_TASK", "recurring_pin_task")
    _rename("task_type_enum", "RECORD_VIEW_START", "record_view_start")
    _rename("task_type_enum", "RECORD_VIEW_END", "record_view_end")

    # ------------------------------------------------------------------ #
    # threshold_policy_scope_enum
    # ------------------------------------------------------------------ #
    _rename("threshold_policy_scope_enum", "WORKSPACE_DEFAULT", "workspace_default")
    _rename("threshold_policy_scope_enum", "UPHOLSTERY", "upholstery")

    # ------------------------------------------------------------------ #
    # upholstery_currency_enum
    # ------------------------------------------------------------------ #
    _rename("upholstery_currency_enum", "SWEDISH_KRONA", "swedish_krona")
    _rename("upholstery_currency_enum", "DANISH_KRONA", "danish_krona")
    _rename("upholstery_currency_enum", "EURO", "euro")

    # ------------------------------------------------------------------ #
    # upholstery_inventory_condition_enum
    # ------------------------------------------------------------------ #
    _rename("upholstery_inventory_condition_enum", "AVAILABLE", "available")
    _rename("upholstery_inventory_condition_enum", "LOW_STOCK", "low_stock")
    _rename("upholstery_inventory_condition_enum", "OUT_OF_STOCK", "out_of_stock")

    # ------------------------------------------------------------------ #
    # user_shift_state_enum
    # ------------------------------------------------------------------ #
    _rename("user_shift_state_enum", "STARTED_SHIFT", "started_shift")
    _rename("user_shift_state_enum", "WORKING", "working")
    _rename("user_shift_state_enum", "IN_PAUSE", "in_pause")
    _rename("user_shift_state_enum", "ENDED_SHIFT", "ended_shift")

    # ------------------------------------------------------------------ #
    # Fix check constraint that compared against the old UPPERCASE label
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "ck_utp_upholstery_scope_requires_id",
        "upholstery_inventory_threshold_policies",
        type_="check",
    )
    op.create_check_constraint(
        "ck_utp_upholstery_scope_requires_id",
        "upholstery_inventory_threshold_policies",
        "scope != 'upholstery' OR upholstery_id IS NOT NULL",
    )

    # ------------------------------------------------------------------ #
    # Fix partial index that used the old UPPERCASE label
    # ------------------------------------------------------------------ #
    op.drop_index("uix_task_items_primary_active", table_name="task_items")
    op.create_index(
        "uix_task_items_primary_active",
        "task_items",
        ["workspace_id", "task_id"],
        unique=True,
        postgresql_where=sa.text("role = 'primary' AND removed_at IS NULL"),
    )


def downgrade() -> None:
    # ------------------------------------------------------------------ #
    # Restore partial index with old uppercase label
    # ------------------------------------------------------------------ #
    op.drop_index("uix_task_items_primary_active", table_name="task_items")
    op.create_index(
        "uix_task_items_primary_active",
        "task_items",
        ["workspace_id", "task_id"],
        unique=True,
        postgresql_where=sa.text("role = 'PRIMARY' AND removed_at IS NULL"),
    )

    # ------------------------------------------------------------------ #
    # Restore check constraint with old uppercase label
    # ------------------------------------------------------------------ #
    op.drop_constraint(
        "ck_utp_upholstery_scope_requires_id",
        "upholstery_inventory_threshold_policies",
        type_="check",
    )
    op.create_check_constraint(
        "ck_utp_upholstery_scope_requires_id",
        "upholstery_inventory_threshold_policies",
        "scope != 'UPHOLSTERY' OR upholstery_id IS NOT NULL",
    )

    # Reverse all renames — lowercase back to UPPERCASE
    _rename("user_shift_state_enum", "started_shift", "STARTED_SHIFT")
    _rename("user_shift_state_enum", "working", "WORKING")
    _rename("user_shift_state_enum", "in_pause", "IN_PAUSE")
    _rename("user_shift_state_enum", "ended_shift", "ENDED_SHIFT")

    _rename("upholstery_inventory_condition_enum", "available", "AVAILABLE")
    _rename("upholstery_inventory_condition_enum", "low_stock", "LOW_STOCK")
    _rename("upholstery_inventory_condition_enum", "out_of_stock", "OUT_OF_STOCK")

    _rename("upholstery_currency_enum", "swedish_krona", "SWEDISH_KRONA")
    _rename("upholstery_currency_enum", "danish_krona", "DANISH_KRONA")
    _rename("upholstery_currency_enum", "euro", "EURO")

    _rename("threshold_policy_scope_enum", "workspace_default", "WORKSPACE_DEFAULT")
    _rename("threshold_policy_scope_enum", "upholstery", "UPHOLSTERY")

    _rename("task_type_enum", "notification", "NOTIFICATION")
    _rename("task_type_enum", "upload_image", "UPLOAD_IMAGE")
    _rename("task_type_enum", "deliver_webhook", "DELIVER_WEBHOOK")
    _rename("task_type_enum", "create_notifications", "CREATE_NOTIFICATIONS")
    _rename("task_type_enum", "send_push_notification", "SEND_PUSH_NOTIFICATION")
    _rename("task_type_enum", "delayed_notify_to_customer", "DELAYED_NOTIFY_TO_CUSTOMER")
    _rename("task_type_enum", "delayed_send_report", "DELAYED_SEND_REPORT")
    _rename("task_type_enum", "delayed_reminder", "DELAYED_REMINDER")
    _rename("task_type_enum", "delayed_batch_notification", "DELAYED_BATCH_NOTIFICATION")
    _rename("task_type_enum", "recurring_send_report", "RECURRING_SEND_REPORT")
    _rename("task_type_enum", "recurring_reminder", "RECURRING_REMINDER")
    _rename("task_type_enum", "recurring_pin_task", "RECURRING_PIN_TASK")
    _rename("task_type_enum", "record_view_start", "RECORD_VIEW_START")
    _rename("task_type_enum", "record_view_end", "RECORD_VIEW_END")

    _rename("task_step_state_enum", "pending", "PENDING")
    _rename("task_step_state_enum", "working", "WORKING")
    _rename("task_step_state_enum", "paused", "PAUSED")
    _rename("task_step_state_enum", "ended_shift", "ENDED_SHIFT")
    _rename("task_step_state_enum", "blocked", "BLOCKED")
    _rename("task_step_state_enum", "completed", "COMPLETED")
    _rename("task_step_state_enum", "skipped", "SKIPPED")
    _rename("task_step_state_enum", "failed", "FAILED")
    _rename("task_step_state_enum", "cancelled", "CANCELLED")

    _rename("task_step_readiness_status_enum", "blocked", "BLOCKED")
    _rename("task_step_readiness_status_enum", "partial", "PARTIAL")
    _rename("task_step_readiness_status_enum", "ready", "READY")

    _rename("task_state_enum", "pending", "PENDING")
    _rename("task_state_enum", "assigned", "ASSIGNED")
    _rename("task_state_enum", "working", "WORKING")
    _rename("task_state_enum", "stalled", "STALLED")
    _rename("task_state_enum", "ready", "READY")
    _rename("task_state_enum", "resolved", "RESOLVED")
    _rename("task_state_enum", "failed", "FAILED")
    _rename("task_state_enum", "cancelled", "CANCELLED")

    _rename("task_return_source_enum", "after_purchase", "AFTER_PURCHASE")
    _rename("task_return_source_enum", "before_purchase", "BEFORE_PURCHASE")
    _rename("task_return_source_enum", "store_return", "STORE_RETURN")

    _rename("task_return_method_enum", "drop_off_by_customer", "DROP_OFF_BY_CUSTOMER")
    _rename("task_return_method_enum", "pickup", "PICKUP")

    _rename("task_priority_enum", "low", "LOW")
    _rename("task_priority_enum", "normal", "NORMAL")
    _rename("task_priority_enum", "high", "HIGH")
    _rename("task_priority_enum", "urgent", "URGENT")

    _rename("task_note_type_enum", "user_note", "USER_NOTE")
    _rename("task_note_type_enum", "system_note", "SYSTEM_NOTE")
    _rename("task_note_type_enum", "correction_note", "CORRECTION_NOTE")
    _rename("task_note_type_enum", "retraction_note", "RETRACTION_NOTE")

    _rename("task_item_role_enum", "primary", "PRIMARY")
    _rename("task_item_role_enum", "related", "RELATED")

    _rename("task_item_location_enum", "store", "STORE")
    _rename("task_item_location_enum", "customer", "CUSTOMER")

    _rename("task_fulfillment_method_enum", "pickup_at_store", "PICKUP_AT_STORE")
    _rename("task_fulfillment_method_enum", "delivery", "DELIVERY")

    _rename("task_event_type_enum", "task_created", "TASK_CREATED")
    _rename("task_event_type_enum", "task_state_changed", "TASK_STATE_CHANGED")
    _rename("task_event_type_enum", "task_step_state_changed", "TASK_STEP_STATE_CHANGED")
    _rename("task_event_type_enum", "task_assignment_changed", "TASK_ASSIGNMENT_CHANGED")
    _rename("task_event_type_enum", "task_resolved", "TASK_RESOLVED")

    _rename("task_event_error_code_enum", "validation_failed", "VALIDATION_FAILED")
    _rename("task_event_error_code_enum", "orchestration_conflict", "ORCHESTRATION_CONFLICT")
    _rename("task_event_error_code_enum", "dependency_blocked", "DEPENDENCY_BLOCKED")
    _rename("task_event_error_code_enum", "unknown", "UNKNOWN")

    _rename("task_domain_event_lifecycle_state_enum", "recorded", "RECORDED")
    _rename("task_domain_event_lifecycle_state_enum", "superseded", "SUPERSEDED")
    _rename("task_domain_event_lifecycle_state_enum", "compensated", "COMPENSATED")
    _rename("task_domain_event_lifecycle_state_enum", "ignored", "IGNORED")

    _rename("step_state_record_accuracy_measured_by_enum", "user", "USER")
    _rename("step_state_record_accuracy_measured_by_enum", "ai", "AI")

    _rename("step_event_reason_enum", "waiting_for_upholstery", "WAITING_FOR_UPHOLSTERY")
    _rename("step_event_reason_enum", "pause_lunch_break", "PAUSE_LUNCH_BREAK")
    _rename("step_event_reason_enum", "pause_coffee_break", "PAUSE_COFFEE_BREAK")
    _rename("step_event_reason_enum", "pause_ended_shift", "PAUSE_ENDED_SHIFT")
    _rename("step_event_reason_enum", "pause_meeting", "PAUSE_MEETING")
    _rename("step_event_reason_enum", "pause_other_task_priority", "PAUSE_OTHER_TASK_PRIORITY")

    _rename("static_cost_currency_enum", "swedish_krona", "SWEDISH_KRONA")
    _rename("static_cost_currency_enum", "danish_krona", "DANISH_KRONA")
    _rename("static_cost_currency_enum", "euro", "EURO")

    _rename("sourcing_escalation_policy_enum", "none", "NONE")
    _rename("sourcing_escalation_policy_enum", "recommend_reorder", "RECOMMEND_REORDER")
    _rename("sourcing_escalation_policy_enum", "escalate_to_procurement", "ESCALATE_TO_PROCUREMENT")

    _rename("scheduler_state_enum", "active", "ACTIVE")
    _rename("scheduler_state_enum", "fired", "FIRED")
    _rename("scheduler_state_enum", "paused", "PAUSED")
    _rename("scheduler_state_enum", "canceled", "CANCELED")
    _rename("scheduler_state_enum", "error", "ERROR")

    _rename("scheduler_origin_source_enum", "command", "COMMAND")
    _rename("scheduler_origin_source_enum", "worker", "WORKER")

    _rename("role_name_enum", "admin", "ADMIN")
    _rename("role_name_enum", "member", "MEMBER")
    _rename("role_name_enum", "field", "FIELD")

    _rename("recurring_scheduler_type_enum", "send_report", "SEND_REPORT")
    _rename("recurring_scheduler_type_enum", "reminder", "REMINDER")
    _rename("recurring_scheduler_type_enum", "pin_task", "PIN_TASK")

    _rename("recurring_scheduler_interval_value_enum", "seconds", "SECONDS")
    _rename("recurring_scheduler_interval_value_enum", "minutes", "MINUTES")
    _rename("recurring_scheduler_interval_value_enum", "days", "DAYS")
    _rename("recurring_scheduler_interval_value_enum", "months", "MONTHS")

    _rename("pending_upload_status_enum", "pending", "PENDING")
    _rename("pending_upload_status_enum", "confirmed", "CONFIRMED")
    _rename("pending_upload_status_enum", "expired", "EXPIRED")

    _rename("item_upholstery_source_enum", "internal", "INTERNAL")
    _rename("item_upholstery_source_enum", "customer", "CUSTOMER")

    _rename("item_upholstery_requirement_state_enum", "available", "AVAILABLE")
    _rename("item_upholstery_requirement_state_enum", "needs_ordering", "NEEDS_ORDERING")
    _rename("item_upholstery_requirement_state_enum", "ordered", "ORDERED")
    _rename("item_upholstery_requirement_state_enum", "in_use", "IN_USE")
    _rename("item_upholstery_requirement_state_enum", "completed", "COMPLETED")
    _rename("item_upholstery_requirement_state_enum", "failed", "FAILED")

    _rename("item_upholstery_requirement_source_enum", "inventory", "INVENTORY")
    _rename("item_upholstery_requirement_source_enum", "surplus", "SURPLUS")

    _rename("item_state_enum", "pending", "PENDING")
    _rename("item_state_enum", "stalled", "STALLED")
    _rename("item_state_enum", "fixing", "FIXING")
    _rename("item_state_enum", "ready", "READY")

    _rename("item_major_category_enum", "wood", "WOOD")
    _rename("item_major_category_enum", "seat", "SEAT")

    _rename("item_issue_state_enum", "pending", "PENDING")
    _rename("item_issue_state_enum", "fixing", "FIXING")
    _rename("item_issue_state_enum", "blocked", "BLOCKED")
    _rename("item_issue_state_enum", "deferred", "DEFERRED")
    _rename("item_issue_state_enum", "skipped", "SKIPPED")
    _rename("item_issue_state_enum", "resolved", "RESOLVED")

    _rename("item_currency_enum", "swedish_krona", "SWEDISH_KRONA")
    _rename("item_currency_enum", "danish_krona", "DANISH_KRONA")
    _rename("item_currency_enum", "euro", "EURO")

    _rename("issue_source_enum", "internal_inspection", "INTERNAL_INSPECTION")
    _rename("issue_source_enum", "customer", "CUSTOMER")
    _rename("issue_source_enum", "supplier", "SUPPLIER")
    _rename("issue_source_enum", "imported", "IMPORTED")

    _rename("inventory_warning_tier_enum", "normal", "NORMAL")
    _rename("inventory_warning_tier_enum", "low_stock_warning", "LOW_STOCK_WARNING")
    _rename("inventory_warning_tier_enum", "urgent_reorder", "URGENT_REORDER")

    _rename("image_storage_provider_enum", "s3", "S3")
    _rename("image_storage_provider_enum", "shopify", "SHOPIFY")
    _rename("image_storage_provider_enum", "external", "EXTERNAL")

    _rename("image_source_type_enum", "uploaded", "UPLOADED")
    _rename("image_source_type_enum", "shopify_sync", "SHOPIFY_SYNC")
    _rename("image_source_type_enum", "generated", "GENERATED")

    _rename("image_source_reference_enum", "s3_image_url", "S3_IMAGE_URL")
    _rename("image_source_reference_enum", "shopify_image_url", "SHOPIFY_IMAGE_URL")

    _rename("image_link_entity_type_enum", "item", "ITEM")
    _rename("image_link_entity_type_enum", "case", "CASE")
    _rename("image_link_entity_type_enum", "case_conversation_message", "CASE_CONVERSATION_MESSAGE")

    _rename("image_events_type_enum", "upload_item_image", "UPLOAD_ITEM_IMAGE")
    _rename("image_events_type_enum", "upload_case_image", "UPLOAD_CASE_IMAGE")
    _rename("image_events_type_enum", "upload_message_image", "UPLOAD_MESSAGE_IMAGE")

    _rename("image_events_error_enum", "upload_failed", "UPLOAD_FAILED")
    _rename("image_events_error_enum", "invalid_content_type", "INVALID_CONTENT_TYPE")
    _rename("image_events_error_enum", "storage_unavailable", "STORAGE_UNAVAILABLE")
    _rename("image_events_error_enum", "file_too_large", "FILE_TOO_LARGE")
    _rename("image_events_error_enum", "virus_detected", "VIRUS_DETECTED")

    _rename("image_annotation_type_enum", "draw", "DRAW")
    _rename("image_annotation_type_enum", "arrow", "ARROW")
    _rename("image_annotation_type_enum", "circle", "CIRCLE")
    _rename("image_annotation_type_enum", "rectangle", "RECTANGLE")
    _rename("image_annotation_type_enum", "text", "TEXT")
    _rename("image_annotation_type_enum", "measurement", "MEASUREMENT")
    _rename("image_annotation_type_enum", "highlight", "HIGHLIGHT")

    _rename("execution_task_state_enum", "open", "OPEN")
    _rename("execution_task_state_enum", "pending", "PENDING")
    _rename("execution_task_state_enum", "in_progress", "IN_PROGRESS")
    _rename("execution_task_state_enum", "retrying", "RETRYING")
    _rename("execution_task_state_enum", "retry_scheduled", "RETRY_SCHEDULED")
    _rename("execution_task_state_enum", "completed", "COMPLETED")
    _rename("execution_task_state_enum", "fail", "FAIL")
    _rename("execution_task_state_enum", "cancel", "CANCEL")

    _rename("event_task_origin_source_enum", "delayed_scheduler", "DELAYED_SCHEDULER")
    _rename("event_task_origin_source_enum", "recurring_scheduler", "RECURRING_SCHEDULER")
    _rename("event_task_origin_source_enum", "instant", "INSTANT")

    _rename("event_record_state_enum", "requested", "REQUESTED")
    _rename("event_record_state_enum", "in_progress", "IN_PROGRESS")
    _rename("event_record_state_enum", "completed", "COMPLETED")
    _rename("event_record_state_enum", "failed", "FAILED")

    _rename("delayed_scheduler_type_enum", "notify_to_customer", "NOTIFY_TO_CUSTOMER")
    _rename("delayed_scheduler_type_enum", "send_report", "SEND_REPORT")
    _rename("delayed_scheduler_type_enum", "reminder", "REMINDER")
    _rename("delayed_scheduler_type_enum", "batch_notification", "BATCH_NOTIFICATION")

    _rename("customer_type_enum", "person", "PERSON")
    _rename("customer_type_enum", "company", "COMPANY")
    _rename("customer_type_enum", "unknown", "UNKNOWN")

    _rename("customer_status_enum", "active", "ACTIVE")
    _rename("customer_status_enum", "inactive", "INACTIVE")

    _rename("customer_history_change_type_enum", "created", "CREATED")
    _rename("customer_history_change_type_enum", "profile_updated", "PROFILE_UPDATED")
    _rename("customer_history_change_type_enum", "contact_updated", "CONTACT_UPDATED")
    _rename("customer_history_change_type_enum", "address_updated", "ADDRESS_UPDATED")
    _rename("customer_history_change_type_enum", "status_updated", "STATUS_UPDATED")
    _rename("customer_history_change_type_enum", "soft_deleted", "SOFT_DELETED")
    _rename("customer_history_change_type_enum", "restored", "RESTORED")
    _rename("customer_history_change_type_enum", "merged", "MERGED")
    _rename("customer_history_change_type_enum", "redacted", "REDACTED")
    _rename("customer_history_change_type_enum", "anonymized", "ANONYMIZED")
    _rename("customer_history_change_type_enum", "correction", "CORRECTION")
    _rename("customer_history_change_type_enum", "retraction", "RETRACTION")

    _rename("content_mention_link_entity_type_enum", "case_conversation_message", "CASE_CONVERSATION_MESSAGE")
    _rename("content_mention_link_entity_type_enum", "task_details_mention", "TASK_DETAILS_MENTION")
    _rename("content_mention_link_entity_type_enum", "task_note_mention", "TASK_NOTE_MENTION")

    _rename("case_state_enum", "open", "OPEN")
    _rename("case_state_enum", "resolving", "RESOLVING")
    _rename("case_state_enum", "resolved", "RESOLVED")

    _rename("case_link_role_enum", "origin", "ORIGIN")
    _rename("case_link_role_enum", "subject", "SUBJECT")
    _rename("case_link_role_enum", "context", "CONTEXT")
    _rename("case_link_role_enum", "actor", "ACTOR")
    _rename("case_link_role_enum", "resolution", "RESOLUTION")

    _rename("case_link_entity_type_enum", "task", "TASK")
    _rename("case_link_entity_type_enum", "customer", "CUSTOMER")

    _rename("business_task_type_enum", "return", "RETURN")
    _rename("business_task_type_enum", "pre_order", "PRE_ORDER")
    _rename("business_task_type_enum", "internal", "INTERNAL")
