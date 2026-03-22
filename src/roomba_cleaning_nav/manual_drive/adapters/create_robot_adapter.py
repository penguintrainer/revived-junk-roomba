"""Create-robot output bridge for manual drive.

Wraps hardware commands with a clean interface for cmd_vel and cleaning motors.
"""
from __future__ import annotations

from typing import Optional

try:
    import create_robot  # type: ignore
    _HAS_CREATE = True
except ImportError:
    _HAS_CREATE = False

from roomba_cleaning_nav.manual_drive.config import (
    MAIN_BRUSH_DUTY,
    SIDE_BRUSH_DUTY,
    VACUUM_DUTY,
)


class CreateRobotAdapter:
    """Adapter for Roomba577 hardware via create_robot."""

    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200) -> None:
        self._port = port
        self._baud = baud
        self._robot: Optional[object] = None
        self._connected = False

    def connect(self) -> bool:
        if not _HAS_CREATE:
            self._connected = False
            return False
        try:
            self._robot = create_robot.Create2(port=self._port, baud=self._baud)
            self._connected = True
            return True
        except Exception:  # noqa: BLE001
            self._connected = False
            return False

    def disconnect(self) -> None:
        if self._robot is not None:
            try:
                getattr(self._robot, "stop", lambda: None)()
            except Exception:  # noqa: BLE001
                pass
        self._robot = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def set_velocity(self, linear: float, angular: float) -> None:
        """Send velocity command. No-op when not connected."""
        if self._robot is None:
            return
        try:
            self._robot.drive_direct(linear, angular)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            self._connected = False

    def stop(self) -> None:
        self.set_velocity(0.0, 0.0)

    def enable_cleaning(self) -> None:
        """Enable side brush, main brush, and vacuum at preset duty cycles."""
        if self._robot is None:
            return
        try:
            self._robot.set_side_brush_motor(SIDE_BRUSH_DUTY)  # type: ignore[attr-defined]
            self._robot.set_main_brush_motor(MAIN_BRUSH_DUTY)  # type: ignore[attr-defined]
            self._robot.set_vacuum(VACUUM_DUTY)               # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    def disable_cleaning(self) -> None:
        """Disable all cleaning motors."""
        if self._robot is None:
            return
        try:
            self._robot.set_side_brush_motor(0)  # type: ignore[attr-defined]
            self._robot.set_main_brush_motor(0)  # type: ignore[attr-defined]
            self._robot.set_vacuum(0)            # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
