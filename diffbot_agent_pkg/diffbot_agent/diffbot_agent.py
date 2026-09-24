#!/usr/bin/env python3
"""
diffbot_agent.py

The LLM agent node for the skill-library architecture:
  - Loads skills.yaml (the permissioned skill library)
  - Subscribes to text commands from the web frontend (/diffbot/user_command)
  - Sends the command + skill schema to Gemini, gets back a structured
    {"skill": ..., "params": {...}} choice
  - Validates that choice against skills.yaml (name exists, params in bounds)
    before dispatching anything to hardware
  - Publishes status/response/image back to the web frontend
  - Handles a dedicated emergency-stop path that bypasses the LLM entirely

Movement skills publish onto /cmd_vel_llm, a twist_mux input (priority 50) —
NOT directly to the controller — so navigation/joystick/emergency inputs
still arbitrate normally. Emergency publishes onto /cmd_vel_emergency
(twist_mux priority 200, highest) for near-immediate override.

Command execution runs in a background thread so the ROS executor stays free
to process emergency-stop messages while a movement skill is mid-execution.
"""

import base64
import json
import os
import threading
import time

import requests
import yaml
import cv2

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from std_msgs.msg import String, Empty
from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import Image

from cv_bridge import CvBridge


GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)


class DiffbotAgent(Node):

    def __init__(self):
        super().__init__('diffbot_agent')

        self.declare_parameter('skills_yaml_path', '')
        skills_path = self.get_parameter('skills_yaml_path').value
        if not skills_path or not os.path.isfile(skills_path):
            raise FileNotFoundError(
                f"skills_yaml_path not set or file not found: '{skills_path}'. "
                "Pass it with -p skills_yaml_path:=/path/to/skills.yaml"
            )
        with open(skills_path, 'r') as f:
            self.skill_library = yaml.safe_load(f)['skills']
        self.skills_by_name = {s['name']: s for s in self.skill_library}

        self.bridge = CvBridge()
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.emergency_flag = threading.Event()

        # --- Publishers ---
        self.cmd_pub = self.create_publisher(TwistStamped, '/cmd_vel_llm', 10)
        self.emergency_cmd_pub = self.create_publisher(TwistStamped, '/cmd_vel_emergency', 10)
        self.status_pub = self.create_publisher(String, '/diffbot/web_status', 10)
        self.response_pub = self.create_publisher(String, '/diffbot/web_response', 10)
        self.image_pub = self.create_publisher(Image, '/diffbot/web_image', 10)

        # --- Subscribers ---
        self.create_subscription(String, '/diffbot/user_command', self._command_cb, 10)
        self.create_subscription(Empty, '/diffbot/web_emergency', self._emergency_cb, 10)
        self.create_subscription(Image, '/camera/image_raw', self._camera_cb, qos_profile_sensor_data)

        if not GEMINI_API_KEY:
            self.get_logger().warn(
                "GEMINI_API_KEY not set — commands will only work via the local keyword fallback parser."
            )

        self.get_logger().info(f"diffbot_agent up | {len(self.skill_library)} skills loaded from {skills_path}")
        self._publish_status("idle")

    # ---------------- camera ----------------

    def _camera_cb(self, msg: Image):
        with self.frame_lock:
            self.latest_frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    # ---------------- status/response helpers ----------------

    def _publish_status(self, state: str, detail: str = ""):
        self.status_pub.publish(String(data=json.dumps({"state": state, "detail": detail})))

    def _publish_response(self, text: str):
        self.response_pub.publish(String(data=text))

    # ---------------- emergency path ----------------

    def _emergency_cb(self, msg: Empty):
        self.get_logger().warn("EMERGENCY STOP triggered")
        self.emergency_flag.set()
        zero = TwistStamped()
        zero.header.stamp = self.get_clock().now().to_msg()
        # publish on both channels: emergency (top mux priority) and llm (in case
        # llm_agent's own input is what's currently active) for a fast local stop
        self.emergency_cmd_pub.publish(zero)
        self.cmd_pub.publish(zero)
        self._publish_status("emergency_stopped")
        self._publish_response("Emergency stop triggered.")

    # ---------------- command handling ----------------

    def _command_cb(self, msg: String):
        # Run in a background thread so this callback returns immediately and
        # the executor stays free to handle _emergency_cb while a skill runs.
        threading.Thread(target=self._handle_command, args=(msg.data,), daemon=True).start()

    def _handle_command(self, text: str):
        self.emergency_flag.clear()
        self._publish_status("thinking", text)

        skill_call = self._parse_command(text)
        if skill_call is None:
            self._publish_response("Sorry, I couldn't understand that command.")
            self._publish_status("idle")
            return

        ok, error = self._validate_skill_call(skill_call)
        if not ok:
            self._publish_response(f"Rejected: {error}")
            self._publish_status("idle")
            return

        name = skill_call['skill']
        params = skill_call.get('params', {})
        self._publish_status("executing", name)

        try:
            self._dispatch(name, params)
        except Exception as e:
            self.get_logger().error(f"Skill '{name}' failed: {e}")
            self._publish_response(f"Skill '{name}' failed: {e}")

        self._publish_status("idle")

    # ---------------- LLM parsing + local fallback ----------------

    def _build_system_prompt(self):
        skill_descriptions = []
        for s in self.skill_library:
            params_desc = ", ".join(
                f"{p['name']}:{p['type']}[{p.get('min','')}-{p.get('max','')}]"
                for p in s.get('params', [])
            ) or "none"
            skill_descriptions.append(f"- {s['name']}: {s['description']} (params: {params_desc})")

        return (
            "You are a robot command parser. Given a user's natural language instruction, "
            "choose exactly ONE skill from this list and output STRICT JSON only, no other text:\n"
            + "\n".join(skill_descriptions) +
            '\n\nOutput format: {"skill": "<name>", "params": {...}}\n'
            "If the instruction doesn't clearly match any skill, output "
            '{"skill": null, "params": {}}'
        )

    def _parse_command(self, text: str):
        if GEMINI_API_KEY:
            result = self._parse_with_gemini(text)
            if result is not None:
                return result
            self.get_logger().warn("Gemini parse failed, falling back to local keyword parser")
        return self._parse_with_keywords(text)

    def _parse_with_gemini(self, text: str):
        try:
            payload = {
                "system_instruction": {"parts": [{"text": self._build_system_prompt()}]},
                "contents": [{"parts": [{"text": text}]}],
                "generationConfig": {"response_mime_type": "application/json"},
            }
            resp = requests.post(GEMINI_URL, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            if not parsed.get("skill"):
                return None
            return parsed
        except Exception as e:
            self.get_logger().warn(f"Gemini request error: {e}")
            return None

    def _parse_with_keywords(self, text: str):
        t = text.lower().strip()
        if "stop" in t and "emergency" in t:
            return {"skill": "emergency_stop", "params": {}}
        if "stop" in t or "halt" in t:
            return {"skill": "stop_robot", "params": {}}
        if "forward" in t or "ahead" in t:
            return {"skill": "move_forward_distance", "params": {"distance_m": 0.3}}
        if "back" in t or "reverse" in t:
            return {"skill": "move_backward_distance", "params": {"distance_m": 0.3}}
        if "left" in t:
            return {"skill": "rotate_angle", "params": {"angle_deg": 45.0}}
        if "right" in t:
            return {"skill": "rotate_angle", "params": {"angle_deg": -45.0}}
        if "what do you see" in t or "describe" in t or "look" in t:
            return {"skill": "describe_scene", "params": {}}
        if "snapshot" in t or "picture" in t or "photo" in t:
            return {"skill": "capture_snapshot", "params": {}}
        if "status" in t:
            return {"skill": "get_status", "params": {}}
        return None

    # ---------------- validation ----------------

    def _validate_skill_call(self, call):
        name = call.get('skill')
        if name not in self.skills_by_name:
            return False, f"Unknown skill '{name}'"

        schema = self.skills_by_name[name]
        params = call.get('params', {})

        for p in schema.get('params', []):
            pname = p['name']
            if pname not in params:
                if 'default' in p:
                    params[pname] = p['default']
                else:
                    return False, f"Missing required param '{pname}' for skill '{name}'"
            val = params[pname]
            if p['type'] == 'float':
                try:
                    val = float(val)
                except (TypeError, ValueError):
                    return False, f"Param '{pname}' must be a number"
                if 'min' in p and val < p['min']:
                    return False, f"Param '{pname}'={val} below min {p['min']}"
                if 'max' in p and val > p['max']:
                    return False, f"Param '{pname}'={val} above max {p['max']}"
            params[pname] = val

        call['params'] = params
        return True, None

    # ---------------- skill dispatch ----------------

    def _dispatch(self, name, params):
        if name == 'move_forward_distance':
            self._timed_drive(params['distance_m'], params.get('speed_mps', 0.15), forward=True)
        elif name == 'move_backward_distance':
            self._timed_drive(params['distance_m'], params.get('speed_mps', 0.15), forward=False)
        elif name == 'rotate_angle':
            self._timed_rotate(params['angle_deg'], params.get('angular_speed_dps', 15.0))
        elif name == 'stop_robot':
            self._publish_twist(0.0, 0.0)
        elif name == 'emergency_stop':
            self._emergency_cb(Empty())
        elif name == 'capture_snapshot':
            self._publish_snapshot()
        elif name == 'describe_scene':
            self._describe_scene()
        elif name == 'get_status':
            self._publish_response(f"Skills loaded: {len(self.skill_library)}. Idle.")
        else:
            raise ValueError(f"No handler implemented for skill '{name}'")

    def _publish_twist(self, linear_x, angular_z):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.twist.linear.x = linear_x
        msg.twist.angular.z = angular_z
        self.cmd_pub.publish(msg)

    def _timed_drive(self, distance_m, speed_mps, forward=True):
        duration = distance_m / speed_mps
        signed_speed = speed_mps if forward else -speed_mps
        end_time = time.monotonic() + duration
        while time.monotonic() < end_time and not self.emergency_flag.is_set():
            self._publish_twist(signed_speed, 0.0)
            time.sleep(0.1)
        self._publish_twist(0.0, 0.0)

    def _timed_rotate(self, angle_deg, angular_speed_dps):
        duration = abs(angle_deg) / angular_speed_dps
        signed_speed_rad = (angular_speed_dps if angle_deg >= 0 else -angular_speed_dps) * 3.14159265 / 180.0
        end_time = time.monotonic() + duration
        while time.monotonic() < end_time and not self.emergency_flag.is_set():
            self._publish_twist(0.0, signed_speed_rad)
            time.sleep(0.1)
        self._publish_twist(0.0, 0.0)

    def _publish_snapshot(self):
        with self.frame_lock:
            frame = None if self.latest_frame is None else self.latest_frame.copy()
        if frame is None:
            self._publish_response("No camera frame available yet.")
            return
        img_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        self.image_pub.publish(img_msg)
        self._publish_response("Snapshot captured.")

    def _describe_scene(self):
        with self.frame_lock:
            frame = None if self.latest_frame is None else self.latest_frame.copy()
        if frame is None:
            self._publish_response("No camera frame available yet.")
            return

        img_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        self.image_pub.publish(img_msg)

        if not GEMINI_API_KEY:
            self._publish_response("Vision description unavailable (no GEMINI_API_KEY set).")
            return

        ok, jpg = cv2.imencode('.jpg', frame)
        if not ok:
            self._publish_response("Failed to encode frame for vision request.")
            return
        b64 = base64.b64encode(jpg.tobytes()).decode('utf-8')

        try:
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Briefly describe what the robot's camera sees, in one or two sentences."},
                        {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                    ]
                }]
            }
            resp = requests.post(GEMINI_URL, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            caption = data["candidates"][0]["content"]["parts"][0]["text"]
            self._publish_response(caption)
        except Exception as e:
            self.get_logger().error(f"describe_scene request failed: {e}")
            self._publish_response(f"Vision request failed: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = DiffbotAgent()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
