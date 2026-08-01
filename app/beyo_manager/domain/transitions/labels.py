"""The single code-owned label map for `transition_reason` (criterion 12).

Read paths import from here. Duplicating this map anywhere else is a review finding —
one place, imported.

**Label parity (criterion 5).** Every display value reproduces, byte for byte, what the
catalog rows these transitions replace carry:

    pause_ended_shift          -> "Ended shift"          .../pause_reasons/ended_shift.webp
    pause_other_task_priority  -> "Other task priority"  .../pause_reasons/other_task_priority.webp

**Why the image URLs live in code.** They were never workspace-authored. The bootstrap
phase (`services/commands/bootstrap/phases/seed_pause_reasons.py::_PAUSE_REASONS`) and the
seed migration (`49bd666da846`) carry the same hardcoded literals, so every workspace
holding these rows holds the identical URL. Keeping them here is what makes a system
transition render with its icon and not merely with its name.

Two shapes are served from one map:

* :func:`resolve_transition_reason_label` — the `{name, image_url, pause_type}` lookup
  entry used by the analytics `pause_reasons` map and the embedded shift-state reference.
* :func:`resolve_transition_reason_catalog_reference` — the full published `PauseReason`
  object, for payloads that embed a catalog object rather than a lookup key. A
  transition-typed row has no catalog row to serialize, and emitting `null` there blanks
  a pause label the client previously rendered.
"""

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.domain.transitions.enums import TransitionReasonEnum


_IMAGE_BASE = "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons"

# Keyed by the persisted string (the enum *value*), because that is the key that appears
# in the published `pause_by_reason` map and is what a database row actually carries.
#
# `slug`, `requires_description` and `is_system_managed` reproduce the seeded catalog row
# each member replaces. Neither is behavioural — nothing branches on them.
#
# The reason is schema conformance: `frontend/packages/pause-reasons/src/types.ts` declares
# `slug: z.string()` and `is_system_managed: z.boolean()` **required and non-nullable**, so an
# embedded object missing either fails Zod validation for the whole payload it sits in. Plus
# display parity — a value differing from what the replaced row carried is a difference a client
# could notice.
#
# `is_system_managed` is `False` here because it is `false` on every real row after the phase 4
# retirement. The synthesized shape and the real shape must not diverge; a client comparing them
# would see a distinction that no longer exists anywhere.
#
# NOTE (corrected 2026-08-01): earlier revisions of this comment justified `slug` by pointing at a
# `slug === "pause_ended_shift"` branch in the worker app that chose a state-machine target. **That
# branch no longer exists** — it was removed by the worker-home workstream. The conclusion is
# unchanged and rests on the Zod schema above; only the cited evidence was stale.
_TRANSITION_REASONS: dict[str, dict] = {
    TransitionReasonEnum.SHIFT_ENDED.value: {
        "name": "Ended shift",
        "image_url": f"{_IMAGE_BASE}/ended_shift.webp",
        "pause_type": PauseTypeEnum.BLOCKER.value,
        "slug": "pause_ended_shift",
        "requires_description": False,
        "is_system_managed": False,
    },
    TransitionReasonEnum.OTHER_TASK_PRIORITY.value: {
        "name": "Other task priority",
        "image_url": f"{_IMAGE_BASE}/other_task_priority.webp",
        "pause_type": PauseTypeEnum.BLOCKER.value,
        "slug": "pause_other_task_priority",
        "requires_description": True,
        "is_system_managed": False,
    },
    # No catalog row ever existed for this one — a declaration carries the reason the
    # worker chose, and this member only records where the segment came from. `image_url`
    # is therefore genuinely `None` rather than reproduced, and `slug` is the member's own
    # value because the published schema requires a string. Unreachable from step
    # payloads: nothing writes this member to `step_state_records`.
    TransitionReasonEnum.WORKER_DECLARED_STATE.value: {
        "name": "Declared state",
        "image_url": None,
        "pause_type": PauseTypeEnum.PERSONAL.value,
        "slug": TransitionReasonEnum.WORKER_DECLARED_STATE.value,
        "requires_description": False,
        "is_system_managed": False,
    },
    # `name`, `pause_type`, `slug` and `requires_description` reproduce the retired
    # `pause_case_created` row exactly as it was seeded — see the anchor INSERT in
    # `migrations/versions/fb10ac7fd439_add_pause_reason_id_to_step_state_.py:71-90`
    # ('Case created', BLOCKER, requires_description false).
    #
    # `image_url` is `None` because **that row has none**. It is the one retired row that
    # was never in the bootstrap seed list (`seed_pause_reasons.py:48`) or in the seed
    # migration `49bd666da846`, both of which are where the hardcoded S3 URLs live; the
    # only row that ever existed for this slug is the soft-deleted anchor, inserted with a
    # literal `NULL` image. There is no `pause_reasons/case_created.webp` anywhere in this
    # repository to reproduce. So this is reproduced-as-null, not omitted — the same
    # honest `None` `worker_declared_state` carries above, arrived at differently.
    TransitionReasonEnum.CASE_CREATED.value: {
        "name": "Case created",
        "image_url": None,
        "pause_type": PauseTypeEnum.BLOCKER.value,
        "slug": "pause_case_created",
        "requires_description": False,
        "is_system_managed": False,
    },
}

# The lookup-entry shape, kept explicit so adding a field above cannot silently widen the
# published `pause_reasons` map.
_LABEL_FIELDS = ("name", "image_url", "pause_type")


def is_transition_reason(value: str | None) -> bool:
    """True when `value` is a known `transition_reason`, not a catalog id or legacy slug."""
    return value is not None and value in _TRANSITION_REASONS


def resolve_transition_reason_label(value: str | None) -> dict[str, str | None] | None:
    """Display fields for a `transition_reason`, in the same shape the catalog lookup
    returns (`name` / `image_url` / `pause_type`). `None` for anything unknown — callers
    fall through to their existing catalog resolution, which is what keeps this additive.
    """
    entry = _TRANSITION_REASONS.get(value) if value is not None else None
    if entry is None:
        return None
    return {field: entry[field] for field in _LABEL_FIELDS}


def resolve_transition_reason_catalog_reference(
    value: str | None,
    *,
    created_at: str,
) -> dict | None:
    """The full published `PauseReason` object shape for a `transition_reason`.

    For payloads that embed a catalog object. A system transition references no catalog
    row, so without this the field serializes `null` and a client rendering
    `pause_reason.name` shows an unexplained pause.

    `created_at` is required because the published schema declares it a non-nullable
    string while a code-owned vocabulary has no creation instant of its own; callers pass
    the owning record's timestamp. `client_id` is the transition value — the same key the
    analytics `pause_by_reason` map uses, so a client resolves both kinds alike.
    """
    entry = _TRANSITION_REASONS.get(value) if value is not None else None
    if entry is None:
        return None
    return {
        "client_id": value,
        "name": entry["name"],
        "image_url": entry["image_url"],
        "pause_type": entry["pause_type"],
        "description": None,
        "requires_description": entry["requires_description"],
        "is_system_managed": entry["is_system_managed"],
        "slug": entry["slug"],
        "created_at": created_at,
        "created_by_id": None,
        "updated_at": None,
        "updated_by_id": None,
    }
