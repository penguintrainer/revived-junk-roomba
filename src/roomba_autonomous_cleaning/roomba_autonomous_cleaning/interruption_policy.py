"""Interruption policy: pause/resume/stop semantics for autonomous cleaning."""
from __future__ import annotations

from typing import Tuple

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    InterruptionReason,
    SessionState,
)

TransitionResult = Tuple[bool, str]


def can_pause(session: AutonomousCleaningSession) -> bool:
    return session.state == SessionState.CLEANING


def can_resume(
    session: AutonomousCleaningSession,
    estop_latched: bool,
) -> bool:
    return session.state == SessionState.PAUSED and not estop_latched


def can_stop(session: AutonomousCleaningSession) -> bool:
    return session.state not in (SessionState.COMPLETED, SessionState.INCOMPLETE)


def apply_pause(session: AutonomousCleaningSession) -> TransitionResult:
    if not can_pause(session):
        return False, f"cannot_pause_from_{session.state.value}"
    session.state = SessionState.PAUSED
    return True, "paused"


def apply_resume(
    session: AutonomousCleaningSession,
    estop_latched: bool,
) -> TransitionResult:
    if not can_resume(session, estop_latched):
        if estop_latched:
            return False, "rejected_estop_latched"
        return False, f"cannot_resume_from_{session.state.value}"
    session.state = SessionState.CLEANING
    return True, "resumed"


def apply_stop(
    session: AutonomousCleaningSession,
    reason: InterruptionReason = InterruptionReason.OPERATOR_STOP,
) -> TransitionResult:
    if not can_stop(session):
        return True, "already_terminated"
    from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import EndReason
    reason_map = {
        InterruptionReason.OPERATOR_STOP: EndReason.OPERATOR_STOP,
        InterruptionReason.ESTOP: EndReason.ESTOP,
        InterruptionReason.LOCALIZATION_LOST: EndReason.LOCALIZATION_LOST,
    }
    end_reason = reason_map.get(reason, EndReason.OPERATOR_STOP)
    session.state = SessionState.INCOMPLETE
    from roomba_autonomous_cleaning.roomba_autonomous_cleaning.session_state_machine import (
        mark_incomplete,
    )
    mark_incomplete(session, end_reason)
    return True, f"stopped_{reason.value}"
