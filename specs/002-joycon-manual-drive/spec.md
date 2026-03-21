# Feature Specification: Joy-Con Manual Drive Cleaning

**Feature Branch**: `002-joycon-manual-drive`
**Created**: 2026-03-21
**Status**: Draft
**Input**: User description: "Joy-Conによるマニュアル走行での掃除をする機能。前進・後退・その場旋回、清掃の有無をボタン入力で実施。バーチャルウォルールなどの禁止領域についても、マニュアル走行時は無視する。"

## Clarifications

### Session 2026-03-21

- Q: Which Joy-Con controller will be used for manual drive? → A: Left Joy-Con — d-pad (↑=forward, ↓=backward, ←=rotate-left, →=rotate-right), ZL or L for cleaning toggle, minus/SR/SL for mode switch.
- Q: What linear and angular velocity preset values should the robot use during manual drive? → A: Linear 150 mm/s, Angular 1.0 rad/s.
- Q: How should the current operating mode and cleaning state be communicated back to the operator? → A: Publish status on a ROS2 topic and provide Joy-Con rumble feedback on mode changes and cleaning toggle events.
- Q: If Joy-Con communication is lost and then later restored, what should the system do? → A: Stay stopped and require explicit re-entry to manual mode.
- Q: How should manual mode entry and exit be triggered on the Joy-Con? → A: Use a long-press of 1 second on the mode button to toggle manual mode.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manual Movement via Joy-Con (Priority: P1)

An operator holds a Joy-Con controller and directly controls the Roomba's movement in real time. Pressing directional inputs causes the robot to move forward, backward, or rotate in place. Releasing the input causes the robot to stop. The robot responds immediately to button presses with no perceptible delay.

**Why this priority**: Core locomotion control is the foundation of the entire manual driving feature; without it, all other capabilities are meaningless.

**Independent Test**: Can be fully tested by pressing directional buttons on the Joy-Con and verifying the robot physically moves as intended, without any cleaning or mapping features enabled.

**Acceptance Scenarios**:

1. **Given** the robot is in manual drive mode, **When** the operator presses the forward button on the Joy-Con, **Then** the robot moves forward at the configured speed until the button is released.
2. **Given** the robot is in manual drive mode, **When** the operator presses the backward button, **Then** the robot moves in reverse until the button is released.
3. **Given** the robot is in manual drive mode, **When** the operator presses the rotate-left button, **Then** the robot rotates counter-clockwise in place until the button is released.
4. **Given** the robot is in manual drive mode, **When** the operator presses the rotate-right button, **Then** the robot rotates clockwise in place until the button is released.
5. **Given** the operator releases all directional buttons, **When** no input is active, **Then** the robot stops within 0.3 seconds.

---

### User Story 2 - Mode Entry and Exit (Priority: P1)

An operator can enter and exit manual drive mode using a dedicated button on the Joy-Con with a 1-second long-press. The current operating mode is clearly indicated through ROS2 status publication and Joy-Con rumble feedback so the operator knows whether the robot is under manual or autonomous control.

**Why this priority**: Safe and unambiguous mode switching prevents accidental autonomous behavior during manual operation and vice versa.

**Independent Test**: Can be tested by pressing the mode toggle button and verifying the robot enters/exits manual drive mode with a clear status indication.

**Acceptance Scenarios**:

1. **Given** the robot is idle or in autonomous mode, **When** the operator long-presses the manual drive mode button on the Joy-Con for 1 second, **Then** the robot enters manual drive mode and the current mode status is updated.
2. **Given** the robot is in manual drive mode, **When** the operator long-presses the same mode button for 1 second, **Then** the robot exits manual drive mode, any ongoing movement stops, and cleaning deactivates.
3. **Given** Joy-Con communication is lost while in manual drive mode, **When** no input is received for more than 1 second, **Then** the robot stops all movement and cleaning immediately (fail-safe).
4. **Given** the robot changes manual-drive mode or cleaning state, **When** the state transition is accepted by the system, **Then** the system publishes the new state on a ROS2 status topic and emits a short Joy-Con rumble pulse.
5. **Given** Joy-Con communication was lost and later restored, **When** the controller reconnects, **Then** the robot remains stopped and manual drive does not resume until the operator explicitly re-enters manual mode.

---

### User Story 3 - Cleaning Toggle via Joy-Con (Priority: P2)

An operator can toggle the Roomba's physical cleaning functions (brush, suction) on and off at will using a dedicated button on the Joy-Con, independently of movement. This allows selective cleaning — for example, driving without cleaning over furniture legs, then activating cleaning when reaching a dirty area.

**Why this priority**: Cleaning toggle is the key differentiator from basic teleoperation; it directly fulfills the "掃除をする" requirement.

**Independent Test**: Can be fully tested by toggling the cleaning button while the robot is stationary and verifying the Roomba's brush/suction activates and deactivates audibly and physically.

**Acceptance Scenarios**:

1. **Given** the robot is in manual drive mode with cleaning inactive, **When** the operator presses the cleaning toggle button, **Then** the Roomba's cleaning functions (brush and suction) activate.
2. **Given** the robot is in manual drive mode with cleaning active, **When** the operator presses the cleaning toggle button again, **Then** the Roomba's cleaning functions deactivate.
3. **Given** the cleaning state is active, **When** the robot is also moving, **Then** cleaning continues uninterrupted during movement.
4. **Given** manual drive mode is exited, **When** the mode transition occurs, **Then** cleaning is automatically deactivated as a safety measure.

---

### User Story 4 - Forbidden Zone Override in Manual Mode (Priority: P3)

When the operator explicitly activates manual drive mode, any virtual walls, keep-out zones, or forbidden areas defined in the map are ignored. The robot follows operator input unconditionally, allowing access to areas that autonomous modes prohibit (e.g., under furniture, doorways, wired areas).

**Why this priority**: Safety constraints for autonomy should not restrict deliberate human-controlled operation; this is an important usability and cleaning-completeness requirement.

**Independent Test**: Can be tested by defining a virtual wall on the map, entering manual drive mode, and commanding the robot to cross that boundary — the robot must proceed without stopping.

**Acceptance Scenarios**:

1. **Given** a virtual wall is defined on the current map, **When** the robot is in manual drive mode and the operator commands movement across it, **Then** the robot crosses the boundary without stopping or deflecting.
2. **Given** a keep-out zone is active for autonomous modes, **When** the robot is in manual drive mode, **Then** no spatial restriction is applied to movement commands.
3. **Given** the robot exits manual drive mode back to autonomous mode, **When** the mode transition occurs, **Then** all virtual walls and forbidden zones are re-enforced immediately.

---

### Edge Cases

- What happens when the Joy-Con battery dies mid-operation? → Robot must stop all movement and cleaning within 1 second (fail-safe on communication loss).
- What happens if multiple directional buttons are pressed simultaneously (e.g., forward + backward)? → The system applies a deterministic priority rule: stop takes precedence; conflicting linear inputs cancel each other; rotation takes precedence over linear movement.
- What happens when the robot's physical bumper sensor is triggered during manual drive? → The operator receives a status update, but movement continues as commanded — the operator has ultimate control over software-level avoidance.
- What happens if the Roomba serial connection is lost during manual drive? → Manual drive mode is exited safely and the operator is notified.
- What happens if the operator commands movement toward a physical drop-off (cliff)? → The Roomba's built-in hardware cliff sensors are honored even in manual mode; the robot stops moving in the hazardous direction.
- What happens if Joy-Con rumble feedback cannot be delivered? → The ROS2 status topic remains the authoritative feedback channel and operation continues without rumble.
- What happens if Joy-Con communication is restored after a fail-safe stop? → The robot remains stopped and outside manual drive mode until the operator explicitly re-enters manual mode.
- What happens if the operator taps the mode button briefly? → A short press shorter than 1 second does not change operating mode.
- What happens when the Roomba's battery reaches a critically low level during manual drive? → The system publishes a low-battery warning on the status topic. Manual drive continues at the operator's discretion. The Roomba's built-in hardware low-battery protection (automatic shutdown) is honored.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept directional movement commands (forward, backward, rotate-left, rotate-right) from the **Left Joy-Con** d-pad in real time (↑=forward, ↓=backward, ←=rotate-left, →=rotate-right).
- **FR-002**: The system MUST translate Left Joy-Con d-pad input into robot velocity commands at a fixed linear speed of **150 mm/s** (forward/backward) and angular speed of **1.0 rad/s** (rotation) while the button is held.
- **FR-003**: The system MUST stop all robot movement within 0.3 seconds when all directional inputs are released.
- **FR-004**: The system MUST provide a dedicated Left Joy-Con button (**minus**) that toggles manual drive mode only after a continuous 1-second long-press.
- **FR-005**: The system MUST publish the current operating mode (manual / autonomous / idle) and cleaning state as observable state on a ROS2 status topic.
- **FR-006**: The system MUST provide a dedicated Left Joy-Con button (**ZL**) to toggle the Roomba's cleaning functions (brush and suction) on and off.
- **FR-007**: The system MUST allow movement and cleaning state to be controlled independently.
- **FR-008**: The system MUST suppress all virtual wall, keep-out zone, and forbidden area constraints while manual drive mode is active.
- **FR-009**: The system MUST re-enforce all spatial constraints immediately upon exiting manual drive mode.
- **FR-010**: The system MUST automatically deactivate cleaning, stop movement, and exit manual drive mode if Joy-Con communication is lost for more than 1 second (fail-safe behavior).
- **FR-011**: The system MUST honor the Roomba's built-in hardware cliff sensors even during manual drive mode.
- **FR-012**: The system MUST apply the following deterministic priority rule when conflicting directional buttons are pressed simultaneously: (1) cliff/e-stop safety override cancels all motion, (2) forward + backward pressed simultaneously → linear velocity = 0 (cancel), (3) left + right pressed simultaneously → angular velocity = 0 (cancel), (4) directional + rotation pressed simultaneously → rotation takes precedence (linear velocity = 0), (5) single directional input → normal velocity output.
- **FR-013**: The system MUST automatically deactivate cleaning when manual drive mode is exited.
- **FR-014**: The system MUST emit a short Joy-Con rumble pulse whenever manual drive mode changes or cleaning is toggled successfully.
- **FR-015**: The system MUST continue operating safely if Joy-Con rumble feedback is unavailable; status publication remains authoritative.
- **FR-016**: The system MUST remain stopped after Joy-Con reconnection following a communication loss and MUST require explicit operator re-entry into manual drive mode before accepting movement or cleaning commands again.
- **FR-017**: The system MUST ignore mode-button presses shorter than 1 second.
- **FR-018**: The system MUST accept e-stop requests at all times and MUST stop all movement and cleaning actuators within 50 ms (one control cycle) of receiving the request.
- **FR-019**: The system MUST provide a `/manual_drive/clear_estop` interface and MUST allow e-stop clearance only when the robot is stopped (zero velocity) and no active safety fault exists. Note: manual drive mode uses only Roomba built-in sensors (bump, cliff, wheel-drop) per Constitution VI; external sensor freshness is not a precondition for e-stop clearance in this mode, unlike 001-random-cleaning-walk (FR-016) and 003-autonomous-cleaning (FR-024).
- **FR-020**: The system MUST poll Joy-Con input at a rate of 20 Hz or higher. This polling rate is a prerequisite for meeting the 300 ms response latency defined in SC-001.

### Key Entities

- **ManualDriveMode**: The active/inactive state of manual control; holds the current mode, active movement direction, and cleaning state.
- **JoyConInput**: The raw button state received from the **Left Joy-Con** controller at each polling cycle; relevant inputs are d-pad (4 directions), ZL (cleaning toggle), and minus (mode switch).
- **VelocityCommand**: The linear and angular velocity values sent to the robot's motion controller, derived from JoyConInput.
- **CleaningCommand**: The on/off command sent to the Roomba's brush and suction actuators.
- **OperatorStatus**: The published state containing the current operating mode, cleaning state, and relevant fault notifications for operators and other ROS2 nodes.
- **ForbiddenZonePolicy**: The collection of virtual walls and keep-out zones; bypassed while manual mode is active, enforced otherwise.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The robot responds to directional Left Joy-Con d-pad input within 300 milliseconds of button press and moves at the configured preset speed (linear 150 mm/s, angular 1.0 rad/s) under normal operating conditions.
- **SC-002**: The robot comes to a complete stop within 300 milliseconds of all directional inputs being released.
- **SC-003**: The robot stops all movement and cleaning, exits manual drive mode, and remains stopped within 1 second of Joy-Con communication loss (fail-safe).
- **SC-004**: The cleaning toggle reliably activates and deactivates the Roomba's physical cleaning functions 100% of the time under normal conditions.
- **SC-005**: All configured virtual walls and forbidden zones are fully bypassed in manual drive mode — the robot crosses defined boundaries when commanded.
- **SC-006**: Forbidden zones are re-enforced within 500 milliseconds of exiting manual drive mode.
- **SC-007**: quickstart.md に記載の操作手順に従い、初回オペレータが5分以内に前進・後退・左旋回・右旋回・清掃トグルの全5操作を正しく実行でき、各モード遷移後にステータストピックの値とJoy-Con rumbleフィードバックを正しく認識できることを手動検証チェックリストで確認する。
- **SC-008**: No unintended movement or cleaning activation occurs when the robot is not in manual drive mode due to stray Joy-Con input.
- **SC-009**: On every successful mode change or cleaning toggle, the new state is published on the ROS2 status topic and Joy-Con rumble feedback is triggered within 300 milliseconds under normal operating conditions.
- **SC-010**: After Joy-Con reconnection following a communication loss, the robot does not resume manual control until the operator explicitly re-enters manual mode.
- **SC-011**: Manual mode changes occur only after a continuous 1-second long-press of the configured mode button, and shorter presses do not change mode.

## Assumptions

- The **Left Joy-Con** controller is connected and paired to the system before manual drive mode is initiated.
- The Left Joy-Con button mapping is: d-pad ↑/↓/←/→ for movement, ZL for cleaning toggle, minus for mode entry/exit.
- The Left Joy-Con mode button uses a 1-second long-press to toggle entry and exit of manual drive mode; shorter presses are ignored.
- Movement speed is fixed at **linear 150 mm/s** and **angular 1.0 rad/s**; speed is not variable via Joy-Con input in this feature version.
- The Roomba 577's serial interface via `create_robot` exposes control over brush and suction independently of movement commands.
- Virtual walls are managed as software-defined zones within the navigation stack; no hardware IR virtual wall emitters are involved.
- The Roomba's built-in hardware safety mechanisms (cliff sensors, bumpers) continue to function at the firmware level regardless of software-issued movement commands.
- Communication loss is defined as no Joy-Con input message received for more than 1 second.
- After a communication-loss fail-safe, reconnecting the Joy-Con does not automatically restore manual drive mode.
- Battery management during manual drive is the operator's responsibility. The system provides a low-battery status notification when battery charge ratio falls below 15% but does not enforce automatic docking or stopping. The Roomba's built-in hardware low-battery shutdown is always active. The 15% threshold is advisory only and is configured as a ROS2 parameter (`manual_drive.low_battery_warn_ratio`, default 0.15).
- 禁止領域（virtual wall, keep-out zone）は、Nav2 の keepout フィルターレイヤーまたは ROS2 パラメータサーバー経由で提供される前提とする。003-autonomous-cleaning で定義される同一データソースを使用する。
- 003-autonomous-cleaning の Nav2 keepout 層が未構築の段階では、禁止領域のバイパス/復帰操作は NOP（no-operation）として安全に無視される。US4 のフル検証は 003 統合後に実施する。
- Joy-Con 入力のポーリングレートは 20Hz 以上とする。SC-001 の 300ms 応答要件はこのポーリング間隔を前提に成立する。
