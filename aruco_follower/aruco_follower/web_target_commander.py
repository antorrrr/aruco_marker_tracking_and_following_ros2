#!/usr/bin/env python3
"""
web_target_commander.py

Web-based, natural-language front end for commanding the ArUco marker
follower. Runs a small Flask web server alongside a ROS2 node. Instead of
typing a bare integer at a terminal prompt (set_target_marker.py), you type
things like:

    "follow marker 2"
    "track id 4 please"
    "stop following"
    "never mind, cancel"

and it's translated into the same /aruco/target_marker_id (std_msgs/Int32)
message set_target_marker.py publishes by hand. aruco_detector.py picks it
up live, exactly as before: the commanded id is boxed GREEN and its pose is
published, every other visible marker is boxed RED and ignored, and "stop"
sends -1 so nothing is tracked until the next follow command.

Natural-language parsing is done by calling the Gemini API. Get a free
API key at https://aistudio.google.com/apikey (needs a Google Cloud
project attached, which AI Studio can create for you). The free tier is
rate-limited but doesn't require billing to be enabled - plenty for a
command-parsing use case like this.

--------------------------------------------------------------------------
Setup
--------------------------------------------------------------------------
    sudo apt install python3-flask python3-requests    (or pip install --break-system-packages flask requests)
    export GEMINI_API_KEY="your-key-here"

Add the console_script entry in setup.py (see the updated setup.py) and
rebuild the package, then:

    ros2 run aruco_follower web_target_commander

Open http://<robot-ip>:5000 from any browser on the same network (phone,
laptop, etc).

Optional env vars:
    GEMINI_API_KEY   (required for real NL understanding - see fallback below)
    GEMINI_MODEL     (default: gemini-2.5-flash)
    WEB_PORT         (default: 5000)
    CAMERA_TOPIC     (default: /aruco/debug_image - the annotated feed to stream in the UI)

If GEMINI_API_KEY is not set, or the API call fails for any reason (offline,
bad key, rate limit), this node falls back to a small local keyword/regex
parser so "follow marker 2" / "stop" style commands still work - it just
won't understand phrasing as flexibly as Gemini does.

The page also streams CAMERA_TOPIC (aruco_detector's debug image - green box
on the target, red on everything else) as MJPEG at /video_feed, so you can
see what the robot sees without a separate rqt_image_view window. This
re-encodes frames to JPEG with OpenCV and serves them over plain HTTP -
fine for one or two viewers on a local network, not meant for many
concurrent viewers or the public internet.
"""

import os
import re
import io
import json
import time
import threading

import cv2
import requests
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy, QoSReliabilityPolicy
from std_msgs.msg import Int32, Bool
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from flask import Flask, request, jsonify, render_template_string, Response


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
WEB_PORT = int(os.environ.get("WEB_PORT", "5000"))
CAMERA_TOPIC = os.environ.get("CAMERA_TOPIC", "/aruco/debug_image")

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

SYSTEM_INSTRUCTION = """You translate short natural-language instructions for an \
ArUco-marker-following robot into strict JSON.

Marker ids are non-negative integers.

Respond with ONLY a single JSON object, no prose, no markdown fences, matching
exactly one of these shapes:

  {"action": "follow", "marker_id": <int>}   user wants to follow/track/go to that id
  {"action": "stop"}                         user wants to stop following / clear the target
  {"action": "unknown"}                      the instruction doesn't map to either of the above

Examples:
"follow id 2" -> {"action": "follow", "marker_id": 2}
"track marker 4 please" -> {"action": "follow", "marker_id": 4}
"go to marker number 0" -> {"action": "follow", "marker_id": 0}
"stop following id 2" -> {"action": "stop"}
"cancel" -> {"action": "stop"}
"never mind, stop" -> {"action": "stop"}
"what's the weather" -> {"action": "unknown"}
"""


def parse_command_with_gemini(text: str) -> dict:
    """Ask Gemini to turn free text into a structured command. Falls back to
    a small local rule-based parser if the API key is missing or the call
    fails, so the interface still works without it."""
    if GEMINI_API_KEY:
        try:
            payload = {
                "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
                "contents": [{"role": "user", "parts": [{"text": text}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.0,
                },
            }
            resp = requests.post(GEMINI_URL, json=payload, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            raw = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw)
            if parsed.get("action") in ("follow", "stop", "unknown"):
                return parsed
        except Exception as e:
            print(f"[web_target_commander] Gemini call failed, using local fallback parser: {e}")

    return _fallback_parse(text)


def _fallback_parse(text: str) -> dict:
    """Small local fallback so the UI still works without an API key."""
    t = text.lower().strip()
    if any(w in t for w in ("stop", "cancel", "clear", "never mind", "quit", "halt")):
        return {"action": "stop"}
    m = re.search(r"(?:id|marker|number)\D{0,5}(\d+)", t)
    if not m:
        m = re.search(r"(\d+)", t)
    if m:
        return {"action": "follow", "marker_id": int(m.group(1))}
    return {"action": "unknown"}


class WebTargetCommander(Node):
    def __init__(self):
        super().__init__('web_target_commander')

        # Transient-local, same as set_target_marker.py: a late-starting
        # aruco_detector still gets the last commanded id on connect.
        qos = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
        )
        self.pub = self.create_publisher(Int32, '/aruco/target_marker_id', qos)
        self.create_subscription(Bool, '/aruco/detected', self._detected_cb, 10)
        self.create_subscription(Image, CAMERA_TOPIC, self._image_cb, qos_profile_sensor_data)

        self.current_target = -1
        self.detected = False
        self.lock = threading.Lock()

        self.bridge = CvBridge()
        self.frame_lock = threading.Lock()
        self.latest_jpeg = None      # bytes, or None until the first frame arrives
        self.last_frame_time = 0.0

    def _image_cb(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        except Exception as e:
            self.get_logger().warn(f"Could not encode camera frame: {e}", throttle_duration_sec=5.0)
            return
        if ok:
            with self.frame_lock:
                self.latest_jpeg = buf.tobytes()
                self.last_frame_time = time.monotonic()

    def get_latest_jpeg(self):
        with self.frame_lock:
            return self.latest_jpeg, self.last_frame_time

    def _detected_cb(self, msg: Bool):
        with self.lock:
            self.detected = msg.data

    def set_target(self, marker_id: int):
        with self.lock:
            self.current_target = marker_id
            self.detected = False  # stale until a fresh /aruco/detected arrives
        msg = Int32()
        msg.data = marker_id
        self.pub.publish(msg)

    def get_status(self):
        with self.lock:
            return {"target_id": self.current_target, "detected": self.detected}


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
ros_node: "WebTargetCommander" = None  # set in main()


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ArUco Marker Commander</title>
<style>
  :root {
    --bg: #0f1115; --panel: #171a21; --border: #262b36;
    --text: #e7e9ee; --muted: #8b93a3;
    --green: #2ecc71; --red: #e74c3c; --accent: #5b8def;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column;
  }
  header {
    padding: 16px 20px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;
  }
  header h1 { font-size: 17px; margin: 0; font-weight: 600; }
  header h1 span { color: var(--muted); font-weight: 400; }
  #status {
    display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--muted);
    background: var(--panel); border: 1px solid var(--border); padding: 6px 12px; border-radius: 20px;
  }
  #status .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--muted); }
  #status.following .dot { background: var(--green); }
  #status.idle .dot { background: var(--muted); }
  #status .target-id { color: var(--text); font-weight: 600; }
  #chat {
    flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 10px;
  }
  .msg { max-width: 70%; padding: 10px 14px; border-radius: 14px; line-height: 1.4; font-size: 14.5px; }
  .msg.user { align-self: flex-end; background: var(--accent); color: white; border-bottom-right-radius: 4px; }
  .msg.bot { align-self: flex-start; background: var(--panel); border: 1px solid var(--border); border-bottom-left-radius: 4px; }
  .msg.bot.follow { border-color: var(--green); }
  .msg.bot.stop { border-color: var(--red); }
  form {
    display: flex; gap: 10px; padding: 16px 20px; border-top: 1px solid var(--border); background: var(--bg);
  }
  input[type=text] {
    flex: 1; background: var(--panel); border: 1px solid var(--border); color: var(--text);
    padding: 12px 14px; border-radius: 10px; font-size: 15px; outline: none;
  }
  input[type=text]:focus { border-color: var(--accent); }
  button {
    background: var(--accent); color: white; border: none; padding: 0 20px; border-radius: 10px;
    font-size: 15px; cursor: pointer; font-weight: 600;
  }
  button:disabled { opacity: 0.5; cursor: default; }
  .hint { color: var(--muted); font-size: 12.5px; padding: 0 20px 14px; margin-top: -8px; }
  .video-wrap { position: relative; background: #000; border-bottom: 1px solid var(--border); flex-shrink: 0; }
  .video-wrap img { display: block; width: 100%; max-height: 38vh; object-fit: contain; background: #000; }
  .video-badge {
    position: absolute; top: 10px; left: 10px; display: flex; align-items: center; gap: 6px;
    background: rgba(0,0,0,0.55); color: var(--text); font-size: 11.5px; font-weight: 600;
    padding: 4px 10px; border-radius: 20px; letter-spacing: 0.03em;
  }
  .video-badge .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); }
  .video-badge.live .dot { background: var(--green); }
  .video-badge.stale .dot { background: var(--red); }
  .video-overlay {
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    color: var(--muted); font-size: 13px; background: rgba(15,17,21,0.9); text-align: center; padding: 0 20px;
  }
  .video-overlay.hidden { display: none; }
</style>
</head>
<body>

<header>
  <h1>ArUco Marker Commander <span>&mdash; natural language control</span></h1>
  <div id="status" class="idle">
    <span class="dot"></span>
    <span id="status-text">No target &middot; waiting for a command</span>
  </div>
</header>

<div class="video-wrap">
  <img id="feed" src="/video_feed" alt="camera feed">
  <div id="video-badge" class="video-badge">
    <span class="dot"></span><span id="video-badge-text">FEED</span>
  </div>
  <div id="video-overlay" class="video-overlay">Waiting for camera feed&hellip;</div>
</div>

<div id="chat">
  <div class="msg bot">Tell me which marker to follow, e.g. <b>"follow marker 2"</b>, or say <b>"stop"</b> at any time.</div>
</div>

<form id="form">
  <input type="text" id="input" autocomplete="off" placeholder="e.g. follow id 2, or stop following" autofocus>
  <button type="submit" id="send">Send</button>
</form>
<div class="hint">Every other visible marker is boxed red and ignored while a target is set.</div>

<script>
const chat = document.getElementById('chat');
const form = document.getElementById('form');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const statusEl = document.getElementById('status');
const statusText = document.getElementById('status-text');
const videoOverlay = document.getElementById('video-overlay');
const videoBadge = document.getElementById('video-badge');
const videoBadgeText = document.getElementById('video-badge-text');

function addMsg(text, who, cls) {
  const div = document.createElement('div');
  div.className = 'msg ' + who + (cls ? ' ' + cls : '');
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function renderStatus(s) {
  if (s.target_id >= 0) {
    statusEl.className = 'following';
    statusText.innerHTML = 'Following marker <span class="target-id">' + s.target_id + '</span>'
      + (s.detected ? ' &middot; visible' : ' &middot; not currently visible');
  } else {
    statusEl.className = 'idle';
    statusText.textContent = 'No target \u00b7 waiting for a command';
  }

  if (s.feed_age === null || s.feed_age === undefined || s.feed_age > 3) {
    videoOverlay.classList.remove('hidden');
    videoBadge.className = 'video-badge stale';
    videoBadgeText.textContent = 'NO FEED';
  } else {
    videoOverlay.classList.add('hidden');
    videoBadge.className = 'video-badge live';
    videoBadgeText.textContent = 'LIVE';
  }
}

async function poll() {
  try {
    const r = await fetch('/api/status');
    renderStatus(await r.json());
  } catch (e) { /* ignore transient errors */ }
}
setInterval(poll, 1500);
poll();

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  addMsg(text, 'user');
  input.value = '';
  sendBtn.disabled = true;
  try {
    const r = await fetch('/api/command', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    const data = await r.json();
    addMsg(data.reply, 'bot', data.action === 'follow' ? 'follow' : (data.action === 'stop' ? 'stop' : ''));
    if (data.status) renderStatus(data.status);
  } catch (err) {
    addMsg('Could not reach the robot (network error).', 'bot');
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/api/status")
def status():
    st = ros_node.get_status()
    _, last_frame_time = ros_node.get_latest_jpeg()
    st["feed_age"] = (time.monotonic() - last_frame_time) if last_frame_time else None
    return jsonify(st)


def mjpeg_generator():
    """Yields the latest annotated camera frame as multipart JPEG, at up to ~15fps.
    Re-sends the last frame if nothing new has arrived so the stream doesn't stall."""
    boundary = b"--frame"
    while True:
        frame, _ = ros_node.get_latest_jpeg()
        if frame is not None:
            yield (
                boundary + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
                + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"
            )
        time.sleep(1.0 / 15.0)


@app.route("/video_feed")
def video_feed():
    return Response(mjpeg_generator(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/command", methods=["POST"])
def command():
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"reply": "Say something like \"follow marker 2\".", "action": "unknown"})

    parsed = parse_command_with_gemini(text)
    action = parsed.get("action")

    if action == "follow" and "marker_id" in parsed:
        try:
            marker_id = int(parsed["marker_id"])
        except (TypeError, ValueError):
            action = "unknown"
            reply = "I heard a follow command but couldn't tell which marker id. Try \"follow marker 2\"."
        else:
            ros_node.set_target(marker_id)
            reply = f"Following marker {marker_id}. Every other marker is boxed red and ignored."
    elif action == "stop":
        ros_node.set_target(-1)
        reply = "Stopped. No marker is being followed until you give the next command."
    else:
        action = "unknown"
        reply = "I didn't catch a marker command in that. Try \"follow marker 3\" or \"stop\"."

    return jsonify({"reply": reply, "action": action, "status": ros_node.get_status()})


def main(args=None):
    global ros_node
    rclpy.init(args=args)
    ros_node = WebTargetCommander()

    if not GEMINI_API_KEY:
        ros_node.get_logger().warn(
            "GEMINI_API_KEY not set - using basic local keyword parsing only. "
            "export GEMINI_API_KEY=... for full natural-language understanding via Gemini."
        )

    spin_thread = threading.Thread(target=rclpy.spin, args=(ros_node,), daemon=True)
    spin_thread.start()

    ros_node.get_logger().info(f"Web commander UI at http://0.0.0.0:{WEB_PORT}")
    try:
        app.run(host="0.0.0.0", port=WEB_PORT, threaded=True)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
