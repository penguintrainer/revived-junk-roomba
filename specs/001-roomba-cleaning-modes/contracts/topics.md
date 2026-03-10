# ROS 2 Interface Contracts: Topics

**Feature**: Roomba577 マルチモード清掃システム
**Date**: 2026-03-10

## Topic Map

### Core Control Topics

| Topic | Type | Publisher | Subscriber(s) | QoS | Rate |
|-------|------|-----------|----------------|-----|------|
| `/cmd_vel` | geometry_msgs/Twist | mode_manager | roomba_driver | RELIABLE, VOLATILE | 50Hz |
| `/cmd_vel_joy` | geometry_msgs/Twist | joycon_teleop | mode_manager | RELIABLE, VOLATILE | 50Hz |
| `/cmd_vel_nav` | geometry_msgs/Twist | nav2 | mode_manager | RELIABLE, VOLATILE | 20Hz |
| `/cmd_vel_random` | geometry_msgs/Twist | roomba_driver (internal) | mode_manager | RELIABLE, VOLATILE | 10Hz |

### Roomba State Topics

| Topic | Type | Publisher | Subscriber(s) | QoS | Rate |
|-------|------|-----------|----------------|-----|------|
| `/roomba/state` | roomba_msgs/RoombaState | roomba_driver | mode_manager, safety_monitor | RELIABLE, TRANSIENT_LOCAL | 10Hz |
| `/roomba/bumper` | roomba_msgs/Bumper | roomba_driver | safety_monitor | RELIABLE, VOLATILE | 50Hz |
| `/roomba/wheel_drop` | roomba_msgs/WheelDrop | roomba_driver | safety_monitor | RELIABLE, VOLATILE | 50Hz |
| `/roomba/battery` | sensor_msgs/BatteryState | roomba_driver | mode_manager | RELIABLE, TRANSIENT_LOCAL | 1Hz |

### Sensor Topics (External Packages)

| Topic | Type | Publisher | Subscriber(s) | QoS | Rate |
|-------|------|-----------|----------------|-----|------|
| `/scan` | sensor_msgs/LaserScan | ydlidar_driver | obstacle_detector, nav2 | BEST_EFFORT, VOLATILE | 10-35Hz |
| `/camera/aligned_depth_to_color/image_raw` | sensor_msgs/Image | realsense_node | obstacle_detector | BEST_EFFORT, VOLATILE | 30Hz |
| `/camera/color/image_raw` | sensor_msgs/Image | realsense_node | obstacle_detector | BEST_EFFORT, VOLATILE | 30Hz |
| `/joy` | sensor_msgs/Joy | joy_node | joycon_teleop | RELIABLE, VOLATILE | 50Hz |

### Navigation Topics

| Topic | Type | Publisher | Subscriber(s) | QoS | Rate |
|-------|------|-----------|----------------|-----|------|
| `/map` | nav_msgs/OccupancyGrid | map_server | nav2, coverage_planner | RELIABLE, TRANSIENT_LOCAL | Latched |
| `/odom` | nav_msgs/Odometry | roomba_driver | nav2 (AMCL) | RELIABLE, VOLATILE | 50Hz |
| `/amcl_pose` | geometry_msgs/PoseWithCovarianceStamped | amcl | safety_monitor, coverage_planner | RELIABLE, VOLATILE | 10Hz |
| `/tf` | tf2_msgs/TFMessage | roomba_driver, amcl | all nodes | RELIABLE, VOLATILE | 50Hz |

### Obstacle Detection Topics

| Topic | Type | Publisher | Subscriber(s) | QoS | Rate |
|-------|------|-----------|----------------|-----|------|
| `/obstacles` | roomba_msgs/ObstacleArray | obstacle_detector | nav2 (costmap layer) | RELIABLE, VOLATILE | 10Hz |
| `/obstacle_costmap` | nav2_msgs/Costmap | obstacle_detector | nav2 | RELIABLE, VOLATILE | 5Hz |

### Diagnostics & Monitoring

| Topic | Type | Publisher | Subscriber(s) | QoS | Rate |
|-------|------|-----------|----------------|-----|------|
| `/diagnostics` | diagnostic_msgs/DiagnosticArray | all nodes | diagnostic_aggregator | RELIABLE, VOLATILE | 1Hz+ |
| `/roomba/mode` | roomba_msgs/DrivingMode | mode_manager | — (monitoring) | RELIABLE, TRANSIENT_LOCAL | On change |

### Safety Topics

| Topic | Type | Publisher | Subscriber(s) | QoS | Rate |
|-------|------|-----------|----------------|-----|------|
| `/emergency_stop` | std_msgs/Bool | safety_monitor | mode_manager, roomba_driver | RELIABLE, VOLATILE | On event |

## Data Flow Summary

```
Joy-Con → /joy → joycon_teleop → /cmd_vel_joy ─┐
Random mode (OI) → /cmd_vel_random ─────────────┤
Nav2 → /cmd_vel_nav ────────────────────────────┘
                                                 ↓
                                          mode_manager
                                          (selects active source)
                                                 ↓
                                            /cmd_vel
                                                 ↓
                                          roomba_driver
                                          (serial → Roomba577)
                                                 ↓
                                      /roomba/state, /odom, /bumper, /wheel_drop
                                                 ↓
                                          safety_monitor
                                          (watchdog, emergency stop)
```
