"""Coverage planner lifecycle node for autonomous boustrophedon cleaning.

Integrates opennav_coverage for boustrophedon (zigzag) path planning,
provides /coverage_clean action server, tracks coverage grid,
and publishes diagnostics.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Optional

import numpy as np
import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn, State
from rclpy.qos import (
    QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
)

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import Pose, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import Header

from roomba_msgs.action import CoverageClean

from .nav2_interface import Nav2Interface

# Coverage constants
COVERAGE_GRID_RESOLUTION = 0.05  # 5cm grid cells
COVERAGE_CELL_RADIUS_M = 0.17    # Roomba577 radius ~17cm
COVERAGE_STRIP_WIDTH_M = 0.30    # Boustrophedon strip width (diameter)
FEEDBACK_RATE_HZ = 1.0           # Feedback publish rate


class CoveragePlannerNode(LifecycleNode):
    """Lifecycle node for boustrophedon coverage path planning.

    Provides:
    - /coverage_clean action server (roomba_msgs/CoverageClean)
    - Coverage grid tracking (cleaned area ratio)
    - Nav2 lifecycle management

    Action Server:
        /coverage_clean (roomba_msgs/CoverageClean)
            Goal: target_area (OccupancyGrid, empty = full map)
            Result: coverage_ratio, total_time_sec, total_distance_m, reason
            Feedback: current_coverage_ratio, current_pose, elapsed_time_sec

    Topics Subscribed:
        /map (nav_msgs/OccupancyGrid)
        /amcl_pose (geometry_msgs/PoseWithCovarianceStamped)

    Topics Published:
        /diagnostics (diagnostic_msgs/DiagnosticArray) @ 1Hz
    """

    def __init__(self) -> None:
        super().__init__('coverage_planner_node')
        self._lock = threading.Lock()

        # Nav2 interface
        self._nav2: Optional[Nav2Interface] = None

        # State
        self._map: Optional[OccupancyGrid] = None
        self._current_pose: Optional[Pose] = None
        self._coverage_grid: Optional[np.ndarray] = None
        self._total_coverage_cells = 0
        self._cleaned_cells = 0

        # Session tracking
        self._session_start: Optional[float] = None
        self._total_distance_m = 0.0
        self._prev_pose: Optional[Pose] = None

        # Action server
        self._action_server = None
        self._active_goal_handle = None

        # Publishers/subscribers
        self._pub_diagnostics = None
        self._sub_map = None
        self._sub_amcl = None

        # Timers
        self._timer_1hz = None
        self._callback_group = None

    # -------------------------------------------------------------------------
    # Lifecycle callbacks
    # -------------------------------------------------------------------------

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Configure action server, Nav2 interface, and subscriptions."""
        self.get_logger().info('Configuring coverage_planner_node')

        self.declare_parameter('strip_width_m', COVERAGE_STRIP_WIDTH_M)
        self.declare_parameter('coverage_grid_resolution', COVERAGE_GRID_RESOLUTION)

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
        qos_reliable_volatile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # Nav2 interface
        self._nav2 = Nav2Interface(self)

        # Publishers
        self._pub_diagnostics = self.create_publisher(
            DiagnosticArray, '/diagnostics', qos_reliable_volatile)

        # Subscribers
        self._sub_map = self.create_subscription(
            OccupancyGrid, '/map', self._map_callback, qos_reliable_transient)
        self._sub_amcl = self.create_subscription(
            PoseWithCovarianceStamped, '/amcl_pose',
            self._amcl_callback, qos_best_effort)

        # Action server (using ReentrantCallbackGroup for concurrent execution)
        self._callback_group = ReentrantCallbackGroup()
        self._action_server = ActionServer(
            self,
            CoverageClean,
            '/coverage_clean',
            execute_callback=self._execute_coverage_clean,
            goal_callback=self._goal_callback,
            cancel_callback=self._cancel_callback,
            callback_group=self._callback_group,
        )

        self.get_logger().info('coverage_planner_node configured')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Start timers."""
        self.get_logger().info('Activating coverage_planner_node')
        self._timer_1hz = self.create_timer(1.0, self._timer_1hz_callback)
        self.get_logger().info('coverage_planner_node activated')
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop active goal if running."""
        self.get_logger().info('Deactivating coverage_planner_node')
        self._cancel_active_goal('Node deactivated')
        if self._timer_1hz is not None:
            self._timer_1hz.cancel()
            self._timer_1hz = None
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """Cleanup."""
        self.get_logger().info('Cleaning up coverage_planner_node')
        self._cancel_active_goal('Node cleanup')
        if self._timer_1hz is not None:
            self._timer_1hz.cancel()
            self._timer_1hz = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """Shutdown."""
        self.get_logger().info('Shutting down coverage_planner_node')
        self._cancel_active_goal('Node shutdown')
        return TransitionCallbackReturn.SUCCESS

    # -------------------------------------------------------------------------
    # Action server callbacks
    # -------------------------------------------------------------------------

    def _goal_callback(self, goal_request) -> GoalResponse:
        """Accept or reject incoming coverage clean goal."""
        self.get_logger().info('Coverage clean goal received')
        with self._lock:
            if self._active_goal_handle is not None:
                self.get_logger().warning('Rejecting goal: already running')
                return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def _cancel_callback(self, goal_handle) -> CancelResponse:
        """Accept cancel requests."""
        self.get_logger().info('Coverage clean cancel requested')
        return CancelResponse.ACCEPT

    async def _execute_coverage_clean(self, goal_handle) -> CoverageClean.Result:
        """Execute coverage cleaning action.

        Implements boustrophedon path planning over the target area,
        tracking coverage progress and publishing feedback.

        Parameters
        ----------
        goal_handle : ServerGoalHandle
            The action goal handle.

        Returns
        -------
        CoverageClean.Result
            Final result with coverage ratio and statistics.
        """
        self.get_logger().info('Starting coverage clean execution')

        with self._lock:
            self._active_goal_handle = goal_handle

        start_time = time.monotonic()
        self._session_start = start_time
        self._total_distance_m = 0.0
        self._prev_pose = None

        # Initialize coverage grid
        with self._lock:
            current_map = self._map
        target_area = goal_handle.request.target_area

        self._initialize_coverage_grid(target_area if target_area.data else current_map)

        result = CoverageClean.Result()
        termination_reason = 'completed'

        # Generate boustrophedon waypoints
        waypoints = self._generate_boustrophedon_waypoints(
            target_area if target_area.data else current_map)

        if not waypoints:
            self.get_logger().warning('No waypoints generated — map not available yet')
            result.coverage_ratio = 0.0
            result.total_time_sec = 0.0
            result.total_distance_m = 0.0
            result.termination_reason = 'no_waypoints'
            goal_handle.succeed()
            with self._lock:
                self._active_goal_handle = None
            return result

        self.get_logger().info(
            'Executing boustrophedon path: %d waypoints', len(waypoints))

        # Main coverage loop
        for i, waypoint in enumerate(waypoints):
            # Check for cancellation
            if goal_handle.is_cancel_requested:
                self.get_logger().info('Coverage clean cancelled')
                goal_handle.canceled()
                result.termination_reason = 'cancelled'
                result.coverage_ratio = self._get_coverage_ratio()
                result.total_time_sec = time.monotonic() - start_time
                result.total_distance_m = self._total_distance_m
                with self._lock:
                    self._active_goal_handle = None
                return result

            # Navigate to waypoint via Nav2
            await self._navigate_to_pose(waypoint)

            # Update coverage grid with current position
            with self._lock:
                pose = self._current_pose
            if pose is not None:
                self._update_coverage_grid(pose)
                self._update_distance(pose)

            # Publish feedback
            feedback = CoverageClean.Feedback()
            feedback.current_coverage_ratio = self._get_coverage_ratio()
            feedback.elapsed_time_sec = time.monotonic() - start_time
            if pose is not None:
                feedback.current_pose = pose
            goal_handle.publish_feedback(feedback)

            self.get_logger().debug(
                'Waypoint %d/%d, coverage: %.1f%%',
                i + 1, len(waypoints),
                feedback.current_coverage_ratio * 100)

        # Cleaning complete
        result.coverage_ratio = self._get_coverage_ratio()
        result.total_time_sec = time.monotonic() - start_time
        result.total_distance_m = self._total_distance_m
        result.termination_reason = termination_reason

        self.get_logger().info(
            'Coverage clean complete: %.1f%% in %.1fs',
            result.coverage_ratio * 100, result.total_time_sec)

        goal_handle.succeed()

        with self._lock:
            self._active_goal_handle = None

        return result

    # -------------------------------------------------------------------------
    # Boustrophedon path planning
    # -------------------------------------------------------------------------

    def _generate_boustrophedon_waypoints(
        self,
        area: Optional[OccupancyGrid],
    ) -> list:
        """Generate boustrophedon (zigzag) waypoints over the area.

        Creates parallel sweep lines across the area with the strip width
        defined by the Roomba's cleaning width.

        Parameters
        ----------
        area : OccupancyGrid or None
            Target cleaning area. If None, uses full map.

        Returns
        -------
        list
            List of Pose waypoints for boustrophedon path.
        """
        if area is None or not area.data:
            return []

        resolution = area.info.resolution
        width = area.info.width
        height = area.info.height
        origin_x = area.info.origin.position.x
        origin_y = area.info.origin.position.y

        strip_width = self.get_parameter('strip_width_m').value
        strip_cells = max(1, int(strip_width / resolution))

        waypoints = []
        forward = True

        # Generate horizontal sweep lines (boustrophedon)
        row = strip_cells // 2
        while row < height:
            if forward:
                col_range = range(0, width, strip_cells)
            else:
                col_range = range(width - 1, -1, -strip_cells)

            for col in col_range:
                # Check if cell is free (value = 0 in occupancy grid)
                idx = row * width + col
                if idx < len(area.data) and area.data[idx] == 0:
                    pose = Pose()
                    pose.position.x = origin_x + col * resolution
                    pose.position.y = origin_y + row * resolution
                    pose.position.z = 0.0
                    # Orientation along sweep direction
                    yaw = 0.0 if forward else math.pi
                    pose.orientation.z = math.sin(yaw / 2)
                    pose.orientation.w = math.cos(yaw / 2)
                    waypoints.append(pose)

            forward = not forward
            row += strip_cells

        return waypoints

    # -------------------------------------------------------------------------
    # Coverage grid management
    # -------------------------------------------------------------------------

    def _initialize_coverage_grid(
        self, area: Optional[OccupancyGrid]
    ) -> None:
        """Initialize coverage grid matching the map dimensions."""
        if area is None or not area.data:
            return

        width = area.info.width
        height = area.info.height
        data = np.array(area.data).reshape(height, width)

        # Count free (value=0) cells as total coverage target.
        # Coverage progress intentionally resets for each new action goal
        # so each cleaning session is independently tracked.
        with self._lock:
            self._coverage_grid = np.zeros((height, width), dtype=np.int8)
            self._total_coverage_cells = int(np.sum(data == 0))
            self._cleaned_cells = 0

    def _update_coverage_grid(self, pose: Pose) -> None:
        """Mark cells near current position as cleaned."""
        with self._lock:
            if self._coverage_grid is None or self._map is None:
                return

            resolution = self._map.info.resolution
            origin_x = self._map.info.origin.position.x
            origin_y = self._map.info.origin.position.y

            # Convert pose to grid coordinates
            col = int((pose.position.x - origin_x) / resolution)
            row = int((pose.position.y - origin_y) / resolution)

            # Mark all cells within robot radius as cleaned
            radius_cells = int(COVERAGE_CELL_RADIUS_M / resolution)
            h, w = self._coverage_grid.shape

            for dr in range(-radius_cells, radius_cells + 1):
                for dc in range(-radius_cells, radius_cells + 1):
                    r = row + dr
                    c = col + dc
                    if (0 <= r < h and 0 <= c < w and
                            self._coverage_grid[r, c] == 0):
                        dist = math.sqrt(dr ** 2 + dc ** 2)
                        if dist <= radius_cells:
                            self._coverage_grid[r, c] = 1
                            self._cleaned_cells += 1

    def _update_distance(self, pose: Pose) -> None:
        """Update total distance traveled."""
        with self._lock:
            if self._prev_pose is not None:
                dx = pose.position.x - self._prev_pose.position.x
                dy = pose.position.y - self._prev_pose.position.y
                self._total_distance_m += math.sqrt(dx * dx + dy * dy)
            self._prev_pose = pose

    def _get_coverage_ratio(self) -> float:
        """Compute coverage ratio (cleaned / total free cells)."""
        with self._lock:
            if self._total_coverage_cells == 0:
                return 0.0
            return min(1.0, self._cleaned_cells / self._total_coverage_cells)

    # -------------------------------------------------------------------------
    # Nav2 navigation
    # -------------------------------------------------------------------------

    async def _navigate_to_pose(self, pose: Pose) -> None:
        """Navigate to a single waypoint using Nav2.

        Sends navigation goal to Nav2 NavigateToPose action server and
        awaits completion. Nav2 controller publishes to /cmd_vel_nav
        which mode_manager forwards to /cmd_vel when in AUTONOMOUS mode.

        Parameters
        ----------
        pose : Pose
            Target pose to navigate to.
        """
        try:
            from nav2_msgs.action import NavigateToPose  # type: ignore[import]
            from rclpy.action import ActionClient

            if not hasattr(self, '_nav_client'):
                self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

            if not self._nav_client.wait_for_server(timeout_sec=2.0):
                self.get_logger().warning('NavigateToPose action server not available')
                return

            from geometry_msgs.msg import PoseStamped
            goal = NavigateToPose.Goal()
            goal.pose = PoseStamped()
            goal.pose.header.frame_id = 'map'
            goal.pose.header.stamp = self.get_clock().now().to_msg()
            goal.pose.pose = pose

            send_goal_future = self._nav_client.send_goal_async(goal)
            await send_goal_future
            goal_handle = send_goal_future.result()

            if goal_handle is None or not goal_handle.accepted:
                self.get_logger().warning('Navigation goal rejected')
                return

            result_future = goal_handle.get_result_async()
            await result_future

        except ImportError:
            # nav2_msgs not available: fall back to direct logging
            self.get_logger().debug(
                'Navigating to (%.2f, %.2f) [nav2_msgs unavailable]',
                pose.position.x, pose.position.y)
        except Exception as exc:
            self.get_logger().warning('Navigation to waypoint failed: %s', exc)

    # -------------------------------------------------------------------------
    # Topic callbacks
    # -------------------------------------------------------------------------

    def _map_callback(self, msg: OccupancyGrid) -> None:
        """Cache received map."""
        with self._lock:
            self._map = msg
        self.get_logger().info(
            'Map received: %dx%d at %.2fm/cell',
            msg.info.width, msg.info.height, msg.info.resolution)

    def _amcl_callback(self, msg: PoseWithCovarianceStamped) -> None:
        """Update current pose from AMCL."""
        with self._lock:
            self._current_pose = msg.pose.pose

    # -------------------------------------------------------------------------
    # Timer callbacks
    # -------------------------------------------------------------------------

    def _timer_1hz_callback(self) -> None:
        """1Hz: publish diagnostics."""
        self._publish_diagnostics()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _cancel_active_goal(self, reason: str) -> None:
        """Cancel any active coverage action goal."""
        with self._lock:
            handle = self._active_goal_handle
        if handle is not None:
            self.get_logger().info('Cancelling active goal: %s', reason)
            try:
                handle.abort()
            except Exception:
                pass

    def _publish_diagnostics(self) -> None:
        """Publish diagnostics."""
        now = self.get_clock().now()
        diag_array = DiagnosticArray()
        header = Header()
        header.stamp = now.to_msg()
        diag_array.header = header

        status = DiagnosticStatus()
        status.name = 'coverage_planner'
        status.hardware_id = 'roomba577_navigation'

        with self._lock:
            has_map = self._map is not None
            coverage = self._get_coverage_ratio() if has_map else 0.0
            active = self._active_goal_handle is not None

        if not has_map:
            status.level = DiagnosticStatus.WARN
            status.message = 'Waiting for map'
        elif active:
            status.level = DiagnosticStatus.OK
            status.message = f'Coverage cleaning active: {coverage * 100:.1f}%'
        else:
            status.level = DiagnosticStatus.OK
            status.message = 'Coverage planner ready'

        status.values = [
            KeyValue(key='has_map', value=str(has_map)),
            KeyValue(key='coverage_ratio', value=f'{coverage:.3f}'),
            KeyValue(key='action_active', value=str(active)),
            KeyValue(key='total_distance_m', value=f'{self._total_distance_m:.2f}'),
        ]

        diag_array.status = [status]
        self._pub_diagnostics.publish(diag_array)


def main(args=None) -> None:
    """Entry point for coverage_planner_node."""
    rclpy.init(args=args)
    node = CoveragePlannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
