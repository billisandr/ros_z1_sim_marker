# Control Guide — Unitree Z1 Simulation

## Container Names

| Simulation | Container name | Launch |
| --- | --- | --- |
| Standard Z1 (no ArUco) | `z1_sim` | `roslaunch unitree_gazebo z1.launch` |
| ArUco tracking | `z1_aruco` | `roslaunch z1_aruco z1_aruco_tracking.launch` |

Use the matching `--name` when starting the container so `docker exec` targets the right one.

---

## Keyboard Mode vs SDK Mode

`sim_ctrl` supports two control modes, selected at launch:

```bash
# Keyboard mode (interactive)
./sim_ctrl keyboard

# SDK mode (programmatic — for running the sdk_z1 examples)
./sim_ctrl
```

---

## Keyboard Controls

### Launch

From a second terminal on the host, exec into the running container:

```bash
# Standard Z1 simulation
docker exec -it z1_sim bash

# ArUco tracking simulation
docker exec -it z1_aruco bash
```

Then inside the container:

```bash
cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard
```

Or as a one-liner:

```bash
# Standard Z1
docker exec -it z1_sim bash -c "cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard"

# ArUco tracking
docker exec -it z1_aruco bash -c "cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl keyboard"
```

> The container must already be running with the matching `--name` for `docker exec` to work.

### FSM State Switching

| Key | State |
| --- | --- |
| `` ` `` | Back to start |
| `1` | Passive (no torque) |
| `2` | Joint control |
| `3` | Cartesian control |
| `4` | MoveJ |
| `5` | MoveL |
| `6` | MoveC |
| `7` | Teach |
| `8` | Teach repeat |
| `9` | Save state |
| `0` | To saved state |
| `-` | Trajectory |
| `=` | Calibration |

### Axis Control

Once in state `2` (joint) or `3` (cartesian), use these keys to move each axis:

| Key up | Key down | Axis |
| --- | --- | --- |
| `q` | `a` | Axis 1 |
| `w` | `s` | Axis 2 |
| `e` | `d` | Axis 3 |
| `r` | `f` | Axis 4 |
| `t` | `g` | Axis 5 |
| `y` | `h` | Axis 6 |
| `down` | `up` | Gripper |

---

## SDK Examples (Programmatic Control)

Run `sim_ctrl` in default SDK mode first, then launch an example from a second terminal.

### Terminal 1 — Start controller in SDK mode

```bash
cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl
```

### Terminal 2 — Exec into the container and run an example

```bash
docker exec -it z1_sim bash
```

Then inside the container:

```bash
# FSM-based moves: MoveJ, MoveL, MoveC sequences
~/sdk_z1/build/highcmd_basic

# Interpolated joint space move to a target position
~/sdk_z1/build/highcmd_development

# Direct torque + PD low-level control with gripper
~/sdk_z1/build/lowcmd_development

# Multi-robot low-level commands
~/sdk_z1/build/lowcmd_multirobots
```

> The SDK examples communicate with `sim_ctrl` over UDP on `127.0.0.1:8071/8072`.

---

## What Each Example Does

| Example | Mode | Description |
| --- | --- | --- |
| `highcmd_basic` | High-level | Runs MoveJ → MoveL → MoveC sequences via FSM |
| `highcmd_development` | High-level | Interpolates joint positions to a target over 1000 steps |
| `lowcmd_development` | Low-level | Sends direct joint torque + PD commands, controls gripper |
| `lowcmd_multirobots` | Low-level | Coordinates commands across multiple robots |
