#!/usr/bin/env python3
"""
Marker Mover Node
Moves the ArUco marker model in Gazebo along a smooth sinusoidal path
within the Z1 arm's reachable workspace, so the arm has something to track.
"""

import rospy
import math
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import SetModelState


class MarkerMoverNode:
    def __init__(self):
        rospy.init_node('marker_mover', anonymous=False)

        # Motion parameters (tunable via ROS params)
        self.amplitude_y  = rospy.get_param('~amplitude_y',  0.20)   # metres, side-to-side
        self.amplitude_z  = rospy.get_param('~amplitude_z',  0.10)   # metres, up-down
        self.frequency    = rospy.get_param('~frequency',    0.2)    # Hz
        self.center_x     = rospy.get_param('~center_x',    0.40)    # metres from arm base
        self.center_z     = rospy.get_param('~center_z',    0.50)    # metres height
        self.update_rate  = rospy.get_param('~update_rate', 50.0)    # Hz

        self.model_name = 'aruco_marker_0'

        rospy.loginfo("[marker_mover] Waiting for /gazebo/set_model_state service...")
        rospy.wait_for_service('/gazebo/set_model_state')
        self.set_state = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)
        rospy.loginfo("[marker_mover] Ready.")

    def run(self):
        rate = rospy.Rate(self.update_rate)
        t0 = rospy.Time.now().to_sec()

        while not rospy.is_shutdown():
            t = rospy.Time.now().to_sec() - t0
            omega = 2.0 * math.pi * self.frequency

            x = self.center_x
            y = self.amplitude_y * math.sin(omega * t)
            z = self.center_z + self.amplitude_z * math.sin(2.0 * omega * t)

            state = ModelState()
            state.model_name = self.model_name
            state.reference_frame = 'world'
            state.pose.position.x = x
            state.pose.position.y = y
            state.pose.position.z = z
            # Rotate marker to face arm base (joint 0 at origin): pitch = -pi/2
            # Quaternion for rotation around Y by -pi/2: (x=0, y=-0.7071, z=0, w=0.7071)
            state.pose.orientation.x = 0.0
            state.pose.orientation.y = -0.7071
            state.pose.orientation.z = 0.0
            state.pose.orientation.w = 0.7071

            try:
                self.set_state(state)
            except Exception as e:
                rospy.logwarn_throttle(5.0, f"[marker_mover] set_model_state failed: {e}")

            rate.sleep()


if __name__ == '__main__':
    try:
        node = MarkerMoverNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
