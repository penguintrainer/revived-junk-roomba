cmake_minimum_required(VERSION 3.8 FATAL_ERROR)
project(roomba_interfaces)

find_package(ament_cmake_auto REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(std_srvs REQUIRED)

find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/RobotStatus.msg"
  "msg/AudioCue.msg"
  "srv/SetMode.srv"
  "action/CleanArea.action"
)

ament_export_dependencies(rclpy std_msgs builtin_interfaces std_srvs)
ament_export_interfaces(rosidl_runtime_c rosidl_runtime_cpp)

ament_package()
