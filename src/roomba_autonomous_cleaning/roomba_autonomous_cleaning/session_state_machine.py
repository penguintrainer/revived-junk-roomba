"""Session state machine for autonomous cleaning.

Pure transition functions — no side effects.
"""
from __future__ import annotations

from typing import Tuple

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import (
    BATTERY_START_THRESHOLD,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    EndReason,
    InterruptionReason,
    SessionState,
)

TransitionResult = Tuple[bool, str]


def request_start(
    session: AutonomousCleaningSession,
    battery_percent: float,
    localization_ok: bool,
    map_available: bool,
) -> TransitionResult:
    """Try to transition idle → preparing → cleaning.

    Returns (success, message).
    """
    if session.state == SessionState.CLEANING:
        return True, "already_cleaning_idempotent"

    if session.state not in (SessionState.IDLE,):
        return False, f"rejected_invalid_state_{session.state.value}"

    if battery_percent < BATTERY_START_THRESHOLD * 100.0:
        session.end(EndReason.STARTUP_REJECTED, SessionState.IDLE)
        return False, "rejected_low_battery"

    if not localization_ok:
        return False, "rejected_localization_not_ready"

    if not map_available:
        return False, "rejected_map_not_available"

    session.state = SessionState.CLEANING
    return True, "started"


def request_pause(session: AutonomousCleaningSession) -> TransitionResult:
    """Pause an active cleaning session."""
    if session.state != SessionState.CLEANING:
        return False, f"cannot_pause_state_{session.state.value}"
    session.state = SessionState.PAUSED
    return True, "paused"


def request_resume(
    session: AutonomousCleaningSession,
    estop_latched: bool,
) -> TransitionResult:
    """Resume a paused session."""
    if session.state != SessionState.PAUSED:
        return False, f"cannot_resume_state_{session.state.value}"
    if estop_latched:
        return False, "rejected_estop_latched"
    session.state = SessionState.CLEANING
    return True, "resumed"


def request_stop(session: AutonomousCleaningSession) -> TransitionResult:
    """Stop the session with operator_stop reason."""
    if session.state in (SessionState.COMPLETED, SessionState.INCOMPLETE):
        return True, "already_terminated"
    session.end(EndReason.OPERATOR_STOP, SessionState.INCOMPLETE)
    return True, "stopped"


def request_estop(session: AutonomousCleaningSession) -> TransitionResult:
    """Emergency stop — transition to safety_stopped."""
    session.state = SessionState.SAFETY_STOPPED
    return True, "estop_applied"


def mark_completed(session: AutonomousCleaningSession) -> None:
    """Mark session as successfully completed."""
    session.end(EndReason.COVERAGE_COMPLETE, SessionState.COMPLETED)


def mark_incomplete(
    session: AutonomousCleaningSession,
    reason: EndReason,
) -> None:
    """Mark session as incomplete with a specific end reason."""
    session.end(reason, SessionState.INCOMPLETE)


def mark_docking(session: AutonomousCleaningSession) -> None:
    """Transition to docking state."""
    session.state = SessionState.DOCKING
