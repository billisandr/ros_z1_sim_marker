#!/usr/bin/env python3
"""
ArUco Detector Node
Subscribes to /camera/color/image_raw, detects ArUco marker ID 0,
and publishes its 3D pose in the world frame via TF lookup.
"""

import rospy
import cv2
import numpy as np
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Bool
import tf2_ros
import tf2_geometry_msgs


class ArucoDetectorNode:
    def __init__(self):
        rospy.init_node('aruco_detector', anonymous=False)

        self.bridge = CvBridge()
        self.camera_matrix = None
        self.dist_coeffs = None
        self.marker_size = rospy.get_param('~marker_size', 0.15)  # metres, matches model.sdf
        self.target_id = rospy.get_param('~marker_id', 0)

        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        # Publishers
        self.pose_pub = rospy.Publisher('/aruco/marker_pose', PoseStamped, queue_size=1)
        self.detected_pub = rospy.Publisher('/aruco/marker_detected', Bool, queue_size=1)
        self.debug_pub = rospy.Publisher('/aruco/debug_image', Image, queue_size=1)

        # Subscribers
        rospy.Subscriber('/camera/color/camera_info', CameraInfo, self._camera_info_cb, queue_size=1)
        rospy.Subscriber('/camera/color/image_raw', Image, self._image_cb, queue_size=1)

        rospy.loginfo("[aruco_detector] Ready, waiting for camera feed...")

    def _camera_info_cb(self, msg):
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.K).reshape(3, 3)
            self.dist_coeffs = np.array(msg.D)
            rospy.loginfo("[aruco_detector] Camera info received.")

    def _image_cb(self, msg):
        if self.camera_matrix is None:
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            rospy.logwarn(f"[aruco_detector] cv_bridge error: {e}")
            return

        corners, ids, _ = self.detector.detectMarkers(frame)

        detected = False
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                if marker_id != self.target_id:
                    continue

                detected = True
                rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                    [corners[i]], self.marker_size, self.camera_matrix, self.dist_coeffs
                )
                rvec = rvecs[0][0]
                tvec = tvecs[0][0]

                # Build PoseStamped in camera frame
                pose_camera = PoseStamped()
                pose_camera.header.stamp = msg.header.stamp
                pose_camera.header.frame_id = 'camera_color_optical_frame'
                pose_camera.pose.position.x = tvec[0]
                pose_camera.pose.position.y = tvec[1]
                pose_camera.pose.position.z = tvec[2]

                rot_mat, _ = cv2.Rodrigues(rvec)
                quat = self._rotation_matrix_to_quaternion(rot_mat)
                pose_camera.pose.orientation.x = quat[0]
                pose_camera.pose.orientation.y = quat[1]
                pose_camera.pose.orientation.z = quat[2]
                pose_camera.pose.orientation.w = quat[3]

                # Transform to world frame
                try:
                    pose_world = self.tf_buffer.transform(
                        pose_camera, 'world', timeout=rospy.Duration(0.1)
                    )
                    self.pose_pub.publish(pose_world)
                except Exception as e:
                    rospy.logwarn_throttle(5.0, f"[aruco_detector] TF transform failed: {e}")

                # Draw debug overlay
                cv2.aruco.drawDetectedMarkers(frame, corners)
                cv2.drawFrameAxes(frame, self.camera_matrix, self.dist_coeffs, rvec, tvec, 0.05)
                break

        self.detected_pub.publish(Bool(data=detected))

        try:
            debug_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            self.debug_pub.publish(debug_msg)
        except Exception:
            pass

    @staticmethod
    def _rotation_matrix_to_quaternion(R):
        trace = R[0, 0] + R[1, 1] + R[2, 2]
        if trace > 0:
            s = 0.5 / np.sqrt(trace + 1.0)
            w = 0.25 / s
            x = (R[2, 1] - R[1, 2]) * s
            y = (R[0, 2] - R[2, 0]) * s
            z = (R[1, 0] - R[0, 1]) * s
        elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
            w = (R[2, 1] - R[1, 2]) / s
            x = 0.25 * s
            y = (R[0, 1] + R[1, 0]) / s
            z = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
            w = (R[0, 2] - R[2, 0]) / s
            x = (R[0, 1] + R[1, 0]) / s
            y = 0.25 * s
            z = (R[1, 2] + R[2, 1]) / s
        else:
            s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
            w = (R[1, 0] - R[0, 1]) / s
            x = (R[0, 2] + R[2, 0]) / s
            y = (R[1, 2] + R[2, 1]) / s
            z = 0.25 * s
        return [x, y, z, w]


if __name__ == '__main__':
    try:
        node = ArucoDetectorNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
