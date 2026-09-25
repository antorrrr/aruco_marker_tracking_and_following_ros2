# Junior handoff: robot inventory only

Prepared 2026-09-25. Purpose: collect facts needed to finalize the consolidation blueprint. The owner is away from the robot and will supply your report later. **This is not deployment or permission to test movement.**

Update 2026-09-26: the initial report has been received and incorporated into blueprint v1.0. This is now the retained original checklist. Continue with [targeted follow-up and G1–G7](robot-inventory-reconciled.md), especially actual package repositories under `~/amr_robot/src`, firmware/configuration/calibration and physical stop/sensor inspection. Do not repeat completed platform queries or treat the supplied report's conflicting final summary as authoritative.

## Boundaries

- Keep the robot stationary. Use the maintainer's established motor-disable procedure if known; if unknown, report that and do not guess wiring, GPIOs, services or buttons.
- Do not install/upgrade packages, flash firmware, change ROS parameters, publish commands, launch a second driver, start the LLM, test E-stop effectiveness or cut Wi-Fi. Do not unplug the motor controller to “test the watchdog.” Those are later supervised qualification tasks.
- Inspect the already-running system. If ROS is not running, report that and record the normal startup instructions; do not start it merely for this inventory if doing so could enable motion.
- Do not send API keys, `.env` contents, full environment dumps, private keys, account tokens, or participant information. We need versions and configuration names, not credentials.

## 1. Physical observations

Fill unknown fields as **unknown**. Distinguish a label/photo/document from something you have actually tested. Photographs of board labels/wiring are useful if allowed by the lab; do not disturb live wiring. Send the report back to the owner through your normal channel; this document does not send it automatically.

| Field | Your observation / source |
|---|---|
| Date/time and person collecting | |
| Computer model and RAM | |
| Power supply/battery and motor supply arrangement | |
| Motor-controller board and motor-driver model | |
| Motor firmware repository/file location, version/hash if known | |
| Firmware build/flash instructions and known-good backup location | |
| Wheel encoders, IMU, lidar/range sensors/other sensors actually fitted | |
| Camera model, USB/CSI connection, mounting direction | |
| Camera calibration file location, image dimensions, frame name | |
| Marker dictionary and measured printed marker side length | |
| Physical E-stop button/switch: label, location, known wiring/function | |
| Does it interrupt motor enable/power independently of the computer? Evidence or unknown | |
| Controller/firmware watchdog: documented timeout and source or unknown | |
| Obstacle sensing: coverage/front/rear/blind spots, known topic or unknown | |
| What is already known to happen on Wi-Fi/browser disconnect? Prior observation only; do not test now | |
| Normal startup and shutdown procedure; does boot automatically enable motion? | |
| Safe test area dimensions, floor, obstacles, access control | |
| Who can be operator and separate physical-stop observer later? | |

## 2. Computer inventory

Run in a Bash terminal **on the robot**, not the Windows laptop. These commands query state. If a command is absent or fails, paste its error and move on. Do not install a missing utility. Shell output such as serial identifiers can be kept in the private report and redacted before publication.

```bash
date -Is
cat /etc/os-release
uname -m
free -h
printenv ROS_DISTRO
printenv ROS_DOMAIN_ID
printenv RMW_IMPLEMENTATION
command -v ros2
command -v python3
python3 --version
ls -l /dev/serial/by-id/
lsusb
v4l2-ctl --list-devices
```

If `ROS_DISTRO` is blank, do not guess or source a different distribution. Ask which setup file the running deployment uses. Record whether the shell differs from the service environment.

## 3. Existing ROS graph (only if already running)

```bash
timeout 20 ros2 doctor --report
timeout 10 ros2 node list
timeout 10 ros2 topic list -t
timeout 10 ros2 control list_controllers
timeout 10 ros2 control list_hardware_interfaces
timeout 10 ros2 param dump /controller_manager
timeout 10 ros2 param dump /diff_controller
timeout 10 ros2 topic info -v /diff_controller/cmd_vel
timeout 10 ros2 topic info -v /diff_controller/odom
timeout 10 ros2 topic info -v /camera/image_raw
timeout 10 ros2 topic info -v /camera/camera_info
timeout 5 ros2 topic echo /camera/camera_info --once
timeout 5 ros2 topic echo /diff_controller/odom --once
timeout 10 ros2 topic hz /camera/image_raw
timeout 10 ros2 topic hz /scan
```

These names come from the source and may differ on your robot. If a name is missing, keep that finding and use `ros2 topic list -t` to identify the real camera, velocity, odometry and scan names. Repeat read-only type/info/rate checks for those observed equivalents. Timeout exit code 124 usually means the observation limit expired; it is not a robot failure by itself. Do not run `ros2 topic pub`, change parameters or launch anything.

## 4. Running source and dependency provenance

Report the absolute directory actually used by the robot and the exact command or service that launches it. If it is a Git checkout, run these inside that directory:

```bash
git status --short
git rev-parse HEAD
git branch --show-current
git remote -v
```

Review remote URLs before sharing; redact credentials if a URL contains them. If not a Git checkout, say so. Do not initialize Git or overwrite files. Provide nonsecret copies or paths of the active controller, mux, camera and robot-description configuration and launch files. Record the source of firmware separately; it was not present in the supplied ArUco folder.

```bash
dpkg-query -W 'ros-*' 'libserial*' 'python3-opencv'
python3 -c 'import cv2; print(cv2.__version__); print("aruco:", hasattr(cv2, "aruco"))'
```

If Python import fails, include the error and interpreter path. Do not repair the environment during this inventory. If a known service is used, inspect only its launch configuration after the maintainer checks for inline secrets; avoid dumping unknown service environments.

## 5. Return this summary

```text
Inventory date:
Collector:
Computer / RAM:
Ubuntu / architecture / ROS distribution:
Actual source directory / Git SHA or no Git:
Normal launch command or service:
Motor board / driver / firmware source-version:
Serial device / baud:
Camera / driver / image topic / CameraInfo topic:
Odometry topic / type:
Velocity input topic / type / publishers:
Sensors fitted / obstacle topic / coverage:
Physical E-stop implementation / evidence or unknown:
Firmware watchdog / evidence or unknown:
Known disconnect behavior / prior evidence or unknown:
Safe area / operator / observer:
Missing commands or errors:
Unknowns needing maintainer input:
Attached nonsecret outputs/configuration references:
```

Completion here means the report is honest and includes unknowns. It does **not** certify safety or demonstrate watchdog, stop distance, sensor coverage, calibration accuracy, or network-loss behavior. Once returned, the blueprint owner reconciles it with the source, chooses the matching deployment branch, and plans supervised tests for unverified safety functions.
