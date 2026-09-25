# Gemini recommendation for the robot

Researched 2026-09-25 using Google's primary documentation. Recommendation requested by the user; no account probe, benchmark, API purchase or paid call performed.

## Recommended starting model

Use **`gemini-3.8-flash` through the direct Google Gemini API**, with **low thinking**, as the single initial model for structured intent translation and occasional image descriptions. This is a design recommendation pending a motor-disabled pilot, not a measured claim that it is the fastest or most accurate for this robot.

Google lists it as the current stable Flash model, with image input and structured outputs. Its documented thinking levels are low/medium/high; `minimal` is unsupported. [Model details](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash). The lifecycle table lists release on September 2, 2026 and no announced shutdown. Existing 2.5-family access is restricted to prior active users, so the checkout's 2.5 default is a poor starting assumption for a new project. [Lifecycle](https://ai.google.dev/gemini-api/docs/deprecations).

Why I recommend this starting point: one model simplifies reproducibility; the workload includes mixed Bangla-English, ambiguous requests and eight-step interpretation, plus captions. Saving a small amount per experiment is less valuable than avoiding provider/model combinations before the first validated release. This rationale is an engineering judgment, not a model-specific benchmark result. All actuation remains local and deterministic.

## Cost comparator

| Candidate | Standard input / 1M tokens | Standard output / 1M tokens | Proposed role |
|---|---:|---:|---|
| `gemini-3.8-flash` | $0.75 | $3.75 | Initial single-model baseline |
| `gemini-3.5-flash-lite` | $0.30 | $2.50 | Separate cost/latency pilot comparator |

Output pricing includes thinking. The 3.8 rates above run through December 31, 2026; listed rates double January 1, 2027. Recheck before collection. [Official pricing](https://ai.google.dev/gemini-api/docs/pricing). Flash-Lite is positioned for economical lightweight/high-volume tasks; task-specific adequacy still needs measurement. [Flash-Lite model](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).

Illustrative calculation, **not a budget forecast**: 1,000 calls averaging 1,000 input and 300 total billed output tokens cost about $1.88 on 3.8 or $1.05 on 3.5 Lite at those rates. Actual thinking, long prompts, images and retries alter the bill. Log provider usage; estimate total from the pilot, then set user-approved per-run and aggregate caps. No spending cap has been supplied yet.

## P09 implementation and evaluation decisions

1. Pin exact model ID, API/SDK version, schema and prompt. Do not use `gemini-flash-latest`, auto-routing or a silent fallback during a research cohort. Record reported model metadata because a stable ID alone is not a guarantee of immutable weights.
2. Start low thinking, one bounded request, compact catalogue, limited chat context and a sufficient output cap for eight steps. Do not copy an old `temperature=0` recipe blindly; use documented model-supported sampling defaults and freeze settings after pilot. Detect truncated output and reject it; never execute partial JSON.
3. No search, code execution, computer-use, external tools, or generated ROS commands. Use schema-constrained output plus the independent local validator. Captions are a separate read-only operation on requested snapshots; continuous video remains local, avoiding unnecessary per-frame cloud cost.
4. Before confirmatory Tests 1/6, use a **separate development set**: proposed 50 labeled utterances covering ambiguity, excess numbers, typos, mixed language, ordered sequences and stop; 10 nonparticipant scenes. Compare 3.8 low with 3.5 Lite's documented low-latency configuration only if budget permits. No motion. Keep all outputs and cost/timing records.
5. Score exact intent/slots/order, schema validity, clarification/refusal, p50/p95 total response time, quota failures and cost. Predeclare pilot acceptance: zero invalid outputs admitted by local validation; no silently changed explicit numeric limits; all designated stop checks bypass cloud; proposed >=95% exact interpretation on unambiguous pilot commands. A small pilot cannot establish safety or broad accuracy. If 3.8 misses the 8-s translation deadline, investigate prompt/settings/quotas; do not weaken the motion watchdog.
6. Choose Lite only if it meets the same predeclared criteria and materially improves measured latency/cost. Otherwise retain 3.8. Freeze one selected model before Test 1/6 datasets or participant collection; do not tune on held-out results. Retain a model-change amendment and separate cohorts if later migration is unavoidable.

Still needed from owner: API account access/region and billing availability (no key in chat), spending cap, acceptance of the direct-provider/image-description/offline policy recommendation. Study staffing and institutional requirements remain undecided independently of model choice.
