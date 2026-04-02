# Quick Start — ROS Noetic Z1 Simulation

## 1. Build the Docker Image

```bash
docker build -t ros-z1 .
```

Both the ArUco tracking and standard Z1 simulations use the same image.
The default CMD auto-launches the ArUco tracking simulation on container start.
Pass `bash` to override and start manually.

---

## 2. Allow X11 Forwarding (Host)

```bash
xhost +local:docker
```

---

## 3. Run the Container

### Auto-launch ArUco tracking on start

```bash
docker run -it --rm \
  --name z1_aruco \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1
```

### Manual launch — shell only (recommended for development)

Override the CMD with `bash` to start a shell and launch nodes manually.

```bash
docker run -it --rm \
  --name z1_aruco \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1 bash
```

### Live file sync (recommended for development)

Mounts local source files directly — edits on the host are instantly reflected
inside the container without rebuilding.

```bash
docker run -it --rm \
  --name z1_aruco \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /home/sense/ros_docker/z1_aruco_detector:/home/rosuser/catkin_ws/src/z1_aruco_detector \
  -v /home/sense/ros_docker/z1_arm_tracker:/home/rosuser/catkin_ws/src/z1_arm_tracker \
  -v /home/sense/ros_docker/unitree_ros/unitree_gazebo/launch:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/launch \
  -v /home/sense/ros_docker/unitree_ros/unitree_gazebo/worlds:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/worlds \
  -v /home/sense/ros_docker/unitree_ros/unitree_gazebo/rviz:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/rviz \
  ros-z1 bash
```

---

## 4. Rendering

The image uses Mesa software rendering (llvmpipe) by default.
`LIBGL_ALWAYS_SOFTWARE=1` and `MESA_GL_VERSION_OVERRIDE=3.3` are baked into the
Dockerfile. No GPU setup is needed — Gazebo and RViz work out of the box.

**Why software rendering:** The Intel Meteor Lake GPU (0x7d67) is too new for
Mesa 21 in Ubuntu 20.04, and NVIDIA GLX rejects indirect X11 connections from
Docker. llvmpipe provides stable OpenGL 3.1 for both Gazebo and RViz.

### Optional — Override to GPU rendering at runtime

Override the baked-in env vars if you want to attempt hardware rendering.
This is not guaranteed to work and is not the tested path.

```bash
docker run -it --rm \
  --name z1_aruco \
  --gpus all \
  --device /dev/dri:/dev/dri \
  -e DISPLAY=$DISPLAY \
  -e LIBGL_ALWAYS_SOFTWARE=0 \
  -e NVIDIA_DRIVER_CAPABILITIES=graphics,display,utility \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1 bash
```

> The nvidia-container-toolkit must be installed on the host for `--gpus all` to work.
> Install: `sudo apt-get install nvidia-container-toolkit && sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`

---

## 5. roslaunch Reference

### z1_aruco_tracking.launch

Launches the ArUco tracking simulation (Gazebo + ArUco detector + marker mover + arm tracker).

```bash
roslaunch unitree_gazebo z1_aruco_tracking.launch [arg:=value ...]
```

| Argument | Default | Options | Description |
| --- | --- | --- | --- |
| `camera_mode` | `end_effector` | `end_effector`, `fixed` | Camera attached to wrist (URDF) or static in world (Gazebo model) |
| `paused` | `true` | `true`, `false` | Start Gazebo paused — press Play in GUI to start physics |
| `gui` | `true` | `true`, `false` | Show the Gazebo GUI window |
| `headless` | `false` | `true`, `false` | No rendering — faster, overrides `gui:=true` |
| `UnitreeGripperYN` | `true` | `true`, `false` | Include gripper controller |
| `debug` | `false` | `true`, `false` | Enable Gazebo debug output |

```bash
# Fixed camera, start unpaused, no GUI
roslaunch unitree_gazebo z1_aruco_tracking.launch \
  camera_mode:=fixed \
  paused:=false \
  gui:=false

# End-effector camera, headless (no Gazebo window, fastest)
roslaunch unitree_gazebo z1_aruco_tracking.launch \
  camera_mode:=end_effector \
  headless:=true

# End-effector camera, start unpaused, GUI visible
roslaunch unitree_gazebo z1_aruco_tracking.launch \
  paused:=false \
  gui:=true
```

> For marker motion, arm tracking speed, camera parameters, and workspace limits,
> edit `z1_aruco_detector/config/aruco_tracking.yaml` on the host and relaunch.
> Changes to the mounted config file take effect on the next `roslaunch`.

### z1.launch

Launches the standard Z1 simulation (Gazebo only, no ArUco).

```bash
roslaunch unitree_gazebo z1.launch [arg:=value ...]
```

| Argument | Default | Options | Description |
| --- | --- | --- | --- |
| `wname` | `earth` | `earth`, `space`, `stairs`, `building_editor_models` | Gazebo world file |
| `paused` | `true` | `true`, `false` | Start Gazebo paused |
| `gui` | `true` | `true`, `false` | Show the Gazebo GUI window |
| `headless` | `false` | `true`, `false` | No rendering |
| `UnitreeGripperYN` | `true` | `true`, `false` | Include gripper controller |
| `user_debug` | `false` | `true`, `false` | Enable FSM debug output |
| `debug` | `false` | `true`, `false` | Enable Gazebo debug output |

```bash
# Launch in stairs world, unpaused
roslaunch unitree_gazebo z1.launch wname:=stairs paused:=false

# Headless, no gripper
roslaunch unitree_gazebo z1.launch headless:=true UnitreeGripperYN:=false
```

---

## 6. Multi-Terminal Workflow — ArUco Simulation

The container must be running with `--name z1_aruco` before using `docker exec`.
Use multiple host terminals or tmux panes inside the container.

### Terminal 1 — Launch Gazebo + ArUco tracking

```bash
source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash
roslaunch unitree_gazebo z1_aruco_tracking.launch
```

### Terminal 2 — Camera feed with ArUco overlay

```bash
docker exec -e DISPLAY=$DISPLAY -it z1_aruco bash -c \
  "source /opt/ros/noetic/setup.bash && \
   source ~/catkin_ws/devel/setup.bash && \
   rosrun image_view image_view image:=/aruco/debug_image"
```

Raw camera feed (no overlay):

```bash
docker exec -e DISPLAY=$DISPLAY -it z1_aruco bash -c \
  "source /opt/ros/noetic/setup.bash && \
   rosrun image_view image_view image:=/camera/color/image_raw"
```

### Terminal 3 — RViz

```bash
docker exec -e DISPLAY=$DISPLAY -it z1_aruco bash -c \
  "source /opt/ros/noetic/setup.bash && \
   source ~/catkin_ws/devel/setup.bash && \
   rviz -d ~/catkin_ws/src/unitree_ros/unitree_gazebo/rviz/z1_aruco_tracking.rviz"
```

Pre-configured displays:

- Grid — ground plane reference
- RobotModel — Z1 arm (Fixed Frame: `world`)
- TF — all frames including `camera_color_optical_frame` and `link06`
- Camera (ArUco overlay) — `/aruco/debug_image` with detected marker outlined
- Camera (raw) — `/camera/color/image_raw` (disabled by default, enable in RViz)
- Camera Frame — axes at the camera optical frame position
- Marker Pose — `/aruco/marker_pose` as a red arrow in world frame

### Terminal 4 — Z1 controller (sim_ctrl)

```bash
docker exec -it z1_aruco bash -c \
  "source /opt/ros/noetic/setup.bash && \
   source ~/catkin_ws/devel/setup.bash && \
   cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard"
```

### Terminal 5 — Monitor detection and tracking

```bash
docker exec -it z1_aruco bash
```

Then inside:

```bash
# Is the marker being detected?
rostopic echo /aruco/marker_detected

# Where is the marker in world frame?
rostopic echo /aruco/marker_pose

# Check all active nodes
rosnode list

# Check topic publish rates
rostopic hz /camera/color/image_raw
rostopic hz /aruco/marker_pose
```

---

## 7. Verify the Environment

```bash
# ROS is sourced
echo $ROS_PACKAGE_PATH

# Unitree packages are found
rospack find z1_description
rospack find unitree_gazebo
rospack find unitree_legged_msgs

# Z1 binaries exist
ls ~/z1_controller/build/z1_ctrl
ls ~/sdk_z1/build/
```

---

## 8. Standard Z1 Simulation (no ArUco)

```bash
# Terminal 1 — Launch Gazebo
source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash
roslaunch unitree_gazebo z1.launch

# Terminal 2 — Start controller
docker exec -it z1_aruco bash -c \
  "cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard"

# Terminal 3 — Run an SDK example
docker exec -it z1_aruco bash -c "~/sdk_z1/build/highcmd_basic"
```

---

## 9. Cleanup

```bash
# Force stop and remove container
docker rm -f z1_aruco

# Revoke X11 access
xhost -local:docker
```
