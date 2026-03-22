"""Integration tests for random cleaning node (headless — no ROS2 required)."""
import uuid
import pytest

from roomba_cleaning_nav.random_cleaning.state_machine import (
    SessionState,
    request_estop,
    request_start,
    request_stop,
    request_safety_stop,
    request_resume_manual,
    request_clear_estop,
)
from roomba_cleaning_nav.random_cleaning.models import RobotMode, SafetyReason


class TestNodeStartStopEstop:
    """Integration-level tests for start/stop/estop service semantics."""

    def _new_state(self) -> SessionState:
        return SessionState()

    def test_start_stop_cycle(self):
        state = self._new_state()
        ok, _ = request_start(state, 80.0, True, str(uuid.uuid4()))
        assert ok
        assert state.is_cleaning()

        ok, _ = request_stop(state)
        assert ok
        assert state.mode == RobotMode.IDLE

    def test_estop_halts_and_latches(self):
        state = self._new_state()
        request_start(state, 80.0, True, str(uuid.uuid4()))
        ok, _ = request_estop(state)
        assert ok
        assert state.mode == RobotMode.SAFETY_STOPPED
        assert state.latched_safety_stop
        assert state.estop_latched

    def test_estop_blocks_restart(self):
        state = self._new_state()
        request_start(state, 80.0, True, str(uuid.uuid4()))
        request_estop(state)
        ok, msg = request_start(state, 80.0, True, str(uuid.uuid4()))
        assert not ok

    def test_clear_estop_and_resume_cycle(self):
        state = self._new_state()
        request_start(state, 80.0, True, str(uuid.uuid4()))
        request_estop(state)

        # Clear estop
        ok, msg = request_clear_estop(state, velocity_zero=True, sensor_fresh=True)
        assert ok
        assert not state.estop_latched

        # Resume manual
        ok, msg = request_resume_manual(state, str(uuid.uuid4()))
        assert ok
        assert state.mode == RobotMode.CLEANING_FORWARD

    def test_safety_stop_from_sensor_dropout(self):
        state = self._new_state()
        request_start(state, 80.0, True, str(uuid.uuid4()))
        ok, _ = request_safety_stop(state, SafetyReason.SENSOR_DROPOUT)
        assert ok
        assert state.mode == RobotMode.SAFETY_STOPPED
        assert state.safety_reason == SafetyReason.SENSOR_DROPOUT

    def test_safety_stop_no_auto_resume(self):
        state = self._new_state()
        request_start(state, 80.0, True, str(uuid.uuid4()))
        request_safety_stop(state, SafetyReason.SENSOR_DROPOUT)
        # Cannot start again while safety-latched
        ok, _ = request_start(state, 80.0, True, str(uuid.uuid4()))
        assert not ok

    def test_idempotent_start_when_already_cleaning(self):
        state = self._new_state()
        request_start(state, 80.0, True, "s1")
        ok, msg = request_start(state, 80.0, True, "s2")
        assert ok
        assert msg == "already_running_idempotent"
