# ArUco Marker Tracking and Following with ROS 2
A ROS 2-based autonomous mobile robot system for detecting, identifying, tracking, and following a selected ArUco marker using computer vision.

The project combines:
- ArUco marker detection using OpenCV
- Camera-based 6-DoF marker pose estimation
- Target marker selection
- Proportional visual servoing
- Differential-drive robot control
- ROS 2 Control
- Serial communication with an Arduino-based motor controller
- Gazebo Sim warehouse simulation
- 'twist_mux' for command arbitration
- Web-based natural-language marker selection
- ROS 2 'Twist / TwistStamped' conversion

**1. Project Overview**
The system is designed around a camera-mounted differential-drive mobile robot.
The basic operation is:
Camera 
  │
  ▼
ArUco Detector
  │
  ├── Marker ID
  ├── Marker Pose
  ├── Distance
  └── Detection Status
  │
  ▼
Marker Follower
  │
  └── TwistStamped velocity command
           │
           ▼
        twist_mux
           │
           ▼
   Differential Drive Controller
           │
           ▼
  
