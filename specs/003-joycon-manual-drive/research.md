# Research: Joy-Con Manual Drive Cleaning

## Decision 1: Joy-Con input is modeled as a dedicated input bridge with hold-state polling and edge-triggered events

- Decision: Use `joycon-python` with the Left Joy-Con and represent input as two layers: continuous hold-state polling for directional motion and edge-triggered events for cleaning toggle / mode toggle.
- Rationale: Directional motion needs deterministic "while-held" behavior, while cleaning toggle and 1-second mode long-press depend on edge timing. `joycon-python` exposes left-button state and button-event helpers, which fits this split cleanly.
- Alternatives considered: Pure polling only (harder to detect long-press and toggle edges reliably), pure event-only handling (awkward for continuous velocity output), custom HID parser (unnecessary complexity).

## Decision 2: Manual mode bypasses Nav2 and publishes directly to Roomba driver interfaces

- Decision: The manual-drive controller publishes directly to `cmd_vel` for motion and to `side_brush_motor`, `main_brush_motor`, and `vacuum_motor` for cleaning actuation.
- Rationale: The feature explicitly ignores virtual walls and forbidden zones while in manual mode. Direct publication to the `create_robot` driver interfaces is the simplest way to satisfy that override while keeping `cmd_vel` as the canonical motion interface required by the constitution.
- Alternatives considered: Routing manual commands through Nav2 (would reintroduce keep-out constraints), directly talking to serial hardware outside `create_robot` (violates dependency choice and increases hardware coupling), sharing one generic teleop node with autonomous arbitration baked in (more coupling, less testability).

## Decision 3: Safety behavior uses a latched fail-safe on link loss and hardware cliff enforcement

- Decision: Joy-Con link loss over 1 second triggers immediate zero-velocity output, cleaning motor shutdown, manual-mode exit, and a latched stopped state. Reconnection does not restore motion until the operator explicitly long-presses the mode button again. Cliff sensor reports from `create_robot` remain hard stop conditions even in manual mode.
- Rationale: This matches the clarified requirements and keeps recovery behavior deterministic. Manual drive intentionally bypasses software keep-out zones, but not hardware drop protection.
- Alternatives considered: Auto-resume on reconnection (unsafe), resume-on-next-button-press (still ambiguous after radio instability), ignoring cliff while in manual mode (violates safety-first principle).

## Decision 4: Operator feedback uses a status topic as the source of truth and Joy-Con feedback as an adapter

- Decision: Publish operator-visible state on `/manual_drive/status` and `/diagnostics`; implement Joy-Con feedback through an adapter that attempts a short vibration pulse on supported hardware/library paths, while keeping the ROS2 status topic authoritative.
- Rationale: The spec requires both machine-readable state and operator feedback. `joycon-python` clearly supports button input and low-level output reports, but first-class rumble APIs are not exposed; isolating rumble in an adapter preserves the rest of the feature even if vibration support needs a no-op fallback on some environments.
- Alternatives considered: ROS2 topic only (does not satisfy clarified operator-feedback choice), console logging only (poor operator ergonomics), making rumble mandatory in core logic (would over-couple the controller to HID details).

## Decision 5: Testing centers on pure command-mapping logic plus ROS2 contract/integration coverage

- Decision: Use `pytest` for button-mapping, long-press timing, conflicting-input priority, and watchdog logic; use `launch_testing` for node wiring to `cmd_vel`, status topics, and create-driver motor topics; add a hardware-in-the-loop smoke test for Left Joy-Con pairing and Roomba serial control.
- Rationale: Most of the feature is deterministic logic that should be validated without real hardware. A small hardware smoke test covers the Joy-Con HID path and `create_robot` serial integration that cannot be fully simulated cheaply.
- Alternatives considered: Hardware-only validation (poor repeatability), simulation-first validation (does not exercise Joy-Con HID and Create Open Interface specifics), end-to-end tests with all dependencies mocked (would miss ROS interface regressions).

## Decision 6: Repository structure stays single-repo but uses feature-isolated ROS2 Python modules and explicit interface boundaries

- Decision: Implement the feature under `src/roomba_cleaning_nav/manual_drive/` with adapters for Joy-Con HID, create-driver output, and status publication, plus corresponding `tests/unit`, `tests/integration`, and `tests/contract` suites.
- Rationale: The current repository already uses a single Python source tree. Feature-isolated modules and ROS topic/service contracts preserve the constitution's separation goals without requiring a repository-wide packaging migration during this feature.
- Alternatives considered: Creating several new top-level ROS2 packages immediately (architecturally pure but high setup cost for the current repo state), placing all logic in one node file (violates SOLID and the 50-line rule).