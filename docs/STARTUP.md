# Startup & Developer Reference — ROS Noetic Z1 ArUco Tracking

This document covers everything needed to build, run, and iterate on the simulation.
It assumes familiarity with ROS, Docker, and the repo structure. See `README.md` for
the high-level overview.

---

## 1. Build the Image

```bash
docker build -t ros-z1 .
```

**When to rebuild** — required when changing:
- `Dockerfile`
- URDF / xacro files (`z1_description/xacro/`)
- C++ sources (`z1_controller/`, `sdk_z1/`)

**When `docker cp` is enough** — no rebuild needed for:
- Python nodes (`aruco_detector_node.py`, `arm_tracker_node.py`, `marker_mover_node.py`)
- YAML config (`aruco_tracking.yaml`)
- Launch files (`.launch`) and RViz configs (`.rviz`)

```bash
# Hot-reload a Python node or config without rebuilding
docker cp z1_aruco_detector/src/aruco_detector_node.py \
  ros-z1:/home/rosuser/catkin_ws/src/z1_aruco_detector/src/
docker cp z1_aruco_detector/config/aruco_tracking.yaml \
  ros-z1:/home/rosuser/catkin_ws/src/z1_aruco_detector/config/
# Then restart the affected node inside the container:
# rosnode kill /aruco_detector && rosrun z1_aruco_detector aruco_detector_node.py
```

---

## 2. X11 Forwarding (Host — run once per session)

```bash
xhost +local:docker

# Revoke when done
xhost -local:docker
```

---

## 3. ArUco Tracking Simulation

This is the primary simulation. The container CMD auto-starts
`roslaunch unitree_gazebo z1_aruco_tracking.launch` on entry.

### 3.1 Start the container

```bash
# Auto-launch (production / demo)
docker run -it --rm \
  --name ros-z1 \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1
```

```bash
# Shell only — launch nodes manually (development)
docker run -it --rm \
  --name ros-z1 \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1 bash
```

```bash
# Bind-mount source files — host edits reflected immediately (fastest iteration)
docker run -it --rm \
  --name ros-z1 \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd)/z1_aruco_detector:/home/rosuser/catkin_ws/src/z1_aruco_detector \
  -v $(pwd)/z1_arm_tracker:/home/rosuser/catkin_ws/src/z1_arm_tracker \
  -v $(pwd)/unitree_ros/unitree_gazebo/launch:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/launch \
  -v $(pwd)/unitree_ros/unitree_gazebo/worlds:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/worlds \
  -v $(pwd)/unitree_ros/unitree_gazebo/rviz:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/rviz \
  ros-z1 bash
```

### 3.2 What auto-starts

When the container starts with the default CMD, the following happens in a single
`roslaunch`:

| Node | Package | Role |
| --- | --- | --- |
| Gazebo | `unitree_gazebo` | Physics sim, joint controllers, camera plugin |
| `robot_state_publisher` | ROS | Publishes TF for the full kinematic chain incl. camera |
| `aruco_detector_node` | `z1_aruco_detector` | Detects marker in camera image, publishes world-frame pose |
| `marker_mover_node` | `z1_aruco_detector` | Moves the ArUco marker in Gazebo along a configurable path |
| `arm_tracker_node` | `z1_arm_tracker` | Solves IK and sends MotorCmd to joint controllers |

No `sim_ctrl` or UDP is involved. The arm tracker publishes directly to
`/z1_gazebo/JointXX_controller/command`.

### 3.3 Unpause Gazebo

The simulation starts paused by default (`paused:=true`). Either click Play in the
Gazebo GUI, or from a second terminal:

```bash
docker exec -it ros-z1 bash -c \
  "source ~/.bashrc && rosservice call /gazebo/unpause_physics"
```

### 3.4 roslaunch arguments

```bash
roslaunch unitree_gazebo z1_aruco_tracking.launch [arg:=value ...]
```

| Argument | Default | Options | Description |
| --- | --- | --- | --- |
| `camera_mode` | `end_effector` | `end_effector`, `fixed` | Wrist camera (URDF, moves with arm) or static world camera |
| `paused` | `true` | `true`, `false` | Start physics paused |
| `gui` | `true` | `true`, `false` | Show Gazebo GUI |
| `headless` | `false` | `true`, `false` | No rendering — fastest, overrides `gui:=true` |
| `UnitreeGripperYN` | `true` | `true`, `false` | Include gripper controller |

```bash
# Headless, unpaused — fastest, no GUI windows
roslaunch unitree_gazebo z1_aruco_tracking.launch headless:=true paused:=false

# Fixed camera mode, GUI visible
roslaunch unitree_gazebo z1_aruco_tracking.launch camera_mode:=fixed paused:=false
```

### 3.5 Configuration

All simulation behaviour is controlled by a single YAML file:

```
z1_aruco_detector/config/aruco_tracking.yaml
```

Loaded onto the ROS parameter server at launch. Key parameters:

| Section | Parameter | Effect |
| --- | --- | --- |
| `marker` | `motion_pattern` | `sinusoidal`, `circular`, `figure8`, `square`, `static` |
| `marker` | `center` | World-frame XYZ of the motion path centre |
| `marker` | `amplitude_y/z` | Side-to-side and up-down range (metres) |
| `marker` | `frequency` | Speed of motion (Hz) |
| `arm_tracker` | `fixed_x` | Fixed forward reach held constant during 2D tracking |
| `arm_tracker` | `smoothing_alpha` | Low-pass filter: `0.0`=frozen, `1.0`=instant snap. Start at `0.05`–`0.10` |
| `arm_tracker` | `joint_kp/kd` | PD gains for MotorCmd — `kp=150, kd=3` are stable defaults |
| `arm_tracker` | `workspace` | Cartesian clamping limits (metres, world frame) |
| `camera` | `mode` | Must match `camera_mode` roslaunch arg |

Changes take effect on next launch. To hot-reload without rebuilding, use `docker cp`
and restart the affected node.

### 3.6 Optional tools

**RViz** (pre-configured layout — robot model, TF, marker pose, camera feed):

```bash
docker exec -e DISPLAY=$DISPLAY -it ros-z1 bash -c \
  "source ~/.bashrc && \
   rviz -d ~/catkin_ws/src/unitree_ros/unitree_gazebo/rviz/z1_aruco_tracking.rviz"
```

**Camera feed with ArUco overlay:**

```bash
docker exec -e DISPLAY=$DISPLAY -it ros-z1 bash -c \
  "source ~/.bashrc && \
   rosrun image_view image_view image:=/aruco/debug_image"
```

**Monitoring topics:**

```bash
docker exec -it ros-z1 bash -c "source ~/.bashrc && rostopic echo /aruco/marker_detected"
docker exec -it ros-z1 bash -c "source ~/.bashrc && rostopic echo /aruco/marker_pose"
docker exec -it ros-z1 bash -c "source ~/.bashrc && rostopic hz /aruco/marker_pose"
docker exec -it ros-z1 bash -c "source ~/.bashrc && rosnode list"
```

---

## 4. Rendering

The image uses Mesa software rendering by default. Both `LIBGL_ALWAYS_SOFTWARE=1`
and `MESA_GL_VERSION_OVERRIDE=3.3` are baked into the Dockerfile via `ENV`.

**Why:** The Intel Meteor Lake GPU (0x7d67) is not supported by Mesa 21 in the
Ubuntu 20.04 base image, and NVIDIA GLX rejects indirect X11 connections from Docker.
Mesa llvmpipe provides stable OpenGL 3.1 for both Gazebo and RViz without any host
GPU configuration.

To attempt hardware rendering, override at runtime:

```bash
docker run -it --rm \
  --name ros-z1 \
  --gpus all \
  --device /dev/dri:/dev/dri \
  -e DISPLAY=$DISPLAY \
  -e LIBGL_ALWAYS_SOFTWARE=0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1 bash
```

Requires `nvidia-container-toolkit` on the host:
```bash
sudo apt-get install nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
# Docker 26+ also requires:
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
```

---

## 5. Architecture

```
Gazebo camera plugin
      │ /camera/color/image_raw
      ▼
aruco_detector_node
      │ /aruco/marker_pose      (PoseStamped, world frame)
      │ /aruco/marker_detected  (Bool)
      │ /aruco/debug_image      (Image)
      ▼
arm_tracker_node
      │ IK via Z1Model (SDK model, no UDP)
      │ /z1_gazebo/Joint01..06_controller/command  (MotorCmd)
      ▼
Gazebo joint controllers
```

**Key design decisions:**

- **No sim_ctrl / no UDP.** `arm_tracker_node` instantiates `ArmInterface(hasGripper=True)`
  without calling `loopOn()` — the SDK model and IK solver are used directly, no socket
  is opened. Joint commands go via ROS topics only.

- **2D tracking.** The arm holds a fixed X depth (`fixed_x` param) and follows only
  the marker's Y (lateral) and Z (vertical). This keeps the marker in the camera FOV.

- **tvec axis remapping.** `camera_color_optical_frame` has `rpy=0,0,0` relative to
  `link06` (X=forward, Y=left, Z=up). OpenCV's tvec uses Z=depth, X=right, Y=down.
  The detector remaps: `pose.x = tvec[2]`, `pose.y = -tvec[0]`, `pose.z = -tvec[1]`.

- **IK warm-start.** The arm subscribes to `/z1_gazebo/joint_states` and passes the
  current joint angles as the initial guess to `inverseKinematics()`, which improves
  convergence and prevents large joint jumps.

**Key topics:**

| Topic | Type | Producer → Consumer |
| --- | --- | --- |
| `/camera/color/image_raw` | `sensor_msgs/Image` | Gazebo → aruco_detector |
| `/aruco/marker_pose` | `geometry_msgs/PoseStamped` | aruco_detector → arm_tracker |
| `/aruco/marker_detected` | `std_msgs/Bool` | aruco_detector → arm_tracker |
| `/z1_gazebo/joint_states` | `sensor_msgs/JointState` | Gazebo → arm_tracker (IK warm-start) |
| `/z1_gazebo/JointXX_controller/command` | `unitree_legged_msgs/MotorCmd` | arm_tracker → Gazebo |

---

## 6. Troubleshooting

**arm_tracker logs `DRY RUN` — not sending commands**

The `unitree_arm_interface` Python binding failed to import. Most likely cause is a
missing `LD_LIBRARY_PATH`. `ENV LD_LIBRARY_PATH=/home/rosuser/sdk_z1/lib` is set in
the Dockerfile, but if running an old image:

```bash
export LD_LIBRARY_PATH=/home/rosuser/sdk_z1/lib:$LD_LIBRARY_PATH
# Verify:
python3 -c "import sys; sys.path.insert(0, '/home/rosuser/sdk_z1/lib'); import unitree_arm_interface; print('OK')"
```

**IK failures — `IK failed for target x:... y:... z:...`**

The requested Cartesian position is outside the Z1's reachable workspace. Check:
- `fixed_x` — values above ~0.55m at non-zero Y/Z can exceed reach. Try `0.25`–`0.40`.
- `workspace.z` max — if the marker Z is being clamped to the ceiling (`0.75`), lower the
  marker `center` Z or raise the clamp value.
- The IK uses `checkWorkspace=True` — it will refuse positions near joint limits.

**Marker world-frame Z is inflated (reads ~0.83m instead of ~0.50m)**

This means the camera axes are misaligned with the TF frame orientation. The tvec axis
remapping in `aruco_detector_node.py` must match the actual `rpy` of
`camera_color_optical_frame` in the URDF. With `rpy="0 0 0"`, the correct remapping
is `pose.x = tvec[2]`, `pose.y = -tvec[0]`, `pose.z = -tvec[1]`.

**`tf_echo world camera_color_optical_frame` fails with "not part of same tree"**

Intermittent timing issue — `robot_state_publisher` hasn't yet published the full chain.
Retry after a few seconds. If persistent, check that `robot_state_publisher` is running
and that `EndEffectorCamera:=true` was passed to xacro (controlled by `camera_mode`).

**Arm moves but loses the marker immediately**

- Marker is too close — increase `marker.center[0]` (X) so it stays further from the arm.
- Tracking is too fast — lower `arm_tracker.smoothing_alpha` (e.g. `0.05`).
- Workspace clamp too tight — the arm may be hitting a Y/Z limit and stopping.

**`unitree_legged_msgs` not found at Python import**

The catkin workspace must be sourced. Inside the container: `source ~/.bashrc`.
The `.bashrc` sources both `/opt/ros/noetic/setup.bash` and `~/catkin_ws/devel/setup.bash`.

---

## 7. Future Work

### Basic Z1 Gazebo + sim_ctrl (currently functional)

A second simulation mode exists without ArUco tracking — useful for testing the Z1 arm
independently, running SDK examples, or developing new controllers.

```bash
# Terminal 1 — inside the container
source ~/.bashrc
roslaunch unitree_gazebo z1.launch

# Terminal 2 — keyboard control
docker exec -it ros-z1 bash -c \
  "cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard"

# Terminal 2 — SDK mode (for programmatic control examples)
docker exec -it ros-z1 bash -c \
  "cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl"
# Then in Terminal 3:
docker exec -it ros-z1 bash -c "~/sdk_z1/build/highcmd_basic"
```

`sim_ctrl` keyboard FSM states: `` ` ``=start, `1`=passive, `2`=joint, `3`=cartesian,
`4`=MoveJ, `5`=MoveL, `6`=MoveC. Axis keys: `q/a`, `w/s`, `e/d`, `r/f`, `t/g`, `y/h`.

SDK examples: `highcmd_basic`, `highcmd_development`, `lowcmd_development` — all
communicate with `sim_ctrl` over UDP on `127.0.0.1:8071/8072`.

This workflow is not integrated into the ArUco tracking launch and is not part of the
workshop demo. It remains available for controller development.

### Hardware rendering

True GPU acceleration would require a newer base image (Ubuntu 22.04 + Mesa 22+) to
support Intel Meteor Lake, or an NVIDIA EGL setup to bypass X11 indirect rendering.
The current llvmpipe path is stable for simulation but slow for complex worlds.

### Real hardware deployment

Deploying to the physical Z1 arm requires:
- Switching to `unitree_ros_to_real` for the ROS ↔ UDP bridge
- Calling `arm.loopOn()` in `arm_tracker_node.py` to open the UDP connection
- Replacing the Gazebo camera with a real RealSense D435 and its ROS driver
- Tuning `smoothing_alpha` and `joint_kp/kd` for real hardware response characteristics
