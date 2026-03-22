"""Bounded random-walk motion decision generation.

All functions are pure — no side effects — to enable easy unit testing.
"""
from __future__ import annotations

import math
import random
from typing import Optional

from roomba_cleaning_nav.random_cleaning.config import (
    ANGULAR_VELOCITY_DEFAULT,
    CONTROL_LOOP_PERIOD_S,
    FORWARD_DISTANCE_MAX_M,
    FORWARD_DISTANCE_MIN_M,
    LINEAR_VELOCITY_DEFAULT,
    TURN_ANGLE_MAX_RAD,
    TURN_ANGLE_MIN_RAD,
)
from roomba_cleaning_nav.random_cleaning.models import (
    MotionDecision,
    MotionPhase,
    MotionTrigger,
)


def _forward_duration_ms(
    distance_m: float,
    linear_velocity: float,
) -> int:
    """Convert a forward distance to a control-loop duration in ms."""
    if linear_velocity <= 0:
        return 0
    return max(1, int((distance_m / linear_velocity) * 1000))


def _turn_duration_ms(
    angle_rad: float,
    angular_velocity: float,
) -> int:
    """Convert a rotation angle to a control-loop duration in ms."""
    if angular_velocity <= 0:
        return 0
    return max(1, int((abs(angle_rad) / angular_velocity) * 1000))


def generate_forward_decision(
    session_id: str = "",
    trigger: MotionTrigger = MotionTrigger.PERIODIC,
    linear_velocity: float = LINEAR_VELOCITY_DEFAULT,
    rng: Optional[random.Random] = None,
) -> MotionDecision:
    """Return a forward MotionDecision with a random bounded distance."""
    rng = rng or random.Random()
    distance = rng.uniform(FORWARD_DISTANCE_MIN_M, FORWARD_DISTANCE_MAX_M)
    duration_ms = _forward_duration_ms(distance, linear_velocity)
    return MotionDecision(
        session_id=session_id,
        phase=MotionPhase.FORWARD,
        duration_ms=duration_ms,
        linear_velocity=linear_velocity,
        angular_velocity=0.0,
        trigger=trigger,
    )


def generate_turn_decision(
    session_id: str = "",
    trigger: MotionTrigger = MotionTrigger.PERIODIC,
    angular_velocity: float = ANGULAR_VELOCITY_DEFAULT,
    rng: Optional[random.Random] = None,
) -> MotionDecision:
    """Return a turn MotionDecision with a random bounded angle."""
    rng = rng or random.Random()
    angle = rng.uniform(TURN_ANGLE_MIN_RAD, TURN_ANGLE_MAX_RAD)
    direction = rng.choice([-1.0, 1.0])
    signed_angular = direction * angular_velocity
    duration_ms = _turn_duration_ms(angle, angular_velocity)
    return MotionDecision(
        session_id=session_id,
        phase=MotionPhase.TURN,
        duration_ms=duration_ms,
        linear_velocity=0.0,
        angular_velocity=signed_angular,
        trigger=trigger,
    )


def generate_escape_turn_decision(
    session_id: str = "",
    angular_velocity: float = ANGULAR_VELOCITY_DEFAULT,
    rng: Optional[random.Random] = None,
) -> MotionDecision:
    """Return a 180-degree escape turn decision."""
    rng = rng or random.Random()
    direction = rng.choice([-1.0, 1.0])
    signed_angular = direction * angular_velocity
    angle_rad = math.pi  # exactly 180 degrees
    duration_ms = _turn_duration_ms(angle_rad, angular_velocity)
    return MotionDecision(
        session_id=session_id,
        phase=MotionPhase.ESCAPE_TURN_180,
        duration_ms=duration_ms,
        linear_velocity=0.0,
        angular_velocity=signed_angular,
        trigger=MotionTrigger.NO_PROGRESS,
    )


def generate_bump_recovery_turn(
    session_id: str = "",
    angular_velocity: float = ANGULAR_VELOCITY_DEFAULT,
    rng: Optional[random.Random] = None,
) -> MotionDecision:
    """Return a bump-recovery turn (90-180 degrees away from contact)."""
    rng = rng or random.Random()
    angle = rng.uniform(math.pi / 2, math.pi)
    direction = rng.choice([-1.0, 1.0])
    signed_angular = direction * angular_velocity
    duration_ms = _turn_duration_ms(angle, angular_velocity)
    return MotionDecision(
        session_id=session_id,
        phase=MotionPhase.TURN,
        duration_ms=duration_ms,
        linear_velocity=0.0,
        angular_velocity=signed_angular,
        trigger=MotionTrigger.OBSTACLE_RECOVERY,
    )


def is_decision_expired(decision: MotionDecision, elapsed_ms: float) -> bool:
    """Return True if the motion decision duration has been exceeded."""
    return elapsed_ms >= decision.duration_ms
