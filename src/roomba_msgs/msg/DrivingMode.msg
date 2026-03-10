std_msgs/Header header
uint8 mode                       # 0=IDLE, 1=RANDOM, 2=MANUAL, 3=AUTONOMOUS
uint8 previous_mode
builtin_interfaces/Time transition_time
uint8 IDLE=0
uint8 RANDOM=1
uint8 MANUAL=2
uint8 AUTONOMOUS=3
