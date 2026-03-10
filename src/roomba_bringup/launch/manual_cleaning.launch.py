"""Launch file for US2: Manual cleaning mode (Joy-Con control).

Launches joy_node, joycon_teleop, roomba_driver, mode_manager,
and safety_monitor for Joy-Con manual control at 300mm/s max speed.

Usage:
    ros2 launch roomba_bringup manual_cleaning.launch.py

    Optional arguments:
        serial_port:=/dev/ttyUSB0
        joy_device:=/dev/input/js0
        use_sim_time:=false
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node


def generate_launch_description() -> LaunchDescription:
    """Generate launch description for manual cleaning mode."""
    bringup_dir = get_package_share_directory('roomba_bringup')
    roomba_params = os.path.join(bringup_dir, 'config', 'roomba_params.yaml')

    # Launch arguments
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

    serial_port = LaunchConfiguration('serial_port')
    joy_device = LaunchConfiguration('joy_device')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # joy_node (from joy ROS2 package)
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

    # joycon_teleop_node (lifecycle)
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

    # mode_manager_node (lifecycle) — starts in MANUAL mode
    mode_manager_node = LifecycleNode(
        package='roomba_mode_manager',
        executable='mode_manager_node',
        name='mode_manager_node',
        namespace='',
        parameters=[
            roomba_params,
            {
                'use_sim_time': use_sim_time,
                'initial_mode': 2,  # MODE_MANUAL
            },
        ],
        output='screen',
    )

    return LaunchDescription([
        serial_port_arg,
        joy_device_arg,
        use_sim_time_arg,
        LogInfo(msg='Starting Roomba577 manual cleaning mode (Joy-Con)...'),
        joy_node,
        joycon_teleop_node,
        roomba_driver_node,
        safety_monitor_node,
        mode_manager_node,
        LogInfo(msg='Manual cleaning launch complete.'),
        LogInfo(msg='Use Joy-Con left stick to control. SL/SR for emergency stop.'),
    ])
