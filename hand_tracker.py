import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import os
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class PoseLandmarks:
    """Stores relevant pose landmarks for arm orientation."""
    left_shoulder: Optional[tuple] = None   # Landmark 11
    right_shoulder: Optional[tuple] = None  # Landmark 12
    left_elbow: Optional[tuple] = None      # Landmark 13
    right_elbow: Optional[tuple] = None     # Landmark 14
    left_wrist: Optional[tuple] = None      # Landmark 15
    right_wrist: Optional[tuple] = None     # Landmark 16


class HandTracker:
    """Handles hand detection and landmark extraction."""
    
    HAND_CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),        # Index
        (0, 9), (9, 10), (10, 11), (11, 12),   # Middle
        (0, 13), (13, 14), (14, 15), (15, 16), # Ring
        (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
        (5, 9), (9, 13), (13, 17)              # Palm
    ]
    
    # Pose landmarks we care about
    POSE_LANDMARK_INDICES = {
        'left_shoulder': 11,
        'right_shoulder': 12,
        'left_elbow': 13,
        'right_elbow': 14,
        'left_wrist': 15,
        'right_wrist': 16
    }
    
    def __init__(self, model_path="hand_landmarker.task", 
                 pose_model_path="pose_landmarker.task",
                 num_hands=2, 
                 min_detection_confidence=0.7, 
                 min_tracking_confidence=0.5,
                 enable_pose=True):
        
        # Hand detector
        self._download_model(model_path, "hand")
        self.hand_detector = self._create_hand_detector(
            model_path, num_hands, 
            min_detection_confidence, 
            min_tracking_confidence
        )
        
        # Pose detector
        self.enable_pose = enable_pose
        self.pose_detector = None
        if enable_pose:
            self._download_model(pose_model_path, "pose")
            self.pose_detector = self._create_pose_detector(
                pose_model_path,
                min_detection_confidence,
                min_tracking_confidence
            )
    
    def _download_model(self, model_path, model_type):
        """Download the model if not present."""
        if not os.path.exists(model_path):
            if model_type == "hand":
                print("Downloading hand landmarker model...")
                url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            else:  # pose
                print("Downloading pose landmarker model...")
                url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
            urllib.request.urlretrieve(url, model_path)
    
    def _create_hand_detector(self, model_path, num_hands, 
                               min_detection_confidence, min_tracking_confidence):
        """Create and return the hand landmarker detector."""
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        return vision.HandLandmarker.create_from_options(options)
    
    def _create_pose_detector(self, model_path, 
                               min_detection_confidence, min_tracking_confidence):
        """Create and return the pose landmarker detector."""
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        return vision.PoseLandmarker.create_from_options(options)
    
    def detect(self, frame):
        """Detect hands in the frame and return results."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        return self.hand_detector.detect(mp_image)
    
    def detect_pose(self, frame) -> Optional[PoseLandmarks]:
        """Detect pose landmarks (shoulders, elbows, wrists)."""
        if not self.enable_pose or self.pose_detector is None:
            return None
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = self.pose_detector.detect(mp_image)
        
        if not results.pose_landmarks:
            return None
        
        # Extract first pose detected
        landmarks = results.pose_landmarks[0]
        
        pose = PoseLandmarks()
        for name, idx in self.POSE_LANDMARK_INDICES.items():
            lm = landmarks[idx]
            setattr(pose, name, (lm.x, lm.y, lm.z))
        
        return pose
    
    def detect_all(self, frame):
        """Detect both hands and pose in a single call."""
        hand_results = self.detect(frame)
        pose_results = self.detect_pose(frame)
        return hand_results, pose_results
    
    def draw_landmarks(self, frame, results, show_numbers=False):
        """Draw hand landmarks and connections on the frame."""
        if not results.hand_landmarks:
            return frame
        
        h, w, _ = frame.shape
        
        for hand_landmarks in results.hand_landmarks:
            # Draw connections
            for start_idx, end_idx in self.HAND_CONNECTIONS:
                start = hand_landmarks[start_idx]
                end = hand_landmarks[end_idx]
                start_point = (int(start.x * w), int(start.y * h))
                end_point = (int(end.x * w), int(end.y * h))
                cv2.line(frame, start_point, end_point, (0, 255, 0), 2)
            
            # Draw landmarks with optional numbers
            for idx, landmark in enumerate(hand_landmarks):
                cx, cy = int(landmark.x * w), int(landmark.y * h)
                cv2.circle(frame, (cx, cy), 5, (255, 0, 255), -1)
                
                # Draw landmark number in red
                if show_numbers:
                    cv2.putText(frame, str(idx), (cx + 8, cy - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return frame
    
    def draw_pose_landmarks(self, frame, pose: PoseLandmarks, show_labels=True):
        """Draw pose landmarks (shoulders, elbows, wrists) on the frame."""
        if pose is None:
            return frame
        
        h, w, _ = frame.shape
        
        # Colors
        SHOULDER_COLOR = (255, 165, 0)  # Orange
        ELBOW_COLOR = (0, 255, 255)     # Yellow
        WRIST_COLOR = (255, 0, 255)     # Magenta
        LINE_COLOR = (200, 200, 200)    # Gray
        
        # Draw connections: shoulder -> elbow -> wrist
        connections = [
            ('left_shoulder', 'left_elbow', 'left_wrist'),
            ('right_shoulder', 'right_elbow', 'right_wrist')
        ]
        
        for shoulder_name, elbow_name, wrist_name in connections:
            shoulder = getattr(pose, shoulder_name)
            elbow = getattr(pose, elbow_name)
            wrist = getattr(pose, wrist_name)
            
            points = []
            for pt in [shoulder, elbow, wrist]:
                if pt is not None:
                    points.append((int(pt[0] * w), int(pt[1] * h)))
                else:
                    points.append(None)
            
            # Draw lines
            if points[0] and points[1]:
                cv2.line(frame, points[0], points[1], LINE_COLOR, 2)
            if points[1] and points[2]:
                cv2.line(frame, points[1], points[2], LINE_COLOR, 2)
        
        # Draw landmark points
        landmarks_to_draw = [
            ('left_shoulder', SHOULDER_COLOR, 'L_SH'),
            ('right_shoulder', SHOULDER_COLOR, 'R_SH'),
            ('left_elbow', ELBOW_COLOR, 'L_ELB'),
            ('right_elbow', ELBOW_COLOR, 'R_ELB'),
            ('left_wrist', WRIST_COLOR, 'L_WR'),
            ('right_wrist', WRIST_COLOR, 'R_WR'),
        ]
        
        for name, color, label in landmarks_to_draw:
            pt = getattr(pose, name)
            if pt is not None:
                cx, cy = int(pt[0] * w), int(pt[1] * h)
                cv2.circle(frame, (cx, cy), 8, color, -1)
                cv2.circle(frame, (cx, cy), 10, (255, 255, 255), 2)
                
                if show_labels:
                    cv2.putText(frame, label, (cx + 12, cy - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
        
        return frame
