# Robot inventory: reconciled baseline and remaining gates

Inventory collected by Antor on 2026-09-25; supplied by the owner on 2026-09-26. This is user-supplied observation, not an independent remote session or safety qualification. The complete [submitted report](evidence/robot-inventory-2026-09-25.txt) is retained unchanged, including its contradictory final summary. Source command blocks take precedence over that summary. `[cite: 1]` strings in the submission have no independently supplied citation target.

**Follow-up received 2026-09-28:** [raw provenance and ROS output](evidence/robot-provenance-followup-2026-09-28.txt), SHA-256 `b2881f60325c7580cb47f9703ec1f58318726dac5821be469904ab2d7296fee3`. It adds package locations, source/install overlays, mux inputs/priorities, the camera calibration URL, and detector/follower configuration. This is user-supplied output, not independent live verification or a safety test. Its Git commands used the literal placeholder `<actual package repository directory from the inventory>` and did not test the located directories.

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

### Follow-up facts and interpretation

| Evidence | Updated baseline / consequence |
|---|---|
| `colcon list` | Source workspace contains `aruco_follower`, `robot_control_pkg`, `sim_pkg`, `twist_stamper`, plus **`diffbot_agent`** at `src/diffbot_agent_pkg`, **`serial_motor_demo`** and **`serial_motor_demo_msgs`** in `src/serial_motor_demo`. The latter three are absent from the supplied Windows ArUco tree; P01 must audit their role and whether they are needed in the sole deployment repo. Package presence does not prove runtime activity. |
| `ros2 pkg prefix` | ArUco follower and robot control resolve to `/home/pi/amr_robot/install/{aruco_follower,robot_control_pkg}`; camera_ros resolves to `/opt/ros/jazzy`. This shows overlay ownership in the reported snapshot, not commit identity or launch order. |
| `/diffbot` node info | Only parameter and rosout interfaces appear; no motor/topic subscription or publication in this snapshot. Identify its executable/process without assigning behavior based on its name. |
| `/twist_mux` info and parameters | Four stamped inputs: `/cmd_vel_emergency` priority 200, `/cmd_vel_joy` 100, `/cmd_vel_llm` 50, `/cmd_vel_nav_stamped` 10; each has a 0.5 s timeout. Output is `/diff_controller/cmd_vel` and diagnostics. This is arbitration, not authority validation or a persistent stop latch. `cmd_vel_llm` is configured in the running graph even though the copied ArUco README does not describe it. Identify every publisher and audit `diffbot_agent_pkg`. |
| `ros2 topic info -v /cmd_vel_emergency` | One best-effort/volatile mux subscriber, **zero publishers** at observation. No software E-stop publisher is evidenced then; priority 200 cannot help without a publisher. Physical E-stop wiring and firmware watchdog remain unknown. |
| Full topic list | Confirms raw **and compressed** camera topics, ArUco topics, four mux inputs, odometry and stamped controller input. `/scan` remains absent. Compressed transport existence does not prove browser consumption or caption behavior. |
| `/camera` parameters | camera_ros configured 640×480, `camera_link_optical`, orientation parameter 0, JPEG quality 95 and `camera_info_url=file:///home/pi/amr_robot/install/robot_control_pkg/share/robot_control_pkg/config/camera_calibration.yaml`. The path is configured; file content, physical orientation, mode match and calibration accuracy remain unverified. Preserve and hash source and installed calibration files. |
| `/aruco_detector` parameters | Active dictionary **`DICT_7X7_50`**, marker size configured **0.1 m**, image `/camera/image_raw`, info `/camera/camera_info`, target -1 at inspection, debug enabled. The copied detector default `DICT_5X5_100` is not the active profile. Measure the printed marker and confirm its dictionary before treating pose as metric evidence. |
| `/marker_follower` parameters | 20 Hz, 0.5 m standoff, 0.5 s marker timeout, max 0.18 m/s and 0.45 rad/s, kp 0.6/1.2 and 0.03 m/rad deadbands; these match copied defaults at inspection. They do not establish tracking accuracy, obstacle response or network-loss stopping. |
| Placeholder Git commands | `ROBOT_SOURCE` was set literally to `<actual package repository directory from the inventory>`; `git -C` failed because it does not exist. Check actual `src/...` directories or hash their trees if unversioned. |

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
2. Initial Git commands ran at `~/amr_robot`; follow-up commands ran against a literal placeholder. Neither checked an actual package directory. Package **locations** are now known; Git state, source hashes/changes and launch provenance remain unresolved. Do not initialize Git across the workspace or assume Windows source equals the running overlay.
3. The follow-up supplies raw `colcon list`, `/twist_mux`/`/diffbot` info, complete topic list and selected parameter dumps. Full `ros2 doctor` and `ros2 node list` remain narrative summaries. Treat Fast DDS as reported evidence. The detailed endpoint and parameter outputs are the stronger routing basis.
4. CameraInfo and odometry timestamps are from separate command invocations; no time-synchronization measurement or clock uncertainty is supplied. Re-collect synchronized timing only when qualifying latency.
5. No physical E-stop wiring, motor enable circuit, effective firmware timeout, Wi-Fi/browser-loss experiment, footprint/obstacle coverage, safe area, or operator/observer evidence is supplied. Unknown is not absent and is not verified. No motor-enabled qualification until its physical prerequisites are met.

## Execution gate register

Blueprint v1.0 is final as a construction plan. These gates block particular future actions, not publication of the plan. Owners are roles to assign, not people presumed to have accepted duties.

| Gate | Responsible role | Evidence to close it | Blocks |
|---|---|---|---|
| G1 Running baseline provenance | Junior / robot maintainer, P01 | **Known:** package locations and two installed prefixes. **Still required:** per-package Git state or source hashes/local modifications, launch/service commands, `diffbot_agent_pkg` and `serial_motor_demo*` code/dependency audit, source-vs-deployment diff, firmware sketch/binary/hash/baud and backup recovery | P01 exit and hardware-specific changes |
| G2 Camera/geometry configuration | Junior / maintainer, P01 then P07/P13 validation | **Known:** camera_ros parameters and configured installed calibration URL; detector `DICT_7X7_50`/0.1 m and follower settings. **Still required:** source+installed calibration hash/content/mode match, physical camera orientation, printed marker dictionary/size, wheel/encoder survey | Metric marker-follow qualification and motion precision claims |
| G3 Independent stop / electrical design | Maintainer + competent hardware reviewer, P05 | Nano/L298N wiring and supply review, independent motor-disable and deliberate reset, firmware timeout and fault evidence | Motor-enabled bench work until independent disable established; all floor work until P05/P06 gates |
| G4 Obstacle sensing | Robot maintainer, P05b/P06 | Hardware survey, actual driver/topic/frame/range/rate, coverage/staleness/invalid-return behavior; restore existing device or select funded hardware if absent | Floor research and physical Test 1D; no auto-clear fallback or caption substitute |
| G5 Area and measured stopping | Operator + separate observer, P13 | Area dimensions/conditions and assigned staff, passed bench gates, restricted commissioning measurements then frozen stopping/clearance thresholds | P13 A until prerequisites; general floor research until P13 B |
| G6 Provider access and cost | Owner, P09/P11 | Direct Gemini account availability, current model capability probe, user-set spend cap, approved image/data use policy | Paid/live-provider evaluation and caption trials; mocked translation development may proceed |
| G7 Study arrangements | Owner + supervisor/institution, P12a/P16 | Named recruiter/operator/observer, actual approval/determination, consent/retention policy, participants and grounded task definitions | Recruitment/data collection and Tests 2–3; synthetic instrument preparation can proceed |

## Targeted follow-up for the junior

Do not repeat completed queries or the failed placeholder commands. With the robot stationary and without launching/reconfiguring anything, capture only missing data. Save errors as findings. These commands query state; controller/firmware fault injection comes later. Protect credentials if inspecting files.

```bash
# These package paths came from colcon; no placeholder substitution is needed.
git -C "$HOME/amr_robot/src/aruco_follower" status --short
git -C "$HOME/amr_robot/src/aruco_follower" rev-parse HEAD
git -C "$HOME/amr_robot/src/robot_control_pkg" status --short
git -C "$HOME/amr_robot/src/robot_control_pkg" rev-parse HEAD
git -C "$HOME/amr_robot/src/diffbot_agent_pkg" status --short
git -C "$HOME/amr_robot/src/diffbot_agent_pkg" rev-parse HEAD
git -C "$HOME/amr_robot/src/serial_motor_demo" status --short
git -C "$HOME/amr_robot/src/serial_motor_demo" rev-parse HEAD
ls -l "$HOME/amr_robot/install/robot_control_pkg/share/robot_control_pkg/config/camera_calibration.yaml"
sha256sum "$HOME/amr_robot/install/robot_control_pkg/share/robot_control_pkg/config/camera_calibration.yaml"
ros2 topic info -v /cmd_vel_llm
ros2 topic info -v /cmd_vel_joy
ros2 topic info -v /cmd_vel_nav_stamped
ros2 topic info -v /camera/image_raw/compressed
ros2 node info /web_target_commander
ros2 param dump /diffbot
```

If a package is not a Git checkout, record no-Git for that package and preserve a source tree hash/backup; do not initialize it. Ask the maintainer for exact startup/shutdown steps and relevant nonsecret launch/config files, source calibration file, firmware source/binary and serial baud. Hash supplied files and retain modified-source diffs if Git exists. Inspect `diffbot_agent_pkg` for `/cmd_vel_llm` and any direct controller/serial path; inspect `serial_motor_demo*` to decide whether deployed or only example code. A package name does not answer this. Do not dump the commander's environment or credentials. Inspect physical sensor/E-stop hardware with the maintainer; do not disconnect Wi-Fi, flash firmware or test motion during inventory.
