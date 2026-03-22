# Manual Drive

ROS2 Jazzy module for Joy-Con manual drive cleaning.

## Button Mapping (Left Joy-Con)

| Button | Action |
|--------|--------|
| ↑ (up) | Forward |
| ↓ (down) | Backward |
| ← (left) | Rotate left |
| → (right) | Rotate right |
| Minus / SR / SL (long-press 1s) | Toggle manual mode |
| ZL or L | Toggle cleaning |

## Interfaces

### Services

| Service | Type | Description |
|---------|------|-------------|
| `/manual_drive/estop` | `std_srvs/srv/Trigger` | Emergency stop |
| `/manual_drive/clear_estop` | `std_srvs/srv/Trigger` | Clear e-stop latch |

### Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Velocity commands |
| `/manual_drive/status` | `std_msgs/msg/String` | JSON operator status |
| `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | Node health |
| `/cliff` | `std_msgs/msg/Bool` | Cliff sensor subscription |

## Safety Assumptions

- Joy-Con link loss > 1s triggers fail-safe stop and mode exit
- Cliff sensor always honored in manual mode
- E-stop must be explicitly cleared; robot stays stopped until operator re-enters manual mode
- All cleaning disabled on mode exit

## Forbidden Zone Override

- Virtual walls and keep-out zones are bypassed while manual mode is active
- Restored immediately on mode exit
