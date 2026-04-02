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
  -v /home/sense/ros_docker/unitree_ros/unitree_gazebo/launch:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/launch \
  -v /home/sense/ros_docker/unitree_ros/unitree_gazebo/worlds:/home/rosuser/catkin_ws/src/unitree_ros/unitree_gazebo/worlds \
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
