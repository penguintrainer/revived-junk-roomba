<!--
SYNC IMPACT REPORT
==================
Version change: (template / unversioned) -> 1.0.0

Added sections:
  - Core Principles (6 principles, all new)
  - Technology Stack & Hardware Constraints (new)
  - Development Workflow & Quality Gates (new)
  - Governance (new)

Modified principles: N/A (initial fill from blank template)
Removed sections: N/A (initial fill)

Templates requiring update:
  - .specify/templates/plan-template.md  checked Constitution Check section present; gates align with 6 principles
  - .specify/templates/spec-template.md  checked No constitution-breaking changes to mandatory sections required
  - .specify/templates/tasks-template.md checked Task categories reflect observability, safety, and package structure
  - .specify/templates/agent-file-template.md checked No agent-specific (CLAUDE-only) references found

Deferred TODOs:
  - None. All placeholders resolved.
-->

# revived-junk-roomba Constitution

## Core Principles

### I. ROS2 Package Composition

Every feature MUST be realized by composing multiple independent ROS2 packages,
each with a single clearly defined responsibility. Cross-package communication
MUST use standard ROS2 message/service/action interfaces (`std_msgs`, `geometry_msgs`,
`nav_msgs`, `sensor_msgs`, etc.). No package may reach into another package's
internal implementation; inter-package contracts are defined solely through topics,
services, and actions. `cmd_vel` MUST be the canonical velocity command interface
for all motion controllers.

**Rationale**: ROS2's composability is the project's primary architectural advantage.
Hard package boundaries keep components independently testable and replaceable as
hardware evolves.

### II. Real-Time State Awareness & Low Latency

The system MUST be able to report its full operational state (robot pose, sensor
status, current mode, active errors) at all times. All safety-critical control
loops (collision avoidance, velocity control) MUST maintain <=50 ms end-to-end
latency. State transitions MUST be logged via ROS2's logging infrastructure at
the appropriate severity level. No blocking I/O or unbounded computation is
permitted on the main executor thread.

**Rationale**: This is a physical robot operating in a real environment. Delayed
or unknown state is a safety hazard. Latency budgets protect people, hardware,
and the environment.

### III. SOLID Design for Agent-Driven Codebases

All source code MUST follow SOLID principles:

- **S** - Single Responsibility: one class/module, one reason to change.
- **O** - Open/Closed: extend via new classes or plugins; do not modify existing interfaces.
- **L** - Liskov Substitution: subtypes MUST be fully substitutable for their base types.
- **I** - Interface Segregation: expose only the methods a client actually needs.
- **D** - Dependency Inversion: depend on abstractions, not concrete implementations.

The primary implementor is a coding agent; human edits are exceptional events.
Code MUST be self-documenting (typed, docstrings on all public symbols) so that
any agent or developer can make a safe, scoped change without requiring deep
context of the full system.

**Rationale**: Agent-generated code that violates SOLID creates cascading breakage.
Strict SOLID adherence is the primary defense against unintended side effects
across iterative agent-driven development cycles.

### IV. Function Discipline - 50-Line Rule & Referential Transparency

Every function or method MUST be <=50 lines (excluding blank lines and comments).
Functions SHOULD be referentially transparent: given the same inputs, always
produce the same output with no observable side effects. Where side effects are
unavoidable (ROS2 publishers, hardware I/O), they MUST be isolated in clearly
named adapter functions at the system boundary. Business logic MUST NOT contain
direct I/O. Each function MUST have exactly one responsibility and MUST be
independently testable without mocking the entire ROS2 graph.

**Rationale**: Short, pure functions are the atomic unit of agent change. A 50-line
cap prevents functions from accumulating unrelated responsibilities over time.
Pure core logic enables fast, deterministic unit tests without a live robot.

### V. ROS2 & Python Coding Standards

All Python code MUST comply with PEP 8 (style) and PEP 257 (docstrings). Type
annotations MUST be present on all function signatures (built-in generics or
`typing`). Python version MUST be 3.13+ to leverage free-threaded execution.
ROS2 node naming, topic namespacing, parameter declaration, and lifecycle
management MUST follow official ROS2 Jazzy coding guidelines. Linting via `ruff`
and type checking via `mypy --strict` MUST pass before any merge. Library choices
MUST prefer established, high-performance packages (`numpy`, `OpenCV`, `scipy`)
over custom implementations for numerical and image processing tasks.

**Rationale**: Consistent style reduces cognitive overhead for both agent and
human reviewers. Strong typing surfaces contract violations before runtime on
a physical robot.

### VI. Safety-First Robot Operation

The robot MUST NOT collide with non-wall obstacles (cables, drop-offs, humans,
furniture) during any operation mode. Sensor data from LiDAR, RGB camera, and
RGBD camera MUST be actively fused for obstacle detection and avoidance during
all motion modes. An emergency stop (e-stop) command MUST be available at all
times and MUST halt all actuators within one control cycle (<=50 ms). The e-stop
MUST be tested as part of every release. Wall contact during autonomous navigation
is permissible; all other physical contact is a fault condition and MUST trigger
an immediate stop and a logged alert.

**Rationale**: Physical safety is non-negotiable. Hardware and humans co-exist in
the operational environment. A fault that damages hardware or injures a person
cannot be undone by a software patch.

## Technology Stack & Hardware Constraints

### Software Stack (mandatory versions)

| Component | Version | Notes |
|:--|:--|:--|
| Ubuntu | 24.04.4 LTS (Noble Numbat) | Host OS |
| ROS2 | Jazzy Jalisco | Primary middleware |
| Python | 3.13+ | GIL-free threading required |
| create_robot | latest | Serial control of Roomba 577 via Create Open Interface |
| YDLidar-SDK | latest | YDLIDAR T-mini Plus driver |
| Conduit | latest | iPhone XR as ROS2 sensor node |
| realsense-ros | latest (ROS2) | Intel RealSense D435i RGBD |
| ruff | latest | Python linter (enforced in CI) |
| mypy | latest, strict mode | Python type checker (enforced in CI) |
| pytest | latest | Unit & integration test runner |
| Nav2 | Jazzy-compatible | Autonomous navigation stack |

### Hardware Platform

| Hardware | Role |
|:--|:--|
| Nintendo Switch (Ubuntu 24.04) | On-robot compute node with GPU |
| Nintendo Joy-Con | Manual teleoperation input device |
| Roomba 577 (serial interface) | Differential-drive actuator platform |
| iPhone XR (via Conduit) | IMU and camera sensor node |
| YDLIDAR T-mini Plus | 2D LiDAR for SLAM and obstacle avoidance |
| Intel RealSense D435i | RGBD sensor (role to be defined per feature spec) |
| Livox Mid 360 | 3D LiDAR (role to be defined per feature spec) |

All hardware drivers MUST expose data via standard ROS2 topic/service interfaces.
Hardware-specific code MUST be isolated in dedicated packages with no leak of
driver internals into business-logic packages.

## Development Workflow & Quality Gates

### Workflow

1. Feature development MUST follow the speckit workflow in sequence:
   `/speckit.specify` -> `/speckit.clarify` -> `/speckit.plan` ->
   `/speckit.tasks` -> `/speckit.implement`.
2. Every spec MUST include acceptance scenarios covering normal operation,
   error conditions, and (for any feature involving motion) explicit e-stop behavior.
3. Implementation MUST be performed by a coding agent. Any human-authored code
   MUST include an inline comment explaining why agent-driven implementation
   was insufficient for that change.

### Quality Gates (all MUST pass before merge)

- `ruff check` passes with zero errors.
- `mypy --strict` passes with zero type errors.
- `pytest` passes with all unit and integration tests green.
- No function exceeds 50 lines.
- All new ROS2 topics, services, and actions are documented in the owning
  package's `README.md`.
- The `plan.md` Constitution Check section is explicitly verified against all
  six principles.

### Observability Requirements

- Every ROS2 node MUST publish a `/diagnostics` topic entry reporting its
  health status.
- All state transitions MUST be logged at `INFO` level or above.
- Fault conditions (e-stop triggered, sensor dropout, unexpected state transition)
  MUST be logged at `ERROR` level with sufficient context to diagnose the root cause.

## Governance

This constitution supersedes all other development guidelines. In case of conflict,
this document takes precedence over any README, inline comment, or agent instruction.

**Amendment procedure**:
1. Propose the amendment with rationale in a GitHub Issue or PR description.
2. Increment `CONSTITUTION_VERSION` per semantic versioning:
   - MAJOR - backward-incompatible removal or redefinition of an existing principle.
   - MINOR - new principle, section, or materially expanded guidance.
   - PATCH - clarification, wording fix, typo, or non-semantic refinement.
3. Update `LAST_AMENDED_DATE` to the amendment date (ISO 8601: YYYY-MM-DD).
4. Run the consistency propagation checklist against all templates and agent
   guidance files before merging.
5. Prepend a Sync Impact Report HTML comment to the updated constitution file.

**Compliance review**: Every `plan.md` MUST contain a Constitution Check section
that explicitly verifies all six principles before Phase 0 research begins.
All PRs that introduce new ROS2 nodes or Python modules MUST be reviewed against
this constitution. Any decision that appears to violate a principle MUST be
justified in the plan's Complexity Tracking section.

**Version**: 1.0.0 | **Ratified**: 2026-03-21 | **Last Amended**: 2026-03-21
