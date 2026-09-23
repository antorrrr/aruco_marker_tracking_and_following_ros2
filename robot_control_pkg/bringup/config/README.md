# config

YAML configuration for the differential-drive controller, joystick teleoperation, and velocity command multiplexing used by the `bringup` launch files.

## Files

### `diffbot_controllers.yaml`

Controller manager configuration for:

- `joint_state_broadcaster` — publishes wheel joint states from the hardware interface
- `diff_controller` — the differential-drive controller, configured with `LeftWheel_joint` and `RightWheel_joint` as the drive joints

This is the file to edit when changing wheel joint names, controller update rate, or other `ros2_control` controller-manager parameters.

### `twist_mux.yaml`

Arbitrates between the two velocity sources the robot accepts, by priority:

| Input | Topic | Priority |
|---|---|---:|
| Navigation / marker follower | `/cmd_vel_nav_stamped` | `10` |
| Joystick | `/cmd_vel_joy` | `100` |

`use_stamped` is enabled, so both inputs are expected as `TwistStamped` rather than plain `Twist`. Because the joystick has the higher priority value, manual joystick input overrides autonomous commands whenever it's actively publishing — giving an operator a reliable manual override without needing to stop the autonomous stack first.

### `joystick.yaml`

Button and axis mapping consumed by `teleop_twist_joy`, defining which physical controls map to linear and angular velocity (and any enable/deadman buttons). Update this file to match a different joystick or controller layout.
