#!/usr/bin/env python3
"""
set_target_marker.py

Interactive terminal tool: type a marker id and it's published to
/aruco/target_marker_id (std_msgs/Int32). aruco_detector.py picks it up
live (no restart needed) and switches to tracking that id - highlighting
it GREEN in the debug image and publishing its pose/distance. Every other
visible marker is shown RED and ignored.

Usage:
    ros2 run aruco_follower set_target_marker

At the prompt:
    <non-negative integer>  -> track that marker id
    -1  (or blank)          -> clear the target (nothing tracked/followed)
    q                       -> quit
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy, QoSReliabilityPolicy
from std_msgs.msg import Int32


class TargetMarkerCommander(Node):
    def __init__(self):
        super().__init__('target_marker_commander')
        # Transient-local: if aruco_detector isn't up yet when this is launched, it'll
        # still receive the last command as soon as it starts listening.
        qos = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
        )
        self.pub = self.create_publisher(Int32, '/aruco/target_marker_id', qos)

    def send(self, marker_id: int):
        msg = Int32()
        msg.data = marker_id
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = TargetMarkerCommander()

    print("ArUco target marker commander")
    print("Enter a marker id to follow it (shown GREEN in the debug image).")
    print("Enter -1 to clear the target (all markers shown RED, robot stops).")
    print("Type 'q' to quit.\n")

    try:
        while rclpy.ok():
            raw = input("target marker id> ").strip()
            if raw.lower() in ('q', 'quit', 'exit'):
                break
            if raw == '':
                continue
            try:
                marker_id = int(raw)
            except ValueError:
                print("Please enter an integer marker id, -1, or 'q'.")
                continue

            node.send(marker_id)
            if marker_id < 0:
                print("Target cleared - no marker will be tracked/followed.")
            else:
                print(f"Now targeting marker id {marker_id}.")
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()