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
from collections import deque

import cv2
import requests
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy, QoSReliabilityPolicy
from std_msgs.msg import Int32, Bool, Float32
from sensor_msgs.msg import Image, Range
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
        self.create_subscription(Float32, '/aruco/distance', self._aruco_distance_cb, 10)
        self.create_subscription(Range, '/tof/range', self._tof_range_cb, 10)
        self.create_subscription(Float32, '/fused_distance', self._fused_distance_cb, 10)

        self.current_target = -1
        self.detected = False
        self.aruco_distance = None
        self.tof_distance = None
        self.fused_distance = None
        self.lock = threading.Lock()

        self.bridge = CvBridge()
        self.frame_lock = threading.Lock()
        self.latest_jpeg = None      # bytes, or None until the first frame arrives
        self.last_frame_time = 0.0
        self.frame_arrival_times = deque(maxlen=30)  # for the FPS readout in the header

    def _image_cb(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        except Exception as e:
            self.get_logger().warn(f"Could not encode camera frame: {e}", throttle_duration_sec=5.0)
            return
        if ok:
            now = time.monotonic()
            with self.frame_lock:
                self.latest_jpeg = buf.tobytes()
                self.last_frame_time = now
                self.frame_arrival_times.append(now)

    def get_latest_jpeg(self):
        with self.frame_lock:
            return self.latest_jpeg, self.last_frame_time

    def get_fps(self):
        with self.frame_lock:
            times = list(self.frame_arrival_times)
        if len(times) < 2:
            return None
        span = times[-1] - times[0]
        return (len(times) - 1) / span if span > 0 else None

    def _detected_cb(self, msg: Bool):
        with self.lock:
            self.detected = msg.data

    def _aruco_distance_cb(self, msg: Float32):
        with self.lock:
            self.aruco_distance = msg.data

    def _tof_range_cb(self, msg: Range):
        with self.lock:
            # ToF node publishes 0.0 for out-of-range readings - surface that
            # as None here so the UI shows "--" rather than a misleading 0.00m
            self.tof_distance = msg.range if msg.range > 0.0 else None

    def _fused_distance_cb(self, msg: Float32):
        with self.lock:
            self.fused_distance = msg.data

    def set_target(self, marker_id: int):
        with self.lock:
            self.current_target = marker_id
            self.detected = False  # stale until a fresh /aruco/detected arrives
        msg = Int32()
        msg.data = marker_id
        self.pub.publish(msg)

    def get_status(self):
        with self.lock:
            return {
                "target_id": self.current_target,
                "detected": self.detected,
                "aruco_distance": self.aruco_distance,
                "tof_distance": self.tof_distance,
                "fused_distance": self.fused_distance,
            }


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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #050B14;
    --panel: #0A1420;
    --panel-raised: #0F1C2C;
    --border: #13283A;
    --text: #E8EDF4;
    --muted: #5C7085;
    --cyan: #22D3EE;
    --cyan-dim: rgba(34,211,238,0.14);
    --orange: #F7A531;
    --green: #2DD4BF;
    --red: #F43F5E;
    --purple: #8B5CF6;
    --sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --hud: 'Rajdhani', var(--sans);
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body {
    margin: 0; font-family: var(--sans);
    background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column;
    overflow: hidden;
  }
  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

  svg.icon { width: 1em; height: 1em; flex-shrink: 0; vertical-align: -0.125em; }

  /* ---------- header ---------- */
  header {
    padding: 10px 20px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px;
    flex-shrink: 0; background: var(--panel);
  }
  .brand { display: flex; align-items: center; gap: 12px; }
  .brand .logo { width: 38px; height: 38px; color: var(--orange); filter: drop-shadow(0 0 5px rgba(247,165,49,0.5)); }
  .brand-titles { display: flex; flex-direction: column; line-height: 1.15; }
  .brand h1 {
    font-family: var(--hud); font-size: 19px; margin: 0; font-weight: 700; letter-spacing: 0.01em;
    color: var(--text);
  }
  .brand h1 .accent { color: var(--orange); }
  .brand .tagline { font-family: var(--hud); font-size: 12px; color: var(--cyan); font-weight: 600; letter-spacing: 0.04em; }

  .header-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .pill {
    display: flex; align-items: center; gap: 7px; font-family: var(--hud); font-weight: 600;
    font-size: 12.5px; padding: 7px 13px; border-radius: 20px; border: 1px solid var(--border);
    background: var(--panel-raised); white-space: nowrap;
  }
  .pill-live { border-color: var(--green); color: var(--green); }
  .pill-live .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 6px var(--green); }
  .pill-group { color: var(--text); gap: 9px; }
  .pill-group .g { color: var(--orange); }
  .pill-group .divider { color: var(--border); }
  #status {
    color: var(--cyan); border-color: var(--cyan); background: rgba(34,211,238,0.08);
  }
  #status.idle { color: var(--muted); border-color: var(--border); background: var(--panel-raised); }
  #status svg { color: inherit; }

  /* ---------- console (two-column body) ---------- */
  .console { flex: 1; display: flex; min-height: 0; padding: 16px; gap: 16px; }

  .viewport {
    flex: 1 1 auto; max-width: min(64vw, 1020px);
    position: relative; background: #000; min-width: 0;
    display: flex; align-items: center; justify-content: center;
    border: 1px solid var(--cyan); border-radius: 14px; overflow: hidden;
    box-shadow: 0 0 0 1px rgba(34,211,238,0.15), 0 0 24px rgba(34,211,238,0.12);
  }
  .viewport img { display: block; width: 100%; height: 100%; object-fit: contain; background: #000; }
  .hud-badge {
    position: absolute; display: flex; align-items: center; gap: 7px;
    background: rgba(5,11,20,0.78); color: var(--text); font-size: 12px; font-weight: 600;
    font-family: var(--hud); padding: 6px 12px; border-radius: 9px; letter-spacing: 0.03em;
    border: 1px solid var(--border);
  }
  .hud-top-left { top: 12px; left: 12px; }
  .hud-top-right { top: 12px; right: 12px; color: var(--cyan); }
  .hud-bottom-left { bottom: 12px; left: 12px; border-color: var(--cyan); color: var(--cyan); }
  .hud-bottom-right { bottom: 12px; right: 12px; color: var(--muted); }
  .hud-badge .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); }
  .video-overlay {
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    color: var(--muted); font-size: 13px; background: rgba(5,11,20,0.92); text-align: center; padding: 0 20px;
  }
  .video-overlay.hidden { display: none; }

  .sidebar {
    flex: 1 1 420px; min-width: 400px; min-height: 0;
    display: flex; flex-direction: column; gap: 12px; overflow-y: auto;
  }

  /* ---------- telemetry cards ---------- */
  .telemetry { display: flex; gap: 10px; flex-wrap: wrap; }
  .tcard {
    flex: 1 1 110px; border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px;
    background: var(--panel-raised);
  }
  .tcard.vision { border-color: rgba(34,211,238,0.35); }
  .tcard.tof { border-color: rgba(139,92,246,0.35); }
  .tcard.fused { border-color: rgba(45,212,191,0.4); background: rgba(45,212,191,0.05); }
  .tcard .thead { display: flex; align-items: center; gap: 7px; font-family: var(--hud); font-weight: 700;
    font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase; }
  .tcard.vision .thead { color: var(--cyan); }
  .tcard.tof .thead { color: var(--purple); }
  .tcard.fused .thead { color: var(--green); }
  .tcard .tvalue {
    font-family: var(--hud); font-size: 24px; font-weight: 700; margin-top: 6px;
    font-variant-numeric: tabular-nums; color: var(--text);
  }
  .tcard .tvalue.na { color: var(--muted); }
  .tcard .tcaption { font-size: 10.5px; color: var(--muted); margin-top: 2px; }

  /* ---------- intro banner ---------- */
  .intro {
    display: flex; align-items: flex-start; gap: 10px; padding: 13px 15px; border-radius: 10px;
    background: rgba(34,211,238,0.07); border: 1px solid rgba(34,211,238,0.3); font-size: 13px; line-height: 1.5;
  }
  .intro .icon-wrap {
    width: 26px; height: 26px; border-radius: 7px; background: var(--cyan); color: var(--bg);
    display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 14px;
  }
  .intro b { color: var(--cyan); }

  /* ---------- status & logs ---------- */
  .logpanel {
    flex: 1 1 auto; min-height: 140px; display: flex; flex-direction: column;
    border: 1px solid var(--border); border-radius: 10px; background: var(--panel-raised); overflow: hidden;
  }
  .logpanel-head {
    display: flex; align-items: center; justify-content: space-between; padding: 11px 14px;
    border-bottom: 1px solid var(--border); font-family: var(--hud); font-weight: 700; font-size: 13.5px;
  }
  .logpanel-head .lh-left { display: flex; align-items: center; gap: 8px; color: var(--text); }
  .logpanel-head .lh-right { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--green);
    font-weight: 600; font-family: var(--sans); }
  .logpanel-head .lh-right .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); box-shadow: 0 0 5px var(--green); }
  #chat { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 7px; }
  .logrow {
    display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 8px;
    background: rgba(255,255,255,0.02); border-left: 3px solid var(--border); font-size: 12.5px;
  }
  .logrow .lstate { flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
  .logrow .ltext { flex: 1; line-height: 1.4; }
  .logrow .ltime { flex-shrink: 0; font-family: var(--hud); font-size: 11px; color: var(--muted);
    display: flex; align-items: center; gap: 6px; }
  .logrow .ltime .dot { width: 5px; height: 5px; border-radius: 50%; background: var(--muted); }
  .logrow.follow { border-left-color: var(--green); background: rgba(45,212,191,0.06); }
  .logrow.follow .lstate { color: var(--green); }
  .logrow.stop { border-left-color: var(--red); background: rgba(244,63,94,0.07); }
  .logrow.stop .lstate { color: var(--red); }
  .logrow.user { border-left-color: var(--orange); background: rgba(247,165,49,0.06); }
  .logrow.user .lstate { color: var(--orange); }
  .logrow.unknown { border-left-color: var(--muted); }
  .logrow.unknown .lstate { color: var(--muted); }

  /* ---------- marker control ---------- */
  .control-panel {
    border: 1px solid var(--border); border-radius: 10px; background: var(--panel-raised);
    padding: 13px 14px; flex-shrink: 0;
  }
  .control-head {
    display: flex; align-items: center; gap: 8px; font-family: var(--hud); font-weight: 700; font-size: 13.5px;
    margin-bottom: 11px; color: var(--text);
  }
  .control-head svg { color: var(--cyan); }
  .quick-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 9px; }
  .quick-btn {
    font-family: var(--hud); cursor: pointer; border-radius: 8px;
    font-size: 13.5px; font-weight: 700; line-height: 1;
    display: flex; align-items: center; justify-content: center; gap: 6px;
  }
  .quick-btn.follow {
    flex: 1 1 auto; min-width: 84px; padding: 11px 8px;
    background: var(--panel); color: var(--orange); border: 1.5px solid var(--orange);
  }
  .quick-btn.follow.active {
    background: var(--cyan); color: #04141A; border-color: var(--cyan);
    box-shadow: 0 0 10px rgba(34,211,238,0.5);
  }
  .quick-btn.follow:active { filter: brightness(0.9); }
  .quick-btn.stop {
    width: 100%; padding: 13px 10px; background: var(--red); color: #210008;
    border: 1.5px solid var(--red); font-size: 14.5px; letter-spacing: 0.04em;
  }
  .quick-btn.stop:active { filter: brightness(0.9); }
  button:disabled { opacity: 0.5; cursor: default; }

  /* ---------- composer ---------- */
  form { display: flex; gap: 9px; margin-top: 10px; }
  input[type=text] {
    flex: 1; background: var(--panel); border: 1px solid var(--border); color: var(--text);
    padding: 11px 13px; border-radius: 9px; font-size: 14px; font-family: var(--sans); outline: none;
  }
  input[type=text]:focus { border-color: var(--cyan); }
  #send {
    background: var(--orange); color: #241400; border: none; padding: 0 18px; border-radius: 9px;
    font-size: 14px; cursor: pointer; font-weight: 700; font-family: var(--hud);
    display: flex; align-items: center; gap: 7px;
  }

  /* ---------- footer ---------- */
  footer {
    flex-shrink: 0; border-top: 1px solid var(--border); background: var(--panel);
    padding: 11px 22px; display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 14px; font-size: 12.5px;
  }
  .foot-dept { display: flex; align-items: center; gap: 10px; }
  .foot-dept svg { width: 26px; height: 26px; color: var(--orange); flex-shrink: 0; }
  .foot-dept-titles { display: flex; flex-direction: column; line-height: 1.3; }
  .foot-dept-titles .d1 { font-weight: 700; color: var(--text); }
  .foot-dept-titles .d2 { color: var(--muted); font-size: 11.5px; }
  .foot-divider { width: 1px; align-self: stretch; background: var(--border); }
  .foot-group {
    display: flex; align-items: center; gap: 7px; font-family: var(--hud); font-weight: 700;
    color: var(--orange); background: rgba(247,165,49,0.08); border: 1px solid rgba(247,165,49,0.35);
    padding: 6px 12px; border-radius: 8px;
  }
  .foot-roll { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }
  .foot-roll-label { display: flex; align-items: center; gap: 6px; color: var(--muted); font-weight: 600; }
  .foot-roll-pills { display: flex; flex-wrap: wrap; gap: 6px; }
  .roll-pill {
    font-family: var(--hud); font-size: 11.5px; font-weight: 600; color: var(--text);
    background: var(--panel-raised); border: 1px solid var(--border); padding: 4px 9px; border-radius: 6px;
  }

  /* ---------- narrow screens: stack camera over sidebar ---------- */
  @media (max-width: 960px) {
    .console { flex-direction: column; }
    .viewport { flex: 0 0 40vh; max-width: 100%; }
    .sidebar { width: 100%; min-width: 0; }
    footer { flex-direction: column; align-items: flex-start; }
  }
</style>
</head>
<body>

<header>
  <div class="brand">
    <svg class="logo icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
      <circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.2"/>
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>
    </svg>
    <div class="brand-titles">
      <h1>ArUco Marker <span class="accent">Commander</span></h1>
      <div class="tagline">NATURAL LANGUAGE CONTROL</div>
    </div>
  </div>
  <div class="header-right">
    <div class="pill pill-live">
      <span class="dot"></span>LIVE
    </div>
    <div class="pill pill-group">
      <span class="g">GROUP 4</span><span class="divider">|</span>MTE 4108
    </div>
    <div class="pill" id="status">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <circle cx="12" cy="8" r="3.2"/><path d="M5 20c0-4 3.1-6.5 7-6.5s7 2.5 7 6.5"/>
      </svg>
      <span id="status-text">No target &middot; waiting for a command</span>
    </div>
  </div>
</header>

<div class="console">
  <div class="viewport">
    <img id="feed" src="/video_feed" alt="camera feed">

    <div class="hud-badge hud-top-left">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <rect x="2" y="6" width="14" height="12" rx="2"/><path d="M16 10l6-3v10l-6-3"/>
      </svg>
      Camera View<span class="dot"></span>
    </div>
    <div class="hud-badge hud-top-right">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M3 20V10M9 20V4M15 20v-7M21 20V8"/>
      </svg>
      FPS <span id="fps-value">--</span>
    </div>
    <div class="hud-badge hud-bottom-left" id="marker-badge">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2.4"/>
      </svg>
      <span id="marker-badge-text">No target</span>
    </div>
    <div class="hud-badge hud-bottom-right" id="clock-badge">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>
      </svg>
      <span id="clock-text">--:--:--</span>
    </div>
    <div id="video-overlay" class="video-overlay">Waiting for camera feed&hellip;</div>
  </div>

  <aside class="sidebar">
    <div class="telemetry">
      <div class="tcard vision">
        <div class="thead">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z"/><circle cx="12" cy="12" r="2.6"/>
          </svg>
          Vision
        </div>
        <div class="tvalue" id="dist-aruco">--</div>
        <div class="tcaption">Distance to target</div>
      </div>
      <div class="tcard tof">
        <div class="thead">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.2"/><path d="M12 3v2.4M12 18.6V21M3 12h2.4M18.6 12H21"/>
          </svg>
          ToF
        </div>
        <div class="tvalue" id="dist-tof">--</div>
        <div class="tcaption">Time-of-flight range</div>
      </div>
      <div class="tcard fused">
        <div class="thead">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
          Fused
        </div>
        <div class="tvalue" id="dist-fused">--</div>
        <div class="tcaption">Filtered distance</div>
      </div>
    </div>

    <div class="intro">
      <div class="icon-wrap">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
      </div>
      <div>Tell me which marker to follow, e.g. <b>&ldquo;follow marker 2&rdquo;</b>, or say <b>&ldquo;stop&rdquo;</b> at any time.</div>
    </div>

    <div class="logpanel">
      <div class="logpanel-head">
        <div class="lh-left">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M8 4h11a1 1 0 011 1v15l-4-3-4 3-4-3-4 3V7a3 3 0 013-3z"/><path d="M9 9h7M9 13h7"/>
          </svg>
          Status &amp; Logs
        </div>
        <div class="lh-right"><span class="dot"></span>Live Updates</div>
      </div>
      <div id="chat"></div>
    </div>

    <div class="control-panel">
      <div class="control-head">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="0.8" fill="currentColor"/>
        </svg>
        Marker Control
      </div>
      <div class="quick-row">
        <button type="button" class="quick-btn follow" data-marker="1" data-cmd="follow marker 1">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/></svg>
          Marker 1
        </button>
        <button type="button" class="quick-btn follow" data-marker="2" data-cmd="follow marker 2">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/></svg>
          Marker 2
        </button>
        <button type="button" class="quick-btn follow" data-marker="3" data-cmd="follow marker 3">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/></svg>
          Marker 3
        </button>
        <button type="button" class="quick-btn follow" data-marker="4" data-cmd="follow marker 4">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/></svg>
          Marker 4
        </button>
      </div>
      <button type="button" class="quick-btn stop" data-cmd="stop">
        <svg class="icon" viewBox="0 0 24 24" fill="currentColor"><rect x="5" y="5" width="14" height="14" rx="2"/></svg>
        STOP FOLLOWING
      </button>
      <form id="form">
        <input type="text" id="input" autocomplete="off" placeholder="e.g. follow id 2, or stop following" autofocus>
        <button type="submit" id="send">
          <svg class="icon" viewBox="0 0 24 24" fill="currentColor"><path d="M3 20l18-8L3 4l0 7 12 1-12 1z"/></svg>
          Send
        </button>
      </form>
    </div>
  </aside>
</div>

<footer>
  <div class="foot-dept">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
      <path d="M12 3l10 5-10 5L2 8z"/><path d="M6 11v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5"/>
    </svg>
    <div class="foot-dept-titles">
      <div class="d1">Department of Mechatronics Engineering</div>
      <div class="d2">Khulna University of Engineering &amp; Technology</div>
    </div>
  </div>
  <div class="foot-divider"></div>
  <div class="foot-group">
    <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
      <circle cx="9" cy="8" r="3"/><path d="M2 20c0-3.3 3-5.5 7-5.5s7 2.2 7 5.5"/><circle cx="17" cy="9" r="2.6"/><path d="M16 14.3c2.6.4 4.5 2.1 4.5 4.2"/>
    </svg>
    Group 4
  </div>
  <div class="foot-roll">
    <div class="foot-roll-label">
      <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M8 3h8a1 1 0 011 1v16l-4.5-2.5L8 20V4a1 1 0 010 0z"/><path d="M9 8h6M9 11h6"/>
      </svg>
      Roll:
    </div>
    <div class="foot-roll-pills" id="roll-pills">
      <!-- EDIT ME: replace with your team's 6 actual roll numbers -->
      <span class="roll-pill">2131020</span>
      <span class="roll-pill">2131021</span>
      <span class="roll-pill">2131022</span>
      <span class="roll-pill">2131023</span>
      <span class="roll-pill">2131024</span>
      <span class="roll-pill">2131025</span>
    </div>
  </div>
</footer>

<script>
const chat = document.getElementById('chat');
const form = document.getElementById('form');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const statusEl = document.getElementById('status');
const statusText = document.getElementById('status-text');
const videoOverlay = document.getElementById('video-overlay');
const fpsValue = document.getElementById('fps-value');
const markerBadge = document.getElementById('marker-badge');
const markerBadgeText = document.getElementById('marker-badge-text');
const clockText = document.getElementById('clock-text');
const distAruco = document.getElementById('dist-aruco');
const distTof = document.getElementById('dist-tof');
const distFused = document.getElementById('dist-fused');

const ICONS = {
  follow: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M8 12l2.5 2.5L16 9"/></svg>',
  stop: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/></svg>',
  user: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="3.2"/><path d="M5 20c0-4 3.1-6.5 7-6.5s7 2.5 7 6.5"/></svg>',
  unknown: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 16v.01M12 8a2.2 2.2 0 012.2 2.2c0 1.6-2.2 1.8-2.2 3.3"/></svg>',
};

function nowHHMMSS() {
  const d = new Date();
  return [d.getHours(), d.getMinutes(), d.getSeconds()].map(n => String(n).padStart(2, '0')).join(':');
}

function renderDistance(el, value) {
  if (value === null || value === undefined) {
    el.textContent = '--';
    el.classList.add('na');
  } else {
    el.textContent = value.toFixed(2) + 'm';
    el.classList.remove('na');
  }
}

function addLog(text, kind) {
  const row = document.createElement('div');
  row.className = 'logrow ' + kind;
  row.innerHTML =
    '<span class="lstate">' + (ICONS[kind] || ICONS.unknown) + '</span>' +
    '<span class="ltext"></span>' +
    '<span class="ltime"><span class="dot"></span>' + nowHHMMSS() + '</span>';
  row.querySelector('.ltext').textContent = text;
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
}

function setActiveMarkerButton(targetId) {
  document.querySelectorAll('.quick-btn.follow').forEach((btn) => {
    btn.classList.toggle('active', String(targetId) === btn.dataset.marker);
  });
}

function renderStatus(s) {
  if (s.target_id >= 0) {
    statusEl.classList.remove('idle');
    statusText.innerHTML = 'Following marker <b>' + s.target_id + '</b>'
      + (s.detected ? ' &middot; visible' : ' &middot; not visible');
    markerBadgeText.textContent = 'Marker ' + s.target_id;
  } else {
    statusEl.classList.add('idle');
    statusText.textContent = 'No target &middot; waiting for a command';
    markerBadgeText.textContent = 'No target';
  }
  setActiveMarkerButton(s.target_id);

  if (s.feed_age === null || s.feed_age === undefined || s.feed_age > 3) {
    videoOverlay.classList.remove('hidden');
    fpsValue.textContent = '--';
  } else {
    videoOverlay.classList.add('hidden');
    fpsValue.textContent = (s.fps === null || s.fps === undefined) ? '--' : s.fps.toFixed(1);
  }

  renderDistance(distAruco, s.aruco_distance);
  renderDistance(distTof, s.tof_distance);
  renderDistance(distFused, s.fused_distance);
}

setInterval(() => { clockText.textContent = nowHHMMSS(); }, 1000);
clockText.textContent = nowHHMMSS();

async function poll() {
  try {
    const r = await fetch('/api/status');
    renderStatus(await r.json());
  } catch (e) { /* ignore transient errors */ }
}
setInterval(poll, 300);
poll();

async function sendCommand(text) {
  if (!text) return;
  addLog(text, 'user');
  sendBtn.disabled = true;
  document.querySelectorAll('.quick-btn').forEach(b => b.disabled = true);
  try {
    const r = await fetch('/api/command', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    const data = await r.json();
    addLog(data.reply, data.action === 'follow' ? 'follow' : (data.action === 'stop' ? 'stop' : 'unknown'));
    if (data.status) renderStatus(data.status);
  } catch (err) {
    addLog('Could not reach the robot (network error).', 'unknown');
  } finally {
    sendBtn.disabled = false;
    document.querySelectorAll('.quick-btn').forEach(b => b.disabled = false);
    input.focus();
  }
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  sendCommand(text);
});

document.querySelectorAll('.quick-btn').forEach((btn) => {
  btn.addEventListener('click', () => sendCommand(btn.dataset.cmd));
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
    st["fps"] = ros_node.get_fps()
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
