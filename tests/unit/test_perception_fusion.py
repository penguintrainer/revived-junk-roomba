"""Unit tests for perception fusion health supervisor."""
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


class TestEvaluatePerceptionFusion:
    def test_all_fresh_is_healthy(self):
        health = PerceptionFusionHealth()
        state = evaluate_perception_fusion(health, 0.0, 0.0, 0.0)
        assert state == PerceptionFusionState.HEALTHY

    def test_lidar_stale_is_lost(self):
        health = PerceptionFusionHealth()
        state = evaluate_perception_fusion(
            health,
            lidar_freshness_ms=LIDAR_STALE_MS + 1.0,
            rgb_freshness_ms=0.0,
            rgbd_freshness_ms=0.0,
        )
        assert state == PerceptionFusionState.LOST

    def test_rgb_and_rgbd_both_stale_is_degraded(self):
        health = PerceptionFusionHealth()
        state = evaluate_perception_fusion(
            health,
            lidar_freshness_ms=0.0,
            rgb_freshness_ms=RGB_STALE_MS + 1.0,
            rgbd_freshness_ms=RGBD_STALE_MS + 1.0,
        )
        assert state == PerceptionFusionState.DEGRADED

    def test_only_rgb_stale_is_healthy(self):
        health = PerceptionFusionHealth()
        state = evaluate_perception_fusion(
            health,
            lidar_freshness_ms=0.0,
            rgb_freshness_ms=RGB_STALE_MS + 1.0,
            rgbd_freshness_ms=0.0,
        )
        assert state == PerceptionFusionState.HEALTHY

    def test_only_rgbd_stale_is_healthy(self):
        health = PerceptionFusionHealth()
        state = evaluate_perception_fusion(
            health,
            lidar_freshness_ms=0.0,
            rgb_freshness_ms=0.0,
            rgbd_freshness_ms=RGBD_STALE_MS + 1.0,
        )
        assert state == PerceptionFusionState.HEALTHY

    def test_freshness_values_stored(self):
        health = PerceptionFusionHealth()
        evaluate_perception_fusion(health, 100.0, 200.0, 300.0)
        assert health.lidar_freshness_ms == 100
        assert health.rgb_freshness_ms == 200
        assert health.rgbd_freshness_ms == 300

    def test_custom_thresholds(self):
        health = PerceptionFusionHealth()
        state = evaluate_perception_fusion(
            health,
            lidar_freshness_ms=500.0,
            rgb_freshness_ms=0.0,
            rgbd_freshness_ms=0.0,
            lidar_stale_threshold_ms=400.0,  # custom threshold
        )
        assert state == PerceptionFusionState.LOST


class TestIsPerceptionOk:
    def test_healthy_is_ok(self):
        health = PerceptionFusionHealth(state=PerceptionFusionState.HEALTHY)
        assert is_perception_ok(health)

    def test_degraded_is_ok(self):
        health = PerceptionFusionHealth(state=PerceptionFusionState.DEGRADED)
        assert is_perception_ok(health)

    def test_lost_is_not_ok(self):
        health = PerceptionFusionHealth(state=PerceptionFusionState.LOST)
        assert not is_perception_ok(health)
