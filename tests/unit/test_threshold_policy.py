"""Unit tests for threshold policy constants."""
import pytest

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import (
    BATTERY_LOW_THRESHOLD,
    BATTERY_START_THRESHOLD,
    DIAGNOSTICS_MAX_PERIOD_S,
    ESTOP_MAX_LATENCY_S,
    RECOVERY_ATTEMPTS,
    RECOVERY_TIMEOUT_S,
)


class TestThresholdPolicy:
    def test_battery_start_threshold_30pct(self):
        assert BATTERY_START_THRESHOLD == pytest.approx(0.30)

    def test_battery_low_threshold_20pct(self):
        assert BATTERY_LOW_THRESHOLD == pytest.approx(0.20)

    def test_start_above_low(self):
        assert BATTERY_START_THRESHOLD > BATTERY_LOW_THRESHOLD

    def test_estop_latency_50ms(self):
        assert ESTOP_MAX_LATENCY_S == pytest.approx(0.05)

    def test_recovery_attempts_is_1(self):
        assert RECOVERY_ATTEMPTS == 1

    def test_recovery_timeout_30s(self):
        assert RECOVERY_TIMEOUT_S == pytest.approx(30.0)

    def test_diagnostics_period_1s(self):
        assert DIAGNOSTICS_MAX_PERIOD_S == pytest.approx(1.0)
