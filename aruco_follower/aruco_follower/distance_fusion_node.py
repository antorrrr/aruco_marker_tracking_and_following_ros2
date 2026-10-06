#!/usr/bin/env python3
"""
distance_fusion_node.py

1D Kalman filter fusing two independent distance measurements:
  - /aruco/distance   (camera + solvePnP, from aruco_detector.py)
  - /tof/range         (VL53L0X, from vl53l0x_node.py)

Publishes the fused estimate on /fused_distance (std_msgs/Float32).

Why fuse: the two sensors have different failure modes. The camera can
measure across a wider field of view and works only when the marker is
detected, but its accuracy degrades with viewing angle and lighting. The
ToF sensor is generally more precise at close range but has a narrow ~25deg
beam (no lateral info) and a hard max range (~1.2m in this configuration).
Fusing lets the filter lean on whichever is more trustworthy moment to
moment, rather than switching between them with hard thresholds.

Measurement noise (R) for each sensor should come from real characterization:
  - ToF: run tof_noise_characterization.py, pass the resulting variance
    as the tof_variance parameter.
  - Camera: derive from your distance_accuracy_logger.py / analyze_distance_accuracy.py
    results (variance of measured distance at a given true distance is a
    reasonable estimate) and pass as camera_variance.
Defaults below are placeholders — replace with your measured values before
trusting fusion results for the report.

Fusion logic per update:
  - If both measurements are available and within tof.max_range: standard
    Kalman update using both as independent measurements (sequential update).
  - If only camera available (marker seen, ToF out of range or > max_range):
    update with camera measurement only.
  - If only ToF available (marker not detected, e.g. occluded): update with
    ToF only, still useful for e.g. collision-avoidance-style use even
    without visual confirmation of the marker itself.
  - If neither available: predict-only step (a plain hold, since there's no
    velocity model here — this is a static 1D distance filter, not a motion
    tracker).
"""

import threading

import rclpy
from rclpy.node import Node

from std_msgs.msg import Float32, Bool
from sensor_msgs.msg import Range


class DistanceFusionNode(Node):

    def __init__(self):
        super().__init__('distance_fusion_node')

        self.declare_parameter('camera_variance', 0.0025)   # m^2, placeholder ~5cm std dev — replace with measured value
        self.declare_parameter('tof_variance', 0.0001)       # m^2, placeholder ~1cm std dev — replace with measured value
        self.declare_parameter('process_variance', 0.0005)   # m^2, how much we trust the estimate to drift between updates
        self.declare_parameter('tof_max_range', 1.2)          # meters, matches VL53L0X default-mode limit

        self.R_camera = self.get_parameter('camera_variance').value
        self.R_tof = self.get_parameter('tof_variance').value
        self.Q = self.get_parameter('process_variance').value
        self.tof_max_range = self.get_parameter('tof_max_range').value

        self.lock = threading.Lock()
        self.x = None       # current fused distance estimate
        self.P = 1.0         # current estimate variance/uncertainty

        self.latest_camera_distance = None
        self.latest_camera_detected = False
        self.latest_tof_range = None

        self.create_subscription(Float32, '/aruco/distance', self._camera_cb, 10)
        self.create_subscription(Bool, '/aruco/detected', self._detected_cb, 10)
        self.create_subscription(Range, '/tof/range', self._tof_cb, 10)

        self.fused_pub = self.create_publisher(Float32, '/fused_distance', 10)

        # fuse at a fixed rate rather than reacting to every individual
        # message, so both sensors' latest values get combined together
        self.create_timer(0.05, self._fuse_step)  # 20 Hz

        self.get_logger().info(
            f"distance_fusion_node up | R_camera={self.R_camera} R_tof={self.R_tof} Q={self.Q}"
        )

    def _camera_cb(self, msg: Float32):
        with self.lock:
            self.latest_camera_distance = msg.data

    def _detected_cb(self, msg: Bool):
        with self.lock:
            self.latest_camera_detected = msg.data

    def _tof_cb(self, msg: Range):
        with self.lock:
            self.latest_tof_range = msg.range

    def _kalman_update(self, measurement, R):
        """Standard 1D Kalman update against the current state."""
        if self.x is None:
            self.x = measurement
            self.P = R
            return
        K = self.P / (self.P + R)  # Kalman gain
        self.x = self.x + K * (measurement - self.x)
        self.P = (1 - K) * self.P

    def _fuse_step(self):
        with self.lock:
            camera_ok = self.latest_camera_detected and self.latest_camera_distance is not None
            camera_val = self.latest_camera_distance
            tof_val = self.latest_tof_range

        tof_ok = tof_val is not None and 0.0 < tof_val <= self.tof_max_range

        # predict step: inflate uncertainty slightly between updates
        if self.x is not None:
            self.P += self.Q

        if camera_ok and tof_ok:
            self._kalman_update(camera_val, self.R_camera)
            self._kalman_update(tof_val, self.R_tof)
        elif camera_ok:
            self._kalman_update(camera_val, self.R_camera)
        elif tof_ok:
            self._kalman_update(tof_val, self.R_tof)
        else:
            return  # nothing to fuse this cycle, hold last estimate

        self.fused_pub.publish(Float32(data=float(self.x)))


def main(args=None):
    rclpy.init(args=args)
    node = DistanceFusionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
