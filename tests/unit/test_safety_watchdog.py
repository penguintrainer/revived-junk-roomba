"""Unit tests for safety_watchdog: sensor freshness, battery, and events."""
import pytest

from roomba_cleaning_nav.random_cleaning.safety_watchdog import (
    WatchdogDecision,
    WatchdogInput,
    check_clear_estop_preconditions,
    evaluate_all,
    evaluate_battery,
    evaluate_bump,
    evaluate_cliff,
    evaluate_sensor_freshness,
    evaluate_serial,
    evaluate_wheel_drop,
)
from roomba_cleaning_nav.random_cleaning.models import SafetyReason
from roomba_cleaning_nav.random_cleaning.config import (
    BATTERY_LOW_THRESHOLD,
    SENSOR_DROPOUT_TIMEOUT_S,
)


class TestEvaluateSensorFreshness:
    def test_fresh_sensor_continues(self):
        result = evaluate_sensor_freshness(500.0)  # 500ms
        assert result.decision == WatchdogDecision.CONTINUE

    def test_stale_sensor_stops(self):
        threshold_ms = SENSOR_DROPOUT_TIMEOUT_S * 1000.0
        result = evaluate_sensor_freshness(threshold_ms + 1.0)
        assert result.decision == WatchdogDecision.SAFETY_STOP
        assert result.reason == SafetyReason.SENSOR_DROPOUT

    def test_exactly_at_threshold_not_stopped(self):
        threshold_ms = SENSOR_DROPOUT_TIMEOUT_S * 1000.0
        result = evaluate_sensor_freshness(threshold_ms)
        # exactly at threshold is not > threshold so still CONTINUE
        assert result.decision == WatchdogDecision.CONTINUE


class TestEvaluateBattery:
    def test_full_battery_continues(self):
        result = evaluate_battery(100.0)
        assert result.decision == WatchdogDecision.CONTINUE

    def test_low_battery_triggers_dock_return(self):
        threshold = BATTERY_LOW_THRESHOLD * 100.0
        result = evaluate_battery(threshold - 0.1)
        assert result.decision == WatchdogDecision.DOCK_RETURN
        assert result.reason == SafetyReason.LOW_BATTERY

    def test_exactly_at_threshold_continues(self):
        threshold = BATTERY_LOW_THRESHOLD * 100.0
        result = evaluate_battery(threshold)
        assert result.decision == WatchdogDecision.CONTINUE


class TestEvaluateCliff:
    def test_no_cliff_continues(self):
        assert evaluate_cliff(False).decision == WatchdogDecision.CONTINUE

    def test_cliff_triggers_avoid(self):
        result = evaluate_cliff(True)
        assert result.decision == WatchdogDecision.AVOID_CLIFF


class TestEvaluateBump:
    def test_no_bump_continues(self):
        assert evaluate_bump(False).decision == WatchdogDecision.CONTINUE

    def test_bump_triggers_recovery(self):
        result = evaluate_bump(True)
        assert result.decision == WatchdogDecision.BUMP_RECOVERY


class TestEvaluateWheelDrop:
    def test_no_wheel_drop_continues(self):
        assert evaluate_wheel_drop(False).decision == WatchdogDecision.CONTINUE

    def test_wheel_drop_stops(self):
        result = evaluate_wheel_drop(True)
        assert result.decision == WatchdogDecision.SAFETY_STOP
        assert result.reason == SafetyReason.CONTROL_FAULT


class TestEvaluateSerial:
    def test_serial_ok_continues(self):
        assert evaluate_serial(True).decision == WatchdogDecision.CONTINUE

    def test_serial_fail_stops(self):
        result = evaluate_serial(False)
        assert result.decision == WatchdogDecision.SAFETY_STOP


class TestEvaluateAll:
    def _ok_input(self) -> WatchdogInput:
        return WatchdogInput(
            sensor_freshness_ms=100.0,
            battery_percent=80.0,
            cliff_detected=False,
            bump_detected=False,
            wheel_drop=False,
            serial_ok=True,
        )

    def test_all_ok_continues(self):
        inp = self._ok_input()
        result = evaluate_all(inp)
        assert result.decision == WatchdogDecision.CONTINUE

    def test_serial_fault_highest_priority(self):
        inp = self._ok_input()
        inp.serial_ok = False
        inp.cliff_detected = True
        result = evaluate_all(inp)
        assert result.decision == WatchdogDecision.SAFETY_STOP

    def test_wheel_drop_above_sensor(self):
        inp = self._ok_input()
        inp.wheel_drop = True
        inp.sensor_freshness_ms = 5000.0  # also stale
        result = evaluate_all(inp)
        assert result.decision == WatchdogDecision.SAFETY_STOP
        assert result.reason == SafetyReason.CONTROL_FAULT  # wheel_drop first

    def test_cliff_above_battery(self):
        inp = self._ok_input()
        inp.cliff_detected = True
        inp.battery_percent = 1.0  # low battery too
        result = evaluate_all(inp)
        assert result.decision == WatchdogDecision.AVOID_CLIFF

    def test_bump_detected(self):
        inp = self._ok_input()
        inp.bump_detected = True
        result = evaluate_all(inp)
        assert result.decision == WatchdogDecision.BUMP_RECOVERY


class TestCheckClearEstopPreconditions:
    def test_all_ok(self):
        ok, reason = check_clear_estop_preconditions(True, True, True)
        assert ok
        assert reason == "ok"

    def test_nonzero_velocity_fails(self):
        ok, reason = check_clear_estop_preconditions(False, True, True)
        assert not ok
        assert "velocity" in reason

    def test_active_fault_fails(self):
        ok, reason = check_clear_estop_preconditions(True, False, True)
        assert not ok
        assert "fault" in reason

    def test_sensor_not_fresh_fails(self):
        ok, reason = check_clear_estop_preconditions(True, True, False)
        assert not ok
        assert "sensor" in reason
