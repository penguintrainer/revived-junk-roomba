# ROS2 Interfaces (Contracts) for Roomba 577 Cleaning & Navigation

This document defines the key ROS2 interfaces (Topics, Services, and Actions) that will serve as the "API contracts" between different nodes within the Roomba 577 cleaning and navigation system. These interfaces facilitate communication and define the data structures for inter-node interactions.

## Topics

### Input Topics
- **`/joy_input`** (`sensor_msgs/msg/Joy`): Raw input data from the Joy-Con controller (axes and button states).
- **`/scan`** (`sensor_msgs/msg/LaserScan`): 2D Lidar scan data for mapping and obstacle avoidance.
- **`/camera_image`** (`sensor_msgs/msg/Image`): Raw image data from the 2D camera for object detection.
- **`/odom`** (`nav_msgs/msg/Odometry`): Robot odometry, typically from the Roomba's internal sensors.

### Output Topics
- **`/cmd_vel`** (`geometry_msgs/msg/Twist`): Velocity commands for controlling the Roomba's linear and angular motion. Published by `teleop_node` in manual mode and `navigation_node` in autonomous mode.
- **`/robot_status`** (`roomba_interfaces/msg/RobotStatus`): Publishes the current operational status of the robot (mode, battery, errors, etc.). Custom message type (see `roomba_interfaces` package).
- **`/audio_cues`** (`roomba_interfaces/msg/AudioCue`): Publishes requests for audio feedback (beeps, tones) to `roomba_driver_node`. Custom message type.

### Transform Topics
- **`/tf`** (`tf2_msgs/msg/TFMessage`): Provides coordinate frame transformations (e.g., `base_link` to `odom`, `odom` to `map`). Essential for navigation.

## Services

### Control Services
- **`/set_mode`** (`roomba_interfaces/srv/SetMode`): A service to request a change between `MANUAL` and `AUTONOMOUS` operating modes.
    - **Request**: `mode` (integer enum representing desired mode).
    - **Response**: `success` (boolean), `message` (string).
- **`/resume_operation`** (`std_srvs/srv/Trigger`): A service to resume robot operation after a safety-triggered stop.
    - **Request**: (empty).
    - **Response**: `success` (boolean), `message` (string).
- **`/toggle_cleaning`** (`std_srvs/srv/SetBool`): A service to activate or deactivate the Roomba's cleaning mechanisms (brushes, suction).
    - **Request**: `data` (boolean, `true` for ON, `false` for OFF).
    - **Response**: `success` (boolean), `message` (string).

## Actions

### Navigation Actions
- **`/navigate_to_pose`** (`nav2_msgs/action/NavigateToPose`): The standard Nav2 action for sending a goal pose for autonomous navigation.
    - **Goal**: `pose` (geometry_msgs/msg/PoseStamped).
    - **Result**: `success` (boolean), `message` (string).
- **`/clean_area`** (`roomba_interfaces/action/CleanArea`): An action to initiate an autonomous cleaning cycle within a defined area.
    - **Goal**: (Currently empty, or could include specific cleaning parameters like `duration`, `area_id`).
    - **Result**: `success` (boolean), `message` (string), `cleaned_percentage` (float).

## Custom Message/Service/Action Definitions

The following custom ROS2 messages, services, and actions will be defined in a `roomba_interfaces` package:

- **`roomba_interfaces/msg/RobotStatus`**:
    - `uint8 mode` (0: MANUAL, 1: AUTONOMOUS, 2: ERROR)
    - `float32 battery_percentage`
    - `bool is_brush_entangled`
    - `bool is_cliff_detected`
    - `string status_message`
- **`roomba_interfaces/msg/AudioCue`**:
    - `uint8 cue_id` (e.g., 0: MODE_CHANGE, 1: ERROR, 2: LOW_BATTERY, 3: SAFETY_STOP)
    - `uint8 severity` (0: INFO, 1: WARNING, 2: CRITICAL)
- **`roomba_interfaces/srv/SetMode`**:
    - Request: `uint8 mode`
    - Response: `bool success` `string message`
- **`roomba_interfaces/action/CleanArea`**:
    - Goal: (empty for now, can be extended)
    - Result: `bool success` `string message` `float32 cleaned_percentage`
    - Feedback: `float32 current_progress` `builtin_interfaces/msg/Duration time_elapsed`
