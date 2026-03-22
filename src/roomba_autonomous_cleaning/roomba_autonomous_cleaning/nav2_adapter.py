"""Nav2 action client adapter for work-unit navigation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import RECOVERY_TIMEOUT_S
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    CoverageWorkUnit,
    WorkUnitFailureReason,
)


class Nav2Result(Enum):
    SUCCESS = auto()
    TIMEOUT = auto()
    OBSTACLE = auto()
    LOCALIZATION_FAILURE = auto()
    CANCELLED = auto()


class Nav2Adapter:
    """Adapter for Nav2 navigate-to-pose action client."""

    def __init__(self, timeout_s: float = RECOVERY_TIMEOUT_S) -> None:
        self._timeout_s = timeout_s
        self._nav_client: Optional[object] = None

    def navigate_to_unit(
        self,
        unit: CoverageWorkUnit,
    ) -> Nav2Result:
        """Send a navigate-to-pose goal for the given work unit.

        Returns Nav2Result (stub returns SUCCESS when not connected to ROS2).
        """
        if self._nav_client is None:
            # Stub / test mode: pretend success
            return Nav2Result.SUCCESS
        try:
            # Real Nav2 call would go here via action client
            return Nav2Result.SUCCESS
        except Exception:  # noqa: BLE001
            return Nav2Result.TIMEOUT

    def cancel(self) -> None:
        """Cancel any in-progress navigation goal."""
        if self._nav_client is not None:
            try:
                pass  # nav_client.cancel_goal()
            except Exception:  # noqa: BLE001
                pass


def nav_result_to_failure_reason(
    result: Nav2Result,
) -> WorkUnitFailureReason:
    mapping = {
        Nav2Result.TIMEOUT: WorkUnitFailureReason.NAV_TIMEOUT,
        Nav2Result.OBSTACLE: WorkUnitFailureReason.OBSTACLE_BLOCKED,
        Nav2Result.LOCALIZATION_FAILURE: WorkUnitFailureReason.LOCALIZATION_DEGRADED,
        Nav2Result.CANCELLED: WorkUnitFailureReason.OPERATOR_PAUSE,
    }
    return mapping.get(result, WorkUnitFailureReason.NAV_TIMEOUT)
