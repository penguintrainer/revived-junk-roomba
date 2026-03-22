"""Perception fusion health supervisor: LiDAR/RGB/RGBD obstacle avoidance."""
from __future__ import annotations

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import (
    LIDAR_STALE_MS,
    RGB_STALE_MS,
    RGBD_STALE_MS,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    PerceptionFusionHealth,
    PerceptionFusionState,
)


def evaluate_perception_fusion(
    health: PerceptionFusionHealth,
    lidar_freshness_ms: float,
    rgb_freshness_ms: float,
    rgbd_freshness_ms: float,
    lidar_stale_threshold_ms: float = LIDAR_STALE_MS,
    rgb_stale_threshold_ms: float = RGB_STALE_MS,
    rgbd_stale_threshold_ms: float = RGBD_STALE_MS,
) -> PerceptionFusionState:
    """Evaluate perception fusion health from source freshness.

    Rules:
    - LiDAR stale → LOST (primary obstacle avoidance source)
    - Both RGB and RGBD stale → DEGRADED
    - All fresh → HEALTHY
    """
    health.lidar_freshness_ms = int(lidar_freshness_ms)
    health.rgb_freshness_ms = int(rgb_freshness_ms)
    health.rgbd_freshness_ms = int(rgbd_freshness_ms)

    lidar_stale = lidar_freshness_ms > lidar_stale_threshold_ms
    rgb_stale = rgb_freshness_ms > rgb_stale_threshold_ms
    rgbd_stale = rgbd_freshness_ms > rgbd_stale_threshold_ms

    if lidar_stale:
        health.state = PerceptionFusionState.LOST
    elif rgb_stale and rgbd_stale:
        health.state = PerceptionFusionState.DEGRADED
    else:
        health.state = PerceptionFusionState.HEALTHY

    return health.state


def is_perception_ok(health: PerceptionFusionHealth) -> bool:
    """Return True if perception is not in LOST state."""
    return health.state != PerceptionFusionState.LOST
