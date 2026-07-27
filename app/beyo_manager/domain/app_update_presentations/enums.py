from enum import StrEnum


class PresentationStatusEnum(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PresentationTypeEnum(StrEnum):
    MODAL = "modal"
    FULL_SCREEN = "full_screen"
    SLIDE_PAGE = "slide_page"


class PresentationCategoryEnum(StrEnum):
    """Semantic topic of an announcement (rendering-independent).

    Lets the frontend badge/route/filter comms without inspecting content.
    """

    IMPROVEMENT = "improvement"
    WORKFLOW = "workflow"
    NEWS = "news"
    ALERT = "alert"


class AudienceModeEnum(StrEnum):
    ALL_MATCHING = "all_matching"
    SELECTED_USERS_ONLY = "selected_users_only"


class SlideLayoutEnum(StrEnum):
    MEDIA_TOP = "media_top"
    MEDIA_FULL = "media_full"
    TEXT_OVERLAY = "text_overlay"


class SlideMediaTypeEnum(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


class SlideElementTypeEnum(StrEnum):
    """A slide timeline element. Text and media are independent, composable
    elements — text is never subordinate to a media row."""

    MEDIA = "media"
    TEXT = "text"


class SlidePlaybackModeEnum(StrEnum):
    """How a slide's timeline advances."""

    MANUAL = "manual"          # user advances explicitly
    TIMED = "timed"            # advances after duration_ms
    MEDIA_DRIVEN = "media_driven"  # the primary (video) media element drives it


# --- Registry sets used INSIDE validated JSON config (not DB columns) ---
# Kept intentionally small for v1; the frontend maintains the render registry.


class AnimationTypeEnum(StrEnum):
    NONE = "none"
    FADE = "fade"
    FADE_UP = "fade_up"
    FADE_DOWN = "fade_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"


class EasingEnum(StrEnum):
    LINEAR = "linear"
    EASE = "ease"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"


class MediaFitEnum(StrEnum):
    COVER = "cover"
    CONTAIN = "contain"
    FILL = "fill"
    NONE = "none"


class LayoutAnchorEnum(StrEnum):
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


class TextAlignEnum(StrEnum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class TextRoleEnum(StrEnum):
    HEADLINE = "headline"
    SUBHEADLINE = "subheadline"
    BODY = "body"
    CAPTION = "caption"
    OVERLINE = "overline"


class PresentationViewStatusEnum(StrEnum):
    SHOWN = "shown"
    DISMISSED = "dismissed"
    COMPLETED = "completed"


class AppKeyEnum(StrEnum):
    """Canonical application keys.

    These intentionally mirror the existing auth ``app_scope`` claim values
    (see ``services/commands/auth/sign_in_user.py``) so app targeting matches
    the signed, unspoofable scope carried in the JWT.
    """

    MANAGER = "manager"
    WORKER = "worker"
    SELLER = "seller"
    ADMIN = "admin"
