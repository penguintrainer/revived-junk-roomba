"""ROS2 session node for autonomous cleaning.

Gracefully degrades when rclpy is unavailable (test environment).
"""
from __future__ import annotations

import time
import uuid
from typing import Any, List, Optional

try:
    import rclpy  # type: ignore
    from rclpy.node import Node  # type: ignore
    from std_msgs.msg import String  # type: ignore
    from std_srvs.srv import Trigger  # type: ignore
    from geometry_msgs.msg import Twist  # type: ignore
    from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue  # type: ignore
    _HAS_ROS = True
except ImportError:
    _HAS_ROS = False
    Node = object  # type: ignore[assignment,misc]

from roomba_autonomous_cleaning.roomba_autonomous_cleaning.config import (
    BATTERY_LOW_THRESHOLD,
    BATTERY_START_THRESHOLD,
    CONTROL_LOOP_PERIOD_S,
    DIAGNOSTICS_MAX_PERIOD_S,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.models import (
    AutonomousCleaningSession,
    CoverageWorkUnit,
    DockAttemptState,
    EStopState,
    EndReason,
    InterruptionReason,
    LocalizationHealth,
    PerceptionFusionHealth,
    SessionState,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.session_state_machine import (
    mark_completed,
    mark_docking,
    mark_incomplete,
    request_estop,
    request_pause,
    request_resume,
    request_start,
    request_stop,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.estop_manager import EStopManager
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.interruption_policy import (
    apply_pause,
    apply_resume,
    apply_stop,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.localization_supervisor import (
    evaluate_localization,
    is_localization_ok,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.perception_fusion import (
    evaluate_perception_fusion,
    is_perception_ok,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.dock_adapter import DockAdapter
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.status_publisher import (
    StatusPublisher,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.result_builder import (
    build_action_result,
)
from roomba_cleaning_coverage.roomba_cleaning_coverage.coverage_tracker import (
    all_reachable_done,
    compute_snapshot,
    mark_unit_covered,
    mark_unit_failed,
    next_unvisited,
)
from roomba_cleaning_coverage.roomba_cleaning_coverage.completion_policy import (
    apply_terminal_state,
)
from roomba_autonomous_cleaning.roomba_autonomous_cleaning.nav2_adapter import (
    Nav2Adapter,
    nav_result_to_failure_reason,
)


class SessionNode(Node):  # type: ignore[misc]
    """ROS2 node orchestrating autonomous cleaning session."""

    def __init__(self) -> None:
        if _HAS_ROS:
            super().__init__("autonomous_cleaning_session_node")
            self._setup_ros()
        else:
            self._setup_headless()

    def _setup_ros(self) -> None:
        self._cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self._status_str_pub = self.create_publisher(
            String, "/autonomous_cleaning/status", 10
        )
        self._diag_pub = self.create_publisher(DiagnosticArray, "/diagnostics", 10)

        self.create_service(Trigger, "/autonomous_cleaning/start", self._cb_start)
        self.create_service(Trigger, "/autonomous_cleaning/pause", self._cb_pause)
        self.create_service(Trigger, "/autonomous_cleaning/resume", self._cb_resume)
        self.create_service(Trigger, "/autonomous_cleaning/stop", self._cb_stop)
        self.create_service(Trigger, "/autonomous_cleaning/estop", self._cb_estop)
        self.create_service(
            Trigger, "/autonomous_cleaning/clear_estop", self._cb_clear_estop
        )
        self.create_service(
            Trigger, "/autonomous_cleaning/get_status", self._cb_get_status
        )

        self._control_timer = self.create_timer(CONTROL_LOOP_PERIOD_S, self._control_loop)
        self._diag_timer = self.create_timer(DIAGNOSTICS_MAX_PERIOD_S, self._publish_diag)
        self._setup_state()

    def _setup_headless(self) -> None:
        self._setup_state()

    def _setup_state(self) -> None:
        self._session = AutonomousCleaningSession()
        self._estop_mgr = EStopManager()
        self._dock = DockAdapter()
        self._nav = Nav2Adapter()
        self._localization = LocalizationHealth()
        self._perception = PerceptionFusionHealth()
        self._publisher = StatusPublisher()
        self._work_units: List[CoverageWorkUnit] = []
        self._battery_percent: float = 100.0
        self._current_linear: float = 0.0
        self._current_angular: float = 0.0

    # ------------------------------------------------------------------
    # Service callbacks
    # ------------------------------------------------------------------

    def _cb_start(self, _req: Any, resp: Any) -> Any:
        ok, msg = request_start(
            self._session,
            battery_percent=self._battery_percent,
            localization_ok=is_localization_ok(self._localization),
            map_available=True,
        )
        resp.success = ok
        resp.message = msg
        return resp

    def _cb_pause(self, _req: Any, resp: Any) -> Any:
        ok, msg = apply_pause(self._session)
        if ok:
            self._send_zero_cmd_vel()
        resp.success = ok
        resp.message = msg
        return resp

    def _cb_resume(self, _req: Any, resp: Any) -> Any:
        ok, msg = apply_resume(self._session, self._estop_mgr.is_latched)
        resp.success = ok
        resp.message = msg
        return resp

    def _cb_stop(self, _req: Any, resp: Any) -> Any:
        ok, msg = apply_stop(self._session, InterruptionReason.OPERATOR_STOP)
        self._send_zero_cmd_vel()
        resp.success = ok
        resp.message = msg
        return resp

    def _cb_estop(self, _req: Any, resp: Any) -> Any:
        self._estop_mgr.latch()
        request_estop(self._session)
        self._send_zero_cmd_vel()
        resp.success = True
        resp.message = "estop_latched"
        return resp

    def _cb_clear_estop(self, _req: Any, resp: Any) -> Any:
        velocity_zero = (
            abs(self._current_linear) < 1e-6 and abs(self._current_angular) < 1e-6
        )
        no_active_fault = True
        perception_ok = is_perception_ok(self._perception)
        ok, msg = self._estop_mgr.clear(velocity_zero, no_active_fault, perception_ok)
        resp.success = ok
        resp.message = msg
        return resp

    def _cb_get_status(self, _req: Any, resp: Any) -> Any:
        snapshot = compute_snapshot(
            self._session.session_id, self._work_units
        )
        result = build_action_result(self._session, snapshot, self._dock.state)
        resp.success = True
        resp.message = str(result)
        return resp

    # ------------------------------------------------------------------
    # Control loop
    # ------------------------------------------------------------------

    def _control_loop(self) -> None:
        if self._estop_mgr.is_latched:
            self._send_zero_cmd_vel()
            return

        if self._session.state != SessionState.CLEANING:
            return

        # Low battery check
        if self._battery_percent < BATTERY_LOW_THRESHOLD * 100.0:
            mark_docking(self._session)
            self._dock.start_dock()
            self._send_zero_cmd_vel()
            return

        if all_reachable_done(self._work_units):
            apply_terminal_state(self._session, self._work_units)
            self._send_zero_cmd_vel()
            return

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
        snapshot = compute_snapshot(self._session.session_id, self._work_units)
        self._publisher.publish_diagnostics(
            self._session,
            self._localization,
            self._battery_percent / 100.0,
            self._dock.state,
            self._session.__class__.__dict__.get("estop", EStopState()),
            self._perception,
        )


def main() -> None:
    if not _HAS_ROS:
        print("rclpy not available; cannot start node")
        return
    rclpy.init()
    node = SessionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
