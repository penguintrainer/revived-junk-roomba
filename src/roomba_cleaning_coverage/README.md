# Roomba Cleaning Coverage

ROS2 Python package for coverage planning and progress tracking.

## Modules

- `target_mask.py` — Reachable floor target mask from occupancy grid
- `work_unit_generator.py` — Decompose mask into CoverageWorkUnit instances
- `coverage_tracker.py` — Work unit state transitions and area metrics
- `completion_policy.py` — Terminal state determination for sessions
