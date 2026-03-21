# Tasks: Autonomous Cleaning

**Input**: Design documents from `/specs/004-autonomous-cleaning/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/autonomous-cleaning-interfaces.md, quickstart.md

**Tests**: No standalone test-writing tasks are listed because the feature specification did not explicitly request TDD/test-first execution.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Every task includes exact file path(s)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare ROS2 package skeletons and build metadata for autonomous cleaning.

- [ ] T001 Create message package manifest and build config in src/roomba_cleaning_msgs/package.xml and src/roomba_cleaning_msgs/CMakeLists.txt
- [ ] T002 [P] Create coverage package manifest and Python packaging config in src/roomba_cleaning_coverage/package.xml and src/roomba_cleaning_coverage/setup.py
- [ ] T003 [P] Create orchestration package manifest and Python packaging config in src/roomba_autonomous_cleaning/package.xml and src/roomba_autonomous_cleaning/setup.py
- [ ] T004 Create package-level Python module scaffolding in src/roomba_cleaning_coverage/roomba_cleaning_coverage/__init__.py and src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/__init__.py
- [ ] T005 Update workspace dependency declarations for autonomous-cleaning packages in pyproject.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared contracts and runtime primitives required by all stories.

**⚠️ CRITICAL**: No user story implementation should begin until this phase is complete.

- [ ] T006 Define `RunAutonomousCleaning` action contract in src/roomba_cleaning_msgs/action/RunAutonomousCleaning.action
- [ ] T007 [P] Define `AutonomousCleaningStatus` message in src/roomba_cleaning_msgs/msg/AutonomousCleaningStatus.msg
- [ ] T008 [P] Define `CoverageProgress` message in src/roomba_cleaning_msgs/msg/CoverageProgress.msg
- [ ] T009 [P] Define `CleaningEvent` message in src/roomba_cleaning_msgs/msg/CleaningEvent.msg
- [ ] T010 [P] Define synchronous status query service in src/roomba_cleaning_msgs/srv/GetAutonomousCleaningStatus.srv
- [ ] T011 Implement shared threshold constants (`start>=0.30`, `low<0.20`, `recovery=1x30s`, `estop<=50ms`) in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/config.py
- [ ] T012 [P] Implement core domain enums/dataclasses for session, coverage, localization, dock, and e-stop state in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/models.py
- [ ] T013 Implement ROS2 node bootstrap, publishers (`/autonomous_cleaning/*`, `/diagnostics`), service/action servers (including `clear_estop`), and timer wiring in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py

**Checkpoint**: Foundation ready — user-story implementation can now begin.

---

## Phase 3: User Story 1 - 既知の部屋を自動で掃除する (Priority: P1) 🎯 MVP

**Goal**: Start autonomous full-floor cleaning on a known map and progress through reachable work units until coverage completion.

**Independent Test**: Start a cleaning session on a known map and verify transition to cleaning, work-unit execution through Nav2, and completion with coverage metrics.

### Implementation for User Story 1

- [ ] T014 [P] [US1] Implement reachable-floor target-mask builder from static map and exclusion layers in src/roomba_cleaning_coverage/roomba_cleaning_coverage/target_mask.py
- [ ] T015 [P] [US1] Implement coverage work-unit decomposition logic in src/roomba_cleaning_coverage/roomba_cleaning_coverage/work_unit_generator.py
- [ ] T016 [P] [US1] Implement coverage progress tracker for covered/remaining/blocked area metrics in src/roomba_cleaning_coverage/roomba_cleaning_coverage/coverage_tracker.py
- [ ] T017 [US1] Implement completion policy and terminal-state helper for coverage-finished sessions in src/roomba_cleaning_coverage/roomba_cleaning_coverage/completion_policy.py
- [ ] T018 [US1] Implement Nav2 action client adapter for per-work-unit navigation execution in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/nav2_adapter.py
- [ ] T043 [US1] Implement obstacle evidence fusion from LiDAR/RGB/RGBD for avoidance decisions in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/perception_fusion.py
- [ ] T019 [US1] Implement session state machine transitions for `idle->preparing->cleaning->completed` in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_state_machine.py
- [ ] T020 [US1] Integrate coverage planning and Nav2 execution loop into runtime orchestration in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py

**Checkpoint**: User Story 1 provides an autonomous-cleaning MVP.

---

## Phase 4: User Story 2 - 清掃を一時停止・再開・停止する (Priority: P1)

**Goal**: Provide deterministic operator controls for pause/resume/stop and emergency-stop behavior while preserving progress.

**Independent Test**: During an active session, call pause/resume/stop and estop endpoints and confirm latency bounds, state transitions, and resume constraints.

### Implementation for User Story 2

- [ ] T021 [P] [US2] Implement interruption policies for pause/resume/stop semantics in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/interruption_policy.py
- [ ] T022 [P] [US2] Implement e-stop latch manager with explicit clear semantics in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/estop_manager.py
- [ ] T023 [P] [US2] Implement operator status payload formatter for control phase and e-stop state in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/status_publisher.py
- [ ] T024 [US2] Add `pause` service handling and motion-halt behavior in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T025 [US2] Add `resume` service handling with remaining-work queue reconstruction and e-stop-clear prerequisite in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T026 [US2] Add `stop` service and action-cancel normalization to `operator_stop` end reason in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T027 [US2] Add `/autonomous_cleaning/estop` handling with `<=50ms` actuator stop enforcement in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T044 [US2] Add `/autonomous_cleaning/clear_estop` handling with precondition checks (zero velocity + no active safety fault) in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T028 [US2] Extend state machine transitions for `cleaning<->paused`, `any->safety_stopped (estop)`, and guarded resume in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_state_machine.py

**Checkpoint**: User Story 2 enables stable operator control and emergency-stop safety.

---

## Phase 5: User Story 3 - 中断が起きても残りの掃除を続ける (Priority: P2)

**Goal**: Continue cleaning reachable regions after local failures and safely terminate when bounded recovery is exhausted.

**Independent Test**: Block part of the map and induce localization degradation; verify one recovery attempt (30s max), skipped/blocked tracking, and continued cleaning where reachable.

### Implementation for User Story 3

- [ ] T029 [P] [US3] Implement localization-health supervisor with `healthy/degraded/lost` states in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/localization_supervisor.py
- [ ] T030 [P] [US3] Implement work-unit retry and blocked-region marking rules in src/roomba_cleaning_coverage/roomba_cleaning_coverage/coverage_tracker.py
- [ ] T031 [P] [US3] Implement per-unit retry and skip strategy in Nav2 adapter in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/nav2_adapter.py
- [ ] T032 [US3] Integrate bounded recovery policy (`1 attempt`, `30s timeout`) into runtime orchestration in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T033 [US3] Extend state machine transitions for `cleaning->incomplete` with explicit interruption reasons in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_state_machine.py
- [ ] T034 [US3] Publish blocked/remaining updates and recovery events during partial completion in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/status_publisher.py

**Checkpoint**: User Story 3 delivers resilient partial-completion behavior.

---

## Phase 6: User Story 4 - 清掃結果を確認する (Priority: P3)

**Goal**: Make final and runtime cleaning outcomes observable with clear completion/interruption context, including low-battery and e-stop terminations.

**Independent Test**: Execute sessions ending in completed, stopped, low-battery-docked, incomplete, and estop-stopped states; verify status/feedback/result consistency.

### Implementation for User Story 4

- [ ] T035 [P] [US4] Implement dock-attempt adapter using `create_robot` battery and charging evidence in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/dock_adapter.py
- [ ] T036 [P] [US4] Add final-result aggregation helpers for action results and status snapshots in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/result_builder.py
- [ ] T037 [US4] Integrate low-battery transition (`<0.20`) to dock attempt and dock success/failure end-state handling in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T038 [US4] Integrate `get_status` service and terminal result publication fields in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T045 [US4] Publish required `/diagnostics` keys (`session_state`, `localization_health`, `battery_charge_ratio`, `dock_attempt_state`, `estop_latched`) in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/status_publisher.py

**Checkpoint**: User Story 4 provides operator-visible completion reporting and end-reason clarity.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final alignment across launch flow, docs, and acceptance validation.

- [ ] T039 [P] Add autonomous-cleaning launch composition for Nav2 dependencies and runtime node in src/roomba_autonomous_cleaning/launch/autonomous_cleaning.launch.py
- [ ] T040 [P] Document interfaces, thresholds, and safety constraints in src/roomba_autonomous_cleaning/README.md and src/roomba_cleaning_coverage/README.md
- [ ] T041 Align quickstart verification steps with threshold and e-stop acceptance criteria in specs/004-autonomous-cleaning/quickstart.md
- [ ] T042 Align contract and data-model terminology with final implementation states in specs/004-autonomous-cleaning/contracts/autonomous-cleaning-interfaces.md and specs/004-autonomous-cleaning/data-model.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** — no dependencies
- **Phase 2: Foundational** — depends on Phase 1; blocks all user stories
- **Phase 3: US1 (MVP)** — depends on Phase 2
- **Phase 4: US2** — depends on Phase 3 (control and e-stop extend active cleaning loop)
- **Phase 5: US3** — depends on Phases 3-4 (recovery depends on established control and safety paths)
- **Phase 6: US4** — depends on Phases 3-5 (final reporting depends on runtime and interruption outcomes)
- **Phase 7: Polish** — depends on all target user stories being complete

### User Story Dependency Graph

- **US1 (P1)** -> **US2 (P1)** -> **US3 (P2)** -> **US4 (P3)**

### Within Each User Story

- Coverage/state logic before node orchestration
- Adapter capability before final state transitions
- Node integration before documentation alignment
- Complete story checkpoint before moving to next dependent story

---

## Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel after T001
- **Phase 2**: T007, T008, T009, T010, and T012 can run in parallel after T006/T011
- **US1**: T014, T015, and T016 can run in parallel before T017-T020
- **US2**: T021, T022, and T023 can run in parallel before T024-T028
- **US3**: T029, T030, and T031 can run in parallel before T032-T034
- **US4**: T035 and T036 can run in parallel before T037-T038
- **Polish**: T039 and T040 can run in parallel before T041-T042

---

## Parallel Example: User Story 2

```text
T021 [US2] Implement interruption policies in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/interruption_policy.py
T022 [US2] Implement e-stop latch manager in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/estop_manager.py
T023 [US2] Implement control/e-stop status formatter in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/status_publisher.py
```

## Parallel Example: User Story 3

```text
T029 [US3] Implement localization-health supervisor in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/localization_supervisor.py
T030 [US3] Implement blocked-region marking rules in src/roomba_cleaning_coverage/roomba_cleaning_coverage/coverage_tracker.py
T031 [US3] Implement retry/skip strategy in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/nav2_adapter.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate autonomous full-floor cleaning start/progress/complete path
5. Demo MVP before control and resilience extensions

### Incremental Delivery

1. Deliver autonomous cleaning base loop (US1)
2. Add pause/resume/stop and e-stop control (US2)
3. Add bounded recovery and partial completion (US3)
4. Add dock/final result reporting (US4)
5. Finish with launch/docs/contract alignment (Polish)

### Suggested MVP Scope

- **MVP**: Phase 1 + Phase 2 + Phase 3 (through T020)

---

## Notes

- All tasks follow the required checklist format (`- [ ] Txxx ...`).
- `[P]` is assigned only to tasks that can run without file-level conflicts.
- No standalone test-authoring tasks were included because test-first development was not explicitly requested in the feature specification.
- Tasks are immediately executable by an LLM with the current design artifacts.
