<!--
Sync Impact Report:
- Version change: 0.0.0 → 1.0.0
- List of modified principles:
  - Added I. ROS 2 & Python Compliance
  - Added II. State Observability
  - Added III. Low-Latency Execution
  - Added IV. SOLID Design & AI-Human Synergy
- Added sections: Robot Control Constraints, AI-First Implementation
- Removed sections: Placeholder sections from template
- Templates requiring updates (✅ updated / ⚠️ pending):
  - .specify/templates/plan-template.md ✅
  - .specify/templates/spec-template.md ✅
  - .specify/templates/tasks-template.md ✅
- Follow-up TODOs: N/A
-->

# Revived Junk Roomba Constitution

## Core Principles

### I. ROS 2 & Python Compliance
All implementation MUST strictly follow ROS 2 coding standards and Python PEP 8 conventions. Every code change MUST pass `ament_lint` (cpplint, flake8, pep257) or equivalent Python linting tools. This ensures compatibility and professional standards across the robotics ecosystem.

### II. State Observability
Robot control software MUST maintain and expose its internal state at all times. This includes hardware status, sensor readings, and control loop health. Comprehensive logging and diagnostic interfaces (topics/services) are mandatory to ensure system transparency and debugging ease.

### III. Low-Latency Execution
The system MUST prioritize low-latency response for control loops. Non-blocking asynchronous patterns SHOULD be preferred for I/O, while ensuring the core control logic is optimized for deterministic performance. Blocking calls in the main robot control thread are strictly prohibited.

### IV. SOLID Design & AI-Human Synergy
Software MUST be architected following SOLID principles (Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, Dependency Inversion). While Gemini (AI) is the primary implementer, the codebase MUST remain clean, modular, and readable to support occasional human manual intervention and review.

## Robot Control Constraints
Security and safety are paramount. All robot motions MUST be accompanied by fail-safes and boundary checks. Software MUST handle asynchronous events gracefully (e.g., sensor disconnects or emergency stops) to prevent physical harm or damage to the robot hardware.

## AI-First Implementation
Gemini acts as the primary developer for this project. The AI's workflow focuses on high-quality, test-driven implementation. Humans provide architectural guidance, high-level requirements, and periodic reviews. All AI-generated code MUST be verified against the core principles before merging.

## Governance
This Constitution is the foundation of all development activities. Amendments require a version bump (Semantic Versioning) and explicit ratification. Any implementation that violates these principles must be flagged as a "Constitution Violation" and justified in the implementation plan.

### Amendment Procedure
1. Any developer (AI or Human) can propose an amendment via a PR modifying this document.
2. Amendments MUST justify why existing principles are insufficient.
3. Ratification occurs when the PR is merged after human review.

### Compliance Review
- Every `plan.md` MUST include a "Constitution Check" against these four principles.
- Automated linting (ROS 2/Python) serves as the first gate for compliance.

**Version**: 1.0.0 | **Ratified**: 2026-02-23 | **Last Amended**: 2026-02-23
