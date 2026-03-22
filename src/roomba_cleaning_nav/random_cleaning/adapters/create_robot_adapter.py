"""Create-robot serial control adapter stub.

Wraps the create_robot library (or simulates it when unavailable) to provide
a clean boundary between ROS2 business logic and hardware I/O.
"""
from __future__ import annotations

from typing import Optional

try:
    import create_robot  # type: ignore
    _HAS_CREATE = True
except ImportError:
    _HAS_CREATE = False


class CreateRobotAdapter:
    """Minimal adapter for the Roomba577 via create_robot serial library."""

    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200) -> None:
        self._port = port
        self._baud = baud
        self._robot: Optional[object] = None
        self._connected = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Open serial connection to the robot. Returns True on success."""
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
        if self._robot is not None and _HAS_CREATE:
            try:
                getattr(self._robot, "stop", lambda: None)()
            except Exception:  # noqa: BLE001
                pass
        self._robot = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Motion
    # ------------------------------------------------------------------

    def set_velocity(self, linear: float, angular: float) -> None:
        """Send velocity command. No-op if not connected."""
        if self._robot is None:
            return
        try:
            self._robot.drive_direct(linear, angular)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            self._connected = False

    def stop(self) -> None:
        """Immediately stop all motion."""
        self.set_velocity(0.0, 0.0)

    # ------------------------------------------------------------------
    # Cleaning motors
    # ------------------------------------------------------------------

    def enable_cleaning(self) -> None:
        """Enable side brush, main brush, and vacuum."""
        if self._robot is None:
            return
        try:
            self._robot.start_cleaning()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    def disable_cleaning(self) -> None:
        """Disable all cleaning motors."""
        if self._robot is None:
            return
        try:
            self._robot.stop_cleaning()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Docking
    # ------------------------------------------------------------------

    def dock(self) -> None:
        """Issue dock-seek command."""
        if self._robot is None:
            return
        try:
            self._robot.seek_dock()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Sensors
    # ------------------------------------------------------------------

    def get_battery_percent(self) -> Optional[float]:
        """Return battery charge as a percentage (0-100), or None."""
        if self._robot is None:
            return None
        try:
            sensors = self._robot.sensors  # type: ignore[attr-defined]
            capacity = sensors.battery_capacity
            charge = sensors.battery_charge
            if capacity and capacity > 0:
                return min(100.0, (charge / capacity) * 100.0)
            return None
        except Exception:  # noqa: BLE001
            return None
