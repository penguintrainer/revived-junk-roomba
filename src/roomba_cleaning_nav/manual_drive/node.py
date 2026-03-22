"""ROS2 node for Joy-Con manual drive cleaning.

Gracefully degrades when rclpy is unavailable (test environment).
"""
from __future__ import annotations

import time
from typing import Any, Optional

try:
    import rclpy  # type: ignore
    from rclpy.node import Node  # type: ignore
    from geometry_msgs.msg import Twist  # type: ignore
    from std_msgs.msg import String, Bool  # type: ignore
    from std_srvs.srv import Trigger  # type: ignore
    from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue  # type: ignore
    _HAS_ROS = True
except ImportError:
    _HAS_ROS = False
    Node = object  # type: ignore[assignment,misc]

from roomba_cleaning_nav.manual_drive.config import (
    CONTROL_LOOP_PERIOD_S,
    DIAGNOSTICS_PERIOD_S,
    LINK_LOSS_TIMEOUT_S,
    STOP_ON_RELEASE_TIMEOUT_S,
)
from roomba_cleaning_nav.manual_drive.models import (
    CleaningState,
    DirectionInput,
    ManualDriveMode,
    ManualDriveState,
    SafetyFault,
)
from roomba_cleaning_nav.manual_drive.command_mapper import (
    clamp_velocity,
    direction_to_velocity,
    resolve_direction,
)
from roomba_cleaning_nav.manual_drive.long_press_tracker import (
    LongPressState,
    check_long_press,
    release_press,
    start_press,
)
from roomba_cleaning_nav.manual_drive.safety_watchdog import (
    SafetyLatch,
    WatchdogDecision,
    check_clear_estop_preconditions,
    evaluate_cliff,
    evaluate_link_health,
)
from roomba_cleaning_nav.manual_drive.adapters.feedback_adapter import FeedbackAdapter


class ManualDriveNode(Node):  # type: ignore[misc]
    """ROS2 node orchestrating Joy-Con manual drive."""

    def __init__(self) -> None:
        if _HAS_ROS:
            super().__init__("manual_drive_node")
            self._setup_ros()
        else:
            self._setup_headless()

    def _setup_ros(self) -> None:
        self._cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self._status_pub = self.create_publisher(String, "/manual_drive/status", 10)
        self._diag_pub = self.create_publisher(DiagnosticArray, "/diagnostics", 10)

        self._feedback = FeedbackAdapter(
            status_pub=lambda msg: self._status_pub.publish(msg),
            string_msg_factory=lambda s: String(data=s),
        )

        self.create_service(Trigger, "/manual_drive/estop", self._cb_estop)
        self.create_service(Trigger, "/manual_drive/clear_estop", self._cb_clear_estop)
        self.create_subscription(Bool, "/cliff", self._cb_cliff, 10)

        self._control_timer = self.create_timer(CONTROL_LOOP_PERIOD_S, self._control_loop)
        self._diag_timer = self.create_timer(DIAGNOSTICS_PERIOD_S, self._publish_diag)
        self._setup_state()

    def _setup_headless(self) -> None:
        self._feedback = FeedbackAdapter()
        self._setup_state()

    def _setup_state(self) -> None:
        self._state = ManualDriveState()
        self._latch = SafetyLatch()
        self._mode_press = LongPressState()
        self._last_input_time: float = time.monotonic()
        self._last_direction = DirectionInput.NONE
        self._no_input_since: float = time.monotonic()
        self._cliff_active: bool = False
        self._serial_ok: bool = True
        self._link_age_ms: float = 0.0
        self._current_linear: float = 0.0
        self._current_angular: float = 0.0

    # ------------------------------------------------------------------
    # Service callbacks
    # ------------------------------------------------------------------

    def _cb_estop(self, _req: Any, resp: Any) -> Any:
        self._latch.latch(SafetyFault.E_STOP)
        self._state.apply_safety_stop(SafetyFault.E_STOP)
        self._state.estop_latched = True
        self._send_zero_cmd_vel()
        resp.success = True
        resp.message = "estop_latched"
        return resp

    def _cb_clear_estop(self, _req: Any, resp: Any) -> Any:
        velocity_zero = (
            abs(self._current_linear) < 1e-6 and abs(self._current_angular) < 1e-6
        )
        no_active_fault = self._state.fault == SafetyFault.E_STOP  # only e-stop latched
        ok, reason = check_clear_estop_preconditions(velocity_zero, no_active_fault)
        if ok:
            self._latch.clear()
            self._state.estop_latched = False
            self._state.safety_latched = False
            self._state.fault = SafetyFault.NONE
            self._state.mode = ManualDriveMode.IDLE
            resp.success = True
            resp.message = "estop_cleared"
        else:
            resp.success = False
            resp.message = f"rejected_{reason}"
        return resp

    def _cb_cliff(self, msg: Any) -> None:
        if _HAS_ROS:
            self._cliff_active = msg.data
        if self._cliff_active and self._state.is_active():
            self._send_zero_cmd_vel()

    # ------------------------------------------------------------------
    # Control loop
    # ------------------------------------------------------------------

    def _control_loop(self) -> None:
        if self._latch.latched:
            self._send_zero_cmd_vel()
            return

        # Link-loss check
        link_decision = evaluate_link_health(self._link_age_ms)
        if link_decision == WatchdogDecision.LINK_LOSS_STOP and self._state.is_active():
            self._state.apply_safety_stop(SafetyFault.LINK_LOSS)
            self._latch.latch(SafetyFault.LINK_LOSS)
            self._send_zero_cmd_vel()
            return

        # Cliff check
        cliff_decision = evaluate_cliff(self._cliff_active)
        if cliff_decision == WatchdogDecision.CLIFF_STOP and self._state.is_active():
            self._send_zero_cmd_vel()
            return

        if not self._state.is_active():
            return

        # Stop-on-release logic
        now = time.monotonic()
        if self._last_direction == DirectionInput.NONE:
            if (now - self._no_input_since) >= STOP_ON_RELEASE_TIMEOUT_S:
                self._publish_cmd_vel(0.0, 0.0)
            return

        linear, angular = direction_to_velocity(self._last_direction)
        linear, angular = clamp_velocity(linear, angular)
        self._current_linear = linear
        self._current_angular = angular
        self._publish_cmd_vel(linear, angular)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def update_direction(self, direction: DirectionInput) -> None:
        """Called when Joy-Con direction changes."""
        if direction == DirectionInput.NONE and self._last_direction != DirectionInput.NONE:
            self._no_input_since = time.monotonic()
        self._last_direction = direction

    def toggle_cleaning(self) -> None:
        """Toggle cleaning state."""
        if not self._state.is_active():
            return
        if self._state.cleaning == CleaningState.OFF:
            self._state.cleaning = CleaningState.ON
        else:
            self._state.cleaning = CleaningState.OFF
        self._feedback.on_cleaning_toggle(self._state)

    def toggle_manual_mode(self) -> None:
        """Enter or exit manual mode."""
        if self._state.is_active():
            self._state.exit_manual_mode()
            self._send_zero_cmd_vel()
        else:
            if self._latch.latched:
                return
            self._state.enter_manual_mode()
        self._feedback.on_mode_change(self._state)

    def _publish_cmd_vel(self, linear: float, angular: float) -> None:
        if not _HAS_ROS:
            self._current_linear = linear
            self._current_angular = angular
            return
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self._cmd_vel_pub.publish(msg)
        self._current_linear = linear
        self._current_angular = angular

    def _send_zero_cmd_vel(self) -> None:
        self._publish_cmd_vel(0.0, 0.0)

    def _publish_diag(self) -> None:
        if not _HAS_ROS:
            return
        self._feedback.publish_diagnostics(self._state, self._link_age_ms)


def main() -> None:
    if not _HAS_ROS:
        print("rclpy not available; cannot start node")
        return
    rclpy.init()
    node = ManualDriveNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
