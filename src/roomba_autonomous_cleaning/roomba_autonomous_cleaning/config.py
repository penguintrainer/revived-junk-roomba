"""Shared threshold constants for autonomous cleaning."""
from __future__ import annotations

# Battery thresholds (fraction 0..1)
BATTERY_START_THRESHOLD: float = 0.30   # 30% — reject start below this
BATTERY_LOW_THRESHOLD: float = 0.20    # 20% — begin dock return

# Recovery policy
RECOVERY_ATTEMPTS: int = 1
RECOVERY_TIMEOUT_S: float = 30.0

# E-stop
ESTOP_MAX_LATENCY_S: float = 0.05   # 50ms

# Diagnostics publish rate
DIAGNOSTICS_MAX_PERIOD_S: float = 1.0

# Control loop
CONTROL_LOOP_HZ: float = 20.0
CONTROL_LOOP_PERIOD_S: float = 1.0 / CONTROL_LOOP_HZ

# Coverage
COVERAGE_GRID_RESOLUTION_M: float = 0.5  # per work unit

# Localization health thresholds
LOCALIZATION_COVARIANCE_HIGH: float = 1.0   # sigma_xy in meters
LOCALIZATION_SCAN_STALE_MS: float = 2000.0
LOCALIZATION_TF_STALE_MS: float = 2000.0

# Perception fusion stale timeouts (ms)
LIDAR_STALE_MS: float = 1000.0
RGB_STALE_MS: float = 2000.0
RGBD_STALE_MS: float = 2000.0
