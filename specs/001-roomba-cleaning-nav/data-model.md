# Data Model: Roomba 577 ROS2 Cleaning & Navigation

This document outlines the key entities and data structures involved in the Roomba 577 ROS2 Cleaning & Navigation system. These entities represent the core data flow and state within the application.

## Entities

### RobotState
Represents the current operational and physical state of the Roomba.
- **pose**: (x, y, theta) - Current position and orientation of the robot in the map frame.
- **battery_level**: Percentage (0-100) - Current battery charge.
- **sensor_status**:
    - **bumpers**: Boolean array/mask - Status of contact sensors.
    - **cliffs**: Boolean array/mask - Status of cliff sensors.
    - **brush_entangled**: Boolean - Indicates if brushes are entangled (from motor current sensing).
- **current_mode**: Enum (`MANUAL`, `AUTONOMOUS`, `ERROR`) - Current operating mode.
- **cleaning_active**: Boolean - Indicates if cleaning mechanisms are active.

### NavigationGoal
Represents a target pose the robot should reach in autonomous mode.
- **target_pose**: (x, y, theta) - Desired position and orientation.
- **frame_id**: String - Coordinate frame of the target pose (e.g., `map`).

### CleaningMode
Represents the state of the Roomba's cleaning hardware.
- **mode**: Enum (`ACTIVE`, `IDLE`) - Whether brushes/suction are engaged.

### JoyInput
Represents raw input from the Joy-Con controller.
- **axes**: Float array - Analog stick values.
- **buttons**: Boolean array - Button press states.

### TwistCommand
A standard ROS2 message type for commanding robot velocity.
- **linear_x**: Float - Linear velocity in X direction.
- **angular_z**: Float - Angular velocity around Z axis.

### MapData
Represents the static map of the cleaning area.
- **image**: PGM image data - The occupancy grid map.
- **metadata**: YAML - Map resolution, origin, frame_id.

### Obstacle
Represents a detected obstacle in the robot's environment.
- **type**: Enum (`WALL`, `CLIFF`, `CABLE`, `GENERAL`) - Classification of the obstacle.
- **location**: (x, y) or Bounding Box - Position or area of the obstacle.
- **distance**: Float - Distance to the obstacle.

### StatusMessage
Represents messages communicated to the operator via audio cues.
- **message_type**: Enum (`MODE_CHANGE`, `ERROR`, `LOW_BATTERY`, `SAFETY_STOP`, `RESUME`) - Type of status update.
- **severity**: Enum (`INFO`, `WARNING`, `CRITICAL`) - Severity of the status.
- **audio_cue_id**: Integer - Identifier for a specific audio tone/beep.
