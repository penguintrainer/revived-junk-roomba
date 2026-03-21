"""Final result aggregation helpers for action results and status snapshots."""
from __future__ import annotations

from typing import Dict, Any

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    CoverageSnapshot,
    DockAttemptState,
    EndReason,
    SessionState,
)


def build_action_result(
    session: AutonomousCleaningSession,
    snapshot: CoverageSnapshot,
    dock_state: DockAttemptState,
) -> Dict[str, Any]:
    """Build an action result dict suitable for the RunAutonomousCleaning action."""
    return {
        "session_id": session.session_id,
        "final_state": session.state.value,
        "end_reason": session.end_reason.value,
        "covered_ratio": round(session.covered_ratio, 4),
        "covered_area_m2": round(session.covered_area_m2, 4),
        "blocked_area_m2": round(session.blocked_area_m2, 4),
        "remaining_area_m2": round(session.remaining_area_m2, 4),
        "dock_state": dock_state.value,
        "success": session.state == SessionState.COMPLETED,
    }


def is_terminal_state(state: SessionState) -> bool:
    """Return True if the session is in a terminal state."""
    return state in (
        SessionState.COMPLETED,
        SessionState.INCOMPLETE,
        SessionState.SAFETY_STOPPED,
    )


def summarize_end(session: AutonomousCleaningSession) -> str:
    """Return a short human-readable summary of session end."""
    if session.end_reason == EndReason.NONE:
        return f"session in progress: {session.state.value}"
    return f"{session.state.value} ({session.end_reason.value})"
