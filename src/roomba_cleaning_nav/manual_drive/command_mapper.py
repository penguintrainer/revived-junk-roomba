"""Directional mapping and conflicting-input resolution for Joy-Con d-pad.

All functions are pure — no side effects.
"""
from __future__ import annotations

from roomba_cleaning_nav.manual_drive.config import (
    ANGULAR_VELOCITY_DEFAULT,
    LINEAR_VELOCITY_DEFAULT,
)
from roomba_cleaning_nav.manual_drive.models import DirectionInput


# Priority rule: stop > conflicting linear cancel > rotation > linear
_CONFLICT_TABLE: dict[frozenset[DirectionInput], DirectionInput] = {
    frozenset({DirectionInput.FORWARD, DirectionInput.BACKWARD}): DirectionInput.NONE,
    frozenset({DirectionInput.ROTATE_LEFT, DirectionInput.ROTATE_RIGHT}): DirectionInput.NONE,
}


def resolve_direction(inputs: list[DirectionInput]) -> DirectionInput:
    """Apply deterministic conflict-resolution rules to a list of held buttons.

    Priority:
    1. No inputs → NONE (stop)
    2. Conflicting linear inputs (forward + backward) → NONE
    3. Conflicting rotation inputs (left + right) → NONE
    4. Rotation overrides linear when both present
    5. Single input → that input
    """
    active = [d for d in inputs if d != DirectionInput.NONE]

    if not active:
        return DirectionInput.NONE

    active_set = set(active)

    # Conflicting linear or rotation pairs → stop
    if DirectionInput.FORWARD in active_set and DirectionInput.BACKWARD in active_set:
        return DirectionInput.NONE
    if DirectionInput.ROTATE_LEFT in active_set and DirectionInput.ROTATE_RIGHT in active_set:
        return DirectionInput.NONE

    # Rotation takes precedence over linear
    if DirectionInput.ROTATE_LEFT in active_set:
        return DirectionInput.ROTATE_LEFT
    if DirectionInput.ROTATE_RIGHT in active_set:
        return DirectionInput.ROTATE_RIGHT
    if DirectionInput.FORWARD in active_set:
        return DirectionInput.FORWARD
    if DirectionInput.BACKWARD in active_set:
        return DirectionInput.BACKWARD

    return DirectionInput.NONE


def direction_to_velocity(direction: DirectionInput) -> tuple[float, float]:
    """Map a resolved DirectionInput to (linear_x, angular_z) velocities."""
    mapping = {
        DirectionInput.NONE: (0.0, 0.0),
        DirectionInput.FORWARD: (LINEAR_VELOCITY_DEFAULT, 0.0),
        DirectionInput.BACKWARD: (-LINEAR_VELOCITY_DEFAULT, 0.0),
        DirectionInput.ROTATE_LEFT: (0.0, ANGULAR_VELOCITY_DEFAULT),
        DirectionInput.ROTATE_RIGHT: (0.0, -ANGULAR_VELOCITY_DEFAULT),
    }
    return mapping.get(direction, (0.0, 0.0))


def clamp_velocity(linear: float, angular: float) -> tuple[float, float]:
    """Clamp velocity to safe operating ranges."""
    max_linear = LINEAR_VELOCITY_DEFAULT
    max_angular = ANGULAR_VELOCITY_DEFAULT
    clamped_linear = max(-max_linear, min(max_linear, linear))
    clamped_angular = max(-max_angular, min(max_angular, angular))
    return clamped_linear, clamped_angular
