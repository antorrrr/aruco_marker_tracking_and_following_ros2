# Source audit and capability/topic map

Inspected 2026-09-24. **C** = verified by static source inspection; **T** = thesis assertion; **U** = unverified hardware/runtime fact; **P** = proposed design. Static source inspection does not prove execution on the robot. Neither checkout has Git metadata. No build, ROS integration test, paid model call, or physical experiment was run in this phase.

**2026-09-26 addendum:** The paragraph above and original map describe the initial source snapshots. A Git checkout and [PR #1](https://github.com/antorrrr/aruco_marker_tracking_and_following_ros2/pull/1) now exist in `aruco-pr-worktree`. **R** = reported robot observation from Antor's 2026-09-25 inventory, preserved in [raw evidence](evidence/robot-inventory-2026-09-25.txt) and interpreted in [reconciled baseline](robot-inventory-reconciled.md). R is not an independent live verification by this assistant. Raw report SHA-256: `741633c0f45f42e9c9b349f9651f0533af083eb1307a9de8304c99b3283ab46e`.

R resolves the platform as Pi 5/8 GB, Ubuntu 24.04.4 ARM64, Jazzy/Python 3.12.3, domain 42 with reported Fast DDS, Camera Module 3 CSI via camera_ros/libcamera. It establishes the current stamped command and odometry endpoints, actual mux publisher, populated CameraInfo and short-window ROS camera rate. `/scan` is not active in the supplied graph. E-stop, firmware watchdog, source/firmware revision, calibrated geometry, safe test area and network-loss behavior remain unverified. The historical maps below remain useful code evidence; use the reconciled table for current deployment decisions. P05b adds the missing sensing integration gate. Git failure at the robot workspace root does not establish package-subdirectory Git state.

## Inputs inspected

- Final thesis: `../Thesis Report Final 1931004.docx.pdf`, 44 PDF pages. Page numbers below are PDF file pages; printed body page = PDF page minus seven. Text was extracted across the document; the numerical results table on PDF p29 was also rendered and visually checked.
- ArUco: root README; all four follower/commander modules; package/build configuration; real and simulation launches; controller/mux/camera configuration; robot control Xacro, C++ system interface and serial communication; bundled Twist converter inventory. Simulation and dependency declarations were inspected, not executed.
- sia-bot: AGENTS.md; agent/provider/configuration; movement, safety, sensing, health and vision modules; ROSA tool registration/ROS command helpers; browser client, health/video/snapshot structure; contracts and representative unit/integration tests; Pixi/UI manifests and documentation inventory. The copied tree supplies the agent and UI but not the thesis's claimed nine-package robot stack.
- Every file in `../required-tests`: `Test_1.txt`, `Test_2.txt`, `Test_3.txt`, `Test_4.txt`, `Test_5.txt`, `Test_6.txt`, `Test_7.txt`, `test_8.txt`; all eight read in full. They are requirements/proposals, not results. `Test_4.txt` has a truncated final percentage example. No matching raw bags/CSV research results were found in the inspected source inventory.
- `sia-bot/AGENTS.md` refers repeatedly to Byterover tools. None are exposed in this session; no Byterover evidence is claimed or written. This is a new blueprint, not an approved implementation being resumed. No personal memory entries were relevant to the robot; none were used or updated.

## Capability map

| Capability | ArUco evidence (C unless noted) | sia-bot adaptation source | Plan disposition |
|---|---|---|---|
| Marker detection/calibrated pose | `aruco_follower/aruco_follower/aruco_detector.py`: image + CameraInfo, dictionary/size, solvePnP, pose/distance/debug. Returns before detection if CameraInfo absent. | No replacement needed | Retain; validate nonzero finite calibration, optical frame, image timestamps, marker size/dictionary; compatibility-test installed OpenCV API. Header comment about guessed intrinsics differs from actual wait-for-CameraInfo behavior. |
| Marker following | `marker_follower.py`: 20 Hz proportional loop, 0.18 m/s and 0.45 rad/s caps, 0.5 s receive-age timeout, final zero on normal exit. Can reverse when too close. | Bounded skill semantics only | Retain control law behind a lease/goal. Add source timestamp/freshness/finite-data tests; no unbounded following or autonomous resumption after stop. No obstacle avoidance is established by this code. |
| Language command | `web_target_commander.py`: Gemini JSON MIME request; only follow/stop/unknown, default model string `gemini-2.5-flash`. | `src/sia_agent/llm_config.py`, prompt ideas | Replace interpretation boundary. Existing action-only check and `int()` coercion are not a strict intent contract. Fallback extracts arbitrary digits and can turn unrelated numeric text into follow. Stop also waits for model call (8 s request timeout). |
| Web chat and live stream | Same commander: Flask, embedded page, MJPEG latest-frame resend at up to 15 sends/s; status poll every 1.5 s | `sia-ui/app/page.tsx`, `lib/ros-client.ts`, components | Retain lightweight web deployment by default, extract assets, add correlated events and separate stop endpoint. Browser sends are not completed action results. Resent frames must not count as new camera FPS. |
| Motor control and odometry | `robot_control_pkg/hardware/diffbot_system.cpp`, `hardware/include/robot_control_pkg/arduino_comms.hpp`, controller YAML | Do not port hardcoded bumperbot motor topics | Retain and harden. C++ deactivate logs success without sending zero; serial read timeout prints and returns a placeholder; encoder parsing uses `atoi`; motor writes lack acknowledgment. Firmware absent from target; firmware timeout not verified. |
| Primitive motion | ArUco provides visual following, not general distance/angle/arc/time skills | `src/sia_agent/tools/movement.py` | Rebuild feedback control. Forward distance has a best-effort monitor importing a cached `_latest_odom` binding; backward distance and rotate angle calculate duration and report starting pose rather than continuously terminating on fresh feedback. All tool starts use `auto_wait=False`; natural-language promises of sequencing are not sufficient. |
| Sequencing/cancel | Not implemented thesis-wide | `MovementManager` and wait/status tool concepts | Build a single-owner state machine. Old manager joins worker under its lock while worker also takes that lock at completion; shared stop state and thread replacement require redesign. Never carry that manager over unchanged. |
| E-stop | Marker clear sends `-1`; this is not a global/latched E-stop | `tools/safety.py`, `_handle_web_emergency` | Independent physical circuit + firmware timeout + final supervisor latch. Sia stop publishes zeros but permits later commands; source does not show a persistent interlock. |
| Obstacle sensing | `real_robot_launch.py` includes `rplidar_ros/rplidar_a2m8_launch.py`; no obstacle-to-stop integration found | Sensing provides odometry; external depth documents are proposals | Physical sensor presence U. Build measured obstacle guard with freshness/coverage checks. A camera description is not collision protection. If sensor absent, procurement/integration gate blocks Test 1D obstacle evidence and floor testing. |
| Network loss | No commander client lease; live follower can continue seeing a marker after browser disappears | UI health-monitor pings every 10 s, 5 s timeout | Build robot-local expiring control lease. A health indicator in a browser is not a motion watchdog. Controller 1 s timeout only helps if fresh nonzero publishers stop. |
| Status/health | target ID, detected flag, frame age | agent status methods, sensing/health modules | Adapt behavior, replace schemas. Old movement status is a placeholder to avoid deadlock. Health request and response share `/bumperbot/web_health`; handler responds to any payload, creating potential self-response feedback. Split channels/types. |
| Snapshot/description | MJPEG is present; no caption tool | `tools/vision.py`, snapshot_guard, response contracts, `useSnapshotStream.ts` | Adapt frame IDs, progress/final, busy/partial/error semantics and tests. Remove hardcoded OpenRouter GPT-4o-mini use and unlimited description timeout defaults. Never let caption content authorize movement. |
| Allowlisted skills | Three commander actions only | `_collect_tools` contains 21 explicit tools; `ROSA/ROSATools` also registers default ROS/system/log/calculation tools and aliases | Do not claim exactly 20 safe skills. Source includes ROS param/service helpers and shell-based ROS commands. New catalogue is explicit, versioned, and closed; no ROSA default tools or arbitrary endpoints. |
| Configuration/deployment | README targets Ubuntu 24.04/Jazzy; C++ Xacro says 57600 baud, ttyUSB0, 5903 encoder counts; two camera launch alternatives | Pixi targets `osx-arm64`, Humble; YAML and provider model defaults disagree | Preserve actual hardware environment after inventory. Fix manifests for used dependencies and installed launch paths. Do not transplant Mac Pixi lockfile, bumperbot topics or thesis baud/limits. |
| Existing tests | Mostly lint scaffolding in sim/converter; no observed end-to-end safety suite | Snapshot contract/unit/integration tests and synthetic camera fixture | Reuse cases, not claims. Tests may skip without rclpy; a schema example cannot prove runtime behavior. Require non-skipped target integration gates. |

## Current topics and proposed ownership

These were source-derived names at initial inspection. The reconciled report now supplies endpoint/QoS/parameter samples for controller/odom/camera; P01 closes missing source/launch and extra-node information. An entry in a launch/README alone is still not proof of a running node.

| Current source endpoint | Type and source | Proposed treatment |
|---|---|---|
| `/camera/image_raw`, `/camera/camera_info` | Image, CameraInfo; detector parameters | Keep configured names after camera-driver audit; one driver, calibrated optical frame. |
| `/aruco/target_marker_id` | Int32; transient-local publisher in commanders | Executor-owned target setting; perception selection is separate from motor authority. Clear on disarm/restart, never replay a motion lease. |
| `/aruco/marker_pose`, `/aruco/distance`, `/aruco/detected` | PoseStamped, Float32, Bool; detector | Retain for perception. Add coherent detection metadata/goal generation for follower tests; marker timeout alone is insufficient. |
| `/aruco/debug_image` | Image | Retain stream source; do not let JPEG encoding starve control. |
| `/cmd_vel_nav_stamped` | TwistStamped; follower → mux navigation priority 10, timeout 0.5 s | Remap to a leased follower candidate channel. |
| `/cmd_vel_joy` | Expected stamped input; mux priority 100, timeout 0.5 s | Verify joystick/stamper actual type; route through same final guard. Dead-man and exclusive source ownership. |
| `/cmd_vel_out` → `/diff_controller/cmd_vel` | Launch mux remap, stamped controller path | Remove direct actuator route; authority-bearing `/control/candidate` messages enter supervisor selector; supervisor alone publishes controller input. |
| `/diff_controller/odom` | Expected Odometry from controller; live verification required | Use configured fresh feedback for skills; confirm actual name with `ros2 topic list -t`. |
| `/scan` | Expected LaserScan from external lidar launch; not verified live | Parameterize; required sensor coverage/stopping envelope determines permitted motions. |
| `/bumperbot_controller/cmd_vel_unstamped`, `/bumperbot_controller/odom` | sia-bot hardcoded Twist/Odometry | Do not deploy; map semantics to verified ArUco controller endpoints. |
| `/bumperbot/web_command`, `/web_response`, `/web_status` under bumperbot | String JSON | Preserve user-visible behavior; migrate to local gateway + versioned `/research/events`, `/control/status`. Optional compatibility adapter only if a stated consumer needs it. |
| `/bumperbot/web_emergency` | Empty | Replace with dedicated stop service independent of LLM/web task queue. Physical stop does not rely on this service. |
| `/bumperbot/web_health` | String requests and replies on same channel | Split `/control/health_request` and `/control/health_response`, exact ping ID matching. |
| `/camera/image_raw/compressed`, `/bumperbot/web_image` | CompressedImage in sia-bot | Adapt snapshot behavior through `/vision/snapshot` and HTTP image endpoint; use explicit frame ID/age and request correlation. |

Proposed ROS interfaces (P02 owns definitions): `robot_interfaces/action/ExecutePlan.action`, `msg/VelocityCandidate.msg`, `msg/ControlLease.msg`, `msg/SafetyState.msg`, `msg/ExecutionEvent.msg`, `srv/SoftEstop.srv`; `/control/candidate` VelocityCandidate, `/control/lease` ControlLease, `/control/safety_state` SafetyState, `/control/execute_plan` action, `/control/soft_estop` service, `/research/events` ExecutionEvent. Gate reset is local/operator-only. VelocityCandidate atomically carries values, source/boot/lease/goal/generation/sequence/expiry authority; correlation in a separate topic is not a substitute. The supervisor emits stock TwistStamped only after validation. Existing twist_mux remains provenance/reference and is removed from direct actuation because it does not preserve this envelope.

## Thesis claim-to-evidence discrepancy register

| Thesis location | Claimed result/behavior | Audit disposition / needed evidence |
|---|---|---|
| PDF p17, p25 | Approximately 20 tools plus vision versus 15 tools | Source explicit list is 21, plus ROSA defaults/aliases. Publish actual new allowlist version and count, not any historical count. Test 1 validates boundary behavior. |
| PDF p28 vs p29 | Prose: primitives 100%, sequences 70%, response 1.2–2.1 s / sequence ~3.2 s. Table: 99%, 90%, 99%, 90%, 83%, 90%; 4.7–10 s. | Contradictory metrics and possible onset/completion confusion. Recollect with defined timing endpoints. Do not average or choose the more favorable account. |
| PDF p29 Table 4.1 | 99% of 20 distance trials; 99% of 10 time trials; 90% of 5 circles and 5 stops; 83% of 15 sequences | Not possible as ordinary binary trial proportions under stated denominators/normal rounding. 90% of 10 angles is possible. Recover original definition/raw records if available; otherwise mark unsupported and replace. Never infer success counts from these percentages. |
| PDF pp35–36 | Guaranteed sequence success, 100% correct execution | Conflicts with 70%/83% elsewhere. Replace with measured whole-plan/per-step results (Test 5), no guarantees. |
| PDF p28 | ±5 cm, ±2°, 1.8 s onset, 0.4 s stop, <100 MB, 99.9% delivery, six hours | Undefined spread, scope, denominators and clock uncertainty. New measured errors, timing decomposition, process/RSS scope, send/receive ledgers and six-hour evidence required. |
| PDF pp27,29,40 | SUS/TLX future work, yet participant benefits and evaluations described | No participant dataset inspected. Run Tests 2–3 with approved protocol; do not imply historical study completion. |
| PDF p26 | CLI/GUI/web baselines and safety/knowledge/background ablations | No inspected results establish those comparisons. New chosen two-condition study; unsafe ablations only in simulation and only if added to protocol. |
| PDF p29 | 11.7 ±1.2 FPS over ten trials, 290 ms latency, no interference; all captions accurate, 4.6 s total | Re-measure unique frames and browser render timing, collect labeled captions and raw stages. Capability is not proof of accuracy or non-interference. See vision supplement and Test 7. |
| PDF pp15,23,25 | Pi 4, Nano, IMU, laser, nine packages, Humble/22.04, 115200 baud | Hardware historical claims, not present-robot facts. README says Jazzy; target Xacro says 57600. Resolve via inventory; never silently replace. |
| PDF pp21,34,36 | Quotas, safe reaction to communication/sensor problems, pausing navigation during capture, production readiness | Not established by inspected execution paths. Implement selected behavior, test it, or narrow the claim. Treat healthcare/logistics/environment benefits as motivation, not demonstrated deployment outcomes. |
| Required Test 2 | SUS/TLX references “10 and 11”; universal novelty of retry metric; SUS >68 “good” | Thesis actually cites SUS/TLX at [14]/[15]. Novelty needs a separate literature review. SUS is not a percentage or a universal pass threshold; report sample/distribution and context. |
| Required Test 5 | Success graph “will slope downward” | Hypothesis only. Report observed slope including flat/increasing data; never force expected trend. |
| Required Test 8 | Bag alone yields total sent and received | A bag observes one subscriber, not endpoint delivery. Add publisher and browser ledgers, sequences, restart IDs and a reconciler. |

## Scope retained and omissions justified

Retain bounded forward/backward/time/turn/circle skills, multi-step plans, marker following, stop/cancel, live camera, snapshot/description (pending D4), real progress/status/health, and research logging. Keep CLI/keyboard for the comparison through the same guard. Preserve firmware/build/config/calibration and third-party attributions in the sole deployment source.

With confirmed D3, omit ROSA arbitrary ROS tools, shell access, runtime model picker, Mac development environment, and simultaneous multi-user actuation. One operator lease plus read-only observers is sufficient for this study. Next.js/rosbridge internals are not required if a smaller Flask/static gateway reproduces the selected behavior; disclose the architecture change. Do not claim rosbridge compliance if it is omitted. Nav2/SLAM, manipulation, speech recognition, healthcare readiness, energy savings and universal obstacle avoidance are outside this bounded paper unless separately built/evaluated. Clean unnecessary dependencies only after a clean-build proof; installed packages alone do not mean these features exist.

External primary references checked for design: [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) supports schema-constrained output but requires application validation; [Jazzy diff-drive controller](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html) documents stamped velocity input and timeout configuration. Recheck exact API/model/ROS package versions when P01/P09 pin the environment; current documentation does not prove account access or installed robot behavior.

## Input fingerprints

SHA-256 read from the local inputs during blueprint preparation; use these to detect replacement before execution. Code source-tree hashes are assigned in P01 after the running deployment is inventoried.

| Input | SHA-256 |
|---|---|
| `Thesis Report Final 1931004.docx.pdf` | `c21c85132fea74cd1af2b7f7b4dd5e6dafba4ade69b049dc84dff4862a5f56f4` |
| `required-tests/Test_1.txt` | `67dca5900257c0546a8bde6e438e4db779611eb7207fa62606735e5c6b065c09` |
| `required-tests/Test_2.txt` | `ef8173a0cf7beb8e2cb724cc39c3bf5930264e0211099ca0dda7819ea2515971` |
| `required-tests/Test_3.txt` | `331cee2da17480164f44172dd02935c32baab51f27a132bb1707fb5b847ddc47` |
| `required-tests/Test_4.txt` | `20a5236443108db6c1273684fe239ea23e66e774bca5f07951717b6ec086e846` |
| `required-tests/Test_5.txt` | `d15e0cc3278e8f308f476a65fbdd9aaeb8f5adc38174007f290bcf67142a469b` |
| `required-tests/Test_6.txt` | `3efb93d3317d55ba38fab3a857c5e536d124c9b34fa29c3379592cf5f8d4c194` |
| `required-tests/Test_7.txt` | `84e8de33d4ace6e041ee0fc58bb3665de5a899a8e11e310d058268a93b9c9d48` |
| `required-tests/test_8.txt` | `9b015a7d44e1f12b0b856166ef6211e3607887bad097b394575af59fcecbb198` |
