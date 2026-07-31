from types import SimpleNamespace

import pytest

from beyo_manager.domain.pause_reasons.serializers import serialize_pause_reason
from beyo_manager.domain.pause_reasons.validators import validate_pause_reason_fields
from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum


def test_no_delete_guard_module_survives():
    """`can_delete_pause_reason` blocked deletion of rows the backend resolved by slug.

    Nothing resolves a pause reason by slug any more, so there is no row left to protect and the
    guard is gone. Every row in this catalog is workspace data the manager owns outright.

    Asserted rather than merely deleted: a guard that reappears would silently re-block deletion of
    a row a manager is now entitled to remove.
    """
    with pytest.raises(ModuleNotFoundError):
        __import__("beyo_manager.domain.pause_reasons.guards")


def test_serializer_still_publishes_the_inert_contract_fields():
    """`slug` and `is_system_managed` carry no behaviour, and must still be serialized.

    `frontend/packages/pause-reasons/src/types.ts` declares both required and non-nullable
    (`slug: z.string()`, `is_system_managed: z.boolean()`), so dropping either fails Zod validation
    on every pause-reasons response — not merely on a branch that reads it.
    """
    result = serialize_pause_reason(
        SimpleNamespace(
            client_id="par_1",
            name="Lunch",
            image_url=None,
            pause_type=PauseTypeEnum.PERSONAL,
            description=None,
            requires_description=False,
            is_system_managed=False,
            slug="pause_lunch_break",
            created_at=__import__("datetime").datetime(2026, 7, 22, tzinfo=__import__("datetime").timezone.utc),
            created_by_id="usr_1",
            updated_at=None,
            updated_by_id=None,
        )
    )

    assert result["slug"] == "pause_lunch_break"
    assert result["is_system_managed"] is False


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
