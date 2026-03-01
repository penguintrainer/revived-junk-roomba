# Tasks for Roomba 577 ROS2 Cleaning & Navigation

**Branch**: `001-roomba-cleaning-nav` | **Date**: 2026-02-23
**Feature Specification**: [specs/001-roomba-cleaning-nav/spec.md](specs/001-roomba-cleaning-nav/spec.md)
**Implementation Plan**: [specs/001-roomba-cleaning-nav/plan.md](specs/001-roomba-cleaning-nav/plan.md)

## Summary

This document outlines the development tasks for implementing the Roomba 577 ROS2 Cleaning & Navigation feature, organized by user stories and phases. The plan prioritizes foundational components, followed by core user functionalities, and concludes with polishing and cross-cutting concerns.

## Implementation Strategy

The implementation will follow an iterative approach, delivering each user story as an independently testable increment. Foundational components that block multiple user stories will be developed first.

## Phase 1: Setup

Initial setup of the ROS2 package structure and core configuration files.

- [X] T001 Create ROS2 package `roomba_cleaning_nav` in workspace src/roomba_cleaning_nav/
- [X] T002 Create `package.xml` for `roomba_cleaning_nav` src/roomba_cleaning_nav/package.xml
- [X] T003 Create `setup.py` for `roomba_cleaning_nav` src/roomba_cleaning_nav/setup.py
- [X] T004 Create `launch` directory src/roomba_cleaning_nav/launch/
- [X] T005 Create `config` directory src/roomba_cleaning_nav/config/
- [X] T006 Create `maps` directory src/roomba_cleaning_nav/maps/
- [X] T007 Create `tests` directory src/roomba_cleaning_nav/tests/
- [X] T008 Create `src` directory for Python nodes src/roomba_cleaning_nav/roomba_cleaning_nav/
- [X] T009 Create initial `roomba_launch.py` src/roomba_cleaning_nav/launch/roomba_launch.py
- [X] T010 Create initial `nav2_params.yaml` src/roomba_cleaning_nav/config/nav2_params.yaml
- [X] T011 Create initial `robot_params.yaml` src/roomba_cleaning_nav/config/robot_params.yaml
- [X] T012 Create empty `roomba_driver_node.py` src/roomba_cleaning_nav/roomba_cleaning_nav/roomba_driver_node.py
- [X] T013 Create empty `teleop_node.py` src/roomba_cleaning_nav/roomba_cleaning_nav/teleop_node.py
- [X] T014 Create empty `navigation_node.py` src/roomba_cleaning_nav/roomba_cleaning_nav/navigation_node.py
- [X] T015 Create empty `cleaning_node.py` src/roomba_cleaning_nav/roomba_cleaning_nav/cleaning_node.py
- [X] T016 Create empty `test_teleop.py` src/roomba_cleaning_nav/tests/test_teleop.py
- [X] T017 Create empty `test_navigation.py` src/roomba_cleaning_nav/tests/test_navigation.py
- [X] T018 Create empty `test_cleaning.py` src/roomba_cleaning_nav/tests/test_cleaning.py

## Phase 2: Foundational Components

Implementation of core, cross-cutting functionalities that serve all user stories.

- [ ] T019 Create custom ROS2 message/service/action definitions in a new `roomba_interfaces` package src/roomba_interfaces/
- [ ] T020 Implement `roomba_interfaces/msg/RobotStatus` src/roomba_interfaces/msg/RobotStatus.msg
- [ ] T021 Implement `roomba_interfaces/msg/AudioCue` src/roomba_interfaces/msg/AudioCue.msg
- [ ] T022 Implement `roomba_interfaces/srv/SetMode` src/roomba_interfaces/srv/SetMode.srv
- [ ] T023 Implement `std_srvs/srv/Trigger` for `/resume_operation` (no custom msg needed)
- [ ] T024 Implement `std_srvs/srv/SetBool` for `/toggle_cleaning` (no custom msg needed)
- [ ] T025 Implement `roomba_interfaces/action/CleanArea` src/roomba_interfaces/action/CleanArea.action
- [ ] T026 Update `package.xml` and `CMakeLists.txt` for `roomba_interfaces` package.
- [ ] T027 Implement basic `roomba_driver_node.py` using `create_robot` library to connect to Roomba 577 src/roomba_cleaning_nav/src/roomba_driver_node.py
- [ ] T028 Implement `odom` publisher in `roomba_driver_node.py` src/roomba_cleaning_nav/src/roomba_driver_node.py
- [ ] T029 Implement `cmd_vel` subscriber in `roomba_driver_node.py` to control Roomba motion src/roomba_cleaning_nav/src/roomba_driver_node.py
- [ ] T030 Implement cleaning mechanism control in `roomba_driver_node.py` via `/toggle_cleaning` service src/roomba_cleaning_nav/src/roomba_driver_node.py
- [ ] T031 Implement audio cue player in `roomba_driver_node.py` subscribing to `/audio_cues` src/roomba_cleaning_nav/src/roomba_driver_node.py

## Phase 3: User Story 1 - Manual Spot Cleaning (P1)

**Story Goal**: As an operator, I want to control the Roomba using a Joy-Con so that I can manually navigate to specific messy areas and clean them.

**Independent Test**: Connect a Joy-Con, launch the teleop node, and successfully drive the robot into a room to pick up debris, activating/deactivating cleaning.

- [ ] T032 [US1] Implement `teleop_node.py` to subscribe to `/joy_input` src/roomba_cleaning_nav/src/teleop_node.py
- [ ] T033 [US1] Map Joy-Con analog sticks to `cmd_vel` and publish to `/cmd_vel` topic src/roomba_cleaning_nav/src/teleop_node.py
- [ ] T034 [US1] Map a dedicated Joy-Con button to toggle cleaning via `/toggle_cleaning` service src/roomba_cleaning_nav/src/teleop_node.py
- [ ] T035 [US1] Map a dedicated Joy-Con button to resume operation after safety stop via `/resume_operation` service src/roomba_cleaning_nav/src/teleop_node.py
- [ ] T036 [US1] Implement `RobotStatus` subscriber in `teleop_node.py` to display current mode src/roomba_cleaning_nav/src/teleop_node.py
- [ ] T037 [US1] Create unit tests for Joy-Con mapping in `test_teleop.py` src/roomba_cleaning_nav/tests/test_teleop.py

## Phase 4: User Story 2 - Map-based Autonomous Navigation (P2)

**Story Goal**: As a user, I want the robot to move autonomously to a designated room using a pre-loaded map so that I don't have to steer it manually.

**Independent Test**: Load a map, set a 2D Navigation Goal in a visualization tool, and observe the robot planning and executing a path to the target.

- [ ] T038 [US2] Integrate Nav2 into `roomba_launch.py` src/roomba_cleaning_nav/launch/roomba_launch.py
- [ ] T039 [US2] Configure `nav2_params.yaml` for AMCL localization and path planning src/roomba_cleaning_nav/config/nav2_params.yaml
- [ ] T040 [US2] Implement `navigation_node.py` to manage Nav2 goal sending and status monitoring src/roomba_cleaning_nav/src/navigation_node.py
- [ ] T041 [US2] Implement `navigation_node.py` to handle `/navigate_to_pose` action goals src/roomba_cleaning_nav/src/navigation_node.py
- [ ] T042 [US2] Implement the zig-zag cleaning pattern in `cleaning_node.py` (or as part of `navigation_node.py` action) src/roomba_cleaning_nav/src/cleaning_node.py
- [ ] T043 [US2] Implement `/clean_area` action server in `cleaning_node.py` (or `navigation_node.py`) src/roomba_cleaning_nav/src/cleaning_node.py
- [ ] T044 [US2] Ensure Lidar data (`/scan`) is correctly published and used by Nav2 src/roomba_cleaning_nav/launch/roomba_launch.py
- [ ] T045 [US2] Create example `my_map.yaml` and `my_map.pgm` src/roomba_cleaning_nav/maps/
- [ ] T046 [US2] Update `roomba_launch.py` to load static map src/roomba_cleaning_nav/launch/roomba_launch.py
- [ ] T047 [US2] Create unit tests for navigation logic in `test_navigation.py` src/roomba_cleaning_nav/tests/test_navigation.py

## Phase 5: User Story 3 - Safe Obstacle Avoidance (P3)

**Story Goal**: As a user, I want the robot to avoid falling down stairs or getting tangled in cables while cleaning, even during autonomous operation.

**Independent Test**: Place the robot near a ledge or a tangled cable path and verify it stops or steers away instead of proceeding.

- [ ] T048 [US3] Implement cliff sensor integration in `roomba_driver_node.py` to publish status src/roomba_cleaning_nav/src/roomba_driver_node.py
- [ ] T049 [US3] Implement safety layer in `navigation_node.py` to process cliff sensor data and trigger safety stop src/roomba_cleaning_nav/src/navigation_node.py
- [ ] T050 [US3] Implement brush motor current monitoring in `roomba_driver_node.py` src/roomba_cleaning_nav/src/roomba_driver_node.py
- [ ] T051 [US3] Implement entanglement detection and safety stop in `navigation_node.py` based on motor current src/roomba_cleaning_nav/src/navigation_node.py
- [ ] T052 [US3] Implement 2D camera integration in `roomba_driver_node.py` to publish `/camera_image` src/roomba_cleaning_nav/src/roomba_driver_node.py
- [ ] T053 [US3] Implement basic object detection (e.g., for cables) using OpenCV in `navigation_node.py` processing `/camera_image` src/roomba_cleaning_nav/src/navigation_node.py
- [ ] T054 [US3] Implement obstacle avoidance behaviors in `navigation_node.py` based on Lidar, camera, and bumper data src/roomba_cleaning_nav/src/navigation_node.py
- [ ] T055 [US3] Implement low battery return-to-start logic in `navigation_node.py` (monitor battery, navigate to start, power down) src/roomba_cleaning_nav/src/navigation_node.py
- [ ] T056 [US3] Create unit tests for obstacle avoidance logic in `test_navigation.py` src/roomba_cleaning_nav/tests/test_navigation.py

## Phase 6: Polish & Cross-Cutting Concerns

Final integration, testing, and documentation to ensure a robust and user-friendly system.

- [ ] T057 Refine `robot_params.yaml` with all necessary robot-specific configurations src/roomba_cleaning_nav/config/robot_params.yaml
- [ ] T058 Implement `robot_status` publisher in `roomba_driver_node.py` to update system state src/roomba_cleaning_nav/src/roomba_driver_node.py
- [ ] T059 Integrate audio cues for all critical status changes (mode switch, error, low battery, safety stop) src/roomba_cleaning_nav/src/roomba_driver_node.py
- [ ] T060 Update `quickstart.md` with detailed instructions for running and testing the complete system specs/001-roomba-cleaning-nav/quickstart.md
- [ ] T061 Conduct system-level integration tests across all nodes and functionalities src/roomba_cleaning_nav/tests/
- [ ] T062 Review `README.md` for `roomba_cleaning_nav` package to ensure completeness src/roomba_cleaning_nav/README.md

## Dependencies

- Phase 1 (Setup) -> Phase 2 (Foundational Components)
- Phase 2 (Foundational Components) -> Phase 3 (US1)
- Phase 2 (Foundational Components) -> Phase 4 (US2)
- Phase 2 (Foundational Components) -> Phase 5 (US3)
- Phase 3 (US1) -> Phase 6 (Polish & Cross-Cutting Concerns)
- Phase 4 (US2) -> Phase 6 (Polish & Cross-Cutting Concerns)
- Phase 5 (US3) -> Phase 6 (Polish & Cross-Cutting Concerns)

## Parallel Execution Opportunities

- Tasks within Phase 1 (Setup) are highly parallelizable, as they involve creating distinct files and directories.
- Within User Story Phases, tasks related to different nodes or entirely separate functional aspects can be parallelized (e.g., implementing teleop node can run in parallel with initial navigation node setup, assuming foundational components are in place).

## Suggested MVP Scope

The Minimum Viable Product (MVP) for this feature is **User Story 1 - Manual Spot Cleaning**. This includes:
- Connecting to the Roomba 577.
- Joy-Con based manual control for navigation.
- Toggling cleaning mechanisms manually.
- Basic safety stop and resume functionality.
- Basic audio feedback for mode changes.

This MVP delivers core value by providing direct control and basic cleaning capabilities, and is an essential prerequisite for autonomous features.
