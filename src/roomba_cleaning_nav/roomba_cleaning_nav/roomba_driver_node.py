import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Joy # Using this temporarily for testing joy inputs
from tf2_ros import TransformBroadcaster, TransformStamped

import serial
import time
import struct
from math import sin, cos, pi

# Assuming create_robot library is installed and available
# from create_robot import CreateRobot, Roomba500 # Placeholder - need to verify actual library usage

# Custom interfaces
from roomba_interfaces.msg import RobotStatus, AudioCue
from std_srvs.srv import Trigger, SetBool

# Roomba Open Interface commands
OI_START = 128
OI_BAUD = 129
OI_FULL_MODE = 132
OI_DRIVE = 137
OI_MOTORS = 138
OI_LEDS = 139
OI_SONG = 140
OI_PLAY_SONG = 141
OI_SENSORS = 142
OI_QUERY_LIST = 149
OI_DRIVE_DIRECT = 145
OI_CLEAN = 135 # Clean (Roomba 500 series)

# Sensor packet IDs - Roomba 577 specific (need to verify documentation)
# A subset of common sensor packet IDs
OI_PACKET_ID_BUMPERS_WHEELS = 7
OI_PACKET_ID_CLIFF_LEFT = 9
OI_PACKET_ID_CLIFF_FRONT_LEFT = 10
OI_PACKET_ID_CLIFF_FRONT_RIGHT = 11
OI_PACKET_ID_CLIFF_RIGHT = 12
OI_PACKET_ID_BATTERY_CHARGE = 16
OI_PACKET_ID_BATTERY_CAPACITY = 17
OI_PACKET_ID_CURRENT_LEFT_MOTOR = 22 # Assuming current data is available
OI_PACKET_ID_CURRENT_RIGHT_MOTOR = 23
OI_PACKET_ID_VIRTUAL_WALL = 13
OI_PACKET_ID_OVERCURRENT_MOTORS = 14 # Bit-mask for overcurrent status

class RoombaDriverNode(Node):
    def __init__(self):
        super().__init__('roomba_driver')
        self.get_logger().info('Roomba Driver Node initializing...')

        # Declare parameters
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('robot_radius', 0.175)
        self.declare_parameter('wheel_distance', 0.235) # Distance between wheels
        self.declare_parameter('battery_low_threshold_percent', 15)
        self.declare_parameter('audio_cue_mode_change', 1)
        self.declare_parameter('audio_cue_error', 2)
        self.declare_parameter('audio_cue_low_battery', 3)

        self.serial_port = self.get_parameter('serial_port').get_parameter_value().string_value
        self.baud_rate = self.get_parameter('baud_rate').get_parameter_value().integer_value
        self.robot_radius = self.get_parameter('robot_radius').get_parameter_value().double_value
        self.wheel_distance = self.get_parameter('wheel_distance').get_parameter_value().double_value
        self.battery_low_threshold_percent = self.get_parameter('battery_low_threshold_percent').get_parameter_value().integer_value
        self.audio_cue_mode_change = self.get_parameter('audio_cue_mode_change').get_parameter_value().integer_value
        self.audio_cue_error = self.get_parameter('audio_cue_error').get_parameter_value().integer_value
        self.audio_cue_low_battery = self.get_parameter('audio_cue_low_battery').get_parameter_value().integer_value

        self.get_logger().info(f'Connecting to Roomba on {self.serial_port} at {self.baud_rate} baud...')
        try:
            self.roomba_serial = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            time.sleep(1) # Give Roomba time to wake up
            self.send_command(OI_START)
            time.sleep(0.1)
            self.send_command(OI_FULL_MODE)
            time.sleep(0.1)
            self.get_logger().info('Roomba connected and in Full Mode.')
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to connect to Roomba: {e}')
            self.roomba_serial = None
            # Consider more robust error handling / retry mechanisms

        self.current_x = 0.0
        self.current_y = 0.0
        self.current_yaw = 0.0
        self.current_vx = 0.0
        self.current_vyaw = 0.0
        self.last_time = self.get_clock().now()

        # QoS Profile for publishers
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            durability=DurabilityPolicy.VOLATILE
        )

        # Publishers
        self.odom_publisher = self.create_publisher(Odometry, 'odom', qos_profile)
        self.robot_status_publisher = self.create_publisher(RobotStatus, 'robot_status', qos_profile)

        # Subscribers
        self.cmd_vel_subscriber = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            qos_profile
        )
        self.audio_cue_subscriber = self.create_subscription(
            AudioCue,
            'audio_cues',
            self.audio_cue_callback,
            qos_profile
        )

        # Service Servers
        self.toggle_cleaning_service = self.create_service(SetBool, 'toggle_cleaning', self.toggle_cleaning_callback)

        # Transform Broadcaster for odometry
        self.tf_broadcaster = TransformBroadcaster(self)

        # Timer for sensor polling and odometry publishing
        self.sensor_timer = self.create_timer(0.05, self.sensor_and_odom_callback) # 20 Hz

        self.is_cleaning = False
        self.get_logger().info('Roomba Driver Node initialized.')


    def send_command(self, opcode, data=None):
        if self.roomba_serial:
            try:
                if data:
                    self.roomba_serial.write(bytes([opcode]) + bytes(data))
                else:
                    self.roomba_serial.write(bytes([opcode]))
                self.roomba_serial.flush()
            except serial.SerialException as e:
                self.get_logger().error(f"Error sending command {opcode}: {e}")
                self.roomba_serial = None # Mark as disconnected
            except Exception as e:
                self.get_logger().error(f"Unexpected error sending command {opcode}: {e}")
        else:
            self.get_logger().warn(f"Attempted to send command {opcode} while not connected to Roomba.")

    def read_sensors(self, packet_id):
        if not self.roomba_serial:
            return None
        try:
            self.send_command(OI_SENSORS, [packet_id])
            # This is a blocking read, may need to be handled more carefully in a real-time system
            # The length of the response varies by packet_id. For Roomba 577, packet 7 is 1 byte, 
            # packets 16,17 are 2 bytes, etc.
            # This needs to be precisely matched with OI specification
            if packet_id == OI_PACKET_ID_BUMPERS_WHEELS:
                response = self.roomba_serial.read(1)
                return struct.unpack('B', response)[0] if response and len(response) == 1 else None
            elif packet_id in [OI_PACKET_ID_BATTERY_CHARGE, OI_PACKET_ID_BATTERY_CAPACITY]:
                response = self.roomba_serial.read(2)
                return struct.unpack('>H', response)[0] if response and len(response) == 2 else None
            elif packet_id == OI_PACKET_ID_OVERCURRENT_MOTORS:
                response = self.roomba_serial.read(1)
                return struct.unpack('B', response)[0] if response and len(response) == 1 else None
            # Add more packet IDs and their response lengths as needed
            else:
                self.get_logger().warn(f"Sensor packet ID {packet_id} not implemented for reading.")
                return None
        except serial.SerialException as e:
            self.get_logger().error(f"Error reading sensor {packet_id}: {e}")
            self.roomba_serial = None
            return None
        except struct.error as e:
            self.get_logger().error(f"Error unpacking sensor data for {packet_id}: {e}")
            return None
        except Exception as e:
            self.get_logger().error(f"Unexpected error reading sensor {packet_id}: {e}")
            return None

    def cmd_vel_callback(self, msg):
        if not self.roomba_serial:
            self.get_logger().warn("Received cmd_vel but not connected to Roomba.")
            return

        # Store current velocities for odometry calculation
        self.current_vx = msg.linear.x
        self.current_vyaw = msg.angular.z

        # Convert linear.x and angular.z to Roomba wheel velocities
        # Roomba OI uses millimeters/second for velocity
        # Max velocity: 500 mm/s, Max radius for turns: 2000 mm, Min radius: -2000 mm
        # Special cases: straight (32768), spin_left (1), spin_right (-1)

        linear_vel_mm = int(msg.linear.x * 1000)
        angular_vel_rad_s = msg.angular.z

        radius = 0 # Default invalid radius
        if angular_vel_rad_s == 0:
            radius = 32768 # Straight
        elif linear_vel_mm == 0:
            radius = 1 if angular_vel_rad_s > 0 else -1 # Spin left/right
        else:
            # Calculate radius of curvature (R = v / omega)
            # Roomba wants radius for the center of the robot
            # We are mapping to the Drive (137) command: velocity and radius
            # R = (Vr + Vl) / (Vr - Vl) * (Wheel_Distance / 2)
            # Vr = V + omega * Wheel_Distance / 2
            # Vl = V - omega * Wheel_Distance / 2
            # V = (Vr + Vl) / 2
            # omega = (Vr - Vl) / Wheel_Distance
            # Drive command (137): [velocity] [radius]
            # Velocity = (Vr + Vl) / 2
            # Radius = (Vr + Vl) / (Vr - Vl) * (Wheel_Distance / 2)
            # From input: linear_vel_mm, angular_vel_rad_s
            # linear_vel_mm = (Vr + Vl) / 2
            # angular_vel_rad_s = (Vr - Vl) / (self.wheel_distance * 1000)

            # Let's derive Radius from linear_vel_mm and angular_vel_rad_s
            # R = (linear_vel_mm / (angular_vel_rad_s * 1000)) * (1000) # This is a simple radius calculation based on a point, not correct for roomba
            # Need to re-evaluate the radius calculation for Roomba's Drive command (137)
            # The Drive command takes velocity and radius, where radius refers to the radius
            # of the arc the center of the robot will take.
            # v = linear_vel_mm
            # omega = angular_vel_rad_s
            # If R_cmd is the radius for Drive command
            # R_cmd = v / omega (for a point robot)
            # However, Roomba's radius is relative to the center of the wheels.
            # The formula in OI spec: (V_right - V_left) * 1000 / (2 * L) = omega
            # (V_right + V_left) / 2 = V
            # Roomba expects radius in mm, velocity in mm/s
            # radius = linear_vel_mm / angular_vel_rad_s # Simple radius, assuming angular_vel_rad_s is not zero
            # This is likely the radius of the turning circle (center of rotation).
            # Need to ensure angular_vel_rad_s is not 0
            if abs(angular_vel_rad_s) > 1e-6: # Avoid division by zero
                radius = int(linear_vel_mm / (angular_vel_rad_s * 1000) * 1000)
                # Clamp radius: -2000 to 2000
                radius = max(min(radius, 2000), -2000)
            else:
                radius = 32768 # Straight if angular velocity is zero or very small

        # Clamp velocities
        linear_vel_mm = max(min(linear_vel_mm, 500), -500) # -500 to 500 mm/s

        # Pack values as 2-byte signed integers (big-endian)
        velocity_bytes = struct.pack('>hh', linear_vel_mm, radius)
        self.send_command(OI_DRIVE, velocity_bytes)

    def audio_cue_callback(self, msg):
        self.get_logger().info(f'Playing audio cue {msg.cue_id} with severity {msg.severity}')
        # Roomba OI requires defining a song (OI_SONG) then playing it (OI_PLAY_SONG)
        # This implementation maps cue_id to song sequence
        
        # Audio cue definitions from spec clarification:
        # Mode Switch: Short, single beep (audio_cue_mode_change parameter)
        # Error: Repeating alarm (audio_cue_error parameter)
        # Low Battery: Slow, intermittent beep (audio_cue_low_battery parameter)

        if msg.cue_id == self.audio_cue_mode_change:
            # Song 0: short, single beep (e.g., C5 for 1/8th note)
            self.send_command(OI_SONG, [0, 1, 60, 10]) # Song 0, 1 note (MIDI C5, 10 * 15ms = 150ms)
            self.send_command(OI_PLAY_SONG, [0])
        elif msg.cue_id == self.audio_cue_error:
            # Song 1: repeating alarm (e.g., two alternating notes)
            self.send_command(OI_SONG, [1, 2, 70, 10, 60, 10]) # Song 1, 2 notes (G5, C5)
            self.send_command(OI_PLAY_SONG, [1]) # Play repeatedly by sending multiple times, or define a longer song
        elif msg.cue_id == self.audio_cue_low_battery:
            # Song 2: slow, intermittent beep (e.g., C4 for 1/4 note, then silence)
            self.send_command(OI_SONG, [2, 1, 48, 20]) # Song 2, 1 note (C4, 20 * 15ms = 300ms)
            self.send_command(OI_PLAY_SONG, [2]) # Play intermittently
        else:
            self.get_logger().warn(f"Unknown audio cue ID: {msg.cue_id}")

    def toggle_cleaning_callback(self, request, response):
        if not self.roomba_serial:
            response.success = False
            response.message = "Not connected to Roomba."
            return

        if request.data: # Enable cleaning
            if not self.is_cleaning:
                self.send_command(OI_CLEAN) # Roomba 500 series 'Clean' command (135)
                self.is_cleaning = True
                self.get_logger().info("Cleaning started.")
            else:
                self.get_logger().info("Cleaning already active.")
        else: # Disable cleaning
            if self.is_cleaning:
                self.send_command(OI_START) # Sending START stops cleaning and resets mode
                self.send_command(OI_FULL_MODE) # Re-enter full mode
                self.is_cleaning = False
                self.get_logger().info("Cleaning stopped.")
            else:
                self.get_logger().info("Cleaning already inactive.")

        response.success = True
        response.message = f"Cleaning toggled to {self.is_cleaning}"
        return response

    def sensor_and_odom_callback(self):
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9

        # Odometry update (very basic for now, needs real encoder feedback)
        # x = x + dt * (vx * cos(yaw) - vy * sin(yaw))
        # y = y + dt * (vx * sin(yaw) + vy * cos(yaw))
        # yaw = yaw + dt * vyaw

        # Assuming differential drive where vx is linear and vyaw is angular
        delta_x = self.current_vx * cos(self.current_yaw) * dt
        delta_y = self.current_vx * sin(self.current_yaw) * dt
        delta_yaw = self.current_vyaw * dt

        self.current_x += delta_x
        self.current_y += delta_y
        self.current_yaw += delta_yaw

        # Normalize yaw to be within -pi to pi
        self.current_yaw = (self.current_yaw + pi) % (2 * pi) - pi

        odom_msg = Odometry()
        odom_msg.header.stamp = current_time.to_msg()
        odom_msg.header.frame_id = 'odom'
        odom_msg.child_frame_id = 'base_link'

        odom_msg.pose.pose.position.x = self.current_x
        odom_msg.pose.pose.position.y = self.current_y
        odom_msg.pose.pose.position.z = 0.0
        # Orientation (quaternion from yaw)
        from tf_transformations import quaternion_from_euler
        q = quaternion_from_euler(0, 0, self.current_yaw)
        odom_msg.pose.pose.orientation.x = q[0]
        odom_msg.pose.pose.orientation.y = q[1]
        odom_msg.pose.pose.orientation.z = q[2]
        odom_msg.pose.pose.orientation.w = q[3]

        odom_msg.twist.twist.linear.x = self.current_vx
        odom_msg.twist.twist.angular.z = self.current_vyaw

        self.odom_publisher.publish(odom_msg)

        # Publish transform (odom -> base_link)
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.current_x
        t.transform.translation.y = self.current_y
        t.transform.translation.z = 0.0
        t.transform.rotation.x = q[0]
        t.transform.rotation.y = q[1]
        t.transform.rotation.z = q[2]
        t.transform.rotation.w = q[3]
        self.tf_broadcaster.sendTransform(t)

        self.last_time = current_time

        # Read and publish RobotStatus
        robot_status_msg = RobotStatus()
        robot_status_msg.header.stamp = current_time.to_msg() # Assuming custom msg has header
        robot_status_msg.mode = RobotStatus.MODE_MANUAL # Placeholder

        # Implement actual sensor readings here
        # Example: Read bumper sensor (packet ID 7)
        bumper_data = self.read_sensors(OI_PACKET_ID_BUMPERS_WHEELS)
        if bumper_data is not None:
            robot_status_msg.is_brush_entangled = bool(bumper_data & 0x02) # Placeholder for entanglement
            robot_status_msg.is_cliff_detected = bool((bumper_data & 0xF0) > 0) # Placeholder for any cliff sensor

        charge = self.read_sensors(OI_PACKET_ID_BATTERY_CHARGE)
        capacity = self.read_sensors(OI_PACKET_ID_BATTERY_CAPACITY)
        if charge is not None and capacity is not None and capacity > 0:
            robot_status_msg.battery_percentage = float(charge) / capacity * 100.0
            if robot_status_msg.battery_percentage <= self.battery_low_threshold_percent:
                # Trigger low battery audio cue (publish to /audio_cues)
                audio_cue_msg = AudioCue()
                audio_cue_msg.cue_id = self.audio_cue_low_battery
                audio_cue_msg.severity = AudioCue.WARNING
                self.audio_cue_publisher.publish(audio_cue_msg) # Need to create this publisher
                
        robot_status_msg.status_message = "Connected"
        self.robot_status_publisher.publish(robot_status_msg)


def main(args=None):
    rclpy.init(args=args)
    node = RoombaDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down Roomba Driver Node.')
    finally:
        node.destroy_node()
        rclpy.roomba_serial.close() # Close serial port
        rclpy.shutdown()

if __name__ == '__main__':
    main()
