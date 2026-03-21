"""Core domain enums and dataclasses for autonomous cleaning."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SessionState(Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    CLEANING = "cleaning"
    PAUSED = "paused"
    DOCKING = "docking"
    SAFETY_STOPPED = "safety_stopped"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"


class EndReason(Enum):
    NONE = "none"
    COVERAGE_COMPLETE = "coverage_complete"
    OPERATOR_STOP = "operator_stop"
    LOCALIZATION_LOST = "localization_lost"
    DOCK_SUCCESS = "dock_success"
    DOCK_FAILURE = "dock_failure"
    STARTUP_REJECTED = "startup_rejected"
    INTERNAL_FAULT = "internal_fault"
    ESTOP = "estop"


class WorkUnitState(Enum):
    UNVISITED = "unvisited"
    RESERVED = "reserved"
    NAVIGATING = "navigating"
    COVERED = "covered"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class WorkUnitFailureReason(Enum):
    NONE = "none"
    NAV_TIMEOUT = "nav_timeout"
    OBSTACLE_BLOCKED = "obstacle_blocked"
    LOCALIZATION_DEGRADED = "localization_degraded"
    OPERATOR_PAUSE = "operator_pause"


class LocalizationHealthState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    LOST = "lost"


class LocalizationTransitionReason(Enum):
    STARTUP_CHECK = "startup_check"
    COVARIANCE_HIGH = "covariance_high"
    SCAN_STALE = "scan_stale"
    RELOCALIZED = "relocalized"
    TIMEOUT = "timeout"


class PerceptionFusionState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    LOST = "lost"


class DockAttemptState(Enum):
    IDLE = "idle"
    ATTEMPTING = "attempting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class InterruptionReason(Enum):
    NONE = "none"
    OPERATOR_PAUSE = "operator_pause"
    OPERATOR_STOP = "operator_stop"
    ESTOP = "estop"
    LOCALIZATION_LOST = "localization_lost"
    PERCEPTION_LOST = "perception_lost"
    LOW_BATTERY = "low_battery"


@dataclass
class AutonomousCleaningSession:
    """Record for a single autonomous cleaning mission."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    map_id: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    state: SessionState = SessionState.IDLE
    target_scope: str = "full_reachable_floor"
    end_reason: EndReason = EndReason.NONE
    covered_ratio: float = 0.0
    covered_area_m2: float = 0.0
    blocked_area_m2: float = 0.0
    remaining_area_m2: float = 0.0

    def end(self, reason: EndReason, state: SessionState) -> None:
        self.ended_at = datetime.utcnow()
        self.end_reason = reason
        self.state = state


@dataclass
class CoverageWorkUnit:
    """Minimum executable cleaning work unit."""
    work_unit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    region_id: str = ""
    state: WorkUnitState = WorkUnitState.UNVISITED
    centroid_x: float = 0.0
    centroid_y: float = 0.0
    area_m2: float = 1.0
    retry_count: int = 0
    last_failure_reason: WorkUnitFailureReason = WorkUnitFailureReason.NONE


@dataclass
class CoverageSnapshot:
    """Current coverage progress for operator and topic publication."""
    session_id: str = ""
    updated_at: datetime = field(default_factory=datetime.utcnow)
    covered_area_m2: float = 0.0
    remaining_area_m2: float = 0.0
    blocked_area_m2: float = 0.0
    covered_ratio: float = 0.0
    reachable_ratio: float = 0.0
    active_work_unit_id: Optional[str] = None


@dataclass
class LocalizationHealth:
    """Runtime localization readiness state."""
    state: LocalizationHealthState = LocalizationHealthState.HEALTHY
    pose_covariance_score: float = 0.0
    laser_freshness_ms: int = 0
    map_to_odom_freshness_ms: int = 0
    last_transition_reason: LocalizationTransitionReason = LocalizationTransitionReason.STARTUP_CHECK
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PerceptionFusionHealth:
    """LiDAR/RGB/RGBD obstacle fusion health."""
    state: PerceptionFusionState = PerceptionFusionState.HEALTHY
    lidar_freshness_ms: int = 0
    rgb_freshness_ms: int = 0
    rgbd_freshness_ms: int = 0
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EStopState:
    """E-stop latch state for autonomous cleaning."""
    latched: bool = False
    clear_reason: str = ""

    def latch(self) -> None:
        self.latched = True

    def clear(self) -> None:
        self.latched = False
