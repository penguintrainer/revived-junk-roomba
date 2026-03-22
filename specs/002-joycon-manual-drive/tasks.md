# Tasks: Joy-Con Manual Drive Cleaning

**Input**: Design documents from `/specs/002-joycon-manual-drive/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/manual-drive-interfaces.md

**Tests**: Test tasks are included in Phase 8 to satisfy the constitution's quality gates (all `pytest` tests green before merge).

**Organization**: Tasks are grouped by user story so each increment can be implemented and validated in order.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Every task includes exact file path(s)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare package structure and project-level configuration for the manual-drive feature.

- [X] T001 Create manual-drive package scaffolding in src/roomba_cleaning_nav/manual_drive/__init__.py and src/roomba_cleaning_nav/manual_drive/adapters/__init__.py
- [X] T002 Update runtime and developer dependencies plus the manual-drive entrypoint in pyproject.toml
- [X] T003 Create operator-facing feature notes in src/roomba_cleaning_nav/manual_drive/README.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared building blocks that MUST exist before any user story work starts.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [X] T004 Create shared configuration constants and safety thresholds in src/roomba_cleaning_nav/manual_drive/config.py
- [X] T005 [P] Create domain entities, enums, and state containers in src/roomba_cleaning_nav/manual_drive/models.py
- [X] T006 [P] Implement the Left Joy-Con HID bridge skeleton in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
- [X] T007 [P] Implement the `create_robot` output bridge skeleton in src/roomba_cleaning_nav/manual_drive/adapters/create_robot_adapter.py
- [X] T008 [P] Implement operator feedback and ROS2 status publication scaffolding in src/roomba_cleaning_nav/manual_drive/adapters/feedback_adapter.py
- [X] T009 [P] Implement status serialization helpers in src/roomba_cleaning_nav/manual_drive/status_formatter.py
- [X] T010 [P] Implement pure safety decision logic (link-loss watchdog, cliff-stop evaluation, e-stop latch management) in src/roomba_cleaning_nav/manual_drive/safety_watchdog.py
- [X] T011 Create the shared ROS2 node lifecycle, publishers, subscribers, and timer wiring in src/roomba_cleaning_nav/manual_drive/node.py

**Checkpoint**: Foundation ready — manual-drive stories can now be implemented.

---

## Phase 3: User Story 1 - Joy-Conで前進・後退・その場旋回を行う (Priority: P1) 🎯 MVP

**Goal**: Deliver directional Roomba motion from the Left Joy-Con d-pad while manual mode is active.

**Independent Test**: With the robot placed in manual mode, press each Left Joy-Con d-pad direction and confirm forward, backward, left rotation, right rotation, and stop-on-release behavior at the specified preset speeds.

### Implementation for User Story 1

- [X] T012 [P] [US1] Implement directional mapping and conflicting-input resolution in src/roomba_cleaning_nav/manual_drive/command_mapper.py
- [X] T013 [P] [US1] Implement held-button motion state capture for the Left Joy-Con d-pad in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
- [X] T014 [US1] Integrate motion-command generation and 300 ms stop-on-release behavior in src/roomba_cleaning_nav/manual_drive/node.py
- [X] T015 [US1] Publish clamped `cmd_vel` commands through the create-driver bridge in src/roomba_cleaning_nav/manual_drive/adapters/create_robot_adapter.py

**Checkpoint**: User Story 1 provides a usable manual locomotion MVP.

---

## Phase 4: User Story 2 - 手動モードの開始・終了とフェイルセーフを行う (Priority: P1)

**Goal**: Let the operator enter and exit manual mode with a 1-second long-press, publish authoritative mode state, and enforce safe behavior on link loss, cliff detection, e-stop, serial fault, and reconnection.

**Independent Test**: Long-press the configured mode button to enter and exit manual mode, verify status publication and feedback occur on each transition, then simulate Joy-Con link loss and reconnection to confirm the robot stops and requires explicit re-entry.

### Implementation for User Story 2

- [X] T016 [P] [US2] Implement 1-second mode-button hold tracking in src/roomba_cleaning_nav/manual_drive/long_press_tracker.py
- [X] T017 [P] [US2] Extend Left Joy-Con event handling for mode-button long-press and link-health tracking in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
- [X] T018 [P] [US2] Implement status and diagnostics payload generation for mode, link, fault state, and low-battery warning indication in src/roomba_cleaning_nav/manual_drive/status_formatter.py
- [X] T019 [P] [US2] Implement rumble-or-no-op feedback and `/manual_drive/status` publication in src/roomba_cleaning_nav/manual_drive/adapters/feedback_adapter.py
- [X] T020 [US2] Integrate mode transitions, link-loss latching, reconnection hold state, and explicit re-entry rules in src/roomba_cleaning_nav/manual_drive/node.py
- [X] T021 [US2] Subscribe to `/cliff` topic and wire cliff-triggered safety-stop through safety_watchdog in src/roomba_cleaning_nav/manual_drive/node.py
- [X] T022 [US2] Implement `/manual_drive/estop` service handler (`std_srvs/srv/Trigger`) using safety_watchdog latch in src/roomba_cleaning_nav/manual_drive/node.py
- [X] T022a [US2] Implement `/manual_drive/clear_estop` service handler (`std_srvs/srv/Trigger`) with precondition checks (zero velocity, no active safety fault) in src/roomba_cleaning_nav/manual_drive/node.py
- [X] T023 [US2] Subscribe to `create_robot` `/diagnostics` topic for serial fault detection and fail-safe handling in src/roomba_cleaning_nav/manual_drive/node.py
- [X] T024 [US2] Wire `/diagnostics` DiagnosticArray publication with required keys (joycon_link_age_ms, manual_mode_active, cleaning_enabled, last_fault, rumble_available) in src/roomba_cleaning_nav/manual_drive/adapters/feedback_adapter.py

**Checkpoint**: User Story 2 makes manual-drive activation safe and operator-visible.

---

## Phase 5: User Story 3 - Joy-Conで清掃をオン・オフする (Priority: P2)

**Goal**: Allow the operator to toggle brush and vacuum cleaning independently of motion while keeping auto-disable-on-exit semantics.

**Independent Test**: While manual mode is active, press the cleaning-toggle button to enable and disable cleaning while stationary and while moving, then exit manual mode and verify all cleaning motors are turned off automatically.

### Implementation for User Story 3

- [X] T025 [P] [US3] Define safe cleaning duty-cycle presets and cleaning-state transitions in src/roomba_cleaning_nav/manual_drive/config.py and src/roomba_cleaning_nav/manual_drive/models.py
- [X] T026 [P] [US3] Implement side-brush, main-brush, and vacuum motor command publication in src/roomba_cleaning_nav/manual_drive/adapters/create_robot_adapter.py
- [X] T027 [P] [US3] Implement Left Joy-Con cleaning-toggle edge detection in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
- [X] T028 [US3] Integrate cleaning toggle, auto-disable-on-exit, and status updates in src/roomba_cleaning_nav/manual_drive/node.py

**Checkpoint**: User Story 3 adds manual cleaning control without breaking manual movement or mode safety.

---

## Phase 6: User Story 4 - 手動モード中は禁止領域を無視する (Priority: P3)

**Goal**: Ensure manual mode explicitly bypasses virtual walls and keep-out constraints, then restores them immediately when manual mode ends.

**Independent Test**: Define a virtual wall or keep-out region in the navigation stack, enter manual mode, drive across the restricted boundary successfully, then exit manual mode and verify the restriction is enforced again.

### Implementation for User Story 4

- [X] T029 [P] [US4] Add forbidden-zone override state and restore semantics to src/roomba_cleaning_nav/manual_drive/models.py
- [X] T030 [P] [US4] Extend operator status formatting with manual override and restore indicators in src/roomba_cleaning_nav/manual_drive/status_formatter.py
- [X] T031 [US4] Integrate keep-out bypass activation and re-enforcement hooks in src/roomba_cleaning_nav/manual_drive/node.py
- [X] T032 [US4] Document virtual-wall bypass expectations and downstream integration notes in src/roomba_cleaning_nav/manual_drive/README.md and specs/002-joycon-manual-drive/contracts/manual-drive-interfaces.md

**Checkpoint**: User Story 4 completes the manual override behavior for autonomous map restrictions.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, packaging, and operator validation updates across all stories.

- [X] T033 [P] Document final button mapping, safety assumptions, and operating limits in src/roomba_cleaning_nav/manual_drive/README.md
- [X] T034 Update operator walkthrough and validation commands in specs/002-joycon-manual-drive/quickstart.md
- [X] T035 Align final interface semantics, fault behavior, and override notes in specs/002-joycon-manual-drive/contracts/manual-drive-interfaces.md
- [X] T036 Validate dependency/install guidance and executable references in pyproject.toml and specs/002-joycon-manual-drive/quickstart.md

**Note**: 003 Phase 8 (T062-T068) にて本機能のソースおよび契約ファイルが Cross-Feature Migration の対象となる。詳細は specs/003-autonomous-cleaning/tasks.md Phase 8 を参照。

---

## Phase 8: Tests

**Purpose**: Validate pure logic, ROS2 contract compliance, and node integration per constitution quality gates (`pytest` passing, all tests green).

**⚠️**: Unit tests for each module should be written after the corresponding implementation phase is complete. Test tasks are grouped here for clarity; execution should follow the story that produces the code under test.

### Unit Tests

- [X] T037 [P] Implement unit tests for directional mapping and conflict resolution in tests/unit/test_command_mapper.py
- [X] T038 [P] Implement unit tests for 1-second long-press timing logic in tests/unit/test_long_press_tracker.py
- [X] T039 [P] Implement unit tests for link-loss watchdog, cliff-stop, and e-stop latch logic in tests/unit/test_safety_watchdog.py
- [X] T040 [P] Implement unit tests for status and diagnostics payload serialization in tests/unit/test_status_formatter.py

### Integration Tests

- [X] T041 Implement integration test for manual_drive_node wiring (cmd_vel, status, motor topics, estop service) in tests/integration/test_manual_drive_node.py
- [X] T041a Write integration test for create_robot driver bridge serial command sequences in tests/integration/test_driver_bridge.py

### Contract Tests

- [X] T042 Implement contract test verifying published topic types, field ranges, and service semantics against contracts/manual-drive-interfaces.md in tests/contract/test_manual_drive_interfaces.py

### Forbidden Zone Tests

- [X] T043 [P] [US4] Implement integration test for forbidden zone bypass activation on manual mode entry and re-enforcement on exit in tests/integration/test_forbidden_zone_override.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** — no dependencies
- **Phase 2: Foundational** — depends on Phase 1; blocks all user stories
- **Phase 3: User Story 1** — depends on Phase 2; establishes the directional manual-drive MVP
- **Phase 4: User Story 2** — depends on Phase 3 because long-press mode entry, status publication, fail-safe handling, cliff/estop/serial-fault safety, and diagnostics extend the active movement loop and shared node state
- **Phase 5: User Story 3** — depends on Phase 4 because cleaning toggle behavior relies on the finalized manual-mode lifecycle and status publication
- **Phase 6: User Story 4** — depends on Phase 4 because forbidden-zone bypass is gated by authoritative manual-mode state; it also integrates with the active command loop from Phase 3
- **Phase 7: Polish** — depends on all completed stories
- **Phase 8: Tests** — unit tests can begin after their corresponding implementation phase; integration and contract tests depend on Phase 7

### User Story Dependency Graph

- **US1 (P1)** → **US2 (P1)** → **US3 (P2)**
- **US2 (P1)** → **US4 (P3)**
- **US3 (P2)** and **US4 (P3)** both depend on the manual-mode lifecycle from **US2 (P1)**

### Within Each User Story

- Shared config, models, and adapter scaffolding must already exist from Foundational
- Pure logic before node integration
- Adapter-level capabilities before end-to-end node orchestration
- Complete the story checkpoint before moving to the next dependent story

---

## Parallel Opportunities

- **Phase 2**: T005, T006, T007, T008, T009, and T010 can run in parallel after T004
- **US1**: T012 and T013 can run in parallel before T014/T015
- **US2**: T016, T017, T018, and T019 can run in parallel before T020; T021–T023 are sequential on node.py after T020; T024 (feedback_adapter.py) can run in parallel with T020
- **US3**: T025, T026, and T027 can run in parallel before T028
- **US4**: T029 and T030 can run in parallel before T031/T032
- **Polish**: T033 can run in parallel with T034 and T035 once implementation is complete
- **Tests**: T037, T038, T039, and T040 can run in parallel; T041 depends on all unit tests; T042 depends on T041

---

## Parallel Example: User Story 1

```text
T012 [US1] Implement directional mapping and conflicting-input resolution in src/roomba_cleaning_nav/manual_drive/command_mapper.py
T013 [US1] Implement held-button motion state capture for the Left Joy-Con d-pad in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
```

## Parallel Example: User Story 2

```text
T016 [US2] Implement 1-second mode-button hold tracking in src/roomba_cleaning_nav/manual_drive/long_press_tracker.py
T018 [US2] Implement status and diagnostics payload generation for mode, link, and fault state in src/roomba_cleaning_nav/manual_drive/status_formatter.py
T019 [US2] Implement rumble-or-no-op feedback and `/manual_drive/status` publication in src/roomba_cleaning_nav/manual_drive/adapters/feedback_adapter.py
```

## Parallel Example: User Story 3

```text
T025 [US3] Define safe cleaning duty-cycle presets and cleaning-state transitions in src/roomba_cleaning_nav/manual_drive/config.py and src/roomba_cleaning_nav/manual_drive/models.py
T026 [US3] Implement side-brush, main-brush, and vacuum motor command publication in src/roomba_cleaning_nav/manual_drive/adapters/create_robot_adapter.py
T027 [US3] Implement Left Joy-Con cleaning-toggle edge detection in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
```

## Parallel Example: User Story 4

```text
T029 [US4] Add forbidden-zone override state and restore semantics to src/roomba_cleaning_nav/manual_drive/models.py
T030 [US4] Extend operator status formatting with manual override and restore indicators in src/roomba_cleaning_nav/manual_drive/status_formatter.py
```

## Parallel Example: Unit Tests

```text
T037 Implement unit tests for directional mapping and conflict resolution in tests/unit/test_command_mapper.py
T038 Implement unit tests for 1-second long-press timing logic in tests/unit/test_long_press_tracker.py
T039 Implement unit tests for link-loss watchdog, cliff-stop, and e-stop latch logic in tests/unit/test_safety_watchdog.py
T040 Implement unit tests for status and diagnostics payload serialization in tests/unit/test_status_formatter.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Verify directional movement and stop-on-release behavior in active manual mode
5. Demo the locomotion MVP before adding mode/fail-safe and cleaning behavior

### Incremental Delivery

1. Deliver directional manual movement (US1)
2. Add safe mode entry/exit, operator status, cliff/estop/serial-fault safety, diagnostics, and link-loss recovery rules (US2)
3. Add cleaning toggle behavior (US3)
4. Add forbidden-zone override semantics (US4)
5. Finish with documentation and quickstart validation
6. Write and validate all tests (Phase 8)

### Suggested MVP Scope

- **MVP**: Phase 1 + Phase 2 + Phase 3 (through T015)

---

## Notes

- All tasks follow the required checklist format.
- `[P]` is only used when files differ and no incomplete prerequisite blocks the work.
- Test tasks are grouped in Phase 8; unit tests for each module should execute after the story that produces the code under test.
- `tasks.md` is immediately executable by an LLM without requiring more feature context.
