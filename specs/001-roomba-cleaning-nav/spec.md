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
- **FR-002**: System MUST provide a teleoperation layer that maps Joy-Con inputs to standard robot movement commands.
- **FR-003**: System MUST support `amcl` for 2D pose estimation within a static map.
- **FR-004**: System MUST implement a safety layer that treats cliff sensor triggers as lethal obstacles.
- **FR-005**: System MUST differentiate between "walls" (contact allowed) and "prohibited obstacles" (steps/cables) in its local path planning.
- **FR-006**: System MUST provide a cleaning control mechanism to toggle suction and main brushes.
- **FR-007**: System MUST allow switching between Manual and Autonomous modes via a Joy-Con toggle.
- **FR-008**: System MUST implement a zig-zag pattern for systematic autonomous floor coverage.
- **FR-009**: System MUST monitor brush motor current to detect and stop upon entanglement with small obstacles like cables.
- **FR-010**: System MUST return the robot to its starting position and power down when the battery level drops below a 15% threshold.

## Assumptions & Constraints

- **A-001**: The environment has sufficient features for the localization algorithm (`amcl`) to work accurately.
- **A-002**: A pre-existing static map of the cleaning area is available.
- **A-003**: The Joy-Con is connected to the host system via Bluetooth and is recognized by the operating system.
- **A-004**: Walls are physically sturdy enough to withstand light bumps from the robot's bumper.
- **A-005**: Cables and steps are detectable by the robot's sensors (bumpers, cliff sensors, or lidar).

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
