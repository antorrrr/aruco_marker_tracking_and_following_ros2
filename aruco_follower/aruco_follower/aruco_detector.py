#!/usr/bin/env python3
"""
aruco_detector.py

Detects ALL visible ArUco markers. Whichever marker id has been commanded
as the "target" (via the target_marker_id launch param, or live over the
/aruco/target_marker_id topic) is:
  - outlined in GREEN in the debug image
  - the only marker whose 6-DoF pose is estimated and published

Every other detected marker is outlined in RED and otherwise ignored
(no pose/distance published for it).

If no target has been commanded (target_id < 0), every marker shows RED
and nothing is published as "detected" - i.e. the robot/follower will not
move until a target is set.

Publishes (for the TARGET marker only):
  - /aruco/marker_pose   (geometry_msgs/PoseStamped)  marker pose in camera optical frame
  - /aruco/distance      (std_msgs/Float32)            straight-line distance to marker (m)
  - /aruco/detected      (std_msgs/Bool)                whether the TARGET marker is currently visible
  - /aruco/debug_image   (sensor_msgs/Image)            annotated image (green=target, red=others)

Subscribes to:
  - <image_topic>              (sensor_msgs/Image)
  - <camera_info_topic>        (sensor_msgs/CameraInfo)
  - /aruco/target_marker_id    (std_msgs/Int32)  set/override which id to target, live

Camera intrinsics come from CameraInfo - the distance/pose numbers are only
as good as that calibration. If you're running uncalibrated, fx/fy/cx/cy
default to a rough guess for a 640x480 image and pose numbers WILL be off.
"""

import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    qos_profile_sensor_data,
    QoSProfile,
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSReliabilityPolicy,
)

from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float32, Bool, Int32

from cv_bridge import CvBridge


ARUCO_DICT_MAP = {
    "DICT_4X4_50": cv2.aruco.DICT_4X4_50,
    "DICT_4X4_100": cv2.aruco.DICT_4X4_100,
    "DICT_5X5_50": cv2.aruco.DICT_5X5_50,
    "DICT_5X5_100": cv2.aruco.DICT_5X5_100,
    "DICT_6X6_50": cv2.aruco.DICT_6X6_50,
    "DICT_6X6_100": cv2.aruco.DICT_6X6_100,
    "DICT_7X7_50": cv2.aruco.DICT_7X7_50,
    "DICT_7X7_100": cv2.aruco.DICT_7X7_100,
    "DICT_7X7_250": cv2.aruco.DICT_7X7_250,
    "DICT_7X7_1000": cv2.aruco.DICT_7X7_1000,
    "DICT_ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
}

GREEN = (0, 255, 0)   # BGR - the commanded target
RED = (0, 0, 255)     # BGR - every other visible marker


def rvec_to_quaternion(rvec):
    """Convert an OpenCV rotation vector to a (x, y, z, w) quaternion."""
    R, _ = cv2.Rodrigues(rvec)
    trace = np.trace(R)
    if trace > 0:
        s = 0.5 / np.sqrt(trace + 1.0)
        w = 0.25 / s
        x = (R[2, 1] - R[1, 2]) * s
        y = (R[0, 2] - R[2, 0]) * s
        z = (R[1, 0] - R[0, 1]) * s
    else:
        if R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
            w = (R[2, 1] - R[1, 2]) / s
            x = 0.25 * s
            y = (R[0, 1] + R[1, 0]) / s
            z = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
            w = (R[0, 2] - R[2, 0]) / s
            x = (R[0, 1] + R[1, 0]) / s
            y = 0.25 * s
            z = (R[1, 2] + R[2, 1]) / s
        else:
            s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
            w = (R[1, 0] - R[0, 1]) / s
            x = (R[0, 2] + R[2, 0]) / s
            y = (R[1, 2] + R[2, 1]) / s
            z = 0.25 * s
    return x, y, z, w


class ArucoDetector(Node):

    def __init__(self):
        super().__init__('aruco_detector')

        # ---- Parameters ----
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('camera_info_topic', '/camera/camera_info')
        self.declare_parameter('marker_size', 0.10)          # meters, side length
        self.declare_parameter('aruco_dictionary', 'DICT_5X5_100')
        self.declare_parameter('target_marker_id', -1)       # -1 = no target commanded yet
        self.declare_parameter('publish_debug_image', True)

        self.marker_size = self.get_parameter('marker_size').value
        dict_name = self.get_parameter('aruco_dictionary').value
        self.target_id = self.get_parameter('target_marker_id').value
        self.publish_debug = self.get_parameter('publish_debug_image').value

        if dict_name not in ARUCO_DICT_MAP:
            self.get_logger().warn(f"Unknown dictionary '{dict_name}', defaulting to DICT_5X5_100")
            dict_name = 'DICT_5X5_100'
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_MAP[dict_name])
        self.aruco_params = cv2.aruco.DetectorParameters_create()

        # 3D corner points of the marker in its own frame (order matches detectMarkers output:
        # top-left, top-right, bottom-right, bottom-left)
        s = self.marker_size / 2.0
        self.obj_points = np.array([
            [-s,  s, 0],
            [ s,  s, 0],
            [ s, -s, 0],
            [-s, -s, 0],
        ], dtype=np.float32)

        self.camera_matrix = None
        self.dist_coeffs = None
        self.bridge = CvBridge()

        # ---- Pub/Sub ----
        image_topic = self.get_parameter('image_topic').value
        info_topic = self.get_parameter('camera_info_topic').value

        self.create_subscription(Image, image_topic, self.image_cb, qos_profile_sensor_data)
        self.create_subscription(CameraInfo, info_topic, self.info_cb, qos_profile_sensor_data)

        # Target id can be set/changed live while the node is running. Transient-local so
        # a commander started after this node still delivers its last command on connect,
        # and this node still gets the last commanded value if it's the one that (re)starts.
        target_qos = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
        )
        self.create_subscription(Int32, '/aruco/target_marker_id', self.target_id_cb, target_qos)

        self.pose_pub = self.create_publisher(PoseStamped, '/aruco/marker_pose', 10)
        self.dist_pub = self.create_publisher(Float32, '/aruco/distance', 10)
        self.detected_pub = self.create_publisher(Bool, '/aruco/detected', 10)
        if self.publish_debug:
            self.debug_pub = self.create_publisher(Image, '/aruco/debug_image', 10)

        self.get_logger().info(
            f"aruco_detector up | dict={dict_name} marker_size={self.marker_size}m "
            f"target_id={self.target_id if self.target_id >= 0 else 'none (waiting for command)'} "
            f"image_topic={image_topic} info_topic={info_topic}"
        )

    def target_id_cb(self, msg: Int32):
        self.target_id = msg.data
        if self.target_id >= 0:
            self.get_logger().info(f"Target marker set to id {self.target_id}")
        else:
            self.get_logger().info("Target marker cleared - no marker will be followed")

    def info_cb(self, msg: CameraInfo):
        self.camera_matrix = np.array(msg.k, dtype=np.float64).reshape(3, 3)
        self.dist_coeffs = np.array(msg.d, dtype=np.float64)

    def image_cb(self, msg: Image):
        if self.camera_matrix is None:
            self.get_logger().warn(
                "No CameraInfo received yet - skipping detection until intrinsics arrive.",
                throttle_duration_sec=5.0
            )
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        corners, ids, _ = cv2.aruco.detectMarkers(
            gray,
            self.aruco_dict,
            parameters=self.aruco_params
        )

        found = False

        if ids is not None:
            ids_flat = ids.flatten()
            target_indices = [i for i, mid in enumerate(ids_flat)
                               if self.target_id >= 0 and mid == self.target_id]
            other_indices = [i for i in range(len(ids_flat)) if i not in target_indices]

            if self.publish_debug:
                if other_indices:
                    cv2.aruco.drawDetectedMarkers(
                        frame, [corners[i] for i in other_indices], ids[other_indices], borderColor=RED
                    )
                if target_indices:
                    cv2.aruco.drawDetectedMarkers(
                        frame, [corners[i] for i in target_indices], ids[target_indices], borderColor=GREEN
                    )

            if target_indices:
                idx = target_indices[0]
                marker_corners = corners[idx]

                ok, rvec, tvec = cv2.solvePnP(
                    self.obj_points, marker_corners[0],
                    self.camera_matrix, self.dist_coeffs
                )

                if ok:
                    found = True
                    distance = float(np.linalg.norm(tvec))

                    pose_msg = PoseStamped()
                    pose_msg.header = msg.header
                    pose_msg.pose.position.x = float(tvec[0])
                    pose_msg.pose.position.y = float(tvec[1])
                    pose_msg.pose.position.z = float(tvec[2])
                    qx, qy, qz, qw = rvec_to_quaternion(rvec)
                    pose_msg.pose.orientation.x = qx
                    pose_msg.pose.orientation.y = qy
                    pose_msg.pose.orientation.z = qz
                    pose_msg.pose.orientation.w = qw
                    self.pose_pub.publish(pose_msg)

                    self.dist_pub.publish(Float32(data=distance))

                    if self.publish_debug:
                        cv2.drawFrameAxes(
                            frame, self.camera_matrix, self.dist_coeffs,
                            rvec, tvec, self.marker_size * 0.5
                        )
                        cv2.putText(
                            frame, f"TARGET id={int(ids_flat[idx])} dist={distance:.2f}m",
                            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, GREEN, 2
                        )

        self.detected_pub.publish(Bool(data=found))

        if self.publish_debug:
            debug_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            debug_msg.header = msg.header
            self.debug_pub.publish(debug_msg)


def main(args=None):
    rclpy.init(args=args)
    node = ArucoDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()