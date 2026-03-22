"""Safety watchdog: sensor freshness, battery monitoring, bump/cliff/wheel-drop.

All evaluation functions are pure — they take state and return decisions
without mutation, enabling deterministic unit testing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Tuple

from roomba_cleaning_nav.random_cleaning.config import (
    BATTERY_LOW_THRESHOLD,
    SENSOR_DROPOUT_TIMEOUT_S,
)
from roomba_cleaning_nav.random_cleaning.models import SafetyReason


class WatchdogDecision(Enum):
    """Outcome of a safety watchdog evaluation."""
    CONTINUE = auto()
    SAFETY_STOP = auto()
    DOCK_RETURN = auto()
    AVOID_CLIFF = auto()
    BUMP_RECOVERY = auto()


@dataclass
class WatchdogInput:
    """Snapshot of sensor and system inputs evaluated by the watchdog."""
    sensor_freshness_ms: float = 0.0        # ms since last sensor update
    battery_percent: float = 100.0
    cliff_detected: bool = False
    bump_detected: bool = False
    wheel_drop: bool = False
    serial_ok: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WatchdogResult:
    """Watchdog evaluation result."""
    decision: WatchdogDecision = WatchdogDecision.CONTINUE
    reason: SafetyReason = SafetyReason.NONE
    detail: str = ""


def evaluate_sensor_freshness(freshness_ms: float) -> WatchdogResult:
    """Return SAFETY_STOP if sensor has been stale for > 1 second."""
    threshold_ms = SENSOR_DROPOUT_TIMEOUT_S * 1000.0
    if freshness_ms > threshold_ms:
        return WatchdogResult(
            decision=WatchdogDecision.SAFETY_STOP,
            reason=SafetyReason.SENSOR_DROPOUT,
            detail=f"sensor_stale_{freshness_ms:.0f}ms",
        )
    return WatchdogResult(decision=WatchdogDecision.CONTINUE)


def evaluate_battery(battery_percent: float) -> WatchdogResult:
    """Return DOCK_RETURN if battery is below low threshold."""
    if battery_percent < BATTERY_LOW_THRESHOLD * 100.0:
        return WatchdogResult(
            decision=WatchdogDecision.DOCK_RETURN,
            reason=SafetyReason.LOW_BATTERY,
            detail=f"battery_{battery_percent:.1f}pct",
        )
    return WatchdogResult(decision=WatchdogDecision.CONTINUE)


def evaluate_cliff(cliff_detected: bool) -> WatchdogResult:
    """Return AVOID_CLIFF if cliff sensor triggered."""
    if cliff_detected:
        return WatchdogResult(
            decision=WatchdogDecision.AVOID_CLIFF,
            reason=SafetyReason.CONTROL_FAULT,
            detail="cliff_detected",
        )
    return WatchdogResult(decision=WatchdogDecision.CONTINUE)


def evaluate_bump(bump_detected: bool) -> WatchdogResult:
    """Return BUMP_RECOVERY if bump sensor triggered."""
    if bump_detected:
        return WatchdogResult(
            decision=WatchdogDecision.BUMP_RECOVERY,
            reason=SafetyReason.NONE,
            detail="bump_detected",
        )
    return WatchdogResult(decision=WatchdogDecision.CONTINUE)


def evaluate_wheel_drop(wheel_drop: bool) -> WatchdogResult:
    """Return SAFETY_STOP if wheel-drop detected."""
    if wheel_drop:
        return WatchdogResult(
            decision=WatchdogDecision.SAFETY_STOP,
            reason=SafetyReason.CONTROL_FAULT,
            detail="wheel_drop",
        )
    return WatchdogResult(decision=WatchdogDecision.CONTINUE)


def evaluate_serial(serial_ok: bool) -> WatchdogResult:
    """Return SAFETY_STOP if serial communication lost."""
    if not serial_ok:
        return WatchdogResult(
            decision=WatchdogDecision.SAFETY_STOP,
            reason=SafetyReason.CONTROL_FAULT,
            detail="serial_disconnected",
        )
    return WatchdogResult(decision=WatchdogDecision.CONTINUE)


def evaluate_all(inp: WatchdogInput) -> WatchdogResult:
    """Evaluate all safety conditions in priority order.

    Priority: serial > wheel_drop > sensor_freshness > cliff > battery > bump
    """
    checks = [
        evaluate_serial(inp.serial_ok),
        evaluate_wheel_drop(inp.wheel_drop),
        evaluate_sensor_freshness(inp.sensor_freshness_ms),
        evaluate_cliff(inp.cliff_detected),
        evaluate_battery(inp.battery_percent),
        evaluate_bump(inp.bump_detected),
    ]
    for result in checks:
        if result.decision != WatchdogDecision.CONTINUE:
            return result
    return WatchdogResult(decision=WatchdogDecision.CONTINUE)


def check_clear_estop_preconditions(
    velocity_zero: bool,
    no_active_fault: bool,
    sensor_fresh: bool,
) -> Tuple[bool, str]:
    """Validate all three preconditions for clearing e-stop latch.

    Returns (ok, reject_reason).
    """
    if not velocity_zero:
        return False, "nonzero_velocity"
    if not no_active_fault:
        return False, "active_safety_fault"
    if not sensor_fresh:
        return False, "sensor_not_fresh"
    return True, "ok"
