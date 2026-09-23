# hardware

The custom C++ `ros2_control` hardware implementation that connects the ROS 2 control stack to the physical robot's Arduino-based motor and encoder controller.

## Files

| File | Purpose |
|---|---|
| `diffbot_system.cpp` | Implementation of the `RobotControlHardware` lifecycle (`on_init`, `on_activate`, `on_deactivate`), the periodic `read()`/`write()` loop, and wheel state handling. |
| `include/robot_control_pkg/diffbot_system.hpp` | Class declaration for `RobotControlHardware`, including its configuration struct (serial device, baud rate, loop rate, encoder counts/rev, PID gains). |
| `include/robot_control_pkg/arduino_comms.hpp` | Serial communication helper — connect/disconnect, encoder reads, motor command writes, PID parameter writes over LibSerial. |
| `include/robot_control_pkg/wheel.hpp` | Per-wheel state representation (name, encoder count, position, velocity, command) and encoder-count-to-angle conversion. |
| `include/robot_control_pkg/visibility_control.h` | Export macros for the hardware plugin's shared library symbols. |

## Data Flow

```text
diff_controller
      │  velocity command
      ▼
RobotControlHardware::write()
      │  converted to serial motor command ("m <left> <right>")
      ▼
Arduino (via arduino_comms)

Arduino
      │  encoder counts (via "e" command)
      ▼
RobotControlHardware::read()
      │  converted to wheel position/velocity via wheel.hpp
      ▼
ros2_control state interfaces
```

`write()` is called each control cycle with the velocity commands `ros2_control` wants applied; it converts them into the Arduino's serial motor-command format via `arduino_comms` and sends them over the configured serial device. `read()` runs on the same cycle, requesting the latest encoder counts from the Arduino and converting them into wheel position and velocity using the per-wheel encoder-to-angle conversion in `wheel.hpp`, so that odometry and any downstream consumer of the state interfaces see accurate, closed-loop wheel state rather than the commanded values alone.

## Plugin Export

The hardware plugin is exported through `robot_control_pkg.xml`, the `pluginlib` description file, as:

```text
robot_control_pkg/RobotControlHardware
```

with base class `hardware_interface::SystemInterface`. This is what allows the plugin to be loaded by name from the `diffbot.ros2_control.xacro` hardware description at launch time, without `ros2_control_node` needing to be built against this package's headers directly.
