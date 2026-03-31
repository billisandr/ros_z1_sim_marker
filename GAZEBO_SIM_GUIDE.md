# Gazebo Simulation Startup Guide — Unitree Z1 Arm

## Prerequisites

- Docker image built from this repo's Dockerfile
- X11 forwarding available on the host (for GUI)
- `xhost` installed on the host

---

## 1. Allow X11 Forwarding (Host)

Run this on your host machine before starting the container:

```bash
xhost +local:docker
```

To revoke after you're done:

```bash
xhost -local:docker
```

---

## 2. Start the Docker Container

```bash
docker run -it --rm \
  --name z1_sim \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1
```

> If you want your local workspace to persist across container restarts, add a volume:
> ```bash
> -v $(pwd)/catkin_ws:/home/rosuser/catkin_ws
> ```

---

## 3. Launch Gazebo Simulation

Open **Terminal 1** (or a tmux pane) — launch the Gazebo world with the Z1 arm:

```bash
roslaunch unitree_gazebo z1.launch
```

> This starts `roscore`, loads the robot URDF/xacro, spawns the arm in Gazebo, and starts the joint controllers.

---

## 4. Start the Simulation Controller

Open **Terminal 2** (or a new tmux pane):

```bash
cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard
```

`sim_ctrl` connects to the Gazebo simulation via ROS topics and runs the Z1 FSM (Finite State Machine) controller.

---

## 5. Run SDK Examples

Open **Terminal 3**. The SDK examples communicate with the controller over UDP.

```bash
cd ~/sdk_z1/build

# Basic high-level command example
./highcmd_basic

# High-level development example
./highcmd_development

# Low-level joint command example
./lowcmd_development
```

> Make sure `sim_ctrl` is already running before launching SDK examples.

---

## 6. Using tmux (Recommended)

Managing multiple terminals inside Docker is easier with tmux:

```bash
tmux new-session -s sim       # create session

# Split into panes
Ctrl+b %    # vertical split
Ctrl+b "    # horizontal split

# Switch between panes
Ctrl+b arrow-key

# Detach from session (container keeps running)
Ctrl+b d

# Reattach
tmux attach -t sim
```

---

## 8. Verify the Simulation is Running

```bash
# Check active ROS nodes
rosnode list

# Check active topics
rostopic list

# Stream joint states
rostopic echo /joint_states

# Open rqt dashboard
rqt

# Open RViz
rviz
```

---

## 9. Shutdown

```bash
# Stop all ROS nodes cleanly
rosnode kill --all

# Then exit tmux panes / container
exit
```

---

## Quick Reference

| Step | Command |
|------|---------|
| Allow X11 | `xhost +local:docker` |
| Start container | `docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix ros-husky` |
| Build sim pkg | `cp -r ~/z1_controller/sim ~/catkin_ws/src/z1_controller && cd ~/catkin_ws && catkin_make` |
| Launch Gazebo | `roslaunch z1_controller z1.launch` |
| Start controller | `~/catkin_ws/devel/lib/z1_controller/sim_ctrl` |
| Run SDK example | `~/sdk_z1/build/highcmd_basic` |
| Check nodes | `rosnode list` |
