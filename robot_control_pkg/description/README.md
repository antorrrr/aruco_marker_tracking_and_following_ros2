# description

The physical robot model used by `robot_control_pkg`: the URDF/Xacro description, `ros2_control` hardware bindings, and mesh assets that together define the robot's kinematics, visuals, and hardware interface.

## Components

| Directory | Contents |
|---|---|
| `urdf/` | Xacro robot description — links, joints, and frames for the differential-drive base, wheels, caster, and camera |
| `ros2_control/` | `ros2_control` hardware-interface configuration, binding the `RobotControlHardware` plugin to the joints defined in `urdf/` |
| `models/` | STL meshes referenced by the robot description for visual and collision geometry |

## Model Structure

The description defines:

- A differential-drive base (`base_link`) with `LeftWheel_joint` and `RightWheel_joint` as the drive joints — wheel separation and radius are set here and must match the values used by `diff_controller` in `bringup/config/diffbot_controllers.yaml`.
- A passive caster for the base's third contact point.
- A camera link and optical frame (`camera_link_optical`), which the camera launch files (`cam_launch.py` / `camera_launch.py`) publish images into.

## Usage

`urdf/` and `ros2_control/` are consumed together by `robot_state_publisher` and `ros2_control_node` at launch time (see `bringup/launch/diffbot.launch.py`), so the two should be kept consistent with each other — a joint added to the URDF also needs a matching interface declared in `ros2_control/`, and vice versa.
