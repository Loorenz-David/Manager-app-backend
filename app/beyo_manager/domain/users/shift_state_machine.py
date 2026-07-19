from beyo_manager.domain.users.enums import UserShiftStateEnum


DURATIONFUL_STATES: frozenset[UserShiftStateEnum] = frozenset(
    {
        UserShiftStateEnum.WORKING,
        UserShiftStateEnum.IN_PAUSE,
        UserShiftStateEnum.IDLE,
    }
)
BOUNDARY_MARKERS: frozenset[UserShiftStateEnum] = frozenset(
    {
        UserShiftStateEnum.STARTED_SHIFT,
        UserShiftStateEnum.ENDED_SHIFT,
    }
)


def derive_target_state(
    open_working_count: int,
    open_paused_count: int,
) -> UserShiftStateEnum:
    if open_working_count >= 1:
        return UserShiftStateEnum.WORKING
    if open_paused_count >= 1:
        return UserShiftStateEnum.IN_PAUSE
    return UserShiftStateEnum.IDLE


def is_valid_shift_state_transition(
    current_state: UserShiftStateEnum,
    target_state: UserShiftStateEnum,
) -> bool:
    if current_state is UserShiftStateEnum.STARTED_SHIFT:
        return target_state in DURATIONFUL_STATES
    if current_state in DURATIONFUL_STATES:
        return target_state in DURATIONFUL_STATES or target_state is UserShiftStateEnum.ENDED_SHIFT
    return False
