# Quickstart: Joy-Con Manual Drive Cleaning (Roomba577)

## 1) Prerequisites

- Ubuntu 24.04.4 LTS
- ROS2 Jazzy
- Python 3.13+
- Left Joy-Con paired over Bluetooth/HID
- Roomba577 connected over serial and supported through `create_robot`
- Linux HID access configured (udev rules / permissions for Joy-Con, `dialout` access for Roomba serial device)

## 2) Workspace Setup

1. Source ROS2 Jazzy.
2. Install Python dependencies for development and Joy-Con HID access.
3. Build the ROS2 workspace / package set.

Example:

- `source /opt/ros/jazzy/setup.bash`
- `pip install -U joycon-python hidapi pyglm pytest ruff mypy`
- `rosdep install --from-paths src -i -y`
- `colcon build --packages-select roomba_cleaning_nav`
- `source install/setup.bash`

## 3) Launch Dependencies

1. Start the Roomba driver via `create_robot` with the Roomba 500-series launch/config.
2. Confirm `cmd_vel`, `cliff`, and diagnostics are available.

Example:

- `ros2 launch create_bringup create_1.launch`
- `ros2 topic echo /cliff`
- `ros2 topic echo /diagnostics`

## 4) Start Manual Drive Node

- Launch the manual drive node.
- Confirm the status topic reports `idle` before entering manual mode.

Example:

- `ros2 run roomba_cleaning_nav manual_drive_node`
- `ros2 topic echo /manual_drive/status`

## 5) Operate with the Left Joy-Con

- Long-press the configured mode button for 1 second to enter manual mode.
- D-pad up/down moves forward/backward.
- D-pad left/right rotates in place.
- `ZL` or `L` toggles cleaning on/off.
- Long-press the mode button again for 1 second to exit manual mode.

Expected behavior:

- Motion stops within 300 ms when directional buttons are released.
- Cleaning turns off automatically on manual-mode exit.
- Virtual walls / keep-out zones are ignored only while manual mode is active.

## 6) Verify Safety Behavior

- Turn off the Joy-Con or move it out of link range; within 1 second the robot must stop, disable cleaning, and leave manual mode.
- Restore Joy-Con link; verify the robot stays stopped until manual mode is explicitly re-entered.
- Trigger or simulate the Roomba cliff sensor; verify motion is inhibited immediately.
- Disable rumble support (or run on a system where it is unavailable); verify `/manual_drive/status` still reports transitions correctly.

## 7) Validation Commands

- `ruff check src tests`
- `mypy --strict src`
- `pytest -q`
- `pytest tests/integration -q`
- `colcon test --packages-select roomba_cleaning_nav`