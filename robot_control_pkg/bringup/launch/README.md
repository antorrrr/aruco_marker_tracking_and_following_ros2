# launch

ROS 2 launch files for bringing up the physical robot: drive control, joystick teleoperation, camera, lidar, and combined full-robot startup.

## `diffbot.launch.py`

Starts the complete `ros2_control` differential-drive stack:

- `ros2_control_node`
- `robot_state_publisher`
- `joint_state_broadcaster`
- `diff_controller`
- `twist_mux`

This is the entry point for drive control alone — no camera or lidar.

```bash
ros2 launch robot_control_pkg diffbot.launch.py
```

## `joystick.launch.py`

Starts:

- `joy_node`
- `teleop_twist_joy`

Joystick output is remapped to `/cmd_vel_joy`, where it's picked up by `twist_mux` (see `config/twist_mux.yaml`) and given priority over autonomous commands.

```bash
ros2 launch robot_control_pkg joystick.launch.py
```

## `real_robot_launch.py`

Includes `diffbot.launch.py` together with the RPLiDAR A2M8 driver launch, bringing up drive control and lidar sensing in a single command. This is the intended entry point for running the physical robot end to end.

```bash
ros2 launch robot_control_pkg real_robot_launch.py
```

## `cam_launch.py`

Starts `camera_ros/camera_node` (libcamera-based) at `640x480` resolution, publishing in the `camera_link_optical` frame. Use this on hardware where `camera_ros` is available and preferred over V4L2.

```bash
ros2 launch robot_control_pkg cam_launch.py
```

## `camera_launch.py`

Starts `v4l2_camera_node` at `640x480` resolution, also publishing in the `camera_link_optical` frame. Use this as the V4L2 fallback for standard USB webcams when `camera_ros` isn't available.

```bash
ros2 launch robot_control_pkg camera_launch.py
```

---

Only one of `cam_launch.py` / `camera_launch.py` should be run at a time, since both publish camera data into the same frame and are meant as alternatives rather than a pair to run together.
