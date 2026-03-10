"""LiDAR-based obstacle detector for Roomba577.

Subscribes to /scan (sensor_msgs/LaserScan), detects floor obstacles
(step edges, cables) while compensating for ~15° downward YDLIDAR mount angle.
Returns typed obstacle list with confidence scores.
"""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from geometry_msgs.msg import Point, Vector3
from sensor_msgs.msg import LaserScan

from roomba_msgs.msg import Obstacle

# YDLIDAR T-mini Plus mount angle (degrees, downward tilt)
LIDAR_MOUNT_TILT_DEG = 15.0
LIDAR_MOUNT_TILT_RAD = math.radians(LIDAR_MOUNT_TILT_DEG)

# Lidar mounting height above floor (meters)
LIDAR_HEIGHT_M = 0.10

# Detection thresholds
STEP_EDGE_DEPTH_THRESHOLD_M = 0.05    # 5cm depth jump → step edge
CABLE_CLUSTER_MAX_SIZE_M = 0.05       # clusters ≤5cm → cable/small object
WALL_DISTANCE_MIN_M = 0.15            # distances > this are not floor obstacles
WALL_DETECTION_RANGE_M = 2.0          # max range for obstacle detection
MIN_CONFIDENCE = 0.3                   # minimum confidence to include
CONSECUTIVE_READINGS_FOR_DETECTION = 3  # consecutive readings needed


class LidarDetector:
    """Detects floor obstacles from LaserScan data.

    Compensates for ~15° downward YDLIDAR T-mini Plus mount angle.
    Identifies step edges and floor-level cables/objects.

    Parameters
    ----------
    mount_tilt_deg : float
        LiDAR downward tilt angle in degrees. Default: 15.0.
    mount_height_m : float
        LiDAR mounting height above floor in meters. Default: 0.10.
    """

    def __init__(
        self,
        mount_tilt_deg: float = LIDAR_MOUNT_TILT_DEG,
        mount_height_m: float = LIDAR_HEIGHT_M,
    ) -> None:
        self._tilt_rad = math.radians(mount_tilt_deg)
        self._height_m = mount_height_m
        self._prev_scan: Optional[LaserScan] = None

    def detect(self, scan: LaserScan) -> List[Obstacle]:
        """Process LaserScan and return list of detected obstacles.

        Parameters
        ----------
        scan : LaserScan
            Input scan from YDLIDAR T-mini Plus.

        Returns
        -------
        List[Obstacle]
            Detected obstacles with type, position, and confidence.
        """
        obstacles: List[Obstacle] = []

        ranges = np.array(scan.ranges, dtype=np.float32)
        angles = np.arange(len(ranges)) * scan.angle_increment + scan.angle_min

        # Filter invalid readings
        valid_mask = np.isfinite(ranges) & (ranges > scan.range_min) & \
                     (ranges < scan.range_max)

        # Project each ray to floor plane, compensating for tilt
        floor_distances = self._project_to_floor(ranges, angles, valid_mask)

        # Detect step edges (sudden depth changes)
        step_obstacles = self._detect_step_edges(
            ranges, angles, floor_distances, valid_mask, scan)
        obstacles.extend(step_obstacles)

        # Detect clusters (cables, small objects on floor)
        cluster_obstacles = self._detect_floor_clusters(
            ranges, angles, floor_distances, valid_mask, scan)
        obstacles.extend(cluster_obstacles)

        # Filter out walls and low-confidence detections
        filtered = [
            obs for obs in obstacles
            if obs.confidence >= MIN_CONFIDENCE
        ]

        self._prev_scan = scan
        return filtered

    def _project_to_floor(
        self,
        ranges: np.ndarray,
        angles: np.ndarray,
        valid_mask: np.ndarray,
    ) -> np.ndarray:
        """Project scan ranges to floor-plane distances, correcting for tilt.

        The YDLIDAR is tilted ~15° downward, so horizontal ranges need
        geometric correction to get true floor distance.

        Parameters
        ----------
        ranges : np.ndarray
            Raw range values from scan.
        angles : np.ndarray
            Angle for each ray (radians).
        valid_mask : np.ndarray
            Boolean mask of valid readings.

        Returns
        -------
        np.ndarray
            Floor-projected distances (NaN for invalid).
        """
        floor_distances = np.full_like(ranges, np.nan)

        # For a tilted LiDAR: the actual floor hit distance differs
        # Horizontal component: r * cos(tilt)
        # Vertical component: h - r * sin(tilt)  (where h is mount height)
        cos_tilt = math.cos(self._tilt_rad)

        # True horizontal distance to where beam hits floor
        floor_distances[valid_mask] = ranges[valid_mask] * cos_tilt

        return floor_distances

    def _detect_step_edges(
        self,
        ranges: np.ndarray,
        angles: np.ndarray,
        floor_distances: np.ndarray,
        valid_mask: np.ndarray,
        scan: LaserScan,
    ) -> List[Obstacle]:
        """Detect step edges (sudden depth discontinuities)."""
        obstacles = []

        valid_ranges = np.where(valid_mask, ranges, np.nan)

        # Compute range differences between consecutive rays
        diffs = np.abs(np.diff(valid_ranges))

        # Find indices where depth jumps significantly
        step_indices = np.where(diffs > STEP_EDGE_DEPTH_THRESHOLD_M)[0]

        # Group nearby indices into single detections
        groups = self._group_indices(step_indices, gap=3)

        for group in groups:
            if not group:
                continue
            center_idx = group[len(group) // 2]
            if not valid_mask[center_idx]:
                continue

            r = ranges[center_idx]
            if r > WALL_DETECTION_RANGE_M:
                continue

            a = angles[center_idx]

            # Check if this is a floor-level obstacle (not a wall)
            hit_height = self._height_m - r * math.sin(self._tilt_rad)
            if hit_height > 0.3:  # Hitting something >30cm above floor → wall
                continue

            # Compute obstacle position in robot frame
            x = r * math.cos(a) * math.cos(self._tilt_rad)
            y = r * math.sin(a) * math.cos(self._tilt_rad)

            obs = Obstacle()
            obs.position = Point(x=float(x), y=float(y), z=0.0)
            obs.obstacle_type = Obstacle.STEP_EDGE
            obs.detection_source = Obstacle.SOURCE_LIDAR

            # Confidence based on depth jump magnitude
            jump_magnitude = diffs[center_idx] if center_idx < len(diffs) else 0.0
            obs.confidence = min(1.0, float(jump_magnitude) / 0.3)

            obs.bounding_size = Vector3(x=0.05, y=0.05, z=0.05)

            obstacles.append(obs)

        return obstacles

    def _detect_floor_clusters(
        self,
        ranges: np.ndarray,
        angles: np.ndarray,
        floor_distances: np.ndarray,
        valid_mask: np.ndarray,
        scan: LaserScan,
    ) -> List[Obstacle]:
        """Detect small floor objects (cables, low obstacles)."""
        obstacles = []

        # Find short-range readings that are significantly closer than neighbors
        valid_ranges = np.where(valid_mask, ranges, np.nan)

        # Local minimum detection: points much closer than surroundings
        window = 5
        for i in range(window, len(ranges) - window):
            if not valid_mask[i]:
                continue

            r = ranges[i]
            if r > WALL_DETECTION_RANGE_M or r < 0.05:
                continue

            # Check if this point is a local minimum (obstacle stands out)
            neighborhood = valid_ranges[i - window:i + window + 1]
            valid_neighbors = neighborhood[~np.isnan(neighborhood)]
            if len(valid_neighbors) < 3:
                continue

            local_mean = float(np.nanmean(neighborhood))
            if local_mean - r < 0.05:  # Not a significant protrusion
                continue

            a = angles[i]
            x = r * math.cos(a) * math.cos(self._tilt_rad)
            y = r * math.sin(a) * math.cos(self._tilt_rad)

            # Estimate size
            angular_span = scan.angle_increment * window * 2
            size = r * math.sin(angular_span)

            obs = Obstacle()
            obs.position = Point(x=float(x), y=float(y), z=0.0)

            if size <= CABLE_CLUSTER_MAX_SIZE_M:
                obs.obstacle_type = Obstacle.CABLE
            else:
                obs.obstacle_type = Obstacle.FLOOR_OBJECT

            obs.detection_source = Obstacle.SOURCE_LIDAR
            obs.confidence = min(0.8, float(local_mean - r) / 0.5)
            obs.bounding_size = Vector3(x=float(size), y=float(size), z=0.05)

            obstacles.append(obs)

        return obstacles

    @staticmethod
    def _group_indices(indices: np.ndarray, gap: int = 3) -> List[List[int]]:
        """Group nearby indices into clusters."""
        if len(indices) == 0:
            return []

        groups: List[List[int]] = []
        current_group = [int(indices[0])]

        for idx in indices[1:]:
            if int(idx) - current_group[-1] <= gap:
                current_group.append(int(idx))
            else:
                groups.append(current_group)
                current_group = [int(idx)]

        groups.append(current_group)
        return groups
