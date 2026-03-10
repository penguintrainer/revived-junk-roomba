"""Obstacle detector lifecycle node for Roomba577.

Instantiates LidarDetector and RgbdDetector, fuses detections,
publishes /obstacles (roomba_msgs/ObstacleArray) at 10Hz.
Excludes walls from obstacles, filters confidence < 0.3.
"""

from __future__ import annotations

import threading
import time
from typing import List, Optional

import rclpy
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn, State
from rclpy.qos import (
    QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
)

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from sensor_msgs.msg import LaserScan, Image, CameraInfo
from std_msgs.msg import Header

from roomba_msgs.msg import Obstacle, ObstacleArray

from .lidar_detector import LidarDetector
from .rgbd_detector import RgbdDetector

# Fusion parameters
LIDAR_WEIGHT = 0.6   # Weight for LiDAR detections in fusion
RGBD_WEIGHT = 0.4    # Weight for RGBD detections in fusion
MIN_CONFIDENCE = 0.3  # Filter threshold
FUSION_DISTANCE_THRESHOLD_M = 0.2  # Merge obstacles within 20cm


class ObstacleDetectorNode(LifecycleNode):
    """Lifecycle node for obstacle detection and fusion.

    Fuses LiDAR and RGBD detections, publishes obstacle array
    filtering out walls and low-confidence detections.

    Topics Subscribed:
        /scan (sensor_msgs/LaserScan)
        /camera/aligned_depth_to_color/image_raw (sensor_msgs/Image)
        /camera/color/image_raw (sensor_msgs/Image)
        /camera/aligned_depth_to_color/camera_info (sensor_msgs/CameraInfo)

    Topics Published:
        /obstacles (roomba_msgs/ObstacleArray) @ 10Hz
        /diagnostics (diagnostic_msgs/DiagnosticArray) @ 1Hz
    """

    def __init__(self) -> None:
        super().__init__('obstacle_detector_node')
        self._lock = threading.Lock()

        # Detectors
        self._lidar_detector: Optional[LidarDetector] = None
        self._rgbd_detector: Optional[RgbdDetector] = None

        # Latest sensor messages
        self._latest_scan: Optional[LaserScan] = None
        self._latest_depth: Optional[Image] = None
        self._latest_color: Optional[Image] = None
        self._scan_time: Optional[float] = None
        self._depth_time: Optional[float] = None

        # Publishers/subscribers
        self._pub_obstacles = None
        self._pub_diagnostics = None
        self._sub_scan = None
        self._sub_depth = None
        self._sub_color = None
        self._sub_camera_info = None

        # Timers
        self._timer_10hz = None
        self._timer_1hz = None

        # Stats
        self._total_lidar_detections = 0
        self._total_rgbd_detections = 0
        self._total_fused_detections = 0

    # -------------------------------------------------------------------------
    # Lifecycle callbacks
    # -------------------------------------------------------------------------

    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Create publishers, subscribers, and detector instances."""
        self.get_logger().info('Configuring obstacle_detector_node')

        self.declare_parameter('lidar_mount_tilt_deg', 15.0)
        self.declare_parameter('lidar_height_m', 0.10)
        self.declare_parameter('min_confidence', MIN_CONFIDENCE)

        tilt = self.get_parameter('lidar_mount_tilt_deg').value
        height = self.get_parameter('lidar_height_m').value
        self._min_confidence = self.get_parameter('min_confidence').value

        # Instantiate detectors
        self._lidar_detector = LidarDetector(
            mount_tilt_deg=tilt,
            mount_height_m=height,
        )
        self._rgbd_detector = RgbdDetector()

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
            depth=5,
        )

        # Publishers
        self._pub_obstacles = self.create_publisher(
            ObstacleArray, '/obstacles', qos_reliable_volatile)
        self._pub_diagnostics = self.create_publisher(
            DiagnosticArray, '/diagnostics', qos_reliable_volatile)

        # Subscribers
        self._sub_scan = self.create_subscription(
            LaserScan, '/scan', self._scan_callback, qos_best_effort)
        self._sub_depth = self.create_subscription(
            Image, '/camera/aligned_depth_to_color/image_raw',
            self._depth_callback, qos_best_effort)
        self._sub_color = self.create_subscription(
            Image, '/camera/color/image_raw',
            self._color_callback, qos_best_effort)
        self._sub_camera_info = self.create_subscription(
            CameraInfo, '/camera/aligned_depth_to_color/camera_info',
            self._camera_info_callback, qos_best_effort)

        self.get_logger().info('obstacle_detector_node configured')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Start detection timers."""
        self.get_logger().info('Activating obstacle_detector_node')
        self._timer_10hz = self.create_timer(0.1, self._timer_10hz_callback)
        self._timer_1hz = self.create_timer(1.0, self._timer_1hz_callback)
        self.get_logger().info('obstacle_detector_node activated')
        return TransitionCallbackReturn.SUCCESS

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop timers."""
        self.get_logger().info('Deactivating obstacle_detector_node')
        self._cancel_timers()
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """Cleanup."""
        self.get_logger().info('Cleaning up obstacle_detector_node')
        self._cancel_timers()
        self._lidar_detector = None
        self._rgbd_detector = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """Shutdown."""
        self.get_logger().info('Shutting down obstacle_detector_node')
        self._cancel_timers()
        return TransitionCallbackReturn.SUCCESS

    # -------------------------------------------------------------------------
    # Topic callbacks
    # -------------------------------------------------------------------------

    def _scan_callback(self, msg: LaserScan) -> None:
        """Cache latest LiDAR scan."""
        with self._lock:
            self._latest_scan = msg
            self._scan_time = time.monotonic()

    def _depth_callback(self, msg: Image) -> None:
        """Cache latest depth image."""
        with self._lock:
            self._latest_depth = msg
            self._depth_time = time.monotonic()

    def _color_callback(self, msg: Image) -> None:
        """Cache latest color image."""
        with self._lock:
            self._latest_color = msg

    def _camera_info_callback(self, msg: CameraInfo) -> None:
        """Update RGBD detector with camera intrinsics."""
        if self._rgbd_detector is not None:
            k = msg.k  # 3x3 intrinsic matrix (row-major)
            self._rgbd_detector.update_camera_info(
                fx=float(k[0]),
                fy=float(k[4]),
                cx=float(k[2]),
                cy=float(k[5]),
            )

    # -------------------------------------------------------------------------
    # Detection pipeline
    # -------------------------------------------------------------------------

    def _timer_10hz_callback(self) -> None:
        """10Hz: run detection pipeline and publish obstacles."""
        with self._lock:
            scan = self._latest_scan
            depth = self._latest_depth
            color = self._latest_color

        lidar_obs: List[Obstacle] = []
        rgbd_obs: List[Obstacle] = []

        # LiDAR detection
        if scan is not None and self._lidar_detector is not None:
            try:
                lidar_obs = self._lidar_detector.detect(scan)
                self._total_lidar_detections += len(lidar_obs)
            except Exception as exc:
                self.get_logger().warning('LiDAR detection error: %s', exc)

        # RGBD detection
        if depth is not None and self._rgbd_detector is not None:
            try:
                rgbd_obs = self._rgbd_detector.detect(depth, color)
                self._total_rgbd_detections += len(rgbd_obs)
            except Exception as exc:
                self.get_logger().warning('RGBD detection error: %s', exc)

        # Fuse detections
        fused = self._fuse_detections(lidar_obs, rgbd_obs)
        self._total_fused_detections += len(fused)

        # Publish
        now = self.get_clock().now()
        msg = ObstacleArray()
        header = Header()
        header.stamp = now.to_msg()
        header.frame_id = 'base_link'
        msg.header = header
        msg.obstacles = fused
        self._pub_obstacles.publish(msg)

    def _timer_1hz_callback(self) -> None:
        """1Hz: publish diagnostics."""
        self._publish_diagnostics()

    # -------------------------------------------------------------------------
    # Fusion
    # -------------------------------------------------------------------------

    def _fuse_detections(
        self,
        lidar_obs: List[Obstacle],
        rgbd_obs: List[Obstacle],
    ) -> List[Obstacle]:
        """Fuse LiDAR and RGBD detections.

        Merges overlapping detections (within 20cm) and boosts confidence
        when both sensors agree. Filters confidence < 0.3.
        Excludes walls from output.

        Parameters
        ----------
        lidar_obs : List[Obstacle]
            Obstacles from LiDAR detector.
        rgbd_obs : List[Obstacle]
            Obstacles from RGBD detector.

        Returns
        -------
        List[Obstacle]
            Fused and filtered obstacle list.
        """
        all_obs = list(lidar_obs) + list(rgbd_obs)

        if not all_obs:
            return []

        # Filter by confidence
        all_obs = [o for o in all_obs if o.confidence >= self._min_confidence]

        # Merge nearby detections
        merged = self._merge_nearby_obstacles(all_obs)

        return merged

    def _merge_nearby_obstacles(
        self,
        obstacles: List[Obstacle],
    ) -> List[Obstacle]:
        """Merge obstacle detections that are within fusion threshold.

        Parameters
        ----------
        obstacles : List[Obstacle]
            Input obstacle list.

        Returns
        -------
        List[Obstacle]
            Merged obstacle list with boosted confidence for fused detections.
        """
        if not obstacles:
            return []

        merged = []
        used = [False] * len(obstacles)

        for i, obs_i in enumerate(obstacles):
            if used[i]:
                continue

            group = [obs_i]
            used[i] = True

            for j, obs_j in enumerate(obstacles[i + 1:], start=i + 1):
                if used[j]:
                    continue

                dist = self._obstacle_distance(obs_i, obs_j)
                if dist < FUSION_DISTANCE_THRESHOLD_M:
                    group.append(obs_j)
                    used[j] = True

            # Merge group into single obstacle
            merged_obs = self._merge_group(group)
            merged.append(merged_obs)

        return merged

    @staticmethod
    def _obstacle_distance(a: Obstacle, b: Obstacle) -> float:
        """Compute Euclidean distance between two obstacle positions."""
        dx = a.position.x - b.position.x
        dy = a.position.y - b.position.y
        return (dx ** 2 + dy ** 2) ** 0.5

    @staticmethod
    def _merge_group(group: List[Obstacle]) -> Obstacle:
        """Merge a group of nearby obstacles into one.

        Uses weighted average of positions. Confidence is boosted
        when multiple sources agree (FUSED detection).
        """
        if len(group) == 1:
            return group[0]

        # Weighted position average
        total_conf = sum(o.confidence for o in group)
        avg_x = sum(o.position.x * o.confidence for o in group) / total_conf
        avg_y = sum(o.position.y * o.confidence for o in group) / total_conf

        # Check if both LiDAR and RGBD detected it
        sources = {o.detection_source for o in group}
        has_lidar = Obstacle.SOURCE_LIDAR in sources
        has_rgbd = Obstacle.SOURCE_RGBD in sources

        # Boost confidence for multi-sensor agreement
        max_conf = max(o.confidence for o in group)
        if has_lidar and has_rgbd:
            fused_confidence = min(0.98, max_conf * 1.3)
            source = Obstacle.SOURCE_FUSED
        else:
            fused_confidence = max_conf
            source = group[0].detection_source

        # Use most common obstacle type
        types = [o.obstacle_type for o in group]
        obs_type = max(set(types), key=types.count)

        result = Obstacle()
        result.position.x = avg_x
        result.position.y = avg_y
        result.position.z = 0.0
        result.obstacle_type = obs_type
        result.detection_source = source
        result.confidence = fused_confidence

        # Average bounding size
        result.bounding_size.x = sum(o.bounding_size.x for o in group) / len(group)
        result.bounding_size.y = sum(o.bounding_size.y for o in group) / len(group)
        result.bounding_size.z = sum(o.bounding_size.z for o in group) / len(group)

        return result

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    def _publish_diagnostics(self) -> None:
        """Publish diagnostics."""
        now = self.get_clock().now()
        diag_array = DiagnosticArray()
        header = Header()
        header.stamp = now.to_msg()
        diag_array.header = header

        status = DiagnosticStatus()
        status.name = 'obstacle_detector'
        status.hardware_id = 'ydlidar_realsense_d435i'

        with self._lock:
            scan_time = self._scan_time
            depth_time = self._depth_time

        now_mono = time.monotonic()
        scan_age = (now_mono - scan_time) if scan_time else float('inf')
        depth_age = (now_mono - depth_time) if depth_time else float('inf')

        if scan_age > 5.0 and depth_age > 5.0:
            status.level = DiagnosticStatus.ERROR
            status.message = 'No sensor data received'
        elif scan_age > 5.0:
            status.level = DiagnosticStatus.WARN
            status.message = 'LiDAR data stale or missing'
        elif depth_age > 5.0:
            status.level = DiagnosticStatus.WARN
            status.message = 'RGBD data stale or missing'
        else:
            status.level = DiagnosticStatus.OK
            status.message = 'Obstacle detector operational'

        status.values = [
            KeyValue(key='scan_age_sec', value=f'{scan_age:.1f}'),
            KeyValue(key='depth_age_sec', value=f'{depth_age:.1f}'),
            KeyValue(key='total_lidar_detections', value=str(self._total_lidar_detections)),
            KeyValue(key='total_rgbd_detections', value=str(self._total_rgbd_detections)),
            KeyValue(key='total_fused_detections', value=str(self._total_fused_detections)),
        ]

        diag_array.status = [status]
        self._pub_diagnostics.publish(diag_array)

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _cancel_timers(self) -> None:
        """Cancel all active timers."""
        for attr in ('_timer_10hz', '_timer_1hz'):
            timer = getattr(self, attr, None)
            if timer is not None:
                timer.cancel()
                setattr(self, attr, None)


def main(args=None) -> None:
    """Entry point for obstacle_detector_node."""
    rclpy.init(args=args)
    node = ObstacleDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
