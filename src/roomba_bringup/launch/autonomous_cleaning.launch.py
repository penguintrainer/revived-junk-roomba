"""Launch file for US3: Autonomous cleaning mode with obstacle avoidance.

Launches Nav2, AMCL, map_server, ydlidar_driver, realsense_node,
obstacle_detector, roomba_navigation, roomba_driver, mode_manager,
and safety_monitor for AMCL-based boustrophedon autonomous cleaning.

Usage:
    ros2 launch roomba_bringup autonomous_cleaning.launch.py map:=/path/to/map.yaml

    Required arguments:
        map:=/path/to/map.yaml  (pre-built SLAM map)

    Optional arguments:
        serial_port:=/dev/ttyUSB0
        use_sim_time:=false
        autostart:=true
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    LogInfo,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import LifecycleNode, Node, PushRosNamespace


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for autonomous cleaning mode."""
    bringup_dir = get_package_share_directory('roomba_bringup')
    roomba_params = os.path.join(bringup_dir, 'config', 'roomba_params.yaml')
    nav2_params = os.path.join(bringup_dir, 'config', 'nav2_params.yaml')
    sensor_params = os.path.join(bringup_dir, 'config', 'sensor_params.yaml')

    # Launch arguments
    map_arg = DeclareLaunchArgument(
        'map',
        description='Full path to pre-built map YAML file',
    )
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyUSB0',
        description='Serial port for Roomba577 connection',
    )
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock',
    )
    autostart_arg = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically activate Nav2 lifecycle nodes',
    )

    map_path = LaunchConfiguration('map')
    serial_port = LaunchConfiguration('serial_port')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')

    # ── Sensor drivers ────────────────────────────────────────────────────────

    # YDLIDAR T-mini Plus driver
    ydlidar_node = Node(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='ydlidar_node',
        parameters=[sensor_params],
        output='screen',
    )

    # Intel RealSense D435i driver
    realsense_node = Node(
        package='realsense2_camera',
        executable='realsense2_camera_node',
        name='realsense2_camera_node',
        parameters=[sensor_params],
        output='screen',
        remappings=[
            ('depth/image_rect_raw',
             'aligned_depth_to_color/image_raw'),
        ],
    )

    # ── Obstacle detection ────────────────────────────────────────────────────

    obstacle_detector_node = LifecycleNode(
        package='obstacle_detector',
        executable='obstacle_detector_node',
        name='obstacle_detector_node',
        namespace='',
        parameters=[sensor_params, {'use_sim_time': use_sim_time}],
        output='screen',
    )

    # ── Navigation (Nav2 + map_server + AMCL) ─────────────────────────────────

    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        parameters=[
            nav2_params,
            {
                'yaml_filename': map_path,
                'use_sim_time': use_sim_time,
            },
        ],
        output='screen',
    )

    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        parameters=[nav2_params, {'use_sim_time': use_sim_time}],
        output='screen',
    )

    nav2_lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[
            {
                'use_sim_time': use_sim_time,
                'autostart': autostart,
                'node_names': [
                    'map_server',
                    'amcl',
                    'controller_server',
                    'planner_server',
                    'behavior_server',
                    'bt_navigator',
                    'waypoint_follower',
                    'velocity_smoother',
                ],
            }
        ],
    )

    controller_server_node = Node(
        package='nav2_controller',
        executable='controller_server',
        output='screen',
        parameters=[nav2_params, {'use_sim_time': use_sim_time}],
        remappings=[('cmd_vel', 'cmd_vel_nav')],
    )

    planner_server_node = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[nav2_params, {'use_sim_time': use_sim_time}],
    )

    behavior_server_node = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[nav2_params, {'use_sim_time': use_sim_time}],
    )

    bt_navigator_node = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[nav2_params, {'use_sim_time': use_sim_time}],
    )

    # ── Coverage navigation ────────────────────────────────────────────────────

    coverage_planner_node = LifecycleNode(
        package='roomba_navigation',
        executable='coverage_planner_node',
        name='coverage_planner_node',
        namespace='',
        parameters=[nav2_params, {'use_sim_time': use_sim_time}],
        output='screen',
    )

    # ── Core Roomba nodes ─────────────────────────────────────────────────────

    roomba_driver_node = LifecycleNode(
        package='roomba_driver',
        executable='roomba_driver_node',
        name='roomba_driver_node',
        namespace='',
        parameters=[
            roomba_params,
            {
                'serial_port': serial_port,
                'use_sim_time': use_sim_time,
            },
        ],
        output='screen',
    )

    safety_monitor_node = LifecycleNode(
        package='roomba_safety',
        executable='safety_monitor_node',
        name='safety_monitor_node',
        namespace='',
        parameters=[
            roomba_params,
            {'use_sim_time': use_sim_time},
        ],
        output='screen',
    )

    mode_manager_node = LifecycleNode(
        package='roomba_mode_manager',
        executable='mode_manager_node',
        name='mode_manager_node',
        namespace='',
        parameters=[
            roomba_params,
            {
                'use_sim_time': use_sim_time,
                'initial_mode': 3,  # MODE_AUTONOMOUS
            },
        ],
        output='screen',
    )

    return LaunchDescription([
        # Arguments
        map_arg,
        serial_port_arg,
        use_sim_time_arg,
        autostart_arg,
        LogInfo(msg='Starting Roomba577 autonomous cleaning mode...'),
        # Sensor drivers
        ydlidar_node,
        realsense_node,
        obstacle_detector_node,
        # Navigation stack
        map_server_node,
        amcl_node,
        controller_server_node,
        planner_server_node,
        behavior_server_node,
        bt_navigator_node,
        coverage_planner_node,
        nav2_lifecycle_manager,
        # Core Roomba nodes
        roomba_driver_node,
        safety_monitor_node,
        mode_manager_node,
        LogInfo(msg='Autonomous cleaning launch complete.'),
        LogInfo(msg='Monitor: ros2 topic echo /roomba/state'),
        LogInfo(msg='Monitor coverage: ros2 topic echo /roomba/mode'),
    ])
