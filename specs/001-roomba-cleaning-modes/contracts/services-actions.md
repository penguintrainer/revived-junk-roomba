# ROS 2 Interface Contracts: Services & Actions

**Feature**: Roomba577 マルチモード清掃システム
**Date**: 2026-03-10

## Services

### /roomba/set_mode

**Package**: roomba_msgs
**Type**: roomba_msgs/srv/SetMode

```
# Request
uint8 mode
uint8 IDLE = 0
uint8 RANDOM = 1
uint8 MANUAL = 2
uint8 AUTONOMOUS = 3
---
# Response
bool success
string message       # 失敗理由（例: "Joy-Con not connected"）
uint8 previous_mode
```

**Provider**: mode_manager_node
**Consumers**: joycon_teleop_node (ボタン入力), CLI (ros2 service call)
**Preconditions**: 切り替え先の必要ハードウェアが接続済み
**Postconditions**: 現在のモードが安全停止 → 新モードに遷移

### /roomba/emergency_stop

**Package**: roomba_msgs
**Type**: std_srvs/srv/Trigger

```
# Request
---
# Response
bool success
string message
```

**Provider**: safety_monitor_node
**Consumers**: mode_manager_node, joycon_teleop_node (ボタン), CLI
**Postconditions**: cmd_vel = 0, モード → IDLE

### /roomba/get_state

**Package**: roomba_msgs
**Type**: roomba_msgs/srv/GetState

```
# Request
---
# Response
roomba_msgs/RoombaState state
roomba_msgs/DrivingMode mode
float64 cleaning_time_sec
float64 distance_traveled_m
```

**Provider**: mode_manager_node
**Consumers**: CLI (モニタリング)

## Actions

### /coverage_clean

**Package**: roomba_msgs
**Type**: roomba_msgs/action/CoverageClean

```
# Goal
nav_msgs/OccupancyGrid target_area  # 清掃対象エリア（空の場合は全エリア）
---
# Result
float64 coverage_ratio              # 達成カバレッジ率 (0.0-1.0)
float64 total_time_sec
float64 total_distance_m
string termination_reason            # "completed", "battery_low", "emergency_stop", "localization_lost"
---
# Feedback
float64 current_coverage_ratio
geometry_msgs/Pose current_pose
float64 elapsed_time_sec
```

**Provider**: coverage_planner_node
**Consumers**: mode_manager_node (自律走行モード時)
**Cancellation**: モード切り替え、緊急停止、バッテリー低下で cancel

## Custom Messages

### roomba_msgs/msg/RoombaState

```
std_msgs/Header header
float32 battery_charge_ratio     # 0.0–1.0
geometry_msgs/Twist velocity
bool bumper_left
bool bumper_right
bool wheel_drop_left
bool wheel_drop_right
bool serial_connected
uint8 oi_mode                    # 0=OFF, 1=PASSIVE, 2=SAFE, 3=FULL
```

### roomba_msgs/msg/DrivingMode

```
std_msgs/Header header
uint8 mode                       # 0=IDLE, 1=RANDOM, 2=MANUAL, 3=AUTONOMOUS
uint8 previous_mode
builtin_interfaces/Time transition_time
```

### roomba_msgs/msg/Bumper

```
std_msgs/Header header
bool left
bool right
bool light_left
bool light_front_left
bool light_center_left
bool light_center_right
bool light_front_right
bool light_right
```

### roomba_msgs/msg/WheelDrop

```
std_msgs/Header header
bool left
bool right
```

### roomba_msgs/msg/ObstacleArray

```
std_msgs/Header header
roomba_msgs/Obstacle[] obstacles
```

### roomba_msgs/msg/Obstacle

```
geometry_msgs/Point position
uint8 obstacle_type              # 0=STEP_EDGE, 1=CABLE, 2=FLOOR_OBJECT, 3=UNKNOWN
uint8 detection_source           # 0=LIDAR, 1=RGBD, 2=FUSED
float32 confidence               # 0.0–1.0
geometry_msgs/Vector3 bounding_size
```
