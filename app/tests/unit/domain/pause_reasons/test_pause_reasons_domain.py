from types import SimpleNamespace

import pytest

from beyo_manager.domain.pause_reasons.guards import can_delete_pause_reason
from beyo_manager.domain.pause_reasons.serializers import serialize_pause_reason
from beyo_manager.domain.pause_reasons.validators import validate_pause_reason_fields
from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum


def test_system_managed_pause_reason_cannot_be_deleted():
    assert can_delete_pause_reason(SimpleNamespace(is_system_managed=True)) is False
    assert can_delete_pause_reason(SimpleNamespace(is_system_managed=False)) is True


@pytest.mark.parametrize(
    "name, description",
    [("", None), ("   ", None), ("x" * 256, None), ("Lunch", "x" * 1025)],
)
def test_pause_reason_fields_reject_invalid_lengths(name, description):
    with pytest.raises(ValueError):
        validate_pause_reason_fields(name, description)


def test_pause_reason_serializer_exposes_public_shape_only():
    instance = SimpleNamespace(
        client_id="par_1",
        name="Lunch",
        image_url=None,
        pause_type=PauseTypeEnum.PERSONAL,
        description=None,
        requires_description=False,
        is_system_managed=False,
        slug=None,
        created_at=__import__("datetime").datetime(2026, 7, 22, tzinfo=__import__("datetime").timezone.utc),
        created_by_id="usr_1",
        updated_at=None,
        updated_by_id=None,
    )

    result = serialize_pause_reason(instance)

    assert result["client_id"] == "par_1"
    assert result["pause_type"] == "personal"
    assert "id" not in result
