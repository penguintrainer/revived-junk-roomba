"""E-stop latch manager with explicit clear semantics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import EStopState


@dataclass
class EStopManager:
    """Manages the e-stop latch lifecycle."""
    _state: EStopState = field(default_factory=EStopState)

    @property
    def is_latched(self) -> bool:
        return self._state.latched

    def latch(self) -> None:
        """Latch the e-stop."""
        self._state.latch()

    def clear(
        self,
        velocity_zero: bool,
        no_active_safety_fault: bool,
        perception_not_lost: bool,
    ) -> Tuple[bool, str]:
        """Clear the e-stop latch if all preconditions are met.

        Returns (success, reason).
        """
        if not self._state.latched:
            return False, "not_latched"
        if not velocity_zero:
            return False, "nonzero_velocity"
        if not no_active_safety_fault:
            return False, "active_safety_fault"
        if not perception_not_lost:
            return False, "perception_lost"
        self._state.clear()
        return True, "cleared"
