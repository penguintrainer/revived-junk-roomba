# Quickstart Guide: Roomba 577 ROS2 Cleaning & Navigation

This guide provides instructions to quickly set up, build, and run the Roomba 577 ROS2 Cleaning & Navigation system.

## 1. Prerequisites

Before you begin, ensure you have the following installed and available:

- **Operating System**: Ubuntu 20.04 LTS (Focal Fossa) or newer, or another ROS2-supported Linux distribution.
- **ROS2 Distribution**: Foxy Fitzroy or Humble Hawksbill (or a later compatible release).
    - Follow the official ROS2 installation guide for your system: [https://docs.ros.org/en/foxy/Installation.html](https://docs.ros.org/en/foxy/Installation.html)
- **Python**: Python 3.13+ (typically comes with ROS2 installation).
- **Joy-Con Controller**: A Nintendo Switch Joy-Con controller, paired via Bluetooth with your host system.
- **Roomba 577 Robot**:
    - Ensure your Roomba 577 has the Open Interface (OI) enabled. This usually involves a serial connection.
    - A USB-to-serial adapter might be required to connect the Roomba to the host computer (e.g., using a FTDI FT232RL chip).

## 2. Setup Development Environment

1.  **Clone the Repository**:
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Install ROS2 Dependencies**:
    The system relies on the `joy_linux` package for Joy-Con input. If not already installed:
    ```bash
    sudo apt update
    sudo apt install ros-<ros2-distro>-joy-linux
    ```
    (Replace `<ros2-distro>` with your ROS2 distribution, e.g., `foxy`, `humble`).

3.  **Install Python Dependencies**:
    Navigate to your workspace root and install required Python packages. It's recommended to use a virtual environment if not already managing system Python packages.
    ```bash
    pip install numpy opencv-python create_robot
    ```

## 3. Build the Project

From your ROS2 workspace root (e.g., `~/ros2_ws`), build the `roomba_cleaning_nav` package:

```bash
cd <your_ros2_workspace_root>
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select roomba_cleaning_nav
```

## 4. Run the System

1.  **Source your ROS2 environment**:
    ```bash
    source install/setup.bash
    ```

2.  **Launch the Roomba ROS2 Nodes**:
    This command will start all necessary nodes including the Roomba driver, teleoperation, navigation, and cleaning control.
    ```bash
    ros2 launch roomba_cleaning_nav roomba_launch.py
    ```

3.  **Upload a Map (if starting autonomous navigation)**:
    Before using autonomous navigation, you must provide a static map.
    - Place your `my_map.yaml` and `my_map.pgm` files in the `roomba_cleaning_nav/maps/` directory.
    - Ensure your `roomba_launch.py` and `nav2_params.yaml` are configured to load this map.

4.  **Teleoperate with Joy-Con**:
    - With the `roomba_launch.py` running, you should be able to use your paired Joy-Con to manually control the Roomba.
    - Refer to the project documentation for specific Joy-Con button mappings.

5.  **Initiate Autonomous Cleaning**:
    - Toggle to autonomous mode using the designated Joy-Con button.
    - You can send a navigation goal via a visualization tool like Rviz or use the `clean_area` action (if implemented) to start an autonomous cleaning cycle.

    **Example (sending goal via ROS2 CLI - advanced)**:
    ```bash
    ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: map}, pose: {position: {x: 1.0, y: 0.5, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}}"
    ```
