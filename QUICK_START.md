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
