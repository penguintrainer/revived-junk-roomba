# Tasks: Autonomous Cleaning

**Input**: Design documents from `/specs/003-autonomous-cleaning/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/autonomous-cleaning-interfaces.md, quickstart.md

**Tests**: Test-authoring tasks are included in Phase 8 to satisfy the constitution’s quality gate requirement that `pytest` must pass before merge.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label for story-phase tasks (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
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
- [ ] T011 [P] Define clear-estop Trigger service contract in specs/003-autonomous-cleaning/contracts/autonomous-cleaning-interfaces.md
- [ ] T012 Implement shared threshold constants (`start>=0.30`, `low<0.20`, `recovery=1x30s`, `estop<=50ms`, `diagnostics<=1s`) in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/config.py
- [ ] T013 [P] Implement core domain enums/dataclasses for session, coverage, localization, perception fusion, dock, diagnostics, and e-stop state in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/models.py
- [ ] T014 Implement ROS2 node bootstrap, publishers (`/autonomous_cleaning/*`, `/diagnostics`), and service/action server wiring in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py

**Checkpoint**: Foundation ready — user-story implementation can now begin.

---

## Phase 3: User Story 1 - 既知の部屋を自動で掃除する (Priority: P1) 🎯 MVP

**Goal**: Start autonomous full-floor cleaning on a known map and progress through reachable work units until coverage completion.

**Independent Test**: Start a cleaning session on a known map and verify transition to cleaning, work-unit execution through Nav2, and completion with coverage metrics.

### Implementation for User Story 1

- [ ] T015 [P] [US1] Implement reachable-floor target-mask builder from static map and exclusion layers in src/roomba_cleaning_coverage/roomba_cleaning_coverage/target_mask.py
- [ ] T016 [P] [US1] Implement coverage work-unit decomposition logic in src/roomba_cleaning_coverage/roomba_cleaning_coverage/work_unit_generator.py
- [ ] T017 [P] [US1] Implement coverage progress tracker for covered/remaining/blocked area metrics in src/roomba_cleaning_coverage/roomba_cleaning_coverage/coverage_tracker.py
- [ ] T018 [P] [US1] Implement obstacle evidence fusion from LiDAR/RGB/RGBD for avoidance decisions in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/perception_fusion.py
- [ ] T019 [US1] Implement completion policy and terminal-state helper for coverage-finished sessions in src/roomba_cleaning_coverage/roomba_cleaning_coverage/completion_policy.py
- [ ] T020 [US1] Implement Nav2 action client adapter for per-work-unit navigation execution in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/nav2_adapter.py
- [ ] T021 [US1] Implement session state machine baseline transitions for `idle->preparing->cleaning->completed` in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_state_machine.py
- [ ] T022 [US1] Integrate coverage planning, fused obstacle gating, and Nav2 execution loop in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py

**Checkpoint**: User Story 1 provides an autonomous-cleaning MVP.

---

## Phase 4: User Story 2 - 清掃を一時停止・再開・停止する (Priority: P1)

**Goal**: Provide deterministic operator controls for pause/resume/stop and emergency-stop behavior while preserving progress.

**Independent Test**: During an active session, call pause/resume/stop/estop/clear_estop endpoints and confirm latency bounds, state transitions, and resume constraints.

### Implementation for User Story 2

- [ ] T023 [P] [US2] Implement interruption policies for pause/resume/stop semantics in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/interruption_policy.py
- [ ] T024 [P] [US2] Implement e-stop latch manager with explicit clear semantics and reject reasons in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/estop_manager.py
- [ ] T025 [P] [US2] Implement operator status payload formatter for control phase and e-stop state in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/status_publisher.py
- [ ] T026 [US2] Add `pause` service handling and motion-halt behavior in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T027 [US2] Add `resume` service handling with remaining-work queue reconstruction and e-stop-clear prerequisite in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T028 [US2] Add `stop` service and action-cancel normalization to `operator_stop` end reason in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T029 [US2] Add `/autonomous_cleaning/estop` handling with `<=50ms` actuator stop enforcement in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T030 [US2] Add `/autonomous_cleaning/clear_estop` handling with precondition checks (zero velocity + no active safety fault) in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T031 [US2] Extend state machine transitions for `cleaning<->paused`, `any->safety_stopped (estop)`, and guarded resume in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_state_machine.py

**Checkpoint**: User Story 2 enables stable operator control and emergency-stop safety.

---

## Phase 5: User Story 3 - 中断が起きても残りの掃除を続ける (Priority: P2)

**Goal**: Continue cleaning reachable regions after local failures and safely terminate when bounded recovery is exhausted.

**Independent Test**: Block part of the map and induce localization degradation; verify one recovery attempt (30s max), skipped/blocked tracking, and continued cleaning where reachable.

### Implementation for User Story 3

- [ ] T032 [P] [US3] Implement localization-health supervisor with `healthy/degraded/lost` states in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/localization_supervisor.py
- [ ] T033 [P] [US3] Implement perception-fusion health supervisor and degraded/lost transitions in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/perception_fusion.py
- [ ] T034 [P] [US3] Implement work-unit retry and blocked-region marking rules in src/roomba_cleaning_coverage/roomba_cleaning_coverage/coverage_tracker.py
- [ ] T035 [P] [US3] Implement per-unit retry and skip strategy in Nav2 adapter in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/nav2_adapter.py
- [ ] T036 [US3] Integrate bounded recovery policy (`1 attempt`, `30s timeout`) into runtime orchestration in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T037 [US3] Extend state machine transitions for `cleaning->incomplete` with explicit interruption reasons in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_state_machine.py
- [ ] T038 [US3] Publish blocked/remaining updates and recovery events during partial completion in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/status_publisher.py

**Checkpoint**: User Story 3 delivers resilient partial-completion behavior.

---

## Phase 6: User Story 4 - 清掃結果を確認する (Priority: P3)

**Goal**: Make final and runtime cleaning outcomes observable with clear completion/interruption context, including low-battery and e-stop terminations.

**Independent Test**: Execute sessions ending in completed, safety_stopped, incomplete (low-battery dock failure, localization lost), and operator-stopped states; verify status/feedback/result consistency with FR-014 vocabulary and `end_reason` disambiguation.

### Implementation for User Story 4

- [ ] T039 [P] [US4] Implement dock-attempt adapter using `create_robot` battery and charging evidence in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/dock_adapter.py
- [ ] T040 [P] [US4] Add final-result aggregation helpers for action results and status snapshots in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/result_builder.py
- [ ] T041 [US4] Integrate low-battery transition (`<0.20`) to dock attempt and dock success/failure end-state handling in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T042 [US4] Integrate `get_status` service and terminal result publication fields in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/session_node.py
- [ ] T043 [US4] Publish required `/diagnostics` keys (`session_state`, `localization_health`, `battery_charge_ratio`, `dock_attempt_state`, `estop_latched`) in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/status_publisher.py

**Checkpoint**: User Story 4 provides operator-visible completion reporting and end-reason clarity.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final alignment across launch flow, docs, and acceptance validation.

- [ ] T044 [P] Add autonomous-cleaning launch composition for Nav2 dependencies, perception fusion, and runtime node in src/roomba_autonomous_cleaning/launch/autonomous_cleaning.launch.py
- [ ] T045 [P] Document interfaces, thresholds, diagnostics keys, and safety constraints in src/roomba_autonomous_cleaning/README.md and src/roomba_cleaning_coverage/README.md
- [ ] T046 Align quickstart verification steps with SC-009/SC-010 acceptance criteria in specs/003-autonomous-cleaning/quickstart.md
- [ ] T047 Align contract and data-model terminology with final implementation states in specs/003-autonomous-cleaning/contracts/autonomous-cleaning-interfaces.md and specs/003-autonomous-cleaning/data-model.md
- [ ] T048 [P] Ensure map artifact directory exists at src/roomba_cleaning_nav/maps/ with a placeholder README

---

## Phase 8: Test Authoring

**Purpose**: Author unit, integration, and contract tests to satisfy constitution quality gates (`pytest` must pass before merge).

- [ ] T049 [P] Write unit tests for session state machine transitions in tests/unit/test_session_state_machine.py
- [ ] T050 [P] Write unit tests for coverage tracker metrics and work-unit state changes in tests/unit/test_coverage_tracker.py
- [ ] T051 [P] Write unit tests for completion policy terminal-state decisions in tests/unit/test_completion_policy.py
- [ ] T052 [P] Write unit tests for interruption policy pause/resume/stop semantics in tests/unit/test_interruption_policy.py
- [ ] T053 [P] Write unit tests for threshold policy start/low-battery/recovery constants in tests/unit/test_threshold_policy.py
- [ ] T054 [P] Write contract tests for RunAutonomousCleaning action goal/feedback/result schema in tests/contract/test_autonomous_cleaning_action_contract.py
- [ ] T055 [P] Write contract tests for status topic and diagnostics required keys in tests/contract/test_status_contract.py
- [ ] T056 Write integration test for full session lifecycle (start→clean→complete) in tests/integration/test_autonomous_cleaning_session.py
- [ ] T057 Write integration test for localization supervisor degraded/lost transitions in tests/integration/test_localization_supervisor.py
- [ ] T058 Write integration test for low-battery dock transition and outcome in tests/integration/test_low_battery_docking.py
- [ ] T059 Write integration test for e-stop latency enforcement in tests/integration/test_estop_latency.py
- [ ] T060 Write integration test for clear-estop precondition checks in tests/integration/test_clear_estop_preconditions.py
- [ ] T061 Write integration test for /diagnostics publish rate and required keys in tests/integration/test_diagnostics_publish_rate.py

**Checkpoint**: All constitution quality gate tests authored and passing.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** — no dependencies
- **Phase 2: Foundational** — depends on Phase 1; blocks all user stories
- **Phase 3: US1 (MVP)** — depends on Phase 2
- **Phase 4: US2** — depends on Phase 3 (control and e-stop extend active cleaning loop)
- **Phase 5: US3** — depends on Phases 3-4 (recovery depends on established control and safety paths)
- **Phase 6: US4** — depends on Phases 3-5 (final reporting depends on runtime and interruption outcomes)
- **Phase 7: Polish** — depends on all user stories
- **Phase 8: Test Authoring** — depends on Phases 3-6 (tests exercise implemented modules)

### User Story Dependency Graph

- **US1 (P1)** -> **US2 (P1)** -> **US3 (P2)** -> **US4 (P3)**

### Within Each User Story

- Planning/model tasks before orchestration integration
- Adapter capabilities before terminal-state/result wiring
- Runtime integration before docs/contract harmonization

---

## Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel after T001
- **Phase 2**: T007-T011 and T013 can run in parallel after T006
- **US1**: T015, T016, T017, and T018 can run in parallel before T019-T022
- **US2**: T023, T024, and T025 can run in parallel before T026-T031
- **US3**: T032, T033, T034, and T035 can run in parallel before T036-T038
- **US4**: T039 and T040 can run in parallel before T041-T043
- **Polish**: T044, T045, and T048 can run in parallel before T046-T047

- **Test Authoring**: T049-T055 can run in parallel before T056-T061

---

## Parallel Example: User Story 1

```text
T015 [US1] Implement reachable-floor target-mask builder in src/roomba_cleaning_coverage/roomba_cleaning_coverage/target_mask.py
T016 [US1] Implement coverage work-unit decomposition in src/roomba_cleaning_coverage/roomba_cleaning_coverage/work_unit_generator.py
T017 [US1] Implement coverage progress tracker in src/roomba_cleaning_coverage/roomba_cleaning_coverage/coverage_tracker.py
T018 [US1] Implement LiDAR/RGB/RGBD obstacle fusion in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/perception_fusion.py
```

## Parallel Example: User Story 2

```text
T023 [US2] Implement interruption policies in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/interruption_policy.py
T024 [US2] Implement e-stop latch manager in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/estop_manager.py
T025 [US2] Implement control/e-stop status formatter in src/roomba_autonomous_cleaning/roomba_autonomous_cleaning/status_publisher.py
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
2. Add pause/resume/stop/estop/clear-estop control (US2)
3. Add bounded recovery and partial completion (US3)
4. Add dock and operator-facing final results (US4)
5. Finish with launch/docs/contract alignment (Polish)

### Suggested MVP Scope

- **MVP**: Phase 1 + Phase 2 + Phase 3 (through T022)

---

## Notes

- All tasks follow the required checklist format (`- [ ] Txxx ...`).
- `[P]` is assigned only to tasks that can run without file-level conflicts.
- Test-authoring tasks (Phase 8) are included to satisfy the constitution’s quality gate requirement that `pytest` must pass before merge.
- Tasks are immediately executable by an LLM with the current design artifacts.
