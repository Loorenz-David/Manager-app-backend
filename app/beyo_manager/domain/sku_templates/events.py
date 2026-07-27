from enum import StrEnum


class SkuTemplateEvent(StrEnum):
    CREATED = "sku_template:created"
    UPDATED = "sku_template:updated"
    SCALAR_RESERVED = "sku_template:scalar-reserved"

