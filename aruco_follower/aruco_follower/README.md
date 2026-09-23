# aruco_follower Python Module

This directory contains the Python implementation of the `aruco_follower` ROS 2 package: the perception, control, and target-selection logic behind ArUco marker detection and following.

## Files

| File | Description |
|---|---|
| `aruco_detector.py` | OpenCV ArUco detection, camera calibration handling, `solvePnP()` pose estimation, active-target filtering, and debug-image generation. |
| `marker_follower.py` | Proportional visual-servoing controller that converts the active marker's pose into linear and angular velocity commands. |
| `set_target_marker.py` | Terminal interface for selecting or clearing the active target marker. |
| `web_target_commander.py` | Flask-based web interface for target selection, with a live debug-video stream and optional Gemini natural-language command parsing. |
| `__init__.py` | Python package initializer. |

Each of the four node modules is exposed as a ROS 2 executable through the package's `setup.py` console-script entry points, so they can be launched with `ros2 run aruco_follower <node>` without needing to reference the file paths directly.

See the [package-level README](../README.md) for topic and parameter documentation, and the [repository README](../../README.md) for the full system overview.
