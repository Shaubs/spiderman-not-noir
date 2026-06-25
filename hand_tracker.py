import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import os


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
    
    def __init__(self, model_path="hand_landmarker.task", num_hands=2, 
                 min_detection_confidence=0.7, min_tracking_confidence=0.5):
        self._download_model(model_path)
        self.detector = self._create_detector(
            model_path, num_hands, 
            min_detection_confidence, 
            min_tracking_confidence
        )
    
    def _download_model(self, model_path):
        """Download the hand landmarker model if not present."""
        if not os.path.exists(model_path):
            print("Downloading hand landmarker model...")
            url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            urllib.request.urlretrieve(url, model_path)
    
    def _create_detector(self, model_path, num_hands, 
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
    
    def detect(self, frame):
        """Detect hands in the frame and return results."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        return self.detector.detect(mp_image)
    
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
