"""Unit tests for state_machine: session lifecycle and state transitions."""
import pytest

from roomba_cleaning_nav.random_cleaning.state_machine import (
    SessionState,
    advance_motion_phase,
    request_clear_estop,
    request_estop,
    request_resume_manual,
    request_start,
    request_stop,
    request_safety_stop,
)
from roomba_cleaning_nav.random_cleaning.models import RobotMode, SafetyReason
from roomba_cleaning_nav.random_cleaning.config import BATTERY_START_THRESHOLD


class TestRequestStart:
    def _state(self, **kwargs):
        s = SessionState(**kwargs)
        return s

    def test_start_from_idle_ok(self):
        s = SessionState()
        ok, msg = request_start(s, battery_percent=50.0, sensor_ok=True, session_id="s1")
        assert ok
        assert msg == "started"
        assert s.mode == RobotMode.CLEANING_FORWARD

    def test_start_idempotent_when_cleaning(self):
        s = SessionState(mode=RobotMode.CLEANING_FORWARD)
        ok, msg = request_start(s, battery_percent=50.0, sensor_ok=True, session_id="s2")
        assert ok
        assert msg == "already_running_idempotent"

    def test_start_rejected_low_battery(self):
        s = SessionState()
        threshold = BATTERY_START_THRESHOLD * 100.0
        ok, msg = request_start(s, battery_percent=threshold - 1, sensor_ok=True, session_id="s3")
        assert not ok
        assert "low_battery" in msg

    def test_start_rejected_sensor_not_ok(self):
        s = SessionState()
        ok, msg = request_start(s, battery_percent=50.0, sensor_ok=False, session_id="s4")
        assert not ok
        assert "sensor" in msg

    def test_start_rejected_when_safety_latched(self):
        s = SessionState(latched_safety_stop=True)
        ok, msg = request_start(s, battery_percent=50.0, sensor_ok=True, session_id="s5")
        assert not ok

    def test_start_rejected_when_estop_latched(self):
        s = SessionState(estop_latched=True)
        ok, msg = request_start(s, battery_percent=50.0, sensor_ok=True, session_id="s6")
        assert not ok

    def test_start_sets_session_id(self):
        s = SessionState()
        request_start(s, battery_percent=50.0, sensor_ok=True, session_id="my-session")
        assert s.session_id == "my-session"


class TestRequestStop:
    def test_stop_from_cleaning(self):
        s = SessionState(mode=RobotMode.CLEANING_FORWARD)
        ok, msg = request_stop(s)
        assert ok
        assert s.mode == RobotMode.IDLE

    def test_stop_from_idle_is_idempotent(self):
        s = SessionState(mode=RobotMode.IDLE)
        ok, msg = request_stop(s)
        assert ok

    def test_stop_clears_session_id(self):
        s = SessionState(mode=RobotMode.CLEANING_TURN, session_id="sess")
        request_stop(s)
        assert s.session_id is None


class TestRequestEstop:
    def test_estop_latches(self):
        s = SessionState(mode=RobotMode.CLEANING_FORWARD)
        ok, msg = request_estop(s)
        assert ok
        assert s.mode == RobotMode.SAFETY_STOPPED
        assert s.latched_safety_stop
        assert s.estop_latched
        assert s.safety_reason == SafetyReason.E_STOP

    def test_estop_from_any_state(self):
        for mode in RobotMode:
            s = SessionState(mode=mode)
            request_estop(s)
            assert s.latched_safety_stop


class TestRequestSafetyStop:
    def test_safety_stop_sets_reason(self):
        s = SessionState(mode=RobotMode.CLEANING_FORWARD)
        ok, msg = request_safety_stop(s, SafetyReason.SENSOR_DROPOUT)
        assert ok
        assert s.mode == RobotMode.SAFETY_STOPPED
        assert s.safety_reason == SafetyReason.SENSOR_DROPOUT
        assert s.latched_safety_stop


class TestRequestResumeManual:
    def test_resume_from_safety_stop_ok(self):
        s = SessionState(mode=RobotMode.SAFETY_STOPPED, latched_safety_stop=True)
        ok, msg = request_resume_manual(s, session_id="new-session")
        assert ok
        assert s.mode == RobotMode.CLEANING_FORWARD
        assert not s.latched_safety_stop

    def test_resume_fails_if_not_latched(self):
        s = SessionState(mode=RobotMode.IDLE)
        ok, msg = request_resume_manual(s, session_id="s")
        assert not ok

    def test_resume_fails_if_estop_still_latched(self):
        s = SessionState(
            mode=RobotMode.SAFETY_STOPPED,
            latched_safety_stop=True,
            estop_latched=True,
        )
        ok, msg = request_resume_manual(s, session_id="s")
        assert not ok
        assert "clear_estop" in msg


class TestRequestClearEstop:
    def test_clear_estop_all_conditions_met(self):
        s = SessionState(estop_latched=True)
        ok, msg = request_clear_estop(s, velocity_zero=True, sensor_fresh=True)
        assert ok
        assert not s.estop_latched

    def test_clear_estop_fails_not_latched(self):
        s = SessionState(estop_latched=False)
        ok, msg = request_clear_estop(s, velocity_zero=True, sensor_fresh=True)
        assert not ok

    def test_clear_estop_fails_velocity_nonzero(self):
        s = SessionState(estop_latched=True)
        ok, msg = request_clear_estop(s, velocity_zero=False, sensor_fresh=True)
        assert not ok
        assert "velocity" in msg

    def test_clear_estop_fails_sensor_not_fresh(self):
        s = SessionState(estop_latched=True)
        ok, msg = request_clear_estop(s, velocity_zero=True, sensor_fresh=False)
        assert not ok
        assert "sensor" in msg


class TestAdvanceMotionPhase:
    def test_forward_to_turn(self):
        s = SessionState(mode=RobotMode.CLEANING_FORWARD)
        advance_motion_phase(s)
        assert s.mode == RobotMode.CLEANING_TURN

    def test_turn_to_forward(self):
        s = SessionState(mode=RobotMode.CLEANING_TURN)
        advance_motion_phase(s)
        assert s.mode == RobotMode.CLEANING_FORWARD

    def test_idle_unchanged(self):
        s = SessionState(mode=RobotMode.IDLE)
        advance_motion_phase(s)
        assert s.mode == RobotMode.IDLE  # no-op for non-cleaning modes
