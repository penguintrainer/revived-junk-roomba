"""Integration tests for perception fusion degraded/lost transitions."""
import pytest

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    PerceptionFusionHealth,
    PerceptionFusionState,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.perception_fusion import (
    evaluate_perception_fusion,
    is_perception_ok,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import (
    LIDAR_STALE_MS,
    RGB_STALE_MS,
    RGBD_STALE_MS,
)


class TestPerceptionFusionIntegration:
    """Integration tests for perception fusion state transitions."""

    def _fresh_health(self) -> PerceptionFusionHealth:
        return PerceptionFusionHealth()

    def test_fresh_sources_healthy(self):
        health = self._fresh_health()
        state = evaluate_perception_fusion(health, 0.0, 0.0, 0.0)
        assert state == PerceptionFusionState.HEALTHY
        assert is_perception_ok(health)

    def test_lidar_stale_transitions_to_lost(self):
        health = self._fresh_health()
        evaluate_perception_fusion(health, LIDAR_STALE_MS + 1.0, 0.0, 0.0)
        assert health.state == PerceptionFusionState.LOST
        assert not is_perception_ok(health)

    def test_both_rgb_and_rgbd_stale_transitions_to_degraded(self):
        health = self._fresh_health()
        evaluate_perception_fusion(
            health, 0.0, RGB_STALE_MS + 1.0, RGBD_STALE_MS + 1.0
        )
        assert health.state == PerceptionFusionState.DEGRADED
        assert is_perception_ok(health)  # degraded is still ok

    def test_recovery_after_stale(self):
        health = self._fresh_health()
        # First go stale
        evaluate_perception_fusion(health, LIDAR_STALE_MS + 100.0, 0.0, 0.0)
        assert health.state == PerceptionFusionState.LOST

        # Then recover
        evaluate_perception_fusion(health, 0.0, 0.0, 0.0)
        assert health.state == PerceptionFusionState.HEALTHY

    def test_freshness_values_tracked(self):
        health = self._fresh_health()
        evaluate_perception_fusion(health, 100.0, 200.0, 300.0)
        assert health.lidar_freshness_ms == 100
        assert health.rgb_freshness_ms == 200
        assert health.rgbd_freshness_ms == 300
