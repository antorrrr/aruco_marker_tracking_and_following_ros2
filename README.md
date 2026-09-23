# ArUco Marker Tracking and Following with ROS 2

A ROS 2 autonomous mobile robot system that detects, identifies, and visually tracks a user-selected ArUco marker, then follows it using closed-loop proportional visual servoing on a differential-drive platform — in simulation and on physical hardware.

**Author:** Antor Mondal · Mechatronics Engineering, Khulna University of Engineering & Technology (KUET)
**Repository:** https://github.com/antorrrr/aruco_marker_tracking_and_following_ros2

---

## Overview

Marker-based following is a common building block in mobile robotics — leader-follower formations, automated guided vehicles (AGVs) tracking a fiducial on a cart, and human-following demonstrations all reduce to the same core problem: detect a known visual target, estimate where it is relative to the robot, and drive toward it while it stays in view.

This project implements that pipeline end to end in ROS 2:

- **Perception** — OpenCV ArUco detection with 6-DoF pose estimation via `solvePnP()`, using calibrated camera intrinsics from `CameraInfo`.
- **Target selection** — the detector can see multiple markers simultaneously, but only one is designated the active target at a time. Selection happens over a terminal command, or a web interface with optional natural-language parsing through the Gemini API.
- **Control** — a proportional visual-servoing controller converts marker pose into `TwistStamped` velocity commands, with deadbands, velocity limits, and a stale-detection timeout for safety.
- **Actuation** — a custom `ros2_control` hardware interface talks to an Arduino-based motor controller over serial, closing the loop with wheel encoder feedback.
- **Simulation** — a Gazebo Sim warehouse environment lets the full stack (detector → follower → `twist_mux` → diff-drive controller) run and be validated before touching physical hardware.

The system is intentionally modular: perception, control, simulation, and message conversion are separate ROS 2 packages, so each layer can be developed, tested, and swapped independently.

```
Camera
  │
  ▼
ArUco Detector ──── Marker ID, Pose, Distance, Detection Status
  │
  ▼
Marker Follower ──── TwistStamped velocity command
  │
  ▼
twist_mux
  │
  ▼
Differential Drive Controller
  │
  ▼
Robot Hardware (Arduino / Motors)
```

The currently selected marker is drawn in **green** in the debug image; every other detected marker is drawn in **red**.

---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [Packages](#packages)
3. [Perception: `aruco_detector`](#perception-aruco_detector)
4. [Control: `marker_follower`](#control-marker_follower)
5. [Target Selection](#target-selection)
6. [Hardware Interface](#hardware-interface)
7. [Simulation](#simulation)
8. [ROS 2 Topic Interface](#ros-2-topic-interface)
9. [Installation](#installation)
10. [Running the System](#running-the-system)
11. [Configuration Reference](#configuration-reference)
12. [Safety Behavior](#safety-behavior)
13. [Troubleshooting](#troubleshooting)
14. [Requirements](#requirements)
15. [Development Notes](#development-notes)
16. [License](#license)

---

## Repository Structure

```text
aruco_marker_tracking_and_following_ros2/
│
├── aruco_follower/                  # Perception + target following (Python, ament_python)
│   ├── aruco_follower/
│   │   ├── aruco_detector.py        # Marker detection & pose estimation
│   │   ├── marker_follower.py       # Visual servoing controller
│   │   ├── set_target_marker.py     # Terminal target selector
│   │   └── web_target_commander.py  # Web / NL target selector
│   ├── resource/aruco_follower
│   ├── package.xml
│   ├── setup.py
│   └── setup.cfg
│
├── robot_control_pkg/                # ros2_control hardware interface (C++)
│   ├── hardware/
│   │   ├── include/robot_control_pkg/
│   │   │   ├── arduino_comms.hpp
│   │   │   ├── diffbot_system.hpp
│   │   │   ├── visibility_control.h
│   │   │   └── wheel.hpp
│   │   └── diffbot_system.cpp
│   ├── launch/
│   ├── config/
│   ├── description/
│   ├── package.xml
│   ├── CMakeLists.txt
│   └── robot_control_pkg.xml
│
├── sim_pkg/                           # Gazebo Sim warehouse simulation
│   ├── launch/sim_launch.py
│   ├── models/ description/
│   ├── worlds/industrial-warehouse.sdf
│   ├── params/ config/ resource/sim_pkg
│   ├── package.xml
│   └── setup.py
│
├── twist_stamper-main/                # Twist <-> TwistStamped conversion utility
│   ├── package.xml
│   └── README.md
│
├── dict_probe.py                      # ArUco dictionary identification tool
└── README.md
```

---

## Packages

| Package | Language | Responsibility |
|---|---|---|
| `aruco_follower` | Python (`ament_python`) | ArUco detection, pose estimation, target selection, visual servoing |
| `robot_control_pkg` | C++ | `ros2_control` hardware interface, serial communication with Arduino, encoder feedback |
| `sim_pkg` | Python / SDF | Gazebo Sim warehouse world, robot spawning, sensor & controller bridging |
| `twist_stamper` | Python | Converts between `geometry_msgs/Twist` and `geometry_msgs/TwistStamped` |

### `aruco_follower` nodes

| Node | Executable | Purpose |
|---|---|---|
| ArUco Detector | `aruco_detector` | Detects markers, estimates 6-DoF pose of the active target |
| Marker Follower | `marker_follower` | Converts target pose into `TwistStamped` velocity commands |
| Target Commander | `set_target_marker` | Selects the active marker from a terminal prompt |
| Web Commander | `web_target_commander` | Selects the active marker from a browser, optionally via natural language |

**Core dependencies:** `rclpy`, `sensor_msgs`, `geometry_msgs`, `std_msgs`, `cv_bridge`, OpenCV (with `contrib`/ArUco support).

---

## Perception: `aruco_detector`

**Subscribes:**

```text
/camera/image_raw          (sensor_msgs/Image)
/camera/camera_info        (sensor_msgs/CameraInfo)
/aruco/target_marker_id    (std_msgs/Int32)
```

**Publishes:**

```text
/aruco/marker_pose         (geometry_msgs/PoseStamped)
/aruco/distance             (std_msgs/Float32)
/aruco/detected              (std_msgs/Bool)
/aruco/debug_image          (sensor_msgs/Image)
```

**Pipeline:**

1. Receive a camera frame and convert it to grayscale.
2. Detect ArUco markers in the frame.
3. Compare detected IDs against the currently selected target ID.
4. Draw the target marker in green; draw every other detected marker in red.
5. Wait for valid camera intrinsics (`CameraInfo`) before attempting pose estimation.
6. Estimate the target's 6-DoF pose with `solvePnP()` using the configured physical marker size.
7. Convert the resulting rotation vector to a quaternion.
8. Publish pose, straight-line distance, and detection status.
9. Publish an annotated debug image for visualization and debugging.

A `target_marker_id` of `-1` means no marker is currently selected, and the detector publishes `detected = false`.

**Key parameters:**

| Parameter | Default | Description |
|---|---|---|
| `image_topic` | `/camera/image_raw` | Source camera stream |
| `camera_info_topic` | `/camera/camera_info` | Calibration source for `solvePnP()` |
| `marker_size` | `0.10` m | Physical side length of the marker |
| `aruco_dictionary` | `DICT_5X5_100` | ArUco dictionary to detect against |
| `target_marker_id` | `-1` | Active target ID (`-1` = none) |
| `publish_debug_image` | `true` | Toggle annotated debug image publishing |

---

## Control: `marker_follower`

This node performs proportional visual servoing: it converts the target marker's pose into robot velocity commands, running at a fixed control rate.

**Subscribes:** `/aruco/marker_pose`, `/aruco/detected`
**Publishes:** `/cmd_vel_nav_stamped` (`geometry_msgs/TwistStamped`)

### Control law

The camera's optical frame is treated with `x` = horizontal offset, `y` = vertical offset, `z` = forward distance to the marker.

**Heading error** (angle between the robot's forward axis and the marker):

```text
heading_error = atan2(x, z)
```

**Angular command** (proportional control, negative feedback):

```text
angular_cmd = -kp_angular × heading_error
```

**Distance error** (how far the robot is from the desired standoff distance):

```text
distance_error = z - target_distance
```

**Linear command:**

```text
linear_cmd = kp_linear × distance_error
```

Both commands are clamped to configurable maximum velocities, and small errors within a deadband are treated as zero to prevent jitter around the setpoint.

**Key parameters:**

| Parameter | Default | Description |
|---|---|---|
| `target_distance` | `0.5` m | Desired standoff distance from the marker |
| `kp_linear` | `0.6` | Proportional gain, linear velocity |
| `kp_angular` | `1.2` | Proportional gain, angular velocity |
| `max_linear` | `0.18` m/s | Linear velocity limit |
| `max_angular` | `0.45` rad/s | Angular velocity limit |
| `distance_deadband` | `0.03` m | Distance error below which linear command is zeroed |
| `heading_deadband` | `0.03` rad | Heading error below which angular command is zeroed |
| `marker_timeout` | `0.5` s | Max age of a detection before it's considered stale |
| `control_rate` | `20` Hz | Controller update rate |
| `cmd_frame_id` | `base_link` | Frame ID stamped on outgoing commands |

If the marker hasn't been seen within `marker_timeout`, the node publishes a zero-velocity command rather than continuing to act on stale visual information.

---

## Target Selection

### Terminal (`set_target_marker`)

```bash
ros2 run aruco_follower set_target_marker
```

```text
target marker id> 2     # follow marker ID 2
target marker id> -1    # clear the target
target marker id> q     # exit
```

The target ID is published to `/aruco/target_marker_id` using **transient-local QoS**, so a detector node started after the target was set still receives the last commanded value.

### Web interface (`web_target_commander`)

```bash
ros2 run aruco_follower web_target_commander
```

Then open `http://<robot-ip>:5000` from a device on the same network.

This node runs a Flask server, an MJPEG stream of the annotated camera feed, and a command interface that accepts phrases such as:

```text
follow marker 2
track id 4
stop following
```

Commands are published to the same `/aruco/target_marker_id` topic.

**Optional natural-language parsing (Gemini API):**

```bash
export GEMINI_API_KEY="your-api-key"
```

| Env var | Default |
|---|---|
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `WEB_PORT` | `5000` |
| `CAMERA_TOPIC` | `/aruco/debug_image` |

If the Gemini API is unreachable or no key is set, the commander falls back to a local keyword/regex parser, so the web interface remains functional offline.

---

## Hardware Interface

`robot_control_pkg` implements a custom `hardware_interface::SystemInterface` (`RobotControlHardware`), exported via `pluginlib` as `robot_control_pkg/RobotControlHardware`.

**Responsibilities:**
- Initialize hardware parameters and validate wheel interfaces
- Export velocity command interfaces and position/velocity state interfaces
- Open and manage the serial connection to the Arduino
- Read raw encoder counts and convert them to wheel position and velocity
- Convert `ros2_control` velocity commands into motor commands
- Apply configured PID gains on the motor controller

**Configuration (`diffbot_system.hpp`):**

```text
left_wheel_name    right_wheel_name
device             loop_rate
baud_rate          timeout_ms
enc_counts_per_rev
pid_p  pid_d  pid_i
```

**Supporting components:**
- `arduino_comms.hpp` — serial connect/disconnect, encoder reads, motor command writes, PID parameter writes
- `wheel.hpp` — per-wheel state (name, encoder count, position, velocity, command) and encoder-to-angle conversion

**Hardware data path:**

```text
ros2_control → diff_drive_controller → RobotControlHardware → Serial → Arduino → Motor Driver → Motors
                                                                              └→ Encoders → Feedback
```

---

## Simulation

`sim_pkg` launches a Gazebo Sim warehouse environment for validating the full stack before deployment to hardware.

```bash
ros2 launch sim_pkg sim_launch.py
```

**`sim_launch.py` starts, in order:**

1. `robot_state_publisher` (from the robot's Xacro description)
2. Gazebo Sim, loading `industrial-warehouse.sdf`
3. Robot spawn (approximately at `x=0, y=0, z=1.4`)
4. `ros_gz_bridge` (parameter/topic bridge) and `ros_gz_image` (camera bridge)
5. Joint State Broadcaster
6. Differential Drive Controller
7. `twist_mux`

Simulation time is enabled by default.

The warehouse world (`industrial-warehouse.sdf`) includes shelves, walls, ground, clutter, a pallet jack, a trash can, and lighting, with several models pulled from Gazebo Fuel — an internet connection may be required the first time uncached models are loaded.

---

## ROS 2 Topic Interface

| Topic | Type | Direction |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | Input |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | Input |
| `/aruco/target_marker_id` | `std_msgs/Int32` | Input (target selection) |
| `/aruco/marker_pose` | `geometry_msgs/PoseStamped` | Output (detector) |
| `/aruco/distance` | `std_msgs/Float32` | Output (detector) |
| `/aruco/detected` | `std_msgs/Bool` | Output (detector) |
| `/aruco/debug_image` | `sensor_msgs/Image` | Output (detector) |
| `/cmd_vel_nav_stamped` | `geometry_msgs/TwistStamped` | Output (follower) |

---

## Installation

**Target platform:** Ubuntu 24.04, ROS 2 Jazzy

```bash
# Create (or reuse) a workspace
mkdir -p ~/amr_robot/src
cd ~/amr_robot/src

# Clone the repository
git clone https://github.com/antorrrr/aruco_marker_tracking_and_following_ros2.git

# Install dependencies
cd ~/amr_robot
rosdep install --from-paths src --ignore-src -r -y

# Build
colcon build

# Source
source install/setup.bash
```

For every new terminal:

```bash
source /opt/ros/jazzy/setup.bash
source ~/amr_robot/install/setup.bash
```

---

## Running the System

### Simulation, step by step

```bash
# Terminal 1 — environment
source /opt/ros/jazzy/setup.bash
source ~/amr_robot/install/setup.bash

# Terminal 2 — simulation
ros2 launch sim_pkg sim_launch.py

# Terminal 3 — perception
ros2 run aruco_follower aruco_detector

# Terminal 4 — target selection
ros2 run aruco_follower set_target_marker
# then enter a marker ID, e.g. 2

# Terminal 5 — control
ros2 run aruco_follower marker_follower
```

**Resulting data flow:**

```text
Camera → ArUco Detection → Target Marker Pose → Visual Servoing →
TwistStamped → twist_mux → Differential Drive Controller → Robot
```

### Sanity checks

```bash
ros2 topic list | grep camera
ros2 topic hz /camera/image_raw
ros2 topic list | grep aruco
ros2 topic echo /aruco/detected
ros2 topic echo /aruco/marker_pose
ros2 topic echo /aruco/distance
```

### Command arbitration (`twist_mux`)

`twist_mux` arbitrates between multiple velocity sources so manual joystick control and autonomous marker-following can coexist with configurable priority:

```text
Joystick ───┐
            ├──► twist_mux ──► Robot Controller
Marker Follower ─┘
```

### Physical hardware

The onboard computer runs the full ROS 2 stack; the Arduino handles low-level motor and encoder I/O over serial. The command path is:

```text
ROS 2 → diff_drive_controller → ros2_control → RobotControlHardware
      → Serial → Arduino → Motor Driver / Encoders
```

---

## Configuration Reference

**ArUco detector:** `marker_size`, `aruco_dictionary`, `image_topic`, `camera_info_topic`, `target_marker_id`, `publish_debug_image`

**Marker follower:** `target_distance`, `kp_linear`, `kp_angular`, `max_linear`, `max_angular`, `distance_deadband`, `heading_deadband`, `marker_timeout`, `control_rate`

Tune the control parameters to match the robot's actual wheel configuration, camera mounting position, motor response characteristics, and operating environment. Start with conservative gains and velocity limits in simulation before transferring settings to hardware.

---

## Safety Behavior

The follower includes a marker-timeout watchdog: if the target hasn't been detected within `marker_timeout` (default `0.5` s), it publishes a zero-velocity command rather than acting on stale pose data. Maximum linear and angular velocities are also enforced independently of the timeout, bounding worst-case robot speed regardless of controller gains.

---

## Troubleshooting

**ArUco marker not detected**
- Confirm the camera is publishing: `ros2 topic hz /camera/image_raw`
- Run `python3 dict_probe.py` to identify which ArUco dictionary the physical marker actually uses
- Check that the marker is visible, adequately lit, in focus, and not heavily distorted or occluded
- Verify `aruco_dictionary` and `marker_size` are configured correctly

**Pose estimation looks wrong**
- Pose accuracy depends on accurate camera intrinsics from `/camera/camera_info` — verify with `ros2 topic echo /camera/camera_info`
- Re-check the calibration if the camera or lens has changed

**Robot doesn't move**
- `ros2 topic echo /aruco/detected` — if `false`, the follower is intentionally holding zero velocity
- `ros2 topic echo /aruco/marker_pose` — confirm pose data is being published
- `ros2 topic echo /cmd_vel_nav_stamped` — confirm the follower is issuing commands
- Confirm `twist_mux` isn't giving priority to a different (silent) input source

**No target marker selected**
- `ros2 topic echo /aruco/target_marker_id` to check the current target
- Set one manually if needed:
  ```bash
  ros2 topic pub --once /aruco/target_marker_id std_msgs/msg/Int32 "{data: 2}"
  ```

---

## Requirements

**Software:** Ubuntu 24.04 · ROS 2 Jazzy · Python 3 · OpenCV with ArUco support · Gazebo Sim · `ros_gz` · ROS 2 Control · Nav2 · SLAM Toolbox · RPLIDAR ROS 2 driver · `twist_mux` · `cv_bridge`

**Hardware (physical robot):** Arduino-based motor controller · serial connection · wheel encoders · differential-drive motor pair · motor driver

---

## Development Notes

The system is deliberately split into independently buildable and testable packages:

- **Perception** — `aruco_follower`
- **Hardware interface** — `robot_control_pkg`
- **Simulation** — `sim_pkg`
- **Message conversion** — `twist_stamper`
- **Diagnostics** — `dict_probe.py`

This separation allows the perception and control pipeline to be developed and validated entirely in simulation before any physical hardware is connected, and lets individual layers (e.g., swapping the hardware interface for a different drive base) be replaced without touching the perception or control code.

**Project status:** experimental research implementation, structured to support further work in autonomous marker following, visual servoing, mobile robot navigation, camera-based localization, and simulation-to-hardware transfer.

---

## License

Individual packages are released under the Apache License 2.0 where specified in their package metadata. See each package's `package.xml` / `CMakeLists.txt` for exact licensing and attribution details.
