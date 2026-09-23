# aruco_follower

A ROS 2 package for detecting ArUco markers, selecting a target among them, estimating that target's pose and distance from a calibrated camera, and generating proportional visual-servoing velocity commands to drive a differential-drive robot toward it.

The package can see and report on every ArUco marker in view, but only one is ever designated the *active target*: the marker actually used for pose estimation and following. Target selection can be changed at runtime, either from a terminal or from a browser with optional natural-language parsing.

---

## Contents

- [Nodes](#nodes)
- [Detection Pipeline](#detection-pipeline)
- [Topics](#topics)
- [Parameters](#parameters)
- [Target Selection](#target-selection)
- [Web Commander](#web-commander)
- [Build](#build)
- [Run](#run)
- [Notes on Accuracy](#notes-on-accuracy)

---

## Nodes

| Node | Executable | Purpose |
|---|---|---|
| ArUco Detector | `aruco_detector` | Detects ArUco markers in the camera image, estimates the active target's pose with `solvePnP()`, publishes its distance and visibility, and produces an annotated debug image. |
| Marker Follower | `marker_follower` | Converts the active target's pose into `TwistStamped` velocity commands via proportional visual servoing. |
| Target Commander | `set_target_marker` | Terminal interface for selecting or clearing the active target marker. |
| Web Commander | `web_target_commander` | Browser-based command interface with a live debug-video stream and optional Gemini natural-language command parsing. |

---

## Detection Pipeline

```text
Camera Image + CameraInfo
          │
          ▼
    aruco_detector
          │
          ├── /aruco/marker_pose
          ├── /aruco/distance
          ├── /aruco/detected
          └── /aruco/debug_image
          │
          ▼
    marker_follower
          │
          ▼
 /cmd_vel_nav_stamped
```

The detector waits for valid intrinsics from `CameraInfo` before attempting pose estimation — without a camera calibration, no pose is published. By default it looks for markers from the `DICT_5X5_100` dictionary with a physical side length of `0.10 m`; both are configurable per marker set.

---

## Topics

### `aruco_detector` — subscribes

| Topic | Type |
|---|---|
| `/camera/image_raw` | `sensor_msgs/msg/Image` |
| `/camera/camera_info` | `sensor_msgs/msg/CameraInfo` |
| `/aruco/target_marker_id` | `std_msgs/msg/Int32` |

### `aruco_detector` — publishes

| Topic | Type |
|---|---|
| `/aruco/marker_pose` | `geometry_msgs/msg/PoseStamped` |
| `/aruco/distance` | `std_msgs/msg/Float32` |
| `/aruco/detected` | `std_msgs/msg/Bool` |
| `/aruco/debug_image` | `sensor_msgs/msg/Image` |

### `marker_follower` — publishes

| Topic | Type |
|---|---|
| `/cmd_vel_nav_stamped` | `geometry_msgs/msg/TwistStamped` |

This topic is intended to feed the `navigation` input of `twist_mux`, so autonomous following can be arbitrated against other velocity sources (e.g. a joystick) rather than driving the robot directly.

---

## Parameters

### `aruco_detector`

| Parameter | Default | Description |
|---|---:|---|
| `image_topic` | `/camera/image_raw` | Camera image topic to subscribe to |
| `camera_info_topic` | `/camera/camera_info` | Camera calibration topic |
| `marker_size` | `0.10` m | Physical side length of the marker |
| `aruco_dictionary` | `DICT_5X5_100` | OpenCV ArUco dictionary to detect against |
| `target_marker_id` | `-1` | Initial active target; `-1` means none selected |
| `publish_debug_image` | `true` | Publish the annotated camera output |

### `marker_follower`

| Parameter | Default | Description |
|---|---:|---|
| `target_distance` | `0.5` m | Desired standoff distance from the marker |
| `kp_linear` | `0.6` | Proportional gain, linear velocity |
| `kp_angular` | `1.2` | Proportional gain, angular velocity |
| `max_linear` | `0.18` m/s | Linear velocity limit |
| `max_angular` | `0.45` rad/s | Angular velocity limit |
| `distance_deadband` | `0.03` m | Distance error below which linear command is zeroed |
| `heading_deadband` | `0.03` rad | Heading error below which angular command is zeroed |
| `marker_timeout` | `0.5` s | Time since last detection after which the robot stops |
| `control_rate` | `20` Hz | Control-loop frequency |
| `cmd_frame_id` | `base_link` | Frame ID stamped on outgoing velocity commands |

If the target hasn't been seen within `marker_timeout`, `marker_follower` publishes a zero-velocity command rather than acting on stale pose data.

---

## Target Selection

### Terminal

```bash
ros2 run aruco_follower set_target_marker
```

```text
target marker id> 2     # follow marker ID 2
target marker id> -1    # clear the target
target marker id> q     # exit
```

The commanded ID is published on `/aruco/target_marker_id` using transient-local QoS, so a detector started afterward still picks up the last-selected target.

The active target is highlighted in **green** in the debug image; every other detected marker is shown in **red**.

---

## Web Commander

Install the required Python packages:

```bash
sudo apt install python3-flask python3-requests
```

Optional Gemini natural-language support:

```bash
export GEMINI_API_KEY="your-api-key"
```

Run:

```bash
ros2 run aruco_follower web_target_commander
```

Then open `http://<robot-ip>:5000` from any device on the same network. The interface streams the annotated debug video and accepts commands such as:

```text
follow marker 2
track id 4
stop following
```

Commands are published to the same `/aruco/target_marker_id` topic used by `set_target_marker`.

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Enables natural-language command parsing via the Gemini API |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model used for parsing |
| `WEB_PORT` | `5000` | Port the web server listens on |
| `CAMERA_TOPIC` | `/aruco/debug_image` | Topic streamed to the browser |

If the Gemini API is unavailable or no key is set, the node falls back to a local keyword/regular-expression parser, so the web interface stays functional without network access.

---

## Build

From the ROS 2 workspace root:

```bash
colcon build --packages-select aruco_follower
source install/setup.bash
```

---

## Run

Start the detector:

```bash
ros2 run aruco_follower aruco_detector
```

Start the follower:

```bash
ros2 run aruco_follower marker_follower
```

Then select a target with either `set_target_marker` or the web commander described above. With a target selected and visible, the detector begins publishing pose data and the follower begins issuing velocity commands.

---

## Notes on Accuracy

Pose and distance estimation depend entirely on a properly calibrated camera — `aruco_detector` uses the camera matrix and distortion coefficients published on `CameraInfo` for `solvePnP()`. An uncalibrated or poorly calibrated camera will produce inaccurate pose estimates even when detection itself succeeds. Marker size should also match `marker_size` exactly, since it directly scales the estimated distance.
