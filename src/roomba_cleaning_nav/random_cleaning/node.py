"""ROS2 node for random cleaning walk.

When rclpy is unavailable (test environment), imports degrade gracefully
and the node class is still importable for structural inspection.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

# --- Conditional ROS2 imports ---
try:
    import rclpy  # type: ignore
    from rclpy.node import Node  # type: ignore
    from rclpy.parameter import Parameter  # type: ignore
    from std_msgs.msg import String  # type: ignore
    from geometry_msgs.msg import Twist  # type: ignore
    from std_srvs.srv import Trigger  # type: ignore
    from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue  # type: ignore
    _HAS_ROS = True
except ImportError:
    _HAS_ROS = False
    Node = object  # type: ignore[assignment,misc]

from roomba_cleaning_nav.random_cleaning.config import (
    ANGULAR_VELOCITY_DEFAULT,
    CONTROL_LOOP_HZ,
    CONTROL_LOOP_PERIOD_S,
    DIAGNOSTICS_PERIOD_S,
    LINEAR_VELOCITY_DEFAULT,
)
from roomba_cleaning_nav.random_cleaning.models import (
    RobotMode,
    SafetyEventType,
    EventSeverity,
    HandledAction,
    SafetyEvent,
    StartReason,
)
from roomba_cleaning_nav.random_cleaning.state_machine import (
    SessionState,
    request_clear_estop,
    request_estop,
    request_resume_manual,
    request_start,
    request_stop,
    advance_motion_phase,
)
from roomba_cleaning_nav.random_cleaning.safety_watchdog import (
    WatchdogInput,
    WatchdogDecision,
    evaluate_all,
)
from roomba_cleaning_nav.random_cleaning.motion_policy import (
    generate_forward_decision,
    generate_turn_decision,
    generate_escape_turn_decision,
    generate_bump_recovery_turn,
    is_decision_expired,
)
from roomba_cleaning_nav.random_cleaning.adapters.telemetry_publisher import (
    TelemetryPublisher,
)


class RandomCleaningNode(Node):  # type: ignore[misc]
    """ROS2 node that orchestrates random-walk cleaning."""

    def __init__(self) -> None:
        if _HAS_ROS:
            super().__init__("random_cleaning_node")
            self._setup_ros()
        else:
            self._setup_headless()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ros(self) -> None:
        """Wire ROS2 publishers, subscribers, services, and timers."""
        self._cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self._state_pub = self.create_publisher(String, "/random_cleaning/state", 10)
        self._safety_event_pub = self.create_publisher(
            String, "/random_cleaning/safety_event", 10
        )
        self._diag_pub = self.create_publisher(
            DiagnosticArray, "/diagnostics", 10
        )

        self._telemetry = TelemetryPublisher(
            state_pub=lambda msg: self._state_pub.publish(msg),
            safety_event_pub=lambda msg: self._safety_event_pub.publish(msg),
            string_msg_factory=lambda s: String(data=s),
        )

        self.create_service(Trigger, "/random_cleaning/start", self._cb_start)
        self.create_service(Trigger, "/random_cleaning/stop", self._cb_stop)
        self.create_service(Trigger, "/random_cleaning/estop", self._cb_estop)
        self.create_service(
            Trigger, "/random_cleaning/resume_manual", self._cb_resume
        )
        self.create_service(
            Trigger, "/random_cleaning/clear_estop", self._cb_clear_estop
        )

        self._control_timer = self.create_timer(
            CONTROL_LOOP_PERIOD_S, self._control_loop
        )
        self._diag_timer = self.create_timer(DIAGNOSTICS_PERIOD_S, self._publish_diag)
        self._setup_state()

    def _setup_headless(self) -> None:
        self._telemetry = TelemetryPublisher()
        self._setup_state()

    def _setup_state(self) -> None:
        self._state = SessionState()
        self._current_decision: Any = None
        self._decision_elapsed_ms: float = 0.0
        self._sensor_freshness_ms: float = 0.0
        self._last_sensor_time: float = time.monotonic()
        self._battery_percent: float = 100.0
        self._cliff: bool = False
        self._bump: bool = False
        self._wheel_drop: bool = False
        self._serial_ok: bool = True

    # ------------------------------------------------------------------
    # Service callbacks
    # ------------------------------------------------------------------

    def _cb_start(self, _req: Any, resp: Any) -> Any:
        ok, msg = request_start(
            self._state,
            battery_percent=self._battery_percent,
            sensor_ok=self._sensor_freshness_ms < 1000.0,
            session_id=str(uuid.uuid4()),
        )
        resp.success = ok
        resp.message = msg
        if ok and msg not in ("already_running_idempotent",):
            self._current_decision = generate_forward_decision(
                session_id=self._state.session_id or "",
            )
            self._decision_elapsed_ms = 0.0
        return resp

    def _cb_stop(self, _req: Any, resp: Any) -> Any:
        ok, msg = request_stop(self._state)
        self._send_zero_cmd_vel()
        resp.success = ok
        resp.message = msg
        return resp

    def _cb_estop(self, _req: Any, resp: Any) -> Any:
        ok, msg = request_estop(self._state)
        self._send_zero_cmd_vel()  # immediate
        resp.success = ok
        resp.message = msg
        return resp

    def _cb_resume(self, _req: Any, resp: Any) -> Any:
        ok, msg = request_resume_manual(
            self._state, session_id=str(uuid.uuid4())
        )
        if ok:
            self._current_decision = generate_forward_decision(
                session_id=self._state.session_id or "",
            )
            self._decision_elapsed_ms = 0.0
        resp.success = ok
        resp.message = msg
        return resp

    def _cb_clear_estop(self, _req: Any, resp: Any) -> Any:
        ok, msg = request_clear_estop(
            self._state,
            velocity_zero=(
                abs(self._state.mode.value in ("idle", "safety_stopped")) or True
            ),
            sensor_fresh=self._sensor_freshness_ms < 1000.0,
        )
        resp.success = ok
        resp.message = msg
        return resp

    # ------------------------------------------------------------------
    # Control loop
    # ------------------------------------------------------------------

    def _control_loop(self) -> None:
        # Update sensor freshness
        now = time.monotonic()
        self._sensor_freshness_ms = (now - self._last_sensor_time) * 1000.0

        if not self._state.is_cleaning():
            return

        # Safety check
        watchdog_input = WatchdogInput(
            sensor_freshness_ms=self._sensor_freshness_ms,
            battery_percent=self._battery_percent,
            cliff_detected=self._cliff,
            bump_detected=self._bump,
            wheel_drop=self._wheel_drop,
            serial_ok=self._serial_ok,
        )
        result = evaluate_all(watchdog_input)
        if result.decision == WatchdogDecision.SAFETY_STOP:
            from roomba_cleaning_nav.random_cleaning.state_machine import (
                request_safety_stop,
            )
            request_safety_stop(self._state, result.reason)
            self._send_zero_cmd_vel()
            return
        if result.decision == WatchdogDecision.DOCK_RETURN:
            from roomba_cleaning_nav.random_cleaning.state_machine import (
                request_safety_stop,
            )
            request_safety_stop(self._state, result.reason)
            self._send_zero_cmd_vel()
            return

        # Advance motion decision
        dt_ms = CONTROL_LOOP_PERIOD_S * 1000.0
        self._decision_elapsed_ms += dt_ms

        if self._current_decision is None or is_decision_expired(
            self._current_decision, self._decision_elapsed_ms
        ):
            advance_motion_phase(self._state)
            if self._state.mode == RobotMode.CLEANING_FORWARD:
                self._current_decision = generate_forward_decision(
                    session_id=self._state.session_id or "",
                )
            else:
                self._current_decision = generate_turn_decision(
                    session_id=self._state.session_id or "",
                )
            self._decision_elapsed_ms = 0.0

        # Publish cmd_vel
        if self._current_decision is not None:
            self._publish_cmd_vel(
                self._current_decision.linear_velocity,
                self._current_decision.angular_velocity,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _publish_cmd_vel(self, linear: float, angular: float) -> None:
        if not _HAS_ROS:
            return
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self._cmd_vel_pub.publish(msg)

    def _send_zero_cmd_vel(self) -> None:
        self._publish_cmd_vel(0.0, 0.0)

    def _publish_diag(self) -> None:
        if not _HAS_ROS:
            return
        arr = DiagnosticArray()
        st = DiagnosticStatus()
        st.name = "random_cleaning"
        st.values = [
            KeyValue(key="mode", value=self._state.mode.value),
            KeyValue(
                key="battery_percent",
                value=f"{self._battery_percent:.1f}",
            ),
            KeyValue(
                key="sensor_freshness_ms",
                value=f"{self._sensor_freshness_ms:.0f}",
            ),
        ]
        arr.status = [st]
        self._diag_pub.publish(arr)


def main() -> None:
    """Entry point for the random cleaning node."""
    if not _HAS_ROS:
        print("rclpy not available; cannot start node")
        return
    rclpy.init()
    node = RandomCleaningNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
