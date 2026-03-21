"""Integration test: localization supervisor degraded/lost transitions."""
import pytest

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    LocalizationHealth,
    LocalizationHealthState,
    LocalizationTransitionReason,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.localization_supervisor import (
    evaluate_localization,
    is_localization_ok,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import (
    LOCALIZATION_COVARIANCE_HIGH,
    LOCALIZATION_SCAN_STALE_MS,
    LOCALIZATION_TF_STALE_MS,
)


class TestLocalizationSupervisor:
    def test_healthy_state(self):
        health = LocalizationHealth()
        state = evaluate_localization(health, 0.1, 100.0, 100.0)
        assert state == LocalizationHealthState.HEALTHY
        assert is_localization_ok(health)

    def test_degraded_on_high_covariance(self):
        health = LocalizationHealth()
        state = evaluate_localization(
            health,
            pose_covariance_score=LOCALIZATION_COVARIANCE_HIGH + 0.1,
            laser_freshness_ms=100.0,
            map_to_odom_freshness_ms=100.0,
        )
        assert state == LocalizationHealthState.DEGRADED
        assert health.last_transition_reason == LocalizationTransitionReason.COVARIANCE_HIGH

    def test_lost_on_stale_scan(self):
        health = LocalizationHealth()
        state = evaluate_localization(
            health,
            pose_covariance_score=0.0,
            laser_freshness_ms=LOCALIZATION_SCAN_STALE_MS + 100.0,
            map_to_odom_freshness_ms=100.0,
        )
        assert state == LocalizationHealthState.LOST
        assert not is_localization_ok(health)

    def test_lost_on_stale_tf(self):
        health = LocalizationHealth()
        state = evaluate_localization(
            health,
            pose_covariance_score=0.0,
            laser_freshness_ms=100.0,
            map_to_odom_freshness_ms=LOCALIZATION_TF_STALE_MS + 100.0,
        )
        assert state == LocalizationHealthState.LOST

    def test_recovery_from_lost(self):
        health = LocalizationHealth()
        evaluate_localization(health, 0.0, LOCALIZATION_SCAN_STALE_MS + 1.0, 100.0)
        assert health.state == LocalizationHealthState.LOST

        evaluate_localization(health, 0.0, 100.0, 100.0)
        assert health.state == LocalizationHealthState.HEALTHY
        assert is_localization_ok(health)
