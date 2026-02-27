from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    ld = LaunchDescription()

    # Roomba Driver Node
    roomba_driver_node = Node(
        package='roomba_cleaning_nav',
        executable='roomba_driver',
        name='roomba_driver',
        output='screen'
    )

    # Teleop Node (Joy-Con)
    teleop_node = Node(
        package='roomba_cleaning_nav',
        executable='teleop_node',
        name='teleop_node',
        output='screen'
    )

    # Joy Node (for Joy-Con input)
    joy_node = Node(
        package='joy_linux', # Assumes joy_linux is installed
        executable='joy_node',
        name='joy_node',
        output='screen',
        parameters=[{
            'dev': '/dev/input/js0', # Adjust as needed for your Joy-Con
            'deadzone': 0.1,
            'autorepeat_rate': 20.0,
        }]
    )

    ld.add_action(roomba_driver_node)
    ld.add_action(teleop_node)
    ld.add_action(joy_node) # Add joy_node to the launch description

    return ld
