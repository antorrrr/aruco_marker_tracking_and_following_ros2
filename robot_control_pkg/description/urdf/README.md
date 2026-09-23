# urdf

The robot's Xacro description, split into a physical-model file and a hardware-interface file that are combined into the final `robot_description`.

## Files

### `diffbot.urdf.xacro`

The top-level entry point. It includes:

- `diffbot_description.urdf.xacro` — the physical robot model
- `diffbot.ros2_control.xacro` — the `ros2_control` hardware interface (see `ros2_control/README.md`)

and instantiates both as a single combined robot description. This is the file referenced by `robot_state_publisher` and by the launch files in `bringup/launch/` — it should be the entry point for any Xacro processing, rather than including the sub-files directly.

### `diffbot_description.urdf.xacro`

Defines the physical robot: links, joints, visual and collision geometry (referencing the STL meshes in `models/`), and the camera frame structure feeding into `camera_link_optical`. This is the file to edit for changes to the robot's physical dimensions, joint limits, or link hierarchy — as opposed to hardware/serial configuration, which lives in `diffbot.ros2_control.xacro`.

## How it fits together

```text
diffbot.urdf.xacro
      │
      ├── diffbot_description.urdf.xacro   (links, joints, geometry)
      │
      └── diffbot.ros2_control.xacro       (hardware interface, serial config)
      │
      ▼
robot_description (via robot_state_publisher)
      │
      ▼
ros2_control_node, RViz, TF, etc.
```

`robot_state_publisher` parses the combined Xacro output into the `robot_description` parameter at launch time, which is what downstream tools — `ros2_control_node`, RViz, TF — actually consume. Any change to link names or joint names here must stay consistent with the joint names referenced in `diffbot.ros2_control.xacro` and `bringup/config/diffbot_controllers.yaml`, or the hardware interface and controller will fail to bind at launch.
