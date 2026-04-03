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
docker cp z1_aruco/config/aruco_tracking.yaml \
  ros-z1:/home/rosuser/catkin_ws/src/z1_aruco/config/
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
`roslaunch z1_aruco z1_aruco_tracking.launch` on entry.

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
  -v $(pwd)/z1_aruco:/home/rosuser/catkin_ws/src/z1_aruco \
  ros-z1 bash
```

### 3.2 What auto-starts

When the container starts with the default CMD, the following happens in a single
`roslaunch`:

| Node | Package | Role |
| --- | --- | --- |
| Gazebo | `z1_aruco` | Physics sim, joint controllers, camera plugin |
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
roslaunch z1_aruco z1_aruco_tracking.launch [arg:=value ...]
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
roslaunch z1_aruco z1_aruco_tracking.launch headless:=true paused:=false

# Fixed camera mode, GUI visible
roslaunch z1_aruco z1_aruco_tracking.launch camera_mode:=fixed paused:=false
```

### 3.5 Configuration

All simulation behaviour is controlled by a single YAML file:

```txt
z1_aruco/config/aruco_tracking.yaml
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
   rviz -d ~/catkin_ws/src/z1_aruco/rviz/z1_aruco_tracking.rviz"
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

## 4. Real Camera Tracking (D435 + Gazebo)

This workflow replaces the simulated camera with a physical RealSense D435 connected
to the host laptop. Gazebo runs the arm and joint controllers as normal. The D435
driver publishes to the same `/camera/color/image_raw` and `/camera/color/camera_info`
topics the detector already expects — nothing else changes.

The camera TF (`camera_color_optical_frame` → `link06`) is still broadcast by
`robot_state_publisher` via the URDF, so the arm "believes" the camera is on its
wrist. The Gazebo sensor plugin is suppressed (`CameraPlugin:=false`) so it does not
conflict with the real camera stream.

### 4.1 Host prerequisites (run once)

The Intel RealSense apt repo does not support Ubuntu 24 (Noble). Install only the
udev rules directly from the upstream source:

```bash
sudo curl -fsSL https://raw.githubusercontent.com/IntelRealSense/librealsense/master/config/99-realsense-libusb.rules \
  -o /etc/udev/rules.d/99-realsense-libusb.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Unplug and replug the D435 after reloading rules. Verify the camera is visible on the host:

```bash
lsusb | grep RealSense
# expected: Bus 00X Device 00X: ID 8086:0b07 Intel Corp. RealSense D435
```

`rs-enumerate-devices` is not available on Ubuntu 24 without building librealsense from
source. Use `lsusb` to confirm the device is present before starting the container.

### 4.2 Build and start the container

```bash
docker build -t ros-z1-aruco-real .
```

Find the USB bus the D435 is on:

```bash
lsusb | grep RealSense
# example: Bus 004 Device 003: ID 8086:0b07 Intel Corp. RealSense D435
```

Start the container passing only that bus (bus 004 in this example):

```bash
docker run -it --rm \
  --name ros-z1-real \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  --device /dev/bus/usb/004:/dev/bus/usb/004 \
  ros-z1-aruco-real bash
```

Using a specific bus (`/dev/bus/usb/004`) rather than all buses is cleaner and avoids
unnecessary device exposure. If the bus number changes after a replug, recheck with
`lsusb` and update the `--device` path.

If the driver logs `RS2_USB_STATUS_ACCESS`, the udev rules have not taken effect —
unplug and replug the D435 after reloading rules. As a fallback for workshop use:

```bash
docker run -it --rm \
  --name ros-z1-real \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  --privileged \
  ros-z1-aruco-real bash
```

### 4.3 Launch

```bash
source ~/.bashrc
roslaunch z1_aruco z1_real_camera_tracking.launch
```

Unpause Gazebo:

```bash
rosservice call /gazebo/unpause_physics
```

Note: `z1_real_camera_tracking.launch` sets `use_sim_time:=false`. This is required
because the D435 driver timestamps images in wall clock time, while Gazebo sim time
starts near zero. With `use_sim_time:=true`, the TF lookup for the camera frame would
fail with "Lookup would require extrapolation into the future".

### 4.4 roslaunch arguments

| Argument | Default | Description |
| --- | --- | --- |
| `realsense_serial` | `""` | D435 serial number — leave empty for first connected device |
| `paused` | `true` | Start Gazebo paused |
| `gui` | `true` | Show Gazebo GUI |
| `headless` | `false` | No rendering |
| `UnitreeGripperYN` | `true` | Include gripper controller |

### 4.5 Marker setup

Use a printed DICT_4X4_50 marker ID 0 at `marker_size: 0.15` m (matches config default).
Hold or mount the marker in front of the D435. The arm will track its Y and Z
in the camera frame, using the same IK and low-pass filter as the simulation.

---

## 6. Rendering

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

## 7. Architecture

```txt
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

## 8. Troubleshooting

**arm_tracker logs `DRY RUN` — not sending commands**

The `unitree_arm_interface` Python binding failed to import. Most likely cause is a
missing `LD_LIBRARY_PATH`. `ENV LD_LIBRARY_PATH=/home/rosuser/sdk_z1/lib` is set in
the Dockerfile, but if running an old image:

```bash
export LD_LIBRARY_PATH=/home/rosuser/sdk_z1/lib:$LD_LIBRARY_PATH
# Verify:
python3 -c "import sys; sys.path.insert(0, '/home/rosuser/sdk_z1/lib'); import unitree_arm_interface; print('OK')"
```

### IK failures — `IK failed for target x:... y:... z:...`

The requested Cartesian position is outside the Z1's reachable workspace. Check:

- `fixed_x` — values above ~0.55m at non-zero Y/Z can exceed reach. Try `0.25`–`0.40`.
- `workspace.z` max — if the marker Z is being clamped to the ceiling (`0.75`), lower the
  marker `center` Z or raise the clamp value.
- The IK uses `checkWorkspace=True` — it will refuse positions near joint limits.

### Marker world-frame Z is inflated (reads ~0.83m instead of ~0.50m)

This means the camera axes are misaligned with the TF frame orientation. The tvec axis
remapping in `aruco_detector_node.py` must match the actual `rpy` of
`camera_color_optical_frame` in the URDF. With `rpy="0 0 0"`, the correct remapping
is `pose.x = tvec[2]`, `pose.y = -tvec[0]`, `pose.z = -tvec[1]`.

### Marker pose scale is wrong — motion in RViz is tiny, arm does not respond

**Cause:** `aruco/marker_size` in `aruco_tracking.yaml` does not match the physical size
(or the Gazebo model size). OpenCV multiplies all `tvec` distances by `marker_size`, so
a mismatch compresses the entire pose estimate by the ratio `yaml_size / actual_size`.

Example: model is 0.15 m but YAML says 0.05 → every distance is reported as 1/3 of
reality → marker appears 3× closer, lateral motion is 3× smaller, arm target falls
inside or outside the workspace in unexpected ways.

**Fix:** keep `aruco/marker_size` in the YAML, the Gazebo `model.sdf` box dimensions,
and the physical printed marker all at the **same value**. Currently the project uses
`0.05 m` everywhere. Check with:

```bash
# Inside the container — what is the node actually using?
rosparam get /aruco/marker_size
```

If it still shows 0.15, the hot-reload of the YAML did not take effect — repeat the
`docker cp` and node restart below.

### Marker not detected with small (50 mm) markers

OpenCV's default `minMarkerPerimeterRate` (0.03) can reject small markers at moderate
distances — the marker's projected perimeter falls below 3 % of the image perimeter.

**Step 1 — verify the param server has the new values** (after `docker cp` + node restart):

```bash
rosparam get /aruco/min_marker_perimeter_rate   # should be 0.02, not 0.03
rosparam get /aruco/marker_size                 # should match your printed marker
```

If these still show defaults, the YAML was not loaded from the updated file. Confirm the
`docker cp` destination path matches exactly what the launch file loads.

**Step 2 — watch the debug image:**

```bash
z1_camera   # alias for rosrun image_view image_view image:=/aruco/debug_image
```

If no green outline ever appears, the detector is rejecting the marker before pose estimation.

**Fix:** lower `min_marker_perimeter_rate` in `aruco_tracking.yaml`:

```yaml
aruco:
  marker_size: 0.05          # physical size in metres — must be exact
  min_marker_perimeter_rate: 0.02   # 0.02 works reliably for 50 mm up to ~1.0 m
  error_correction_rate: 0.6        # raise to 0.8 if marker is blurry or poorly printed
```

Hot-reload without rebuilding:

```bash
docker cp z1_aruco/config/aruco_tracking.yaml \
  ros-z1-real:/home/rosuser/catkin_ws/src/z1_aruco/config/aruco_tracking.yaml
# restart the node inside the container:
rosnode kill /aruco_detector
rosrun z1_aruco_detector aruco_detector_node.py
```

Detection range reference for a 50 mm marker at 640×480 / 69° FOV:

| Distance | Approx. marker width (px) | Detectable (default 0.03) | Detectable (0.02) |
| --- | --- | --- | --- |
| 0.5 m | ~45 px | yes | yes |
| 0.7 m | ~32 px | yes | yes |
| 1.0 m | ~22 px | marginal | yes |
| 1.5 m | ~15 px | no | marginal |

If detection is still unreliable above 1.0 m, reduce `min_marker_perimeter_rate` further
to 0.01 and ensure the marker is printed at high contrast on matte paper (glossy causes
specular reflections that confuse the adaptive threshold).

### `tf_echo world camera_color_optical_frame` fails with "not part of same tree"

Intermittent timing issue — `robot_state_publisher` hasn't yet published the full chain.
Retry after a few seconds. If persistent, check that `robot_state_publisher` is running
and that `EndEffectorCamera:=true` was passed to xacro (controlled by `camera_mode`).

### Arm moves but loses the marker immediately

- Marker is too close — increase `marker.center[0]` (X) so it stays further from the arm.
- Tracking is too fast — lower `arm_tracker.smoothing_alpha` (e.g. `0.05`).
- Workspace clamp too tight — the arm may be hitting a Y/Z limit and stopping.

### `unitree_legged_msgs` not found at Python import

The catkin workspace must be sourced. Inside the container: `source ~/.bashrc`.
The `.bashrc` sources both `/opt/ros/noetic/setup.bash` and `~/catkin_ws/devel/setup.bash`.

### TF error: "Lookup would require extrapolation into the future" (real camera mode)

Caused by `use_sim_time:=true` mixed with real camera wall-clock timestamps. The D435
driver stamps images at ~1.7 billion seconds (Unix epoch), while Gazebo sim time starts
near zero. The TF lookup for `camera_color_optical_frame` then asks for a timestamp far
in the future relative to the sim clock. `z1_real_camera_tracking.launch` sets
`use_sim_time:=false` to prevent this. If the error appears, confirm you are using the
correct launch file and not `z1_aruco_tracking.launch`.

### D435 not found or `RS2_USB_STATUS_ACCESS` in real camera mode

The container cannot open the USB device. Steps to resolve:

1. Confirm the camera is visible on the host: `lsusb | grep RealSense`
2. Install udev rules on the host and unplug/replug the D435 (see section 4.1)
3. Start the container with `--device /dev/bus/usb:/dev/bus/usb`
4. If still failing on Ubuntu 24, use `--privileged` as a fallback

---

## 9. Future Work

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
