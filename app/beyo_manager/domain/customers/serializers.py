"""Serializers for the customers domain."""

from beyo_manager.domain.items.serializers import serialize_item_list
from beyo_manager.models.tables.customers.customer import Customer
from beyo_manager.models.tables.items.item import Item


def serialize_customer(customer: Customer) -> dict:
    return {
        "client_id": customer.client_id,
        "workspace_id": customer.workspace_id,
        "display_name": customer.display_name,
        "customer_type": customer.customer_type.value,
        "status": customer.status.value,
        "primary_email": customer.primary_email,
        "primary_phone_number": customer.primary_phone_number,
        "primary_email_normalized": customer.primary_email_normalized,
        "primary_phone_number_normalized": customer.primary_phone_number_normalized,
        "address": customer.address,
        "latest_history_record_id": customer.latest_history_record_id,
        "created_at": customer.created_at.isoformat(),
        "created_by_id": customer.created_by_id,
        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
        "updated_by_id": customer.updated_by_id,
    }


def serialize_customer_detail(
    customer: Customer,
    items: list[Item],
    issue_counts: dict[str, int],
) -> dict:
    return {
        **serialize_customer(customer),
        "linked_items": [
            serialize_item_list(item, issue_counts.get(item.client_id, 0))
            for item in items
        ],
    }
