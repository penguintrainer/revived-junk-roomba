# Random Cleaning Walk

ROS2 Jazzy module for Roomba-like random walk cleaning using the create_robot driver.

## Interfaces

### Services

| Service | Type | Description |
|---------|------|-------------|
| `/random_cleaning/start` | `std_srvs/srv/Trigger` | Start cleaning (idempotent) |
| `/random_cleaning/stop` | `std_srvs/srv/Trigger` | Stop cleaning |
| `/random_cleaning/estop` | `std_srvs/srv/Trigger` | Emergency stop (latched) |
| `/random_cleaning/resume_manual` | `std_srvs/srv/Trigger` | Resume after safety stop |
| `/random_cleaning/clear_estop` | `std_srvs/srv/Trigger` | Clear e-stop latch |

### Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Velocity commands |
| `/random_cleaning/state` | `std_msgs/msg/String` | Current mode string |
| `/random_cleaning/safety_event` | `std_msgs/msg/String` | Safety event payload |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | Node health |

## Safety Assumptions

- Sensor dropout > 1s triggers immediate safety stop and latches
- Low battery < 10% triggers 180s dock-return attempt then safety stop
- Wheel drop and cliff events trigger safety stop
- E-stop must be explicitly cleared before resuming

## Operating Limits

- Linear velocity: 150 mm/s (default)
- Angular velocity: 1.0 rad/s (default)
- Forward distance: 0.5 – 3.0 m
- Turn angle: 30° – 180°
- Battery start threshold: 20%
- Battery low threshold: 10%
