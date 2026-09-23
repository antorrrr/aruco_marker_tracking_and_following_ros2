# robot_control_pkg

A ROS 2 hardware and bringup package for a differential-drive mobile robot, built on `ros2_control` with a custom hardware interface that talks to an Arduino-based motor and encoder controller over serial.

The package covers the full bringup for the physical robot: the URDF/Xacro description, the `ros2_control` hardware plugin, controller configuration, joystick teleoperation, camera launch files, and a combined real-robot launch that brings up drive, sensing, and lidar together.

---

## Contents

- [Architecture](#architecture)
- [Main Components](#main-components)
- [Launch Files](#launch-files)
- [Hardware Interface](#hardware-interface)
- [Serial Protocol](#serial-protocol)
- [Controller Configuration](#controller-configuration)
- [Command Multiplexing](#command-multiplexing)
- [Build](#build)
- [Hardware Notes](#hardware-notes)

---

## Architecture

```text
ROS 2 velocity command
        │
        ▼
     twist_mux
   ┌────┴─────┐
   │          │
Joystick   Navigation
   │          │
   └────┬─────┘
        ▼
 diff_controller
        │
        ▼
 ros2_control
        │
 RobotControlHardware
        │
      Serial
        │
        ▼
 Arduino motor controller
        │
   ┌────┴────┐
 Motors    Encoders
   │          │
   └────┬─────┘
        ▼
   Encoder feedback
```

`twist_mux` sits upstream of the controller so manually-driven joystick input and autonomous navigation/follower commands can share the same robot without conflicting — see [Command Multiplexing](#command-multiplexing) for priorities. Encoder feedback closes the loop back into `ros2_control`'s state interfaces, so the rest of the ROS 2 stack (odometry, controllers, diagnostics) sees real wheel state rather than open-loop commands.

---

## Main Components

| Directory | Contents |
|---|---|
| `bringup/` | Launch files and YAML controller configuration |
| `description/` | URDF/Xacro robot description, meshes, and `ros2_control` hardware description |
| `hardware/` | C++ `ros2_control` hardware plugin and Arduino serial communication layer |
| `doc/` | Package documentation and robot reference image |

---

## Launch Files

### Main robot control

```bash
ros2 launch robot_control_pkg diffbot.launch.py
```

Brings up the core control stack:

- `ros2_control_node`
- `robot_state_publisher`
- `joint_state_broadcaster`
- `diff_controller`
- `twist_mux`

### Joystick teleoperation

```bash
ros2 launch robot_control_pkg joystick.launch.py
```

Starts `joy_node` and `teleop_twist_joy`. Joystick output is published on `cmd_vel_joy`.

### Camera

Two camera backends are provided depending on what's available on the target hardware:

```bash
# libcamera-based, via camera_ros
ros2 launch robot_control_pkg cam_launch.py

# V4L2-based (standard USB webcams)
ros2 launch robot_control_pkg camera_launch.py
```

### Real robot (full bringup)

```bash
ros2 launch robot_control_pkg real_robot_launch.py
```

Combines the differential-drive bringup with the RPLiDAR A2M8 driver launch, so a single command brings the physical robot to a fully sensed, drivable state.

---

## Hardware Interface

The custom `ros2_control` plugin is exported as:

```text
robot_control_pkg/RobotControlHardware
```

It implements the `hardware_interface::SystemInterface` lifecycle and exports:

- Velocity **command** interfaces for the left and right wheels
- Position **state** interfaces
- Velocity **state** interfaces

**Default hardware configuration (Xacro):**

| Setting | Value |
|---|---|
| Serial device | `/dev/ttyUSB0` |
| Baud rate | `57600` |
| Loop rate | `30` Hz |
| Encoder counts / revolution | `5903` |
| PID P | `2.55` |
| PID I | `2.15` |
| PID D | `0.35` |

These values are specific to the current motor-controller firmware and encoder hardware and should be re-tuned if either changes.

---

## Serial Protocol

The Arduino communication layer (`arduino_comms`) uses LibSerial to exchange short ASCII commands with the motor-controller firmware. Commands implemented by the hardware interface include:

| Command | Effect |
|---|---|
| `e` | Request current encoder values |
| `m <left> <right>` | Set left/right motor output |
| PID command | Send updated PID gains to the firmware |

The exact wire format must match what the Arduino firmware expects — see `arduino_comms.hpp` for the authoritative implementation.

---

## Controller Configuration

The differential-drive controller is configured with:

| Parameter | Value |
|---|---|
| Left wheel joint | `LeftWheel_joint` |
| Right wheel joint | `RightWheel_joint` |
| Wheel separation | `0.178` m |
| Wheel radius | `0.02254` m |
| Base frame | `base_link` |

Full configuration lives in `bringup/config/diffbot_controllers.yaml`.

---

## Command Multiplexing

`twist_mux` merges two velocity sources by priority:

| Source | Topic | Priority |
|---|---|---|
| Navigation / marker follower | `cmd_vel_nav_stamped` | `10` |
| Joystick | `cmd_vel_joy` | `100` |

The joystick takes priority over autonomous commands whenever it's actively publishing, giving an operator a reliable manual override during autonomous operation.

---

## Build

Install the required ROS 2 packages and LibSerial, then build from the workspace root:

```bash
colcon build --packages-select robot_control_pkg
source install/setup.bash
```

The package links against LibSerial at build time and depends on the standard `ros2_control` hardware-interface packages.

---

## Hardware Notes

Before running on the physical robot:

1. Confirm the Arduino is connected and enumerated at the expected serial device.
2. Verify `/dev/ttyUSB0` is correct, or update the Xacro configuration to match the actual device.
3. Confirm the Arduino firmware implements the same serial command protocol the hardware interface expects.
4. Double-check wheel joint names and the encoder-counts-per-revolution value against the actual hardware.
5. Verify emergency-stop and manual joystick control both work before enabling autonomous operation.
