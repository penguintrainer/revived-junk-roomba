# revived-junk-roomba Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-21

## Active Technologies
- Python 3.13+, ROS2 Jazzy (`rclpy`) + `joycon-python`, `hidapi`, `pyglm`, `create_robot`, `create_msgs`, `rclpy`, `geometry_msgs`, `diagnostic_msgs`, `std_msgs`, `pytest`, `launch_testing` (003-joycon-manual-drive)
- N/A（ランタイム状態のみ、検証時は rosbag2 任意） (003-joycon-manual-drive)

- Python 3.13+, ROS2 Jazzy (rclpy) + `create_robot`, `rclpy`, `geometry_msgs`, `sensor_msgs`, `std_msgs`, `diagnostic_msgs`, `pytest`, `launch_testing` (002-random-cleaning-walk)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.13+, ROS2 Jazzy (rclpy): Follow standard conventions

## Recent Changes
- 003-joycon-manual-drive: Added Python 3.13+, ROS2 Jazzy (`rclpy`) + `joycon-python`, `hidapi`, `pyglm`, `create_robot`, `create_msgs`, `rclpy`, `geometry_msgs`, `diagnostic_msgs`, `std_msgs`, `pytest`, `launch_testing`

- 002-random-cleaning-walk: Added Python 3.13+, ROS2 Jazzy (rclpy) + `create_robot`, `rclpy`, `geometry_msgs`, `sensor_msgs`, `std_msgs`, `diagnostic_msgs`, `pytest`, `launch_testing`

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
