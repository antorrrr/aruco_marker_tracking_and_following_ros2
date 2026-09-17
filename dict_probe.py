#!/usr/bin/env python3
"""
dict_probe.py

One-shot diagnostic: grabs a single frame from an image topic and tries
EVERY ArUco dictionary against it, printing which ones detect markers
(and how many). Run this while holding the marker sheet steady in view
of the camera.

Usage:
    ros2 run <your_pkg> dict_probe.py
    # or just: python3 dict_probe.py  (needs rclpy + cv_bridge on PYTHONPATH)

Optional:
    --topic /camera/image_raw   (default)
"""

import argparse
import sys

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

ARUCO_DICT_MAP = {
    "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
    "DICT_4X4_250": cv2.aruco.DICT_4X4_250,
    "DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
    "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
    "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
    "DICT_5X5_250": cv2.aruco.DICT_5X5_250,
    "DICT_5X5_1000": cv2.aruco.DICT_5X5_1000,
    "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
    "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
    "DICT_6X6_250": cv2.aruco.DICT_6X6_250,
    "DICT_6X6_1000": cv2.aruco.DICT_6X6_1000,
    "DICT_7X7_50": cv2.aruco.DICT_7X7_50,
    "DICT_7X7_100": cv2.aruco.DICT_7X7_100,
    "DICT_7X7_250": cv2.aruco.DICT_7X7_250,
    "DICT_7X7_1000": cv2.aruco.DICT_7X7_1000,
    "DICT_ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
}


class DictProbe(Node):
    def __init__(self, topic: str):
        super().__init__('dict_probe')
        self.bridge = CvBridge()
        self.done = False
        self.create_subscription(Image, topic, self.cb, qos_profile_sensor_data)
        self.get_logger().info(f"Waiting for one frame on {topic} ...")

    def cb(self, msg: Image):
        if self.done:
            return
        self.done = True
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        print("\n--- Trying every ArUco dictionary against this frame ---\n")
        hits = []
        for name, dict_id in ARUCO_DICT_MAP.items():
            aruco_dict = cv2.aruco.getPredefinedDictionary(dict_id)
            params = cv2.aruco.DetectorParameters_create()
            corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=params)
            n = 0 if ids is None else len(ids)
            marker = "  <-- HIT" if n > 0 else ""
            print(f"{name:22s} detected: {n}{marker}")
            if n > 0:
                hits.append((name, ids.flatten().tolist()))

        print("\n--- Summary ---")
        if hits:
            for name, ids_found in hits:
                print(f"  {name}: ids {ids_found}")
        else:
            print("  No dictionary detected anything on this frame.")
            print("  Try again with better lighting/focus/less glare, or confirm")
            print("  the sheet was actually generated as ArUco (not AprilTag/ChArUco).")

        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='/camera/image_raw')
    args, _ = parser.parse_known_args()

    rclpy.init()
    node = DictProbe(args.topic)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
