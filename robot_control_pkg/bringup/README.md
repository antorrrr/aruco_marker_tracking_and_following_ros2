# bringup

Launch and configuration files for starting the physical robot and its supporting interfaces — drive control, joystick teleoperation, camera, and lidar.

## Subdirectories

| Directory | Contents |
|---|---|
| `launch/` | ROS 2 launch files for drive control, joystick, camera, and full-robot bringup |
| `config/` | YAML configuration for the differential-drive controller, joystick mapping, and `twist_mux` velocity multiplexing |

## Launch Files

| File | Starts |
|---|---|
| `diffbot.launch.py` | Core drive stack — `ros2_control_node`, `robot_state_publisher`, `joint_state_broadcaster`, `diff_controller`, `twist_mux` |
| `joystick.launch.py` | `joy_node` and `teleop_twist_joy` for manual teleoperation |
| `cam_launch.py` | Camera via `camera_ros` (libcamera-based) |
| `camera_launch.py` | Camera via V4L2 (standard USB webcams) |
| `real_robot_launch.py` | Full physical-robot bringup — combines drive control with the RPLiDAR A2M8 driver |

`diffbot.launch.py` is the entry point for drive control alone; `real_robot_launch.py` is the entry point for bringing up the complete physical robot in one command.

## Configuration

`config/` holds the YAML files consumed by the launch files above, including the differential-drive controller parameters (wheel names, separation, radius) and `twist_mux` topic priorities. See the package-level README for the specific parameter values currently in use.
