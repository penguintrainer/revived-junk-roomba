# Data Model: Joy-Con Manual Drive Cleaning

## Entity: ManualDriveSession

- Purpose: Represents one explicit operator-controlled manual driving session.
- Fields:
  - session_id (string, UUID)
  - started_at (datetime)
  - ended_at (datetime, nullable)
  - entry_source (enum: joycon_long_press, recovery_reentry)
  - exit_reason (enum: operator_exit, link_loss, estop, serial_fault, cliff_stop, shutdown)
  - joycon_side (enum: left)
  - cleaning_enabled_on_entry (bool)
  - cleaning_enabled_on_exit (bool)
- Validation rules:
  - `ended_at >= started_at` when `ended_at` is present
  - `joycon_side` is always `left` for this feature version
  - `exit_reason=link_loss` implies session is not auto-resumed

## Entity: JoyConInputSnapshot

- Purpose: Captures the effective Left Joy-Con button state for one control tick.
- Fields:
  - captured_at (datetime)
  - up_pressed (bool)
  - down_pressed (bool)
  - left_pressed (bool)
  - right_pressed (bool)
  - cleaning_toggle_pressed (bool)
  - mode_button_pressed (bool)
  - link_healthy (bool)
  - source_latency_ms (int)
- Validation rules:
  - `source_latency_ms >= 0`
  - `link_healthy=false` implies movement command is zeroed before publication

## Entity: ManualDriveCommand

- Purpose: The resolved motion + cleaning command derived from Joy-Con input and safety state.
- Fields:
  - command_id (string, UUID)
  - created_at (datetime)
  - linear_velocity_mps (float)
  - angular_velocity_rps (float)
  - cleaning_enabled (bool)
  - mode_active (bool)
  - conflict_resolution (enum: none, cancel_linear, rotate_priority, safety_override)
  - publishable (bool)
- Validation rules:
  - `linear_velocity_mps` is one of `-0.15`, `0.0`, `0.15`
  - `angular_velocity_rps` is one of `-1.0`, `0.0`, `1.0`
  - `mode_active=false` implies both velocity fields are `0.0`
  - `publishable=false` implies command is for internal rejection/audit only

## Entity: CleaningMotorState

- Purpose: Tracks the requested actuation state for Roomba cleaning hardware.
- Fields:
  - enabled (bool)
  - side_brush_duty_cycle (int)
  - main_brush_duty_cycle (int)
  - vacuum_duty_cycle (int)
  - updated_at (datetime)
  - last_change_reason (enum: operator_toggle, session_exit, link_loss, estop, fault)
- Validation rules:
  - Duty-cycle fields are `0` when `enabled=false`
  - Duty-cycle fields are within the accepted `create_msgs/msg/MotorSetpoint` range chosen in implementation
  - `last_change_reason=operator_toggle` only occurs while `mode_active=true`

## Entity: OperatorStatus

- Purpose: The authoritative state published to the operator and peer ROS2 nodes.
- Fields:
  - mode (enum: idle, manual_active, safety_stopped, fault)
  - cleaning_enabled (bool)
  - link_state (enum: healthy, stale, lost, reconnected_waiting_reentry)
  - last_fault (enum: none, link_loss, cliff, serial_fault, estop, rumble_unavailable)
  - mode_button_hold_progress_ms (int)
  - updated_at (datetime)
- Validation rules:
  - `mode_button_hold_progress_ms >= 0`
  - `link_state=reconnected_waiting_reentry` implies `mode != manual_active`
  - `mode=safety_stopped` implies motion output is zero

## Entity: SafetyLatch

- Purpose: Represents a latched stop condition that blocks manual motion until explicit operator action.
- Fields:
  - latched (bool)
  - reason (enum: none, link_loss, cliff, estop, serial_fault)
  - triggered_at (datetime, nullable)
  - cleared_at (datetime, nullable)
  - requires_manual_reentry (bool)
- Validation rules:
  - `latched=true` implies `triggered_at` is present
  - `requires_manual_reentry=true` for `link_loss`, `cliff`, and `estop`
  - `cleared_at` cannot precede `triggered_at`

## State Transitions

- idle -> manual_active: Operator performs 1-second long-press on the configured mode button and no safety latch blocks entry.
- manual_active -> manual_active: Directional input changes, cleaning toggles, or status-only updates occur without mode exit.
- manual_active -> safety_stopped: Link loss, cliff detection, e-stop, or serial fault occurs.
- manual_active -> idle: Operator performs 1-second long-press to exit manual mode intentionally.
- safety_stopped -> idle: Safety condition is cleared; robot remains stopped and awaits explicit re-entry.
- idle -> fault / manual_active -> fault: Internal unrecoverable controller error occurs.

## Invariants

- Virtual walls and keep-out zones are ignored only while `mode=manual_active`; they are re-enforced immediately in all other modes.
- Movement commands are always zero whenever manual mode is inactive, the safety latch is active, or link health is not `healthy`.
- Reconnection after link loss never restores manual motion automatically.
- Cliff stop overrides operator motion intent even during manual mode.
- Cleaning is disabled automatically on every transition out of `manual_active`.