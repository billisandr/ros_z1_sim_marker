# Quick Start — ROS Noetic Z1 Simulation

## 1. Build the Docker Image

```bash
docker build -t ros-z1 .
```

---

## 2. Allow X11 Forwarding (Host)

```bash
xhost +local:docker
```

---

## 3. Run the Container

```bash
docker run -it --rm \
  --name z1_sim \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1
```

# If rendering is slow

Option A — Use NVIDIA GPU (best performance)
First check if nvidia-container-toolkit is installed on the host:

```bash
nvidia-smi
docker run --gpus all --rm nvidia/cuda:11.0-base nvidia-smi
```

If that works, run the container with:

```bash
docker run -it --rm \
  --name z1_aruco \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  --gpus all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  ros-z1-aruco
```

Option B — Force software rendering (quickest fix, no GPU needed)

```bash
docker run -it --rm \
  --name z1_aruco \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e LIBGL_ALWAYS_SOFTWARE=1 \
  -e MESA_GL_VERSION_OVERRIDE=3.3 \
  ros-z1-aruco
```

---

## 4. Verify the Environment (inside container)

**Check ROS is sourced:**

```bash
echo $ROS_PACKAGE_PATH
```

Should list paths including `catkin_ws` and `/opt/ros/noetic`.

**Check Unitree packages are found:**

```bash
rospack find z1_description
rospack find unitree_gazebo
rospack find unitree_legged_msgs
```

All three should return paths without errors.

**Check Z1 binaries:**

```bash
ls ~/z1_controller/build/z1_ctrl
ls ~/sdk_z1/build/
```

---

## 5. Launch the Z1 Gazebo Simulation

```bash
roslaunch unitree_gazebo z1.launch
```

Gazebo opens with the Z1 arm spawned in the world.

---

## 6. Start the Controller (new terminal / tmux pane)

```bash
docker exec -it z1_sim bash
cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard
```

---

## 7. Run an SDK Example (new terminal / tmux pane)

```bash
docker exec -it z1_sim bash
~/sdk_z1/build/highcmd_basic
```

---

## Cleanup

```bash
# Revoke X11 access
xhost -local:docker
```
