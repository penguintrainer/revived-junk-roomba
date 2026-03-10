"""Safety monitor lifecycle node for Roomba577.

Monitors serial connection, wheel drop, battery level, and AMCL localization
quality. Provides emergency stop service and publishes safety status.
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
from geometry_msgs.msg import PoseWithCovarianceStamped
from std_msgs.msg import Bool, Header
from std_srvs.srv import Trigger

from roomba_msgs.msg import RoombaState, Bumper, WheelDrop

# Safety thresholds
BATTERY_LOW_THRESHOLD = 0.15       # 15% battery triggers warning
BATTERY_CRITICAL_THRESHOLD = 0.05  # 5% triggers emergency stop
AMCL_COVARIANCE_LIMIT = 0.5        # m^2 (xx + yy > this → localization lost)
WHEEL_DROP_STOP_DELAY = 0.0        # Immediate stop on wheel drop


class SafetyMonitorNode(LifecycleNode):
    """Lifecycle node that monitors Roomba577 safety conditions.

    Monitors:
        - Serial connection loss
        - Wheel drop events
        - Battery low / critical
        - AMCL localization covariance (US3)

    Services:
        /roomba/emergency_stop (std_srvs/Trigger)

    Topics Published:
        /emergency_stop (std_msgs/Bool) — on event
        /diagnostics (diagnostic_msgs/DiagnosticArray) @ 1Hz

    Topics Subscribed:
        /roomba/state (roomba_msgs/RoombaState)
        /roomba/bumper (roomba_msgs/Bumper)
        /roomba/wheel_drop (roomba_msgs/WheelDrop)
        /amcl_pose (geometry_msgs/PoseWithCovarianceStamped)
    """

    def __init__(self) -> None:
        super().__init__('safety_monitor_node')
        self._lock = threading.Lock()

        # Safety state
        self._emergency_active = False
        self._serial_connected = False
        self._wheel_drop_left = False
        self._wheel_drop_right = False
        self._battery_ratio = 1.0
        self._amcl_covariance = 0.0
        self._last_state_time: Optional[float] = None
        self._state_timeout = 5.0  # seconds without state = serial disconnect

        # Publishers/subscribers (created in on_configure)
        self._pub_emergency_stop = None
        self._pub_diagnostics = None
        self._srv_emergency_stop = None
        self._sub_state = None
        self._sub_bumper = None
        self._sub_wheel_drop = None
        self._sub_amcl = None
        self._timer_1hz = None

    # -------------------------------------------------------------------------
    # Lifecycle callbacks
    # -------------------------------------------------------------------------

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Create publishers, subscribers, and service."""
        self.get_logger().info('Configuring safety_monitor_node')

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
        qos_best_effort = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        # Publishers
        self._pub_emergency_stop = self.create_publisher(
            Bool, '/emergency_stop', qos_reliable_volatile)
        self._pub_diagnostics = self.create_publisher(
            DiagnosticArray, '/diagnostics', qos_reliable_volatile)

        # Service
        self._srv_emergency_stop = self.create_service(
            Trigger, '/roomba/emergency_stop', self._handle_emergency_stop)

        # Subscribers
        self._sub_state = self.create_subscription(
            RoombaState, '/roomba/state', self._state_callback,
            qos_reliable_transient)
        self._sub_bumper = self.create_subscription(
            Bumper, '/roomba/bumper', self._bumper_callback,
            qos_reliable_volatile)
        self._sub_wheel_drop = self.create_subscription(
            WheelDrop, '/roomba/wheel_drop', self._wheel_drop_callback,
            qos_reliable_volatile)
        self._sub_amcl = self.create_subscription(
            PoseWithCovarianceStamped, '/amcl_pose', self._amcl_pose_callback,
            qos_best_effort)

        self.get_logger().info('safety_monitor_node configured')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Start monitoring timers."""
        self.get_logger().info('Activating safety_monitor_node')
        self._timer_1hz = self.create_timer(1.0, self._timer_1hz_callback)
        self.get_logger().info('safety_monitor_node activated')
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop monitoring."""
        self.get_logger().info('Deactivating safety_monitor_node')
        if self._timer_1hz is not None:
            self._timer_1hz.cancel()
            self._timer_1hz = None
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """Clean up resources."""
        self.get_logger().info('Cleaning up safety_monitor_node')
        if self._timer_1hz is not None:
            self._timer_1hz.cancel()
            self._timer_1hz = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """Shutdown."""
        self.get_logger().info('Shutting down safety_monitor_node')
        return TransitionCallbackReturn.SUCCESS

    # -------------------------------------------------------------------------
    # Service handlers
    # -------------------------------------------------------------------------

    def _handle_emergency_stop(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /roomba/emergency_stop service call."""
        self.get_logger().warning('Emergency stop triggered via service!')
        self._trigger_emergency_stop('Manual emergency stop via service')
        response.success = True
        response.message = 'Emergency stop activated'
        return response

    # -------------------------------------------------------------------------
    # Topic callbacks
    # -------------------------------------------------------------------------

    def _state_callback(self, msg: RoombaState) -> None:
        """Monitor Roomba state for safety conditions."""
        with self._lock:
            self._last_state_time = time.monotonic()
            self._serial_connected = msg.serial_connected
            self._battery_ratio = msg.battery_charge_ratio

            # Check battery critical level
            if msg.battery_charge_ratio < BATTERY_CRITICAL_THRESHOLD:
                self.get_logger().error(
                    'Battery critically low: %.1f%%', msg.battery_charge_ratio * 100)
                self._trigger_emergency_stop_locked('Battery critically low')
            elif msg.battery_charge_ratio < BATTERY_LOW_THRESHOLD:
                self.get_logger().warning(
                    'Battery low: %.1f%%', msg.battery_charge_ratio * 100)

    def _bumper_callback(self, msg: Bumper) -> None:
        """Log bumper events (not an emergency stop condition)."""
        if msg.left or msg.right:
            self.get_logger().debug(
                'Bumper contact: left=%s right=%s', msg.left, msg.right)

    def _wheel_drop_callback(self, msg: WheelDrop) -> None:
        """Handle wheel drop — immediate emergency stop."""
        with self._lock:
            if msg.left or msg.right:
                if not self._emergency_active:
                    self.get_logger().error(
                        'Wheel drop detected! left=%s right=%s', msg.left, msg.right)
                    self._trigger_emergency_stop_locked(
                        f'Wheel drop: left={msg.left} right={msg.right}')
                self._wheel_drop_left = msg.left
                self._wheel_drop_right = msg.right

    def _amcl_pose_callback(self, msg: PoseWithCovarianceStamped) -> None:
        """Monitor AMCL localization covariance (US3)."""
        cov = msg.pose.covariance
        # Position covariance: xx is index 0, yy is index 7
        pos_covariance = cov[0] + cov[7]
        with self._lock:
            self._amcl_covariance = pos_covariance
            if pos_covariance > AMCL_COVARIANCE_LIMIT:
                self.get_logger().error(
                    'Localization lost! AMCL covariance: %.3f m² > %.1f m²',
                    pos_covariance, AMCL_COVARIANCE_LIMIT)
                self._trigger_emergency_stop_locked(
                    f'Localization lost: covariance={pos_covariance:.3f}m²')

    # -------------------------------------------------------------------------
    # Timer callbacks
    # -------------------------------------------------------------------------

    def _timer_1hz_callback(self) -> None:
        """1Hz: check serial timeout and publish diagnostics."""
        with self._lock:
            # Check for serial disconnect (no state received)
            if self._last_state_time is not None:
                age = time.monotonic() - self._last_state_time
                if age > self._state_timeout:
                    self.get_logger().error(
                        'Serial timeout: no state received for %.1fs', age)
                    if not self._emergency_active:
                        self._trigger_emergency_stop_locked('Serial disconnect timeout')

        self._publish_diagnostics()

    # -------------------------------------------------------------------------
    # Emergency stop
    # -------------------------------------------------------------------------

    def _trigger_emergency_stop(self, reason: str) -> None:
        """Trigger emergency stop (call without lock held)."""
        with self._lock:
            self._trigger_emergency_stop_locked(reason)

    def _trigger_emergency_stop_locked(self, reason: str) -> None:
        """Trigger emergency stop (call with lock held)."""
        if not self._emergency_active:
            self.get_logger().error('EMERGENCY STOP: %s', reason)
            self._emergency_active = True

        # Always publish to ensure Roomba stops
        msg = Bool()
        msg.data = True
        self._pub_emergency_stop.publish(msg)

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    def _publish_diagnostics(self) -> None:
        """Publish diagnostics status."""
        now = self.get_clock().now()
        diag_array = DiagnosticArray()
        header = Header()
        header.stamp = now.to_msg()
        diag_array.header = header

        status = DiagnosticStatus()
        status.name = 'safety_monitor'
        status.hardware_id = 'roomba577_safety'

        with self._lock:
            emergency = self._emergency_active
            battery = self._battery_ratio
            wheel_drop = self._wheel_drop_left or self._wheel_drop_right
            covariance = self._amcl_covariance

        if emergency:
            status.level = DiagnosticStatus.ERROR
            status.message = 'EMERGENCY STOP ACTIVE'
        elif wheel_drop:
            status.level = DiagnosticStatus.ERROR
            status.message = 'Wheel drop detected'
        elif battery < BATTERY_LOW_THRESHOLD:
            status.level = DiagnosticStatus.WARN
            status.message = f'Battery low: {battery * 100:.0f}%'
        else:
            status.level = DiagnosticStatus.OK
            status.message = 'Safety monitor nominal'

        status.values = [
            KeyValue(key='emergency_stop', value=str(emergency)),
            KeyValue(key='battery_ratio', value=f'{battery:.3f}'),
            KeyValue(key='wheel_drop_left', value=str(self._wheel_drop_left)),
            KeyValue(key='wheel_drop_right', value=str(self._wheel_drop_right)),
            KeyValue(key='amcl_covariance', value=f'{covariance:.4f}'),
        ]

        diag_array.status = [status]
        self._pub_diagnostics.publish(diag_array)


def main(args=None) -> None:
    """Entry point for safety_monitor_node."""
    rclpy.init(args=args)
    node = SafetyMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
