"""Operator feedback adapter: Joy-Con rumble and ROS2 status publication."""
from __future__ import annotations

from typing import Any, Callable, Optional

from roomba_cleaning_nav.manual_drive.models import ManualDriveState, OperatorStatus
from roomba_cleaning_nav.manual_drive.status_formatter import (
    format_diagnostics_keys,
    format_status,
    status_to_json,
)

PublishFn = Callable[[Any], None]
_NOOP: PublishFn = lambda _: None  # noqa: E731


class FeedbackAdapter:
    """Publishes operator status and attempts Joy-Con rumble feedback."""

    def __init__(
        self,
        status_pub: Optional[PublishFn] = None,
        diag_pub: Optional[PublishFn] = None,
        string_msg_factory: Optional[Callable[[str], Any]] = None,
        diag_msg_factory: Optional[Callable[[dict], Any]] = None,
    ) -> None:
        self._status_pub = status_pub or _NOOP
        self._diag_pub = diag_pub or _NOOP
        self._string_msg = string_msg_factory or (lambda s: s)
        self._diag_msg = diag_msg_factory or (lambda d: d)
        self._rumble_available = False  # hardware-dependent

    def publish_status(self, state: ManualDriveState) -> None:
        """Publish the current operator status as JSON."""
        status = format_status(state)
        self._status_pub(self._string_msg(status_to_json(status)))

    def publish_diagnostics(
        self, state: ManualDriveState, link_age_ms: float
    ) -> None:
        """Publish diagnostics with all required keys."""
        keys = format_diagnostics_keys(state, link_age_ms)
        self._diag_pub(self._diag_msg(keys))

    def rumble(self, duration_ms: int = 200) -> None:
        """Emit a short rumble pulse (no-op if unavailable)."""
        if not self._rumble_available:
            return
        # Hardware rumble call would go here

    def on_mode_change(self, state: ManualDriveState) -> None:
        """Publish status and attempt rumble on mode transition."""
        self.publish_status(state)
        self.rumble()

    def on_cleaning_toggle(self, state: ManualDriveState) -> None:
        """Publish status and attempt rumble on cleaning toggle."""
        self.publish_status(state)
        self.rumble(100)
