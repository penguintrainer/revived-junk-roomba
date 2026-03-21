# Autonomous Cleaning

ROS2 Jazzy autonomous floor cleaning using Nav2 navigation stack.

## Architecture

- `session_node.py` — Main orchestration node
- `session_state_machine.py` — Pure state transition functions
- `interruption_policy.py` — Pause/resume/stop semantics
- `estop_manager.py` — E-stop latch lifecycle
- `localization_supervisor.py` — Localization health monitoring
- `perception_fusion.py` — LiDAR/RGB/RGBD health fusion
- `nav2_adapter.py` — Nav2 action client wrapper
- `dock_adapter.py` — Dock-return management
- `status_publisher.py` — Status and diagnostics publication
- `result_builder.py` — Final result aggregation

## Interfaces

### Services

| Service | Type | Description |
|---------|------|-------------|
| `/autonomous_cleaning/start` | `std_srvs/srv/Trigger` | Start session |
| `/autonomous_cleaning/pause` | `std_srvs/srv/Trigger` | Pause session |
| `/autonomous_cleaning/resume` | `std_srvs/srv/Trigger` | Resume paused session |
| `/autonomous_cleaning/stop` | `std_srvs/srv/Trigger` | Stop session |
| `/autonomous_cleaning/estop` | `std_srvs/srv/Trigger` | Emergency stop |
| `/autonomous_cleaning/clear_estop` | `std_srvs/srv/Trigger` | Clear e-stop latch |
| `/autonomous_cleaning/get_status` | `std_srvs/srv/Trigger` | Get current status |

### Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Velocity commands |
| `/autonomous_cleaning/status` | `std_msgs/msg/String` | JSON session status |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | Node health |

## Safety Constraints

- Battery start threshold: 30%
- Battery low (dock-return) threshold: 20%
- E-stop response: ≤50ms
- Localization lost → motion prohibited
- E-stop clear requires: zero velocity + no active fault + perception not lost
