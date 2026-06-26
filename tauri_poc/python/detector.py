"""
Python Sidecar for Tauri - Camera capture and hand detection.
Outputs JSON-L to stdout for Rust to consume.
"""
import sys
import json
import time
import base64
import signal
from pathlib import Path

import cv2
import numpy as np

# Add parent project to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import from main project
try:
    from holistic_tracker import HolisticTracker
    HAS_TRACKER = True
except ImportError:
    HAS_TRACKER = False
    print(json.dumps({"type": "error", "message": "HolisticTracker not available"}), flush=True)

# Import gesture state machine
try:
    from gesture_state_machine import GestureStateMachine
    HAS_STATE_MACHINE = True
except ImportError:
    HAS_STATE_MACHINE = False

# Try to import gesture classifier
try:
    from ffnn_classifier.run_classifier import FFNNGestureClassifier
    HAS_CLASSIFIER = True
except ImportError:
    HAS_CLASSIFIER = False


class Detector:
    """Main detector class - captures camera, runs detection, outputs JSON."""
    
    def __init__(self):
        self.running = True
        self.cap = None
        self.tracker = None
        self.classifier = None
        self.state_machine = None
        
        # Performance tracking
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
        
        # Frame settings
        self.frame_width = 1280
        self.frame_height = 720
        self.jpeg_quality = 70  # Lower = smaller, faster
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.running = False
    
    def _output(self, data: dict):
        """Output JSON line to stdout."""
        print(json.dumps(data), flush=True)
    
    def _init_camera(self) -> bool:
        """Initialize camera."""
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self._output({"type": "error", "message": "Failed to open camera"})
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self._output({
            "type": "status",
            "message": f"Camera initialized: {actual_w}x{actual_h}"
        })
        
        return True
    
    def _init_tracker(self) -> bool:
        """Initialize MediaPipe tracker."""
        if not HAS_TRACKER:
            self._output({"type": "warning", "message": "Tracker not available"})
            return False
        
        try:
            self.tracker = HolisticTracker()
            self._output({"type": "status", "message": "Tracker initialized"})
            return True
        except Exception as e:
            self._output({"type": "error", "message": f"Tracker init failed: {e}"})
            return False
    
    def _init_classifier(self):
        """Initialize gesture classifier."""
        if not HAS_CLASSIFIER:
            return
        
        try:
            self.classifier = FFNNGestureClassifier()
            self._output({"type": "status", "message": "Classifier loaded"})
        except Exception as e:
            self._output({"type": "warning", "message": f"Classifier not loaded: {e}"})
    
    def _init_state_machine(self):
        """Initialize gesture state machine."""
        if not HAS_STATE_MACHINE:
            return
        
        try:
            self.state_machine = GestureStateMachine()
            self._output({"type": "status", "message": "State machine initialized"})
        except Exception as e:
            self._output({"type": "warning", "message": f"State machine not loaded: {e}"})
    
    def _frame_to_base64(self, frame: np.ndarray) -> str:
        """Convert frame to base64 JPEG."""
        # Flip horizontally (mirror)
        frame = cv2.flip(frame, 1)
        
        # Encode as JPEG
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
        _, buffer = cv2.imencode('.jpg', frame, encode_params)
        
        # Convert to base64
        return base64.b64encode(buffer).decode('utf-8')
    
    def _extract_landmarks(self, hand_result) -> list | None:
        """Extract hand landmarks as list of [x, y, z]."""
        if not hand_result:
            return None
        
        if not hasattr(hand_result, 'hand_landmarks') or not hand_result.hand_landmarks:
            return None
        
        # hand_landmarks is List[list] - take first hand
        first_hand = hand_result.hand_landmarks[0]
        
        landmarks = []
        for lm in first_hand:
            landmarks.append([
                round(lm.x, 4),
                round(lm.y, 4),
                round(lm.z, 4) if hasattr(lm, 'z') else 0
            ])
        
        return landmarks
    
    def _extract_pose(self, pose_result) -> dict | None:
        """Extract pose landmarks (wrists and elbows)."""
        if not pose_result:
            return None
        
        def get_point(attr_name):
            point = getattr(pose_result, attr_name, None)
            if point is None:
                return None
            if hasattr(point, 'x'):
                return [round(point.x, 4), round(point.y, 4)]
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                return [round(point[0], 4), round(point[1], 4)]
            return None
        
        return {
            "right_wrist": get_point('right_wrist'),
            "right_elbow": get_point('right_elbow'),
            "left_wrist": get_point('left_wrist'),
            "left_elbow": get_point('left_elbow'),
        }
    
    def _classify_gesture(self, hand_result) -> tuple[str | None, float]:
        """Classify the hand gesture."""
        if not self.classifier or not hand_result:
            return None, 0.0
        
        if not hasattr(hand_result, 'hand_landmarks') or not hand_result.hand_landmarks:
            return None, 0.0
        
        try:
            gesture, confidence = self.classifier.predict(hand_result.hand_landmarks)
            return gesture, confidence
        except Exception:
            return None, 0.0
    
    def _update_fps(self):
        """Update FPS calculation."""
        self.frame_count += 1
        elapsed = time.time() - self.fps_start_time
        
        if elapsed >= 1.0:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.fps_start_time = time.time()
    
    def run(self):
        """Main detection loop."""
        # Initialize components
        if not self._init_camera():
            return
        
        self._init_tracker()
        self._init_classifier()
        self._init_state_machine()
        
        self._output({"type": "ready", "message": "Detector ready"})
        
        # Main loop
        while self.running:
            loop_start = time.time()
            
            # Capture frame
            ret, frame = self.cap.read()
            if not ret:
                self._output({"type": "error", "message": "Failed to read frame"})
                time.sleep(0.1)
                continue
            
            # Convert frame to base64 and emit
            frame_b64 = self._frame_to_base64(frame)
            self._output({
                "type": "frame",
                "data": frame_b64,
                "timestamp": int(time.time() * 1000)
            })
            
            # Run detection if tracker available
            if self.tracker:
                # Flip frame for detection (same as display)
                detect_frame = cv2.flip(frame, 1)
                
                detection_start = time.time()
                hand_result, pose_result = self.tracker.detect_all(detect_frame)
                detection_ms = (time.time() - detection_start) * 1000
                
                # Extract data
                landmarks = self._extract_landmarks(hand_result)
                pose = self._extract_pose(pose_result)
                
                # Classify gesture
                gesture_name, confidence = self._classify_gesture(hand_result)
                is_spiderman = gesture_name == "spiderman" and confidence > 0.7
                
                # Get handedness
                handedness = "Right"
                if hand_result and hasattr(hand_result, 'handedness') and hand_result.handedness:
                    first_handedness = hand_result.handedness[0]
                    if first_handedness and len(first_handedness) > 0:
                        handedness = getattr(first_handedness[0], 'category_name', 'Right')
                
                # Update state machine
                trigger_fired = False
                state = "LOOKING"
                if self.state_machine and landmarks:
                    wrist = landmarks[0] if landmarks else None
                    wrist_pos = (wrist[0], wrist[1]) if wrist else None
                    trigger_fired = self.state_machine.update(is_spiderman, wrist_pos)
                    state = self.state_machine.state
                
                # Emit detection data
                self._output({
                    "type": "detection",
                    "timestamp": int(time.time() * 1000),
                    "detection_ms": round(detection_ms, 1),
                    "hand": {
                        "detected": landmarks is not None,
                        "landmarks": landmarks,
                        "handedness": handedness
                    } if landmarks else None,
                    "pose": pose,
                    "gesture": {
                        "name": gesture_name,
                        "confidence": round(confidence, 2) if confidence else 0,
                        "is_spiderman": is_spiderman
                    },
                    "state": state,
                    "trigger_fired": trigger_fired
                })
            
            # Update FPS
            self._update_fps()
            
            # Emit periodic stats
            if self.frame_count == 0:  # Once per second
                self._output({
                    "type": "stats",
                    "fps": round(self.current_fps, 1),
                    "frame_width": self.frame_width,
                    "frame_height": self.frame_height
                })
            
            # Rate limiting - target ~30fps
            elapsed = time.time() - loop_start
            sleep_time = max(0, (1/30) - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Cleanup
        if self.cap:
            self.cap.release()
        
        self._output({"type": "shutdown", "message": "Detector stopped"})


if __name__ == "__main__":
    detector = Detector()
    detector.run()
