"""Launch file for US4: Full system with all modes and runtime mode switching.

Launches all sensor drivers, all processing nodes, and all core nodes
for the complete Roomba577 multi-mode cleaning system.
Supports runtime switching between RANDOM/MANUAL/AUTONOMOUS modes.

Usage:
    ros2 launch roomba_bringup full_system.launch.py map:=/path/to/map.yaml

    Required arguments:
        map:=/path/to/map.yaml  (pre-built SLAM map)

    Optional arguments:
        serial_port:=/dev/ttyUSB0
        joy_device:=/dev/input/js0
        use_sim_time:=false
        autostart:=true
        initial_mode:=0  (0=IDLE, 1=RANDOM, 2=MANUAL, 3=AUTONOMOUS)

Switching modes at runtime:
    ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 1}"  # RANDOM
    ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 2}"  # MANUAL
    ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 3}"  # AUTONOMOUS
    ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 0}"  # IDLE (stop)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for full multi-mode system."""
    bringup_dir = get_package_share_directory('roomba_bringup')
    roomba_params = os.path.join(bringup_dir, 'config', 'roomba_params.yaml')
    nav2_params = os.path.join(bringup_dir, 'config', 'nav2_params.yaml')
    sensor_params = os.path.join(bringup_dir, 'config', 'sensor_params.yaml')

    # Launch arguments
    map_arg = DeclareLaunchArgument(
        'map',
        default_value='',
        description='Full path to pre-built map YAML file (required for AUTONOMOUS mode)',
    )
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyUSB0',
        description='Serial port for Roomba577 connection',
    )
    joy_device_arg = DeclareLaunchArgument(
        'joy_device',
        default_value='/dev/input/js0',
        description='Joy-Con input device path',
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
    initial_mode_arg = DeclareLaunchArgument(
        'initial_mode',
        default_value='0',
        description='Initial driving mode (0=IDLE, 1=RANDOM, 2=MANUAL, 3=AUTONOMOUS)',
    )

    map_path = LaunchConfiguration('map')
    serial_port = LaunchConfiguration('serial_port')
    joy_device = LaunchConfiguration('joy_device')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    initial_mode = LaunchConfiguration('initial_mode')

    # ── Sensor drivers ────────────────────────────────────────────────────────

    # Joy-Con via joy_node
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        parameters=[
            {
                'device_name': joy_device,
                'deadzone': 0.05,
                'autorepeat_rate': 50.0,
                'use_sim_time': use_sim_time,
            }
        ],
        output='screen',
    )

    # YDLIDAR T-mini Plus
    ydlidar_node = Node(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='ydlidar_node',
        parameters=[sensor_params, {'use_sim_time': use_sim_time}],
        output='screen',
    )

    # Intel RealSense D435i
    realsense_node = Node(
        package='realsense2_camera',
        executable='realsense2_camera_node',
        name='realsense2_camera_node',
        parameters=[sensor_params, {'use_sim_time': use_sim_time}],
        output='screen',
    )

    # ── Processing nodes ──────────────────────────────────────────────────────

    # Joy-Con teleoperation (lifecycle)
    joycon_teleop_node = LifecycleNode(
        package='joycon_teleop',
        executable='joycon_teleop_node',
        name='joycon_teleop_node',
        namespace='',
        parameters=[
            roomba_params,
            {
                'max_linear_speed_m_s': 0.3,
                'max_angular_speed_rad_s': 4.25,
                'use_sim_time': use_sim_time,
            },
        ],
        output='screen',
    )

    # Obstacle detection (lifecycle)
    obstacle_detector_node = LifecycleNode(
        package='obstacle_detector',
        executable='obstacle_detector_node',
        name='obstacle_detector_node',
        namespace='',
        parameters=[sensor_params, {'use_sim_time': use_sim_time}],
        output='screen',
    )

    # ── Navigation stack (Nav2) ───────────────────────────────────────────────

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
                ],
            }
        ],
    )

    # Coverage planner (lifecycle)
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
        parameters=[roomba_params, {'use_sim_time': use_sim_time}],
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
                'initial_mode': initial_mode,
            },
        ],
        output='screen',
    )

    return LaunchDescription([
        # Arguments
        map_arg,
        serial_port_arg,
        joy_device_arg,
        use_sim_time_arg,
        autostart_arg,
        initial_mode_arg,
        LogInfo(msg='Starting Roomba577 full multi-mode cleaning system...'),
        # Sensor drivers
        ydlidar_node,
        realsense_node,
        joy_node,
        # Processing nodes
        joycon_teleop_node,
        obstacle_detector_node,
        # Navigation stack
        map_server_node,
        amcl_node,
        controller_server_node,
        planner_server_node,
        behavior_server_node,
        bt_navigator_node,
        nav2_lifecycle_manager,
        coverage_planner_node,
        # Core Roomba nodes
        roomba_driver_node,
        safety_monitor_node,
        mode_manager_node,
        LogInfo(msg='Full system launch complete.'),
        LogInfo(msg='Switch modes: ros2 service call /roomba/set_mode roomba_msgs/srv/SetMode "{mode: 1}"'),
        LogInfo(msg='Emergency stop: ros2 service call /roomba/emergency_stop std_srvs/srv/Trigger'),
        LogInfo(msg='Monitor: ros2 topic echo /roomba/state && ros2 topic echo /roomba/mode'),
    ])
