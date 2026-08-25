from datetime import datetime, timezone

from beyo_manager.domain.items.enums import (
    ItemUpholsteryRequirementSourceEnum,
    ItemUpholsteryRequirementStateEnum,
    ItemUpholsterySourceEnum,
)
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import (
    ItemUpholsteryRequirement,
)
from scripts.backfill.cleanup_duplicate_item_upholsteries import decide_cleanup


def _iup(client_id: str, created_at: int, *, upholstery_id: str | None = None, requirement_id: str | None = None):
    return ItemUpholstery(
        client_id=client_id,
        workspace_id="ws_test",
        item_id="itm_test",
        upholstery_id=upholstery_id,
        amount_meters=2.5,
        source=ItemUpholsterySourceEnum.INTERNAL,
        active_requirement_id=requirement_id,
        created_at=datetime.fromtimestamp(created_at, tz=timezone.utc),
    )


def _requirement(client_id: str, state: ItemUpholsteryRequirementStateEnum):
    return ItemUpholsteryRequirement(
        client_id=client_id,
        workspace_id="ws_test",
        item_upholstery_id="unused",
        amount_meters=2.5,
        source=ItemUpholsteryRequirementSourceEnum.INVENTORY,
        state=state,
    )


def test_keeps_only_row_with_unfinished_requirement():
    original = _iup("iup_original", 1, upholstery_id="uph_1", requirement_id="iur_1")
    duplicate = _iup("iup_duplicate", 2)
    requirement = _requirement("iur_1", ItemUpholsteryRequirementStateEnum.IN_USE)

    decision = decide_cleanup([original, duplicate], {requirement.client_id: requirement})

    assert decision.keep is original
    assert decision.archive == (duplicate,)
    assert decision.skip_reason is None


def test_skips_when_multiple_rows_own_unfinished_requirements():
    first = _iup("iup_first", 1, upholstery_id="uph_1", requirement_id="iur_1")
    second = _iup("iup_second", 2, upholstery_id="uph_2", requirement_id="iur_2")
    requirements = {
        "iur_1": _requirement("iur_1", ItemUpholsteryRequirementStateEnum.AVAILABLE),
        "iur_2": _requirement("iur_2", ItemUpholsteryRequirementStateEnum.IN_USE),
    }

    decision = decide_cleanup([first, second], requirements)

    assert decision.keep is None
    assert decision.archive == ()
    assert decision.skip_reason is not None


def test_keeps_only_selected_row_when_other_rows_are_deferred():
    selected = _iup("iup_selected", 2, upholstery_id="uph_1")
    deferred = _iup("iup_deferred", 1)

    decision = decide_cleanup([selected, deferred], {})

    assert decision.keep is selected
    assert decision.archive == (deferred,)
