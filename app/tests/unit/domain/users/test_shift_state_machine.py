import itertools

import pytest

from beyo_manager.domain.users.enums import UserShiftStateEnum
from beyo_manager.domain.users.shift_state_machine import (
    BOUNDARY_MARKERS,
    DURATIONFUL_STATES,
    derive_target_state,
    is_valid_shift_state_transition,
)


@pytest.mark.parametrize(
    ("open_working_count", "open_paused_count", "expected"),
    [
        (working_count, paused_count, expected)
        for working_count, paused_count in itertools.product(range(3), repeat=2)
        for expected in [
            UserShiftStateEnum.WORKING
            if working_count >= 1
            else (
                UserShiftStateEnum.IN_PAUSE
                if paused_count >= 1
                else UserShiftStateEnum.IDLE
            )
        ]
    ],
)
def test_derive_target_state_exhaustive(
    open_working_count: int,
    open_paused_count: int,
    expected: UserShiftStateEnum,
) -> None:
    assert derive_target_state(open_working_count, open_paused_count) is expected


def test_boundary_markers_are_never_derived() -> None:
    derived = {
        derive_target_state(working_count, paused_count)
        for working_count, paused_count in itertools.product(range(3), repeat=2)
    }

    assert derived == DURATIONFUL_STATES
    assert derived.isdisjoint(BOUNDARY_MARKERS)


@pytest.mark.parametrize(
    ("current_state", "target_state"),
    itertools.product(UserShiftStateEnum, repeat=2),
)
def test_transition_validity_matrix(
    current_state: UserShiftStateEnum,
    target_state: UserShiftStateEnum,
) -> None:
    expected = (
        current_state is UserShiftStateEnum.STARTED_SHIFT
        and target_state in DURATIONFUL_STATES
    ) or (
        current_state in DURATIONFUL_STATES
        and (
            target_state in DURATIONFUL_STATES
            or target_state is UserShiftStateEnum.ENDED_SHIFT
        )
    )

    assert is_valid_shift_state_transition(current_state, target_state) is expected
