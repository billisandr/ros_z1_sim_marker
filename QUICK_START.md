# Quick Start — ROS Noetic Z1 Simulation

## 1. Build the Docker Image

```bash
# Standard Z1 simulation
docker build -t ros-z1 .

# ArUco tracking simulation
docker build -t ros-z1-aruco .
```

---

## 2. Allow X11 Forwarding (Host)

```bash
xhost +local:docker
```

---

## 3. Run the Container

### Standard Z1 simulation

```bash
docker run -it --rm \
  --name z1_sim \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1
```

### ArUco simulation — auto-launch on start

```bash
docker run -it --rm \
  --name z1_aruco \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1-aruco
```

### ArUco simulation — live file sync (recommended for development)

Mounts local source files directly — edits on the host are instantly reflected
inside the container without rebuilding or copying files.

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
  ros-z1-aruco bash
```

---

## 4. GPU / Rendering (required for RViz)

RViz requires OpenGL 3.1+. Without GPU passthrough it falls back to slow software
rendering. The NVIDIA container toolkit is required to pass the GPU into the container.

### Step 1 — Install nvidia-container-toolkit (host, once)

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit

# Configure Docker runtime and generate CDI device specs (required on Docker 26+)
sudo nvidia-ctk runtime configure --runtime=docker
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
sudo systemctl restart docker
```

Verify:

```bash
docker run --rm --gpus all ubuntu nvidia-smi
```

### Step 2 — Run the container with GPU access

Replace the standard `docker run` with:

```bash
docker run -it --rm \
  --name z1_aruco \
  --gpus all \
  --device /dev/dri:/dev/dri \
  -e DISPLAY=$DISPLAY \
  -e NVIDIA_DRIVER_CAPABILITIES=graphics,display,utility \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /home/sense/ros_docker/z1_aruco_detector:/home/rosuser/catkin_ws/src/z1_aruco_detector \
  -v /home/sense/ros_docker/z1_arm_tracker:/home/rosuser/catkin_ws/src/z1_arm_tracker \
  -v /home/sense/ros_docker/unitree_ros/unitree_gazebo/launch:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/launch \
  -v /home/sense/ros_docker/unitree_ros/unitree_gazebo/worlds:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/worlds \
  -v /home/sense/ros_docker/unitree_ros/unitree_gazebo/rviz:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/rviz \
  ros-z1-aruco bash
```

### Fallback — Software rendering (no GPU needed)

If nvidia-container-toolkit is not available, force Mesa software rendering:

```bash
docker run -it --rm \
  --name z1_aruco \
  -e DISPLAY=$DISPLAY \
  -e LIBGL_ALWAYS_SOFTWARE=1 \
  -e MESA_GL_VERSION_OVERRIDE=3.3 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1-aruco bash
```

---

## 5. Multi-Terminal Workflow (ArUco Simulation)

Use multiple host terminals or tmux panes — the container must be running with
`--name z1_aruco` before using `docker exec`.

---

### Terminal 1 — Launch Gazebo simulation

**Default launch (end_effector camera, sinusoidal marker):**

```bash
source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash
roslaunch unitree_gazebo z1_aruco_tracking.launch
```

**With launch arguments (override config defaults):**

```bash
# Fixed camera, Gazebo starts unpaused, no GUI
roslaunch unitree_gazebo z1_aruco_tracking.launch \
  camera_mode:=fixed \
  paused:=false \
  gui:=true

# End-effector camera, headless (no Gazebo window)
roslaunch unitree_gazebo z1_aruco_tracking.launch \
  camera_mode:=end_effector \
  headless:=true \
  gui:=false
```

> To change marker motion, tracking speed, workspace limits etc. edit
> `z1_aruco_detector/config/aruco_tracking.yaml` on the host and relaunch.

---

### Terminal 2 — View camera feed (with ArUco overlay)

```bash
docker exec -e DISPLAY=$DISPLAY -it z1_aruco bash -c \
  "source /opt/ros/noetic/setup.bash && \
   source ~/catkin_ws/devel/setup.bash && \
   rosrun image_view image_view image:=/aruco/debug_image"
```

**Or view the raw camera feed (no overlay):**

```bash
docker exec -e DISPLAY=$DISPLAY -it z1_aruco bash -c \
  "source /opt/ros/noetic/setup.bash && \
   rosrun image_view image_view image:=/camera/color/image_raw"
```

---

### Terminal 3 — RViz (visualise arm, TF, camera frame)

```bash
docker exec -e DISPLAY=$DISPLAY -it z1_aruco bash -c \
  "source /opt/ros/noetic/setup.bash && \
   source ~/catkin_ws/devel/setup.bash && \
   rviz -d ~/catkin_ws/src/unitree_ros/unitree_gazebo/rviz/z1_aruco_tracking.rviz"
```

Pre-configured displays:

- **Grid** — ground plane reference
- **RobotModel** — Z1 arm (Fixed Frame: `world`)
- **TF** — all frames including `camera_color_optical_frame` and `link06`
- **Camera (ArUco overlay)** — `/aruco/debug_image` with detected marker outlined
- **Camera (raw)** — `/camera/color/image_raw` (disabled by default, enable in RViz)
- **Camera Frame** — axes at the camera optical frame position
- **Marker Pose** — `/aruco/marker_pose` as a red arrow in world frame

---

### Terminal 4 — Start the Z1 controller (sim_ctrl)

```bash
docker exec -it z1_aruco bash -c \
  "source /opt/ros/noetic/setup.bash && \
   source ~/catkin_ws/devel/setup.bash && \
   cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard"
```

---

### Terminal 4 — Monitor detection and arm tracking

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

## 6. Verify the Environment

**Check ROS is sourced:**

```bash
echo $ROS_PACKAGE_PATH
```

**Check Unitree packages are found:**

```bash
rospack find z1_description
rospack find unitree_gazebo
rospack find unitree_legged_msgs
```

**Check Z1 binaries:**

```bash
ls ~/z1_controller/build/z1_ctrl
ls ~/sdk_z1/build/
```

---

## 7. Standard Z1 Simulation (no ArUco)

**Terminal 1 — Launch Gazebo:**

```bash
roslaunch unitree_gazebo z1.launch
```

**Terminal 2 — Start controller:**

```bash
docker exec -it z1_sim bash
cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard
```

**Terminal 3 — Run an SDK example:**

```bash
docker exec -it z1_sim bash
~/sdk_z1/build/highcmd_basic
```

---

## Cleanup

```bash
# Force stop and remove container
docker rm -f z1_aruco

# Revoke X11 access
xhost -local:docker
```
