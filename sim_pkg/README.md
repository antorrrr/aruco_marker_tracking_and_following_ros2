# sim_pkg

A ROS 2 simulation package that reproduces the physical robot in Gazebo Sim, using `ros_gz` and `gz_ros2_control` so the same controllers, topic structure, and velocity-command pipeline used on hardware can be developed and validated entirely in simulation first.

The simulated robot exposes the same camera and command topics as the real one, so packages like `aruco_follower` and `robot_control_pkg`'s higher-level nodes can run against either target — sim or hardware — without modification.

---

## Contents

- [Simulation Stack](#simulation-stack)
- [Main Files](#main-files)
- [Run Simulation](#run-simulation)
- [Robot](#robot)
- [Camera](#camera)
- [Bridge](#bridge)

---

## Simulation Stack

```text
ArUco / Joystick / Navigation
            │
            ▼
        twist_mux
            │
            ▼
       diff_controller
            │
            ▼
     gz_ros2_control
            │
            ▼
       Gazebo Sim robot
            │
     ┌──────┴──────┐
     │             │
   Camera         LiDAR
     │             │
     ▼             ▼
 camera/image_raw  scan
```

This mirrors the physical-robot control path in `robot_control_pkg` almost exactly, with `gz_ros2_control` standing in for the real `RobotControlHardware` serial interface. Because the interface presented to `ros2_control` is the same either way, `diff_controller`, `twist_mux`, and everything upstream of it are unaware of whether they're driving a simulated or physical robot.

---

## Main Files

| File / Directory | Purpose |
|---|---|
| `launch/sim_launch.py` | Full Gazebo simulation launch — world, robot spawn, controllers, bridges |
| `launch/rsp_launch.py` | `robot_state_publisher`-only launch, for visualizing the robot description (e.g. in RViz) without starting Gazebo |
| `description/` | Robot Xacro/URDF plus Gazebo-specific sensor and `gz_ros2_control` plugin definitions |
| `models/` | Robot STL meshes used by the simulated description |
| `config/` | Controller and `twist_mux` configuration for the simulated robot |
| `params/` | `ros_gz_bridge` topic bridge configuration |
| `worlds/` | The industrial warehouse world (`industrial-warehouse.sdf`) |

---

## Run Simulation

Build and source the workspace:

```bash
colcon build --packages-select sim_pkg
source install/setup.bash
```

Start the simulation:

```bash
ros2 launch sim_pkg sim_launch.py
```

`sim_launch.py` performs, in order:

1. Starts Gazebo Sim, loading the industrial warehouse world
2. Spawns the robot (`agv_robot`)
3. Starts `robot_state_publisher`
4. Starts the differential-drive and joint-state-broadcaster controllers via `gz_ros2_control`
5. Bridges selected Gazebo topics into ROS 2 via `ros_gz_bridge`
6. Bridges the camera image via `ros_gz_image`
7. Starts `twist_mux`

Once running, the same sanity checks used on hardware apply — e.g. `ros2 topic hz /camera/image_raw` to confirm the camera is publishing, or `ros2 topic echo /scan` for the lidar.

---

## Robot

The simulated robot (`agv_robot`) includes:

- Differential-drive wheels, controlled through `ros2_control`'s standard velocity command interfaces
- A passive caster
- A front-mounted camera
- Gazebo Sim sensor plugins for camera and lidar
- Spawn position of approximately `x = 0, y = 0, z = 1.4` in the industrial warehouse environment

Because the robot description reuses the same joint names and general structure as the physical robot's Xacro, differences between simulated and real behavior should mainly come down to controller tuning and physics fidelity, not structural mismatches.

---

## Camera

The simulated camera publishes:

```text
/camera/image_raw       (sensor_msgs/Image)
/camera/camera_info     (sensor_msgs/CameraInfo)
```

configured at `640×480` resolution, `30` Hz, with `camera_link_optical` as its Gazebo frame — matching the physical robot's camera configuration. These topics are consumed directly by `aruco_follower`'s `aruco_detector` node, so the marker-following stack can be developed and tuned in simulation before being pointed at the real camera.

---

## Bridge

`params/ros_gz_bridge.yaml` bridges the following topics from Gazebo into ROS 2 via `ros_gz_bridge`:

| Topic | Purpose |
|---|---|
| `/clock` | Simulation time, so ROS 2 nodes stay synchronized with Gazebo |
| `/scan` | LiDAR scan data |
| `/camera/camera_info` | Camera calibration, required by `aruco_detector`'s `solvePnP()` pose estimation |
| `/tf` | Transform tree |

The camera **image** itself is bridged separately via `ros_gz_image` rather than `ros_gz_bridge`, since image transport benefits from `ros_gz_image`'s dedicated handling rather than the generic message bridge.
