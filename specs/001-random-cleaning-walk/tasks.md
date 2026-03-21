# Tasks: Roomba-like Random Walk Cleaning

**Input**: Design documents from `/specs/001-random-cleaning-walk/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/random-cleaning-interfaces.md

**Tests**: Constitution の品質ゲート（pytest 100% green）を満たすため、各フェーズにテストタスクを配置。ユニットテストは pytest、統合テストは launch_testing を使用する。

**Organization**: Tasks are grouped by user story so each increment can be implemented and validated in order.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Every task includes exact file path(s)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare package structure and project-level tooling for the random-cleaning feature.

- [ ] T001 Create random cleaning package scaffolding in src/roomba_cleaning_nav/random_cleaning/__init__.py and src/roomba_cleaning_nav/random_cleaning/adapters/__init__.py
- [ ] T002 Update runtime and developer dependencies for ROS2 random cleaning in pyproject.toml
- [ ] T003 Create feature package usage notes in src/roomba_cleaning_nav/random_cleaning/README.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared building blocks that all user stories depend on.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [ ] T004 Create shared feature configuration and thresholds in src/roomba_cleaning_nav/random_cleaning/config.py
- [ ] T005 [P] Create domain entities and enums in src/roomba_cleaning_nav/random_cleaning/models.py
- [ ] T006 [P] Implement Roomba577 serial control adapter with create_robot integration in src/roomba_cleaning_nav/random_cleaning/adapters/create_robot_adapter.py
- [ ] T007 [P] Implement base telemetry publisher utilities in src/roomba_cleaning_nav/random_cleaning/adapters/telemetry_publisher.py
- [ ] T008 [P] Implement JSON Lines persistence helpers for sessions and events in src/roomba_cleaning_nav/random_cleaning/persistence.py
- [ ] T009 Create common ROS2 node lifecycle skeleton and timer wiring in src/roomba_cleaning_nav/random_cleaning/node.py

**Checkpoint**: Foundation ready — random cleaning behavior can now be implemented.

---

## Phase 3: User Story 1 - ランダム走行清掃を開始・停止する (Priority: P1) 🎯 MVP

**Goal**: Start, run, stop, and e-stop a Roomba-like random cleaning session using ROS2 services and `cmd_vel` output.

**Independent Test**: Launch the node, call `/random_cleaning/start`, verify random forward/turn motion begins, then call `/random_cleaning/stop` and `/random_cleaning/estop` to confirm motion halts within one control cycle.

### Implementation for User Story 1

- [ ] T010 [P] [US1] Implement bounded random-walk motion decision generation in src/roomba_cleaning_nav/random_cleaning/motion_policy.py
- [ ] T011 [P] [US1] Implement session lifecycle and idempotent start-stop transitions in src/roomba_cleaning_nav/random_cleaning/state_machine.py
- [ ] T012 [US1] Wire `/random_cleaning/start`, `/random_cleaning/stop`, and `/random_cleaning/estop` services in src/roomba_cleaning_nav/random_cleaning/node.py
- [ ] T013 [US1] Publish forward and turn `cmd_vel` commands from the control loop in src/roomba_cleaning_nav/random_cleaning/node.py
- [ ] T014 [US1] Replace the placeholder executable with the random cleaning entrypoint in main.py

### Tests for User Story 1

- [ ] T027 [P] [US1] Write unit tests for motion decision generation in tests/unit/test_motion_policy.py
- [ ] T028 [P] [US1] Write unit tests for session lifecycle and state transitions in tests/unit/test_state_machine.py
- [ ] T029 [US1] Write integration test for node start/stop/estop services using launch_testing in tests/integration/test_random_cleaning_node.py

**Checkpoint**: User Story 1 delivers a usable MVP random cleaning mode.

---

## Phase 4: User Story 2 - 接触・危険を検知して安全に振る舞う (Priority: P2)

**Goal**: Enforce fail-safe behavior for sensor dropout, low battery, stuck detection, and manual resume after safety latching.

**Independent Test**: While random cleaning is active, inject sensor dropout, low-battery, and no-progress events and verify the node stops or recovers exactly per the clarified rules.

### Implementation for User Story 2

- [ ] T015 [P] [US2] Implement sensor freshness, battery watchdog, bump/cliff/wheel-drop event response rules, and cliff-triggered reverse-then-turn avoidance action (FR-005) in src/roomba_cleaning_nav/random_cleaning/safety_watchdog.py
- [ ] T016 [P] [US2] Extend state transitions for low-battery dock-return timeout (180s) and latched safety stop in src/roomba_cleaning_nav/random_cleaning/state_machine.py; dock-return command issuance via create_robot_adapter.py
- [ ] T017 [P] [US2] Add no-progress detection, single 180-degree escape behavior, and bump-triggered direction-change avoidance maneuver (FR-006) in src/roomba_cleaning_nav/random_cleaning/motion_policy.py
- [ ] T018 [US2] Integrate safety latch handling and `/random_cleaning/resume_manual` gating in src/roomba_cleaning_nav/random_cleaning/node.py
- [ ] T018a [US2] Implement `/random_cleaning/clear_estop` service handler with precondition checks (zero velocity, no active safety fault, sensor freshness restored) in src/roomba_cleaning_nav/random_cleaning/node.py
- [ ] T019 [US2] Connect immediate hardware stop semantics for safety events in src/roomba_cleaning_nav/random_cleaning/adapters/create_robot_adapter.py

### Tests for User Story 2

- [ ] T030 [P] [US2] Write unit tests for sensor watchdog and bump/cliff/wheel-drop handling in tests/unit/test_safety_watchdog.py
- [ ] T031 [US2] Write integration test for safety latch, dock-return timeout, and manual resume in tests/integration/test_random_cleaning_node.py
- [ ] T033 [P] [US2] Write unit tests for clear_estop precondition validation (zero velocity, no active fault, sensor freshness) in tests/unit/test_safety_watchdog.py

**Checkpoint**: User Story 2 adds operational safety without changing MVP behavior semantics.

---

## Phase 5: User Story 3 - 清掃実行状態を把握する (Priority: P3)

**Goal**: Publish runtime state, diagnostics, and persistent event records so operators can understand what the robot is doing and why.

**Independent Test**: Run a session through start, normal cleaning, safety stop, and manual resume paths and confirm state topics, diagnostics, and persisted event records update consistently.

### Implementation for User Story 3

- [ ] T020 [P] [US3] Publish `/random_cleaning/state` and `/random_cleaning/safety_event` payloads in src/roomba_cleaning_nav/random_cleaning/adapters/telemetry_publisher.py
- [ ] T021 [P] [US3] Persist cleaning sessions and safety events to JSON Lines logs in src/roomba_cleaning_nav/random_cleaning/persistence.py
- [ ] T022 [US3] Publish `/diagnostics` health summaries from the runtime node in src/roomba_cleaning_nav/random_cleaning/node.py
- [ ] T023 [US3] Record structured state-transition logs and telemetry update calls in src/roomba_cleaning_nav/random_cleaning/node.py

### Tests for User Story 3

- [ ] T032 [P] [US3] Write contract tests for published topic schemas in tests/contract/test_interfaces_contract.py
- [ ] T033a [P] [US3] Write unit tests for JSON Lines persistence helpers in tests/unit/test_persistence.py

**Checkpoint**: User Story 3 makes the feature observable and auditable in operation.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, operator documentation, and end-to-end validation.

- [ ] T024 [P] Document ROS2 interfaces, safety assumptions, and operating limits in src/roomba_cleaning_nav/random_cleaning/README.md
- [ ] T025 Update operator validation steps and command examples in specs/001-random-cleaning-walk/quickstart.md
- [ ] T025a Document SC-005 manual verification procedure (coverage ratio grid calculation and turn frequency log analysis) in specs/001-random-cleaning-walk/quickstart.md
- [ ] T026 Run the documentation alignment pass for interface semantics in specs/001-random-cleaning-walk/contracts/random-cleaning-interfaces.md

**Note**: 003 Phase 8 (T062-T068) にて本機能のソースおよび契約ファイルが Cross-Feature Migration の対象となる。詳細は specs/003-autonomous-cleaning/tasks.md Phase 8 を参照。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** — no dependencies
- **Phase 2: Foundational** — depends on Phase 1; blocks all user stories
- **Phase 3: User Story 1** — depends on Phase 2; establishes the MVP runtime path
- **Phase 4: User Story 2** — depends on Phase 3 because safety logic extends the active cleaning loop and shared state machine
- **Phase 5: User Story 3** — depends on Phases 3 and 4 because observability consumes runtime and safety state transitions
- **Phase 6: Polish** — depends on all completed stories

### User Story Dependency Graph

- **US1 (P1)** → **US2 (P2)** → **US3 (P3)**

### Within Each User Story

- Shared model/config work must already exist from Foundational
- Pure decision logic before node integration
- Service/control integration before documentation polish
- Complete the story checkpoint before moving to the next dependent story

---

## Parallel Opportunities

- **Phase 2**: T005, T006, T007, and T008 can run in parallel after T004
- **US1**: T010 and T011 can run in parallel before T012/T013
- **US1 Tests**: T027 and T028 can run in parallel after T010/T011
- **US2**: T015, T016, and T017 can run in parallel before T018
- **US2 Tests**: T030 can run in parallel with T031's prerequisites
- **US3**: T020 and T021 can run in parallel before T022/T023
- **US3 Tests**: T032 and T033a can run in parallel after T021
- **Polish**: T024 can run in parallel with T025 once implementation is complete

---

## Parallel Example: User Story 1

```text
T010 [US1] Implement bounded random-walk motion decision generation in src/roomba_cleaning_nav/random_cleaning/motion_policy.py
T011 [US1] Implement session lifecycle and idempotent start-stop transitions in src/roomba_cleaning_nav/random_cleaning/state_machine.py
```

## Parallel Example: User Story 2

```text
T015 [US2] Implement sensor freshness, battery watchdog, and bump/cliff/wheel-drop event response rules in src/roomba_cleaning_nav/random_cleaning/safety_watchdog.py
T016 [US2] Extend state transitions for low-battery dock-return timeout and latched safety stop in src/roomba_cleaning_nav/random_cleaning/state_machine.py
T017 [US2] Add no-progress detection and single 180-degree escape behavior in src/roomba_cleaning_nav/random_cleaning/motion_policy.py
```

## Parallel Example: User Story 3

```text
T020 [US3] Publish `/random_cleaning/state` and `/random_cleaning/safety_event` payloads in src/roomba_cleaning_nav/random_cleaning/adapters/telemetry_publisher.py
T021 [US3] Persist cleaning sessions and safety events to JSON Lines logs in src/roomba_cleaning_nav/random_cleaning/persistence.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate start/stop/e-stop behavior as the MVP
5. Demo or review before safety and observability extensions

### Incremental Delivery

1. Deliver MVP random cleaning loop (US1)
2. Add fail-safe runtime protection (US2)
3. Add runtime observability and persisted records (US3)
4. Finish with documentation and operator validation updates

### Suggested MVP Scope

- **MVP**: Phase 1 + Phase 2 + Phase 3 (through T014, plus T027-T029)

---

## Notes

- All tasks follow the required checklist format.
- `[P]` is only used when files differ and no incomplete prerequisite blocks the work.
- User stories are intentionally sequenced because this feature extends shared node/state-machine files across phases.
- `tasks.md` is immediately executable by an LLM without requiring more feature context.
