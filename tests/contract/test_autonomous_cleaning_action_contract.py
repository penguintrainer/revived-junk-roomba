"""Contract tests for autonomous cleaning action and status schemas."""
import pytest

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    CoverageWorkUnit,
    DockAttemptState,
    EStopState,
    LocalizationHealth,
    PerceptionFusionHealth,
    SessionState,
    WorkUnitState,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.result_builder import (
    build_action_result,
    is_terminal_state,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.status_publisher import (
    StatusPublisher,
)
from roomba_cleaning_coverage.roomba_cleaning_coverage.coverage_tracker import (
    compute_snapshot,
)

REQUIRED_DIAGNOSTICS_KEYS = {
    "session_state",
    "localization_health",
    "battery_charge_ratio",
    "dock_attempt_state",
    "estop_latched",
}

ALLOWED_SESSION_STATES = {
    "idle", "preparing", "cleaning", "paused",
    "docking", "safety_stopped", "completed", "incomplete",
}


class TestActionResultContract:
    def _make_result(self) -> dict:
        session = AutonomousCleaningSession(state=SessionState.COMPLETED)
        units = [CoverageWorkUnit(area_m2=1.0) for _ in range(3)]
        for u in units:
            u.state = WorkUnitState.COVERED
        snapshot = compute_snapshot(session.session_id, units)
        return build_action_result(session, snapshot, DockAttemptState.IDLE)

    def test_result_has_required_fields(self):
        result = self._make_result()
        for field in ("session_id", "final_state", "end_reason", "covered_ratio",
                      "covered_area_m2", "blocked_area_m2", "remaining_area_m2",
                      "dock_state", "success"):
            assert field in result

    def test_covered_ratio_in_range(self):
        result = self._make_result()
        assert 0.0 <= result["covered_ratio"] <= 1.0

    def test_final_state_is_valid(self):
        result = self._make_result()
        assert result["final_state"] in ALLOWED_SESSION_STATES

    def test_success_true_when_completed(self):
        result = self._make_result()
        assert result["success"] is True


class TestDiagnosticsContract:
    def test_all_required_diagnostics_keys_present(self):
        collected = []
        publisher = StatusPublisher(diag_pub=collected.append)
        session = AutonomousCleaningSession()
        localization = LocalizationHealth()
        dock = DockAttemptState.IDLE
        estop = EStopState()
        perception = PerceptionFusionHealth()
        keys = publisher.publish_diagnostics(
            session, localization, 0.80, dock, estop, perception
        )
        assert REQUIRED_DIAGNOSTICS_KEYS.issubset(set(keys.keys()))

    def test_session_state_is_valid(self):
        collected = []
        publisher = StatusPublisher(diag_pub=collected.append)
        session = AutonomousCleaningSession()
        keys = publisher.publish_diagnostics(
            session, LocalizationHealth(), 1.0,
            DockAttemptState.IDLE, EStopState(), PerceptionFusionHealth()
        )
        assert keys["session_state"] in ALLOWED_SESSION_STATES

    def test_battery_charge_ratio_format(self):
        collected = []
        publisher = StatusPublisher(diag_pub=collected.append)
        session = AutonomousCleaningSession()
        keys = publisher.publish_diagnostics(
            session, LocalizationHealth(), 0.75,
            DockAttemptState.IDLE, EStopState(), PerceptionFusionHealth()
        )
        ratio = float(keys["battery_charge_ratio"])
        assert 0.0 <= ratio <= 1.0

    def test_estop_latched_is_bool_string(self):
        collected = []
        publisher = StatusPublisher(diag_pub=collected.append)
        session = AutonomousCleaningSession()
        estop = EStopState()
        estop.latch()
        keys = publisher.publish_diagnostics(
            session, LocalizationHealth(), 0.5,
            DockAttemptState.IDLE, estop, PerceptionFusionHealth()
        )
        assert keys["estop_latched"] in ("true", "false")


class TestIsTerminalState:
    def test_completed_is_terminal(self):
        assert is_terminal_state(SessionState.COMPLETED)

    def test_incomplete_is_terminal(self):
        assert is_terminal_state(SessionState.INCOMPLETE)

    def test_safety_stopped_is_terminal(self):
        assert is_terminal_state(SessionState.SAFETY_STOPPED)

    def test_cleaning_is_not_terminal(self):
        assert not is_terminal_state(SessionState.CLEANING)

    def test_paused_is_not_terminal(self):
        assert not is_terminal_state(SessionState.PAUSED)
