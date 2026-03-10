geometry_msgs/Point position
uint8 obstacle_type              # 0=STEP_EDGE, 1=CABLE, 2=FLOOR_OBJECT, 3=UNKNOWN
uint8 STEP_EDGE=0
uint8 CABLE=1
uint8 FLOOR_OBJECT=2
uint8 UNKNOWN=3
uint8 detection_source           # 0=LIDAR, 1=RGBD, 2=FUSED
uint8 SOURCE_LIDAR=0
uint8 SOURCE_RGBD=1
uint8 SOURCE_FUSED=2
float32 confidence               # 0.0-1.0
geometry_msgs/Vector3 bounding_size
