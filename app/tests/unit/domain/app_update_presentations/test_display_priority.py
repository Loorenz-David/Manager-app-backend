import pytest

from beyo_manager.domain.app_update_presentations.display_priority import (
    default_display_priority,
)
from beyo_manager.domain.app_update_presentations.enums import (
    PresentationCategoryEnum,
)


@pytest.mark.unit
def test_none_category_is_baseline():
    assert default_display_priority(None) == 0


@pytest.mark.unit
@pytest.mark.parametrize(
    ("category", "expected"),
    [
        (PresentationCategoryEnum.ALERT, 300),
        (PresentationCategoryEnum.WORKFLOW, 200),
        (PresentationCategoryEnum.IMPROVEMENT, 100),
        (PresentationCategoryEnum.NEWS, 0),
    ],
)
def test_category_defaults(category, expected):
    assert default_display_priority(category) == expected


@pytest.mark.unit
def test_alert_outranks_news():
    assert default_display_priority(
        PresentationCategoryEnum.ALERT
    ) > default_display_priority(PresentationCategoryEnum.NEWS)
