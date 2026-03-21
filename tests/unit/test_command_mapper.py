"""Unit tests for command_mapper: directional mapping and conflict resolution."""
import pytest

from roomba_cleaning_nav.manual_drive.command_mapper import (
    clamp_velocity,
    direction_to_velocity,
    resolve_direction,
)
from roomba_cleaning_nav.manual_drive.models import DirectionInput
from roomba_cleaning_nav.manual_drive.config import (
    ANGULAR_VELOCITY_DEFAULT,
    LINEAR_VELOCITY_DEFAULT,
)


class TestResolveDirection:
    def test_no_input_stops(self):
        assert resolve_direction([]) == DirectionInput.NONE

    def test_none_input_stops(self):
        assert resolve_direction([DirectionInput.NONE]) == DirectionInput.NONE

    def test_forward_only(self):
        assert resolve_direction([DirectionInput.FORWARD]) == DirectionInput.FORWARD

    def test_backward_only(self):
        assert resolve_direction([DirectionInput.BACKWARD]) == DirectionInput.BACKWARD

    def test_rotate_left_only(self):
        assert resolve_direction([DirectionInput.ROTATE_LEFT]) == DirectionInput.ROTATE_LEFT

    def test_rotate_right_only(self):
        assert resolve_direction([DirectionInput.ROTATE_RIGHT]) == DirectionInput.ROTATE_RIGHT

    def test_forward_backward_conflict_stops(self):
        result = resolve_direction([DirectionInput.FORWARD, DirectionInput.BACKWARD])
        assert result == DirectionInput.NONE

    def test_rotate_left_right_conflict_stops(self):
        result = resolve_direction([DirectionInput.ROTATE_LEFT, DirectionInput.ROTATE_RIGHT])
        assert result == DirectionInput.NONE

    def test_rotation_overrides_forward(self):
        result = resolve_direction([DirectionInput.FORWARD, DirectionInput.ROTATE_LEFT])
        assert result == DirectionInput.ROTATE_LEFT

    def test_rotation_overrides_backward(self):
        result = resolve_direction([DirectionInput.BACKWARD, DirectionInput.ROTATE_RIGHT])
        assert result == DirectionInput.ROTATE_RIGHT

    def test_rotate_left_priority_over_rotate_right_when_no_conflict(self):
        # Only one rotation direction present
        result = resolve_direction([DirectionInput.ROTATE_LEFT])
        assert result == DirectionInput.ROTATE_LEFT


class TestDirectionToVelocity:
    def test_none_is_zero(self):
        lin, ang = direction_to_velocity(DirectionInput.NONE)
        assert lin == 0.0
        assert ang == 0.0

    def test_forward(self):
        lin, ang = direction_to_velocity(DirectionInput.FORWARD)
        assert lin == LINEAR_VELOCITY_DEFAULT
        assert ang == 0.0

    def test_backward(self):
        lin, ang = direction_to_velocity(DirectionInput.BACKWARD)
        assert lin == -LINEAR_VELOCITY_DEFAULT
        assert ang == 0.0

    def test_rotate_left(self):
        lin, ang = direction_to_velocity(DirectionInput.ROTATE_LEFT)
        assert lin == 0.0
        assert ang == ANGULAR_VELOCITY_DEFAULT

    def test_rotate_right(self):
        lin, ang = direction_to_velocity(DirectionInput.ROTATE_RIGHT)
        assert lin == 0.0
        assert ang == -ANGULAR_VELOCITY_DEFAULT


class TestClampVelocity:
    def test_within_limits_unchanged(self):
        lin, ang = clamp_velocity(0.10, 0.5)
        assert lin == 0.10
        assert ang == 0.5

    def test_linear_clamped_positive(self):
        lin, ang = clamp_velocity(999.0, 0.0)
        assert lin == LINEAR_VELOCITY_DEFAULT

    def test_linear_clamped_negative(self):
        lin, ang = clamp_velocity(-999.0, 0.0)
        assert lin == -LINEAR_VELOCITY_DEFAULT

    def test_angular_clamped(self):
        _, ang = clamp_velocity(0.0, 999.0)
        assert ang == ANGULAR_VELOCITY_DEFAULT

    def test_zero_unchanged(self):
        lin, ang = clamp_velocity(0.0, 0.0)
        assert lin == 0.0
        assert ang == 0.0
