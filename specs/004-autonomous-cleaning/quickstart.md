# Quickstart: Autonomous Cleaning (Roomba577)

## 1) Prerequisites

- Ubuntu 24.04.4 LTS
- ROS2 Jazzy
- Python 3.13+
- Roomba577 connected over serial and supported by `create_robot`
- YDLIDAR T-mini Plus publishing 2D LiDAR scans
- iPhone XR connected through Conduit and publishing IMU data
- Nav2, `robot_localization`, `slam_toolbox`, and `map_server` installed
- A saved 2D occupancy map for the cleaning environment

## 2) Workspace Setup

1. Source ROS2 Jazzy.
2. Install runtime and development dependencies.
3. Build the workspace packages for messages, coverage, and autonomous cleaning.

Example:

- `source /opt/ros/jazzy/setup.bash`
- `pip install -U pytest ruff mypy`
- `rosdep install --from-paths src -i -y`
- `colcon build --packages-select roomba_cleaning_msgs roomba_cleaning_coverage roomba_autonomous_cleaning`
- `source install/setup.bash`

## 3) Prepare or Refresh the Map

1. Launch `create_robot`, YDLIDAR, Conduit IMU bridge, and `slam_toolbox` in mapping mode.
2. Drive the robot manually or with an existing safe mode to cover the room perimeter and open floor area.
3. Save the generated map under the repository map directory.

Expected artifact:

- `src/roomba_cleaning_nav/maps/home.yaml`
- matching occupancy image file (for example `home.pgm`)

## 4) Start Runtime Localization and Navigation

1. Launch the Roomba driver and confirm battery / diagnostics topics are available.
2. Launch the LiDAR and Conduit bridges.
3. Start `robot_localization` for fused local odometry.
4. Start `map_server`, `amcl`, and the Nav2 stack against the saved map.

Verify before cleaning:

- `map -> odom` is being published
- laser scans are fresh
- current pose is stable on the known map
- `/diagnostics` shows no blocking driver faults

## 5) Start the Autonomous Cleaning Node

- Launch the autonomous cleaning session node.
- Confirm the status topic reports `idle` or `preparing` before any cleaning request.

Example:

- `ros2 launch roomba_autonomous_cleaning autonomous_cleaning.launch.py map:=src/roomba_cleaning_nav/maps/home.yaml`
- `ros2 topic echo /autonomous_cleaning/status`
- `ros2 topic echo /autonomous_cleaning/coverage`

## 6) Run a Full-Floor Cleaning Session

1. Send the `RunAutonomousCleaning` action goal for `full_reachable_floor`.
2. Observe feedback for `session_state`, `covered_ratio`, `remaining_area_m2`, and current phase.
3. Confirm the robot progresses through reachable regions instead of repeating already covered space.

Expected behavior:

- session enters `cleaning` within 10 seconds of an accepted request
- coverage metrics update continuously during movement
- blocked regions are reported but do not immediately fail the entire session if other reachable regions remain

## 7) Pause, Resume, and Stop

- Use the pause service to halt movement and cleaning while preserving progress.
- Use the resume service only after localization health has returned to `healthy` or acceptable `degraded` state.
- Use the stop service to end the session and publish a terminal result.

Expected behavior:

- pause or stop takes effect within 2 seconds
- resume rebuilds remaining work units instead of depending on an old Nav2 goal handle
- final session result includes covered, remaining, and blocked area metrics

## 8) Validate Low-Battery and Localization Recovery

- Simulate or trigger low battery and confirm the session transitions to `docking`.
- Confirm the dock adapter issues the dock request through the Roomba driver and records success or failure.
- Simulate localization degradation and confirm the supervisor first attempts bounded recovery.
- Confirm `lost` localization ends the session safely as `incomplete` if recovery fails.

## 9) Validation Commands

- `ruff check src tests`
- `mypy --strict src`
- `pytest -q`
- `pytest tests/integration -q`
- `colcon test --packages-select roomba_cleaning_msgs roomba_cleaning_coverage roomba_autonomous_cleaning`
