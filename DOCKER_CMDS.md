# Docker Commands Reference

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

# Run with X11 GUI support (for rviz, rqt, etc.)
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  <image-name>

# Run with a volume mount
docker run -it --rm -v <host-path>:<container-path> <image-name>

# Run in detached (background) mode
docker run -d --name <container-name> <image-name>
```

## Enter (exec into running container)

```bash
# Open a bash shell in a running container
docker exec -it <container-name> bash

# Run a specific command inside a running container
docker exec -it <container-name> <command>
```

## Check

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# List all images
docker images

# Show container logs
docker logs <container-name>

# Follow container logs in real time
docker logs -f <container-name>

# Inspect container details (network, mounts, env, etc.)
docker inspect <container-name>

# Show resource usage of running containers
docker stats
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
