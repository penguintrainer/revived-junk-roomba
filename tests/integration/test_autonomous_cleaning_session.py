"""Integration tests for autonomous cleaning session lifecycle."""
import pytest

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    CoverageWorkUnit,
    DockAttemptState,
    EStopState,
    EndReason,
    LocalizationHealth,
    LocalizationHealthState,
    PerceptionFusionHealth,
    PerceptionFusionState,
    SessionState,
    WorkUnitState,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.session_state_machine import (
    mark_completed,
    mark_incomplete,
    request_estop,
    request_pause,
    request_resume,
    request_start,
    request_stop,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.interruption_policy import (
    apply_pause,
    apply_resume,
    apply_stop,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.estop_manager import EStopManager
from roomba_cleaning_coverage.roomba_cleaning_coverage.coverage_tracker import (
    all_reachable_done,
    mark_unit_covered,
)
from roomba_cleaning_coverage.roomba_cleaning_coverage.completion_policy import (
    apply_terminal_state,
)


class TestFullSessionLifecycle:
    """Test start -> clean -> complete lifecycle."""

    def _session(self) -> AutonomousCleaningSession:
        return AutonomousCleaningSession()

    def _units(self, n: int) -> list:
        return [CoverageWorkUnit(area_m2=1.0) for _ in range(n)]

    def test_start_to_complete(self):
        session = self._session()
        units = self._units(3)
        ok, msg = request_start(session, 80.0, True, True)
        assert ok

        for u in units:
            mark_unit_covered(u)

        apply_terminal_state(session, units)
        assert session.state == SessionState.COMPLETED
        assert session.end_reason == EndReason.COVERAGE_COMPLETE

    def test_pause_resume(self):
        session = self._session()
        request_start(session, 80.0, True, True)
        assert session.state == SessionState.CLEANING

        ok, _ = apply_pause(session)
        assert ok
        assert session.state == SessionState.PAUSED

        ok, _ = apply_resume(session, False)
        assert ok
        assert session.state == SessionState.CLEANING

    def test_operator_stop(self):
        session = self._session()
        request_start(session, 80.0, True, True)
        ok, _ = apply_stop(session)
        assert ok
        assert session.ended_at is not None

    def test_estop_latency_enforcement(self):
        """E-stop should immediately transition to safety_stopped."""
        import time
        session = self._session()
        request_start(session, 80.0, True, True)

        t0 = time.monotonic()
        request_estop(session)
        elapsed_ms = (time.monotonic() - t0) * 1000.0

        assert session.state == SessionState.SAFETY_STOPPED
        # State transition itself must be fast (no async blocking)
        assert elapsed_ms < 50.0  # well under 50ms

    def test_clear_estop_preconditions(self):
        mgr = EStopManager()
        mgr.latch()
        assert mgr.is_latched

        ok, msg = mgr.clear(
            velocity_zero=True,
            no_active_safety_fault=True,
            perception_not_lost=True,
        )
        assert ok
        assert not mgr.is_latched

    def test_clear_estop_fails_when_perception_lost(self):
        mgr = EStopManager()
        mgr.latch()
        ok, msg = mgr.clear(
            velocity_zero=True,
            no_active_safety_fault=True,
            perception_not_lost=False,
        )
        assert not ok
        assert "perception" in msg


class TestLocalizationSupervisorIntegration:
    def test_healthy_to_degraded_to_lost(self):
        from roomba_autonomous_cleaning.roomba_autonomous_cleaning.localization_supervisor import (
            evaluate_localization,
        )
        health = LocalizationHealth()
        # Healthy
        state = evaluate_localization(health, 0.1, 100.0, 100.0)
        assert state == LocalizationHealthState.HEALTHY

        # Covariance high → degraded
        state = evaluate_localization(health, 2.0, 100.0, 100.0)
        assert state == LocalizationHealthState.DEGRADED

        # Scan stale → lost
        state = evaluate_localization(health, 0.1, 5000.0, 100.0)
        assert state == LocalizationHealthState.LOST


class TestLowBatteryDocking:
    def test_session_transitions_to_docking_on_low_battery(self):
        from roomba_autonomous_cleaning.roomba_autonomous_cleaning.session_state_machine import (
            mark_docking,
        )
        session = AutonomousCleaningSession()
        request_start(session, 80.0, True, True)
        mark_docking(session)
        assert session.state == SessionState.DOCKING

    def test_dock_failure_marks_incomplete(self):
        session = AutonomousCleaningSession()
        request_start(session, 80.0, True, True)
        mark_incomplete(session, EndReason.DOCK_FAILURE)
        assert session.state == SessionState.INCOMPLETE
        assert session.end_reason == EndReason.DOCK_FAILURE
