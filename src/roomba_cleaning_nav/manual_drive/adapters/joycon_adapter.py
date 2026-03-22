"""Left Joy-Con HID bridge adapter.

Wraps joycon-python (or stubs when unavailable) to read d-pad state,
mode-button long-press, and cleaning-toggle edge detection.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

try:
    from joycon import JoyCon, get_L_id  # type: ignore
    _HAS_JOYCON = True
except ImportError:
    _HAS_JOYCON = False

from roomba_cleaning_nav.manual_drive.models import DirectionInput


@dataclass
class JoyConState:
    """Snapshot of Joy-Con HID button state."""
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False
    mode_button: bool = False       # minus / SR / SL
    cleaning_toggle: bool = False   # ZL or L
    connected: bool = False
    last_packet_time: float = field(default_factory=time.monotonic)


class JoyConAdapter:
    """Read Left Joy-Con HID events and expose structured state."""

    def __init__(self, vendor_id: int = 0x057e, product_id: int = 0x2006) -> None:
        self._vendor_id = vendor_id
        self._product_id = product_id
        self._joycon: Optional[Any] = None
        self._state = JoyConState()
        self._prev_cleaning_button = False

    def connect(self) -> bool:
        """Open HID connection. Returns True on success."""
        if not _HAS_JOYCON:
            return False
        try:
            ids = get_L_id()
            if ids is None:
                return False
            self._joycon = JoyCon(*ids)
            self._state.connected = True
            return True
        except Exception:  # noqa: BLE001
            self._state.connected = False
            return False

    def disconnect(self) -> None:
        self._joycon = None
        self._state.connected = False

    @property
    def is_connected(self) -> bool:
        return self._state.connected

    def poll(self) -> JoyConState:
        """Read latest button state from the Joy-Con."""
        if self._joycon is None:
            return self._state
        try:
            s = self._joycon.get_status()
            buttons = s.get("buttons", {}).get("left", {})
            self._state.up = bool(buttons.get("up", False))
            self._state.down = bool(buttons.get("down", False))
            self._state.left = bool(buttons.get("left", False))
            self._state.right = bool(buttons.get("right", False))
            self._state.mode_button = bool(buttons.get("minus", False))
            self._state.cleaning_toggle = bool(
                buttons.get("zl", False) or buttons.get("l", False)
            )
            self._state.last_packet_time = time.monotonic()
        except Exception:  # noqa: BLE001
            self._state.connected = False
        return self._state

    def get_active_directions(self) -> list[DirectionInput]:
        """Return currently pressed directional inputs."""
        directions: list[DirectionInput] = []
        if self._state.up:
            directions.append(DirectionInput.FORWARD)
        if self._state.down:
            directions.append(DirectionInput.BACKWARD)
        if self._state.left:
            directions.append(DirectionInput.ROTATE_LEFT)
        if self._state.right:
            directions.append(DirectionInput.ROTATE_RIGHT)
        return directions

    def consume_cleaning_toggle_edge(self) -> bool:
        """Return True once per rising-edge press of the cleaning toggle button."""
        current = self._state.cleaning_toggle
        was = self._prev_cleaning_button
        self._prev_cleaning_button = current
        return current and not was

    def link_age_ms(self) -> float:
        """Milliseconds since the last successful packet."""
        return (time.monotonic() - self._state.last_packet_time) * 1000.0
