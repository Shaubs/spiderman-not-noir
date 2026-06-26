"""
Coordinate Streamer - Sends game state as JSON via WebSocket.
Uses existing trackers from the main project.
"""
import sys
from pathlib import Path
import asyncio
import time
import math
from typing import AsyncGenerator, Optional
import cv2

# Add parent project to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import from main project
from holistic_tracker import HolisticTracker
from gesture_state_machine import GestureStateMachine, GestureState
from symbiote import SymbioteManager
from shared_constants import (
    FRAME_WIDTH, FRAME_HEIGHT,
    WEB_SPREAD_ANGLE, WEB_LINE_COUNT
)

# Try to import gesture classifier
try:
    from ffnn_classifier.run_classifier import FFNNGestureClassifier
    HAS_CLASSIFIER = True
except ImportError:
    HAS_CLASSIFIER = False
    print("⚠️ FFNN classifier not available")


class CoordinateStreamer:
    """
    Extracts game coordinates and streams as JSON.
    Uses existing trackers but does NOT render any graphics.
    """
    
    def __init__(self, video_streamer):
        self.video_streamer = video_streamer
        
        # Initialize trackers (same as main game)
        self.tracker: Optional[HolisticTracker] = None
        self.state_machine: Optional[GestureStateMachine] = None
        self.symbiote_manager: Optional[SymbioteManager] = None
        self.gesture_classifier = None
        
        # Lazy initialization flag
        self._initialized = False
        
        # Performance metrics
        self.detection_times: list[float] = []
        self.avg_detection_time: float = 0
        
        # Game state
        self.score = {
            "webs_shot": 0,
            "balls_destroyed": 0,
            "hits_taken": 0,
            "combo": 0,
        }
        
        # Active web shots (for rendering, auto-expire)
        self.active_web_shots: list[dict] = []
        self.web_shot_duration = 0.5  # seconds
        
        # THWIP effect
        self.thwip_effect: Optional[dict] = None
        self.thwip_duration = 0.5  # seconds
        
        # Last wrist position for arm direction
        self.last_wrist_pos: Optional[tuple] = None
        self.last_elbow_pos: Optional[tuple] = None
    
    def _lazy_init(self):
        """Initialize heavy components on first use."""
        if self._initialized:
            return
        
        print("🔧 Initializing trackers...")
        self.tracker = HolisticTracker()
        self.state_machine = GestureStateMachine()
        self.symbiote_manager = SymbioteManager()
        
        # Try to load gesture classifier
        if HAS_CLASSIFIER:
            try:
                self.gesture_classifier = FFNNGestureClassifier()
                print("✅ FFNN Gesture classifier loaded")
            except Exception as e:
                print(f"⚠️ Could not load gesture classifier: {e}")
                self.gesture_classifier = None
        
        self._initialized = True
        print("✅ Trackers initialized")
    
    async def generate_states(self) -> AsyncGenerator[dict, None]:
        """
        Generate game state JSON at ~30fps.
        Yields coordinate data for frontend rendering.
        """
        self._lazy_init()
        
        target_fps = 30  # Reduced for stability
        frame_time = 1.0 / target_fps
        
        while True:
            try:
                loop_start = time.time()
                
                # Get current frame from video streamer
                frame, frame_id, frame_timestamp = self.video_streamer.get_frame()
                
                if frame is None:
                    await asyncio.sleep(0.01)
                    continue
                
                # Flip frame (same as video stream)
                frame = cv2.flip(frame, 1)
                
                # Run detection
                detection_start = time.time()
                hand_result, pose_result = self._run_detection(frame)
                detection_time = (time.time() - detection_start) * 1000  # ms
                
                # Track detection time
                self.detection_times.append(detection_time)
                if len(self.detection_times) > 60:
                    self.detection_times.pop(0)
                self.avg_detection_time = sum(self.detection_times) / len(self.detection_times)
                
                # Process gesture and state machine
                gesture_detected = False
                gesture_name = None
                wrist_y = None
                
                if hand_result and hasattr(hand_result, 'hand_landmarks') and hand_result.hand_landmarks:
                    # Get wrist position for state machine
                    wrist = hand_result.hand_landmarks[0]  # Landmark 0 is wrist
                    wrist_y = wrist.y
                    
                    # Store wrist/elbow for web direction
                    self.last_wrist_pos = (wrist.x, wrist.y)
                    
                    # Check gesture using classifier
                    if self.gesture_classifier:
                        try:
                            gesture_name, confidence = self.gesture_classifier.predict(
                                hand_result.hand_landmarks
                            )
                            gesture_detected = gesture_name == "spiderman" and confidence > 0.7
                        except Exception as e:
                            print(f"Gesture classification error: {e}")
                
                # Extract pose for elbow position
                if pose_result:
                    if hasattr(pose_result, 'right_wrist') and pose_result.right_wrist:
                        if hasattr(pose_result, 'right_elbow') and pose_result.right_elbow:
                            self.last_elbow_pos = (
                                pose_result.right_elbow.x if hasattr(pose_result.right_elbow, 'x') 
                                else pose_result.right_elbow[0],
                                pose_result.right_elbow.y if hasattr(pose_result.right_elbow, 'y')
                                else pose_result.right_elbow[1]
                            )
                
                # Update state machine
                prev_state = self.state_machine.state if self.state_machine else None
                if self.state_machine:
                    self.state_machine.update(gesture_detected, wrist_y)
                
                # Check for trigger - fire web!
                triggered = (
                    prev_state != GestureState.TRIGGERED and 
                    self.state_machine and 
                    self.state_machine.state == GestureState.TRIGGERED
                )
                
                if triggered:
                    self._fire_web()
                
                # Update symbiotes with frame dimensions
                hit_balls = self.symbiote_manager.update(FRAME_WIDTH, FRAME_HEIGHT)
                
                # Track hits taken
                if hit_balls:
                    self.score["hits_taken"] += len(hit_balls)
                    self.score["combo"] = 0
                
                # Clean up expired web shots
                self._cleanup_web_shots()
                
                # Clean up expired THWIP effect
                self._cleanup_thwip()
                
                # Check for web-ball collisions
                self._check_web_collisions()
                
                # Build state JSON
                state = {
                    # Timing info for latency measurement
                    "frame_id": frame_id,
                    "frame_timestamp": frame_timestamp * 1000,  # Convert to ms
                    "server_timestamp": time.time() * 1000,     # Current server time in ms
                    "detection_time_ms": round(detection_time, 2),
                    "avg_detection_time_ms": round(self.avg_detection_time, 2),
                    
                    # Game entities
                    "hand": self._extract_hand(hand_result, gesture_name),
                    "pose": self._extract_pose(pose_result),
                    "symbiotes": self._extract_symbiotes(),
                    "web_shots": self.active_web_shots.copy(),
                    
                    # Effects
                    "thwip": self.thwip_effect,
                    
                    # Game state
                    "score": self.score.copy(),
                    "state": self.state_machine.state.name if self.state_machine else "UNKNOWN",
                    "gesture_detected": gesture_detected,
                    "gesture_name": gesture_name,
                    
                    # Frame dimensions
                    "frame_width": FRAME_WIDTH,
                    "frame_height": FRAME_HEIGHT,
                }
                
                yield state
                
                # Maintain target FPS
                elapsed = time.time() - loop_start
                sleep_time = max(0, frame_time - elapsed)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                print(f"❌ Error in generate_states loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(0.1)  # Brief pause before retry
    
    def _fire_web(self):
        """Create a new web shot when triggered."""
        if not self.last_wrist_pos:
            return
        
        start_x, start_y = self.last_wrist_pos
        
        # Calculate web direction (from elbow to wrist, extended)
        if self.last_elbow_pos:
            dx = start_x - self.last_elbow_pos[0]
            dy = start_y - self.last_elbow_pos[1]
        else:
            # Default: shoot upward-right
            dx = 0.3
            dy = -0.5
        
        # Normalize direction
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            dx /= length
            dy /= length
        
        # Create web lines with spread
        lines = []
        base_angle = math.atan2(dy, dx)
        web_length = 0.4  # Normalized length
        
        for i in range(WEB_LINE_COUNT):
            angle_offset = (i - WEB_LINE_COUNT // 2) * math.radians(WEB_SPREAD_ANGLE)
            angle = base_angle + angle_offset
            
            end_x = start_x + math.cos(angle) * web_length
            end_y = start_y + math.sin(angle) * web_length
            
            lines.append({
                "end": {"x": round(end_x, 4), "y": round(end_y, 4)},
                "angle": round(math.degrees(angle), 1)
            })
        
        # Add web shot
        web_shot = {
            "id": f"web_{time.time()}",
            "start": {"x": round(start_x, 4), "y": round(start_y, 4)},
            "lines": lines,
            "alpha": 255,
            "created_at": time.time(),
        }
        self.active_web_shots.append(web_shot)
        self.score["webs_shot"] += 1
        
        # Create THWIP effect at web origin
        self.thwip_effect = {
            "x": round(start_x, 4),
            "y": round(start_y, 4),
            "created_at": time.time(),
        }
        
        print(f"🕸️ Web fired! Start: ({start_x:.2f}, {start_y:.2f})")
    
    def _cleanup_web_shots(self):
        """Remove expired web shots."""
        now = time.time()
        self.active_web_shots = [
            web for web in self.active_web_shots
            if now - web["created_at"] < self.web_shot_duration
        ]
        
        # Update alpha based on age
        for web in self.active_web_shots:
            age = now - web["created_at"]
            progress = age / self.web_shot_duration
            web["alpha"] = int(255 * (1 - progress))
    
    def _cleanup_thwip(self):
        """Remove expired THWIP effect."""
        if self.thwip_effect:
            age = time.time() - self.thwip_effect["created_at"]
            if age >= self.thwip_duration:
                self.thwip_effect = None
            else:
                self.thwip_effect["age"] = round(age / self.thwip_duration, 2)
    
    def _check_web_collisions(self):
        """Check if any web shots hit symbiote balls."""
        if not self.symbiote_manager:
            return
        
        for web in self.active_web_shots:
            for ball in self.symbiote_manager.active_balls:
                if ball.is_destroyed:
                    continue
                
                # Get ball position in normalized coords
                ball_x = ball.current_x / FRAME_WIDTH
                ball_y = ball.current_y / FRAME_HEIGHT
                ball_radius = ball.current_size / FRAME_WIDTH  # Rough normalization
                
                # Check each web line
                for line in web["lines"]:
                    # Simple point-to-line distance check
                    start = web["start"]
                    end = line["end"]
                    
                    # Check if ball center is near the line
                    dist = self._point_to_segment_distance(
                        ball_x, ball_y,
                        start["x"], start["y"],
                        end["x"], end["y"]
                    )
                    
                    if dist < ball_radius + 0.02:  # Hit!
                        ball.is_destroyed = True
                        ball.destroyed_at = time.time()
                        self.score["balls_destroyed"] += 1
                        self.score["combo"] += 1
                        
                        # Create THWIP at ball position
                        self.thwip_effect = {
                            "x": round(ball_x, 4),
                            "y": round(ball_y, 4),
                            "created_at": time.time(),
                        }
                        print(f"💥 Ball destroyed! Combo: {self.score['combo']}")
                        break
    
    def _point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        """Calculate distance from point to line segment."""
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)))
        
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        
        return math.sqrt((px - proj_x)**2 + (py - proj_y)**2)
    
    def _run_detection(self, frame) -> tuple:
        """Run hand and pose detection."""
        if self.tracker is None:
            return None, None
        
        try:
            hand_result, pose_result = self.tracker.detect_all(frame)
            return hand_result, pose_result
        except Exception as e:
            print(f"Detection error: {e}")
            return None, None
    
    def _extract_hand(self, hand_result, gesture_name: Optional[str] = None) -> Optional[dict]:
        """Extract hand landmarks as normalized coordinates."""
        if not hand_result:
            return None
        
        if not hasattr(hand_result, 'hand_landmarks') or not hand_result.hand_landmarks:
            return None
        
        landmarks = []
        for lm in hand_result.hand_landmarks:
            landmarks.append({
                "x": round(lm.x, 4),
                "y": round(lm.y, 4),
                "z": round(lm.z, 4) if hasattr(lm, 'z') else 0,
            })
        
        return {
            "detected": True,
            "landmarks": landmarks,
            "handedness": getattr(hand_result, 'handedness', 'Unknown'),
            "gesture": gesture_name,
            "confidence": getattr(hand_result, 'confidence', 0),
        }
    
    def _extract_pose(self, pose_result) -> Optional[dict]:
        """Extract pose landmarks for arm tracking."""
        if not pose_result:
            return None
        
        def point_to_dict(point) -> Optional[dict]:
            if point is None:
                return None
            if hasattr(point, 'x'):
                return {"x": round(point.x, 4), "y": round(point.y, 4)}
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                return {"x": round(point[0], 4), "y": round(point[1], 4)}
            return None
        
        return {
            "left_elbow": point_to_dict(getattr(pose_result, 'left_elbow', None)),
            "right_elbow": point_to_dict(getattr(pose_result, 'right_elbow', None)),
            "left_wrist": point_to_dict(getattr(pose_result, 'left_wrist', None)),
            "right_wrist": point_to_dict(getattr(pose_result, 'right_wrist', None)),
        }
    
    def _extract_symbiotes(self) -> list[dict]:
        """Extract symbiote ball positions."""
        if not self.symbiote_manager:
            return []
        
        balls = []
        for ball in self.symbiote_manager.active_balls:
            if ball.is_destroyed:
                continue
            balls.append({
                "id": str(id(ball)),
                "x": round(ball.current_x / FRAME_WIDTH, 4),
                "y": round(ball.current_y / FRAME_HEIGHT, 4),
                "size": int(ball.current_size),
                "progress": round(ball.progress, 3),
            })
        return balls
