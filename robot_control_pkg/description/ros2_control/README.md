# ros2_control description

`diffbot.ros2_control.xacro` declares the `ros2_control` hardware interface for the physical robot — binding the custom `RobotControlHardware` plugin to the wheel joints defined in `urdf/`, and configuring the serial connection and PID gains it uses to talk to the Arduino motor controller.

This file is included by the main robot Xacro and is read at launch time by `ros2_control_node` (see `bringup/launch/diffbot.launch.py`) to instantiate the hardware interface.

## Hardware Plugin

```text
robot_control_pkg/RobotControlHardware
```

Implemented in `robot_control_pkg/hardware/diffbot_system.cpp`; see the package-level README for what the plugin does internally.

## Hardware Parameters

| Parameter | Value | Description |
|---|---|---|
| Left wheel joint | `LeftWheel_joint` | Joint driven by the left motor |
| Right wheel joint | `RightWheel_joint` | Joint driven by the right motor |
| Serial device | `/dev/ttyUSB0` | Arduino serial port |
| Baud rate | `57600` | Serial communication speed |
| Loop rate | `30` Hz | Hardware read/write update rate |
| Encoder counts / revolution | `5903` | Used to convert raw encoder counts to wheel position |
| PID P | `2.55` | Proportional gain, sent to the Arduino firmware |
| PID I | `2.15` | Integral gain, sent to the Arduino firmware |
| PID D | `0.35` | Derivative gain, sent to the Arduino firmware |

Both `LeftWheel_joint` and `RightWheel_joint` expose a velocity **command** interface plus position and velocity **state** interfaces, which is what allows `diff_controller` to both drive the wheels and read back their actual motion.

## Notes

- The serial device path (`/dev/ttyUSB0`) is not guaranteed to be stable across reboots on some systems — if the Arduino enumerates on a different port, update this file (or set up a udev rule for a persistent device name) before launching.
- PID values here are firmware-side gains sent to the Arduino, not ROS 2 controller gains — they should be tuned against the actual motor/encoder hardware, not assumed to transfer between robots.
