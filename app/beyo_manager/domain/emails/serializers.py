from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beyo_manager.models.tables.emails.email_connection import EmailConnection
    from beyo_manager.models.tables.emails.email_message import EmailMessage
    from beyo_manager.models.tables.emails.email_template import EmailTemplate
    from beyo_manager.models.tables.emails.email_thread import EmailThread
    from beyo_manager.models.tables.emails.email_thread_topic_preset import EmailThreadTopicPreset
    from beyo_manager.models.tables.emails.email_thread_user_state import EmailThreadUserState


def serialize_email_thread(
    thread: "EmailThread",
    user_state: "EmailThreadUserState | None" = None,
) -> dict:
    if user_state is None:
        is_unread = thread.last_inbound_message_at is not None
    elif thread.last_inbound_message_at is None:
        is_unread = False
    elif user_state.last_read_at is None:
        is_unread = True
    else:
        is_unread = thread.last_inbound_message_at > user_state.last_read_at

    return {
        "client_id": thread.client_id,
        "workspace_id": thread.workspace_id,
        "connection_id": thread.connection_id,
        "entity_type": thread.entity_type,
        "entity_client_id": thread.entity_client_id,
        "major_entity_type": thread.major_entity_type,
        "major_entity_client_id": thread.major_entity_client_id,
        "topic": thread.topic,
        "subject_normalized": thread.subject_normalized,
        "last_message_at": thread.last_message_at.isoformat() if thread.last_message_at else None,
        "last_inbound_message_at": (
            thread.last_inbound_message_at.isoformat() if thread.last_inbound_message_at else None
        ),
        "created_at": thread.created_at.isoformat(),
        "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
        "is_unread": is_unread,
        "user_state": serialize_email_thread_user_state(user_state) if user_state else None,
    }


def serialize_email_thread_user_state(state: "EmailThreadUserState") -> dict:
    return {
        "thread_id": state.thread_id,
        "user_id": state.user_id,
        "last_read_at": state.last_read_at.isoformat() if state.last_read_at else None,
        "muted_at": state.muted_at.isoformat() if state.muted_at else None,
        "archived_at": state.archived_at.isoformat() if state.archived_at else None,
    }


def serialize_email_message(message: "EmailMessage") -> dict:
    return {
        "client_id": message.client_id,
        "workspace_id": message.workspace_id,
        "connection_id": message.connection_id,
        "thread_id": message.thread_id,
        "direction": message.direction,
        "provider_folder": message.provider_folder,
        "provider_uid": message.provider_uid,
        "from_address": message.from_address,
        "from_name": message.from_name,
        "to_addresses_json": message.to_addresses_json,
        "cc_addresses_json": message.cc_addresses_json,
        "bcc_addresses_json": message.bcc_addresses_json,
        "subject": message.subject,
        "text_body": message.text_body,
        "text_body_clean": message.text_body_clean,
        "html_body": message.html_body,
        "body_preview": message.body_preview,
        "rfc_message_id": message.rfc_message_id,
        "in_reply_to": message.in_reply_to,
        "references_json": message.references_json,
        "tracking_token": message.tracking_token,
        "sent_or_received_at": (
            message.sent_or_received_at.isoformat() if message.sent_or_received_at else None
        ),
        "created_by_user_id": message.created_by_user_id,
        "send_attempted_at": message.send_attempted_at.isoformat() if message.send_attempted_at else None,
        "send_error": message.send_error,
        "created_at": message.created_at.isoformat(),
    }


def serialize_email_thread_topic_preset(preset: "EmailThreadTopicPreset") -> dict:
    return {
        "client_id": preset.client_id,
        "label": preset.label,
        "sort_order": preset.sort_order,
    }


def serialize_email_connection(connection: "EmailConnection") -> dict:
    return {
        "client_id": connection.client_id,
        "workspace_id": connection.workspace_id,
        "owner_user_id": connection.owner_user_id,
        "email_address": connection.email_address,
        "display_name": connection.display_name,
        "provider_type": connection.provider_type,
        "status": connection.status,
        "smtp_host": connection.smtp_host,
        "smtp_port": connection.smtp_port,
        "smtp_security": connection.smtp_security,
        "smtp_username": connection.smtp_username,
        "imap_host": connection.imap_host,
        "imap_port": connection.imap_port,
        "imap_security": connection.imap_security,
        "imap_username": connection.imap_username,
        "inbox_folder": connection.inbox_folder,
        "last_error": connection.last_error,
        "created_at": connection.created_at.isoformat(),
        "updated_at": connection.updated_at.isoformat() if connection.updated_at else None,
    }


def serialize_email_template(template: "EmailTemplate") -> dict:
    return {
        "client_id": template.client_id,
        "workspace_id": template.workspace_id,
        "name": template.name,
        "subject": template.subject,
        "content": template.content,
        "topic": template.topic,
        "template_type": template.template_type,
        "created_by_id": template.created_by_id,
        "created_at": template.created_at.isoformat(),
        "updated_by_id": template.updated_by_id,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }
