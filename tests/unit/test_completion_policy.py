"""Unit tests for completion policy."""
import pytest

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    CoverageWorkUnit,
    EndReason,
    SessionState,
    WorkUnitState,
)
from roomba_cleaning_coverage.roomba_cleaning_coverage.completion_policy import (
    apply_terminal_state,
    determine_end_reason,
    is_session_complete,
)


def _units_all_covered(n: int) -> list:
    units = [CoverageWorkUnit(area_m2=1.0) for _ in range(n)]
    for u in units:
        u.state = WorkUnitState.COVERED
    return units


def _units_mixed(covered: int, blocked: int) -> list:
    units = []
    for _ in range(covered):
        u = CoverageWorkUnit(area_m2=1.0)
        u.state = WorkUnitState.COVERED
        units.append(u)
    for _ in range(blocked):
        u = CoverageWorkUnit(area_m2=1.0)
        u.state = WorkUnitState.BLOCKED
        units.append(u)
    return units


class TestIsSessionComplete:
    def test_all_covered_is_complete(self):
        assert is_session_complete(_units_all_covered(3))

    def test_some_uncovered_is_not_complete(self):
        units = _units_all_covered(2)
        units.append(CoverageWorkUnit(area_m2=1.0))  # unvisited
        assert not is_session_complete(units)

    def test_empty_is_complete(self):
        assert is_session_complete([])


class TestDetermineEndReason:
    def test_all_covered_returns_coverage_complete(self):
        units = _units_all_covered(2)
        reason = determine_end_reason(units)
        assert reason == EndReason.COVERAGE_COMPLETE

    def test_interrupted_reason_overrides(self):
        units = _units_all_covered(2)
        reason = determine_end_reason(units, EndReason.OPERATOR_STOP)
        assert reason == EndReason.OPERATOR_STOP

    def test_all_reachable_done_is_coverage_complete(self):
        units = _units_mixed(covered=2, blocked=1)
        reason = determine_end_reason(units)
        assert reason == EndReason.COVERAGE_COMPLETE


class TestApplyTerminalState:
    def test_all_covered_session_completed(self):
        session = AutonomousCleaningSession(state=SessionState.CLEANING)
        units = _units_all_covered(3)
        apply_terminal_state(session, units)
        assert session.state == SessionState.COMPLETED
        assert session.end_reason == EndReason.COVERAGE_COMPLETE
        assert session.covered_ratio == 1.0

    def test_interrupted_session_incomplete(self):
        session = AutonomousCleaningSession(state=SessionState.CLEANING)
        units = [CoverageWorkUnit(area_m2=1.0) for _ in range(3)]  # unvisited
        apply_terminal_state(session, units, EndReason.LOCALIZATION_LOST)
        assert session.state == SessionState.INCOMPLETE
        assert session.end_reason == EndReason.LOCALIZATION_LOST
