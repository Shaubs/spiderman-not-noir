#!/usr/bin/env python3
"""
Real-time Spider-Man gesture classification using Feed Forward Neural Network.
"""

import sys
import cv2
import numpy as np
import torch
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hand_tracker import HandTracker
from ffnn_classifier.train import GestureNet, extract_features


# Hand connections for drawing
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),      # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),      # Index
    (5, 9), (9, 10), (10, 11), (11, 12), # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (0, 17)                               # Palm
]


def draw_hand_landmarks(frame, hand_landmarks):
    """Draw hand landmarks on frame."""
    h, w, _ = frame.shape
    
    # Draw connections
    for start_idx, end_idx in HAND_CONNECTIONS:
        start = hand_landmarks[start_idx]
        end = hand_landmarks[end_idx]
        start_point = (int(start.x * w), int(start.y * h))
        end_point = (int(end.x * w), int(end.y * h))
        cv2.line(frame, start_point, end_point, (0, 255, 0), 2)
    
    # Draw landmarks
    for landmark in hand_landmarks:
        cx, cy = int(landmark.x * w), int(landmark.y * h)
        cv2.circle(frame, (cx, cy), 5, (255, 0, 255), -1)


class FFNNClassifier:
    """Real-time classifier using trained FFNN model."""
    
    def __init__(self, model_path: Path, threshold: float = 0.7):
        self.threshold = threshold
        self.model = None
        self.load_model(model_path)
    
    def load_model(self, model_path: Path):
        """Load trained model from disk."""
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}\n"
                "Please train the model first: python ffnn_classifier/train.py"
            )
        
        checkpoint = torch.load(model_path, map_location='cpu')
        input_size = checkpoint.get('input_size', 82)
        
        self.model = GestureNet(input_size=input_size)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        print(f"✅ Loaded FFNN model from {model_path}")
    
    def predict(self, landmarks: list) -> tuple[bool, float]:
        """
        Predict if landmarks represent Spider-Man gesture.
        
        Returns:
            (is_spiderman, confidence)
        """
        if len(landmarks) != 21:
            return False, 0.0
        
        # Convert landmarks to dict format expected by extract_features
        landmarks_dict = [
            {'x': lm.x, 'y': lm.y, 'z': lm.z}
            for lm in landmarks
        ]
        
        # Extract features
        features = extract_features(landmarks_dict)
        features_tensor = torch.FloatTensor(features).unsqueeze(0)
        
        # Predict
        with torch.no_grad():
            confidence = self.model(features_tensor).item()
        
        is_spiderman = confidence >= self.threshold
        return is_spiderman, confidence


def main():
    # Paths
    script_dir = Path(__file__).parent
    model_path = script_dir / "model.pt"
    
    # Initialize
    try:
        classifier = FFNNClassifier(model_path)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return
    
    tracker = HandTracker()
    
    # Video capture
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("\n" + "=" * 50)
    print("FFNN Gesture Classifier - Real-Time")
    print("=" * 50)
    print("Controls:")
    print("  +/-  Adjust threshold")
    print("  p    Toggle pose detection")
    print("  q    Quit")
    print("=" * 50)
    
    show_pose = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        
        # Detect hands
        result = tracker.detect(frame)
        
        # Draw hand landmarks
        if result.hand_landmarks:
            for hand_landmarks in result.hand_landmarks:
                draw_hand_landmarks(frame, hand_landmarks)
                
                # Classify
                is_spiderman, confidence = classifier.predict(hand_landmarks)
                
                # Draw result
                if is_spiderman:
                    color = (0, 255, 0)  # Green
                    label = f"SPIDER-MAN! ({confidence:.1%})"
                    
                    # Draw border
                    cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), color, 10)
                else:
                    color = (0, 0, 255)  # Red
                    label = f"Not Spider-Man ({confidence:.1%})"
                
                # Draw label
                cv2.putText(
                    frame, label,
                    (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2, color, 3
                )
                
                # Confidence bar
                bar_width = int(confidence * 300)
                bar_color = (0, int(255 * confidence), int(255 * (1 - confidence)))
                cv2.rectangle(frame, (10, 60), (10 + bar_width, 80), bar_color, -1)
                cv2.rectangle(frame, (10, 60), (310, 80), (255, 255, 255), 2)
        
        # Draw threshold
        cv2.putText(
            frame, f"Threshold: {classifier.threshold:.2f}",
            (10, frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6, (255, 255, 255), 2
        )
        
        # Show frame
        cv2.imshow("FFNN Gesture Classifier", frame)
        
        # Handle input
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('+') or key == ord('='):
            classifier.threshold = min(0.99, classifier.threshold + 0.05)
            print(f"Threshold: {classifier.threshold:.2f}")
        elif key == ord('-'):
            classifier.threshold = max(0.01, classifier.threshold - 0.05)
            print(f"Threshold: {classifier.threshold:.2f}")
        elif key == ord('p'):
            show_pose = not show_pose
            print(f"Pose detection: {'ON' if show_pose else 'OFF'}")
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
