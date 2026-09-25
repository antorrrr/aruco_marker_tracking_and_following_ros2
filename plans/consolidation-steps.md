# One-PR work packages

Read `consolidation-blueprint.md` for decisions/dependencies and `consolidation-source-audit.md` for verified baseline. All work is future work. Each package is a reviewable PR; evidence collection PRs contain protocol-linked manifests/results, not uncontrolled large media files. Original/raw evidence goes into a backed-up immutable store with hashes and resolvable locations. Do not create a PR that also performs an unrelated cleanup.

## Shared execution rules

Cold start for **every** PR: read its brief below, the named contract/protocol and predecessor exit manifests; inspect current `AGENTS.md`, `git status --short`, `git log -5 --oneline`, dependency versions and actual files. Stop on unexplained source drift. Never use a stale blueprint path as proof that a file exists. After P01 establishes history, branch from the verified integration head; submit a bounded PR and retain its URL/hash. Until a remote is available, use local commits/patches with the same review gates. Do not push or publish participant data.

Verification commands below use Bash on the verified Ubuntu robot or matching test host, from the repository root unless marked `WS`. Define `REPO` as the checkout and `WS` as its colcon workspace. New command interfaces are specified here for the owning PR to implement, not tools available during blueprint creation. Pure tests use synthetic inputs with motor-disabled/default-off transports. Live tests must carry explicit bench/physical profiles. Every exit manifest records commands, versions, outputs, tests skipped and why; skipped required tests fail the gate.

Rollback for any code change: stop/disarm with the local operator, verify halt, disable motor enable, revert the PR using Git rather than copying old build products, rebuild from its pinned dependencies, and repeat no-motion smoke checks. Do not automatically restart motion. Preserve all evidence and configuration snapshots. Specific rollback clauses below add to this procedure.

## P01 — Preserve baseline and establish actual platform (1–2 days)

**Cold-start brief:** The supplied ArUco folder is the deployment target, but both local folders lack `.git`. README Jazzy and thesis Humble conflict; firmware, sensors and E-stop are unverified. This PR is inventory/provenance only, no changes to motor behavior. Strongest review recommended.

**Components:** new `docs/hardware-inventory.md`, `docs/decisions.md`, `research/provenance/source-manifest.json`, `docs/licenses.md`, `.gitignore`; owner-approved source history; sibling `sia-bot` and thesis read-only inputs.

**Tasks:** hash source snapshots and all eight test files; preserve independent backups; resolve D1/D2 and scope/D4/D5 answers without storing secrets. Capture live node/topic/type/QoS/publisher/parameter/package inventory, exact startup commands, robot computer/OS/RAM, wiring and camera calibration, firmware source/hash/build/flash procedure, sensors and test area. Diff running source against supplied copy. Confirm upstream ownership/license/attribution (target README author differs from thesis author), verified remote and default branch; import local changes without overwriting working hardware checkout. Archive original thesis and test requirements with access-controlled provenance. Record D8 grounding as a study decision to be finalized P12.

**Verify:** inventory commands in deployment Stage A; `git status --short`; `git remote -v`; `git symbolic-ref refs/remotes/origin/HEAD` only if a remote is configured; `sha256sum` on files and backup samples. Recheck `gh auth status` only when publication is needed; current authentication is invalid.

**Retain:** source SHA-256 manifest, inventory outputs, wiring/firmware/calibration evidence, known-working launch capture, decision log and backup restore record.

**Rollback:** no robot changes; restore imported source only from verified preserved snapshot, never delete either original. **Exit:** platform facts and provenance recorded; no unresolved fact silently replaced by README defaults. Missing watchdog/sensor is a named hardware blocker, not a claim that it exists.

## P02 — Freeze contracts and policy (2–3 days; P01)

**Cold-start brief:** Current commander is marker-only and permissive; sia-bot tool catalogue is not closed. Build a pure local contract before any actuator consumes model output. Read execution-contracts in full. Strongest review.

**Components:** new `robot_interfaces/{action,msg,srv}`, `robot_core/robot_core/{intent.py,policy.py}`, `config/{topics.yaml,safety.yaml,skills.yaml}`, `research/schemas/{event,trial,run,delivery}.schema.json`, `tests/contracts/`, `docs/interfaces.md`.

**Tasks:** define typed envelopes, union skill schemas (including `face_landmark` with a configured `window` enum), unit/bound/cumulative checks, generation/expiry ownership, terminal states and safety fault matrix. Specify reset/arm authority and sensor freshness. Pin the namespace/type/QoS map and build manifests. Add generated positive/negative examples including every Test 1 category, unknown keys, NaN, Boolean/integer coercion, oversized/9-step plans and 360° wraparound semantics. Decide local profile limits with P01 evidence; record proposed physical thresholds as not yet measured. P07 implements the landmark resolver; P09/P12a consume this already-frozen schema.

**Verify:** `python3 -m pytest tests/contracts -q`; `python3 -m json.tool research/schemas/event.schema.json`; `colcon build --base-paths "$REPO" --packages-select robot_interfaces robot_core` in clean test workspace.

**Retain:** versioned schemas, allowlist count, topic table, failing-case fixtures and test report. **Rollback:** revert contracts before consumers merge; after consumers exist, version migration rather than removing fields silently. **Exit:** explicit field/type/unit ownership; no model-provided topic/shell/reset authority; all invalid fixtures rejected locally.

## P03 — Establish research event plumbing (2–3 days; P02)

**Cold-start brief:** No inspected raw dataset links command to motor output; Test 8 requires both endpoints. Build data capture before feature integration so later gates produce comparable evidence.

**Components:** new `robot_core/robot_core/events.py`, `robot_observability/`, `research/schemas/`, `tests/observability/`, `tools/validate_run.py`.

**Tasks:** implement nonblocking structured event writer, monotonic/UTC timestamps, boot IDs, sequence IDs, redaction, manifest hashing, correlation and durable terminal-event semantics. Define adapter hooks for supervisor/controller/serial and browser events. Add recorder health/disk-full behavior. `tools/validate_run.py` validates schema, hashes, correlation and required events without inventing missing values. Synthetic fixture datasets explicitly labeled synthetic.

**Verify:** `python3 -m pytest tests/observability -q`; `python3 tools/validate_run.py research/fixtures/synthetic-valid`; test deliberate missing/corrupt/duplicate events produce nonzero exit codes; bounded queue/disk failure cannot block a mock stop callback.

**Retain:** schema-tested synthetic fixture, validation report, load-test bounds, redaction tests. **Rollback:** disable admission of research runs if recorder is removed; retain existing raw logs. **Exit:** a sample command→intent→validation→action→candidate→motor-attempt→result trace is reconstructable, with simulated events labeled.

## P04 — Reproduce clean build and no-motion launch (2–4 days; P01)

**Cold-start brief:** Existing launches/config are useful but not a reproducible deployment. Two camera drivers exist, manifests differ from actual imports, and simulation may fetch remote assets. Preserve the observed OS/ROS version.

**Components:** existing `aruco_follower/{package.xml,setup.py}`, `robot_control_pkg/{package.xml,CMakeLists.txt,bringup/launch,bringup/config}`, `sim_pkg/{package.xml,setup.py,launch,config,worlds}`, `twist_stamper-main`; new `robot_bringup/`, `requirements-{runtime,dev}.lock`, `docs/deployment.md`, `config/robot.example.yaml`, `tools/doctor.py`, CI build configuration.

**Tasks:** pin supported native dependency versions, resolve Flask/requests/OpenCV/serial/camera/mux dependencies; isolate test-only vs runtime requirements; preserve licenses. Make one selected camera path/config, stable serial device mapping, no-motion launch default, environment/secret templates. Add a simple cached local simulation world for deterministic CI; keep warehouse optional. Define service startup/shutdown order. Do not auto-arm. Clean build from separate workspace with no sia-bot/Pixi/PYTHONPATH dependency.

**Verify:** deployment Stage B build; `ros2 launch robot_bringup system.launch.py --show-args`; `python3 tools/doctor.py --profile simulation --no-motion`; `colcon test --base-paths "$REPO"`; `colcon test-result --verbose`. Capture any missing actual launch executable as a failure.

**Retain:** OS/package inventory, locks, colcon logs, installed-package list, successful no-motion run, dependency/license audit. **Rollback:** restore baseline service configuration and disable new autostart; do not replace running robot image during planning. **Exit:** fresh supported host builds all packages and starts with zero motor authority; no sibling repository paths.

## P05 — Independent physical stop and firmware/serial fail-stop (3–6 days; P01/P04)

**Cold-start brief:** ROS controller timeout is not a hardware watchdog. Firmware is absent; C++ deactivate has no zero write and serial timeout parsing can accept invalid feedback. Strongest safety/hardware review; named operator present.

**Components:** existing `robot_control_pkg/hardware/diffbot_system.cpp`, `hardware/include/robot_control_pkg/arduino_comms.hpp`; new `firmware/` containing retrieved compatible source/build lock, `docs/hardware-safety.md`, `tests/hardware_interface/`, `research/qualification/watchdog/`. If actual firmware is externally maintained, vendor a reviewed pinned source and attribution so the deployment can be reproduced.

**Tasks:** document/install verified physical motor-enable interruption and deliberate reset; identify controller/driver behavior on power/serial loss. Bound serial reads, reject malformed/stale encoder replies, propagate errors, send zero on deactivate/error where possible, validate finite motor command conversions. Firmware requires command-age timeout independent of Linux and no movement after boot/reset. Preserve known-good firmware binary and exact flash/restore tooling. Split electrical modification into a separately reviewed hardware change if necessary; code PR cannot certify wiring.

**Verify:** `colcon test --packages-select robot_control_pkg`; `colcon test-result --verbose`; implement `python3 tools/qualify_safety.py --profile wheels-raised --case firmware-watchdog` and cases `physical-estop`, `serial-loss`, `controller-kill`. Operator follows inspected stop procedure; automated script never requests floor motion.

**Retain:** firmware/build hashes, wiring photos/schematic, MCU timeout telemetry, external wheel-stop timing, controller fault logs. **Rollback:** motor disabled; named maintainer reflashes preserved verified image using documented tool; repeat watchdog/stop tests before any motion. If restore lacks safety, remain disabled. **Exit:** independent stop and firmware expiry demonstrated, reset does not restart motion; zero-write alone is insufficient.

## P06 — Final velocity supervisor and leases (3–5 days; P02/P03/P04/P05)

**Cold-start brief:** Mux currently routes joystick/follower directly to controller; follower can keep publishing through Wi-Fi loss. Put a guard after all arbitration. Strongest review.

**Components:** new `robot_safety/robot_safety/{supervisor.py,leases.py,obstacle_guard.py}`, `tests/safety/`, `config/safety.yaml`; existing real/sim mux YAML and diffbot/sim launches; follower output remap; `tools/qualify_safety.py`.

**Tasks:** exclusive motion ownership, local client lease, fresh command/sensor enforcement, latched stop/reset, final publisher, bounded zero output, motor-disabled startup. Replace direct twist_mux actuation with a deterministic authority-preserving selector; validate candidate identity/boot/lease/goal/generation/sequence/expiry atomically, never by a side-channel association or relabeling stale messages. Validate scan geometry/coverage including turning and reverse, conservative swept-volume clearance and measured braking envelope. Block unknown clearance. Prevent replayed targets/lease renewals and joystick bypass. Instrument every reject/stop/output through P03. Restrict untrusted DDS/browser access; remove deployed direct controller endpoints. Test process failure relying on P05 and old workers publishing after cancel/re-arm.

**Verify:** `python3 -m pytest tests/safety -q`; `ros2 topic info -v /diff_controller/cmd_vel` (exactly expected supervisor publisher); `python3 tools/qualify_safety.py --profile wheels-raised --case all`; bounded simulation injections for stale sensors, camera pause, restart, replay, competing source and CPU load.

**Retain:** topology/publisher report, timeout distributions, fault matrix and coverage map. **Rollback:** disable all command sources before reverting launch remaps; retain physical disable. **Exit:** every actuator source gated, each listed fault stops/blocks in bench/simulation bounds, no automatic resume; stop/status remain available with expired lease, active competing goal and sensor faults. Braking envelope is still provisional. P13's limited commissioning sub-gate measures it before general floor/research authorization, so P06 does not claim measured floor braking.

## P07 — Bounded feedback motion skills (3–5 days; P06)

**Cold-start brief:** Existing ArUco following works by visual feedback; general thesis movement is missing. Sia timed motion is only design reference. Build physical skills without any LLM dependency.

**Components:** new `robot_skills/robot_skills/{distance.py,rotate.py,arc.py,timed.py,follow.py,landmarks.py}`, `tests/skills/`; existing `aruco_follower/aruco_follower/{marker_follower.py,aruco_detector.py}` for valid/fresh input and enabled-goal behavior; `config/{skills.yaml,landmarks.yaml}`.

**Tasks:** implement fresh-odom closed-loop completion, unwrapped yaw, settle/deadline/stall/overshoot, per-goal cancellation tokens, signed-direction clearance, bounded follow duration and marker loss abort. Preserve tuned baseline gains initially. Ensure inactive sources publish no competing nonzero output; every candidate carries atomic authority metadata. Implement the deterministic surveyed-window bearing resolver against P02's frozen `face_landmark` schema: consistent reference frame/current yaw, shortest-turn convention, calibration identity, reset invalidation and missing-transform refusal. Document that this is configured landmark grounding, not semantic visual navigation. Test it alongside arc/circle geometry and units.

**Verify:** `python3 -m pytest tests/skills -q`; `colcon test --packages-select robot_skills aruco_follower`; `python3 tools/qualify_skills.py --profile simulation --case all` (created here). Include 0.25/0.5/1/2 m, 45/90/180/360°, reset/NaN/stale odometry and reverse/arc fixtures.

**Retain:** simulated trajectory plots, stop/cancel traces, deterministic fixtures. **Rollback:** disable new skill registry entries; baseline follower still requires P06 guard. **Exit:** all supported motions bounded and terminate on feedback/failure; no physical precision claims from simulated results.

## P08 — Deterministic plan executor (2–4 days; P02/P03/P07)

**Cold-start brief:** Model-issued waits cannot guarantee sequencing. Executor alone decides when a next step may begin; stopped plans never resume.

**Components:** new `robot_executor/robot_executor/{executor.py,state.py}`, `tests/executor/`, action adapter for `ExecutePlan`.

**Tasks:** single-owner 1–8-step plan, step precondition revalidation, wait for measured terminal result, total deadline/travel budgets, ID deduplication, cancellation generation, atomic terminal event and no queue replay. Busy returns typed error instead of silently replacing motion. State queries remain responsive. Fail/cancel final step and intermediate step race tests.

**Verify:** `python3 -m pytest tests/executor -q`; `python3 tools/qualify_skills.py --profile simulation --case sequences`; assert strict step event ordering and no nonzero output after cancellation/rearm until a new admitted goal.

**Retain:** 2/4/6/8-step traces and replay/race reports. **Rollback:** disable plan submission; supervised manual bench diagnostics only. **Exit:** every admitted plan has exactly one terminal result, no skipped/overlapping steps, and partial completion cannot masquerade as success.

## P09 — Gemini adapter and local validation (2–3 days; P02/P03/P04/D4)

**Cold-start brief:** Existing Gemini handler validates only action name and permissively converts IDs. Replace it with a narrow translator, never a ROS tool agent. No secrets or paid calls without D4 access/budget settings.

**Components:** new `robot_language/robot_language/{provider.py,gemini.py,translator.py}`, `prompts/intent-v1.txt`, `config/provider.example.yaml`, `tests/language/`; remove deployed commander parsing path after new entrypoint exists.

**Tasks:** account-specific model capability probe without motor access, supported structured output schema, pinned SDK/API/model configuration and reported model metadata. Strict local parse/bounds/provenance validation; local stop dispatch; deadlines/generation cancellation; typed quota/error/refusal handling; cost/token caps; no digit-regex motion fallback. No dynamic model switching during confirmatory trials. Fixture provider supports offline CI but results labeled synthetic.

**Verify:** `python3 -m pytest tests/language tests/contracts -q`; `python3 tools/probe_provider.py --config config/provider.yaml --no-actuation` (created here); fresh small pilot set, separate from held-out Test 6, within approved spend.

**Retain:** redacted capability probe, requested/reported model ID, prompt/schema hashes, negative cases, token/latency data and budget configuration. **Rollback:** provider off; local stop/status remain, no fallback cloud-driven motion. **Exit:** malformed/adversarial/late replies cannot bypass local checks; keys never enter browser, URL logs or research data.

## P10 — Web control, progress, status and health (3–5 days; P06/P08/P09)

**Cold-start brief:** The current embedded Flask UI provides marker chat/video only. Adapt sia-ui behavior, not its bumperbot transport assumptions. D3 permits a lighter UI implementation; D6 requires comparison parity.

**Components:** new `robot_web/{gateway.py,static/,templates/}`, `tests/web/`; dedicated local safety endpoint in `robot_safety`; `robot_observability` health/status publishers; `docs/interfaces.md`.

**Tasks:** authenticated operator lease/read-only viewers, chat clarification/error/busy handling, correlated progress + terminal state, cancel and prominent soft-E-stop on independent control path, status with freshness, split ping/reply IDs, reconnection state refresh with no replay. Video remains separate. Do not label publish acknowledgment as halt. Add accessible keyboard operation, explicit stale/disconnected state and structured browser timing/delivery logs. No arbitrary topic/service browser proxy.

**Verify:** `python3 -m pytest tests/web -q`; `python3 tools/check_web.py --base-url http://127.0.0.1:5000 --profile no-motion` (created here); browser automation/screenshot checks for pending model request, cancel/stop, lost lease, reconnect, two clients, health stale and oversize input.

**Retain:** UI behavior recordings, API conformance and browser logs, no-secret bundle scan. **Rollback:** gateway disabled and lease expires; preserve supervisor/physical stop. **Exit:** all control paths reflect actual server state; LLM/stream congestion cannot block local stop; client loss cannot retain motor ownership.

## P11 — Live video and bounded vision response (2–4 days; P10/D4)

**Cold-start brief:** Existing MJPEG resends cached frames; sia vision supports useful partial/busy/progress concepts but has provider/timeouts to replace. Tests 2/3 include “what can it see?”

**Components:** new `robot_vision/robot_vision/{frames.py,snapshot.py,describe.py}`, web video/snapshot assets, `tests/vision/`, `config/vision.yaml`.

**Tasks:** one camera source; frame ID/age, bounded encoding/backpressure, image then caption, finite capture/description deadlines, busy/partial/error/cancel, image privacy controls, no motor output from caption. Instrument unique capture/delivery/render events. Default snapshots while stationary for study; concurrent-motion stress tests only after safety gate and with explicit protocol. Test synthetic and real images separately.

**Verify:** `python3 -m pytest tests/vision -q`; `python3 tools/check_web.py --profile synthetic-camera --base-url http://127.0.0.1:5000`; `ros2 topic hz /camera/image_raw`; no-camera, stale-frame, delayed model and wrong-request-ID cases. Real caption pilot uses nonparticipant scenes and approved provider budget.

**Retain:** frame/caption timing traces, labeled pilot images and error cases, CPU/bandwidth measurements. **Rollback:** disable description/stream; no cached image presented as live. **Exit:** image and caption correlate, stale data labeled, bounded response/cancellation and safety non-interference measured during qualification.

## P12a — Freeze experiment harness and analysis (2–3 days; P02/P03/P04/D5/D6/D8)

**Cold-start brief:** Required-tests are informal protocols with measurement ambiguities and unsupported assumptions. Read research companion fully. This PR prepares instruments, not outcomes; recruitment needs institutional determination. P12b separately builds the executable comparison interface. References elsewhere to P12 mean both packages where relevant.

**Components:** new `research/{protocols,datasets,analysis,fixtures}`, `research/protocols/study/`, `tools/{validate_run.py,collect_trial.py,analyze.py}` and `docs/baseline-interface-contract.md`.

**Tasks:** freeze Test 1 150-case suite plus valid controls; Test 6 100 held-out phrasings/gold intents; randomization and trial sheets for all tests, tolerances/task definitions and consent/data policy. Specify baseline CLI+teleop contract using same supervisor and scene-description backend; no raw controller publication. Analysis with known synthetic fixtures, exact denominators, pairing and failure accounting. Define netem profiles with local recovery instructions and a six-hour workload. Run instrument dry-runs only; never label synthetic/pilot rows confirmatory.

**Verify:** `python3 -m pytest research/analysis/tests -q`; `python3 tools/analyze.py --synthetic --out research/fixtures/analysis-check`; `python3 tools/validate_run.py research/fixtures/synthetic-valid`; instrument dry-run of each protocol including incomplete/failure rows.

**Retain:** frozen protocol/dataset hashes, supervisor/institution determination, blank consent/questionnaires, analysis unit fixtures, randomization schedule and metrology calibration plan. **Rollback:** version/amend protocol; never overwrite frozen version or delete collected trials. **Exit:** every required test has defined numerator/denominator, timing, raw format, collection owner and completeness rule; no invented participant outcomes.

## P12b — Implement the safe comparison toolchain (1–2 days; P06/P08/P10/P11/P12a)

**Cold-start brief:** User selected one CLI-plus-teleop baseline with all six task capabilities. Read `docs/baseline-interface-contract.md`, current action/lease/vision contracts and P12a task definitions. A protocol alone does not make the comparison executable.

**Components:** new `robot_tools/robot_tools/{baseline.py,teleop_adapter.py}`, `tests/baseline/`, `docs/baseline-quickstart.md`; existing gateway/executor APIs only through their documented interfaces.

**Tasks:** CLI bounded distance/turn/sequence/arc/surveyed-window/status/snapshot/description commands; guarded keyboard dead-man adapter emitting atomic candidates with a valid lease, no direct controller access. Local cancel/soft-stop, comparable transcript/action logging, same speed/clearance and feedback limits as web. Implement non-motion fixtures and six-task walkthrough in simulation; no added NLP advantage in the structured baseline.

**Verify:** `python3 -m pytest tests/baseline -q`; `ros2 run robot_tools baseline --help`; `python3 tools/check_baseline.py --profile simulation --tasks all` (created here); test key-release, client death, late candidates, unavailable camera and cross-condition frame/status parity.

**Retain:** CLI manual/reference sheet, simulated six-task transcripts, lease/stop parity evidence. **Rollback:** disable baseline admission; no change to physical stop or web guard. **Exit:** all six goals are achievable through the documented comparison toolchain with identical safety gates and honest action-count logging. Physical parity is confirmed in P13.

## P13 — Integrated qualification and junior rehearsal (2–4 days; P05–P12)

**Cold-start brief:** Individual tests do not prove the deployed system. Qualification precedes any confirmatory trials or participants. Strongest independent safety review and named physical operator required.

**Components:** `docs/deployment.md`, `research/qualification/`, `tools/{doctor.py,qualify_safety.py,qualify_skills.py}`, systemd/launch configuration.

**Tasks:** junior follows clean-checkout runbook on the actual target or separate clean robot storage; no inherited sia-bot installation. Validate motor-disabled startup, physical stop, MCU timeout, final publisher, lease loss, API failure, sensor fault, cancel mid-plan, restart/no replay, vision load, and firmware restore path. Two physical sub-gates: (A) after bench gates pass, named operator/observer authorize limited low-speed commissioning in an oversized clear area, with physical motor disable reachable and provisional conservative travel/time bounds; measure braking/stop-distance and sensor coverage. (B) freeze measured safe speed/time/clearance thresholds, rerun all fault tests against them, then authorize general floor research. No participants during commissioning. Verify bounded CLI and web parity. Record every undocumented intervention; repair docs and repeat relevant rehearsal.

**Verify:** deployment Stage B–E commands; `python3 tools/doctor.py --profile robot --no-motion`; `python3 tools/qualify_safety.py --profile wheels-raised --case all`; after human go/no-go `python3 tools/qualify_safety.py --profile physical-supervised --case all`; validate qualification manifest.

**Retain:** junior transcript/checklist, topology and package hashes, physical halt video/encoder traces, signed readiness gate, repair/retest history. **Rollback:** disarm and restore last qualified version; any unexplained motion revokes floor authorization. **Exit:** junior independently deploys, exact robot build reproduces bounded behavior, all fault gates pass within frozen bounds. No participant study before this exit.

## P14 — Collect Tests 1, 4, 5 and 6 (3–5 days; P12/P13)

**Cold-start brief:** These tests need real command entry and physical measurements for motion/context cases. Test 6 assesses interpretation separately; it does not require driving 100 times. Research failure rates may be nonzero without invalidating honest completion.

**Components:** `research/results/test-{1,4,5,6}/` manifests and deidentified tables; immutable raw store; existing analysis scripts only bug fixes in separately reviewed changes.

**Tasks:** run frozen 150 safety commands plus controls; 240 primitive measurements; 60 sequence trials; 100 held-out interpretations. Record every attempt, translation, validation and motor observation; external metrology for accuracy. No prompt tuning between confirmatory trials. Unsafe case stops the session and returns to qualification; preserve interrupted/incomplete records. Separate revised builds as new cohorts.

**Verify:** `python3 tools/validate_run.py "$RUN_DIR"`; `python3 tools/analyze.py --tests 1,4,5,6 --manifest "$MANIFEST" --out "$DERIVED_DIR"`; completeness counts and matching raw hashes; independent spot audit of sampled trajectories and blocked commands.

**Retain:** raw bags/logs, annotated case sheet, external measurements, calibration and all failures, plots/tables with denominators. **Rollback:** no physical undo; invalidate affected analysis explicitly and rerun from immutable raw data, never erase observations. **Exit:** all required cells complete or transparently blocked; P17 requires completed tests, not silently reduced samples.

## P15 — Collect Tests 7 and 8 (2–3 days plus six-hour run; P12/P13)

**Cold-start brief:** Network impairment must not remove the independent stop; six-hour message reliability needs sender/receiver ledgers. A bag alone is not a delivery denominator.

**Components:** `research/results/test-{7,8}/`, local netem/recovery scripts prepared by P12, immutable bag/browser/firmware records.

**Tasks:** execute frozen impairment matrix and 10 disconnects, measuring actual link conditions and unique video/status delivery. Independent spotter at physical stop. Run six-hour bounded workload with continuous recording, endpoint sequences, resource/storage checks and privacy controls; no unattended free-driving loop. Preserve restarts/failures and separate repeat sessions. Restore network settings locally after each profile.

**Verify:** `python3 tools/validate_run.py "$RUN_DIR"`; `ros2 bag info "$BAG_DIR"`; `python3 tools/analyze.py --tests 7,8 --manifest "$MANIFEST" --out "$DERIVED_DIR"`; reconcile sent/received/duplicates/out-of-order/restarts and stopwatch/external timing.

**Retain:** measured netem/network profile logs, all 10 stop traces, six-hour manifest/bag/ledgers and gaps. **Rollback:** disarm; remove only the qdisc created on the dedicated test interface using the recorded recovery command. Keep physical local access; never depend on impaired SSH for recovery. **Exit:** bounded physical stop proved per profile, six-hour dataset accounted for; if run fails early, report failure and retain it, then complete a separately labeled six-hour run after repair.

## P16 — Run Tests 2 and 3 participant study (3–5 days plus recruitment; P12/P13/D5)

**Cold-start brief:** User selected web versus CLI-plus-teleop. 12–15 consenting ROS-naive people, six tasks in both conditions, counterbalanced order; participant is the analysis unit. This cannot run autonomously.

**Components:** restricted consent/identity store; `research/results/test-{2,3}/` deidentified rows/questionnaire scores; protocol deviation ledger.

**Tasks:** qualified operator and independent safety observer recruit/run approved sessions. Equal safety briefing/reference-sheet policy, no task coaching; log interventions, retries, failures/timeouts and withdrawal. Same robot/profile/scene backend in both conditions. Collect SUS and frozen NASA-TLX variant per condition; separate quotes/images consent. Safety intervention takes priority and is recorded, never hidden.

**Verify:** `python3 tools/validate_run.py "$STUDY_DIR"`; `python3 tools/analyze.py --tests 2,3 --manifest "$MANIFEST" --out "$DERIVED_DIR"`; check participant pairing/order, six tasks/condition and item-level questionnaire completeness; manually verify anonymization.

**Retain:** deidentified trial/item data, consent determination/access rules, paired plots/CIs, attrition/deviations, consented quotes. **Rollback:** pause collection, honor approved withdrawal procedure, preserve permissible integrity metadata; amendments trigger a new cohort label. **Exit:** 12–15 qualifying participants complete required comparable observations (or explicit shortfall remains blocked), analysis respects missingness and no fabricated scores.

## P17 — Publication evidence package and claim audit (2–4 days; P14/P15/P16)

**Cold-start brief:** The thesis numbers conflict and cannot seed new results. Complete evidence does not mean a publishable manuscript is ready. Strongest independent methodological review.

**Components:** `research/publication/{README.md,claim-evidence.csv,limitations.md,figures,tables}`, pinned analysis environment, evidence manifest and restricted/public data split.

**Tasks:** regenerate all results from raw manifests; integer successes and denominators, uncertainty intervals, timing endpoints, protocol deviations, hardware/provider versions. Map each intended claim to source dataset, analysis function and figure/table; disposition old claims as replaced/narrowed/unsupported. Include selection bias, small convenience sample, order effects, hardware-specific results, model variability, metrology/clock uncertainty, network profiles, no certification, and any scope exclusions. Archive licenses/consent/access/reproduction instructions; verify novelty separately before making “first” claims.

**Verify:** `python3 tools/analyze.py --tests 1,2,3,4,5,6,7,8 --manifest "$MANIFEST" --out "$FRESH_OUTPUT"`; `python3 tools/audit_claims.py research/publication/claim-evidence.csv` (created here); rerun in clean pinned analysis environment, compare generated artifacts/hashes or documented numerical tolerances; independent raw-to-table audit.

**Retain:** scripts/locks, raw manifest, all figures/tables, claim audit and review report. **Rollback:** retract incorrect derived outputs and regenerate; preserve originals/version history and correction note. **Exit:** every retained empirical claim has traceable evidence, all Tests 1–8 dossiers complete, limitations explicit. No claim of paper acceptance/readiness based solely on this gate.

## P18 — Retire sia-bot from deployment (1–2 days; P13/P17)

**Cold-start brief:** User chose cessation of deployment with a read-only archive. No deletion or hosted archive operation is part of this choice. Migration is complete only when ArUco is independently deployable and research provenance survives.

**Components:** `docs/retirement.md`, deployment service/env/package inventory, `research/provenance/retirement-manifest.json`, archival backup (location agreed P01).

**Tasks:** verify clean deployment and junior rehearsal still valid at release hash; archive immutable sia-bot source/config/contracts with hashes, license notices and original thesis/tests, excluding secrets from public artifacts. Verify backup restoration independently. Remove sia-bot service/PYTHONPATH/build/UI/runtime dependencies in controlled deployment configuration; preserve historical source. Retain all raw evidence and analysis. Resolve any remaining source-license ownership before release distribution.

**Verify:** `rg -n 'sia-bot|bumperbot_controller|OPENROUTER' robot_* config requirements*` (review expected documentary references; runtime imports/paths must be absent); clean checkout deployment again; full qualification smoke; `python3 tools/audit_claims.py research/publication/claim-evidence.csv`; archive hash/restore check.

**Retain:** sole-runtime dependency report, release and firmware hashes, junior sign-off, archive restore proof, all eight completion manifests. **Rollback:** retain qualified ArUco release and archive; if integration fails, disarm and revert deployment configuration. Historical sia-bot is not an automatically safe fallback controller. **Exit:** sole deployable ArUco repository, verified archive, all tests/evidence preserved, no outstanding retirement blocker; no source deletion.
