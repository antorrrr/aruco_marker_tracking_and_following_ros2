#!/usr/bin/env python3
"""
tof_noise_characterization.py

Hold the VL53L0X still at a fixed, known distance and this logs N samples
from /tof/range, then reports mean/std/variance — the noise parameters the
Kalman filter fusion node needs.

Run:
    ros2 run aruco_follower tof_noise_characterization --ros-args -p num_samples:=100
"""

import statistics

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Range


class ToFNoiseCharacterization(Node):

    def __init__(self):
        super().__init__('tof_noise_characterization')
        self.declare_parameter('num_samples', 100)
        self.num_samples = self.get_parameter('num_samples').value
        self.samples = []
        self.create_subscription(Range, '/tof/range', self._cb, 10)
        self.get_logger().info(f"Collecting {self.num_samples} samples — hold the sensor still...")

    def _cb(self, msg: Range):
        if len(self.samples) < self.num_samples:
            self.samples.append(msg.range)


def main(args=None):
    rclpy.init(args=args)
    node = ToFNoiseCharacterization()
    try:
        while len(node.samples) < node.num_samples:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass

    samples = node.samples
    if len(samples) < 2:
        print("Not enough samples collected.")
    else:
        mean = statistics.mean(samples)
        std = statistics.stdev(samples)
        variance = std ** 2
        print(f"\n=== VL53L0X noise characterization ({len(samples)} samples) ===")
        print(f"Mean distance: {mean:.4f} m")
        print(f"Std dev:       {std:.5f} m")
        print(f"Variance:      {variance:.7f} m^2   <-- use this for the Kalman filter's measurement noise")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
