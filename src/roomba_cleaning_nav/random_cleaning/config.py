"""Configuration constants and thresholds for random cleaning walk."""
from __future__ import annotations

# Velocity presets
LINEAR_VELOCITY_DEFAULT: float = 0.15  # m/s (150 mm/s)
ANGULAR_VELOCITY_DEFAULT: float = 1.0  # rad/s

# Motion parameters
FORWARD_DISTANCE_MIN_M: float = 0.5
FORWARD_DISTANCE_MAX_M: float = 3.0
TURN_ANGLE_MIN_RAD: float = 0.5236  # ~30 degrees
TURN_ANGLE_MAX_RAD: float = 3.1416  # ~180 degrees

# Control loop
CONTROL_LOOP_HZ: float = 20.0
CONTROL_LOOP_PERIOD_S: float = 1.0 / CONTROL_LOOP_HZ

# Battery thresholds (fraction 0..1)
BATTERY_START_THRESHOLD: float = 0.20   # 20% — reject start below this
BATTERY_LOW_THRESHOLD: float = 0.10    # 10% — begin dock-return attempt

# Dock return
DOCK_RETURN_TIMEOUT_S: int = 180

# Sensor freshness
SENSOR_DROPOUT_TIMEOUT_S: float = 1.0   # safety-stop after 1s of dropout

# No-progress detection
NO_PROGRESS_WINDOW_S: float = 10.0
NO_PROGRESS_DISTANCE_M: float = 0.1

# E-stop maximum latency (seconds)
ESTOP_MAX_LATENCY_S: float = 0.05  # 50ms / 1 control cycle

# Diagnostics
DIAGNOSTICS_PERIOD_S: float = 1.0
