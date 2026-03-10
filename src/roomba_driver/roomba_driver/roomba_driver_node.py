"""Roomba577 driver lifecycle node.

Publishes robot state, odometry, sensor data, and TF transforms.
Subscribes to velocity commands and translates them to serial commands.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Optional

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn, State
from rclpy.qos import (
    QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
)

from builtin_interfaces.msg import Time as RosTime
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool, Header
import tf2_ros

from roomba_msgs.msg import RoombaState, Bumper, WheelDrop

from .serial_interface import RoombaSerialInterface, OI_MODE_SAFE

# Roomba577 physical constants
WHEEL_BASE_M = 0.258       # meters between wheel centers
ENCODER_COUNTS_PER_REV = 508.8
WHEEL_DIAMETER_M = 0.072   # meters
WHEEL_CIRCUMFERENCE_M = math.pi * WHEEL_DIAMETER_M
MM_PER_COUNT = (WHEEL_CIRCUMFERENCE_M * 1000.0) / ENCODER_COUNTS_PER_REV


class RoombaDriverNode(LifecycleNode):
    """Lifecycle node for Roomba577 serial communication driver.

    Topics Published:
        /roomba/state (roomba_msgs/RoombaState) @ 10Hz
        /odom (nav_msgs/Odometry) @ 50Hz
        /roomba/bumper (roomba_msgs/Bumper) @ 50Hz
        /roomba/wheel_drop (roomba_msgs/WheelDrop) @ 50Hz
        /roomba/battery (sensor_msgs/BatteryState) @ 1Hz
        /tf (tf2_msgs/TFMessage) @ 50Hz
        /diagnostics (diagnostic_msgs/DiagnosticArray) @ 1Hz

    Topics Subscribed:
        /cmd_vel (geometry_msgs/Twist)
        /emergency_stop (std_msgs/Bool)
    """

    def __init__(self) -> None:
        super().__init__('roomba_driver_node')
        self._serial: Optional[RoombaSerialInterface] = None
        self._lock = threading.Lock()

        # Odometry state
        self._x = 0.0
        self._y = 0.0
        self._theta = 0.0
        self._prev_left_encoder: Optional[int] = None
        self._prev_right_encoder: Optional[int] = None
        self._cleaning_start_time: Optional[float] = None
        self._distance_traveled_m = 0.0

        # Latest cmd_vel
        self._cmd_linear = 0.0
        self._cmd_angular = 0.0
        self._cmd_vel_time: Optional[float] = None
        self._cmd_vel_timeout = 0.5  # seconds

        # Emergency stop flag
        self._emergency_stop = False

        # Publishers (created in on_configure)
        self._pub_state = None
        self._pub_odom = None
        self._pub_bumper = None
        self._pub_wheel_drop = None
        self._pub_battery = None
        self._pub_diagnostics = None
        self._tf_broadcaster = None

        # Subscribers
        self._sub_cmd_vel = None
        self._sub_emergency_stop = None

        # Timers
        self._timer_50hz = None
        self._timer_10hz = None
        self._timer_1hz = None

    # -------------------------------------------------------------------------
    # Lifecycle callbacks
    # -------------------------------------------------------------------------

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Create publishers, subscribers, and serial interface."""
        self.get_logger().info('Configuring roomba_driver_node')

        # Declare parameters
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('oi_mode_workaround', True)
        self.declare_parameter('max_speed_mm_s', 500.0)

        port = self.get_parameter('serial_port').value
        baud = self.get_parameter('baud_rate').value
        workaround = self.get_parameter('oi_mode_workaround').value

        # QoS profiles
        qos_reliable_volatile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        qos_reliable_transient = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # Publishers
        self._pub_state = self.create_publisher(
            RoombaState, '/roomba/state', qos_reliable_transient)
        self._pub_odom = self.create_publisher(
            Odometry, '/odom', qos_reliable_volatile)
        self._pub_bumper = self.create_publisher(
            Bumper, '/roomba/bumper', qos_reliable_volatile)
        self._pub_wheel_drop = self.create_publisher(
            WheelDrop, '/roomba/wheel_drop', qos_reliable_volatile)
        self._pub_battery = self.create_publisher(
            BatteryState, '/roomba/battery', qos_reliable_transient)
        self._pub_diagnostics = self.create_publisher(
            DiagnosticArray, '/diagnostics', qos_reliable_volatile)

        # TF broadcaster
        self._tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # Subscribers
        self._sub_cmd_vel = self.create_subscription(
            Twist, '/cmd_vel', self._cmd_vel_callback, qos_reliable_volatile)
        self._sub_emergency_stop = self.create_subscription(
            Bool, '/emergency_stop', self._emergency_stop_callback,
            qos_reliable_volatile)

        # Serial interface
        self._serial = RoombaSerialInterface(
            port=port, baud_rate=baud, oi_mode_workaround=workaround)

        self.get_logger().info('roomba_driver_node configured')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Connect to Roomba and start publishing timers."""
        self.get_logger().info('Activating roomba_driver_node')

        if not self._serial.connect():
            self.get_logger().error('Failed to connect to Roomba577')
            return TransitionCallbackReturn.FAILURE

        if not self._serial.set_mode_safe():
            self.get_logger().warning('Could not set SAFE mode, continuing anyway')

        self._cleaning_start_time = time.monotonic()
        self._distance_traveled_m = 0.0

        # 50Hz timer: odometry, bumper, wheel_drop, tf, cmd_vel relay
        self._timer_50hz = self.create_timer(0.02, self._timer_50hz_callback)
        # 10Hz timer: state
        self._timer_10hz = self.create_timer(0.1, self._timer_10hz_callback)
        # 1Hz timer: battery, diagnostics
        self._timer_1hz = self.create_timer(1.0, self._timer_1hz_callback)

        self.get_logger().info('roomba_driver_node activated')
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop Roomba and cancel timers."""
        self.get_logger().info('Deactivating roomba_driver_node')

        if self._serial:
            self._serial.stop()

        self._cancel_timers()
        self.get_logger().info('roomba_driver_node deactivated')
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """Disconnect serial and destroy publishers."""
        self.get_logger().info('Cleaning up roomba_driver_node')

        if self._serial:
            self._serial.disconnect()
            self._serial = None

        self._cancel_timers()
        self.get_logger().info('roomba_driver_node cleaned up')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """Emergency shutdown."""
        self.get_logger().info('Shutting down roomba_driver_node')
        if self._serial and self._serial.is_connected:
            self._serial.stop()
            self._serial.disconnect()
        return TransitionCallbackReturn.SUCCESS

    # -------------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------------

    def _cmd_vel_callback(self, msg: Twist) -> None:
        """Handle incoming velocity commands."""
        if self._emergency_stop:
            return
        with self._lock:
            self._cmd_linear = msg.linear.x
            self._cmd_angular = msg.angular.z
            self._cmd_vel_time = time.monotonic()

    def _emergency_stop_callback(self, msg: Bool) -> None:
        """Handle emergency stop signal."""
        if msg.data:
            self.get_logger().warning('Emergency stop received!')
            self._emergency_stop = True
            with self._lock:
                self._cmd_linear = 0.0
                self._cmd_angular = 0.0
            if self._serial:
                self._serial.stop()

    # -------------------------------------------------------------------------
    # Timer callbacks
    # -------------------------------------------------------------------------

    def _timer_50hz_callback(self) -> None:
        """50Hz: send drive command, publish odom/bumper/wheel_drop/tf."""
        if self._serial is None or not self._serial.is_connected:
            return

        sensors = self._serial.get_sensors()
        if sensors is None:
            self.get_logger().warning('Lost serial connection to Roomba577')
            return

        now = self.get_clock().now()

        # Send drive command (with timeout check)
        self._send_drive_command()

        # Publish bumper
        self._publish_bumper(sensors, now)

        # Publish wheel drop
        self._publish_wheel_drop(sensors, now)

        # Update and publish odometry + tf
        self._update_odometry(sensors, now)

    def _timer_10hz_callback(self) -> None:
        """10Hz: publish roomba state."""
        if self._serial is None or not self._serial.is_connected:
            return

        sensors = self._serial.get_sensors()
        if sensors is None:
            return

        now = self.get_clock().now()
        self._publish_state(sensors, now)

    def _timer_1hz_callback(self) -> None:
        """1Hz: publish battery state and diagnostics."""
        if self._serial is None:
            self._publish_diagnostics_disconnected()
            return

        sensors = self._serial.get_sensors()
        now = self.get_clock().now()

        if sensors is not None:
            self._publish_battery(sensors, now)

        self._publish_diagnostics(sensors, now)

    # -------------------------------------------------------------------------
    # Drive commands
    # -------------------------------------------------------------------------

    def _send_drive_command(self) -> None:
        """Send current cmd_vel to Roomba, applying timeout."""
        with self._lock:
            if self._emergency_stop:
                self._serial.stop()
                return

            # Check for command timeout (no new cmd_vel received)
            if self._cmd_vel_time is not None:
                age = time.monotonic() - self._cmd_vel_time
                if age > self._cmd_vel_timeout:
                    self._cmd_linear = 0.0
                    self._cmd_angular = 0.0

            # Convert m/s to mm/s
            linear_mm_s = self._cmd_linear * 1000.0
            angular_rad_s = self._cmd_angular

            # Clamp to max speed
            max_speed = self.get_parameter('max_speed_mm_s').value
            linear_mm_s = max(-max_speed, min(max_speed, linear_mm_s))

            # Differential drive: compute wheel velocities
            half_base = WHEEL_BASE_M * 1000.0 / 2.0  # mm
            right_mm_s = linear_mm_s + angular_rad_s * half_base
            left_mm_s = linear_mm_s - angular_rad_s * half_base

            self._serial.drive_direct(left_mm_s, right_mm_s)

    # -------------------------------------------------------------------------
    # Publish helpers
    # -------------------------------------------------------------------------

    def _publish_bumper(self, sensors: dict, now) -> None:
        """Publish bumper state."""
        msg = Bumper()
        msg.header = self._make_header(now, 'base_link')
        msg.left = bool(sensors.get('bumper_left', False))
        msg.right = bool(sensors.get('bumper_right', False))
        msg.light_left = bool(sensors.get('light_bumper_left', False))
        msg.light_front_left = bool(sensors.get('light_bumper_front_left', False))
        msg.light_center_left = bool(sensors.get('light_bumper_center_left', False))
        msg.light_center_right = bool(sensors.get('light_bumper_center_right', False))
        msg.light_front_right = bool(sensors.get('light_bumper_front_right', False))
        msg.light_right = bool(sensors.get('light_bumper_right', False))
        self._pub_bumper.publish(msg)

    def _publish_wheel_drop(self, sensors: dict, now) -> None:
        """Publish wheel drop state."""
        msg = WheelDrop()
        msg.header = self._make_header(now, 'base_link')
        msg.left = bool(sensors.get('wheel_drop_left', False))
        msg.right = bool(sensors.get('wheel_drop_right', False))
        self._pub_wheel_drop.publish(msg)

    def _update_odometry(self, sensors: dict, now) -> None:
        """Compute and publish odometry from encoder counts."""
        left_enc = int(sensors.get('left_encoder_counts', 0))
        right_enc = int(sensors.get('right_encoder_counts', 0))

        if self._prev_left_encoder is None:
            self._prev_left_encoder = left_enc
            self._prev_right_encoder = right_enc
            return

        # Compute deltas with rollover handling (16-bit signed)
        d_left_counts = self._encoder_delta(left_enc, self._prev_left_encoder)
        d_right_counts = self._encoder_delta(right_enc, self._prev_right_encoder)
        self._prev_left_encoder = left_enc
        self._prev_right_encoder = right_enc

        d_left_mm = d_left_counts * MM_PER_COUNT
        d_right_mm = d_right_counts * MM_PER_COUNT

        d_center_mm = (d_left_mm + d_right_mm) / 2.0
        d_theta_rad = (d_right_mm - d_left_mm) / (WHEEL_BASE_M * 1000.0)

        # Update pose
        self._x += d_center_mm / 1000.0 * math.cos(self._theta + d_theta_rad / 2.0)
        self._y += d_center_mm / 1000.0 * math.sin(self._theta + d_theta_rad / 2.0)
        # Normalize theta to [-π, π) for stable control algorithm behavior
        raw_theta = self._theta + d_theta_rad
        self._theta = math.atan2(math.sin(raw_theta), math.cos(raw_theta))
        self._distance_traveled_m += abs(d_center_mm / 1000.0)

        # Publish odometry
        odom = Odometry()
        odom.header = self._make_header(now, 'odom')
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self._x
        odom.pose.pose.position.y = self._y
        odom.pose.pose.position.z = 0.0
        q = self._yaw_to_quaternion(self._theta)
        odom.pose.pose.orientation.x = q[0]
        odom.pose.pose.orientation.y = q[1]
        odom.pose.pose.orientation.z = q[2]
        odom.pose.pose.orientation.w = q[3]
        self._pub_odom.publish(odom)

        # Publish TF: odom -> base_link
        tf_msg = TransformStamped()
        tf_msg.header = self._make_header(now, 'odom')
        tf_msg.child_frame_id = 'base_link'
        tf_msg.transform.translation.x = self._x
        tf_msg.transform.translation.y = self._y
        tf_msg.transform.translation.z = 0.0
        tf_msg.transform.rotation.x = q[0]
        tf_msg.transform.rotation.y = q[1]
        tf_msg.transform.rotation.z = q[2]
        tf_msg.transform.rotation.w = q[3]
        self._tf_broadcaster.sendTransform(tf_msg)

    def _publish_state(self, sensors: dict, now) -> None:
        """Publish RoombaState message."""
        msg = RoombaState()
        msg.header = self._make_header(now, 'base_link')

        charge = float(sensors.get('battery_charge', 0))
        capacity = float(sensors.get('battery_capacity', 1))
        msg.battery_charge_ratio = charge / capacity if capacity > 0 else 0.0

        msg.bumper_left = bool(sensors.get('bumper_left', False))
        msg.bumper_right = bool(sensors.get('bumper_right', False))
        msg.wheel_drop_left = bool(sensors.get('wheel_drop_left', False))
        msg.wheel_drop_right = bool(sensors.get('wheel_drop_right', False))
        msg.serial_connected = self._serial.is_connected
        msg.oi_mode = int(sensors.get('oi_mode', 0))

        with self._lock:
            msg.velocity.linear.x = self._cmd_linear
            msg.velocity.angular.z = self._cmd_angular

        self._pub_state.publish(msg)

    def _publish_battery(self, sensors: dict, now) -> None:
        """Publish battery state."""
        msg = BatteryState()
        msg.header = self._make_header(now, 'base_link')
        charge = float(sensors.get('battery_charge', 0))
        capacity = float(sensors.get('battery_capacity', 1))
        msg.percentage = (charge / capacity) if capacity > 0 else 0.0
        msg.charge = charge / 1000.0  # mAh to Ah
        msg.capacity = capacity / 1000.0
        msg.present = True
        self._pub_battery.publish(msg)

    def _publish_diagnostics(self, sensors: Optional[dict], now) -> None:
        """Publish diagnostics status."""
        diag_array = DiagnosticArray()
        diag_array.header = self._make_header(now, '')

        status = DiagnosticStatus()
        status.name = 'roomba_driver'
        status.hardware_id = 'roomba577'

        if sensors is not None and self._serial and self._serial.is_connected:
            status.level = DiagnosticStatus.OK
            status.message = 'Roomba driver operational'
            charge = float(sensors.get('battery_charge', 0))
            capacity = float(sensors.get('battery_capacity', 1))
            ratio = charge / capacity if capacity > 0 else 0.0
            status.values = [
                KeyValue(key='connected', value='true'),
                KeyValue(key='oi_mode', value=str(sensors.get('oi_mode', 0))),
                KeyValue(key='battery_ratio', value=f'{ratio:.2f}'),
                KeyValue(key='emergency_stop', value=str(self._emergency_stop)),
            ]
        else:
            status.level = DiagnosticStatus.ERROR
            status.message = 'Roomba not connected'
            status.values = [KeyValue(key='connected', value='false')]

        diag_array.status = [status]
        self._pub_diagnostics.publish(diag_array)

    def _publish_diagnostics_disconnected(self) -> None:
        """Publish disconnected diagnostics."""
        now = self.get_clock().now()
        diag_array = DiagnosticArray()
        diag_array.header = self._make_header(now, '')
        status = DiagnosticStatus()
        status.name = 'roomba_driver'
        status.hardware_id = 'roomba577'
        status.level = DiagnosticStatus.ERROR
        status.message = 'Serial interface not initialized'
        diag_array.status = [status]
        self._pub_diagnostics.publish(diag_array)

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

    def _cancel_timers(self) -> None:
        """Cancel all active timers."""
        for timer_attr in ('_timer_50hz', '_timer_10hz', '_timer_1hz'):
            timer = getattr(self, timer_attr, None)
            if timer is not None:
                timer.cancel()
                setattr(self, timer_attr, None)

    @staticmethod
    def _make_header(now, frame_id: str) -> Header:
        """Create a ROS Header."""
        header = Header()
        header.stamp = now.to_msg()
        header.frame_id = frame_id
        return header

    @staticmethod
    def _yaw_to_quaternion(yaw: float) -> tuple:
        """Convert yaw angle to quaternion (x, y, z, w)."""
        half = yaw / 2.0
        return (0.0, 0.0, math.sin(half), math.cos(half))

    @staticmethod
    def _encoder_delta(current: int, previous: int) -> int:
        """Compute signed encoder delta handling 16-bit rollover."""
        delta = current - previous
        # Handle 16-bit signed rollover
        if delta > 32767:
            delta -= 65536
        elif delta < -32768:
            delta += 65536
        return delta


def main(args=None) -> None:
    """Entry point for roomba_driver_node."""
    rclpy.init(args=args)
    node = RoombaDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
