"""Default display-priority policy by announcement category. Pure, no I/O.

Higher wins in the active / what's-new ordering. The admin can always override
with an explicit ``display_priority``; this only supplies a sensible default
when none is given, so category severity drives ordering out of the box.
"""

from beyo_manager.domain.app_update_presentations.enums import (
    PresentationCategoryEnum,
)

_BASELINE = 0

_DEFAULT_BY_CATEGORY: dict[PresentationCategoryEnum, int] = {
    PresentationCategoryEnum.ALERT: 300,
    PresentationCategoryEnum.WORKFLOW: 200,
    PresentationCategoryEnum.IMPROVEMENT: 100,
    PresentationCategoryEnum.NEWS: 0,
}


def default_display_priority(category: PresentationCategoryEnum | None) -> int:
    if category is None:
        return _BASELINE
    return _DEFAULT_BY_CATEGORY.get(category, _BASELINE)
