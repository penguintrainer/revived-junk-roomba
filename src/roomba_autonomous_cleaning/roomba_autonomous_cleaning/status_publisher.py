"""Status publisher for autonomous cleaning — operator-facing payload helpers."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    CoverageSnapshot,
    DockAttemptState,
    EStopState,
    LocalizationHealth,
    PerceptionFusionHealth,
    SessionState,
)

PublishFn = Callable[[Any], None]
_NOOP: PublishFn = lambda _: None  # noqa: E731


class StatusPublisher:
    """Formats and dispatches status/diagnostics payloads."""

    def __init__(
        self,
        status_pub: Optional[PublishFn] = None,
        diag_pub: Optional[PublishFn] = None,
        msg_factory: Optional[Callable[[Dict], Any]] = None,
    ) -> None:
        self._status_pub = status_pub or _NOOP
        self._diag_pub = diag_pub or _NOOP
        self._msg_factory = msg_factory or (lambda d: d)

    def publish_status(
        self,
        session: AutonomousCleaningSession,
        snapshot: CoverageSnapshot,
        estop_state: EStopState,
    ) -> None:
        payload = {
            "session_id": session.session_id,
            "state": session.state.value,
            "end_reason": session.end_reason.value,
            "covered_ratio": round(session.covered_ratio, 4),
            "covered_area_m2": round(session.covered_area_m2, 4),
            "remaining_area_m2": round(snapshot.remaining_area_m2, 4),
            "blocked_area_m2": round(snapshot.blocked_area_m2, 4),
            "estop_latched": estop_state.latched,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._status_pub(self._msg_factory(payload))

    def publish_diagnostics(
        self,
        session: AutonomousCleaningSession,
        localization: LocalizationHealth,
        battery_charge_ratio: float,
        dock_state: DockAttemptState,
        estop_state: EStopState,
        perception: PerceptionFusionHealth,
    ) -> Dict[str, str]:
        """Return and publish required diagnostics keys."""
        keys: Dict[str, str] = {
            "session_state": session.state.value,
            "localization_health": localization.state.value,
            "battery_charge_ratio": f"{battery_charge_ratio:.3f}",
            "dock_attempt_state": dock_state.value,
            "estop_latched": str(estop_state.latched).lower(),
            "perception_health": perception.state.value,
        }
        self._diag_pub(self._msg_factory(keys))
        return keys
