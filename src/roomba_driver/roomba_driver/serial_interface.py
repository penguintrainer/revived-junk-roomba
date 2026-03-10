"""Serial interface wrapping create_robot for Roomba577 OI v2.0 at 115200 baud."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Constants for Roomba OI modes
OI_MODE_OFF = 0
OI_MODE_PASSIVE = 1
OI_MODE_SAFE = 2
OI_MODE_FULL = 3


class RoombaSerialInterface:
    """Wraps the create_robot library for Roomba577 serial communication.

    Provides a thread-safe interface for controlling the Roomba577 via
    the Open Interface (OI) protocol at 115200 baud.

    Parameters
    ----------
    port : str
        Serial port path (e.g. '/dev/ttyUSB0').
    baud_rate : int
        Baud rate for serial communication. Default: 115200.
    oi_mode_workaround : bool
        Enable OI mode workaround for Roomba577 firmware quirks.
    """

    def __init__(
        self,
        port: str = '/dev/ttyUSB0',
        baud_rate: int = 115200,
        oi_mode_workaround: bool = True,
    ) -> None:
        self._port = port
        self._baud_rate = baud_rate
        self._oi_mode_workaround = oi_mode_workaround
        self._robot: Optional[object] = None
        self._lock = threading.Lock()
        self._connected = False
        self._oi_mode = OI_MODE_OFF

    @property
    def is_connected(self) -> bool:
        """Return True if serial connection is active."""
        return self._connected

    @property
    def oi_mode(self) -> int:
        """Return current OI mode (0=OFF, 1=PASSIVE, 2=SAFE, 3=FULL)."""
        return self._oi_mode

    def connect(self) -> bool:
        """Open serial connection to Roomba577.

        Returns
        -------
        bool
            True on success, False on failure.
        """
        with self._lock:
            try:
                from create_robot import Robot  # type: ignore[import]
                self._robot = Robot(port=self._port, baud=self._baud_rate)
                self._connected = True
                logger.info(
                    'Connected to Roomba577 on %s at %d baud',
                    self._port, self._baud_rate,
                )
                if self._oi_mode_workaround:
                    self._apply_oi_mode_workaround()
                return True
            except Exception as exc:
                logger.error('Failed to connect to Roomba577: %s', exc)
                self._connected = False
                return False

    def disconnect(self) -> None:
        """Close serial connection."""
        with self._lock:
            if self._robot is not None:
                try:
                    self._robot.disconnect()
                except Exception as exc:
                    logger.warning('Error during disconnect: %s', exc)
                finally:
                    self._robot = None
            self._connected = False
            self._oi_mode = OI_MODE_OFF
            logger.info('Disconnected from Roomba577')

    def _apply_oi_mode_workaround(self) -> None:
        """Apply OI mode workaround for Roomba577 firmware quirks.

        The Roomba577 sometimes requires a short delay and explicit
        mode transition sequence to reliably enter SAFE/FULL mode.
        """
        try:
            # Brief delay to allow OI to stabilize after connection
            time.sleep(0.1)
            if self._robot is not None:
                # Transition through PASSIVE to avoid mode lock-up
                self._robot.start()
                time.sleep(0.05)
            logger.debug('OI mode workaround applied')
        except Exception as exc:
            logger.warning('OI mode workaround failed: %s', exc)

    def set_mode_passive(self) -> bool:
        """Set Roomba to PASSIVE OI mode."""
        return self._set_mode(OI_MODE_PASSIVE, lambda r: r.start())

    def set_mode_safe(self) -> bool:
        """Set Roomba to SAFE OI mode."""
        return self._set_mode(OI_MODE_SAFE, lambda r: r.safe())

    def set_mode_full(self) -> bool:
        """Set Roomba to FULL OI mode."""
        return self._set_mode(OI_MODE_FULL, lambda r: r.full())

    def _set_mode(self, mode: int, mode_fn) -> bool:
        """Internal helper to transition OI mode."""
        with self._lock:
            if not self._connected or self._robot is None:
                logger.error('Cannot set mode: not connected')
                return False
            try:
                mode_fn(self._robot)
                self._oi_mode = mode
                logger.debug('OI mode set to %d', mode)
                return True
            except Exception as exc:
                logger.error('Failed to set OI mode %d: %s', mode, exc)
                return False

    def drive(self, linear_mm_s: float, angular_rad_s: float) -> bool:
        """Send drive command to Roomba577.

        Parameters
        ----------
        linear_mm_s : float
            Linear velocity in mm/s. Range: -500 to 500.
        angular_rad_s : float
            Angular velocity in rad/s.

        Returns
        -------
        bool
            True on success.
        """
        with self._lock:
            if not self._connected or self._robot is None:
                return False
            try:
                # Clamp to Roomba577 hardware limits
                linear_mm_s = max(-500.0, min(500.0, linear_mm_s))
                self._robot.drive(velocity=linear_mm_s, radius=self._angular_to_radius(
                    linear_mm_s, angular_rad_s))
                return True
            except Exception as exc:
                logger.error('Drive command failed: %s', exc)
                return False

    def drive_direct(self, left_mm_s: float, right_mm_s: float) -> bool:
        """Send direct wheel velocity commands.

        Parameters
        ----------
        left_mm_s : float
            Left wheel velocity in mm/s.
        right_mm_s : float
            Right wheel velocity in mm/s.

        Returns
        -------
        bool
            True on success.
        """
        with self._lock:
            if not self._connected or self._robot is None:
                return False
            try:
                left_mm_s = max(-500.0, min(500.0, left_mm_s))
                right_mm_s = max(-500.0, min(500.0, right_mm_s))
                self._robot.drive_direct(left_velocity=left_mm_s, right_velocity=right_mm_s)
                return True
            except Exception as exc:
                logger.error('Drive direct command failed: %s', exc)
                return False

    def stop(self) -> bool:
        """Stop Roomba movement immediately."""
        with self._lock:
            if not self._connected or self._robot is None:
                return False
            try:
                self._robot.drive_direct(left_velocity=0, right_velocity=0)
                return True
            except Exception as exc:
                logger.error('Stop command failed: %s', exc)
                return False

    def get_sensors(self) -> Optional[dict]:
        """Read sensor packet from Roomba.

        Returns
        -------
        dict or None
            Dictionary with sensor values, or None on failure.
        """
        with self._lock:
            if not self._connected or self._robot is None:
                return None
            try:
                return {
                    'battery_charge': self._safe_sensor('battery_charge', 0),
                    'battery_capacity': self._safe_sensor('battery_capacity', 1),
                    'bumper_left': self._safe_sensor('bumper_left', False),
                    'bumper_right': self._safe_sensor('bumper_right', False),
                    'wheel_drop_left': self._safe_sensor('wheel_drop_left', False),
                    'wheel_drop_right': self._safe_sensor('wheel_drop_right', False),
                    'light_bumper_left': self._safe_sensor('light_bumper_left', False),
                    'light_bumper_front_left': self._safe_sensor('light_bumper_front_left', False),
                    'light_bumper_center_left': self._safe_sensor(
                        'light_bumper_center_left', False),
                    'light_bumper_center_right': self._safe_sensor(
                        'light_bumper_center_right', False),
                    'light_bumper_front_right': self._safe_sensor(
                        'light_bumper_front_right', False),
                    'light_bumper_right': self._safe_sensor('light_bumper_right', False),
                    'left_encoder_counts': self._safe_sensor('left_encoder_counts', 0),
                    'right_encoder_counts': self._safe_sensor('right_encoder_counts', 0),
                    'velocity_left': self._safe_sensor('velocity_left', 0),
                    'velocity_right': self._safe_sensor('velocity_right', 0),
                    'oi_mode': self._oi_mode,
                }
            except Exception as exc:
                logger.error('Failed to read sensors: %s', exc)
                self._connected = False
                return None

    def _safe_sensor(self, sensor_name: str, default):
        """Safely read a single sensor value."""
        try:
            return getattr(self._robot.sensors, sensor_name)
        except AttributeError:
            try:
                return self._robot.sensors[sensor_name]
            except (KeyError, TypeError):
                return default

    @staticmethod
    def _angular_to_radius(linear_mm_s: float, angular_rad_s: float) -> float:
        """Convert angular velocity to Roomba turning radius.

        Parameters
        ----------
        linear_mm_s : float
            Linear velocity in mm/s.
        angular_rad_s : float
            Angular velocity in rad/s.

        Returns
        -------
        float
            Turning radius in mm. Special values: 32767=straight, ±1=spin.
        """
        if abs(angular_rad_s) < 1e-6:
            return 32767.0  # Drive straight
        if abs(linear_mm_s) < 1e-6:
            # Pure rotation: use special values
            return 1.0 if angular_rad_s > 0 else -1.0
        # Turning radius: R = v / omega
        radius = linear_mm_s / angular_rad_s
        # Clamp to valid range (-2000 to 2000, excluding 0)
        radius = max(-2000.0, min(2000.0, radius))
        if abs(radius) < 1.0:
            radius = 1.0 if radius >= 0 else -1.0
        return radius
