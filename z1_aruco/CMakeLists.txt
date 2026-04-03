cmake_minimum_required(VERSION 3.0.2)
project(z1_aruco)

find_package(catkin REQUIRED)

catkin_package()

install(DIRECTORY launch worlds models rviz xacro config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
