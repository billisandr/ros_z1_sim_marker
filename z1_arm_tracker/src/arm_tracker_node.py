#!/usr/bin/env python3
"""
Arm Tracker Node — Reference Implementation
Tracks a moving ArUco marker in 2D (Y lateral + Z vertical) by publishing
MotorCmd directly to the Gazebo joint controllers via ROS topics.

No sim_ctrl or UDP required — pure ROS control.
IK is computed using the Unitree Z1 model from the SDK (model only, no UDP).

Fixed X (forward reach) is held constant; only Y and Z follow the marker.
"""

import sys
import threading
import numpy as np
import rospy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Bool
from sensor_msgs.msg import JointState

SDK_LIB_PATH = '/home/rosuser/sdk_z1/lib'
if SDK_LIB_PATH not in sys.path:
    sys.path.insert(0, SDK_LIB_PATH)

try:
    import unitree_arm_interface as arm_sdk
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    rospy.logwarn("[arm_tracker] unitree_arm_interface not found — running in DRY RUN mode.")

try:
    from unitree_legged_msgs.msg import MotorCmd
    MSGS_AVAILABLE = True
except ImportError:
    MSGS_AVAILABLE = False
    rospy.logwarn("[arm_tracker] unitree_legged_msgs not found — running in DRY RUN mode.")


# Joint order matching IOROS.cpp publisher indices 0-5
JOINT_TOPICS = [
    '/z1_gazebo/Joint01_controller/command',
    '/z1_gazebo/Joint02_controller/command',
    '/z1_gazebo/Joint03_controller/command',
    '/z1_gazebo/Joint04_controller/command',
    '/z1_gazebo/Joint05_controller/command',
    '/z1_gazebo/Joint06_controller/command',
]
JOINT_NAMES = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6']


class ArmTrackerNode:
    def __init__(self):
        rospy.init_node('arm_tracker', anonymous=False)

        self.update_rate = rospy.get_param('arm_tracker/update_rate',     50.0)
        self.enabled     = rospy.get_param('arm_tracker/enabled',         True)
        self.fixed_x     = rospy.get_param('arm_tracker/fixed_x',         0.50)
        offset           = rospy.get_param('arm_tracker/target_offset',  [0.0, 0.0, 0.0])
        self.offset_y    = offset[1]
        self.offset_z    = offset[2]

        # Low-pass filter on Cartesian target: 0.0=frozen, 1.0=instant, 0.05=slow/smooth
        self.alpha = rospy.get_param('arm_tracker/smoothing_alpha', 0.05)

        # Joint PD gains for MotorCmd
        self.kp = rospy.get_param('arm_tracker/joint_kp', 150.0)
        self.kd = rospy.get_param('arm_tracker/joint_kd',   3.0)

        # Smoothed Cartesian target — initialised to fixed_x, arm home Y/Z
        self._tx = self.fixed_x
        self._ty = 0.0
        self._tz = 0.40

        ws = rospy.get_param('arm_tracker/workspace', {})
        self.y_min = ws.get('y', [-0.35, 0.35])[0]
        self.y_max = ws.get('y', [-0.35, 0.35])[1]
        self.z_min = ws.get('z', [0.10, 0.75])[0]
        self.z_max = ws.get('z', [0.10, 0.75])[1]

        self.marker_detected = False
        self.latest_pose     = None
        self.q_current       = np.zeros(6)
        self._q_lock         = threading.Lock()

        if not self.enabled:
            rospy.loginfo("[arm_tracker] Tracking disabled in config — observe mode.")

        # Joint state subscriber — keeps q_current up to date for IK warm-start
        rospy.Subscriber('/z1_gazebo/joint_states', JointState, self._joint_state_cb, queue_size=1)
        rospy.Subscriber('/aruco/marker_pose',       PoseStamped, self._pose_cb,       queue_size=1)
        rospy.Subscriber('/aruco/marker_detected',   Bool,        self._detected_cb,   queue_size=1)

        # One publisher per joint — matches IOROS topic order
        self.joint_pubs = None
        if MSGS_AVAILABLE:
            self.joint_pubs = [
                rospy.Publisher(t, MotorCmd, queue_size=1) for t in JOINT_TOPICS
            ]

        # Arm model for IK — instantiate without loopOn() (no UDP connection)
        self.arm_model = None
        if SDK_AVAILABLE:
            try:
                _iface = arm_sdk.ArmInterface(hasGripper=True)
                self.arm_model = _iface._ctrlComp.armModel
                rospy.loginfo("[arm_tracker] Z1 model loaded for IK.")
            except Exception as e:
                rospy.logwarn(f"[arm_tracker] Could not load arm model: {e}")

        rospy.loginfo(f"[arm_tracker] Ready — fixed_x={self.fixed_x:.2f} m, "
                      f"Y∈[{self.y_min:.2f},{self.y_max:.2f}], "
                      f"Z∈[{self.z_min:.2f},{self.z_max:.2f}]")

    # ------------------------------------------------------------------ callbacks

    def _joint_state_cb(self, msg):
        with self._q_lock:
            for i, name in enumerate(JOINT_NAMES):
                if name in msg.name:
                    idx = msg.name.index(name)
                    self.q_current[i] = msg.position[idx]

    def _detected_cb(self, msg):
        self.marker_detected = msg.data

    def _pose_cb(self, msg):
        self.latest_pose = msg

    # ------------------------------------------------------------------ helpers

    def _clamp(self, v, lo, hi):
        return max(lo, min(hi, v))

    def _send_joint_commands(self, q_target):
        for i, pub in enumerate(self.joint_pubs):
            cmd = MotorCmd()
            cmd.mode = 10        # position + velocity + torque PD control
            cmd.q    = float(q_target[i])
            cmd.dq   = 0.0
            cmd.tau  = 0.0
            cmd.Kp   = self.kp
            cmd.Kd   = self.kd
            pub.publish(cmd)

    # ------------------------------------------------------------------ main loop

    def run(self):
        rate = rospy.Rate(self.update_rate)

        while not rospy.is_shutdown():
            if self.enabled and self.marker_detected and self.latest_pose is not None:
                p = self.latest_pose.pose.position

                # 2D tracking: hold X fixed, follow marker Y and Z only
                # Low-pass filter smooths the target to prevent jerky motion
                ty_raw = self._clamp(p.y + self.offset_y, self.y_min, self.y_max)
                tz_raw = self._clamp(p.z + self.offset_z, self.z_min, self.z_max)
                self._ty += self.alpha * (ty_raw - self._ty)
                self._tz += self.alpha * (tz_raw - self._tz)
                tx = self.fixed_x
                ty = self._ty
                tz = self._tz

                if self.arm_model is not None and self.joint_pubs is not None:
                    try:
                        # Build target homogeneous transform from 6D posture
                        target_posture = np.array([0.0, 0.0, 0.0, tx, ty, tz])
                        T_target = arm_sdk.postureToHomo(target_posture)

                        # IK: warm-started from current joint angles
                        with self._q_lock:
                            q_target = self.q_current.copy()

                        success, q_target = self.arm_model.inverseKinematics(T_target, q_target, True)

                        if success:
                            self._send_joint_commands(q_target)
                        else:
                            rospy.logwarn_throttle(2.0,
                                f"[arm_tracker] IK failed for target "
                                f"x:{tx:.3f} y:{ty:.3f} z:{tz:.3f}")

                    except Exception as e:
                        rospy.logwarn_throttle(5.0, f"[arm_tracker] Control error: {e}")
                else:
                    rospy.loginfo_throttle(1.0,
                        f"[arm_tracker] DRY RUN — x:{tx:.3f} y:{ty:.3f} z:{tz:.3f}")

            rate.sleep()


if __name__ == '__main__':
    try:
        node = ArmTrackerNode()
        node.run()
    except rospy.ROSInterruptException:
        pass
