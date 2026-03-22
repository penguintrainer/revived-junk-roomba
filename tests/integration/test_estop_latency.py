"""Integration test: e-stop latency enforcement."""
import time
import pytest

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    SessionState,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.session_state_machine import (
    request_estop,
    request_start,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.estop_manager import EStopManager
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import ESTOP_MAX_LATENCY_S


class TestEstopLatency:
    def test_estop_state_transition_under_50ms(self):
        session = AutonomousCleaningSession()
        request_start(session, 80.0, True, True)

        t0 = time.monotonic()
        request_estop(session)
        elapsed_s = time.monotonic() - t0

        assert session.state == SessionState.SAFETY_STOPPED
        assert elapsed_s < ESTOP_MAX_LATENCY_S, (
            f"State transition took {elapsed_s*1000:.2f}ms, must be < 50ms"
        )

    def test_estop_manager_latch_is_fast(self):
        mgr = EStopManager()
        t0 = time.monotonic()
        mgr.latch()
        elapsed_s = time.monotonic() - t0
        assert mgr.is_latched
        assert elapsed_s < 0.001  # under 1ms for pure state change


class TestClearEstopPreconditions:
    def test_clear_estop_all_met(self):
        mgr = EStopManager()
        mgr.latch()
        ok, msg = mgr.clear(True, True, True)
        assert ok

    def test_clear_estop_blocked_by_velocity(self):
        mgr = EStopManager()
        mgr.latch()
        ok, msg = mgr.clear(False, True, True)
        assert not ok

    def test_clear_estop_blocked_by_fault(self):
        mgr = EStopManager()
        mgr.latch()
        ok, msg = mgr.clear(True, False, True)
        assert not ok

    def test_clear_estop_blocked_by_perception(self):
        mgr = EStopManager()
        mgr.latch()
        ok, msg = mgr.clear(True, True, False)
        assert not ok

    def test_clear_without_latch_fails(self):
        mgr = EStopManager()
        ok, msg = mgr.clear(True, True, True)
        assert not ok
        assert "not_latched" in msg
