"""
Lightweight Coordinate Streamer - DETECTION ONLY.
All game logic (balls, webs, collisions) moved to React frontend.
"""
import sys
from pathlib import Path
import asyncio
import time
from typing import AsyncGenerator, Optional
import cv2

# Add parent project to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import from main project
from holistic_tracker import HolisticTracker
from shared_constants import FRAME_WIDTH, FRAME_HEIGHT

# Try to import gesture classifier
try:
    from ffnn_classifier.run_classifier import FFNNGestureClassifier
    HAS_CLASSIFIER = True
except ImportError:
    HAS_CLASSIFIER = False
    print("⚠️ FFNN classifier not available")


class LightweightStreamer:
    """
    Lightweight streamer - ONLY sends detection results.
    Game logic (symbiotes, webs, collisions) handled by React.
    """
    
    def __init__(self, video_streamer):
        self.video_streamer = video_streamer
        
        # Only detection - NO game logic
        self.tracker: Optional[HolisticTracker] = None
        self.gesture_classifier = None
        
        # Lazy initialization flag
        self._initialized = False
        
        # Performance metrics
        self.detection_times: list[float] = []
        self.avg_detection_time: float = 0
        self.frame_count: int = 0
    
    def _lazy_init(self):
        """Initialize detection components on first use."""
        if self._initialized:
            return
        
        print("🔧 Initializing lightweight tracker...")
        self.tracker = HolisticTracker()
        
        # Try to load gesture classifier
        if HAS_CLASSIFIER:
            try:
                self.gesture_classifier = FFNNGestureClassifier()
                print("✅ FFNN Gesture classifier loaded")
            except Exception as e:
                print(f"⚠️ Could not load gesture classifier: {e}")
                self.gesture_classifier = None
        
        self._initialized = True
        print("✅ Lightweight tracker initialized")
    
    async def generate_states(self) -> AsyncGenerator[dict, None]:
        """
        Generate MINIMAL detection data at best possible FPS.
        NO game logic - just raw detection results.
        """
        self._lazy_init()
        
        # Target higher FPS since we're doing less work
        target_fps = 60
        frame_time = 1.0 / target_fps
        
        while True:
            try:
                loop_start = time.time()
                
                # Get current frame from video streamer
                frame, frame_id, frame_timestamp = self.video_streamer.get_frame()
                
                if frame is None:
                    await asyncio.sleep(0.005)
                    continue
                
                # Flip frame (same as video stream)
                frame = cv2.flip(frame, 1)
                
                # Run detection
                detection_start = time.time()
                hand_result, pose_result = self._run_detection(frame)
                detection_time = (time.time() - detection_start) * 1000  # ms
                
                # Track detection time (rolling average)
                self.detection_times.append(detection_time)
                if len(self.detection_times) > 30:
                    self.detection_times.pop(0)
                self.avg_detection_time = sum(self.detection_times) / len(self.detection_times)
                
                self.frame_count += 1
                
                # Extract gesture info
                gesture_detected = False
                gesture_name = None
                gesture_confidence = 0.0
                
                if hand_result and hasattr(hand_result, 'hand_landmarks') and hand_result.hand_landmarks:
                    if self.gesture_classifier:
                        try:
                            gesture_name, gesture_confidence = self.gesture_classifier.predict(
                                hand_result.hand_landmarks
                            )
                            gesture_detected = gesture_name == "spiderman" and gesture_confidence > 0.7
                        except Exception:
                            pass
                
                # Build MINIMAL state JSON - only detection results
                state = {
                    # Timing
                    "frame_id": frame_id,
                    "timestamp": time.time() * 1000,
                    "detection_ms": round(detection_time, 1),
                    "avg_detection_ms": round(self.avg_detection_time, 1),
                    
                    # Hand detection (ONLY landmarks, no game logic)
                    "hand": self._extract_hand_minimal(hand_result),
                    
                    # Pose detection (for arm direction)
                    "pose": self._extract_pose_minimal(pose_result),
                    
                    # Gesture (for trigger detection in React)
                    "gesture": {
                        "detected": gesture_detected,
                        "name": gesture_name,
                        "confidence": round(gesture_confidence, 2) if gesture_confidence else 0,
                    },
                    
                    # Frame info
                    "frame_width": FRAME_WIDTH,
                    "frame_height": FRAME_HEIGHT,
                }
                
                yield state
                
                # Maintain target FPS
                elapsed = time.time() - loop_start
                sleep_time = max(0, frame_time - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
            except Exception as e:
                print(f"❌ Error in generate_states: {e}")
                await asyncio.sleep(0.05)
    
    def _run_detection(self, frame) -> tuple:
        """Run hand and pose detection."""
        if self.tracker is None:
            return None, None
        
        try:
            return self.tracker.detect_all(frame)
        except Exception as e:
            print(f"Detection error: {e}")
            return None, None
    
    def _extract_hand_minimal(self, hand_result) -> Optional[dict]:
        """Extract MINIMAL hand data - just landmarks."""
        if not hand_result:
            return None
        
        if not hasattr(hand_result, 'hand_landmarks') or not hand_result.hand_landmarks:
            return None
        
        # hand_landmarks is a List[list] - each element is a full hand's landmarks
        # We take the first detected hand
        first_hand_landmarks = hand_result.hand_landmarks[0]
        
        # Send landmarks as flat array for efficiency
        landmarks = []
        for lm in first_hand_landmarks:
            # Each landmark has x, y, z attributes (MediaPipe NormalizedLandmark)
            landmarks.append([
                round(lm.x, 4),
                round(lm.y, 4),
                round(lm.z, 4) if hasattr(lm, 'z') else 0,
            ])
        
        # Get handedness - also a list of lists
        handedness = 'Right'
        if hasattr(hand_result, 'handedness') and hand_result.handedness:
            first_handedness = hand_result.handedness[0]
            if first_handedness and len(first_handedness) > 0:
                handedness = first_handedness[0].category_name if hasattr(first_handedness[0], 'category_name') else 'Right'
        
        return {
            "landmarks": landmarks,
            "handedness": handedness,
        }
    
    def _extract_pose_minimal(self, pose_result) -> Optional[dict]:
        """Extract MINIMAL pose data - just wrist and elbow."""
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
