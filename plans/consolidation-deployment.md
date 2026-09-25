# Junior deployment runbook specification

This is the executable runbook **to be completed and rehearsed by P04/P13**, not a claim that proposed packages exist now. Stage A commands are read-only inventory commands for the actual Linux robot. Later stages become valid only at their owning PR's exit. Never paste these into the Windows planning shell. Do not substitute the thesis's old Humble environment for the running robot without verification.

Version 1.0 platform is fixed by the [reconciled inventory](robot-inventory-reconciled.md): Pi 5/8 GB, Ubuntu 24.04.4 aarch64, Jazzy/Python 3.12.3, camera_ros/libcamera CSI Camera Module 3. Use its package-version table and retained raw report as the dependency starting point. Production domain is 42; doctor summary reports Fast DDS despite unset RMW environment. `/diff_controller/cmd_vel` is TwistStamped, `/diff_controller/odom` is Odometry, `/camera/image_raw` and `/camera/camera_info` are Image/CameraInfo. Recorded camera mode is 640×480, frame `camera_link_optical`, roughly 29 Hz at the ROS observer. Camera calibration provenance, serial baud and actual startup procedure remain G1/G2.

## Stage A — Inventory now

Initial inventory is complete enough to select the platform. Run the targeted follow-up in `robot-inventory-reconciled.md` for missing source/configuration/firmware/extra-node facts. The full list below is retained for future clean-machine baseline comparison; do not repeat completed work unnecessarily.

Have the maintainer disable motor power/enable using the actual established method; do not guess a service or GPIO. Keep the physical operator present. Save outputs with timestamps and redact host/user identifiers in public copies. If the robot is already running, inventory it without starting a second driver/controller. `timeout` ends observation, not the underlying robot node.

```bash
cat /etc/os-release
uname -m
free -h
printenv ROS_DISTRO
printenv ROS_DOMAIN_ID
printenv RMW_IMPLEMENTATION
ros2 doctor --report
ros2 node list
ros2 topic list -t
ros2 control list_controllers
ros2 control list_hardware_interfaces
ros2 param dump /controller_manager
ros2 param dump /diff_controller
ros2 topic info -v /diff_controller/cmd_vel
ros2 topic info -v /diff_controller/odom
ros2 topic info -v /camera/image_raw
ros2 topic info -v /camera/camera_info
timeout 5 ros2 topic echo /camera/camera_info --once
timeout 5 ros2 topic echo /diff_controller/odom --once
timeout 10 ros2 topic hz /camera/image_raw
timeout 10 ros2 topic hz /scan
ls -l /dev/serial/by-id/
lsusb
v4l2-ctl --list-devices
dpkg-query -W 'ros-*' 'libserial*' 'python3-opencv'
```

Missing tools/topics are inventory findings, not permission to install or invent sensors. Record actual equivalents in `config/robot.yaml`. Ask maintainer for current launch command/service, firmware source/version, motor-driver type, serial baud, encoder conversion, battery/power design, E-stop wiring, watchdog timeout, camera mounting/intrinsics, lidar/range coverage, and cleared test area dimensions. Avoid dumping the entire process environment (may expose API keys). Record calibration files and units; Xacro's 57600 baud is a candidate only.

## Stage B — Clean supported checkout (P04/P13)

P01 closes running-source/firmware provenance; OS/ROS/architecture are already selected. P04 supplies `requirements-*.lock`, package manifests and install guide. The release SHA below must be a later reviewed implementation release, not the documentation-only blueprint commit. Use separate clean storage/workspace to prove no hidden dependency. System ROS Python libraries must remain compatible with cv_bridge/OpenCV/rclpy; do not use `pip --break-system-packages`. Run integration/fault tests on a verified isolated ROS domain or test host; never run them against the existing live domain 42.

```bash
# Fill from the verified release manifest before running.
ROS_RELEASE='jazzy'
SOURCE_URL='https://github.com/antorrrr/aruco_marker_tracking_and_following_ros2.git'
RELEASE_SHA='<qualified implementation release full SHA>'
# Fill with a domain verified unused by the physical robot before integration tests.
export ROS_DOMAIN_ID='<verified isolated test domain>'
export RMW_IMPLEMENTATION='rmw_fastrtps_cpp'
WS="$HOME/robot_ws"
REPO="$WS/src/aruco_marker_tracking_and_following_ros2"
source "/opt/ros/$ROS_RELEASE/setup.bash"
mkdir -p "$WS/src"
git clone "$SOURCE_URL" "$REPO"
git -C "$REPO" checkout --detach "$RELEASE_SHA"
cd "$WS"
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro "$ROS_RELEASE" -y
python3 -m venv --system-site-packages "$WS/.venv"
source "$WS/.venv/bin/activate"
python3 -m pip install --require-hashes -r "$REPO/requirements-runtime.lock"
# Qualification/test host additionally needs the pinned test environment:
python3 -m pip install --require-hashes -r "$REPO/requirements-dev.lock"
colcon build --symlink-install
source "$WS/install/setup.bash"
colcon test
colcon test-result --verbose
cd "$REPO"
python3 tools/doctor.py --profile robot --no-motion
```

P04 must verify this Python/ament install arrangement on the actual platform and revise the exact commands if interpreter selection does not preserve ROS ABI compatibility. Record interpreter path and `python3 -c 'import rclpy, cv2, cv_bridge; print(cv2.__version__)'`. Lock hardware runtime and offline test dependencies separately. Preserve a native `dpkg-query` package-version manifest plus the OS image/repository snapshot or required package cache and verify a clean reconstruction against it; `rosdep install` alone does not pin native versions. A later runtime-only installation may omit dev dependencies, but must not be reported as the clean test environment. Required system/tool classes: supported ROS base, colcon/rosdep, controller_manager/diff_drive_controller/joint_state_broadcaster, rclcpp/rclpy, geometry/sensor/std messages, TF/xacro/state publisher, libserial, selected camera driver, cv_bridge/OpenCV ArUco, joystick tooling if used, rosbag2 storage, Flask/HTTP client/schema validator. Gazebo/ros_gz belong on a compatible simulation host if robot resources are insufficient. Dependencies are declared in package manifests; no undocumented global pip installs.

Before cloning into an existing workspace, inventory it and select a new workspace name; never delete or overwrite the working one. If network/remote is unavailable, use the P01 verified offline source bundle and package cache with the same hashes. No unreviewed branch tip in study deployment.

## Configuration and secrets

`config/robot.example.yaml` defines topics/types, serial device/baud, wheel geometry/encoder conversion, camera driver/index/calibration, sensor frames, robot namespace/domain and environment profile. Junior copies to a local ignored `config/robot.yaml` and fills verified values. `config/safety.yaml` and `skills.yaml` are reviewed versioned policies, never browser-editable. `config/provider.example.yaml` holds provider/model ID, deadlines, output cap, per-run/daily budget and offline policy without secret values. `config/vision.yaml` holds frame size/FPS/age, privacy and caption deadlines. All nonsecret effective configs are hashed into each run manifest.

Populate known deployment defaults: production domain 42, Fast DDS, camera_ros/libcamera, image/CameraInfo names above, optical frame and 640×480, controller `diff_controller`, joints `LeftWheel_joint`/`RightWheel_joint`, configured radius/separation 0.021/0.134 m, by-id CH340 device. Mark baud, firmware identity, calibration-file path, marker dictionary/physical size and obstacle sensor configuration as required unknowns until G1/G2/G4 close; startup must reject an armed profile with these gaps. Existing 1.0-s controller timeout and ±0.2/±0.5 limits are baseline settings, not measured safety bounds. Do not indiscriminately replace optional `.nan` controller parameters: verify their installed semantics and set explicit qualified braking policy later. `publish_limited_velocity=false` requires P03/P06 instrumentation work for motor-output evidence.

Store API key in a private owner-readable environment file outside the checkout (e.g. `~/.config/thesis-robot/provider.env`, mode 600), or the platform credential mechanism. Do not echo it, use URL query parameters, place it in shell history, browser code, bags or screenshots. Supply it only to the translator/vision process; safety/controller processes need no cloud credentials. `.gitignore`, artifact redaction and bundle scanning must cover local secret/config/log files. Junior verifies **presence**, not contents. Rotate any previously exposed key through its provider, outside this blueprint's scope.

Use an unprivileged service account with only needed serial/video device access; stable `/dev/serial/by-id` or narrowly scoped udev mapping prevents motor/lidar port swaps. Confirm group membership and reboot/login effect; avoid mode 777 devices. Keep controller DDS and any legacy rosbridge inaccessible to untrusted LAN clients; no generic web publish/service capability. Authenticated gateway may be bound to the protected LAN with HTTPS/session setup documented. Physical control remains local. Document firewall rules and restore commands in the platform-specific runbook.

## Stage C — Launch order (P04/P06–P11)

Proposed entrypoint: `ros2 launch robot_bringup system.launch.py profile:=robot robot_config:=<absolute-path> armed:=false`. P04 provides the entrypoint; P06–P11 add components. It must validate dependencies and refuse to arm if required checks fail. Junior should never need to launch sia-bot, ROSA, OpenRouter or a second motor driver.

Before starting this entrypoint on production domain 42, the maintainer must use the captured shutdown procedure to stop the old controller/mux/follower stack with motors independently disabled; verify no competing publishers or serial-device owners remain. Only then set `ROS_DOMAIN_ID=42` and `RMW_IMPLEMENTATION=rmw_fastrtps_cpp`. A separate checkout does not isolate ROS or serial hardware. Rehearse on test storage/domain first. The currently observed `/scan` absence means inspection can start disarmed, but floor research remains blocked until P05b/P06/P13 establish real sensing and qualification.

1. Motor enable remains off. Verify E-stop availability and firmware watchdog/configuration.
2. Load state publisher and hardware controller in a safe inactive/zero state; start validated encoder/sensor interfaces. Check odometry/TF and required sensor freshness.
3. Start safety supervisor **disarmed**, then source arbitration. Verify supervisor is sole controller command publisher and zero output; no follower/joystick bypass.
4. Start selected camera driver and calibration, detector with target `-1`, disabled follower skill. Check frame conventions and timestamp coherence.
5. Start event recorder, status/health monitor, executor and skills. No active plan or lease after startup.
6. Start language/vision workers with bounded queues and credentials. API failure must leave stop/status functional.
7. Start web/static and separate stop endpoint; sign in, inspect disarmed status and camera age, run read-only provider/health/snapshot smoke checks.
8. P13-qualified operator performs local readiness checks, deliberate re-arm and fresh control lease; only then enable motor authority for a bounded supervised action.

Shutdown: local stop/cancel, confirm measured halt, disarm/disable motor enable, end lease, flush recorder, stop language/web/vision, executor/sources, supervisor/controller and hardware in documented order. Restart policy always returns disarmed; systemd dependency/restart settings must never replay a goal. No default service auto-enables motors.

## Stage D — Smoke and qualification commands

```bash
ros2 control list_controllers
ros2 topic info -v /diff_controller/cmd_vel
ros2 topic echo /control/safety_state --once
ros2 topic echo /diff_controller/odom --once
ros2 topic echo /camera/camera_info --once
timeout 10 ros2 topic hz /camera/image_raw
python3 tools/check_web.py --base-url http://127.0.0.1:5000 --profile no-motion
python3 tools/probe_provider.py --config config/provider.yaml --no-actuation
python3 tools/qualify_safety.py --profile wheels-raised --case all
```

Tests require an authenticated test client/session where appropriate; P10 documents secure credential loading without command-line token exposure. Confirm camera/scan names from effective config. On no camera/API, smoke checks should report unavailable/partial rather than false success. General live command acceptance is disabled until qualified. The sole exception is P13 commissioning sub-gate A's separately enabled bounded low-speed test profile after bench gates and operator/observer clearance; it is not available to ordinary web/participant sessions. `--no-motion` must always guarantee no actuator publication, including during commissioning.

Physical motion commands are intentionally not pasted as raw `ros2 topic pub` recipes: P12 provides a guarded baseline CLI, P13 records explicit arming and safe test area prerequisites, and each trial uses a bounded skill with watchdog/lease. The raw `/cmd_vel` example in required Test 3 is not compatible with the current stamped controller or final safety design. Do not bypass the supervisor to imitate it.

## Stage E — Troubleshooting and restore

| Symptom | Read-only checks | Corrective action / stop condition |
|---|---|---|
| No camera/detection | topic type/QoS, driver logs, device enumeration, CameraInfo K values, image age | Select one proven driver, correct calibration/frame/dictionary/marker size. No follow motion with missing/invalid calibration. |
| Package/import failure | release/OS/arch, interpreter, `rosdep check`, colcon logs | Restore pinned dependencies in clean workspace; do not mix Humble/Jazzy or Mac Pixi. |
| No motor output | safety state/reason, lease, publisher ownership, controller state, serial mapping | Diagnose while disarmed. Never raise speed/disable guard merely to make wheels turn. |
| Wrong direction/odometry scale | wheel joints/encoder conversion and signs, Xacro geometry | Wheels-raised calibration, then controlled metrology; invalidate old motion precision data after changes. |
| Serial timeout/garbled encoder | tty by-id, baud/firmware hash, serial logs | Disable motor, verify firmware/protocol; reject invalid feedback instead of interpreting zero. |
| API unavailable/429/budget | sanitized provider status/model and spend ledger | Stop/status remain; no new language motion. Retry only within documented bounds; no automatic provider/model swap. |
| Browser stale/disconnect | lease age and session/generation, status IDs | Local expiry stops motion; reconnect shows disarmed state. Explicit re-arm/new command only. |
| Video smooth but old | unique frame sequence/capture age | Show stale overlay; repeated JPEG is not fresh FPS. Fix camera pipeline separately from controls. |
| Recorder/disk fault | free space, recorder health, bag info | Stop research admission safely; preserve partial artifacts and mark incomplete. |
| Unexpected movement or ineffective stop | physical stop and disable first | Revoke qualification; preserve incident logs; do not continue participant trials. |

Rollback references previous **qualified** release+firmware+config hashes; no `git reset --hard` over local work. Use a clean worktree/check-out and restore documented service paths while disabled. Rehearse restore with junior and verify no-motion checks again. Hardware changes require hardware rollback review; no software rollback can undo an unsafe circuit.

Junior acceptance record: exact elapsed setup time, commands run, missing dependency count, every intervention by author, boot/reboot/disconnect behavior, firmware/config/source hashes, one bounded demonstration after safety qualification, and successful evidence export. If the author must improvise instructions, fix the guide and repeat the affected clean-checkout steps before retirement.
