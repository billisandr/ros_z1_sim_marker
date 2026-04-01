cmake_minimum_required(VERSION 3.0)
project(z1_aruco_detector)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  geometry_msgs
  sensor_msgs
  gazebo_msgs
  cv_bridge
  image_transport
  tf2_ros
  tf2_geometry_msgs
)

catkin_package()

catkin_install_python(PROGRAMS
  src/aruco_detector_node.py
  src/marker_mover_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
