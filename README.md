# ROS Noetic Z1 Arm Simulation

Gazebo simulation of the Unitree Z1 robotic arm with ArUco marker tracking, containerized in Docker.

![ROS Noetic](https://img.shields.io/badge/ROS-Noetic-blue)
![Python 3.8](https://img.shields.io/badge/Python-3.8-blue)
![Docker](https://img.shields.io/badge/Docker-required-blue)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Installation and Dependencies](#installation-and-dependencies)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [AI-Assistance](#ai-assistance)

---

## Overview

We run ROS Noetic inside Docker to simulate the Unitree Z1 arm on Ubuntu 24, which does not natively support Noetic. The workspace implements a full perception-to-control pipeline: a RealSense D435 camera in Gazebo detects a moving ArUco marker, and the Z1 arm follows it in real time using Cartesian control.

The primary use case is a robotics workshop where participants receive boilerplate ROS nodes with TODOs and must complete the vision and control pipelines.

The image uses Mesa software rendering (llvmpipe) by default — no GPU is required to run Gazebo or RViz.

---

## Key Features

- Full Gazebo simulation of the Unitree Z1 6-DOF arm with gripper
- ArUco marker detection via OpenCV and cv_bridge, published as 3D world-frame poses
- Configurable camera modes: end-effector (wrist-mounted) and fixed (static world pose)
- Animated marker with configurable motion patterns: sinusoidal, circular, figure-8, and static
- Smooth Cartesian arm tracking with low-pass filtering and workspace clamping
- Centralized YAML configuration — change marker motion, tracking gain, camera mode, and workspace limits without rebuilding
- Pre-configured RViz layout with robot model, TF tree, camera feeds, and marker pose visualization
- Software rendering baked in — works without NVIDIA drivers or GPU passthrough
- Live file sync via Docker bind mounts — edit source on the host, relaunch inside the container

---

## Installation and Dependencies

### Prerequisites

| Dependency | Version | Notes |
| --- | --- | --- |
| Docker | 24+ | Required |
| Python | 3.8 | Inside the container |
| ROS Noetic | 1.16 | Inside the container |
| X11 / `xhost` | any | Required for GUI (Gazebo, RViz) |

No ROS installation is needed on the host. Everything runs inside the container.

### Build the Docker Image [RECOMMENDED]

```bash
git clone <repo-url> ros_docker
cd ros_docker
docker build -t ros-z1 .
```

The build installs ROS Noetic, Gazebo, RViz, OpenCV with ArUco support, and compiles
`z1_controller` and `sdk_z1` binaries. First build takes 10-15 minutes.

### Optional — GPU Hardware Rendering

The image uses software rendering by default. To override to NVIDIA GPU rendering,
install `nvidia-container-toolkit` on the host:

```bash
sudo apt-get install nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Then pass `-e LIBGL_ALWAYS_SOFTWARE=0 --gpus all` to `docker run`. See [docs/DOCKER_CMDS.md](docs/DOCKER_CMDS.md) for the full command.

---

## Quick Start

**1. Allow X11 forwarding on the host:**

```bash
xhost +local:docker
```

**2. Start the container with live file sync:** [RECOMMENDED]

```bash
docker run -it --rm \
  --name z1_aruco \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd)/z1_aruco_detector:/home/rosuser/catkin_ws/src/z1_aruco_detector \
  -v $(pwd)/z1_arm_tracker:/home/rosuser/catkin_ws/src/z1_arm_tracker \
  -v $(pwd)/unitree_ros/unitree_gazebo/launch:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/launch \
  -v $(pwd)/unitree_ros/unitree_gazebo/worlds:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/worlds \
  -v $(pwd)/unitree_ros/unitree_gazebo/rviz:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/rviz \
  ros-z1 bash
```

**3. Launch the ArUco tracking simulation (Terminal 1, inside container):**

```bash
source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash
roslaunch unitree_gazebo z1_aruco_tracking.launch
```

**4. Open RViz to visualize the arm and marker (Terminal 2):**

```bash
docker exec -e DISPLAY=$DISPLAY -it ros-z1 bash -c \
  "source ~/.bashrc && \
   rviz -d ~/catkin_ws/src/unitree_ros/unitree_gazebo/rviz/z1_aruco_tracking.rviz"
```

See [docs/STARTUP.md](docs/STARTUP.md) for the full developer reference — roslaunch arguments,
configuration, architecture notes, troubleshooting, and future work.

---

## Project Structure

```txt
ros_docker/
├── Dockerfile                        # ROS Noetic image with all dependencies
├── README.md
├── docs/
│   ├── STARTUP.md                    # Full developer reference — build, run, config, architecture
│   ├── DOCKER_CMDS.md                # Docker command reference
│   ├── QUICKSTART.md                 # (legacy — superseded by STARTUP.md)
│   ├── CONTROL_GUIDE.md              # (legacy — content merged into STARTUP.md)
│   └── GAZEBO_SIM_GUIDE.md           # (legacy — content merged into STARTUP.md)
│
├── z1_aruco_detector/                # ROS package — perception pipeline
│   ├── src/
│   │   ├── aruco_detector_node.py    # Detects ArUco, publishes 3D marker pose
│   │   └── marker_mover_node.py      # Animates the ArUco marker in Gazebo
│   └── config/
│       └── aruco_tracking.yaml       # Centralized simulation configuration
│
├── z1_arm_tracker/                   # ROS package — control pipeline
│   └── src/
│       └── arm_tracker_node.py       # Sends Cartesian commands to sim_ctrl via UDP
│
├── unitree_ros/                      # Unitree ROS packages (submodule)
│   └── unitree_gazebo/
│       ├── launch/
│       │   ├── z1_aruco_tracking.launch   # Master launch: Gazebo + all nodes
│       │   └── z1.launch                  # Standard Z1 Gazebo launch
│       ├── worlds/
│       │   └── aruco_tracking.world       # World with arm, camera, marker
│       ├── models/
│       │   ├── realsense_d435/            # Gazebo RealSense D435 model
│       │   └── aruco_marker_0/            # Gazebo ArUco marker ID 0 model
│       └── rviz/
│           └── z1_aruco_tracking.rviz     # Pre-configured RViz layout
│
├── z1_controller/                    # Unitree Z1 FSM controller (C++)
│   └── build/                        # sim_ctrl binary (run from here)
│
├── sdk_z1/                           # Unitree Z1 SDK (C++)
│   └── build/                        # highcmd_basic, lowcmd_development, etc.
│
└── tests/                            # Development test scripts
    ├── test_arm_motion.py
    ├── test_follower_no_camera.py
    └── test_marker_control.py
```

---

## Architecture

```txt
  Gazebo Simulation
  ┌─────────────────────────────────────────────┐
  │  Z1 Arm  ←── joint controllers              │
  │  ArUco Marker (animated)                    │
  │  RealSense D435 camera plugin               │
  └──────────────┬──────────────────────────────┘
                 │ /camera/color/image_raw
                 ▼
        aruco_detector_node.py
        (OpenCV ArUco detection,
         TF projection to world frame)
                 │ /aruco/marker_pose (PoseStamped)
                 │ /aruco/marker_detected (Bool)
                 │ /aruco/debug_image (Image)
                 ▼
        arm_tracker_node.py
        (Cartesian proportional control,
         low-pass filter, workspace clamping)
                 │ UDP 127.0.0.1:8071
                 ▼
        sim_ctrl (SDK mode)
        (Unitree FSM — Cartesian state)
                 │ ROS joint controllers
                 ▼
          Z1 arm follows marker

  marker_mover_node.py ──► /gazebo/set_model_state
  (sinusoidal / circular / figure-8 / static)
```

### Data Flow

| Topic / Channel | Type | From | To |
| --- | --- | --- | --- |
| `/camera/color/image_raw` | `sensor_msgs/Image` | Gazebo camera plugin | aruco_detector |
| `/aruco/marker_pose` | `geometry_msgs/PoseStamped` | aruco_detector | arm_tracker |
| `/aruco/marker_detected` | `std_msgs/Bool` | aruco_detector | arm_tracker |
| `/aruco/debug_image` | `sensor_msgs/Image` | aruco_detector | image_view / RViz |
| `/gazebo/set_model_state` | `gazebo_msgs/ModelState` | marker_mover | Gazebo |
| UDP 127.0.0.1:8071 | binary | arm_tracker | sim_ctrl |

---

## Configuration

All simulation parameters load from a single file at launch time:

```txt
z1_aruco_detector/config/aruco_tracking.yaml
```

Edit this file on the host and relaunch — no rebuild required when using bind mounts.

### Camera Mode

```yaml
camera:
  mode: end_effector   # end_effector (wrist-mounted) or fixed (static world pose)
```

The launch file argument `camera_mode:=end_effector` must match `camera/mode` in the YAML.

### Marker Motion

```yaml
marker:
  motion_pattern: sinusoidal   # sinusoidal, circular, figure8, static
  center: [0.70, 0.0, 0.50]    # world frame (metres)
  amplitude_y: 0.20             # side-to-side
  amplitude_z: 0.10             # up-down
  frequency: 0.2                # Hz
```

### Arm Tracker

```yaml
arm_tracker:
  cartesian_speed: 0.1     # m/s — keep <= 0.5 for safe simulation
  proportional_gain: 2.0   # gain=2 → full speed at 0.5 m error
  smoothing_alpha: 0.10    # low-pass filter (0.0=frozen, 1.0=instant)
  fixed_x: 0.25            # fixed forward reach (metres)
  workspace:
    x: [0.20, 0.65]
    y: [-0.35, 0.35]
    z: [0.10, 0.75]
```

### roslaunch Arguments

```bash
# ArUco tracking simulation
roslaunch unitree_gazebo z1_aruco_tracking.launch \
  camera_mode:=end_effector \   # end_effector | fixed
  paused:=true \                # start Gazebo paused
  gui:=true \                   # show Gazebo window
  headless:=false \             # no rendering (fastest)
  UnitreeGripperYN:=true        # include gripper controller

# Standard Z1 simulation
roslaunch unitree_gazebo z1.launch \
  wname:=earth \                # earth | space | stairs | building_editor_models
  paused:=true \
  gui:=true \
  headless:=false \
  UnitreeGripperYN:=true
```

---

## Troubleshooting

```txt
Error: "cannot open display"
- Cause: X11 forwarding not enabled on the host
- Solution: Run "xhost +local:docker" before starting the container

Error: "roslaunch: command not found" or "package not found"
- Cause: ROS environment not sourced
- Solution: Run "source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash"

Error: arm_tracker sends commands but arm does not move
- Cause: sim_ctrl is not running, or is in keyboard mode instead of SDK mode
- Solution: Run "cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl" (no "keyboard" argument)

Error: aruco_detector node starts but /aruco/marker_detected stays false
- Cause: Camera not publishing, or marker not visible in camera frame
- Solution: Check "rostopic hz /camera/color/image_raw" — should be ~30 Hz
            Check camera_mode in YAML matches the camera_mode launch argument

Error: Gazebo opens but arm is frozen / physics paused
- Cause: Gazebo starts paused by default
- Solution: Click Play in the Gazebo GUI, or relaunch with "paused:=false"
```

---

## Gallery

### RViz — arm tracking marker in real time

![RViz ArUco tracking](assets/z1-aruco-rviz.png)

### ROS node graph

![ROS node graph](assets/rosgraph.png)

### Gazebo simulation (video)

[z1-aruco-gazebo.webm](assets/z1-aruco-gazebo.webm)

### RViz visualization (video)

[z1-aruco-rviz.webm](assets/z1-aruco-rviz.webm)

---

## AI-Assistance

Parts of this workspace were developed with the assistance of large language models
(Claude by Anthropic).

AI-generated code in this workspace controls a simulated robotic arm. Before using
any part of this code with real hardware:

- Review all motion limits and workspace bounds in `aruco_tracking.yaml`
- Validate Cartesian speed limits (`cartesian_speed`) against your physical setup
- Test incrementally at low speeds before enabling full tracking
- This code is provided for simulation and educational use — use caution when
  adapting it for real hardware applications
