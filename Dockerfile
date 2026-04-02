# Utilisation de l'image officielle ROS Noetic
FROM osrf/ros:noetic-desktop-full

# Installation de quelques outils utiles + support GUI
RUN apt-get update && apt-get install -y \
    python3-rosdep \
    python3-rosinstall \
    python3-rosinstall-generator \
    python3-wstool \
    build-essential \
    nano \
    git \
    tmux \
    wget \
    curl \
    iputils-ping \
    net-tools \
    psmisc \
    # OpenGL — libglvnd vendor-neutral dispatch routes GL to NVIDIA or Mesa at runtime
    libglvnd0 \
    libgl1 \
    libglx0 \
    libegl1 \
    libgles2 \
    libglvnd-dev \
    libgl1-mesa-dri \
    mesa-utils \
    x11-apps \
    # Outils ROS GUI
    ros-noetic-rqt \
    ros-noetic-rqt-common-plugins \
    ros-noetic-rviz \
    # ROS controllers
    ros-noetic-position-controllers \
    ros-noetic-effort-controllers \
    ros-noetic-joint-state-controller \
    # Gazebo ROS integration
    ros-noetic-gazebo-ros-pkgs \
    ros-noetic-gazebo-ros-control \
    ros-noetic-robot-state-publisher \
    ros-noetic-controller-manager \
    ros-noetic-realtime-tools \
    ros-noetic-hardware-interface \
    ros-noetic-controller-interface \
    # Dependencies for sdk_z1 and z1_controller
    libboost-all-dev \
    libeigen3-dev \
    # ArUco detection dependencies
    python3-pip \
    python3-opencv \
    ros-noetic-cv-bridge \
    ros-noetic-image-transport \
    ros-noetic-tf2-ros \
    ros-noetic-tf2-geometry-msgs \
    && pip3 install opencv-contrib-python-headless \
    && rm -rf /var/lib/apt/lists/*

# Initialisation de rosdep
RUN rosdep update

# Création d'un utilisateur non-root
ARG USERNAME=rosuser
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && usermod -aG video $USERNAME

# Copy and build sdk_z1
COPY --chown=$USERNAME:$USERNAME sdk_z1 /home/$USERNAME/sdk_z1
RUN cd /home/$USERNAME/sdk_z1 && \
    rm -rf build && mkdir build && cd build && \
    cmake .. && make -j$(nproc)

# Copy and build z1_controller
COPY --chown=$USERNAME:$USERNAME z1_controller /home/$USERNAME/z1_controller
RUN cd /home/$USERNAME/z1_controller && \
    rm -rf build && mkdir build && cd build && \
    cmake .. && make -j$(nproc)

# Préparer le workspace catkin et copier unitree_ros (encore en root pour COPY --chown)
RUN mkdir -p /home/$USERNAME/catkin_ws/src
COPY --chown=$USERNAME:$USERNAME unitree_ros /home/$USERNAME/catkin_ws/src/unitree_ros
COPY --chown=$USERNAME:$USERNAME z1_controller/sim /home/$USERNAME/catkin_ws/src/z1_controller
COPY --chown=$USERNAME:$USERNAME z1_aruco_detector /home/$USERNAME/catkin_ws/src/z1_aruco_detector
COPY --chown=$USERNAME:$USERNAME z1_arm_tracker /home/$USERNAME/catkin_ws/src/z1_arm_tracker

# Cloner unitree_legged_msgs depuis unitree_ros_to_real
RUN git clone --depth 1 https://github.com/unitreerobotics/unitree_ros_to_real.git /tmp/unitree_ros_to_real_tmp && \
    cp -r /tmp/unitree_ros_to_real_tmp/unitree_legged_msgs /home/$USERNAME/catkin_ws/src/unitree_legged_msgs && \
    chown -R $USERNAME:$USERNAME /home/$USERNAME/catkin_ws/src/unitree_legged_msgs && \
    rm -rf /tmp/unitree_ros_to_real_tmp && \
    chown -R $USERNAME:$USERNAME /home/$USERNAME/catkin_ws

# Passer à l'utilisateur non-root
USER $USERNAME
ENV HOME=/home/$USERNAME

# Construire le workspace catkin (inclut unitree_ros + unitree_legged_msgs)
RUN /bin/bash -c "source /opt/ros/noetic/setup.bash && \
    cd $HOME/catkin_ws && \
    catkin_make"

# Configuration du shell pour charger ROS automatiquement
RUN echo "source /opt/ros/noetic/setup.bash" >> $HOME/.bashrc && \
    echo "source $HOME/catkin_ws/devel/setup.bash" >> $HOME/.bashrc && \
    echo 'export PS1="\[\033[01;36m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "' >> $HOME/.bashrc

# GUI / GPU environment
ENV LD_LIBRARY_PATH=/home/rosuser/sdk_z1/lib
ENV QT_X11_NO_MITSHM=1
# Tell NVIDIA container runtime to expose the GPU and its GL libraries
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=graphics,display,utility
# Force Mesa software renderer (llvmpipe).
# The Intel GPU (Meteor Lake / 0x7d67) is too new for Mesa 21 in Ubuntu 20.04,
# and NVIDIA GLX rejects indirect X11 connections from Docker.
# llvmpipe provides stable OpenGL 3.1 for Gazebo and RViz.
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV MESA_GL_VERSION_OVERRIDE=3.3

WORKDIR $HOME

# Launch ArUco tracking simulation on container start
CMD ["/bin/bash", "-c", "source /opt/ros/noetic/setup.bash && source $HOME/catkin_ws/devel/setup.bash && roslaunch unitree_gazebo z1_aruco_tracking.launch"]
