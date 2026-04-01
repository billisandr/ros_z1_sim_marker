#!/usr/bin/env python3
"""
Arm Tracker Node
Subscribes to /aruco/marker_pose (world frame) and sends smooth
Cartesian end-effector commands to sim_ctrl via the unitree_arm SDK.

sim_ctrl must be running in SDK mode (no 'keyboard' argument):
  cd ~/z1_controller/build && ~/catkin_ws/build/sim_ctrl
"""

import sys
import rospy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Bool

# The unitree_arm_interface Python binding is pre-compiled in sdk_z1/lib/
SDK_LIB_PATH = '/home/rosuser/sdk_z1/lib'
if SDK_LIB_PATH not in sys.path:
    sys.path.insert(0, SDK_LIB_PATH)

try:
    import unitree_arm_interface as arm_sdk
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    rospy.logwarn("[arm_tracker] unitree_arm_interface not found — running in DRY RUN mode.")


class ArmTrackerNode:
    def __init__(self):
        rospy.init_node('arm_tracker', anonymous=False)

        self.update_rate     = rospy.get_param('arm_tracker/update_rate',     50.0)
        self.speed           = rospy.get_param('arm_tracker/cartesian_speed', 0.3)
        self.enabled         = rospy.get_param('arm_tracker/enabled',         True)
        offset               = rospy.get_param('arm_tracker/target_offset',  [-0.05, 0.0, 0.0])
        self.offset_x        = offset[0]
        self.offset_y        = offset[1]
        self.offset_z        = offset[2]
        self.marker_detected = False
        self.latest_pose     = None

        ws = rospy.get_param('arm_tracker/workspace', {})
        self.x_min = ws.get('x', [0.20, 0.65])[0]
        self.x_max = ws.get('x', [0.20, 0.65])[1]
        self.y_min = ws.get('y', [-0.35, 0.35])[0]
        self.y_max = ws.get('y', [-0.35, 0.35])[1]
        self.z_min = ws.get('z', [0.10, 0.75])[0]
        self.z_max = ws.get('z', [0.10, 0.75])[1]

        if not self.enabled:
            rospy.loginfo("[arm_tracker] Tracking disabled in config — running in observe mode.")

        rospy.Subscriber('/aruco/marker_pose',     PoseStamped, self._pose_cb,     queue_size=1)
        rospy.Subscriber('/aruco/marker_detected', Bool,        self._detected_cb, queue_size=1)

        if SDK_AVAILABLE:
            rospy.loginfo("[arm_tracker] Initialising arm SDK...")
            self.arm = arm_sdk.unitreeArm(hasGripper=True)
            self.arm.sendRecvThread.start()
            self.arm.backToStart()
            self.arm.startTrack(arm_sdk.ArmFSMState.CARTESIAN)
            rospy.loginfo("[arm_tracker] Arm in CARTESIAN mode. Ready to track.")
        else:
            self.arm = None
            rospy.logwarn("[arm_tracker] DRY RUN — poses will be logged but not sent to arm.")

    def _detected_cb(self, msg):
        self.marker_detected = msg.data

    def _pose_cb(self, msg):
        self.latest_pose = msg

    def _clamp(self, value, lo, hi):
        return max(lo, min(hi, value))

    def run(self):
        rate = rospy.Rate(self.update_rate)

        while not rospy.is_shutdown():
            if self.enabled and self.marker_detected and self.latest_pose is not None:
                p = self.latest_pose.pose.position

                # Apply offset so end-effector stops before reaching the marker
                x = self._clamp(p.x + self.offset_x, self.x_min, self.x_max)
                y = self._clamp(p.y + self.offset_y, self.y_min, self.y_max)
                z = self._clamp(p.z + self.offset_z, self.z_min, self.z_max)

                if SDK_AVAILABLE and self.arm is not None:
                    # Build 6D Cartesian target: [roll, pitch, yaw, x, y, z]
                    # Keep end-effector orientation fixed (pointing forward)
                    import numpy as np
                    target = np.array([0.0, 0.0, 0.0, x, y, z])
                    try:
                        self.arm.cartesianCtrlCmd(target, 0.0, self.speed)
                    except Exception as e:
                        rospy.logwarn_throttle(5.0, f"[arm_tracker] SDK command failed: {e}")
                else:
                    rospy.loginfo_throttle(1.0,
                        f"[arm_tracker] DRY RUN target -> x:{x:.3f} y:{y:.3f} z:{z:.3f}")

            rate.sleep()

        # Clean shutdown
        if SDK_AVAILABLE and self.arm is not None:
            self.arm.backToStart()
            self.arm.setFsm(arm_sdk.ArmFSMState.PASSIVE)
            self.arm.sendRecvThread.shutdown()


if __name__ == '__main__':
    try:
        node = ArmTrackerNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
