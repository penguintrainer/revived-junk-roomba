"""Safety watchdog for manual drive: link-loss, cliff-stop, e-stop latch.

All evaluation functions are pure — no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple

from roomba_cleaning_nav.manual_drive.config import LINK_LOSS_TIMEOUT_S
from roomba_cleaning_nav.manual_drive.models import SafetyFault


class WatchdogDecision(Enum):
    CONTINUE = auto()
    SAFETY_STOP = auto()
    CLIFF_STOP = auto()
    LINK_LOSS_STOP = auto()


@dataclass
class SafetyLatch:
    """Mutable e-stop latch state."""
    latched: bool = False
    fault: SafetyFault = SafetyFault.NONE

    def latch(self, fault: SafetyFault) -> None:
        self.latched = True
        self.fault = fault

    def clear(self) -> None:
        self.latched = False
        self.fault = SafetyFault.NONE


def evaluate_link_health(
    link_age_ms: float,
    timeout_ms: float = LINK_LOSS_TIMEOUT_S * 1000.0,
) -> WatchdogDecision:
    """Return LINK_LOSS_STOP if the link has been absent longer than timeout."""
    if link_age_ms > timeout_ms:
        return WatchdogDecision.LINK_LOSS_STOP
    return WatchdogDecision.CONTINUE


def evaluate_cliff(cliff_detected: bool) -> WatchdogDecision:
    """Return CLIFF_STOP if cliff sensor is triggered."""
    if cliff_detected:
        return WatchdogDecision.CLIFF_STOP
    return WatchdogDecision.CONTINUE


def evaluate_estop_latch(latch: SafetyLatch) -> WatchdogDecision:
    """Return SAFETY_STOP if the e-stop latch is engaged."""
    if latch.latched:
        return WatchdogDecision.SAFETY_STOP
    return WatchdogDecision.CONTINUE


def evaluate_serial(serial_ok: bool) -> WatchdogDecision:
    """Return SAFETY_STOP if serial communication is lost."""
    if not serial_ok:
        return WatchdogDecision.SAFETY_STOP
    return WatchdogDecision.CONTINUE


def check_clear_estop_preconditions(
    velocity_zero: bool,
    no_active_fault: bool,
) -> Tuple[bool, str]:
    """Validate preconditions for clearing the e-stop latch.

    Returns (ok, reason_string).
    """
    if not velocity_zero:
        return False, "nonzero_velocity"
    if not no_active_fault:
        return False, "active_safety_fault"
    return True, "ok"
