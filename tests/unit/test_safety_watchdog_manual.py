"""Unit tests for manual drive safety_watchdog."""
import pytest

from roomba_cleaning_nav.manual_drive.safety_watchdog import (
    SafetyLatch,
    WatchdogDecision,
    check_clear_estop_preconditions,
    evaluate_cliff,
    evaluate_estop_latch,
    evaluate_link_health,
    evaluate_serial,
)
from roomba_cleaning_nav.manual_drive.models import SafetyFault
from roomba_cleaning_nav.manual_drive.config import LINK_LOSS_TIMEOUT_S


class TestEvaluateLinkHealth:
    def test_fresh_link_continues(self):
        timeout_ms = LINK_LOSS_TIMEOUT_S * 1000.0
        result = evaluate_link_health(link_age_ms=timeout_ms - 100.0)
        assert result == WatchdogDecision.CONTINUE

    def test_stale_link_stops(self):
        timeout_ms = LINK_LOSS_TIMEOUT_S * 1000.0
        result = evaluate_link_health(link_age_ms=timeout_ms + 1.0)
        assert result == WatchdogDecision.LINK_LOSS_STOP

    def test_exactly_at_threshold_continues(self):
        timeout_ms = LINK_LOSS_TIMEOUT_S * 1000.0
        result = evaluate_link_health(link_age_ms=timeout_ms)
        # exactly at limit: not > threshold, so CONTINUE
        assert result == WatchdogDecision.CONTINUE


class TestEvaluateCliff:
    def test_no_cliff_continues(self):
        assert evaluate_cliff(False) == WatchdogDecision.CONTINUE

    def test_cliff_stops(self):
        assert evaluate_cliff(True) == WatchdogDecision.CLIFF_STOP


class TestEvaluateSerial:
    def test_ok_continues(self):
        assert evaluate_serial(True) == WatchdogDecision.CONTINUE

    def test_fault_stops(self):
        assert evaluate_serial(False) == WatchdogDecision.SAFETY_STOP


class TestEvaluateEstopLatch:
    def test_not_latched_continues(self):
        latch = SafetyLatch()
        assert evaluate_estop_latch(latch) == WatchdogDecision.CONTINUE

    def test_latched_stops(self):
        latch = SafetyLatch()
        latch.latch(SafetyFault.E_STOP)
        assert evaluate_estop_latch(latch) == WatchdogDecision.SAFETY_STOP

    def test_clear_after_latch_continues(self):
        latch = SafetyLatch()
        latch.latch(SafetyFault.E_STOP)
        latch.clear()
        assert evaluate_estop_latch(latch) == WatchdogDecision.CONTINUE


class TestCheckClearEstopPreconditions:
    def test_all_conditions_met(self):
        ok, reason = check_clear_estop_preconditions(True, True)
        assert ok

    def test_nonzero_velocity_fails(self):
        ok, reason = check_clear_estop_preconditions(False, True)
        assert not ok
        assert "velocity" in reason

    def test_active_fault_fails(self):
        ok, reason = check_clear_estop_preconditions(True, False)
        assert not ok
        assert "fault" in reason
