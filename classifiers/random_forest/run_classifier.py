"""
Real-time Gesture Classification using trained Random Forest model (Legacy).

Runs the webcam and classifies hand gestures in real-time.
Note: This classifier has been superseded by the FFNN classifier.
"""

import cv2
import os
import sys
import pickle
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tracking import HandTracker

# Model path
MODEL_PATH = Path(__file__).parent / "model.pkl"


class GestureClassifier:
    """Real-time gesture classifier using trained Random Forest model."""
    
    def __init__(self, model_path: Path = MODEL_PATH):
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {model_path}\n"
                f"Run 'python classifiers/random_forest/train.py' first."
            )
        
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        print(f"✅ Loaded model from: {model_path}")
    
    def extract_features(self, hand_landmarks) -> list:
        """Extract features from MediaPipe hand landmarks."""
        features = []
        
        # Raw coordinates (21 landmarks × 3 coordinates = 63 features)
        for lm in hand_landmarks:
            features.extend([lm.x, lm.y, lm.z])
        
        # Relative features: fingertip distances from wrist
        wrist = hand_landmarks[0]
        fingertips = [4, 8, 12, 16, 20]
        for tip_idx in fingertips:
            tip = hand_landmarks[tip_idx]
            dist_x = tip.x - wrist.x
            dist_y = tip.y - wrist.y
            features.extend([dist_x, dist_y])
        
        # Knuckle distances from wrist (palm orientation)
        knuckles = [5, 9, 13, 17]
        for knuckle_idx in knuckles:
            knuckle = hand_landmarks[knuckle_idx]
            dist_y = knuckle.y - wrist.y
            features.append(dist_y)
        
        # Finger curl features (tip to pip y-distance)
        finger_pairs = [(8, 6), (12, 10), (16, 14), (20, 18)]
        for tip_idx, pip_idx in finger_pairs:
            tip = hand_landmarks[tip_idx]
            pip = hand_landmarks[pip_idx]
            curl = tip.y - pip.y
            features.append(curl)
        
        # Palm inversion feature
        avg_knuckle_y = sum(hand_landmarks[k].y for k in knuckles) / len(knuckles)
        palm_inverted = wrist.y - avg_knuckle_y
        features.append(palm_inverted)
        
        return features
    
    def predict(self, hand_landmarks) -> tuple:
        """
        Predict gesture class and confidence.
        
        Returns:
            (prediction, confidence) where prediction is 0/1 and confidence is 0-1
        """
        features = self.extract_features(hand_landmarks)
        features = np.array(features).reshape(1, -1)
        
        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]
        confidence = probabilities[1]  # Probability of positive class
        
        return prediction, confidence


def main():
    print("="*60)
    print("🌲 RANDOM FOREST GESTURE CLASSIFIER")
    print("="*60)
    
    # Initialize
    try:
        classifier = GestureClassifier()
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        return
    
    tracker = HandTracker(enable_pose=True)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    show_pose = True
    confidence_threshold = 0.7
    
    print("\nControls:")
    print("  'p' - Toggle pose landmarks")
    print("  '+' - Increase confidence threshold")
    print("  '-' - Decrease confidence threshold")
    print("  'q' - Quit")
    print("="*60)
    
    # Detection counter
    detection_count = 0
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        
        # Detect hands and pose
        hand_results = tracker.detect(frame)
        
        if show_pose:
            pose_results = tracker.detect_pose(frame)
            frame = tracker.draw_pose_landmarks(frame, pose_results)
        
        frame = tracker.draw_landmarks(frame, hand_results)
        
        # Classify gesture
        prediction = 0
        confidence = 0.0
        
        if hand_results.hand_landmarks:
            hand_landmarks = hand_results.hand_landmarks[0]
            prediction, confidence = classifier.predict(hand_landmarks)
        
        # Draw classification result
        if prediction == 1 and confidence >= confidence_threshold:
            # Spider-Man gesture detected!
            detection_count += 1
            
            # Green bar at top
            cv2.rectangle(frame, (0, 0), (w, 60), (0, 255, 0), -1)
            cv2.putText(frame, f"SPIDER-MAN! ({confidence:.0%})", (10, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
            
            # Detection counter
            cv2.putText(frame, f"Count: {detection_count}", (w - 150, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        else:
            # No detection
            cv2.rectangle(frame, (0, 0), (w, 60), (50, 50, 50), -1)
            
            if hand_results.hand_landmarks:
                cv2.putText(frame, f"Not Spider-Man ({confidence:.0%})", (10, 42),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
            else:
                cv2.putText(frame, "No hand detected", (10, 42),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
        
        # Show confidence threshold
        cv2.putText(frame, f"Threshold: {confidence_threshold:.0%}", (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Show confidence bar
        bar_width = int(confidence * 200)
        bar_color = (0, 255, 0) if confidence >= confidence_threshold else (0, 0, 255)
        cv2.rectangle(frame, (10, h - 50), (10 + bar_width, h - 35), bar_color, -1)
        cv2.rectangle(frame, (10, h - 50), (210, h - 35), (255, 255, 255), 1)
        cv2.putText(frame, f"{confidence:.0%}", (220, h - 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow("Random Forest Classifier", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('p'):
            show_pose = not show_pose
        elif key == ord('+') or key == ord('='):
            confidence_threshold = min(0.99, confidence_threshold + 0.05)
            print(f"Threshold: {confidence_threshold:.0%}")
        elif key == ord('-'):
            confidence_threshold = max(0.5, confidence_threshold - 0.05)
            print(f"Threshold: {confidence_threshold:.0%}")
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
