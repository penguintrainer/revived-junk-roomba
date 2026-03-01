#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

def main(args=None):
    rclpy.init(args=args)
    node = Node('cleaning_node')
    node.get_logger().info('Cleaning Node started')
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
