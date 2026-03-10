# Tasks: Roomba577 マルチモード清掃システム

**Input**: Design documents from `/specs/001-roomba-cleaning-modes/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Not explicitly requested in the feature specification. Test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **ROS 2 multi-package workspace**: `src/` at repository root, one subdirectory per package
- **Custom messages**: `src/roomba_msgs/` (CMake package)
- **Python packages**: `src/<package_name>/<package_name>/` (ament_python)
- **Launch & config**: `src/roomba_bringup/launch/`, `src/roomba_bringup/config/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create ROS 2 workspace directory structure and initialize all 8 packages

- [X] T001 Create project directory structure for all 8 ROS 2 packages (roomba_msgs, roomba_driver, roomba_safety, roomba_mode_manager, joycon_teleop, obstacle_detector, roomba_navigation, roomba_bringup) per plan.md project structure in src/
- [X] T002 [P] Initialize roomba_msgs CMake package with package.xml and CMakeLists.txt for msg/srv/action generation in src/roomba_msgs/
- [X] T003 [P] Initialize all 7 Python ROS 2 packages (roomba_driver, roomba_safety, roomba_mode_manager, joycon_teleop, obstacle_detector, roomba_navigation, roomba_bringup) with package.xml, setup.py, setup.cfg, and __init__.py in src/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core message definitions, Roomba serial driver, and safety monitor that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Define custom message types (RoombaState, DrivingMode, Bumper, WheelDrop, ObstacleArray, Obstacle) per contracts/services-actions.md in src/roomba_msgs/msg/
- [X] T005 [P] Define custom service types (SetMode, GetState) per contracts/services-actions.md in src/roomba_msgs/srv/
- [X] T006 [P] Define custom action type (CoverageClean) per contracts/services-actions.md in src/roomba_msgs/action/
- [X] T007 Implement serial_interface.py wrapping create_robot for Roomba577 OI v2.0 at 115200 baud with oi_mode_workaround parameter in src/roomba_driver/roomba_driver/serial_interface.py
- [X] T008 Implement roomba_driver_node.py as lifecycle node: subscribe /cmd_vel (geometry_msgs/Twist), publish /roomba/state (10Hz), /odom (50Hz), /roomba/bumper (50Hz), /roomba/wheel_drop (50Hz), /roomba/battery (1Hz), /tf (50Hz), /diagnostics (1Hz) in src/roomba_driver/roomba_driver/roomba_driver_node.py
- [X] T009 Implement safety_monitor_node.py as lifecycle node: subscribe /roomba/state, /roomba/bumper, /roomba/wheel_drop; provide /roomba/emergency_stop service (std_srvs/Trigger); publish /emergency_stop (std_msgs/Bool), /diagnostics (1Hz); detect serial disconnect, wheel drop, and battery low in src/roomba_safety/roomba_safety/safety_monitor_node.py
- [X] T010 [P] Create roomba_params.yaml with serial port, baud rate (115200), oi_mode_workaround flag, topic publish rates, max speed limits (500mm/s general, 300mm/s manual) in src/roomba_bringup/config/roomba_params.yaml

**Checkpoint**: Foundation ready — Roomba serial communication, state monitoring, and safety infrastructure operational. User story implementation can now begin.

---

## Phase 3: User Story 1 — ランダム走行清掃 (Priority: P1) 🎯 MVP

**Goal**: Activate Roomba577's built-in random walk cleaning algorithm via OI, with state monitoring and safe stop capability

**Independent Test**: Connect Roomba577 via serial, launch random_cleaning.launch.py, verify Roomba starts random cleaning, monitor state via `ros2 topic echo /roomba/state`, and stop via `ros2 service call /roomba/emergency_stop std_srvs/srv/Trigger`

### Implementation for User Story 1

- [X] T011 [US1] Implement mode_manager_node.py as lifecycle node: DrivingMode state machine (IDLE, RANDOM states), /cmd_vel multiplexer subscribing /cmd_vel_random, publish /cmd_vel (50Hz) and /roomba/mode (on change), provide /roomba/set_mode (SetMode) and /roomba/get_state (GetState) services, publish /diagnostics (1Hz) in src/roomba_mode_manager/roomba_mode_manager/mode_manager_node.py
- [X] T012 [US1] Create random_cleaning.launch.py launching roomba_driver, mode_manager, safety_monitor with roomba_params.yaml configuration in src/roomba_bringup/launch/random_cleaning.launch.py

**Checkpoint**: User Story 1 complete — Roomba performs random walk cleaning with state monitoring and emergency stop. MVP deliverable.

---

## Phase 4: User Story 2 — Joy-Con マニュアル走行清掃 (Priority: P2)

**Goal**: Enable Joy-Con left stick control of Roomba577 for targeted manual cleaning with 300mm/s max speed and <200ms response time

**Independent Test**: Pair Joy-Con via Bluetooth, launch manual_cleaning.launch.py, verify left stick forward/back/rotate controls Roomba within 200ms, verify stick release stops movement

### Implementation for User Story 2

- [X] T013 [P] [US2] Implement joycon_teleop_node.py as lifecycle node: subscribe /joy (sensor_msgs/Joy) from joy_node, publish /cmd_vel_joy (geometry_msgs/Twist) at 50Hz, apply 300mm/s max linear speed limit and deadzone calibration, handle Joy-Con disconnect detection, publish /diagnostics (1Hz) in src/joycon_teleop/joycon_teleop/joycon_teleop_node.py
- [X] T014 [US2] Add MANUAL mode to mode_manager_node.py: extend DrivingMode state machine with MANUAL state, subscribe /cmd_vel_joy, forward to /cmd_vel when mode=MANUAL in src/roomba_mode_manager/roomba_mode_manager/mode_manager_node.py
- [X] T015 [US2] Create manual_cleaning.launch.py launching joy_node, joycon_teleop, roomba_driver, mode_manager, safety_monitor with roomba_params.yaml in src/roomba_bringup/launch/manual_cleaning.launch.py

**Checkpoint**: User Stories 1 AND 2 independently functional — random cleaning and Joy-Con manual cleaning both work.

---

## Phase 5: User Story 3 — 自律走行清掃・障害物回避付き (Priority: P3)

**Goal**: Enable AMCL-based autonomous boustrophedon (zigzag) cleaning with LiDAR and RealSense D435i obstacle detection/avoidance, wall contact permitted, coverage tracking

**Independent Test**: Connect LiDAR and camera, launch autonomous_cleaning.launch.py with pre-built map, verify Roomba follows boustrophedon pattern, avoids floor obstacles (cables, step edges), permits wall contact, and stops safely when AMCL covariance exceeds 0.5m²

### Implementation for User Story 3

- [X] T016 [P] [US3] Implement lidar_detector.py: subscribe /scan (sensor_msgs/LaserScan), detect floor obstacles (step edges, cables) compensating for ~15° downward YDLIDAR mount angle, return typed obstacle list with confidence scores in src/obstacle_detector/obstacle_detector/lidar_detector.py
- [X] T017 [P] [US3] Implement rgbd_detector.py: subscribe /camera/aligned_depth_to_color/image_raw and /camera/color/image_raw, apply RANSAC floor plane fitting, detect obstacles with depth deviation >2-5cm threshold, apply hole_filling_filter for glossy surfaces, return typed obstacle list in src/obstacle_detector/obstacle_detector/rgbd_detector.py
- [X] T018 [US3] Implement obstacle_detector_node.py as lifecycle node: instantiate lidar_detector and rgbd_detector, fuse detections, publish /obstacles (roomba_msgs/ObstacleArray) at 10Hz filtering confidence <0.3, exclude walls from obstacles, publish /diagnostics (1Hz) in src/obstacle_detector/obstacle_detector/obstacle_detector_node.py
- [X] T019 [P] [US3] Implement nav2_interface.py: Nav2 lifecycle management utilities, configure costmap2d with obstacle layer subscribing /obstacles topic, wall contact permissive configuration in src/roomba_navigation/roomba_navigation/nav2_interface.py
- [X] T020 [US3] Implement coverage_planner_node.py as lifecycle node: integrate opennav_coverage for boustrophedon path planning, provide /coverage_clean action server (CoverageClean) with goal/result/feedback, track coverage_grid for cleaned area ratio, publish /diagnostics (1Hz) in src/roomba_navigation/roomba_navigation/coverage_planner_node.py
- [X] T021 [US3] Add AUTONOMOUS mode to mode_manager_node.py: extend DrivingMode state machine, subscribe /cmd_vel_nav, forward to /cmd_vel when mode=AUTONOMOUS, start /coverage_clean action on mode entry and cancel on exit in src/roomba_mode_manager/roomba_mode_manager/mode_manager_node.py
- [X] T022 [US3] Add AMCL covariance monitoring to safety_monitor_node.py: subscribe /amcl_pose (geometry_msgs/PoseWithCovarianceStamped), trigger emergency stop when position covariance (xx + yy) > 0.5m², notify user of localization loss in src/roomba_safety/roomba_safety/safety_monitor_node.py
- [X] T023 [P] [US3] Create nav2_params.yaml (Nav2 controller, planner, AMCL, costmap with obstacle layer config) and sensor_params.yaml (YDLIDAR T-mini Plus scan params, RealSense D435i depth/color stream params) in src/roomba_bringup/config/
- [X] T024 [US3] Create autonomous_cleaning.launch.py launching Nav2, AMCL, map_server, ydlidar_driver, realsense_node, obstacle_detector, roomba_navigation, roomba_driver, mode_manager, safety_monitor with nav2_params.yaml, sensor_params.yaml, roomba_params.yaml in src/roomba_bringup/launch/autonomous_cleaning.launch.py

**Checkpoint**: User Stories 1, 2, AND 3 independently functional — random, manual, and autonomous cleaning all work with obstacle avoidance.

---

## Phase 6: User Story 4 — 走行モード切り替え (Priority: P4)

**Goal**: Enable safe runtime mode switching between RANDOM/MANUAL/AUTONOMOUS via Joy-Con buttons (primary) and ROS 2 CLI (auxiliary), with hardware pre-checks and ≤2s transition time

**Independent Test**: Launch full_system.launch.py, switch between modes via Joy-Con buttons and `ros2 service call /roomba/set_mode`, verify Roomba stops safely before each transition, verify transition rejects when required hardware is missing

### Implementation for User Story 4

- [X] T025 [US4] Add safe mode transition logic to mode_manager_node.py: send cmd_vel=0, verify Roomba stopped via /roomba/state, complete transition within 2s timeout, reject transition if stop fails in src/roomba_mode_manager/roomba_mode_manager/mode_manager_node.py
- [X] T026 [US4] Add hardware availability pre-checks to mode_manager_node.py: verify Joy-Con connected for MANUAL mode (/joy topic active), verify LiDAR (/scan) and camera (/camera/*) for AUTONOMOUS mode, return descriptive failure message via SetMode response in src/roomba_mode_manager/roomba_mode_manager/mode_manager_node.py
- [X] T027 [US4] Add Joy-Con button mapping for mode switching and emergency stop to joycon_teleop_node.py: map specific buttons to SetMode service calls (IDLE, RANDOM, MANUAL, AUTONOMOUS) and emergency_stop trigger in src/joycon_teleop/joycon_teleop/joycon_teleop_node.py
- [X] T028 [US4] Create full_system.launch.py launching all sensor drivers (ydlidar, realsense, joy_node), all processing nodes (joycon_teleop, obstacle_detector, roomba_navigation), core nodes (roomba_driver, mode_manager, safety_monitor) with all config files in src/roomba_bringup/launch/full_system.launch.py

**Checkpoint**: All 4 user stories complete — full multi-mode cleaning system with safe runtime switching.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Verify cross-cutting requirements and documentation

- [X] T029 [P] Verify all nodes publish /diagnostics at ≥1Hz (SC-008) and implement lifecycle node state transitions (configure/activate/deactivate/shutdown) consistently across all 7 packages
- [X] T030 Update README.md with project overview, architecture summary, hardware requirements, build instructions (colcon build), and usage guide referencing quickstart.md
- [X] T031 Run quickstart.md validation: verify all 4 launch files start correctly, all CLI service calls work (/roomba/set_mode, /roomba/emergency_stop, /roomba/get_state), and topic monitoring (/roomba/state, /roomba/mode, /diagnostics) returns expected data

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — **BLOCKS all user stories**
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2)
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2). Independent of US1 but builds on mode_manager created in US1
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2). Independent of US1/US2 but extends mode_manager
- **User Story 4 (Phase 6)**: Depends on **US1 + US2 + US3** (requires all modes to exist for switching)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ──── BLOCKS ALL ────┐
    │                                       │
    ▼                                       │
Phase 3 (US1: Random) ◄────────────────────┘
    │
    ▼
Phase 4 (US2: Manual)       ← extends mode_manager from US1
    │
    ▼
Phase 5 (US3: Autonomous)   ← extends mode_manager from US1/US2
    │
    ▼
Phase 6 (US4: Mode Switch)  ← requires ALL modes from US1+US2+US3
    │
    ▼
Phase 7 (Polish)
```

### Within Each User Story

- Models/message definitions before nodes that use them
- Core node implementation before launch files
- Node extensions (mode additions) before corresponding launch files
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1**:
- T002 + T003 (different package types, no dependencies)

**Phase 2**:
- T004 + T005 + T006 (different msg/srv/action directories, independent definitions)
- T010 (config file) parallel with T007–T009 (node implementations)

**Phase 4**:
- T013 (joycon_teleop — separate package) parallel with other non-mode_manager work

**Phase 5**:
- T016 + T017 (lidar_detector + rgbd_detector — different files, same package)
- T019 (nav2_interface — different package) parallel with T016–T018 (obstacle_detector)
- T023 (config files) parallel with T019–T022 (node implementations)

---

## Parallel Example: User Story 3

```text
# Step 1: Launch detector modules in parallel (different files):
Task T016: "Implement lidar_detector.py in src/obstacle_detector/obstacle_detector/lidar_detector.py"
Task T017: "Implement rgbd_detector.py in src/obstacle_detector/obstacle_detector/rgbd_detector.py"

# In parallel with detectors, work on navigation package (different package):
Task T019: "Implement nav2_interface.py in src/roomba_navigation/roomba_navigation/nav2_interface.py"

# Also in parallel, create config files (no code dependencies):
Task T023: "Create nav2_params.yaml and sensor_params.yaml in src/roomba_bringup/config/"

# Step 2: After T016+T017 complete, fuse them:
Task T018: "Implement obstacle_detector_node.py" (depends on T016, T017)

# Step 3: After T019 complete, build planner:
Task T020: "Implement coverage_planner_node.py" (depends on T019)

# Step 4: After T018+T020, extend mode_manager:
Task T021: "Add AUTONOMOUS mode to mode_manager_node.py"

# Step 5: Safety addition (can parallel with T021):
Task T022: "Add AMCL covariance monitoring to safety_monitor_node.py"

# Step 6: Launch file (after all above):
Task T024: "Create autonomous_cleaning.launch.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T010) — **CRITICAL, blocks all stories**
3. Complete Phase 3: User Story 1 (T011–T012)
4. **STOP and VALIDATE**: Launch `random_cleaning.launch.py`, verify Roomba cleans, monitor state, emergency stop
5. Deploy/demo if ready — this alone delivers cleaning value

### Incremental Delivery

1. Setup + Foundational → Roomba connected and safe
2. Add US1 (Random) → Test independently → **MVP!** (Roomba cleans autonomously)
3. Add US2 (Manual) → Test independently → Joy-Con control available
4. Add US3 (Autonomous) → Test independently → Intelligent obstacle-avoiding cleaning
5. Add US4 (Mode Switch) → Test independently → Seamless mode transitions
6. Polish → Production-quality system
7. Each story adds value without breaking previous stories

### Single Developer Strategy

Work sequentially: Phase 1 → 2 → 3 (validate MVP) → 4 → 5 → 6 → 7. Leverage [P] tasks within each phase to reduce context switching.

---

## Notes

- [P] tasks = different files/packages, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All nodes must be lifecycle nodes per Constitution Principle II
- All nodes must publish /diagnostics at ≥1Hz per SC-008
- Python 3.13+ with standard GIL mode (NOT free-threaded)
- create_robot rolling branch with `oi_mode_workaround: true` for Roomba577
