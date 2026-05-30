from types import SimpleNamespace

import pytest

from beyo_manager.domain.cases.enums import CaseLinkEntityTypeEnum
from beyo_manager.domain.cases.serializers import serialize_case_type_entry


@pytest.mark.unit
def test_serialize_case_type_entry_returns_contract_fields():
    case_type = SimpleNamespace(
        client_id="cty_1",
        name="Damage",
        image_url="https://cdn.example.com/case-types/damage.webp",
        description="Issues related to damaged items",
        entity_type=CaseLinkEntityTypeEnum.item,
    )

    serialized = serialize_case_type_entry(case_type)

    assert serialized == {
        "client_id": "cty_1",
        "name": "Damage",
        "image_url": "https://cdn.example.com/case-types/damage.webp",
        "description": "Issues related to damaged items",
        "entity_type": "item",
    }
