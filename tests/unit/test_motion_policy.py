"""Unit tests for motion_policy: random-walk decision generation."""
import math
import random

import pytest

from roomba_cleaning_nav.random_cleaning.motion_policy import (
    generate_forward_decision,
    generate_turn_decision,
    generate_escape_turn_decision,
    generate_bump_recovery_turn,
    is_decision_expired,
)
from roomba_cleaning_nav.random_cleaning.models import MotionPhase, MotionTrigger
from roomba_cleaning_nav.random_cleaning.config import (
    FORWARD_DISTANCE_MIN_M,
    FORWARD_DISTANCE_MAX_M,
    TURN_ANGLE_MIN_RAD,
    TURN_ANGLE_MAX_RAD,
    LINEAR_VELOCITY_DEFAULT,
    ANGULAR_VELOCITY_DEFAULT,
)


class TestGenerateForwardDecision:
    def test_phase_is_forward(self):
        d = generate_forward_decision()
        assert d.phase == MotionPhase.FORWARD

    def test_linear_velocity_default(self):
        d = generate_forward_decision()
        assert d.linear_velocity == LINEAR_VELOCITY_DEFAULT

    def test_angular_velocity_is_zero(self):
        d = generate_forward_decision()
        assert d.angular_velocity == 0.0

    def test_duration_within_expected_range(self):
        rng = random.Random(42)
        d = generate_forward_decision(rng=rng)
        min_ms = int((FORWARD_DISTANCE_MIN_M / LINEAR_VELOCITY_DEFAULT) * 1000)
        max_ms = int((FORWARD_DISTANCE_MAX_M / LINEAR_VELOCITY_DEFAULT) * 1000)
        assert d.duration_ms >= min_ms
        assert d.duration_ms <= max_ms + 1  # allow rounding

    def test_session_id_attached(self):
        d = generate_forward_decision(session_id="test-session")
        assert d.session_id == "test-session"

    def test_trigger_default_periodic(self):
        d = generate_forward_decision()
        assert d.trigger == MotionTrigger.PERIODIC

    def test_duration_positive(self):
        for seed in range(20):
            d = generate_forward_decision(rng=random.Random(seed))
            assert d.duration_ms > 0


class TestGenerateTurnDecision:
    def test_phase_is_turn(self):
        d = generate_turn_decision()
        assert d.phase == MotionPhase.TURN

    def test_linear_velocity_is_zero(self):
        d = generate_turn_decision()
        assert d.linear_velocity == 0.0

    def test_angular_velocity_nonzero(self):
        d = generate_turn_decision()
        assert d.angular_velocity != 0.0

    def test_angular_velocity_bounded(self):
        rng = random.Random(0)
        for _ in range(20):
            d = generate_turn_decision(rng=rng)
            assert abs(d.angular_velocity) == ANGULAR_VELOCITY_DEFAULT

    def test_turn_direction_varies(self):
        directions = set()
        for seed in range(30):
            d = generate_turn_decision(rng=random.Random(seed))
            directions.add(d.angular_velocity > 0)
        assert len(directions) == 2  # both CW and CCW represented

    def test_duration_positive(self):
        for seed in range(10):
            d = generate_turn_decision(rng=random.Random(seed))
            assert d.duration_ms > 0


class TestGenerateEscapeTurn:
    def test_phase_is_escape(self):
        d = generate_escape_turn_decision()
        assert d.phase == MotionPhase.ESCAPE_TURN_180

    def test_trigger_is_no_progress(self):
        d = generate_escape_turn_decision()
        assert d.trigger == MotionTrigger.NO_PROGRESS

    def test_duration_close_to_180_degrees(self):
        d = generate_escape_turn_decision(angular_velocity=1.0)
        expected_ms = int(math.pi * 1000)
        assert abs(d.duration_ms - expected_ms) <= 2

    def test_angular_velocity_nonzero(self):
        d = generate_escape_turn_decision()
        assert d.angular_velocity != 0.0


class TestGenerateBumpRecovery:
    def test_trigger_is_obstacle_recovery(self):
        d = generate_bump_recovery_turn()
        assert d.trigger == MotionTrigger.OBSTACLE_RECOVERY

    def test_angular_velocity_nonzero(self):
        d = generate_bump_recovery_turn()
        assert d.angular_velocity != 0.0

    def test_phase_is_turn(self):
        d = generate_bump_recovery_turn()
        assert d.phase == MotionPhase.TURN


class TestIsDecisionExpired:
    def test_not_expired_before_duration(self):
        d = generate_forward_decision()
        assert not is_decision_expired(d, d.duration_ms - 1)

    def test_expired_at_duration(self):
        d = generate_forward_decision()
        assert is_decision_expired(d, d.duration_ms)

    def test_expired_after_duration(self):
        d = generate_forward_decision()
        assert is_decision_expired(d, d.duration_ms + 100)
