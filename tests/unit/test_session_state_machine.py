"""Unit tests for autonomous cleaning session state machine."""
import pytest

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.session_state_machine import (
    mark_completed,
    mark_docking,
    mark_incomplete,
    request_estop,
    request_pause,
    request_resume,
    request_start,
    request_stop,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    EndReason,
    SessionState,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import (
    BATTERY_START_THRESHOLD,
)


class TestRequestStart:
    def test_start_from_idle(self):
        session = AutonomousCleaningSession()
        ok, msg = request_start(session, 50.0, localization_ok=True, map_available=True)
        assert ok
        assert session.state == SessionState.CLEANING

    def test_start_rejected_low_battery(self):
        session = AutonomousCleaningSession()
        threshold = BATTERY_START_THRESHOLD * 100.0 - 1
        ok, msg = request_start(session, threshold, localization_ok=True, map_available=True)
        assert not ok
        assert "low_battery" in msg

    def test_start_rejected_no_localization(self):
        session = AutonomousCleaningSession()
        ok, msg = request_start(session, 50.0, localization_ok=False, map_available=True)
        assert not ok
        assert "localization" in msg

    def test_start_rejected_no_map(self):
        session = AutonomousCleaningSession()
        ok, msg = request_start(session, 50.0, localization_ok=True, map_available=False)
        assert not ok
        assert "map" in msg

    def test_start_idempotent_when_cleaning(self):
        session = AutonomousCleaningSession(state=SessionState.CLEANING)
        ok, msg = request_start(session, 50.0, True, True)
        assert ok
        assert "idempotent" in msg


class TestRequestPause:
    def test_pause_from_cleaning(self):
        session = AutonomousCleaningSession(state=SessionState.CLEANING)
        ok, msg = request_pause(session)
        assert ok
        assert session.state == SessionState.PAUSED

    def test_pause_from_idle_fails(self):
        session = AutonomousCleaningSession(state=SessionState.IDLE)
        ok, msg = request_pause(session)
        assert not ok


class TestRequestResume:
    def test_resume_from_paused(self):
        session = AutonomousCleaningSession(state=SessionState.PAUSED)
        ok, msg = request_resume(session, estop_latched=False)
        assert ok
        assert session.state == SessionState.CLEANING

    def test_resume_blocked_when_estop_latched(self):
        session = AutonomousCleaningSession(state=SessionState.PAUSED)
        ok, msg = request_resume(session, estop_latched=True)
        assert not ok
        assert "estop" in msg

    def test_resume_from_idle_fails(self):
        session = AutonomousCleaningSession(state=SessionState.IDLE)
        ok, msg = request_resume(session, estop_latched=False)
        assert not ok


class TestRequestStop:
    def test_stop_active_session(self):
        session = AutonomousCleaningSession(state=SessionState.CLEANING)
        ok, msg = request_stop(session)
        assert ok
        assert session.end_reason == EndReason.OPERATOR_STOP
        assert session.ended_at is not None

    def test_stop_already_terminated_idempotent(self):
        session = AutonomousCleaningSession(state=SessionState.COMPLETED)
        ok, msg = request_stop(session)
        assert ok


class TestRequestEstop:
    def test_estop_moves_to_safety_stopped(self):
        session = AutonomousCleaningSession(state=SessionState.CLEANING)
        ok, msg = request_estop(session)
        assert ok
        assert session.state == SessionState.SAFETY_STOPPED


class TestMarkCompleted:
    def test_mark_completed(self):
        session = AutonomousCleaningSession(state=SessionState.CLEANING)
        mark_completed(session)
        assert session.state == SessionState.COMPLETED
        assert session.end_reason == EndReason.COVERAGE_COMPLETE
        assert session.ended_at is not None


class TestMarkIncomplete:
    def test_mark_incomplete(self):
        session = AutonomousCleaningSession(state=SessionState.CLEANING)
        mark_incomplete(session, EndReason.LOCALIZATION_LOST)
        assert session.state == SessionState.INCOMPLETE
        assert session.end_reason == EndReason.LOCALIZATION_LOST
