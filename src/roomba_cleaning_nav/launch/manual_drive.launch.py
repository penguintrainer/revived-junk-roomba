"""Launch file for the Joy-Con manual drive node.

Usage (once the workspace is built and sourced):

    ros2 launch roomba_cleaning_nav manual_drive.launch.py

Optional arguments:
    use_sim_time:=true   Use simulation clock (default: false)
    log_level:=debug     Set node log level (default: info)
    namespace:=''        Node namespace (default: empty)
"""
from __future__ import annotations

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="false",
        description="Use simulation clock if true",
    )
    log_level_arg = DeclareLaunchArgument(
        "log_level",
        default_value="info",
        description="Log level for the node (debug|info|warn|error|fatal)",
    )
    namespace_arg = DeclareLaunchArgument(
        "namespace",
        default_value="",
        description="ROS namespace for the node",
    )

    manual_drive_node = Node(
        package="roomba_cleaning_nav",
        executable="manual_drive_node",
        name="manual_drive_node",
        namespace=LaunchConfiguration("namespace"),
        parameters=[
            {"use_sim_time": LaunchConfiguration("use_sim_time")},
        ],
        arguments=["--ros-args", "--log-level", LaunchConfiguration("log_level")],
        output="screen",
        emulate_tty=True,
    )

    return LaunchDescription(
        [
            use_sim_time_arg,
            log_level_arg,
            namespace_arg,
            manual_drive_node,
        ]
    )
