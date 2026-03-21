"""Configuration constants for Joy-Con manual drive."""
from __future__ import annotations

# Velocity presets
LINEAR_VELOCITY_DEFAULT: float = 0.15   # m/s (150 mm/s)
ANGULAR_VELOCITY_DEFAULT: float = 1.0  # rad/s

# Stop-on-release timeout
STOP_ON_RELEASE_TIMEOUT_S: float = 0.3

# Long-press mode button duration
MODE_LONG_PRESS_S: float = 1.0

# Link-loss fail-safe timeout
LINK_LOSS_TIMEOUT_S: float = 1.0

# Control loop
CONTROL_LOOP_HZ: float = 20.0
CONTROL_LOOP_PERIOD_S: float = 1.0 / CONTROL_LOOP_HZ

# Cleaning motor duty cycle presets (0..1)
SIDE_BRUSH_DUTY: float = 0.5
MAIN_BRUSH_DUTY: float = 0.8
VACUUM_DUTY: float = 0.6

# E-stop latency
ESTOP_MAX_LATENCY_S: float = 0.05  # 50ms

# Diagnostics
DIAGNOSTICS_PERIOD_S: float = 1.0
