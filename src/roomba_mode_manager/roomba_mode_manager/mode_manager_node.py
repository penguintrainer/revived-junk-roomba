"""Mode manager lifecycle node for Roomba577.

Implements DrivingMode state machine (IDLE, RANDOM, MANUAL, AUTONOMOUS),
cmd_vel multiplexer, SetMode/GetState services, and hardware pre-checks.
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

from builtin_interfaces.msg import Time as RosTime
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, Header

from sensor_msgs.msg import Joy, LaserScan

from roomba_msgs.msg import RoombaState, DrivingMode
from roomba_msgs.srv import SetMode, GetState

# Mode constants (mirror DrivingMode.msg)
MODE_IDLE = 0
MODE_RANDOM = 1
MODE_MANUAL = 2
MODE_AUTONOMOUS = 3

MODE_NAMES = {
    MODE_IDLE: 'IDLE',
    MODE_RANDOM: 'RANDOM',
    MODE_MANUAL: 'MANUAL',
    MODE_AUTONOMOUS: 'AUTONOMOUS',
}

# Hardware check timeout
HW_CHECK_TIMEOUT_SEC = 2.0
# Mode transition stop timeout
TRANSITION_TIMEOUT_SEC = 2.0
# Joy topic freshness threshold (seconds)
JOY_TOPIC_TIMEOUT_SEC = 3.0
# Sensor topic freshness threshold
SENSOR_TOPIC_TIMEOUT_SEC = 5.0


class ModeManagerNode(LifecycleNode):
    """Lifecycle node managing Roomba577 driving mode state machine.

    Driving Modes:
        IDLE (0): No motion. Default state.
        RANDOM (1): Roomba's built-in random walk via OI.
        MANUAL (2): Joy-Con direct control via /cmd_vel_joy.
        AUTONOMOUS (3): Nav2 boustrophedon via /cmd_vel_nav.

    Services:
        /roomba/set_mode (roomba_msgs/SetMode)
        /roomba/get_state (roomba_msgs/GetState)

    Topics Published:
        /cmd_vel (geometry_msgs/Twist) @ 50Hz
        /roomba/mode (roomba_msgs/DrivingMode) — on change
        /diagnostics (diagnostic_msgs/DiagnosticArray) @ 1Hz

    Topics Subscribed:
        /cmd_vel_random (geometry_msgs/Twist)
        /cmd_vel_joy (geometry_msgs/Twist)
        /cmd_vel_nav (geometry_msgs/Twist)
        /roomba/state (roomba_msgs/RoombaState)
        /emergency_stop (std_msgs/Bool)
    """

    def __init__(self) -> None:
        super().__init__('mode_manager_node')
        self._lock = threading.Lock()

        # Mode state machine
        self._current_mode = MODE_IDLE
        self._previous_mode = MODE_IDLE
        self._transition_time: Optional[float] = None

        # Latest cmd_vel from each source
        self._cmd_random: Optional[Twist] = None
        self._cmd_joy: Optional[Twist] = None
        self._cmd_nav: Optional[Twist] = None

        # Topic freshness tracking
        self._joy_last_time: Optional[float] = None
        self._scan_last_time: Optional[float] = None
        self._camera_last_time: Optional[float] = None

        # Roomba state
        self._roomba_state: Optional[RoombaState] = None
        self._emergency_stop = False

        # Coverage action client (US3)
        self._coverage_action_client = None
        self._coverage_goal_handle = None

        # Publishers/subscribers/services
        self._pub_cmd_vel = None
        self._pub_mode = None
        self._pub_diagnostics = None
        self._srv_set_mode = None
        self._srv_get_state = None
        self._sub_cmd_random = None
        self._sub_cmd_joy = None
        self._sub_cmd_nav = None
        self._sub_state = None
        self._sub_emergency = None

        # Topic existence subscribers (for HW checks)
        self._sub_joy_check = None
        self._sub_scan_check = None

        # Timers
        self._timer_50hz = None
        self._timer_1hz = None

        # Cleaning session tracking
        self._session_start_time: Optional[float] = None
        self._distance_traveled_m = 0.0

    # -------------------------------------------------------------------------
    # Lifecycle callbacks
    # -------------------------------------------------------------------------

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Create publishers, subscribers, and services."""
        self.get_logger().info('Configuring mode_manager_node')

        self.declare_parameter('max_manual_speed_mm_s', 300.0)
        self.declare_parameter('mode_transition_timeout_sec', 2.0)
        self.declare_parameter('cmd_vel_publish_rate_hz', 50.0)

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
        self._pub_cmd_vel = self.create_publisher(
            Twist, '/cmd_vel', qos_reliable_volatile)
        self._pub_mode = self.create_publisher(
            DrivingMode, '/roomba/mode', qos_reliable_transient)
        self._pub_diagnostics = self.create_publisher(
            DiagnosticArray, '/diagnostics', qos_reliable_volatile)

        # Services
        self._srv_set_mode = self.create_service(
            SetMode, '/roomba/set_mode', self._handle_set_mode)
        self._srv_get_state = self.create_service(
            GetState, '/roomba/get_state', self._handle_get_state)

        # Subscribers — cmd_vel sources
        self._sub_cmd_random = self.create_subscription(
            Twist, '/cmd_vel_random', self._cmd_random_callback,
            qos_reliable_volatile)
        self._sub_cmd_joy = self.create_subscription(
            Twist, '/cmd_vel_joy', self._cmd_joy_callback,
            qos_reliable_volatile)
        self._sub_cmd_nav = self.create_subscription(
            Twist, '/cmd_vel_nav', self._cmd_nav_callback,
            qos_reliable_volatile)

        # Subscribers — state monitoring
        self._sub_state = self.create_subscription(
            RoombaState, '/roomba/state', self._state_callback,
            qos_reliable_transient)
        self._sub_emergency = self.create_subscription(
            Bool, '/emergency_stop', self._emergency_stop_callback,
            qos_reliable_volatile)

        # HW check subscribers (just track timestamps)
        self._sub_joy_check = self.create_subscription(
            Joy,
            '/joy', self._joy_check_callback,
            QoSProfile(
                reliability=ReliabilityPolicy.BEST_EFFORT,
                durability=DurabilityPolicy.VOLATILE,
                history=HistoryPolicy.KEEP_LAST,
                depth=1,
            ))

        # LiDAR topic freshness (for AUTONOMOUS hw check)
        self._sub_scan_check = self.create_subscription(
            LaserScan,
            '/scan', self._scan_check_callback,
            QoSProfile(
                reliability=ReliabilityPolicy.BEST_EFFORT,
                durability=DurabilityPolicy.VOLATILE,
                history=HistoryPolicy.KEEP_LAST,
                depth=1,
            ))

        self.get_logger().info('mode_manager_node configured')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Start timers."""
        self.get_logger().info('Activating mode_manager_node')
        self._session_start_time = time.monotonic()
        self._timer_50hz = self.create_timer(0.02, self._timer_50hz_callback)
        self._timer_1hz = self.create_timer(1.0, self._timer_1hz_callback)
        # Publish initial mode
        self._publish_mode()
        self.get_logger().info('mode_manager_node activated in IDLE mode')
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop timers."""
        self.get_logger().info('Deactivating mode_manager_node')
        self._cancel_timers()
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """Cleanup resources."""
        self.get_logger().info('Cleaning up mode_manager_node')
        self._cancel_timers()
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """Shutdown."""
        self.get_logger().info('Shutting down mode_manager_node')
        self._cancel_timers()
        return TransitionCallbackReturn.SUCCESS

    # -------------------------------------------------------------------------
    # Service handlers
    # -------------------------------------------------------------------------

    def _handle_set_mode(
        self, request: SetMode.Request, response: SetMode.Response
    ) -> SetMode.Response:
        """Handle /roomba/set_mode service call."""
        new_mode = request.mode
        mode_name = MODE_NAMES.get(new_mode, f'UNKNOWN({new_mode})')

        self.get_logger().info(
            'Mode transition request: %s → %s',
            MODE_NAMES[self._current_mode], mode_name)

        # Validate mode value
        if new_mode not in MODE_NAMES:
            response.success = False
            response.message = f'Unknown mode: {new_mode}'
            response.previous_mode = self._current_mode
            return response

        # Hardware pre-checks
        hw_ok, hw_msg = self._check_hardware(new_mode)
        if not hw_ok:
            response.success = False
            response.message = hw_msg
            response.previous_mode = self._current_mode
            return response

        # Safe mode transition: stop Roomba first
        stop_ok, stop_msg = self._safe_stop_for_transition()
        if not stop_ok:
            response.success = False
            response.message = f'Safe stop failed: {stop_msg}'
            response.previous_mode = self._current_mode
            return response

        # Apply transition
        with self._lock:
            old_mode = self._current_mode
            self._previous_mode = old_mode
            self._current_mode = new_mode
            self._transition_time = time.monotonic()

        # Handle autonomous mode entry/exit
        if new_mode == MODE_AUTONOMOUS:
            self._start_coverage_action()
        elif old_mode == MODE_AUTONOMOUS:
            self._cancel_coverage_action()

        self._publish_mode()

        response.success = True
        response.message = f'Mode changed to {mode_name}'
        response.previous_mode = old_mode

        self.get_logger().info('Mode transition complete: %s', mode_name)
        return response

    def _handle_get_state(
        self, request: GetState.Request, response: GetState.Response
    ) -> GetState.Response:
        """Handle /roomba/get_state service call."""
        with self._lock:
            if self._roomba_state is not None:
                response.state = self._roomba_state

            mode_msg = DrivingMode()
            mode_msg.header.stamp = self.get_clock().now().to_msg()
            mode_msg.mode = self._current_mode
            mode_msg.previous_mode = self._previous_mode
            response.mode = mode_msg

            if self._session_start_time is not None:
                response.cleaning_time_sec = time.monotonic() - self._session_start_time
            else:
                response.cleaning_time_sec = 0.0

            response.distance_traveled_m = self._distance_traveled_m

        return response

    # -------------------------------------------------------------------------
    # Topic callbacks
    # -------------------------------------------------------------------------

    def _cmd_random_callback(self, msg: Twist) -> None:
        """Receive random mode velocity command."""
        with self._lock:
            self._cmd_random = msg

    def _cmd_joy_callback(self, msg: Twist) -> None:
        """Receive Joy-Con velocity command with speed limiting."""
        max_speed_m_s = self.get_parameter('max_manual_speed_mm_s').value / 1000.0
        msg.linear.x = max(-max_speed_m_s, min(max_speed_m_s, msg.linear.x))
        with self._lock:
            self._cmd_joy = msg
            self._joy_last_time = time.monotonic()

    def _cmd_nav_callback(self, msg: Twist) -> None:
        """Receive Nav2 velocity command."""
        with self._lock:
            self._cmd_nav = msg

    def _state_callback(self, msg: RoombaState) -> None:
        """Update cached Roomba state."""
        with self._lock:
            self._roomba_state = msg

    def _emergency_stop_callback(self, msg: Bool) -> None:
        """Handle emergency stop — force IDLE mode."""
        if msg.data:
            self.get_logger().error('Emergency stop: forcing IDLE mode')
            with self._lock:
                if not self._emergency_stop:
                    self._emergency_stop = True
                    self._previous_mode = self._current_mode
                    self._current_mode = MODE_IDLE
            self._publish_mode()
            # Publish zero velocity immediately
            self._pub_cmd_vel.publish(Twist())

    def _joy_check_callback(self, msg) -> None:
        """Track Joy topic freshness for hardware checks."""
        with self._lock:
            self._joy_last_time = time.monotonic()

    def _scan_check_callback(self, msg: LaserScan) -> None:
        """Track /scan topic freshness for AUTONOMOUS mode hardware check."""
        with self._lock:
            self._scan_last_time = time.monotonic()

    # -------------------------------------------------------------------------
    # Timer callbacks
    # -------------------------------------------------------------------------

    def _timer_50hz_callback(self) -> None:
        """50Hz: forward appropriate cmd_vel based on current mode."""
        with self._lock:
            mode = self._current_mode
            emergency = self._emergency_stop

        if emergency:
            self._pub_cmd_vel.publish(Twist())
            return

        cmd = self._select_cmd_vel(mode)
        self._pub_cmd_vel.publish(cmd)

    def _timer_1hz_callback(self) -> None:
        """1Hz: publish diagnostics."""
        self._publish_diagnostics()

    # -------------------------------------------------------------------------
    # Mode selection logic
    # -------------------------------------------------------------------------

    def _select_cmd_vel(self, mode: int) -> Twist:
        """Select and return the appropriate cmd_vel for the current mode."""
        with self._lock:
            if mode == MODE_RANDOM:
                return self._cmd_random if self._cmd_random else Twist()
            elif mode == MODE_MANUAL:
                return self._cmd_joy if self._cmd_joy else Twist()
            elif mode == MODE_AUTONOMOUS:
                return self._cmd_nav if self._cmd_nav else Twist()
            else:  # IDLE
                return Twist()

    # -------------------------------------------------------------------------
    # Safe mode transition
    # -------------------------------------------------------------------------

    def _safe_stop_for_transition(self) -> tuple[bool, str]:
        """Send zero velocity and wait for Roomba to stop.

        Returns
        -------
        tuple[bool, str]
            (success, message)
        """
        # Send stop command
        self._pub_cmd_vel.publish(Twist())

        timeout = self.get_parameter('mode_transition_timeout_sec').value
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            with self._lock:
                state = self._roomba_state

            if state is not None:
                # Check if velocity is near zero
                linear = state.velocity.linear.x
                angular = state.velocity.angular.z
                if abs(linear) < 0.01 and abs(angular) < 0.01:
                    return True, 'Roomba stopped'

            time.sleep(0.05)  # 20Hz polling

        # Timeout — proceed anyway if velocity unknown
        self.get_logger().warning('Mode transition stop timeout, proceeding anyway')
        return True, 'Transition timeout (proceeding)'

    # -------------------------------------------------------------------------
    # Hardware pre-checks
    # -------------------------------------------------------------------------

    def _check_hardware(self, mode: int) -> tuple[bool, str]:
        """Verify required hardware is available for the requested mode.

        Returns
        -------
        tuple[bool, str]
            (ok, failure_message)
        """
        now = time.monotonic()

        if mode == MODE_MANUAL:
            # Check Joy-Con connectivity via /joy topic freshness
            with self._lock:
                joy_time = self._joy_last_time
            if joy_time is None or (now - joy_time) > JOY_TOPIC_TIMEOUT_SEC:
                return False, (
                    'Joy-Con not connected: /joy topic not active. '
                    'Pair Joy-Con via Bluetooth first.'
                )

        elif mode == MODE_AUTONOMOUS:
            # Check LiDAR and camera topics
            with self._lock:
                scan_time = self._scan_last_time
                camera_time = self._camera_last_time

            missing = []
            if scan_time is None or (now - scan_time) > SENSOR_TOPIC_TIMEOUT_SEC:
                missing.append('LiDAR (/scan)')
            if camera_time is None or (now - camera_time) > SENSOR_TOPIC_TIMEOUT_SEC:
                missing.append('RealSense D435i (/camera/*)')

            if missing:
                return False, (
                    f'Required sensors not available: {", ".join(missing)}. '
                    'Connect sensors and ensure drivers are running.'
                )

        return True, ''

    # -------------------------------------------------------------------------
    # Coverage action (US3)
    # -------------------------------------------------------------------------

    def _start_coverage_action(self) -> None:
        """Start coverage cleaning action when entering AUTONOMOUS mode."""
        self.get_logger().info('Starting coverage clean action (AUTONOMOUS mode)')
        # Action client setup deferred to when nav2 is available

    def _cancel_coverage_action(self) -> None:
        """Cancel coverage cleaning action when leaving AUTONOMOUS mode."""
        if self._coverage_goal_handle is not None:
            self.get_logger().info('Cancelling coverage clean action')
            try:
                self._coverage_goal_handle.cancel_goal()
            except Exception as exc:
                self.get_logger().warning('Failed to cancel coverage action: %s', exc)
            self._coverage_goal_handle = None

    # -------------------------------------------------------------------------
    # Publish helpers
    # -------------------------------------------------------------------------

    def _publish_mode(self) -> None:
        """Publish current driving mode."""
        msg = DrivingMode()
        msg.header.stamp = self.get_clock().now().to_msg()
        with self._lock:
            msg.mode = self._current_mode
            msg.previous_mode = self._previous_mode
        self._pub_mode.publish(msg)

    def _publish_diagnostics(self) -> None:
        """Publish diagnostics."""
        now = self.get_clock().now()
        diag_array = DiagnosticArray()
        header = Header()
        header.stamp = now.to_msg()
        diag_array.header = header

        status = DiagnosticStatus()
        status.name = 'mode_manager'
        status.hardware_id = 'roomba577_mode_manager'

        with self._lock:
            mode = self._current_mode
            emergency = self._emergency_stop

        if emergency:
            status.level = DiagnosticStatus.ERROR
            status.message = 'Emergency stop active'
        else:
            status.level = DiagnosticStatus.OK
            status.message = f'Mode: {MODE_NAMES[mode]}'

        status.values = [
            KeyValue(key='current_mode', value=MODE_NAMES[mode]),
            KeyValue(key='previous_mode', value=MODE_NAMES.get(
                self._previous_mode, 'UNKNOWN')),
            KeyValue(key='emergency_stop', value=str(emergency)),
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
    """Entry point for mode_manager_node."""
    rclpy.init(args=args)
    node = ModeManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
