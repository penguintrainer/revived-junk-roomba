"""Domain entities, enums, and state containers for manual drive."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class ManualDriveMode(Enum):
    """Operating mode of the manual drive node."""
    IDLE = "idle"
    MANUAL_ACTIVE = "manual_active"
    SAFETY_STOPPED = "safety_stopped"
    FAULT = "fault"


class DirectionInput(Enum):
    """D-pad direction input from the Joy-Con."""
    NONE = "none"
    FORWARD = "forward"
    BACKWARD = "backward"
    ROTATE_LEFT = "rotate_left"
    ROTATE_RIGHT = "rotate_right"


class CleaningState(Enum):
    OFF = "off"
    ON = "on"


class SafetyFault(Enum):
    NONE = "none"
    LINK_LOSS = "link_loss"
    CLIFF = "cliff"
    E_STOP = "e_stop"
    SERIAL_FAULT = "serial_fault"


class ForbiddenZoneOverride(Enum):
    ENFORCED = "enforced"
    BYPASSED = "bypassed"


@dataclass
class ManualDriveState:
    """Runtime state container for the manual drive node."""
    mode: ManualDriveMode = ManualDriveMode.IDLE
    cleaning: CleaningState = CleaningState.OFF
    fault: SafetyFault = SafetyFault.NONE
    estop_latched: bool = False
    safety_latched: bool = False
    forbidden_zone_override: ForbiddenZoneOverride = ForbiddenZoneOverride.ENFORCED
    link_health_ok: bool = True
    low_battery_warning: bool = False
    last_direction: DirectionInput = DirectionInput.NONE
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_active(self) -> bool:
        return self.mode == ManualDriveMode.MANUAL_ACTIVE

    def enter_manual_mode(self) -> None:
        self.mode = ManualDriveMode.MANUAL_ACTIVE
        self.forbidden_zone_override = ForbiddenZoneOverride.BYPASSED
        self.updated_at = datetime.utcnow()

    def exit_manual_mode(self) -> None:
        self.mode = ManualDriveMode.IDLE
        self.cleaning = CleaningState.OFF
        self.forbidden_zone_override = ForbiddenZoneOverride.ENFORCED
        self.last_direction = DirectionInput.NONE
        self.updated_at = datetime.utcnow()

    def apply_safety_stop(self, fault: SafetyFault) -> None:
        self.mode = ManualDriveMode.SAFETY_STOPPED
        self.cleaning = CleaningState.OFF
        self.fault = fault
        self.safety_latched = True
        self.forbidden_zone_override = ForbiddenZoneOverride.ENFORCED
        self.updated_at = datetime.utcnow()


@dataclass
class OperatorStatus:
    """Serializable snapshot of the current operator-facing status."""
    mode: str = "idle"
    cleaning: str = "off"
    fault: str = "none"
    estop_latched: bool = False
    link_ok: bool = True
    low_battery: bool = False
    forbidden_zone_override: str = "enforced"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
