# Feature Specification: Roomba 577 ROS2 Cleaning & Navigation

**Feature Branch**: `001-roomba-cleaning-nav`  
**Created**: 2026-02-23  
**Status**: Draft  
**Input**: User description: "ROS2の複数のパッケージを実装。Roomba577を活用して、部屋の掃除を実施。Joy-Conによるマニュアル走行から、amclなどに基づく自動走行、掃除を実施。壁には衝突しても構わないが、段差やケーブルなどの障害物は回避。"

## Clarifications

### Session 2026-02-23
- Q: How is the "cleaning area" or "cleaning path" defined for autonomous mode? → A: Zig-zag pattern (systematic coverage)
- Q: How should the robot handle cable detection if Lidar misses them? → A: Motor Current Sensing (Reactive detection)
- Q: What is the behavior when the battery is low? → A: Return to Start (and stop there)
- Q: How should the system recover from safety stops (cliff/entanglement)? → A: Manual button press on Joy-Con to resume.
- Q: How should the operator toggle between Manual and Autonomous modes? → A: Single dedicated Joy-Con button.
- Q: How should the system communicate its current operating status? → A: Audio cues (beeps, tones) from the robot.
- Q: What are the primary sensor inputs for general obstacle detection and avoidance? → A: Lidar (2D) and 2D Camera with object detection.
- Q: How should the static map of the cleaning area be provided? → A: Manual upload of a static map file.
- Q: What is the exact ROS2 message type and coordinate frame for standard robot movement commands? → A: `geometry_msgs/msg/Twist` in `base_link` frame.
- Q: Please define the parameters for the zig-zag cleaning pattern? → A: Zig-zag with 75% overlap, maintaining 10cm distance from boundaries.
- Q: Please specify the criteria for recognizing cables via the 2D camera and the expected avoidance behavior. → A: Detection: Recognize objects matching "cable" visual patterns. Avoidance: Reroute around object.
- Q: Please describe the distinct audio cues for each specified status change. → A: Mode Switch: Short, single beep. Error: Repeating alarm. Low Battery: Slow, intermittent beep.
- Q: How should the 15% low battery threshold be explicitly defined? → A: Manufacturer's Spec: Refer to the Roomba 577 manufacturer's definition of 15% low battery.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manual Spot Cleaning (Priority: P1)

As an operator, I want to control the Roomba using a Joy-Con so that I can manually navigate to specific messy areas and clean them.

**Why this priority**: Manual control is the baseline safety and utility requirement. It ensures the robot can be recovered or used immediately without complex setup.

**Independent Test**: Can be fully tested by connecting a Joy-Con, launching the teleop node, and successfully driving the robot into a room to pick up debris.

**Acceptance Scenarios**:

1. **Given** the robot is powered on and Joy-Con is connected, **When** the operator moves the joystick, **Then** the Roomba moves in the corresponding direction.
2. **Given** the robot is moving manually, **When** a button mapped to "Clean" is pressed, **Then** the brushes/suction activate.

---

### User Story 2 - Map-based Autonomous Navigation (Priority: P2)

As a user, I want the robot to move autonomously to a designated room using a pre-loaded map so that I don't have to steer it manually.

**Why this priority**: Automation is the core value of a robotic cleaner. Localizing using amcl allows for repeatable and reliable coverage.

**Independent Test**: Load a map, set a 2D Navigation Goal in a visualization tool, and observe the robot planning and executing a path to the target.

**Acceptance Scenarios**:

1. **Given** a valid map and initial pose, **When** a goal is sent, **Then** the robot calculates a path and moves to the goal.
2. **Given** the robot is navigating autonomously, **When** it approaches a wall, **Then** it may touch the wall but continues its path without error.

---

### User Story 3 - Safe Obstacle Avoidance (Priority: P3)

As a user, I want the robot to avoid falling down stairs or getting tangled in cables while cleaning, even during autonomous operation.

**Why this priority**: Prevents hardware damage and mission failure. Essential for unattended operation.

**Independent Test**: Place the robot near a ledge or a tangled cable path and verify it stops or steers away instead of proceeding.

**Acceptance Scenarios**:

1. **Given** the robot is moving (manual or auto), **When** a cliff/step is detected by sensors, **Then** the robot immediately stops or reverses.
2. **Given** the robot is moving, **When** a cable or small obstacle is detected on the floor, **Then** the robot navigates around it.

### Edge Cases

- **Connectivity Loss**: What happens when the Joy-Con loses connection? (Expected: Robot should stop immediately).
- **Localization Failure**: How does the system handle `amcl` losing track of the robot's position? (Expected: Robot stops and requests manual re-localization or spins to find features).
- **Entanglement**: What if a cable is detected too late? (Expected: Brush motor current spikes; system stops cleaning motors and robot movement immediately).
- **Low Battery**: What happens when battery is critical? (Expected: System aborts cleaning and executes return-to-start navigation).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement a communication layer to interface with Roomba 577.
- **FR-002**: System MUST provide a teleoperation layer that maps Joy-Con inputs to `geometry_msgs/msg/Twist` commands in the `base_link` frame.
- **FR-003**: System MUST support `amcl` for 2D pose estimation within a static map.
- **FR-004**: System MUST implement a safety layer that treats cliff sensor triggers as lethal obstacles.
- **FR-005**: System MUST differentiate between "walls" (contact allowed) and "prohibited obstacles" (steps/cables) in its local path planning.
- **FR-006**: System MUST provide a cleaning control mechanism to toggle suction and main brushes.
- **FR-007**: System MUST allow switching between Manual and Autonomous modes via a single dedicated Joy-Con button.
- **FR-008**: System MUST implement a zig-zag pattern for systematic autonomous floor coverage with 75% overlap, maintaining 10cm distance from boundaries.
- **FR-009**: System MUST monitor brush motor current to detect and stop upon entanglement with small obstacles like cables.
- **FR-010**: System MUST return the robot to its starting position and power down when the battery level drops below a 15% threshold, as defined by the Roomba 577 manufacturer's specification.
- **FR-011**: System MUST require a specific Joy-Con button press to resume operation after a safety-triggered stop (e.g., cliff detection or entanglement).
- **FR-012**: System MUST provide distinct audio cues: a short, single beep for mode changes; a repeating alarm for error states; and a slow, intermittent beep for low battery.
- **FR-013**: System MUST utilize a 2D Lidar for mapping and general obstacle detection, and a 2D camera to recognize objects matching "cable" visual patterns for avoidance by rerouting around them.

## Assumptions & Constraints

- **A-001**: The environment has sufficient features for the localization algorithm (`amcl`) to work accurately.
- **A-002**: A pre-existing static map of the cleaning area is manually uploaded to the robot.
- **A-003**: The Joy-Con is connected to the host system via Bluetooth and is recognized by the operating system.
- **A-004**: Walls are physically sturdy enough to withstand light bumps from the robot's bumper.
- **A-005**: Obstacles (cables, steps, general clutter) are detectable by the robot's Lidar, camera (for cable patterns), bumpers, and cliff sensors.

### Key Entities *(include if feature involves data)*

- **RobotState**: Represents current pose (x, y, theta), battery level, and sensor status (bumpers, cliffs).
- **NavigationGoal**: A target pose on the map that the autonomous system attempts to reach.
- **CleaningMode**: State representing whether cleaning hardware (brushes/suction) is Active or Idle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero falls recorded when operating near steps/ledges over 10 test runs.
- **SC-002**: Robot reaches navigation goals within a 15cm radius and 5-degree heading accuracy.
- **SC-003**: Latency between Joy-Con input and robot movement is under 100ms.
- **SC-004**: Robot successfully navigates through a doorway with < 5cm clearance on each side.
- **SC-005**: 100% of wall bumps during navigation are handled gracefully without the navigation stack crashing or aborting.
