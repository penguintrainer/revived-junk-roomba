"""Joy-Con teleoperation lifecycle node for Roomba577 manual control.

Subscribes to /joy (sensor_msgs/Joy) from the joy_node driver,
translates Joy-Con left stick to Twist commands with 300mm/s speed limit,
and publishes to /cmd_vel_joy at 50Hz.

Also handles Joy-Con button mapping for mode switching and emergency stop.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn, State
from rclpy.qos import (
    QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
)

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from std_srvs.srv import Trigger

from roomba_msgs.srv import SetMode

# Joy-Con Left (horizontal hold) axis/button mapping
# When Joy-Con L is held horizontally:
#   Axis 0: left/right (left stick, or single horizontal axis)
#   Axis 1: up/down (forward/backward motion)
# Buttons (Joy-Con L horizontal):
#   Button 0: Left button (←) → switch to MANUAL mode
#   Button 1: Down button (↓) → switch to RANDOM mode
#   Button 2: Up button (↑) → switch to AUTONOMOUS mode
#   Button 3: Right button (→) → switch to IDLE
#   Button 4: SL button → emergency stop
#   Button 5: SR button → emergency stop (redundant)
AXIS_LINEAR = 1    # Left stick vertical (forward/backward)
AXIS_ANGULAR = 0   # Left stick horizontal (rotate)

BUTTON_MODE_MANUAL = 0      # ← Joy-Con L left button
BUTTON_MODE_RANDOM = 1      # ↓ Joy-Con L down button
BUTTON_MODE_AUTONOMOUS = 2  # ↑ Joy-Con L up button
BUTTON_MODE_IDLE = 3        # → Joy-Con L right button
BUTTON_EMERGENCY_STOP_1 = 4  # SL
BUTTON_EMERGENCY_STOP_2 = 5  # SR

# Mode constants
MODE_IDLE = 0
MODE_RANDOM = 1
MODE_MANUAL = 2
MODE_AUTONOMOUS = 3

# Deadzone for analog stick input
DEADZONE = 0.1

# Disconnect detection timeout
JOY_TIMEOUT_SEC = 3.0


class JoyconTeleopNode(LifecycleNode):
    """Lifecycle node for Joy-Con teleoperation.

    Translates Joy-Con inputs to Roomba velocity commands with:
    - 300mm/s maximum linear speed limit
    - Analog deadzone compensation
    - Joy-Con disconnect detection
    - Button-based mode switching

    Topics Subscribed:
        /joy (sensor_msgs/Joy) @ 50Hz

    Topics Published:
        /cmd_vel_joy (geometry_msgs/Twist) @ 50Hz
        /diagnostics (diagnostic_msgs/DiagnosticArray) @ 1Hz

    Services Called:
        /roomba/set_mode (roomba_msgs/SetMode)
        /roomba/emergency_stop (std_srvs/Trigger)
    """

    def __init__(self) -> None:
        super().__init__('joycon_teleop_node')
        self._lock = threading.Lock()

        # Latest joy state
        self._joy_msg: Optional[Joy] = None
        self._joy_last_time: Optional[float] = None
        self._connected = False

        # Button state tracking (for edge detection)
        self._prev_buttons: list[int] = []

        # Publishers/subscribers
        self._pub_cmd_vel_joy = None
        self._pub_diagnostics = None
        self._sub_joy = None

        # Service clients
        self._cli_set_mode = None
        self._cli_emergency_stop = None

        # Timers
        self._timer_50hz = None
        self._timer_1hz = None

    # -------------------------------------------------------------------------
    # Lifecycle callbacks
    # -------------------------------------------------------------------------

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Create publishers, subscribers, service clients."""
        self.get_logger().info('Configuring joycon_teleop_node')

        self.declare_parameter('max_linear_speed_m_s', 0.3)      # 300mm/s
        self.declare_parameter('max_angular_speed_rad_s', 4.25)
        self.declare_parameter('deadzone', DEADZONE)
        self.declare_parameter('joy_timeout_sec', JOY_TIMEOUT_SEC)

        qos_reliable_volatile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        qos_best_effort = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # Publishers
        self._pub_cmd_vel_joy = self.create_publisher(
            Twist, '/cmd_vel_joy', qos_reliable_volatile)
        self._pub_diagnostics = self.create_publisher(
            DiagnosticArray, '/diagnostics', qos_reliable_volatile)

        # Subscriber
        self._sub_joy = self.create_subscription(
            Joy, '/joy', self._joy_callback, qos_best_effort)

        # Service clients
        self._cli_set_mode = self.create_client(SetMode, '/roomba/set_mode')
        self._cli_emergency_stop = self.create_client(Trigger, '/roomba/emergency_stop')

        self.get_logger().info('joycon_teleop_node configured')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Start timers."""
        self.get_logger().info('Activating joycon_teleop_node')
        self._timer_50hz = self.create_timer(0.02, self._timer_50hz_callback)
        self._timer_1hz = self.create_timer(1.0, self._timer_1hz_callback)
        self.get_logger().info('joycon_teleop_node activated')
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop timers and publish zero velocity."""
        self.get_logger().info('Deactivating joycon_teleop_node')
        self._cancel_timers()
        self._pub_cmd_vel_joy.publish(Twist())
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """Cleanup."""
        self.get_logger().info('Cleaning up joycon_teleop_node')
        self._cancel_timers()
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """Shutdown."""
        self.get_logger().info('Shutting down joycon_teleop_node')
        self._cancel_timers()
        return TransitionCallbackReturn.SUCCESS

    # -------------------------------------------------------------------------
    # Topic callbacks
    # -------------------------------------------------------------------------

    def _joy_callback(self, msg: Joy) -> None:
        """Process incoming Joy message."""
        with self._lock:
            # Edge-detect button presses for mode switching
            self._handle_button_presses(msg)
            self._joy_msg = msg
            self._joy_last_time = time.monotonic()
            self._connected = True

    # -------------------------------------------------------------------------
    # Button handling
    # -------------------------------------------------------------------------

    def _handle_button_presses(self, msg: Joy) -> None:
        """Detect button press edges and trigger mode/emergency actions."""
        buttons = list(msg.buttons)

        # Skip if we don't have previous state
        if not self._prev_buttons:
            self._prev_buttons = buttons
            return

        # Check each button for rising edge
        for i, (prev, curr) in enumerate(zip(self._prev_buttons, buttons)):
            if prev == 0 and curr == 1:
                self._handle_button_press(i)

        self._prev_buttons = buttons

    def _handle_button_press(self, button_index: int) -> None:
        """Handle a specific button press (called with lock held)."""
        if button_index in (BUTTON_EMERGENCY_STOP_1, BUTTON_EMERGENCY_STOP_2):
            self.get_logger().warning('Joy-Con emergency stop button pressed!')
            self._call_emergency_stop()
        elif button_index == BUTTON_MODE_IDLE:
            self.get_logger().info('Joy-Con: switching to IDLE mode')
            self._call_set_mode(MODE_IDLE)
        elif button_index == BUTTON_MODE_RANDOM:
            self.get_logger().info('Joy-Con: switching to RANDOM mode')
            self._call_set_mode(MODE_RANDOM)
        elif button_index == BUTTON_MODE_MANUAL:
            self.get_logger().info('Joy-Con: switching to MANUAL mode')
            self._call_set_mode(MODE_MANUAL)
        elif button_index == BUTTON_MODE_AUTONOMOUS:
            self.get_logger().info('Joy-Con: switching to AUTONOMOUS mode')
            self._call_set_mode(MODE_AUTONOMOUS)

    # -------------------------------------------------------------------------
    # Timer callbacks
    # -------------------------------------------------------------------------

    def _timer_50hz_callback(self) -> None:
        """50Hz: publish cmd_vel_joy from current joy state."""
        timeout = self.get_parameter('joy_timeout_sec').value

        with self._lock:
            joy = self._joy_msg
            joy_time = self._joy_last_time

        # Check for disconnect
        if joy is None or joy_time is None:
            self._pub_cmd_vel_joy.publish(Twist())
            return

        age = time.monotonic() - joy_time
        if age > timeout:
            if self._connected:
                self.get_logger().warning(
                    'Joy-Con disconnected (no message for %.1fs)', age)
                self._connected = False
            self._pub_cmd_vel_joy.publish(Twist())
            return

        self._connected = True
        twist = self._joy_to_twist(joy)
        self._pub_cmd_vel_joy.publish(twist)

    def _timer_1hz_callback(self) -> None:
        """1Hz: publish diagnostics."""
        self._publish_diagnostics()

    # -------------------------------------------------------------------------
    # Joy → Twist conversion
    # -------------------------------------------------------------------------

    def _joy_to_twist(self, joy: Joy) -> Twist:
        """Convert Joy message to Twist command with deadzone and speed limiting.

        Parameters
        ----------
        joy : Joy
            Input Joy message from joy_node.

        Returns
        -------
        Twist
            Velocity command with limits applied.
        """
        max_linear = self.get_parameter('max_linear_speed_m_s').value
        max_angular = self.get_parameter('max_angular_speed_rad_s').value
        deadzone = self.get_parameter('deadzone').value

        # Get axis values safely
        axes = joy.axes
        linear_raw = self._safe_axis(axes, AXIS_LINEAR)
        angular_raw = self._safe_axis(axes, AXIS_ANGULAR)

        # Apply deadzone
        linear_raw = self._apply_deadzone(linear_raw, deadzone)
        angular_raw = self._apply_deadzone(angular_raw, deadzone)

        # Scale to max speeds
        twist = Twist()
        twist.linear.x = linear_raw * max_linear
        twist.angular.z = angular_raw * max_angular

        return twist

    @staticmethod
    def _safe_axis(axes: list, index: int) -> float:
        """Safely get axis value, returning 0.0 if out of range."""
        if index < len(axes):
            return float(axes[index])
        return 0.0

    @staticmethod
    def _apply_deadzone(value: float, deadzone: float) -> float:
        """Apply deadzone and rescale remaining range.

        Parameters
        ----------
        value : float
            Raw axis value in [-1, 1].
        deadzone : float
            Deadzone threshold (0.0 to 1.0).

        Returns
        -------
        float
            Processed value with deadzone applied and range rescaled.
        """
        if abs(value) < deadzone:
            return 0.0
        # Rescale to maintain full range outside deadzone
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - deadzone) / (1.0 - deadzone)

    # -------------------------------------------------------------------------
    # Service calls (async fire-and-forget)
    # -------------------------------------------------------------------------

    def _call_set_mode(self, mode: int) -> None:
        """Call /roomba/set_mode service asynchronously."""
        if not self._cli_set_mode.service_is_ready():
            self.get_logger().warning('SetMode service not available')
            return
        req = SetMode.Request()
        req.mode = mode
        future = self._cli_set_mode.call_async(req)
        future.add_done_callback(self._set_mode_done_callback)

    def _set_mode_done_callback(self, future) -> None:
        """Handle set_mode response."""
        try:
            result = future.result()
            if result.success:
                self.get_logger().info('Mode switch: %s', result.message)
            else:
                self.get_logger().warning('Mode switch failed: %s', result.message)
        except Exception as exc:
            self.get_logger().error('SetMode service call failed: %s', exc)

    def _call_emergency_stop(self) -> None:
        """Call /roomba/emergency_stop service asynchronously."""
        if not self._cli_emergency_stop.service_is_ready():
            self.get_logger().warning('EmergencyStop service not available')
            return
        req = Trigger.Request()
        future = self._cli_emergency_stop.call_async(req)
        future.add_done_callback(self._emergency_stop_done_callback)

    def _emergency_stop_done_callback(self, future) -> None:
        """Handle emergency stop response."""
        try:
            result = future.result()
            self.get_logger().warning('Emergency stop: %s', result.message)
        except Exception as exc:
            self.get_logger().error('EmergencyStop service call failed: %s', exc)

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    def _publish_diagnostics(self) -> None:
        """Publish diagnostics."""
        now = self.get_clock().now()
        diag_array = DiagnosticArray()
        from std_msgs.msg import Header
        header = Header()
        header.stamp = now.to_msg()
        diag_array.header = header

        status = DiagnosticStatus()
        status.name = 'joycon_teleop'
        status.hardware_id = 'nintendo_joycon_l'

        timeout = self.get_parameter('joy_timeout_sec').value
        with self._lock:
            connected = self._connected
            joy_time = self._joy_last_time

        age = (time.monotonic() - joy_time) if joy_time is not None else float('inf')

        if connected and age <= timeout:
            status.level = DiagnosticStatus.OK
            status.message = f'Joy-Con connected (last msg: {age:.1f}s ago)'
        else:
            status.level = DiagnosticStatus.WARN
            status.message = 'Joy-Con disconnected or not publishing'

        status.values = [
            KeyValue(key='connected', value=str(connected)),
            KeyValue(key='last_msg_age_sec', value=f'{age:.2f}'),
        ]

        diag_array.status = [status]
        self._pub_diagnostics.publish(diag_array)

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _cancel_timers(self) -> None:
        """Cancel all active timers."""
        for attr in ('_timer_50hz', '_timer_1hz'):
            timer = getattr(self, attr, None)
            if timer is not None:
                timer.cancel()
                setattr(self, attr, None)


def main(args=None) -> None:
    """Entry point for joycon_teleop_node."""
    rclpy.init(args=args)
    node = JoyconTeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
