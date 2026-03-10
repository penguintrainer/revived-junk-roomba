"""RGBD-based obstacle detector using RealSense D435i.

Subscribes to /camera/aligned_depth_to_color/image_raw and
/camera/color/image_raw. Applies RANSAC floor plane fitting and
detects obstacles with depth deviation > 2-5cm threshold.
Applies hole_filling_filter for glossy surfaces.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import cv2
import numpy as np

from geometry_msgs.msg import Point, Vector3
from sensor_msgs.msg import Image

from roomba_msgs.msg import Obstacle

# Detection parameters
FLOOR_DEVIATION_THRESHOLD_M = 0.03  # 3cm above floor plane → obstacle
FLOOR_DEVIATION_MIN_M = 0.02        # 2cm minimum
MAX_OBSTACLE_HEIGHT_M = 0.50        # Objects taller than 50cm likely walls
MIN_OBSTACLE_HEIGHT_M = 0.01        # 1cm minimum height
RANSAC_ITERATIONS = 100
RANSAC_THRESHOLD_M = 0.01           # 1cm inlier threshold
MIN_CONFIDENCE = 0.3
WALL_PROXIMITY_M = 0.20             # Ignore obstacles within 20cm of walls

# Camera intrinsics (RealSense D435i default 640x480)
# These would normally come from /camera/depth/camera_info
DEFAULT_FX = 383.0
DEFAULT_FY = 383.0
DEFAULT_CX = 320.0
DEFAULT_CY = 240.0
DEFAULT_DEPTH_SCALE = 0.001  # mm to meters

# Hole filling kernel size (for glossy surfaces)
HOLE_FILL_KERNEL_SIZE = 5


class RgbdDetector:
    """Detects floor obstacles from RealSense D435i aligned depth images.

    Uses RANSAC floor plane fitting to separate floor from obstacles,
    with hole filling for glossy/reflective surfaces.

    Parameters
    ----------
    fx, fy : float
        Camera focal lengths (pixels).
    cx, cy : float
        Camera principal point (pixels).
    depth_scale : float
        Depth value to meters conversion factor.
    floor_deviation_threshold_m : float
        Minimum height above floor plane to classify as obstacle.
    """

    def __init__(
        self,
        fx: float = DEFAULT_FX,
        fy: float = DEFAULT_FY,
        cx: float = DEFAULT_CX,
        cy: float = DEFAULT_CY,
        depth_scale: float = DEFAULT_DEPTH_SCALE,
        floor_deviation_threshold_m: float = FLOOR_DEVIATION_THRESHOLD_M,
    ) -> None:
        self._fx = fx
        self._fy = fy
        self._cx = cx
        self._cy = cy
        self._depth_scale = depth_scale
        self._floor_threshold = floor_deviation_threshold_m
        self._floor_plane: Optional[np.ndarray] = None  # [a, b, c, d] ax+by+cz+d=0

    def update_camera_info(self, fx: float, fy: float, cx: float, cy: float) -> None:
        """Update camera intrinsics from camera_info topic.

        Parameters
        ----------
        fx, fy : float
            Camera focal lengths.
        cx, cy : float
            Camera principal point.
        """
        self._fx = fx
        self._fy = fy
        self._cx = cx
        self._cy = cy

    def detect(
        self,
        depth_msg: Image,
        color_msg: Optional[Image] = None,
    ) -> List[Obstacle]:
        """Process depth image and return list of detected obstacles.

        Parameters
        ----------
        depth_msg : Image
            Aligned depth image from RealSense.
        color_msg : Image, optional
            Color image (used for context, not required).

        Returns
        -------
        List[Obstacle]
            Detected obstacles with type, position, and confidence.
        """
        # Convert ROS Image to numpy array
        depth_array = self._decode_depth_image(depth_msg)
        if depth_array is None:
            return []

        # Apply hole filling filter (for glossy/reflective surfaces)
        depth_filled = self._apply_hole_filling(depth_array)

        # Convert depth to 3D point cloud (subsampled for performance)
        points_3d = self._depth_to_pointcloud(depth_filled)
        if points_3d is None or len(points_3d) == 0:
            return []

        # Fit floor plane using RANSAC
        floor_plane = self._fit_floor_plane_ransac(points_3d)
        if floor_plane is not None:
            self._floor_plane = floor_plane

        if self._floor_plane is None:
            return []

        # Find obstacles above floor plane
        obstacles = self._extract_obstacles(points_3d, self._floor_plane, depth_filled)

        return [obs for obs in obstacles if obs.confidence >= MIN_CONFIDENCE]

    # -------------------------------------------------------------------------
    # Image processing
    # -------------------------------------------------------------------------

    def _decode_depth_image(self, msg: Image) -> Optional[np.ndarray]:
        """Convert ROS depth Image to float32 numpy array in meters."""
        try:
            height = msg.height
            width = msg.width
            encoding = msg.encoding

            if encoding in ('16UC1', 'mono16'):
                raw = np.frombuffer(msg.data, dtype=np.uint16)
                depth = raw.reshape((height, width)).astype(np.float32)
                depth *= self._depth_scale  # Convert mm → meters
            elif encoding == '32FC1':
                raw = np.frombuffer(msg.data, dtype=np.float32)
                depth = raw.reshape((height, width))
            else:
                depth = np.frombuffer(msg.data, dtype=np.uint16)
                depth = depth.reshape((height, width)).astype(np.float32)
                depth *= self._depth_scale

            # Zero values = invalid (no depth reading)
            depth[depth == 0] = np.nan
            return depth
        except Exception:
            return None

    def _apply_hole_filling(self, depth: np.ndarray) -> np.ndarray:
        """Apply morphological hole filling for glossy/reflective surfaces.

        Uses dilation + erosion to fill small holes in depth image,
        mimicking RealSense SDK's hole_filling_filter behavior.

        Parameters
        ----------
        depth : np.ndarray
            Input depth image (float32, meters, NaN for invalid).

        Returns
        -------
        np.ndarray
            Depth image with holes filled.
        """
        # Convert NaN to 0 for OpenCV processing
        depth_cv = np.where(np.isnan(depth), 0.0, depth).astype(np.float32)
        kernel = np.ones((HOLE_FILL_KERNEL_SIZE, HOLE_FILL_KERNEL_SIZE), np.uint8)

        # Create valid pixel mask
        valid_mask = (depth_cv > 0).astype(np.uint8)

        # Dilate valid pixels to fill small holes
        valid_dilated = cv2.dilate(valid_mask, kernel, iterations=1)

        # For each hole pixel, use the mean of valid dilated neighbors
        hole_mask = (valid_mask == 0) & (valid_dilated > 0)

        if hole_mask.any():
            # Apply median blur to fill in holes
            depth_filled = cv2.medianBlur(depth_cv, HOLE_FILL_KERNEL_SIZE)
            result = np.where(hole_mask, depth_filled, depth_cv)
        else:
            result = depth_cv

        # Restore NaN for pixels that couldn't be filled
        result = np.where(result == 0, np.nan, result)
        return result

    def _depth_to_pointcloud(self, depth: np.ndarray) -> Optional[np.ndarray]:
        """Convert depth image to 3D point cloud.

        Uses subsampling (1/4 resolution) for performance on ARM64/Tegra.

        Parameters
        ----------
        depth : np.ndarray
            Depth image in meters.

        Returns
        -------
        np.ndarray or None
            Nx3 array of 3D points in camera frame, or None on failure.
        """
        # Subsample 1/4 for performance
        depth_sub = depth[::4, ::4]
        h, w = depth_sub.shape

        rows, cols = np.mgrid[0:h, 0:w]
        # Scale pixel coordinates back to original resolution
        rows_orig = rows * 4
        cols_orig = cols * 4

        # Backproject pixels to 3D
        z = depth_sub
        x = (cols_orig - self._cx) * z / self._fx
        y = (rows_orig - self._cy) * z / self._fy

        # Stack and filter valid points
        points = np.stack([x, y, z], axis=-1).reshape(-1, 3)
        valid = np.isfinite(points).all(axis=1) & (points[:, 2] > 0.1) & \
                (points[:, 2] < 3.0)

        return points[valid] if valid.any() else None

    def _fit_floor_plane_ransac(
        self, points: np.ndarray
    ) -> Optional[np.ndarray]:
        """Fit floor plane using RANSAC.

        The floor is typically the dominant planar surface in the lower
        portion of the image.

        Parameters
        ----------
        points : np.ndarray
            Nx3 array of 3D points in camera frame.

        Returns
        -------
        np.ndarray or None
            Floor plane coefficients [a, b, c, d] for ax+by+cz+d=0,
            or None if fitting fails.
        """
        if len(points) < 10:
            return None

        # Focus on lower portion of image (floor region, y > 0 in camera frame)
        floor_candidates = points[points[:, 1] > 0]
        if len(floor_candidates) < 10:
            floor_candidates = points

        best_plane = None
        best_inliers = 0
        threshold = RANSAC_THRESHOLD_M

        rng = np.random.default_rng(42)

        for _ in range(RANSAC_ITERATIONS):
            if len(floor_candidates) < 3:
                break

            # Sample 3 random points
            idx = rng.choice(len(floor_candidates), 3, replace=False)
            p1, p2, p3 = floor_candidates[idx]

            # Compute plane normal
            v1 = p2 - p1
            v2 = p3 - p1
            normal = np.cross(v1, v2)
            norm = np.linalg.norm(normal)
            if norm < 1e-6:
                continue

            normal = normal / norm
            d = -np.dot(normal, p1)
            plane = np.append(normal, d)

            # Count inliers
            distances = np.abs(points @ normal + d)
            inliers = np.sum(distances < threshold)

            if inliers > best_inliers:
                best_inliers = inliers
                best_plane = plane

        # Require at least 10% of points to be inliers
        if best_plane is None or best_inliers < len(points) * 0.1:
            return None

        return best_plane

    def _extract_obstacles(
        self,
        points: np.ndarray,
        floor_plane: np.ndarray,
        depth: np.ndarray,
    ) -> List[Obstacle]:
        """Extract obstacles as points significantly above the floor plane.

        Parameters
        ----------
        points : np.ndarray
            Nx3 point cloud in camera frame.
        floor_plane : np.ndarray
            Floor plane [a, b, c, d].
        depth : np.ndarray
            Original depth image for context.

        Returns
        -------
        List[Obstacle]
            Detected obstacles in robot base_link frame.
        """
        normal = floor_plane[:3]
        d = floor_plane[3]

        # Signed distance of each point from floor plane
        # Positive = above floor
        distances = points @ normal + d

        # Points above floor threshold (obstacles)
        obstacle_mask = (distances > self._floor_threshold) & \
                        (distances < MAX_OBSTACLE_HEIGHT_M)

        obstacle_points = points[obstacle_mask]

        if len(obstacle_points) == 0:
            return []

        # Cluster obstacle points using simple grid-based clustering
        clusters = self._cluster_points(obstacle_points)
        obstacles = []

        for cluster in clusters:
            if len(cluster) < 3:  # Too few points to be a real obstacle
                continue

            cluster_arr = np.array(cluster)
            center = cluster_arr.mean(axis=0)
            extent = cluster_arr.max(axis=0) - cluster_arr.min(axis=0)

            # Convert camera frame (x-right, y-down, z-forward) to
            # robot frame (x-forward, y-left, z-up)
            # Camera is mounted looking forward
            robot_x = float(center[2])    # z_cam → x_robot (forward)
            robot_y = -float(center[0])   # x_cam → -y_robot (right → left)
            robot_z = -float(center[1])   # y_cam → -z_robot (up in robot frame)

            # Skip if too close to walls (large width extent)
            if float(extent[0]) > WALL_PROXIMITY_M and float(extent[2]) < 0.3:
                obs_type = Obstacle.FLOOR_OBJECT
            elif float(extent[0]) > 1.0:  # Wide → likely wall
                continue
            elif float(center[2]) < CABLE_FLAT_DEPTH:
                obs_type = Obstacle.CABLE
            else:
                obs_type = Obstacle.FLOOR_OBJECT

            obs = Obstacle()
            obs.position = Point(x=robot_x, y=robot_y, z=0.0)
            obs.obstacle_type = obs_type
            obs.detection_source = Obstacle.SOURCE_RGBD

            # Confidence based on cluster size and deviation from floor
            cluster_distances = points[obstacle_mask] @ normal + d
            mean_deviation = float(np.mean(cluster_distances))
            obs.confidence = min(0.95, mean_deviation / MAX_OBSTACLE_HEIGHT_M + 0.3)

            obs.bounding_size = Vector3(
                x=float(extent[2]),  # depth extent → x size
                y=float(extent[0]),  # width extent → y size
                z=float(extent[1]),  # height extent
            )

            obstacles.append(obs)

        return obstacles

    @staticmethod
    def _cluster_points(
        points: np.ndarray,
        voxel_size: float = 0.05,
    ) -> List[List[np.ndarray]]:
        """Simple voxel-grid clustering of 3D points.

        Parameters
        ----------
        points : np.ndarray
            Nx3 array of 3D points.
        voxel_size : float
            Voxel size in meters for clustering.

        Returns
        -------
        List[List[np.ndarray]]
            List of clusters, each cluster is a list of 3D points.
        """
        if len(points) == 0:
            return []

        # Assign each point to a voxel
        voxel_keys = (points / voxel_size).astype(int)

        # Group points by voxel
        voxel_dict: dict = {}
        for i, key in enumerate(voxel_keys):
            k = tuple(key)
            if k not in voxel_dict:
                voxel_dict[k] = []
            voxel_dict[k].append(points[i])

        # Merge adjacent voxels into clusters (simple connected components)
        visited = set()
        clusters = []

        for voxel in voxel_dict:
            if voxel in visited:
                continue

            cluster = []
            stack = [voxel]

            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)

                if current in voxel_dict:
                    cluster.extend(voxel_dict[current])

                    # Check 6-connected neighbors
                    cx, cy, cz = current
                    for dx, dy, dz in [
                        (1, 0, 0), (-1, 0, 0),
                        (0, 1, 0), (0, -1, 0),
                        (0, 0, 1), (0, 0, -1),
                    ]:
                        neighbor = (cx + dx, cy + dy, cz + dz)
                        if neighbor in voxel_dict and neighbor not in visited:
                            stack.append(neighbor)

            if cluster:
                clusters.append(cluster)

        return clusters


# Cable flat depth threshold (objects < 15cm away are likely floor cables)
CABLE_FLAT_DEPTH = 0.15
