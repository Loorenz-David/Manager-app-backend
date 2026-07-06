from beyo_manager.services.infra.email_enrichment.var_parsers.customer_parsers import (
    parse_customer_address,
    parse_customer_email,
    parse_customer_name,
    parse_customer_phone,
)
from beyo_manager.services.infra.email_enrichment.var_parsers.item_parsers import (
    parse_item_article_number,
    parse_item_category,
    parse_item_sku,
)
from beyo_manager.services.infra.email_enrichment.var_parsers.task_parsers import (
    parse_task_fulfillment_method,
    parse_task_scheduled_time,
    parse_task_state,
    parse_task_type,
)


VAR_PARSER_MAP = {
    "customer_name": parse_customer_name,
    "customer_email": parse_customer_email,
    "customer_phone": parse_customer_phone,
    "customer_address": parse_customer_address,
    "task_type": parse_task_type,
    "task_fulfillment_method": parse_task_fulfillment_method,
    "task_state": parse_task_state,
    "task_scheduled_time": parse_task_scheduled_time,
    "item_article_number": parse_item_article_number,
    "item_sku": parse_item_sku,
    "item_category": parse_item_category,
}
