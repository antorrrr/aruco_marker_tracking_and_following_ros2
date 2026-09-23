# include/robot_control_pkg

Public headers for the `robot_control_pkg` hardware plugin — declaring the hardware interface class, its serial communication layer, per-wheel state, and the shared-library visibility macros needed to build it as a `pluginlib`-loadable plugin.

## `arduino_comms.hpp`

Serial communication layer between `RobotControlHardware` and the Arduino motor controller, built on LibSerial. Provides:

- Connecting to and disconnecting from the configured serial device
- Reading current encoder values (`e` command)
- Sending motor commands (`m <left> <right>`)
- Sending updated PID gains to the firmware

This is the only file that talks to the serial port directly — `diffbot_system.cpp` calls into it rather than handling LibSerial itself, keeping the transport concern isolated from the `ros2_control` lifecycle logic.

## `diffbot_system.hpp`

Declares `RobotControlHardware`, the `hardware_interface::SystemInterface` implementation exported as the `robot_control_pkg/RobotControlHardware` plugin. Defines the hardware's configuration struct — serial device, baud rate, loop rate, encoder counts per revolution, and PID gains — along with the wheel and serial-communication members used across the lifecycle (`on_init`, `on_activate`, `read`, `write`).

## `wheel.hpp`

Per-wheel state representation, storing joint name, raw encoder count, position, velocity, and the last commanded value. Converts raw encoder counts into wheel angle using the configured counts-per-revolution, which `RobotControlHardware::read()` relies on to turn Arduino encoder readings into the position/velocity state interfaces `ros2_control` exposes.

## `visibility_control.h`

Compiler-specific symbol visibility macros (`_EXPORT`/`_IMPORT`/`_LOCAL`) used to correctly export the hardware plugin's public symbols when built as a shared library — required for `pluginlib` to load the plugin by name across the shared-library boundary.
