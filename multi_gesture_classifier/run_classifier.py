#!/usr/bin/env python3
"""
Multi-Gesture Classifier Runtime

Loads the trained multi-gesture model and provides inference.
Detects: Spider-Man, Dr. Strange, and None gestures.

This is completely independent from the Spider-Man game code.
"""

import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class GestureResult:
    """Result of gesture detection."""
    gesture: str           # 'spiderman', 'dr_strange', or 'none'
    confidence: float      # Confidence score (0.0 to 1.0)
    all_probs: Dict[str, float]  # Probabilities for all classes


class MultiGestureNet(nn.Module):
    """
    Feed Forward Neural Network for multi-gesture classification.
    Must match the architecture used in training.
    """
    
    def __init__(self, input_size=82, num_classes=3):
        super(MultiGestureNet, self).__init__()
        
        self.network = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.2),
            
            nn.Linear(32, num_classes),
        )
    
    def forward(self, x):
        return self.network(x)


class MultiGestureClassifier:
    """
    Runtime classifier for multiple gesture detection.
    
    Usage:
        classifier = MultiGestureClassifier()
        result = classifier.predict(hand_landmarks)
        
        if result.gesture == 'spiderman':
            print(f"Spider-Man detected with {result.confidence:.0%} confidence!")
        elif result.gesture == 'dr_strange':
            print(f"Dr. Strange detected with {result.confidence:.0%} confidence!")
    """
    
    # Default thresholds for each gesture
    DEFAULT_THRESHOLDS = {
        'spiderman': 0.7,
        'dr_strange': 0.7,
    }
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize the classifier.
        
        Args:
            model_path: Path to the trained model file. If None, uses default.
            thresholds: Per-gesture confidence thresholds. If None, uses defaults.
        """
        if model_path is None:
            model_path = Path(__file__).parent / "multi_gesture_model.pt"
        
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.copy()
        
        # Load model
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Please run train.py first to train the model."
            )
        
        checkpoint = torch.load(model_path, map_location='cpu')
        
        self.input_size = checkpoint.get('input_size', 82)
        self.num_classes = checkpoint.get('num_classes', 3)
        self.class_names = checkpoint.get('class_names', {0: 'none', 1: 'spiderman', 2: 'dr_strange'})
        self.gesture_classes = checkpoint.get('gesture_classes', {'none': 0, 'spiderman': 1, 'dr_strange': 2})
        
        self.model = MultiGestureNet(
            input_size=self.input_size,
            num_classes=self.num_classes
        )
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        print(f"✅ Loaded multi-gesture model from {model_path}")
        print(f"   Classes: {list(self.class_names.values())}")
        print(f"   Accuracy: {checkpoint.get('accuracy', 'N/A'):.2%}")
    
    def _extract_features(self, landmarks) -> np.ndarray:
        """Extract features from hand landmarks."""
        # Handle different input formats
        if hasattr(landmarks, '__iter__') and hasattr(landmarks[0], 'x'):
            # MediaPipe NormalizedLandmark objects
            landmarks_list = [{'x': lm.x, 'y': lm.y, 'z': lm.z} for lm in landmarks]
        elif isinstance(landmarks[0], dict):
            # Already dict format
            landmarks_list = landmarks
        else:
            raise ValueError("Unsupported landmarks format")
        
        # Raw coordinates (63 features)
        coords = []
        for lm in landmarks_list:
            coords.extend([lm['x'], lm['y'], lm['z']])
        
        # Derived features (19 features)
        derived = []
        
        wrist = landmarks_list[0]
        middle_mcp = landmarks_list[9]
        palm_orientation = wrist['y'] - middle_mcp['y']
        derived.append(palm_orientation)
        
        finger_tips = [4, 8, 12, 16, 20]
        finger_mcps = [2, 5, 9, 13, 17]
        
        for tip_idx, mcp_idx in zip(finger_tips, finger_mcps):
            tip = landmarks_list[tip_idx]
            mcp = landmarks_list[mcp_idx]
            extension = tip['y'] - mcp['y']
            derived.append(extension)
        
        for tip_idx, mcp_idx in zip(finger_tips, finger_mcps):
            tip = landmarks_list[tip_idx]
            mcp = landmarks_list[mcp_idx]
            curl = np.sqrt(
                (tip['x'] - mcp['x'])**2 + 
                (tip['y'] - mcp['y'])**2 + 
                (tip['z'] - mcp['z'])**2
            )
            derived.append(curl)
        
        palm_center_x = np.mean([landmarks_list[i]['x'] for i in [0, 5, 9, 13, 17]])
        palm_center_y = np.mean([landmarks_list[i]['y'] for i in [0, 5, 9, 13, 17]])
        palm_center_z = np.mean([landmarks_list[i]['z'] for i in [0, 5, 9, 13, 17]])
        
        fingertip_distances = []
        for tip_idx in finger_tips:
            tip = landmarks_list[tip_idx]
            dist = np.sqrt(
                (tip['x'] - palm_center_x)**2 +
                (tip['y'] - palm_center_y)**2 +
                (tip['z'] - palm_center_z)**2
            )
            fingertip_distances.append(dist)
        hand_openness = np.mean(fingertip_distances)
        derived.append(hand_openness)
        
        thumb_tip = landmarks_list[4]
        pinky_tip = landmarks_list[20]
        thumb_pinky_dist = np.sqrt(
            (thumb_tip['x'] - pinky_tip['x'])**2 +
            (thumb_tip['y'] - pinky_tip['y'])**2 +
            (thumb_tip['z'] - pinky_tip['z'])**2
        )
        derived.append(thumb_pinky_dist)
        
        index_tip = landmarks_list[8]
        index_vec = np.array([index_tip['x'] - wrist['x'], index_tip['y'] - wrist['y']])
        pinky_vec = np.array([pinky_tip['x'] - wrist['x'], pinky_tip['y'] - wrist['y']])
        
        index_norm = np.linalg.norm(index_vec)
        pinky_norm = np.linalg.norm(pinky_vec)
        
        if index_norm > 0 and pinky_norm > 0:
            cos_angle = np.dot(index_vec, pinky_vec) / (index_norm * pinky_norm)
            cos_angle = np.clip(cos_angle, -1, 1)
            index_pinky_angle = np.arccos(cos_angle)
        else:
            index_pinky_angle = 0
        derived.append(index_pinky_angle)
        
        index_mcp = landmarks_list[5]
        pinky_mcp = landmarks_list[17]
        wrist_angle = np.arctan2(
            pinky_mcp['y'] - index_mcp['y'],
            pinky_mcp['x'] - index_mcp['x']
        )
        derived.append(wrist_angle)
        
        z_values = [lm['z'] for lm in landmarks_list]
        z_variance = np.var(z_values)
        derived.append(z_variance)
        
        v1 = np.array([
            index_mcp['x'] - wrist['x'],
            index_mcp['y'] - wrist['y'],
            index_mcp['z'] - wrist['z']
        ])
        v2 = np.array([
            pinky_mcp['x'] - wrist['x'],
            pinky_mcp['y'] - wrist['y'],
            pinky_mcp['z'] - wrist['z']
        ])
        palm_normal = np.cross(v1, v2)
        palm_normal_norm = np.linalg.norm(palm_normal)
        if palm_normal_norm > 0:
            palm_normal = palm_normal / palm_normal_norm
        derived.extend(palm_normal.tolist())
        
        all_features = coords + derived
        return np.array(all_features, dtype=np.float32)
    
    def predict(self, landmarks) -> GestureResult:
        """
        Predict gesture from hand landmarks.
        
        Args:
            landmarks: Hand landmarks (21 points) - either MediaPipe format or dict list
            
        Returns:
            GestureResult with gesture name, confidence, and all probabilities
        """
        features = self._extract_features(landmarks)
        features_tensor = torch.FloatTensor(features).unsqueeze(0)
        
        with torch.no_grad():
            logits = self.model(features_tensor)
            probs = torch.softmax(logits, dim=1).squeeze().numpy()
        
        # Get all probabilities
        all_probs = {self.class_names[i]: float(probs[i]) for i in range(len(probs))}
        
        # Find best matching gesture above threshold
        best_gesture = 'none'
        best_confidence = probs[self.gesture_classes['none']]
        
        for gesture_name in ['spiderman', 'dr_strange']:
            class_idx = self.gesture_classes[gesture_name]
            prob = probs[class_idx]
            threshold = self.thresholds.get(gesture_name, 0.7)
            
            if prob > threshold and prob > best_confidence:
                best_gesture = gesture_name
                best_confidence = prob
        
        return GestureResult(
            gesture=best_gesture,
            confidence=best_confidence,
            all_probs=all_probs
        )
    
    def predict_spiderman(self, landmarks) -> Tuple[bool, float]:
        """
        Check specifically for Spider-Man gesture.
        
        Returns:
            Tuple of (is_spiderman, confidence)
        """
        result = self.predict(landmarks)
        is_spiderman = result.gesture == 'spiderman'
        confidence = result.all_probs.get('spiderman', 0.0)
        return is_spiderman, confidence
    
    def predict_dr_strange(self, landmarks) -> Tuple[bool, float]:
        """
        Check specifically for Dr. Strange gesture.
        
        Returns:
            Tuple of (is_dr_strange, confidence)
        """
        result = self.predict(landmarks)
        is_dr_strange = result.gesture == 'dr_strange'
        confidence = result.all_probs.get('dr_strange', 0.0)
        return is_dr_strange, confidence


# Demo/test function
def demo():
    """Run a demo with webcam input."""
    import cv2
    from tracking import HandTracker
    
    print("🔮 Multi-Gesture Classifier Demo")
    print("=" * 50)
    print("Detecting: Spider-Man 🕷️ and Dr. Strange 🔮")
    print("Press 'q' to quit")
    print()
    
    # Initialize
    classifier = MultiGestureClassifier()
    tracker = HandTracker()
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        results = tracker.detect(frame)
        
        if results.hand_landmarks:
            for hand_landmarks in results.hand_landmarks:
                # Predict gesture
                result = classifier.predict(hand_landmarks)
                
                # Draw hand
                for lm in hand_landmarks:
                    x = int(lm.x * frame.shape[1])
                    y = int(lm.y * frame.shape[0])
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
                
                # Display result
                if result.gesture == 'spiderman':
                    color = (0, 0, 255)  # Red
                    text = f"SPIDER-MAN {result.confidence:.0%}"
                elif result.gesture == 'dr_strange':
                    color = (255, 165, 0)  # Orange
                    text = f"DR. STRANGE {result.confidence:.0%}"
                else:
                    color = (128, 128, 128)  # Gray
                    text = f"None"
                
                cv2.putText(frame, text, (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)
                
                # Show all probabilities
                y_offset = 100
                for gesture, prob in result.all_probs.items():
                    prob_text = f"{gesture}: {prob:.0%}"
                    cv2.putText(frame, prob_text, (50, y_offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    y_offset += 25
        
        cv2.imshow("Multi-Gesture Classifier", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    demo()
