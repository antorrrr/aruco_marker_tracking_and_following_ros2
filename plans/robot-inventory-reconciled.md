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

This is the **complete P01 collection handoff**. The first two reports established the platform and much of the ROS graph; do not rerun those measurements just to fill a form. Work on the existing robot **stationary**, without launching, reconfiguring, flashing, publishing motion, disconnecting Wi-Fi, or testing E-stop effectiveness. Ask the maintainer which existing procedure disables motors before touching wiring. If none is known, photograph/describe without manipulating it and record `unknown`. Git/ROS/hash queries only read state; the backup steps below write evidence files under a new private folder on the Pi and later a separate storage location, not robot configuration. Preserve failures as evidence. Do not include `.env`, tokens, passwords, credential-bearing Git remote URLs, private keys or participant data in returned material. Review outputs locally before sharing.

### A. Source provenance for **all seven** packages

The previous Git attempt failed because a literal placeholder was used. Run this block exactly in Bash on the Pi. It prints each actual directory and checks Git **inside** it. A nonzero Git exit is a result for that package, not a reason to initialize Git. `git diff --stat` shows changed-file counts; if a package is dirty, privately retain staged and unstaged full diffs **and untracked source files** after checking for secrets. A commit ID alone does not capture local changes. Review `git remote -v` output for embedded credentials before returning it.

```bash
for package_dir in \
  "$HOME/amr_robot/src/aruco_follower" \
  "$HOME/amr_robot/src/robot_control_pkg" \
  "$HOME/amr_robot/src/diffbot_agent_pkg" \
  "$HOME/amr_robot/src/serial_motor_demo/serial_motor_demo" \
  "$HOME/amr_robot/src/serial_motor_demo/serial_motor_demo_msgs" \
  "$HOME/amr_robot/src/sim_pkg" \
  "$HOME/amr_robot/src/twist_stamper-main"; do
  printf '\nPACKAGE %s\n' "$package_dir"
  if test ! -d "$package_dir"; then printf 'MISSING DIRECTORY\n'; continue; fi
  if git -C "$package_dir" rev-parse --show-toplevel; then
    git -C "$package_dir" rev-parse HEAD
    git -C "$package_dir" status --short
    git -C "$package_dir" diff --stat
    git -C "$package_dir" diff --cached --stat
    git -C "$package_dir" remote -v
  else
    printf 'NO GIT FOUND AT THIS PACKAGE PATH\n'
  fi
done
```

For every package, preserve a **private source copy** and SHA-256 manifest; a dirty Git checkout needs both its HEAD and modified/untracked files. The following creates an owner-readable source archive without touching deployed binaries. It excludes common credential/generated paths, but still inspect it privately for secrets before transferring it. Do **not** attach it to a public PR. Keep the archive, hash and any error output together. The seven package paths above include two nested demo packages, so archive their parent once. A new timestamp avoids overwriting a previous packet.

```bash
umask 077
mkdir -p "$HOME/p01-private"
snapshot_stamp=$(date -u +%Y%m%dT%H%M%SZ)
snapshot_path="$HOME/p01-private/robot-source-$snapshot_stamp.tar.gz"
tar -C "$HOME/amr_robot/src" \
  --exclude='*/.git' --exclude='*/__pycache__' --exclude='*.pyc' \
  --exclude='*.env' --exclude='*.pem' --exclude='*.key' \
  -czf "$snapshot_path" \
  aruco_follower robot_control_pkg diffbot_agent_pkg \
  serial_motor_demo sim_pkg twist_stamper-main
sha256sum "$snapshot_path"
gzip -t "$snapshot_path"
tar -tzf "$snapshot_path" > "$HOME/p01-private/source-file-list-$snapshot_stamp.txt"
cd "$HOME/amr_robot/src"
find aruco_follower robot_control_pkg diffbot_agent_pkg serial_motor_demo sim_pkg twist_stamper-main \
  -type f ! -path '*/.git/*' ! -path '*/__pycache__/*' \
  ! -name '*.pyc' ! -name '*.env' ! -name '*.pem' ! -name '*.key' -print0 \
  | sort -z | xargs -0 sha256sum > "$HOME/p01-private/source-file-sha256-$snapshot_stamp.txt"
sha256sum "$HOME/p01-private/source-file-sha256-$snapshot_stamp.txt"
find aruco_follower robot_control_pkg diffbot_agent_pkg serial_motor_demo sim_pkg twist_stamper-main \
  -type l -printf '%p -> %l\n' > "$HOME/p01-private/source-symlinks-$snapshot_stamp.txt"
for package_name in aruco_follower robot_control_pkg diffbot_agent \
  serial_motor_demo serial_motor_demo_msgs sim_pkg twist_stamper; do
  printf '\nINSTALLED PREFIX %s\n' "$package_name"
  ros2 pkg prefix "$package_name"
done
```

**Test the backup without affecting the running workspace:** extract the archive to a new private directory and check all included source-file hashes. The manifest was created relative to `~/amr_robot/src`, so the check runs from the extraction root. Keep the output, including failures. Check the symlink list: a link pointing outside the archive needs an independently preserved target; a link that only resolves because the live workspace exists is not a valid restore. `gzip -t` alone proves compressed-stream readability, not that source was restored. Arrange a second copy on a separate laptop/drive/private store; compare its SHA-256 with the original and repeat extraction/hash checks there before P01 exit.

```bash
restore_dir=$(mktemp -d "$HOME/p01-private/restore-XXXXXXXX")
tar -xzf "$snapshot_path" -C "$restore_dir"
cd "$restore_dir"
sha256sum --check "$HOME/p01-private/source-file-sha256-$snapshot_stamp.txt"
find . -type l -printf '%p -> %l\n'
```

The archive excludes `.git`, so return Git roots/HEADs/status/remotes separately. Review `.yaml`, `.py` and shell files for embedded keys before sending copies. An installed-prefix error is a finding; record it instead of installing a package. The owner uses this snapshot to compare live code with ArUco and sia-bot. If an archive/package or external symlink target is missing or unrestorable, G1 remains open.

### B. Actual launch and command ownership

Ask the person who normally starts the robot to **write down the exact commands or service/unit names in order**, including how camera, controllers, detector, follower, web commander, LLM agent, joystick, firmware link and any demos are started and stopped. Record whether any service starts at boot, which processes run on Pi versus laptop, and the normal terminal setup (`source` commands, domain 42, Fast DDS). Do not start or stop them for this inventory. Obtain nonsecret launch files, parameter YAMLs and service units plus their hashes. The normal launch sequence is still unknown and is required to reproduce the system.

Inspect the current sources of `diffbot_agent_pkg` and `serial_motor_demo*` for velocity publishing or serial writes. Record whether they are deployed, examples, or independent motor paths, using file/line evidence and the maintainer's startup account. The live `/diffbot` node's sparse interfaces do not establish its role. Record every present publisher on the following topics, plus the web commander's subscriptions; zero publishers is meaningful. Do not infer that the emergency input works merely because it has priority 200.

```bash
ros2 topic info -v /cmd_vel_llm
ros2 topic info -v /cmd_vel_joy
ros2 topic info -v /cmd_vel_nav_stamped
ros2 topic info -v /cmd_vel_emergency
ros2 topic info -v /diff_controller/cmd_vel
ros2 node info /web_target_commander
ros2 node info /diffbot
ros2 pkg prefix diffbot_agent
ros2 pkg prefix serial_motor_demo
ros2 pkg prefix serial_motor_demo_msgs
```

The first report saw zero emergency publishers; repeat that read-only publisher query to capture current ownership, not as a stop test. Preserve `/twist_mux` parameters already collected (priorities 200/100/50/10, 0.5-s timeouts). State topic type/QoS or namespace changes. Ask the maintainer to match each active node, especially `/diffbot`, to its launch command/process and installed package. Review this process listing **on the robot** for paths and boot/service ownership; it may contain credentials if a launcher passed them as arguments, so redact before returning. A ROS node name or `ros2 pkg prefix` alone does not establish executed code identity.

```bash
ps -eo pid,ppid,comm,args | grep -E '[r]os2|[c]amera_node|[a]ruco_detector|[m]arker_follower|[w]eb_target_commander|[d]iffbot|[t]wist_mux|[r]os2_control_node'
```

Capture the **effective installed payload**, resolved symlink targets and file hashes for every overlay prefix. This exposes installed Python modules, launch/config copies or C++ plugins that differ from the source archive. Keep these files private and screen them for secrets. An executable may be a wrapper around a Python module; identify both. Preserve an installed-prefix archive for comparison even if filenames appear to match source. Record missing prefixes instead of silently skipping them.

```bash
installed_stamp=$(date -u +%Y%m%dT%H%M%SZ)
for package_name in aruco_follower robot_control_pkg diffbot_agent \
  serial_motor_demo serial_motor_demo_msgs sim_pkg twist_stamper; do
  printf '\nINSTALLED FILES %s\n' "$package_name"
  if prefix=$(ros2 pkg prefix "$package_name"); then
    printf 'PREFIX %s\n' "$prefix"
    find "$prefix" -type l -printf '%p -> %l\n'
    find -L "$prefix" -type f -print0 | sort -z | xargs -0 -r sha256sum \
      > "$HOME/p01-private/installed-$package_name-$installed_stamp.sha256"
    sha256sum "$HOME/p01-private/installed-$package_name-$installed_stamp.sha256"
    tar -C "$prefix" --exclude='*.env' --exclude='*.pem' --exclude='*.key' \
      -czf "$HOME/p01-private/installed-$package_name-$installed_stamp.tar.gz" .
    sha256sum "$HOME/p01-private/installed-$package_name-$installed_stamp.tar.gz"
  else
    printf 'NO INSTALLED PREFIX FOUND\n'
  fi
done
```

Use the process/launch mapping and installed hash manifests to compare running package payload with preserved source. If the effective module/library cannot be identified, or the installed code differs without a preserved copy and explanation, G1 stays open. Do not stop, restart or rebuild the live stack to make outputs match.

### C. Camera, marker and wheel geometry

The configured camera URL points to an installed YAML file. Record its file hash **and contents after checking for secrets**, identify the corresponding source file, hash that too, and state whether the contents match. Record camera mount direction/height and whether its physical optical axis aligns with `camera_link_optical`; configured `orientation: 0` alone does not prove physical alignment. Verify calibration was made for this Camera Module 3 at 640×480 and the current crop/mode, or write `unverified` with the calibration owner. Do not recalibrate during P01.

```bash
ls -l "$HOME/amr_robot/install/robot_control_pkg/share/robot_control_pkg/config/camera_calibration.yaml"
sha256sum "$HOME/amr_robot/install/robot_control_pkg/share/robot_control_pkg/config/camera_calibration.yaml"
find "$HOME/amr_robot/src/robot_control_pkg" -name 'camera_calibration.yaml' -print
find "$HOME/amr_robot/src/robot_control_pkg" -name 'camera_calibration.yaml' -type f -exec sha256sum {} +
```

Photograph the printed target marker with a ruler. Record its printed ID, measured **black-square outer side** in millimetres, and how its dictionary was generated or confirmed. Active detector configuration is `DICT_7X7_50`, 0.1 m; do not silently use the copied code's `DICT_5X5_100` default. Record the camera-to-base transform, wheel radius/separation measurements, encoder counts per revolution and wheel sign source. Existing Xacro/controller numbers are configuration observations, not measured geometry. If a dimension cannot be measured safely, mark it unverified and assign G2/P13.

### D. Firmware, power and physical safety facts

Ask the maintainer to point to the **complete firmware project corresponding to the flashed Nano**: main sketch, included headers/configuration, custom libraries, any compiled hex/binary, exact Arduino CLI build/upload commands, board FQBN, tool/core/library versions, serial baud/protocol and known-good restore copy. A single `.ino`, a generic `hbrobotics/ros_arduino_bridge` URL, or a backup location alone is insufficient. Record a flash log/date or other evidence linking the project/build to this Nano. If the project lives on the maintainer's laptop, capture and hash it there; do not call a Pi copy the installed source without checking. Collect wiring/schematic or labeled photographs for Nano, CH340, L298N, battery, motor-driver enable and any E-stop switch. Record battery voltage/power isolation and any **prior witnessed** Pi/serial/Wi-Fi-loss behavior. Do not create a new failure trial during inventory.

Once the maintainer identifies the project directory/files, enter their **absolute paths** when prompted below. This creates a private archive and hashes; it does not upload or read the controller. Inspect the archive for credentials and identify custom libraries outside the project before transfer. If no compiled binary was kept, say so. `arduino-cli` commands query toolchains only; if unavailable, get version/build details from the maintainer's machine.

```bash
umask 077
mkdir -p "$HOME/p01-private"
firmware_stamp=$(date -u +%Y%m%dT%H%M%SZ)
read -r -p 'Absolute path to the complete flashed Nano project directory: ' firmware_project_dir
if test -d "$firmware_project_dir"; then
  tar -C "$firmware_project_dir" --exclude='*/.git' --exclude='*.env' \
    -czf "$HOME/p01-private/nano-firmware-$firmware_stamp.tar.gz" .
  sha256sum "$HOME/p01-private/nano-firmware-$firmware_stamp.tar.gz"
  gzip -t "$HOME/p01-private/nano-firmware-$firmware_stamp.tar.gz"
  (cd "$firmware_project_dir" && find . -type f ! -path '*/.git/*' ! -name '*.env' \
    -print0 | sort -z | xargs -0 -r sha256sum) \
    > "$HOME/p01-private/nano-firmware-$firmware_stamp.sha256"
  sha256sum "$HOME/p01-private/nano-firmware-$firmware_stamp.sha256"
else printf 'FIRMWARE PROJECT DIRECTORY NOT FOUND\n'; fi
read -r -p 'Absolute path to preserved compiled firmware (Enter if none): ' firmware_binary_path
if test -z "$firmware_binary_path"; then printf 'NO COMPILED BACKUP IDENTIFIED\n'; elif test -f "$firmware_binary_path"; then sha256sum "$firmware_binary_path"; else printf 'BINARY FILE NOT FOUND\n'; fi
if command -v arduino-cli >/dev/null 2>&1; then
  arduino-cli board list
  arduino-cli core list
  arduino-cli lib list
else printf 'ARDUINO CLI NOT ON THIS COMPUTER\n'; fi
```

Before declaring the backup usable, extract the firmware archive into a new private directory and run `sha256sum --check` against its manifest there, as in section A; repeat on the separate off-robot copy. Preserve a second firmware-project copy off robot with matching archive hash. For **every custom library outside the project**, preserve its source/version/hash and state where the build found it; otherwise the project is not reproducible. If the binary is outside the project, privately preserve a copy too and record its hash. If there is no binary, document a pinned reconstruction recipe and evidence linking it to the flashed controller; **do not claim byte-for-byte recovery of installed firmware**. If build inputs/versions or flashed-source association cannot be established, G1 remains open. A motor-safe flash/restore rehearsal belongs to P05, not P01.

Separately record whether a physical E-stop exists, exactly which electrical path it interrupts, how it resets, and whether firmware has a command-age watchdog, with file/line or maintainer evidence. `unknown` is acceptable **for P01 documentation** but leaves G3 open; it is not a verified safety feature. Inspect whether a range sensor is physically fitted, model/mount/coverage and why `/scan` is absent; `unknown` leaves G4/P05b open. Record safe-area dimensions, access control and likely operator/independent stop observer or assign G5. No physical motion, disconnection, firmware upload or electrical modification belongs to P01.

### E. Study grounding inputs for D8

Ask the study owner to identify a candidate room/window for the six study tasks, a fixed reference frame and whether the window bearing from a standardized robot start pose can be surveyed. Record whether a circle route with a stated radius/direction fits the candidate area. Do not move the robot during P01 to measure this. Record the intended clarification when a command names an ambiguous landmark, and who will approve task wording. If the site/task owner has not decided, write `D8 pending` with a named owner and decision date. P12a freezes surveyed values, tolerances and scripts before participants; P01 gathers decision inputs only.

### F. Return package and P01 closure check

Give the owner one dated, labeled packet: (1) raw outputs/errors from A–D, locally screened for credentials; (2) per-package Git root/commit/status/remote or explicit no-Git, **restored** private source snapshot and per-file hashes, and verified off-robot backup; (3) process/node/installed-payload mapping with resolved symlinks, source-versus-installed differences and exact startup/shutdown/service/launch instructions; (4) source and installed camera calibration copies/hashes, marker and geometry observations; (5) complete firmware project/toolchain/build/reconstruction evidence, optional binary hash, baud and wiring; (6) G2–G5 known/unknown/owner table; (7) D8 site/window/circle/clarification owner. Keep raw artifacts untouched and include SHA-256 manifests for copies. Do not put secrets or private source archives in a public PR.

Also provide the **P02 input sheet**: effective robot computer/OS/ROS/domain/RMW, source archive hash, active executable/launch order, each motor-command topic with type/QoS/publisher node, controller/odometry names and configured bounds, actual camera mode/calibration/marker settings, current obstacle input (or absent), current independent-stop/watchdog evidence (or unknown), and the status of any extra motor/LLM path. Mark uncertain fields `unknown → G3/G4/...`, never `working`. The owner then compares live package sources/configuration against this PR's ArUco tree and sia-bot, records required adaptations/licensing in P01 and hands the versioned input sheet to P02.

P01 can be marked **verified** only when running source **and installed payload** identity and launch order are reconstructable, firmware project/baud/flashed-source evidence are preserved, source/firmware backups have an evidenced offline recovery route, differences from the target repository are documented, and P02 has a versioned input sheet. P01 requires the installed/source calibration file **identity** and actual printed marker description/size to be recorded, or a named G2 blocker if access/measurement is impossible. Calibration **accuracy**, wheel geometry precision and stopping distances are later G2/P07/P13 qualification, so their lack of test results does not by itself hold P01 open. Unknown physical E-stop, firmware watchdog, obstacle sensing, Wi-Fi stopping and area performance are explicitly assigned to G3/G4/G5, not counted as verified because P01 closes. If running-source identity, firmware/baud/reconstruction, recoverable snapshot or normal launch remain unknown, P01 stays open. The owner records the exit manifest before P02 contracts and P04 clean-build work.
