"""Domain entities and enums for random cleaning walk."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class RobotMode(Enum):
    """Current operational state of the random cleaning node."""
    IDLE = "idle"
    CLEANING_FORWARD = "cleaning_forward"
    CLEANING_TURN = "cleaning_turn"
    SAFETY_STOPPED = "safety_stopped"
    FAULT = "fault"


class SafetyReason(Enum):
    """Reason for a safety stop."""
    NONE = "none"
    SENSOR_DROPOUT = "sensor_dropout"
    LOW_BATTERY = "low_battery"
    E_STOP = "e_stop"
    CONTROL_FAULT = "control_fault"
    DOCK_RETURN_TIMEOUT = "dock_return_timeout"


class StartReason(Enum):
    USER_REQUEST = "user_request"
    MANUAL_RESUME = "manual_resume"


class EndReason(Enum):
    USER_STOP = "user_stop"
    E_STOP = "e_stop"
    LOW_BATTERY_STOP = "low_battery_stop"
    SENSOR_DROPOUT = "sensor_dropout"
    FAULT = "fault"


class MotionPhase(Enum):
    FORWARD = "forward"
    TURN = "turn"
    ESCAPE_TURN_180 = "escape_turn_180"


class MotionTrigger(Enum):
    PERIODIC = "periodic"
    OBSTACLE_RECOVERY = "obstacle_recovery"
    NO_PROGRESS = "no_progress"
    STARTUP = "startup"


class SafetyEventType(Enum):
    E_STOP = "e_stop"
    SENSOR_DROPOUT = "sensor_dropout"
    LOW_BATTERY_TRIGGER = "low_battery_trigger"
    DOCK_RETURN_TIMEOUT = "dock_return_timeout"
    COLLISION_RISK = "collision_risk"


class EventSeverity(Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class HandledAction(Enum):
    STOP = "stop"
    AVOID = "avoid"
    DOCK_RETURN = "dock_return"
    IGNORE = "ignore"


@dataclass
class CleaningSession:
    """Record for a single random cleaning session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    start_reason: StartReason = StartReason.USER_REQUEST
    end_reason: Optional[EndReason] = None
    final_state: RobotMode = RobotMode.IDLE
    dock_return_attempted: bool = False
    dock_return_elapsed_sec: int = 0

    def end(self, reason: EndReason, final_state: RobotMode) -> None:
        self.ended_at = datetime.utcnow()
        self.end_reason = reason
        self.final_state = final_state


@dataclass
class RobotRuntimeState:
    """Current runtime state of the random cleaning node."""
    mode: RobotMode = RobotMode.IDLE
    latched_safety_stop: bool = False
    safety_reason: SafetyReason = SafetyReason.NONE
    battery_percent: float = 100.0
    sensor_freshness_ms: int = 0
    last_cmd_vel_linear: float = 0.0
    last_cmd_vel_angular: float = 0.0
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.updated_at = datetime.utcnow()


@dataclass
class SafetyEvent:
    """Record of a safety-related event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    event_type: SafetyEventType = SafetyEventType.E_STOP
    severity: EventSeverity = EventSeverity.INFO
    detected_at: datetime = field(default_factory=datetime.utcnow)
    handled_action: HandledAction = HandledAction.STOP
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def resolve(self) -> None:
        self.resolved = True
        self.resolved_at = datetime.utcnow()


@dataclass
class MotionDecision:
    """Result of a random-walk motion decision."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    phase: MotionPhase = MotionPhase.FORWARD
    duration_ms: int = 0
    linear_velocity: float = 0.0
    angular_velocity: float = 0.0
    trigger: MotionTrigger = MotionTrigger.PERIODIC
    created_at: datetime = field(default_factory=datetime.utcnow)
