"""Launch file for US1: Random cleaning mode.

Launches roomba_driver, mode_manager, and safety_monitor nodes
configured for random walk cleaning (Roomba built-in OI algorithm).

Usage:
    ros2 launch roomba_bringup random_cleaning.launch.py

    Optional arguments:
        serial_port:=/dev/ttyUSB0
        use_sim_time:=false
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for random cleaning mode."""
    bringup_dir = get_package_share_directory('roomba_bringup')
    roomba_params = os.path.join(bringup_dir, 'config', 'roomba_params.yaml')

    # Launch arguments
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

    serial_port = LaunchConfiguration('serial_port')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # roomba_driver_node (lifecycle)
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

    # safety_monitor_node (lifecycle)
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

    # mode_manager_node (lifecycle) — starts in IDLE, transitions to RANDOM
    mode_manager_node = LifecycleNode(
        package='roomba_mode_manager',
        executable='mode_manager_node',
        name='mode_manager_node',
        namespace='',
        parameters=[
            roomba_params,
            {
                'use_sim_time': use_sim_time,
                # Initial mode: RANDOM (1)
                'initial_mode': 1,
            },
        ],
        output='screen',
    )

    return LaunchDescription([
        serial_port_arg,
        use_sim_time_arg,
        LogInfo(msg='Starting Roomba577 random cleaning mode...'),
        roomba_driver_node,
        safety_monitor_node,
        mode_manager_node,
        LogInfo(msg='Random cleaning launch complete. Monitor: ros2 topic echo /roomba/state'),
        LogInfo(msg='Stop: ros2 service call /roomba/emergency_stop std_srvs/srv/Trigger'),
    ])
