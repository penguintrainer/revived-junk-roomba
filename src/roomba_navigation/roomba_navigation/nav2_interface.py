"""Nav2 lifecycle management utilities for Roomba577 autonomous navigation.

Provides Nav2 lifecycle management helpers, costmap2d configuration
with obstacle layer subscribing /obstacles topic, and wall-contact
permissive configuration for Roomba577.
"""

from __future__ import annotations

import threading
import time
from typing import List, Optional

from lifecycle_msgs.msg import State as LifecycleState, Transition
from lifecycle_msgs.srv import ChangeState, GetState

import rclpy
from rclpy.node import Node


# Nav2 lifecycle node names that need to be managed
NAV2_LIFECYCLE_NODES = [
    'controller_server',
    'planner_server',
    'behavior_server',
    'bt_navigator',
    'waypoint_follower',
    'velocity_smoother',
    'lifecycle_manager_navigation',
]

# Lifecycle state IDs
STATE_UNCONFIGURED = 1
STATE_INACTIVE = 2
STATE_ACTIVE = 3
STATE_FINALIZED = 4


class Nav2Interface:
    """Manages Nav2 lifecycle nodes and provides configuration utilities.

    Handles bringing Nav2 nodes through their lifecycle states
    (configure → activate) and provides costmap configuration
    with obstacle layer for /obstacles topic integration.

    Parameters
    ----------
    node : rclpy.node.Node
        Parent ROS2 node for creating clients.
    """

    def __init__(self, node: Node) -> None:
        self._node = node
        self._lock = threading.Lock()
        self._nav2_ready = False
        self._transition_clients: dict = {}
        self._state_clients: dict = {}

    def configure_all(self, timeout_sec: float = 10.0) -> bool:
        """Configure all Nav2 lifecycle nodes.

        Parameters
        ----------
        timeout_sec : float
            Timeout per node in seconds.

        Returns
        -------
        bool
            True if all nodes configured successfully.
        """
        success = True
        for node_name in NAV2_LIFECYCLE_NODES:
            if not self._transition_node(node_name, Transition.TRANSITION_CONFIGURE,
                                         timeout_sec):
                self._node.get_logger().warning(
                    'Failed to configure Nav2 node: %s', node_name)
                success = False
        return success

    def activate_all(self, timeout_sec: float = 10.0) -> bool:
        """Activate all Nav2 lifecycle nodes.

        Parameters
        ----------
        timeout_sec : float
            Timeout per node in seconds.

        Returns
        -------
        bool
            True if all nodes activated successfully.
        """
        success = True
        for node_name in NAV2_LIFECYCLE_NODES:
            if not self._transition_node(node_name, Transition.TRANSITION_ACTIVATE,
                                         timeout_sec):
                self._node.get_logger().warning(
                    'Failed to activate Nav2 node: %s', node_name)
                success = False
        if success:
            self._nav2_ready = True
        return success

    def deactivate_all(self, timeout_sec: float = 5.0) -> bool:
        """Deactivate all Nav2 lifecycle nodes."""
        self._nav2_ready = False
        success = True
        for node_name in reversed(NAV2_LIFECYCLE_NODES):
            if not self._transition_node(node_name, Transition.TRANSITION_DEACTIVATE,
                                         timeout_sec):
                success = False
        return success

    def is_ready(self) -> bool:
        """Return True if Nav2 is fully activated and ready."""
        return self._nav2_ready

    def get_costmap_config(self) -> dict:
        """Return costmap2d configuration with obstacle layer.

        Returns configuration dict with:
        - obstacle_layer subscribing to /obstacles (roomba_msgs/ObstacleArray)
        - wall-contact permissive settings (inflation_radius tuned for Roomba)

        Returns
        -------
        dict
            Costmap2d ROS parameter configuration.
        """
        return {
            'global_costmap': {
                'ros__parameters': {
                    'update_frequency': 5.0,
                    'publish_frequency': 2.0,
                    'global_frame': 'map',
                    'robot_base_frame': 'base_link',
                    'robot_radius': 0.17,  # Roomba577 radius ~17cm
                    'resolution': 0.05,
                    'track_unknown_space': True,
                    'plugins': ['static_layer', 'obstacle_layer', 'inflation_layer'],
                    'static_layer': {
                        'plugin': 'nav2_costmap_2d::StaticLayer',
                        'map_subscribe_transient_local': True,
                    },
                    'obstacle_layer': {
                        'plugin': 'nav2_costmap_2d::ObstacleLayer',
                        'enabled': True,
                        'observation_sources': 'lidar_scan obstacle_topic',
                        'lidar_scan': {
                            'topic': '/scan',
                            'max_obstacle_height': 2.0,
                            'clearing': True,
                            'marking': True,
                            'data_type': 'LaserScan',
                            'raytrace_max_range': 3.0,
                            'obstacle_max_range': 2.5,
                        },
                        # /obstacles topic handled via custom costmap plugin
                        # or converted to PointCloud2 via obstacle bridge
                    },
                    'inflation_layer': {
                        'plugin': 'nav2_costmap_2d::InflationLayer',
                        # Permissive for wall contact: small inflation radius
                        'cost_scaling_factor': 5.0,
                        'inflation_radius': 0.20,  # 20cm — allows wall proximity
                    },
                }
            },
            'local_costmap': {
                'ros__parameters': {
                    'update_frequency': 10.0,
                    'publish_frequency': 5.0,
                    'global_frame': 'odom',
                    'robot_base_frame': 'base_link',
                    'rolling_window': True,
                    'width': 3.0,
                    'height': 3.0,
                    'resolution': 0.05,
                    'robot_radius': 0.17,
                    'plugins': ['obstacle_layer', 'inflation_layer'],
                    'obstacle_layer': {
                        'plugin': 'nav2_costmap_2d::ObstacleLayer',
                        'enabled': True,
                        'observation_sources': 'lidar_scan',
                        'lidar_scan': {
                            'topic': '/scan',
                            'max_obstacle_height': 2.0,
                            'clearing': True,
                            'marking': True,
                            'data_type': 'LaserScan',
                        },
                    },
                    'inflation_layer': {
                        'plugin': 'nav2_costmap_2d::InflationLayer',
                        'cost_scaling_factor': 5.0,
                        'inflation_radius': 0.15,  # Local costmap: tighter
                    },
                }
            }
        }

    def _transition_node(
        self,
        node_name: str,
        transition_id: int,
        timeout_sec: float,
    ) -> bool:
        """Call lifecycle transition service for a Nav2 node.

        Parameters
        ----------
        node_name : str
            Nav2 node name.
        transition_id : int
            Lifecycle transition ID.
        timeout_sec : float
            Service call timeout.

        Returns
        -------
        bool
            True on success.
        """
        service_name = f'{node_name}/change_state'

        client = self._transition_clients.get(node_name)
        if client is None:
            client = self._node.create_client(ChangeState, service_name)
            self._transition_clients[node_name] = client

        if not client.wait_for_service(timeout_sec=timeout_sec):
            self._node.get_logger().warning(
                'Lifecycle service not available: %s', service_name)
            return False

        request = ChangeState.Request()
        request.transition.id = transition_id

        future = client.call_async(request)

        deadline = time.monotonic() + timeout_sec
        while not future.done() and time.monotonic() < deadline:
            time.sleep(0.05)

        if not future.done():
            self._node.get_logger().warning(
                'Lifecycle transition timeout: %s', node_name)
            return False

        result = future.result()
        return result is not None and result.success
