#!/usr/bin/env python3
"""
marker_follower.py

Closes the loop on the ArUco detector's output to make the diffbot follow
the marker: turns to keep it centered, and drives to hold a target
standoff distance.

Subscribes:
  - /aruco/marker_pose  (geometry_msgs/PoseStamped)  marker pose in camera
                        optical frame (x=right, y=down, z=forward)
  - /aruco/detected     (std_msgs/Bool)               whether marker is visible

Publishes:
  - /cmd_vel_nav_stamped (geometry_msgs/TwistStamped)  feeds twist_mux's
                          'navigation' input (priority 10, lower than joystick)

Control law (simple proportional, run on a timer so we can also react to
"marker lost"):
  - heading_error = atan2(x, z)          -> angular.z = -kp_angular * heading_error
  - distance_error = z - target_distance -> linear.x  =  kp_linear  * distance_error
  - If marker not seen within `marker_timeout` seconds, publish zero twist
    (robot stops rather than coasting on stale commands).

Tune via parameters (see declare_parameter calls below).
"""

import math
import time

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped, TwistStamped
from std_msgs.msg import Bool


class MarkerFollower(Node):

    def __init__(self):
        super().__init__('marker_follower')

        # ---- Parameters ----
        self.declare_parameter('target_distance', 0.5)     # meters, desired standoff
        self.declare_parameter('kp_linear', 0.6)
        self.declare_parameter('kp_angular', 1.2)
        self.declare_parameter('max_linear', 0.18)          # stay under diff_controller's 0.2 limit
        self.declare_parameter('max_angular', 0.45)         # stay under diff_controller's 0.5 limit
        self.declare_parameter('distance_deadband', 0.03)   # meters, don't creep for tiny error
        self.declare_parameter('heading_deadband', 0.03)    # radians
        self.declare_parameter('marker_timeout', 0.5)       # seconds since last detection -> stop
        self.declare_parameter('control_rate', 20.0)        # Hz
        self.declare_parameter('cmd_frame_id', 'base_link')

        self.target_distance = self.get_parameter('target_distance').value
        self.kp_linear = self.get_parameter('kp_linear').value
        self.kp_angular = self.get_parameter('kp_angular').value
        self.max_linear = self.get_parameter('max_linear').value
        self.max_angular = self.get_parameter('max_angular').value
        self.distance_deadband = self.get_parameter('distance_deadband').value
        self.heading_deadband = self.get_parameter('heading_deadband').value
        self.marker_timeout = self.get_parameter('marker_timeout').value
        self.cmd_frame_id = self.get_parameter('cmd_frame_id').value
        control_rate = self.get_parameter('control_rate').value

        # ---- State ----
        self.last_x = 0.0
        self.last_z = 0.0
        self.marker_visible = False
        self.last_seen_time = 0.0  # monotonic seconds

        # ---- Pub/Sub ----
        self.create_subscription(PoseStamped, '/aruco/marker_pose', self.pose_cb, 10)
        self.create_subscription(Bool, '/aruco/detected', self.detected_cb, 10)
        self.cmd_pub = self.create_publisher(TwistStamped, '/cmd_vel_nav_stamped', 10)

        self.timer = self.create_timer(1.0 / control_rate, self.control_loop)

        self.get_logger().info(
            f"marker_follower up | target_distance={self.target_distance}m "
            f"max_linear={self.max_linear} max_angular={self.max_angular} "
            f"marker_timeout={self.marker_timeout}s"
        )

    def pose_cb(self, msg: PoseStamped):
        self.last_x = msg.pose.position.x
        self.last_z = msg.pose.position.z
        self.last_seen_time = time.monotonic()

    def detected_cb(self, msg: Bool):
        self.marker_visible = msg.data

    def control_loop(self):
        now = time.monotonic()
        age = now - self.last_seen_time
        lost = (not self.marker_visible) or (age > self.marker_timeout)

        twist_msg = TwistStamped()
        twist_msg.header.stamp = self.get_clock().now().to_msg()
        twist_msg.header.frame_id = self.cmd_frame_id

        if lost:
            # Marker not currently visible/fresh -> stop rather than coast.
            twist_msg.twist.linear.x = 0.0
            twist_msg.twist.angular.z = 0.0
            self.cmd_pub.publish(twist_msg)
            return

        heading_error = math.atan2(self.last_x, self.last_z)
        distance_error = self.last_z - self.target_distance

        angular_cmd = 0.0
        if abs(heading_error) > self.heading_deadband:
            angular_cmd = -self.kp_angular * heading_error
            angular_cmd = max(-self.max_angular, min(self.max_angular, angular_cmd))

        linear_cmd = 0.0
        if abs(distance_error) > self.distance_deadband:
            linear_cmd = self.kp_linear * distance_error
            linear_cmd = max(-self.max_linear, min(self.max_linear, linear_cmd))

        twist_msg.twist.linear.x = linear_cmd
        twist_msg.twist.angular.z = angular_cmd
        self.cmd_pub.publish(twist_msg)


def main(args=None):
    rclpy.init(args=args)
    node = MarkerFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Publish a final stop command on the way out.
        stop = TwistStamped()
        stop.header.stamp = node.get_clock().now().to_msg()
        stop.header.frame_id = node.cmd_frame_id
        node.cmd_pub.publish(stop)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
