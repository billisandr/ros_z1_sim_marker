# Docker Commands Reference

## Inspect

```bash
# List images
docker images

# List containers (running)
docker ps

# List all containers (including stopped)
docker ps -a

# Show resource usage of running containers
docker stats
docker stats <container-name>
```

## Build

```bash
# Build an image from the Dockerfile in the current directory
docker build -t <image-name> .

# Build with a specific Dockerfile
docker build -f <Dockerfile-path> -t <image-name> .

# Build without using cache
docker build --no-cache -t <image-name> .
```

## Run

```bash
# Run a container interactively
docker run -it <image-name>

# Run with a name
docker run -it --name <container-name> <image-name>

# Run and remove container on exit
docker run -it --rm <image-name>

# Run with X11 GUI support (for rviz, rqt, Gazebo)
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  <image-name>

# Run with a volume mount
docker run -it --rm -v <host-path>:<container-path> <image-name>

# Run in detached (background) mode
docker run -d --name <container-name> <image-name>

# Override the default CMD (e.g. start a shell instead of auto-launching)
docker run -it --rm <image-name> bash
```

## Volumes / Live File Sync

Bind mounts map a host directory into the container in real time.
Any file edited on the host is instantly visible inside — no rebuild or docker cp needed.

```bash
# Mount a single directory
docker run -it --rm \
  -v <host-path>:<container-path> \
  <image-name>

# Mount multiple directories (one -v per path)
docker run -it --rm \
  -v /home/sense/ros_docker/z1_aruco_detector:/home/rosuser/catkin_ws/src/z1_aruco_detector \
  -v /home/sense/ros_docker/z1_arm_tracker:/home/rosuser/catkin_ws/src/z1_arm_tracker \
  -v /home/sense/ros_docker/z1_aruco:/home/rosuser/catkin_ws/src/z1_aruco \
  ros-z1 bash

# Mount as read-only (container cannot write back to host)
docker run -it --rm \
  -v <host-path>:<container-path>:ro \
  <image-name>
```

> Bind mounts override files baked into the image at those paths.
> Keep host files as the source of truth.

---

## GPU / Rendering

The `ros-z1` image uses Mesa software rendering by default (`LIBGL_ALWAYS_SOFTWARE=1`
is set in the Dockerfile). No GPU flags are needed to run Gazebo or RViz.

To attempt hardware GPU rendering, override the env vars at runtime:

```bash
# NVIDIA GPU (requires nvidia-container-toolkit on host)
docker run -it --rm \
  --gpus all \
  --device /dev/dri:/dev/dri \
  -e DISPLAY=$DISPLAY \
  -e LIBGL_ALWAYS_SOFTWARE=0 \
  -e NVIDIA_DRIVER_CAPABILITIES=graphics,display,utility \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1 bash

# Intel / Mesa hardware (DRI passthrough)
docker run -it --rm \
  --device /dev/dri:/dev/dri \
  -e DISPLAY=$DISPLAY \
  -e LIBGL_ALWAYS_SOFTWARE=0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ros-z1 bash
```

> Install nvidia-container-toolkit once on the host:
> `sudo apt-get install nvidia-container-toolkit && sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`

---

## USB Device Passthrough (RealSense D435)

The D435 is a USB device. Docker does not expose USB devices by default.

**Host prerequisite — udev rules (run once):**

The Intel RealSense apt repo does not support Ubuntu 24 (Noble). Install the udev rules
directly from upstream instead:

```bash
sudo curl -fsSL https://raw.githubusercontent.com/IntelRealSense/librealsense/master/config/99-realsense-libusb.rules \
  -o /etc/udev/rules.d/99-realsense-libusb.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Unplug and replug the D435. Verify it is visible on the host:

```bash
lsusb | grep RealSense
# expected: Bus 00X Device 00X: ID 8086:0b07 Intel Corp. RealSense D435
```

**Pass the D435 USB bus into the container:**

First find the bus number:

```bash
lsusb | grep RealSense
# example: Bus 004 Device 003: ID 8086:0b07 Intel Corp. RealSense D435
```

Then pass only that bus (cleaner than exposing all buses):

```bash
docker run -it --rm \
  --name ros-z1-real \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  --device /dev/bus/usb/004:/dev/bus/usb/004 \
  ros-z1-aruco-real bash
```

If the bus number changes after a replug, recheck with `lsusb` and update the path.

If the driver logs `RS2_USB_STATUS_ACCESS`, the udev rules have not taken effect.
Unplug and replug the D435 after reloading rules. As a fallback, use `--privileged`:

```bash
# Fallback — full device access (workshop / dev use only)
docker run -it --rm \
  --name ros-z1-real \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  --privileged \
  ros-z1-aruco-real bash
```

Verify the camera is visible inside the container:

```bash
docker exec -it ros-z1 bash -c "rs-enumerate-devices | grep -A3 D435"
```

---

## Enter (exec into running container)

```bash
# Open a bash shell in a running container
docker exec -it <container-name> bash

# Run a specific command inside a running container
docker exec -it <container-name> <command>

# Pass environment variables (e.g. for GUI tools)
docker exec -e DISPLAY=$DISPLAY -it <container-name> bash
```

## Logs

```bash
# Show container logs
docker logs <container-name>

# Follow container logs in real time
docker logs -f <container-name>

# Inspect container details (network, mounts, env, etc.)
docker inspect <container-name>
```

## Stop / Start

```bash
# Stop a running container
docker stop <container-name>

# Start a stopped container
docker start <container-name>

# Restart a container
docker restart <container-name>
```

## Delete

```bash
# Remove a stopped container
docker rm <container-name>

# Force remove a running container
docker rm -f <container-name>

# Remove an image
docker rmi <image-name>

# Remove all stopped containers
docker container prune

# Remove all unused images
docker image prune

# Remove all unused images, containers, volumes, and networks
docker system prune -a
```
