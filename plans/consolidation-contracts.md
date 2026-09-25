# Execution, safety and evidence contracts (proposed)

P02 freezes these contracts after P01 inventory. Numeric values below are **initial bench proposals**, not certified limits or measured stop performance. Hardware qualification can lower limits; changes before confirmatory collection are versioned and justified.

## Intent boundary

Browser request envelope, issued by the authenticated gateway: schema version, server-assigned `command_id`, `session_id`, `boot_id`, local monotonic receive time, expiry, operator lease/generation, UTF-8 command text, and bounded context reference. Model cannot set identity, timestamps, expiry, safety limits, topic names, lease, or authorization.

Model output is a discriminated union; every object rejects extra properties. P02 implements JSON Schema plus independent semantic validation, positive and negative examples, and schema-version tests. The provider schema is a supported subset; the local contract is authoritative.

```json
{
  "schema_version": "1.0",
  "kind": "plan",
  "steps": [
    {"skill": "move_distance", "distance_m": 0.5, "direction": "forward"},
    {"skill": "rotate", "angle_deg": -90}
  ]
}
```

Other variants: `{"schema_version":"1.0","kind":"clarify","question":"How far should I move?"}` or `{"schema_version":"1.0","kind":"reject","reason_code":"unsupported"}`. No executable action exists in clarify/reject. Read-only requests use a one-step plan and the same catalogue, but cannot affect motor authority. `stop` is handled locally before any cloud call; a model-produced stop is also accepted through the same local path. A stop button and local soft-E-stop service remain available when parsing is busy or offline. Reset is never an LLM skill.

Initial catalogue (count derived from versioned registry, never advertised as “20”):

| Skill | Required fields / semantics | Local execution limits and feedback |
|---|---|---|
| `move_distance` | finite `distance_m`, direction forward/backward | >0 to 2 m initially; profile speed default 0.10 m/s, cap <=0.18; fresh odometry and directional clearance; distance feedback, deadline and stall detection. |
| `rotate` | finite signed `angle_deg`, positive CCW | Nonzero magnitude <=360°; default 0.30 rad/s, cap <=0.45; accumulated unwrapped yaw, not final heading modulo 360. |
| `move_timed` | finite duration, direction | 0<duration<=10 s initially, profile speed; no user-selected raw Twist. |
| `arc` | radius_m, signed sweep_deg | Radius 0.30–1.0 m proposed; sweep <=360°; enforce `v/r` angular cap, swept-volume clearance, total travel/time. Circle is a 360° arc. |
| `follow_marker` | integer marker_id, duration_s | ID in actual dictionary, not Boolean/coerced string; duration <=30 s proposed, calibrated pose freshness, approved standoff, loss abort, supervisor lease. |
| `face_landmark` | enum landmark name, initially `window` | Local surveyed bearing in a verified frame; fresh yaw, calibrated transform, shortest-turn convention; missing/reset calibration rejects. |
| `snapshot` | no motor fields | Fresh frame; returns request/frame IDs or unavailable. |
| `describe_scene` | optional bounded user question | Fresh snapshot and caption; finite timeout; cannot supply skills or motor commands. |
| `get_status`, `get_health` | no parameters | Typed measured subsystem status with age, not “healthy” because a process replied. |
| `stop` | no parameters | Cancel plan and all queued work, invalidate motion generation, command zero; success only after stop observation. |

Speed remains local profile configuration initially. If a user specifies an unsupported speed, the parser must clarify/reject rather than silently discard it. Named landmarks such as “window” are only usable with an explicitly surveyed local frame mapping; otherwise ask a clarifying question. Never infer reachable waypoints from captions. A circle command without needed geometry receives a consistent clarification in every condition.

Validation order:

1. Bound request length (proposed 2 KiB), output bytes (16 KiB), parse depth and plan length (1–8); validate content type. Reject duplicate JSON keys, trailing data, code fences, truncated JSON, NaN/Infinity, Booleans as numbers, unknown fields/skills/versions and strings masquerading as numbers. No tolerant repair that introduces executable intent.
2. Validate each field's units, enums, finite bounds, required fields and cross-field feasibility. Normalize explicitly written units deterministically; prohibit invented units/default distances. A schema-valid interpretation can still misunderstand language; Test 6 assesses that limitation.
3. Validate whole-plan totals: proposed 8 m aggregate linear travel, 1440° total absolute rotation and 240 s cumulative deadline. Eight 1 m/90° alternating steps can fit at the initial profile, while any step must also meet its deadline. Derive conservative per-step deadline using profile velocity, acceleration allowance and settle time, capped at 90 s; reject infeasible requests, do not truncate them silently. P01 must confirm the test area's size for each planned route.
4. For **motion admission only**, require live operator lease, correct session/generation, ID deduplication, no competing motion owner, no safety latch, supported/calibrated sensor coverage, and fresh required odometry/scan/camera. Revalidate these conditions immediately before every motion step and continuously while moving; the current goal is its own valid owner. Model confidence never overrides a failed precondition. Stop/cancel bypass motion-admission checks: authorized operators/safety observers can stop while busy, lease-expired, latched or sensor-faulted. Status/health remain queryable during motion, disarm and cloud outage without a motion lease. Snapshot/description require their own camera/provider preconditions, not a motion lease; a separately requested stationary capture policy may refuse or await an explicit safe stop, never silently cancel or resume unrelated motion. Test every stop/read-only combination explicitly.
5. Reject expired or cancelled model replies. Proposed maximum translation wait 8 s and **admission expiry** 10 s from gateway receipt; cancel/stop increments generation so an in-flight reply cannot revive motion. Admission expiry is checked only before acceptance. Once accepted, execution uses its fresh client lease, candidate expiry, per-step deadline and up-to-240-s plan deadline; it does not reuse the 10-s parsing expiry. Per-step revalidation checks these execution conditions, not the obsolete admission timestamp. No automatic actuation retry following HTTP timeout. Duplicate command IDs return recorded status rather than dispatch twice; reboot never replays stored plans.

API failures (invalid key, quota, 429/5xx, refusal, missing candidate, blocked content, deadline, transport error) produce typed errors and no new motion. Default no retries; if P09 adds a bounded translation retry, it must fit the original deadline and retain a single dispatch ID. Existing admitted local motion remains bounded by lease and executor; no new cloud request is needed to stop it. If a dependent step needs the cloud and fails, stop/abort rather than improvise. Budget exhaustion behaves like provider unavailability. Record request/model/schema/prompt version, response text after redaction, finish reason, usage/cost and timings; do not log credentials or hidden model reasoning.

## Local execution

Exactly one motion goal owns the actuator at a time. States: RECEIVED → PARSING → VALIDATING → REJECTED/NEEDS_CLARIFICATION or ACCEPTED → RUNNING(step index) → SUCCEEDED/FAILED/CANCELLED/TIMED_OUT. Each accepted request has exactly one terminal event. “Accepted” or “started” is not “succeeded.” Each step has its own terminal reason and measured end state. A plan succeeds only when every step meets its completion criterion; terminate remaining steps on any failure.

Every motion source emits `robot_interfaces/msg/VelocityCandidate`, containing the Twist values, source ID, producer boot ID, lease ID, command/goal ID, captured generation, monotonic sequence, source timestamp and short validity interval. The supervisor validates identity and freshness atomically with the velocity, then alone emits controller `TwistStamped`. A raw Twist with a separate ownership topic is insufficient: a late old worker could otherwise be misattributed to a new goal. Workers capture authority at admission and cannot acquire current authority just by publishing. Source adapters must never relabel stale messages with the newest lease. Clear candidate caches on cancel/disarm/generation change; test old-worker messages arriving after re-arm.

Existing `twist_mux` cannot be assumed to preserve this custom authority envelope. P06 replaces its direct actuator arbitration with an authority-preserving deterministic selector in the supervisor; retain old mux configuration only as baseline/reference or isolated diagnostics, never as a bypass. Manual source priority is explicit, but source switch first stops/revokes the old goal and requires a valid new owner. All candidates remain subject to the same final guard.

Use ROS action cancellation and a single deterministic scheduler, not model-issued waits or independent shared-state movement threads. Cancellation invalidates the plan generation atomically, suppresses old workers, zeroes actuator output, and terminates unfinished steps as cancelled. Join/wait operations cannot hold locks needed by a worker or safety callback. LLM/vision/JPEG/HTTP tasks run outside the control and safety executors. No cloud callbacks can block stop handling.

Feedback primitives: distance uses odometry projection/path criterion and cross-track guard; angle uses incremental unwrapped yaw; arc validates radius and accumulated sweep; all use fresh finite timestamps, distance/time limits, measured velocity settling and stall/overshoot failure reasons. Success requires measured velocity below a frozen threshold for a settle window, not merely a zero command publication. Proposed bench threshold 0.01 m/s and 0.02 rad/s for 0.3 s must be checked against encoder resolution. Odometry is control feedback; external metrology measures research accuracy.

For study window grounding, P02 defines `face_landmark` in the initial schema/catalogue so P09 prompts and P12a datasets include it; P07 implements its local resolver. It has an enum restricted to surveyed names (initially `window`), a configured reference-frame bearing and calibration/version identifier. Local code computes shortest signed relative rotation from fresh yaw in that same verified frame; ties at 180° use a documented direction. Startup/odometry reset invalidates the mapping until a local operator re-establishes the surveyed start-frame transform. Missing transform/calibration/landmark rejects or clarifies. Gemini supplies only the landmark name, never an invented bearing; no image-based window localization claim. Disclose this configured grounding in the paper and baseline task instructions.

Marker selection may remain transient-local for perception but cannot grant movement. Follower only runs with an explicit expiring goal, fresh source stamps and safety lease. Camera pause/stale frame/marker loss ends the goal; reappearance does not restart cancelled work. Clamp/validate controller parameters on startup and refuse invalid settings. Do not use yaw modulo arithmetic to treat a 360° command as already complete.

## Safety layers and failure matrix

Proposed bench lease: browser renews at 5 Hz with monotonically increasing sequence and a robot-issued challenge; expiry 0.6 s on the robot's monotonic clock. The gateway may **forward actual client renewals**, but must not synthesize renewals for a disconnected browser. Buffered/replayed renewals cannot extend control: use short-lived challenges, session nonce and sequence checks. Browser close/hidden-tab throttling/network loss leads to expiry; no reliance on unload handlers. Recovery requires an explicit new lease and re-arm; never resume unfinished movement.

Supervisor proposal: 50 Hz evaluation, candidate maximum age 0.15 s, odometry/scan freshness <=0.3 s where achievable, perception expiry <=0.5 s. Controller timeout and firmware watchdog proposed <=0.3 s after their input ceases. Inventory, sensor rates and braking tests must establish feasible values before general floor/research motion. The sole preceding floor exception is P13 commissioning sub-gate A: named operator and independent observer, passed bench gates, low-speed bounded characterization in an oversized clear area, reachable physical disable and provisional conservative limits. No participants or research trials run under that exception. Do not add these timeouts as if they always run in series: measure the actual worst-case end-to-end stop latency and stopping distance on each fault path.

| Fault | Required local behavior | Evidence gate |
|---|---|---|
| Physical E-stop pressed, even with Linux frozen | Independent motor disable; deliberate physical reset and separate software re-arm; zero command on restart | Wheels-raised circuit demonstration then low-speed measured halt; wiring and firmware provenance |
| Browser soft E-stop while model/vision busy | Dedicated control path latches supervisor, revokes all sources/queues; UI shows requested vs confirmed halt | Concurrent-load latency, actuator zeros and measured halt; no API dependency |
| Browser/Wi-Fi disappears; gateway crashes | Client lease expires locally; stop and latch disconnected state, no automatic continuation | 10 physical disconnect trials after bench fault injection |
| Supervisor/process/DDS failure | Controller stale-input timeout then independent firmware expiry; physical stop remains usable | Kill/suspend process and serial disconnect bench tests; post-reset no old motion |
| Serial read/write failure | No placeholder encoder acceptance; controller fault; firmware timeout stops when communication fails | Fake serial malformed/truncated/timeout tests plus wheels-raised unplug |
| Obstacle within stopping envelope, scan stale/invalid | Stop/deny motion in affected direction; unknown is not clear | Sensor coverage, blind spot and stationary 20 cm fixture tests |
| Odometry stale/reset/jump/NaN or stall | Abort feedback skill and command zero; operator investigation | Injected faults; cannot label deadline expiry as successful travel |
| Late/duplicated commands, old target/lease, model output after stop | Reject using generation/expiry; no movement on reconnect | Deterministic replay and race tests |
| Camera unavailable | Follow abort; snapshot/description unavailable; other motion only if independent required clearance sensors remain valid | Unplug/freeze/replayed-frame tests |
| Logger full or recorder unavailable | Stop admitting research trials; supervisor remains independent. Active trial safely stops and is marked incomplete | Disk-full fault injection with reserved safety resources |

Obstacle policy accounts for footprint, reaction interval, measured braking deceleration, uncertainty margin and clearance for reverse/turn/arc. A 20 cm frontal box test is not complete obstacle coverage. Until coverage is established, do not authorize blind reverse or turning sweep. A supervisor or spotter cannot be substituted as the measured automatic obstacle detector. Real robot skill limits must be consistent at validator, supervisor, controller and firmware layers; select the tightest applicable bound.

## Web, vision and observability

Lightweight Flask gateway/static assets under proposed `robot_web/` keeps one robot deployment without requiring Next.js at runtime. Preserve usable chat history, busy/clarification/error states, per-command timeline, current step, cancel/soft-E-stop, lease state, robot pose/data age, subsystem health and video age. A separate local safety endpoint/process routes stop independently of web workers; physical stop remains the fallback if Wi-Fi fails. Same-origin auth, CSRF/origin protection, limited request sizes and read-only observer sessions; no API key in browser or command URL.

Proposed HTTP contracts: `POST /api/commands` returns 202 + command ID, `GET /api/events` bounded event stream, `GET /api/status`, `/api/health`, `POST /api/lease/renew`, `POST /api/commands/{id}/cancel`, dedicated safety endpoint `POST /api/estop`, `/video_feed`, `GET /api/snapshots/{frame_id}`. Final transport detail is frozen P02/P10. On reconnect fetch server state, show missed-history boundary and never resend motor commands. Status traffic has separate scheduling from video; backpressure drops old video frames, never queues obsolete control renewals.

One camera driver feeds perception and a shared latest-frame cache. Distinguish capture, encode, gateway send, browser receipt/render. Each unique frame has sequence/source timestamp and frame ID. Repeated JPEG bytes or renders do not inflate unique FPS. A snapshot captures a fresh frame once, returns image promptly and emits caption later. Outcomes: success(image+caption), partial(image with caption timeout), error(no image), busy. Timeouts are finite; cancellation/late caption cannot attach to another command. Image descriptions are informational, can be incorrect, and are never clearance authorization. Use objects/scene checks scored independently; do not infer “all accurate” from model reputation.

## Data contract

P03 owns schemas under `research/schemas/`; P12 owns instruments/protocols. Store immutable source facts, derive analysis separately.

- `run_manifest.json`: run/protocol IDs, UTC start/end, robot/software/firmware commits or hashes, dependency lock hashes, model requested/reported ID, provider, prompts/schema hash, policy/calibration hash, hardware inventory ID, environment/floor/battery, operators (pseudonyms), clock offset/uncertainty, condition/randomization seed, camera settings, exclusions/deviations, consent access class, evidence hashes.
- `events.jsonl`: `schema_version, run_id, event_id, command_id, plan_id, step_id, boot_id, source_id, source_seq, utc_ns, monotonic_ns, event_type, payload`. Event types include command received, translation start/end, raw parsed output, validation/reason, admission, step start/progress/end, cancel/stop requested/latch, candidate/supervised velocity, controller limited output, serial motor ticks sent, encoder feedback, halt observed, browser received/rendered, terminal result and recorder health. An unavailable measurement is null plus reason, never zero.
- `trials.csv`: `test_id, trial_id, run_id, command_id, condition_id, participant_id?, attempt, target, measured, measurement_unit, ground_truth_method, uncertainty, success, failure_reason, started_utc, elapsed_ms, evidence_paths, deviation_id`. Test-specific columns are specified in research protocols.
- `delivery.jsonl`: source/session/boot/sequence, publish/send-attempt/receive/render/ACK times and endpoint, duplicates/out-of-order flags; distinguish application publish attempt from physical wire transmission. Quantify only what is instrumented.
- `motor_samples` in bag/events: requested and limited Twist, firmware input values if observable, encoder state. Serial write evidence is an attempted motor command, not proof of applied torque/physical motion. Add firmware ACK/sequence telemetry when possible; document gaps rather than fabricate.

Use monotonic clocks for durations on one host; ROS simulated time only for simulation trajectories. Preserve UTC and measured offsets for cross-host alignment. Bound round-trip offset uncertainty or use synchronized video/LED instrumentation for fine latency. Report RTT as RTT when one-way timing is unsupported. Correlate receipt to motor onset/halt using independent external observations for physical claims. Redact tokens, names and secrets; use consented pseudonymous command text/images in a restricted archive and redacted publication extracts. Backpressure and logging errors cannot delay a stop.
