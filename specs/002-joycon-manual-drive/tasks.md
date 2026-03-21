# Tasks: Joy-Con Manual Drive Cleaning

**Input**: Design documents from `/specs/003-joycon-manual-drive/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/manual-drive-interfaces.md

**Tests**: No standalone test-writing tasks are listed because the feature spec did not explicitly request TDD/test-first execution. Validation is captured through implementation-ready tasks plus quickstart walkthrough and final validation.

**Organization**: Tasks are grouped by user story so each increment can be implemented and validated in order.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Every task includes exact file path(s)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare package structure and project-level configuration for the manual-drive feature.

- [ ] T001 Create manual-drive package scaffolding in src/roomba_cleaning_nav/manual_drive/__init__.py and src/roomba_cleaning_nav/manual_drive/adapters/__init__.py
- [ ] T002 Update runtime and developer dependencies plus the manual-drive entrypoint in pyproject.toml
- [ ] T003 Create operator-facing feature notes in src/roomba_cleaning_nav/manual_drive/README.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared building blocks that MUST exist before any user story work starts.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [ ] T004 Create shared configuration constants and safety thresholds in src/roomba_cleaning_nav/manual_drive/config.py
- [ ] T005 [P] Create domain entities, enums, and state containers in src/roomba_cleaning_nav/manual_drive/models.py
- [ ] T006 [P] Implement the Left Joy-Con HID bridge skeleton in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
- [ ] T007 [P] Implement the `create_robot` output bridge skeleton in src/roomba_cleaning_nav/manual_drive/adapters/create_robot_adapter.py
- [ ] T008 [P] Implement operator feedback and ROS2 status publication scaffolding in src/roomba_cleaning_nav/manual_drive/adapters/feedback_adapter.py
- [ ] T009 [P] Implement status serialization helpers in src/roomba_cleaning_nav/manual_drive/status_formatter.py
- [ ] T010 Create the shared ROS2 node lifecycle, publishers, subscribers, and timer wiring in src/roomba_cleaning_nav/manual_drive/node.py

**Checkpoint**: Foundation ready — manual-drive stories can now be implemented.

---

## Phase 3: User Story 1 - Joy-Conで前進・後退・その場旋回を行う (Priority: P1) 🎯 MVP

**Goal**: Deliver directional Roomba motion from the Left Joy-Con d-pad while manual mode is active.

**Independent Test**: With the robot placed in manual mode, press each Left Joy-Con d-pad direction and confirm forward, backward, left rotation, right rotation, and stop-on-release behavior at the specified preset speeds.

### Implementation for User Story 1

- [ ] T011 [P] [US1] Implement directional mapping and conflicting-input resolution in src/roomba_cleaning_nav/manual_drive/command_mapper.py
- [ ] T012 [P] [US1] Implement held-button motion state capture for the Left Joy-Con d-pad in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
- [ ] T013 [US1] Integrate motion-command generation and 300 ms stop-on-release behavior in src/roomba_cleaning_nav/manual_drive/node.py
- [ ] T014 [US1] Publish clamped `cmd_vel` commands through the create-driver bridge in src/roomba_cleaning_nav/manual_drive/adapters/create_robot_adapter.py

**Checkpoint**: User Story 1 provides a usable manual locomotion MVP.

---

## Phase 4: User Story 2 - 手動モードの開始・終了とフェイルセーフを行う (Priority: P1)

**Goal**: Let the operator enter and exit manual mode with a 1-second long-press, publish authoritative mode state, and enforce safe behavior on link loss and reconnection.

**Independent Test**: Long-press the configured mode button to enter and exit manual mode, verify status publication and feedback occur on each transition, then simulate Joy-Con link loss and reconnection to confirm the robot stops and requires explicit re-entry.

### Implementation for User Story 2

- [ ] T015 [P] [US2] Implement 1-second mode-button hold tracking in src/roomba_cleaning_nav/manual_drive/long_press_tracker.py
- [ ] T016 [P] [US2] Extend Left Joy-Con event handling for mode-button long-press and link-health tracking in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
- [ ] T017 [P] [US2] Implement status and diagnostics payload generation for mode, link, and fault state in src/roomba_cleaning_nav/manual_drive/status_formatter.py
- [ ] T018 [P] [US2] Implement rumble-or-no-op feedback and `/manual_drive/status` publication in src/roomba_cleaning_nav/manual_drive/adapters/feedback_adapter.py
- [ ] T019 [US2] Integrate mode transitions, link-loss latching, reconnection hold state, and explicit re-entry rules in src/roomba_cleaning_nav/manual_drive/node.py

**Checkpoint**: User Story 2 makes manual-drive activation safe and operator-visible.

---

## Phase 5: User Story 3 - Joy-Conで清掃をオン・オフする (Priority: P2)

**Goal**: Allow the operator to toggle brush and vacuum cleaning independently of motion while keeping auto-disable-on-exit semantics.

**Independent Test**: While manual mode is active, press the cleaning-toggle button to enable and disable cleaning while stationary and while moving, then exit manual mode and verify all cleaning motors are turned off automatically.

### Implementation for User Story 3

- [ ] T020 [P] [US3] Define safe cleaning duty-cycle presets and cleaning-state transitions in src/roomba_cleaning_nav/manual_drive/config.py and src/roomba_cleaning_nav/manual_drive/models.py
- [ ] T021 [P] [US3] Implement side-brush, main-brush, and vacuum motor command publication in src/roomba_cleaning_nav/manual_drive/adapters/create_robot_adapter.py
- [ ] T022 [P] [US3] Implement Left Joy-Con cleaning-toggle edge detection in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
- [ ] T023 [US3] Integrate cleaning toggle, auto-disable-on-exit, and status updates in src/roomba_cleaning_nav/manual_drive/node.py

**Checkpoint**: User Story 3 adds manual cleaning control without breaking manual movement or mode safety.

---

## Phase 6: User Story 4 - 手動モード中は禁止領域を無視する (Priority: P3)

**Goal**: Ensure manual mode explicitly bypasses virtual walls and keep-out constraints, then restores them immediately when manual mode ends.

**Independent Test**: Define a virtual wall or keep-out region in the navigation stack, enter manual mode, drive across the restricted boundary successfully, then exit manual mode and verify the restriction is enforced again.

### Implementation for User Story 4

- [ ] T024 [P] [US4] Add forbidden-zone override state and restore semantics to src/roomba_cleaning_nav/manual_drive/models.py
- [ ] T025 [P] [US4] Extend operator status formatting with manual override and restore indicators in src/roomba_cleaning_nav/manual_drive/status_formatter.py
- [ ] T026 [US4] Integrate keep-out bypass activation and re-enforcement hooks in src/roomba_cleaning_nav/manual_drive/node.py
- [ ] T027 [US4] Document virtual-wall bypass expectations and downstream integration notes in src/roomba_cleaning_nav/manual_drive/README.md and specs/003-joycon-manual-drive/contracts/manual-drive-interfaces.md

**Checkpoint**: User Story 4 completes the manual override behavior for autonomous map restrictions.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, packaging, and operator validation updates across all stories.

- [ ] T028 [P] Document final button mapping, safety assumptions, and operating limits in src/roomba_cleaning_nav/manual_drive/README.md
- [ ] T029 Update operator walkthrough and validation commands in specs/003-joycon-manual-drive/quickstart.md
- [ ] T030 Align final interface semantics, fault behavior, and override notes in specs/003-joycon-manual-drive/contracts/manual-drive-interfaces.md
- [ ] T031 Validate dependency/install guidance and executable references in pyproject.toml and specs/003-joycon-manual-drive/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup** — no dependencies
- **Phase 2: Foundational** — depends on Phase 1; blocks all user stories
- **Phase 3: User Story 1** — depends on Phase 2; establishes the directional manual-drive MVP
- **Phase 4: User Story 2** — depends on Phase 3 because long-press mode entry, status publication, and fail-safe handling extend the active movement loop and shared node state
- **Phase 5: User Story 3** — depends on Phase 4 because cleaning toggle behavior relies on the finalized manual-mode lifecycle and status publication
- **Phase 6: User Story 4** — depends on Phase 4 because forbidden-zone bypass is gated by authoritative manual-mode state; it also integrates with the active command loop from Phase 3
- **Phase 7: Polish** — depends on all completed stories

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

- **Phase 2**: T005, T006, T007, T008, and T009 can run in parallel after T004
- **US1**: T011 and T012 can run in parallel before T013/T014
- **US2**: T015, T016, T017, and T018 can run in parallel before T019
- **US3**: T020, T021, and T022 can run in parallel before T023
- **US4**: T024 and T025 can run in parallel before T026/T027
- **Polish**: T028 can run in parallel with T029 and T030 once implementation is complete

---

## Parallel Example: User Story 1

```text
T011 [US1] Implement directional mapping and conflicting-input resolution in src/roomba_cleaning_nav/manual_drive/command_mapper.py
T012 [US1] Implement held-button motion state capture for the Left Joy-Con d-pad in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
```

## Parallel Example: User Story 2

```text
T015 [US2] Implement 1-second mode-button hold tracking in src/roomba_cleaning_nav/manual_drive/long_press_tracker.py
T017 [US2] Implement status and diagnostics payload generation for mode, link, and fault state in src/roomba_cleaning_nav/manual_drive/status_formatter.py
T018 [US2] Implement rumble-or-no-op feedback and `/manual_drive/status` publication in src/roomba_cleaning_nav/manual_drive/adapters/feedback_adapter.py
```

## Parallel Example: User Story 3

```text
T020 [US3] Define safe cleaning duty-cycle presets and cleaning-state transitions in src/roomba_cleaning_nav/manual_drive/config.py and src/roomba_cleaning_nav/manual_drive/models.py
T021 [US3] Implement side-brush, main-brush, and vacuum motor command publication in src/roomba_cleaning_nav/manual_drive/adapters/create_robot_adapter.py
T022 [US3] Implement Left Joy-Con cleaning-toggle edge detection in src/roomba_cleaning_nav/manual_drive/adapters/joycon_adapter.py
```

## Parallel Example: User Story 4

```text
T024 [US4] Add forbidden-zone override state and restore semantics to src/roomba_cleaning_nav/manual_drive/models.py
T025 [US4] Extend operator status formatting with manual override and restore indicators in src/roomba_cleaning_nav/manual_drive/status_formatter.py
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
2. Add safe mode entry/exit, operator status, and link-loss recovery rules (US2)
3. Add cleaning toggle behavior (US3)
4. Add forbidden-zone override semantics (US4)
5. Finish with documentation and quickstart validation

### Suggested MVP Scope

- **MVP**: Phase 1 + Phase 2 + Phase 3 (through T014)

---

## Notes

- All tasks follow the required checklist format.
- `[P]` is only used when files differ and no incomplete prerequisite blocks the work.
- No standalone test-authoring tasks were added because the feature spec did not explicitly request them.
- `tasks.md` is immediately executable by an LLM without requiring more feature context.
