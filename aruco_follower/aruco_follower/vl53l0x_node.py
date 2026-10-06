#!/usr/bin/env python3
"""
vl53l0x_node.py

Reads the VL53L0X time-of-flight distance sensor over I2C and publishes
sensor_msgs/Range on /tof/range.

Wiring (Raspberry Pi 40-pin header):
    VL53L0X VIN -> Pi pin 1  (3.3V)
    VL53L0X GND -> Pi pin 6  (GND)
    VL53L0X SDA -> Pi pin 3  (GPIO2 / SDA1)
    VL53L0X SCL -> Pi pin 5  (GPIO3 / SCL1)

Requires I2C enabled (raspi-config -> Interface Options -> I2C) and the
sensor detected at the default address 0x29 (check with `i2cdetect -y 1`).

Dependencies:
    pip install --break-system-packages adafruit-circuitpython-vl53l0x adafruit-blinka

VL53L0X specs used for the Range message:
    field_of_view ~= 25 degrees (0.436 rad) — narrow cone, no lateral info
    min_range = 0.03 m (below this the sensor is unreliable)
    max_range = 1.2 m in default mode (can extend to ~2m in long-range mode,
                not used here for simplicity/stability)
"""

import math

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Range

try:
    import board
    import busio
    import adafruit_vl53l0x
    HARDWARE_AVAILABLE = True
except (ImportError, NotImplementedError):
    HARDWARE_AVAILABLE = False


class VL53L0XNode(Node):

    def __init__(self):
        super().__init__('vl53l0x_node')

        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('frame_id', 'tof_link')
        self.declare_parameter('zero_above_range', 1.2)  # meters — readings above this publish as 0.0

        rate_hz = self.get_parameter('publish_rate_hz').value
        self.frame_id = self.get_parameter('frame_id').value
        self.zero_above_range = self.get_parameter('zero_above_range').value
        self.add_on_set_parameters_callback(self._on_param_change)

        if not HARDWARE_AVAILABLE:
            raise RuntimeError(
                "adafruit-circuitpython-vl53l0x / board / busio not available. "
                "Install with: pip install --break-system-packages adafruit-circuitpython-vl53l0x adafruit-blinka "
                "and make sure this is running on the actual Pi with I2C enabled."
            )

        i2c = busio.I2C(board.SCL, board.SDA)
        self.sensor = adafruit_vl53l0x.VL53L0X(i2c)

        self.range_pub = self.create_publisher(Range, '/tof/range', 10)

        period = 1.0 / rate_hz
        self.timer = self.create_timer(period, self._publish_range)

        self.get_logger().info(f"vl53l0x_node up | publishing /tof/range at {rate_hz} Hz")

    def _on_param_change(self, params):
        from rcl_interfaces.msg import SetParametersResult
        for p in params:
            if p.name == 'zero_above_range':
                self.zero_above_range = p.value
                self.get_logger().info(f"zero_above_range live-updated to {p.value}")
        return SetParametersResult(successful=True)

    def _publish_range(self):
        try:
            distance_mm = self.sensor.range
        except Exception as e:
            self.get_logger().warn(f"VL53L0X read failed: {e}", throttle_duration_sec=2.0)
            return

        distance_m = distance_mm / 1000.0

        if distance_m > self.zero_above_range:
            distance_m = 0.0

        msg = Range()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.radiation_type = Range.INFRARED
        msg.field_of_view = math.radians(25.0)
        msg.min_range = 0.03
        msg.max_range = 1.2
        msg.range = distance_m
        self.range_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = VL53L0XNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
