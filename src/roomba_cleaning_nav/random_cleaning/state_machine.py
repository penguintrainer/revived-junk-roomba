"""Session lifecycle and idempotent start/stop state transitions.

All transition functions are pure — they return (new_state, success, message)
without side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple

from roomba_cleaning_nav.random_cleaning.config import (
    BATTERY_START_THRESHOLD,
)
from roomba_cleaning_nav.random_cleaning.models import (
    RobotMode,
    SafetyReason,
    StartReason,
)


@dataclass
class SessionState:
    """Mutable session state managed by the state machine."""
    mode: RobotMode = RobotMode.IDLE
    latched_safety_stop: bool = False
    safety_reason: SafetyReason = SafetyReason.NONE
    session_id: Optional[str] = None
    start_reason: StartReason = StartReason.USER_REQUEST
    battery_percent: float = 100.0
    estop_latched: bool = False

    def is_cleaning(self) -> bool:
        return self.mode in (RobotMode.CLEANING_FORWARD, RobotMode.CLEANING_TURN)

    def is_stopped(self) -> bool:
        return self.mode in (RobotMode.IDLE, RobotMode.SAFETY_STOPPED)


TransitionResult = Tuple[bool, str]


def request_start(
    state: SessionState,
    battery_percent: float,
    sensor_ok: bool,
    session_id: str,
) -> TransitionResult:
    """Try to start a cleaning session.

    Returns (success, message).
    Idempotent: already-running returns (True, 'already_running_idempotent').
    """
    if state.is_cleaning():
        return True, "already_running_idempotent"

    if state.latched_safety_stop or state.estop_latched:
        return False, "rejected_safety_stop_latched"

    if battery_percent < BATTERY_START_THRESHOLD * 100.0:
        return False, "rejected_low_battery"

    if not sensor_ok:
        return False, "rejected_sensor_not_ready"

    state.mode = RobotMode.CLEANING_FORWARD
    state.session_id = session_id
    state.battery_percent = battery_percent
    state.safety_reason = SafetyReason.NONE
    return True, "started"


def request_stop(state: SessionState) -> TransitionResult:
    """Stop the cleaning session (idempotent)."""
    if state.mode == RobotMode.IDLE:
        return True, "already_stopped"
    state.mode = RobotMode.IDLE
    state.session_id = None
    state.safety_reason = SafetyReason.NONE
    return True, "stopped"


def request_estop(state: SessionState) -> TransitionResult:
    """Emergency stop — latch safety stop immediately."""
    state.mode = RobotMode.SAFETY_STOPPED
    state.latched_safety_stop = True
    state.estop_latched = True
    state.safety_reason = SafetyReason.E_STOP
    return True, "estop_latched"


def request_safety_stop(
    state: SessionState,
    reason: SafetyReason,
) -> TransitionResult:
    """System-initiated safety stop (sensor dropout, low battery, etc.)."""
    state.mode = RobotMode.SAFETY_STOPPED
    state.latched_safety_stop = True
    state.safety_reason = reason
    return True, f"safety_stopped_{reason.value}"


def request_resume_manual(state: SessionState, session_id: str) -> TransitionResult:
    """Resume from safety-stop latch after manual operator re-entry."""
    if not state.latched_safety_stop:
        return False, "not_in_safety_stop"
    if state.estop_latched:
        return False, "estop_still_latched_use_clear_estop"
    state.mode = RobotMode.CLEANING_FORWARD
    state.latched_safety_stop = False
    state.safety_reason = SafetyReason.NONE
    state.session_id = session_id
    return True, "resumed"


def request_clear_estop(
    state: SessionState,
    velocity_zero: bool,
    sensor_fresh: bool,
) -> TransitionResult:
    """Clear the e-stop latch — requires preconditions.

    Preconditions:
    - Robot is stopped (velocity == 0)
    - No active safety fault (other than the latch itself)
    - Sensor freshness restored
    """
    if not state.estop_latched:
        return False, "estop_not_latched"
    if not velocity_zero:
        return False, "rejected_nonzero_velocity"
    if not sensor_fresh:
        return False, "rejected_sensor_not_fresh"
    state.estop_latched = False
    # Keep latched_safety_stop=True; operator must call resume_manual next
    return True, "estop_cleared"


def advance_motion_phase(state: SessionState) -> None:
    """Toggle between forward and turn cleaning phases."""
    if state.mode == RobotMode.CLEANING_FORWARD:
        state.mode = RobotMode.CLEANING_TURN
    elif state.mode == RobotMode.CLEANING_TURN:
        state.mode = RobotMode.CLEANING_FORWARD
