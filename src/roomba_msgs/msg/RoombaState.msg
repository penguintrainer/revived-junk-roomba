std_msgs/Header header
float32 battery_charge_ratio     # 0.0-1.0
geometry_msgs/Twist velocity
bool bumper_left
bool bumper_right
bool wheel_drop_left
bool wheel_drop_right
bool serial_connected
uint8 oi_mode                    # 0=OFF, 1=PASSIVE, 2=SAFE, 3=FULL
uint8 OI_MODE_OFF=0
uint8 OI_MODE_PASSIVE=1
uint8 OI_MODE_SAFE=2
uint8 OI_MODE_FULL=3
