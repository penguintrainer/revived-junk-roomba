"""Unit tests for interruption policy."""
import pytest

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    EndReason,
    InterruptionReason,
    SessionState,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.interruption_policy import (
    apply_pause,
    apply_resume,
    apply_stop,
    can_pause,
    can_resume,
    can_stop,
)


class TestCanPause:
    def test_can_pause_when_cleaning(self):
        s = AutonomousCleaningSession(state=SessionState.CLEANING)
        assert can_pause(s)

    def test_cannot_pause_when_idle(self):
        s = AutonomousCleaningSession(state=SessionState.IDLE)
        assert not can_pause(s)

    def test_cannot_pause_when_paused(self):
        s = AutonomousCleaningSession(state=SessionState.PAUSED)
        assert not can_pause(s)


class TestCanResume:
    def test_can_resume_when_paused_no_estop(self):
        s = AutonomousCleaningSession(state=SessionState.PAUSED)
        assert can_resume(s, False)

    def test_cannot_resume_when_estop(self):
        s = AutonomousCleaningSession(state=SessionState.PAUSED)
        assert not can_resume(s, True)

    def test_cannot_resume_when_not_paused(self):
        s = AutonomousCleaningSession(state=SessionState.CLEANING)
        assert not can_resume(s, False)


class TestCanStop:
    def test_can_stop_when_cleaning(self):
        s = AutonomousCleaningSession(state=SessionState.CLEANING)
        assert can_stop(s)

    def test_cannot_stop_when_completed(self):
        s = AutonomousCleaningSession(state=SessionState.COMPLETED)
        assert not can_stop(s)


class TestApplyPause:
    def test_pause_transitions_state(self):
        s = AutonomousCleaningSession(state=SessionState.CLEANING)
        ok, msg = apply_pause(s)
        assert ok
        assert s.state == SessionState.PAUSED

    def test_pause_from_idle_fails(self):
        s = AutonomousCleaningSession(state=SessionState.IDLE)
        ok, msg = apply_pause(s)
        assert not ok


class TestApplyResume:
    def test_resume_transitions_to_cleaning(self):
        s = AutonomousCleaningSession(state=SessionState.PAUSED)
        ok, msg = apply_resume(s, False)
        assert ok
        assert s.state == SessionState.CLEANING

    def test_resume_blocked_by_estop(self):
        s = AutonomousCleaningSession(state=SessionState.PAUSED)
        ok, msg = apply_resume(s, True)
        assert not ok
        assert "estop" in msg


class TestApplyStop:
    def test_stop_active_session(self):
        s = AutonomousCleaningSession(state=SessionState.CLEANING)
        ok, msg = apply_stop(s)
        assert ok

    def test_stop_already_done(self):
        s = AutonomousCleaningSession(state=SessionState.COMPLETED)
        ok, msg = apply_stop(s)
        assert ok
        assert "already_terminated" in msg
