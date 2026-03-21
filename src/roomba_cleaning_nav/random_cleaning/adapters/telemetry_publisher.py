"""Telemetry publisher utilities for random cleaning state and events.

Provides helpers to format and publish state/event payloads.
When rclpy is unavailable (unit test environment), publishing is no-op.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Optional

from roomba_cleaning_nav.random_cleaning.models import (
    RobotMode,
    RobotRuntimeState,
    SafetyEvent,
)

# Type alias for a ROS2 publisher's publish method
PublishFn = Callable[[Any], None]

_NOOP: PublishFn = lambda _: None  # noqa: E731


class TelemetryPublisher:
    """Formats and dispatches state / event payloads to ROS2 topics."""

    def __init__(
        self,
        state_pub: Optional[PublishFn] = None,
        safety_event_pub: Optional[PublishFn] = None,
        string_msg_factory: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self._state_pub = state_pub or _NOOP
        self._safety_event_pub = safety_event_pub or _NOOP
        self._string_msg = string_msg_factory or (lambda s: s)

    # ------------------------------------------------------------------
    # State publication
    # ------------------------------------------------------------------

    def publish_state(self, state: RobotRuntimeState) -> None:
        """Publish the current robot mode as a string payload."""
        payload = state.mode.value
        self._state_pub(self._string_msg(payload))

    def publish_state_str(self, mode_value: str) -> None:
        """Publish a raw state string."""
        self._state_pub(self._string_msg(mode_value))

    # ------------------------------------------------------------------
    # Safety event publication
    # ------------------------------------------------------------------

    def publish_safety_event(self, event: SafetyEvent) -> None:
        """Publish a safety event in pipe-delimited format.

        Format: ``event_type|severity|timestamp|detail_code``
        """
        detail = event.handled_action.value
        payload = "|".join([
            event.event_type.value,
            event.severity.value,
            event.detected_at.isoformat(),
            detail,
        ])
        self._safety_event_pub(self._string_msg(payload))

    def publish_safety_event_str(
        self,
        event_type: str,
        severity: str,
        detail: str,
    ) -> None:
        """Publish a raw safety event string."""
        payload = "|".join([
            event_type,
            severity,
            datetime.utcnow().isoformat(),
            detail,
        ])
        self._safety_event_pub(self._string_msg(payload))

    # ------------------------------------------------------------------
    # Parsing helpers (for contract tests)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_safety_event_payload(payload: str) -> dict[str, str]:
        """Parse a pipe-delimited safety event payload into a dict."""
        parts = payload.split("|")
        if len(parts) != 4:
            raise ValueError(f"Invalid safety event payload: {payload!r}")
        return {
            "event_type": parts[0],
            "severity": parts[1],
            "timestamp": parts[2],
            "detail_code": parts[3],
        }
