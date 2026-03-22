"""Completion policy: determine terminal state for a coverage session."""
from __future__ import annotations

from typing import List

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    CoverageWorkUnit,
    EndReason,
    SessionState,
    WorkUnitState,
)
from roomba_cleaning_coverage.roomba_cleaning_coverage.coverage_tracker import (
    all_reachable_done,
    compute_snapshot,
)


def is_session_complete(units: List[CoverageWorkUnit]) -> bool:
    """Return True if all units are covered (no remaining reachable units)."""
    return all(u.state == WorkUnitState.COVERED for u in units)


def determine_end_reason(
    units: List[CoverageWorkUnit],
    interrupted_reason: EndReason = EndReason.NONE,
) -> EndReason:
    """Determine the appropriate end reason given unit states."""
    if interrupted_reason != EndReason.NONE:
        return interrupted_reason
    if is_session_complete(units):
        return EndReason.COVERAGE_COMPLETE
    if all_reachable_done(units):
        # All processed but some blocked/skipped
        return EndReason.COVERAGE_COMPLETE
    return EndReason.INTERNAL_FAULT


def apply_terminal_state(
    session: AutonomousCleaningSession,
    units: List[CoverageWorkUnit],
    interrupted_reason: EndReason = EndReason.NONE,
) -> None:
    """Apply the terminal state and end_reason to the session."""
    end_reason = determine_end_reason(units, interrupted_reason)
    if end_reason == EndReason.COVERAGE_COMPLETE:
        session.end(end_reason, SessionState.COMPLETED)
    else:
        session.end(end_reason, SessionState.INCOMPLETE)
    snapshot = compute_snapshot(session.session_id, units)
    session.covered_ratio = snapshot.covered_ratio
    session.covered_area_m2 = snapshot.covered_area_m2
    session.blocked_area_m2 = snapshot.blocked_area_m2
    session.remaining_area_m2 = snapshot.remaining_area_m2
