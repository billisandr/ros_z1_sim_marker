#!/usr/bin/env python3
"""
Marker Mover Node
Moves the ArUco marker model in Gazebo along a configurable path.
Motion pattern is set in z1_aruco_detector/config/aruco_tracking.yaml.
"""

import rospy
import math
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import SetModelState


class MarkerMoverNode:
    def __init__(self):
        rospy.init_node('marker_mover', anonymous=False)

        self.motion_pattern = rospy.get_param('marker/motion_pattern', 'sinusoidal')
        self.amplitude_y    = rospy.get_param('marker/amplitude_y',  0.20)
        self.amplitude_z    = rospy.get_param('marker/amplitude_z',  0.10)
        self.frequency      = rospy.get_param('marker/frequency',    0.2)
        self.radius         = rospy.get_param('marker/radius',       0.20)
        self.center_x       = rospy.get_param('marker/center', [0.40, 0.0, 0.50])[0]
        self.center_z       = rospy.get_param('marker/center', [0.40, 0.0, 0.50])[2]
        self.update_rate    = rospy.get_param('marker/update_rate', 50.0)

        self.model_name = 'aruco_marker_0'

        rospy.loginfo(f"[marker_mover] Pattern: {self.motion_pattern}")
        rospy.loginfo("[marker_mover] Waiting for /gazebo/set_model_state service...")
        rospy.wait_for_service('/gazebo/set_model_state')
        self.set_state = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)
        rospy.loginfo("[marker_mover] Ready.")

    def _compute_position(self, t):
        omega = 2.0 * math.pi * self.frequency

        if self.motion_pattern == 'sinusoidal':
            x = self.center_x
            y = self.amplitude_y * math.sin(omega * t)
            z = self.center_z + self.amplitude_z * math.sin(2.0 * omega * t)

        elif self.motion_pattern == 'circular':
            x = self.center_x
            y = self.radius * math.sin(omega * t)
            z = self.center_z + self.radius * math.cos(omega * t)

        elif self.motion_pattern == 'figure8':
            x = self.center_x
            y = self.radius * math.sin(omega * t)
            z = self.center_z + self.radius * math.sin(2.0 * omega * t) / 2.0

        elif self.motion_pattern == 'square':
            # One full cycle = 4 sides. Phase within current side: 0..1
            period = 1.0 / self.frequency
            phase = (t % period) / period        # 0..1 over full cycle
            side = int(phase * 4)                # 0,1,2,3
            s = (phase * 4) - side               # 0..1 within each side
            corners_y = [ self.amplitude_y, -self.amplitude_y, -self.amplitude_y,  self.amplitude_y]
            corners_z = [ self.amplitude_z,  self.amplitude_z, -self.amplitude_z, -self.amplitude_z]
            next_side = (side + 1) % 4
            x = self.center_x
            y = corners_y[side] + s * (corners_y[next_side] - corners_y[side])
            z = self.center_z + corners_z[side] + s * (corners_z[next_side] - corners_z[side])

        else:  # static
            x = self.center_x
            y = 0.0
            z = self.center_z

        return x, y, z

    def run(self):
        rate = rospy.Rate(self.update_rate)
        t0 = rospy.Time.now().to_sec()

        while not rospy.is_shutdown():
            t = rospy.Time.now().to_sec() - t0
            x, y, z = self._compute_position(t)

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
