"""Localization health supervisor."""
from __future__ import annotations

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import (
    LOCALIZATION_COVARIANCE_HIGH,
    LOCALIZATION_SCAN_STALE_MS,
    LOCALIZATION_TF_STALE_MS,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    LocalizationHealth,
    LocalizationHealthState,
    LocalizationTransitionReason,
)


def evaluate_localization(
    health: LocalizationHealth,
    pose_covariance_score: float,
    laser_freshness_ms: float,
    map_to_odom_freshness_ms: float,
) -> LocalizationHealthState:
    """Evaluate and update localization health state.

    Returns the new state.
    """
    health.pose_covariance_score = pose_covariance_score
    health.laser_freshness_ms = int(laser_freshness_ms)
    health.map_to_odom_freshness_ms = int(map_to_odom_freshness_ms)

    if laser_freshness_ms > LOCALIZATION_SCAN_STALE_MS:
        health.state = LocalizationHealthState.LOST
        health.last_transition_reason = LocalizationTransitionReason.SCAN_STALE
    elif map_to_odom_freshness_ms > LOCALIZATION_TF_STALE_MS:
        health.state = LocalizationHealthState.LOST
        health.last_transition_reason = LocalizationTransitionReason.SCAN_STALE
    elif pose_covariance_score > LOCALIZATION_COVARIANCE_HIGH:
        health.state = LocalizationHealthState.DEGRADED
        health.last_transition_reason = LocalizationTransitionReason.COVARIANCE_HIGH
    else:
        health.state = LocalizationHealthState.HEALTHY
        health.last_transition_reason = LocalizationTransitionReason.RELOCALIZED

    return health.state


def is_localization_ok(health: LocalizationHealth) -> bool:
    """Return True if localization is healthy enough for navigation."""
    return health.state != LocalizationHealthState.LOST
