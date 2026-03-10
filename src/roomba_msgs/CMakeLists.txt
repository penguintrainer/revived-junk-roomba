cmake_minimum_required(VERSION 3.8)
project(roomba_msgs)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(action_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/RoombaState.msg"
  "msg/DrivingMode.msg"
  "msg/Bumper.msg"
  "msg/WheelDrop.msg"
  "msg/ObstacleArray.msg"
  "msg/Obstacle.msg"
  "srv/SetMode.srv"
  "srv/GetState.srv"
  "action/CoverageClean.action"
  DEPENDENCIES std_msgs geometry_msgs nav_msgs builtin_interfaces action_msgs
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
