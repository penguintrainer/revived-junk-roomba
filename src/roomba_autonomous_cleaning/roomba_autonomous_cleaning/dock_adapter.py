"""Dock attempt adapter using create_robot battery and charging evidence."""
from __future__ import annotations

from enum import Enum, auto
from typing import Optional

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import DockAttemptState


class DockAdapter:
    """Manages dock-return attempt lifecycle."""

    def __init__(self) -> None:
        self._state = DockAttemptState.IDLE

    @property
    def state(self) -> DockAttemptState:
        return self._state

    def start_dock(self) -> None:
        """Issue the dock command."""
        self._state = DockAttemptState.ATTEMPTING

    def on_charging_detected(self) -> None:
        """Called when charging evidence is confirmed."""
        self._state = DockAttemptState.SUCCEEDED

    def on_timeout(self) -> None:
        """Called when dock attempt times out."""
        self._state = DockAttemptState.FAILED

    def reset(self) -> None:
        self._state = DockAttemptState.IDLE

    def is_docking_done(self) -> bool:
        return self._state in (DockAttemptState.SUCCEEDED, DockAttemptState.FAILED)
