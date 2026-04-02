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
  ros-z1 bash
```

> The image uses Mesa software rendering by default (LIBGL_ALWAYS_SOFTWARE=1 is set
> in the Dockerfile). No GPU setup is required to run Gazebo or RViz.

---

## 3. Launch Gazebo Simulation

Open **Terminal 1** (or a tmux pane) inside the container:

```bash
source /opt/ros/noetic/setup.bash && source ~/catkin_ws/devel/setup.bash
roslaunch unitree_gazebo z1.launch
```

This starts `roscore`, loads the robot URDF/xacro, spawns the arm in Gazebo,
and starts the joint controllers.

### roslaunch Arguments — z1.launch

| Argument | Default | Options | Description |
| --- | --- | --- | --- |
| `wname` | `earth` | `earth`, `space`, `stairs`, `building_editor_models` | Gazebo world |
| `paused` | `true` | `true`, `false` | Start Gazebo paused — press Play in GUI to start physics |
| `gui` | `true` | `true`, `false` | Show the Gazebo GUI window |
| `headless` | `false` | `true`, `false` | No rendering — faster, overrides `gui:=true` |
| `UnitreeGripperYN` | `true` | `true`, `false` | Include gripper controller |
| `user_debug` | `false` | `true`, `false` | Enable FSM debug output |
| `debug` | `false` | `true`, `false` | Enable Gazebo debug output |

```bash
# Start unpaused in the stairs world
roslaunch unitree_gazebo z1.launch wname:=stairs paused:=false

# Headless, no gripper
roslaunch unitree_gazebo z1.launch headless:=true UnitreeGripperYN:=false

# GUI visible, start immediately
roslaunch unitree_gazebo z1.launch paused:=false gui:=true
```

---

## 4. Start the Simulation Controller

Open **Terminal 2** (or a new tmux pane):

```bash
cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard
```

`sim_ctrl` connects to the Gazebo simulation via ROS topics and runs the Z1 FSM
(Finite State Machine) controller. Pass no argument for SDK mode.

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

## 7. Verify the Simulation is Running

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

## 8. Shutdown

```bash
# Stop all ROS nodes cleanly
rosnode kill --all

# Then exit tmux panes / container
exit
```

---

## Quick Reference

| Step | Command |
| --- | --- |
| Allow X11 | `xhost +local:docker` |
| Start container | `docker run -it --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix ros-z1 bash` |
| Launch Gazebo | `roslaunch unitree_gazebo z1.launch` |
| Start controller | `cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard` |
| Run SDK example | `~/sdk_z1/build/highcmd_basic` |
| Check nodes | `rosnode list` |
