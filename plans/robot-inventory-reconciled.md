# Robot inventory: reconciled baseline and remaining gates

Inventory collected by Antor on 2026-09-25; supplied by the owner on 2026-09-26. This is user-supplied observation, not an independent remote session or safety qualification. The complete [submitted report](evidence/robot-inventory-2026-09-25.txt) is retained unchanged, including its contradictory final summary. Source command blocks take precedence over that summary. `[cite: 1]` strings in the submission have no independently supplied citation target.

## Established deployment target

| Item | Evidence from report | Blueprint decision |
|---|---|---|
| Computer | Collector: Raspberry Pi 5, 8 GB; memory output 7.8 GiB total, 5.2 GiB free at observation | Target Pi 5 ARM64; do not retain thesis Pi 4 claims for new work. Free RAM is a snapshot, not robot software memory usage. |
| OS / ROS / Python | Ubuntu 24.04.4 LTS Noble, aarch64, Jazzy, `/opt/ros/jazzy/bin/ros2`, `/usr/bin/python3` 3.12.3 | Native Jazzy/Python 3.12 runtime; no Humble or macOS Pixi migration. |
| DDS | ROS_DOMAIN_ID=42; RMW environment unset, collector reports doctor selected `rmw_fastrtps_cpp` | Make domain 42 and Fast DDS explicit in deployment profile; domain ID alone does not enforce security. Isolate simulator/fault tests from live domain 42. |
| Motors / firmware | Collector: N20 encoder motors, Arduino Nano, L298N; reported firmware source `hbrobotics/ros_arduino_bridge`; Arduino CLI/VS Code flashing; backups reported in three places | Preserve exact installed fork/sketch/binary before editing. Upstream URL does not prove installed revision or watchdog behavior. Battery 3200 mAh LiPo reported; voltage/power isolation unknown. |
| Serial | CH340 `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` resolves to ttyUSB0 | Prefer observed by-id path after device identity check. Baud remains unknown; source Xacro 57600 is not confirmed actual baud. Check adapter uniqueness if adding another CH340. |
| Camera | Collector: Camera Module 3 CSI, rp1-cfe/libcamera; installed `ros-jazzy-camera-ros`; active `/camera` node | Use `camera_ros`/libcamera; target `cam_launch.py` as adaptation reference. Do not select the v4l2 alternative just because its package is installed. Mount orientation/calibration file still need capture. |
| Camera graph | `/camera/image_raw` Image and `/camera/camera_info` CameraInfo; both reliable/volatile publisher to best-effort/volatile detector subscriber | Preserve names/types and compatible sensor QoS. Reported queue depth UNKNOWN must be queried/configured, not converted to zero. |
| Image geometry | CameraInfo: 640×480, `camera_link_optical`, plumb_bob, populated K/D/R/P | Capture exact calibration file and association with this camera mode. Intrinsics exist; calibration accuracy is not established. fx=549.772535, fy=549.118413, cx=426.245907, cy=245.72688; off-center principal point warrants checking crop/mode/calibration, not automatically replacing values. |
| Camera rate | Seven observed running averages 28.132–29.046 Hz, final 28.911 Hz | Approximately 29 Hz at the ROS observer during this short capture. Not browser FPS, latency, long-run reliability or caption accuracy. |
| Motor command graph | `/diff_controller/cmd_vel` TwistStamped: one publisher `twist_mux` (reliable/volatile), one subscriber `diff_controller` (best-effort/volatile) | Current direct mux path confirmed in snapshot. P06 replaces actuation path with authority-preserving supervisor. One publisher is not proof of safety/absence of alternate future publishers. |
| Odometry | `/diff_controller/odom` Odometry; reliable/transient-local publisher; zero subscribers in info snapshot, followed by a separate echo | Feedback exists; no connected skill consumer shown at that moment. Use fresh timestamp/boot/epoch checks and volatile sensor subscription for control so retained odometry cannot admit a goal. Echo shows `odom` → `base_link`, near-zero twist once; no movement accuracy established. |
| Controller | Active diff_controller and joint_state_broadcaster; wheel velocity interfaces claimed | Keep `LeftWheel_joint`/`RightWheel_joint` and controller package; verify actual hardware/firmware mapping. `open_loop=false`, `position_feedback=true` support feedback configuration, not metrology accuracy. |
| Current limits | ±0.2 m/s, ±0.5 rad/s, linear max acceleration 0.3, angular ±1.0; timeout 1.0 s; wheel radius 0.021 m, separation 0.134 m, update_rate 30, publish_rate 50 | Record as configured baseline. Preserve until deliberate tuning in P05/P06/P13; proposed tighter 0.3-s controller/MCU expiry remains future qualification. Geometry is configured, not physically calibrated by this report. |
| Config gaps | `/controller_manager` dump empty; several optional reverse/deceleration limits `.nan`; limited velocity publication false | Retain exact dump; do not infer manager rate from empty dump or flag optional parameter NaN as corrupt telemetry. Review installed controller parameter definitions before setting braking bounds. Add controller output instrumentation because limited velocity is not currently published. |
| Obstacles | Collector says `/scan` absent; hz command reports no publisher | No active LaserScan path evidenced. This does not prove lidar hardware absent; survey hardware and integrate a real clearance source in P05b. No obstacle-protection claim today. |
| Other nodes/topics | Report lists detector, commander, follower, camera, mux, controllers, state publisher, and extra `/diffbot`; mentions `/cmd_vel_emergency` | Identify `/diffbot`, emergency topic type/publishers/consumers and all velocity paths. Name alone proves neither latched E-stop nor safe priority. Preserve graph before reconfiguration. |

## Observed package versions

These are the report's installed versions, not tested dependency locks or a complete OS image. P04 must capture required native/firmware/Python dependencies and a reproducible package cache/image; the report's wildcard list alone is insufficient.

| Package | Version |
|---|---|
| python3-opencv:arm64 | 4.6.0+dfsg-13.1ubuntu1; import reports 4.6.0 and ArUco present |
| libserial-dev:arm64, libserial1:arm64 | 1.0.0-9build1 |
| ros-jazzy-camera-ros | 0.6.0-1noble.20260615.074621 |
| ros-jazzy-libcamera | 0.7.1-1noble.20260429.110019 |
| ros-jazzy-cv-bridge | 4.1.0-1noble.20260902.175525 |
| ros-jazzy-controller-manager | 4.45.2-1noble.20260612.162541 |
| ros-jazzy-diff-drive-controller | 4.40.1-1noble.20260614.101845 |
| ros-jazzy-rmw-fastrtps-cpp | 8.4.4-1noble.20260612.092346 |
| ros-jazzy-twist-mux | 4.5.0-1noble.20260612.102044 |

## Reconciliation rules and outstanding evidence

1. Summary says topic-info/echo/hz and dpkg/Python checks were skipped, and velocity publishers were not queried. Earlier detailed blocks show them. Use the detailed blocks as supplied observations; retain the contradictory summary for provenance, never call it a second confirming source.
2. Git commands were run at `~/amr_robot`, the colcon workspace root. The failure there proves only that directory is not a Git worktree; packages in `~/amr_robot/src` may have their own repositories. Installed source location and commit remain unresolved. Do not initialize Git across the workspace or assume the Windows source equals the running overlay.
3. No raw full `ros2 doctor`, node list or topic list is supplied, only narrative summaries for those commands. Treat reported Fast DDS/node inventory as reported evidence and refresh the missing raw artifacts in P01. The parameter/topic endpoint samples do contain detailed output.
4. CameraInfo and odometry timestamps are from separate command invocations; no time-synchronization measurement or clock uncertainty is supplied. Re-collect synchronized timing only when qualifying latency.
5. No physical E-stop wiring, motor enable circuit, effective firmware timeout, Wi-Fi/browser-loss experiment, footprint/obstacle coverage, safe area, or operator/observer evidence is supplied. Unknown is not absent and is not verified. No motor-enabled qualification until its physical prerequisites are met.

## Execution gate register

Blueprint v1.0 is final as a construction plan. These gates block particular future actions, not publication of the plan. Owners are roles to assign, not people presumed to have accepted duties.

| Gate | Responsible role | Evidence to close it | Blocks |
|---|---|---|---|
| G1 Running baseline provenance | Junior / robot maintainer, P01 | Actual package directories and installed prefixes, source commit/hash and local changes, complete launch/service commands, source-vs-deployment diff, firmware sketch/binary/hash/baud and backup recovery procedure | P01 exit and hardware-specific changes |
| G2 Camera/geometry configuration | Junior / maintainer, P01 then P07/P13 validation | camera_ros parameters/calibration path, physical camera orientation, marker dictionary + physical size, wheel/encoder config and survey | Metric marker-follow qualification and motion precision claims |
| G3 Independent stop / electrical design | Maintainer + competent hardware reviewer, P05 | Nano/L298N wiring and supply review, independent motor-disable and deliberate reset, firmware timeout and fault evidence | Motor-enabled bench work until independent disable established; all floor work until P05/P06 gates |
| G4 Obstacle sensing | Robot maintainer, P05b/P06 | Hardware survey, actual driver/topic/frame/range/rate, coverage/staleness/invalid-return behavior; restore existing device or select funded hardware if absent | Floor research and physical Test 1D; no auto-clear fallback or caption substitute |
| G5 Area and measured stopping | Operator + separate observer, P13 | Area dimensions/conditions and assigned staff, passed bench gates, restricted commissioning measurements then frozen stopping/clearance thresholds | P13 A until prerequisites; general floor research until P13 B |
| G6 Provider access and cost | Owner, P09/P11 | Direct Gemini account availability, current model capability probe, user-set spend cap, approved image/data use policy | Paid/live-provider evaluation and caption trials; mocked translation development may proceed |
| G7 Study arrangements | Owner + supervisor/institution, P12a/P16 | Named recruiter/operator/observer, actual approval/determination, consent/retention policy, participants and grounded task definitions | Recruitment/data collection and Tests 2–3; synthetic instrument preparation can proceed |

## Targeted follow-up for the junior

Do not repeat the whole completed inventory. With the robot stationary and without launching/reconfiguring anything, capture the missing data below. Save errors as findings. All commands query current state; controller/firmware fault injection comes later.

```bash
# Locate packages; failure at the workspace root does not establish package Git state.
colcon list --base-paths "$HOME/amr_robot/src"
ros2 pkg prefix robot_control_pkg
ros2 pkg prefix aruco_follower
ros2 pkg prefix camera_ros
ros2 node info /diffbot
ros2 node info /twist_mux
ros2 topic list -t
ros2 topic info -v /cmd_vel_emergency
ros2 param dump /twist_mux
ros2 param dump /camera
ros2 param dump /aruco_detector
ros2 param dump /marker_follower
```

Use the observed package source directory below; this placeholder is not a path to paste literally:

```bash
ROBOT_SOURCE='<actual package repository directory from the inventory>'
git -C "$ROBOT_SOURCE" rev-parse --show-toplevel
git -C "$ROBOT_SOURCE" status --short
git -C "$ROBOT_SOURCE" rev-parse HEAD
```

Ask the maintainer for the exact startup/shutdown sequence and relevant nonsecret launch/configuration files, calibration file and firmware source/binary. Hash supplied files; retain modified-source diff if Git exists. Do not dump the commander's environment or credentials. Inspect physical sensor and E-stop hardware visually with the maintainer; do not disconnect Wi-Fi, flash firmware or test motion as an inventory shortcut.
