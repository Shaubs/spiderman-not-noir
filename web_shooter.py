#!/usr/bin/env python3
"""
Spider-Man Web Shooter - Main Application

Integrates:
- FFNN classifier for Spider-Man hand detection
- State machine for gesture sequence
- Web effect rendering with trajectory from elbow through wrist
- Symbiote ball enemies to shoot

Configuration:
    config.py - Web shooter and trigger settings
    symbiote_config.py - Enemy ball settings

Usage:
    python web_shooter.py

Controls:
    q - Quit
    r - Reset state machine
    g - Reset game (symbiotes)
    p - Toggle pose landmarks
    n - Toggle landmark numbers
    +/- - Adjust detection threshold
"""

import cv2
import time
import math
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

from hand_tracker import HandTracker
from gesture_state_machine import GestureStateMachine, StateConfig, GestureState
from ffnn_classifier.run_classifier import FFNNClassifier
from config import ACTIVE_CONFIG, GameConfig
from symbiote import SymbioteManager
from symbiote_config import ACTIVE_SYMBIOTE_CONFIG
from depth_config import ACTIVE_DEPTH_CONFIG


@dataclass
class WebLine:
    """A single line in the web spread."""
    start_x: int
    start_y: int
    end_x: int
    end_y: int


@dataclass
class WebShot:
    """Represents an active web shot effect (ADR-010: 3-line spread)."""
    start_x: int
    start_y: int
    # Center line
    center_end_x: int
    center_end_y: int
    # Side lines (±15° spread)
    left_end_x: int
    left_end_y: int
    right_end_x: int
    right_end_y: int
    # Timing
    created_at: float
    duration: float = ACTIVE_CONFIG.web_duration
    
    @property
    def age(self) -> float:
        return time.time() - self.created_at
    
    @property
    def is_expired(self) -> bool:
        return self.age > self.duration
    
    @property
    def progress(self) -> float:
        """0.0 to 1.0 representing web travel progress."""
        return min(1.0, self.age / self.duration)
    
    @property
    def opacity(self) -> float:
        """Fade out as web travels."""
        return max(0.0, 1.0 - (self.age / self.duration) ** 0.5)
    
    @property
    def thickness(self) -> int:
        """Start thick, end thin."""
        base_thickness = ACTIVE_CONFIG.web_thickness
        return max(1, int(base_thickness * (1.0 - self.progress * 0.8)))
    
    def get_lines(self) -> List[WebLine]:
        """Get all 3 web lines for collision detection."""
        return [
            WebLine(self.start_x, self.start_y, self.left_end_x, self.left_end_y),
            WebLine(self.start_x, self.start_y, self.center_end_x, self.center_end_y),
            WebLine(self.start_x, self.start_y, self.right_end_x, self.right_end_y),
        ]


class WebEffectRenderer:
    """Renders web shooting effects on video frames (ADR-010: 3-line spread)."""
    
    def __init__(self, depth_config=ACTIVE_DEPTH_CONFIG):
        self.active_webs: List[WebShot] = []
        self.depth_config = depth_config
    
    def shoot_web(self, elbow_x: int, elbow_y: int, 
                   wrist_x: int, wrist_y: int,
                   frame_width: int, frame_height: int) -> WebShot:
        """Create a new web shot with 3-line spread from elbow through wrist (ADR-010)."""
        # Calculate direction vector from elbow to wrist
        dx = wrist_x - elbow_x
        dy = wrist_y - elbow_y
        
        # Normalize
        length = math.sqrt(dx**2 + dy**2)
        if length > 0:
            dx /= length
            dy /= length
        
        # Center angle
        center_angle = math.atan2(dy, dx)
        
        # Get spread angles from depth config
        spread_rad = math.radians(self.depth_config.web_spread_angle)
        left_angle = center_angle - spread_rad
        right_angle = center_angle + spread_rad
        
        # Extend from elbow through wrist to frame boundary
        max_extend = max(frame_width, frame_height) * 2
        
        # Calculate end points for all 3 lines (starting from elbow, extending through wrist)
        center_end_x = int(elbow_x + math.cos(center_angle) * max_extend)
        center_end_y = int(elbow_y + math.sin(center_angle) * max_extend)
        
        left_end_x = int(elbow_x + math.cos(left_angle) * max_extend)
        left_end_y = int(elbow_y + math.sin(left_angle) * max_extend)
        
        right_end_x = int(elbow_x + math.cos(right_angle) * max_extend)
        right_end_y = int(elbow_y + math.sin(right_angle) * max_extend)
        
        web = WebShot(
            start_x=elbow_x,
            start_y=elbow_y,
            center_end_x=center_end_x,
            center_end_y=center_end_y,
            left_end_x=left_end_x,
            left_end_y=left_end_y,
            right_end_x=right_end_x,
            right_end_y=right_end_y,
            created_at=time.time()
        )
        self.active_webs.append(web)
        return web
    
    def update_and_render(self, frame: np.ndarray) -> np.ndarray:
        """Update web effects and render them on the frame."""
        self.active_webs = [w for w in self.active_webs if not w.is_expired]
        for web in self.active_webs:
            self._render_web(frame, web)
        return frame
    
    def _render_web(self, frame: np.ndarray, web: WebShot):
        """Render a 3-line web shot."""
        progress = web.progress
        alpha = int(255 * web.opacity)
        
        # Define all 3 lines with their end points
        lines = [
            (web.left_end_x, web.left_end_y),
            (web.center_end_x, web.center_end_y),
            (web.right_end_x, web.right_end_y),
        ]
        
        for end_x, end_y in lines:
            current_end_x = int(web.start_x + (end_x - web.start_x) * progress)
            current_end_y = int(web.start_y + (end_y - web.start_y) * progress)
            
            # Outer glow
            cv2.line(frame, 
                     (web.start_x, web.start_y), 
                     (current_end_x, current_end_y),
                     (alpha // 2, alpha // 2, alpha),
                     web.thickness + 2)
            
            # Main web line (white)
            cv2.line(frame,
                     (web.start_x, web.start_y),
                     (current_end_x, current_end_y),
                     (alpha, alpha, alpha),
                     web.thickness)
        
        # Origin point
        cv2.circle(frame, (web.start_x, web.start_y), 
                   web.thickness + 2, (0, 0, alpha), -1)


class SpiderManWebShooter:
    """Main web shooter application."""
    
    def __init__(self, config: GameConfig = ACTIVE_CONFIG):
        self.config = config
        self.depth_config = ACTIVE_DEPTH_CONFIG
        
        # Initialize components
        self.tracker = HandTracker(enable_pose=True)
        self.classifier = FFNNClassifier(
            model_path=Path(__file__).parent / "ffnn_classifier" / "model.pt",
            threshold=config.detection_threshold
        )
        self.web_renderer = WebEffectRenderer(self.depth_config)
        self.symbiote_manager = SymbioteManager(ACTIVE_SYMBIOTE_CONFIG, self.depth_config)
        
        # Configure state machine (ADR-009)
        state_config = StateConfig(
            toggle_count_threshold=config.toggle_count_threshold,
            toggle_window_seconds=config.toggle_window_seconds,
            upward_threshold=config.upward_threshold,
            sustained_hold_seconds=config.sustained_hold_seconds,
            cooldown_seconds=config.cooldown_seconds
        )
        self.state_machine = GestureStateMachine(state_config)
        
        # State
        self.trigger_count = 0
        self.show_pose = config.show_pose_landmarks
        self.show_numbers = config.show_landmark_numbers
        self.last_hand_landmarks = None
        self.last_pose_landmarks = None
        self.last_handedness = None  # 'Left' or 'Right'
        self.last_frame_size = None
        self.frame_count = 0
        
        # Register trigger callback
        self.state_machine.on_trigger(self._on_web_shoot)
    
    def _pose_to_dict(self, pose) -> dict:
        """Convert PoseLandmarks dataclass to dict for symbiote targeting."""
        pose_dict = {}
        
        # Map our PoseLandmarks attributes to standard MediaPipe indices
        mapping = {
            # Face
            'nose': 0,
            'left_eye': 2,
            'right_eye': 5,
            'left_ear': 7,
            'right_ear': 8,
            # Upper body
            'left_shoulder': 11,
            'right_shoulder': 12,
            'left_elbow': 13,
            'right_elbow': 14,
            'left_wrist': 15,
            'right_wrist': 16,
            # Lower body
            'left_hip': 23,
            'right_hip': 24,
            'left_knee': 25,
            'right_knee': 26,
        }
        
        for attr_name, idx in mapping.items():
            pt = getattr(pose, attr_name, None)
            if pt is not None:
                pose_dict[idx] = {'x': pt[0], 'y': pt[1], 'z': pt[2]}
        
        return pose_dict
    
    def _on_web_shoot(self):
        """Called when web shoot gesture is triggered."""
        self.trigger_count += 1
        
        if (self.last_hand_landmarks is not None and 
            self.last_pose_landmarks is not None and 
            self.last_frame_size is not None):
            
            landmarks = self.last_hand_landmarks
            pose = self.last_pose_landmarks
            h, w = self.last_frame_size
            
            # Get wrist from hand landmarks (more accurate)
            wrist = landmarks[0]
            wrist_x = int(wrist.x * w)
            wrist_y = int(wrist.y * h)
            
            # Get elbow from pose landmarks based on which hand
            elbow = None
            if self.last_handedness == 'Left':
                elbow = pose.left_elbow
            elif self.last_handedness == 'Right':
                elbow = pose.right_elbow
            
            if elbow is not None:
                elbow_x = int(elbow[0] * w)
                elbow_y = int(elbow[1] * h)
                
                # Web goes from elbow through wrist and extends outward
                self.web_renderer.shoot_web(
                    elbow_x=elbow_x,
                    elbow_y=elbow_y,
                    wrist_x=wrist_x,
                    wrist_y=wrist_y,
                    frame_width=w,
                    frame_height=h
                )
            else:
                print(f"⚠️  No elbow detected for {self.last_handedness} hand")
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process a single video frame."""
        h, w = frame.shape[:2]
        self.last_frame_size = (h, w)
        self.frame_count += 1
        
        # Detect hands and pose
        hand_results = self.tracker.detect(frame)
        pose_results = self.tracker.detect_pose(frame)
        
        # Convert PoseLandmarks dataclass to dict for symbiote targeting
        pose_landmarks_dict = None
        if pose_results:
            pose_landmarks_dict = self._pose_to_dict(pose_results)
        
        # Draw landmarks
        if self.show_pose:
            frame = self.tracker.draw_pose_landmarks(frame, pose_results, show_labels=True)
        frame = self.tracker.draw_landmarks(frame, hand_results, show_numbers=self.show_numbers)
        
        # Check for Spider-Man gesture
        spiderman_detected = False
        wrist_y = None
        confidence = 0.0
        
        if hand_results.hand_landmarks:
            for idx, hand_landmarks in enumerate(hand_results.hand_landmarks):
                is_spiderman, conf = self.classifier.predict(hand_landmarks)
                if is_spiderman:
                    spiderman_detected = True
                    confidence = conf
                    wrist_y = hand_landmarks[0].y
                    self.last_hand_landmarks = hand_landmarks
                    self.last_pose_landmarks = pose_results
                    # Get handedness (Left/Right)
                    if hand_results.handedness and idx < len(hand_results.handedness):
                        self.last_handedness = hand_results.handedness[idx][0].category_name
                    break
        
        # Update state machine
        current_state = self.state_machine.update(spiderman_detected, wrist_y)
        state_info = self.state_machine.get_state_info()
        state_color = self.state_machine.get_state_color()
        
        # Update symbiote balls
        hit_balls = self.symbiote_manager.update(w, h, pose_landmarks_dict)
        for ball in hit_balls:
            print(f"💀 HIT! Symbiote hit your {ball.hit_body_part}!")
        
        # Check web collisions with symbiotes (ADR-010: check all 3 lines)
        for web in self.web_renderer.active_webs:
            # Check center line
            destroyed = self.symbiote_manager.check_web_collision(
                web.start_x, web.start_y, web.center_end_x, web.center_end_y, web.progress
            )
            if not destroyed:
                # Check left line
                destroyed = self.symbiote_manager.check_web_collision(
                    web.start_x, web.start_y, web.left_end_x, web.left_end_y, web.progress
                )
            if not destroyed:
                # Check right line
                destroyed = self.symbiote_manager.check_web_collision(
                    web.start_x, web.start_y, web.right_end_x, web.right_end_y, web.progress
                )
            if destroyed:
                print(f"🕸️ THWACK! Ball destroyed! Total: {self.symbiote_manager.balls_destroyed}")
        
        # Render game elements
        frame = self.symbiote_manager.render_grayscale_effect(frame)  # ADR-010: Grayscale on hit
        frame = self.symbiote_manager.render(frame)
        frame = self.symbiote_manager.render_hit_markers(frame)
        frame = self.web_renderer.update_and_render(frame)
        
        # Draw UI
        frame = self._draw_ui(frame, current_state, state_info, state_color, 
                              confidence, spiderman_detected, wrist_y)
        
        return frame
    
    def _draw_ui(self, frame: np.ndarray, state: GestureState, 
                  state_info: dict, state_color: tuple,
                  confidence: float, detected: bool, wrist_y: Optional[float]) -> np.ndarray:
        """Draw UI overlay on frame."""
        h, w = frame.shape[:2]
        stats = self.symbiote_manager.get_stats()
        
        # Top bar with state
        cv2.rectangle(frame, (0, 0), (w, 50), state_color, -1)
        cv2.putText(frame, f"State: {state_info['state']}", (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        
        # Game stats
        stats_x = w // 2 - 100
        cv2.putText(frame, f"Destroyed: {stats['balls_destroyed']}", (stats_x, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 0), 2)
        cv2.putText(frame, f"Hits: {stats['hits_taken']}", (stats_x, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 150), 2)
        
        # Web count
        cv2.putText(frame, f"Webs: {self.trigger_count}", (w - 150, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        
        # Confidence bar
        if detected:
            bar_width = int(200 * confidence)
            cv2.rectangle(frame, (10, 55), (10 + bar_width, 70), (0, 255, 0), -1)
            cv2.rectangle(frame, (10, 55), (210, 70), (255, 255, 255), 1)
            cv2.putText(frame, f"{confidence:.1%}", (220, 68),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Trigger methods (right side)
        cfg = self.config
        toggle_count = state_info.get('toggle_count', 0)
        sustained_progress = state_info.get('sustained_progress', 0)
        
        checklist_x = w - 280
        checklist_y = 80
        cv2.putText(frame, "TRIGGERS:", (checklist_x, checklist_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        triggers = [
            (f"Flick ({toggle_count}/{cfg.toggle_count_threshold})", toggle_count >= cfg.toggle_count_threshold - 1),
            (f"UP ({cfg.upward_threshold:.0%})", False),
            (f"Hold ({sustained_progress:.0%})", sustained_progress > 0.5),
        ]
        
        for i, (label, active) in enumerate(triggers):
            y = checklist_y + 20 + i * 18
            color = (0, 255, 255) if active else (150, 150, 150)
            cv2.putText(frame, label, (checklist_x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Instructions
        y_offset = 100
        if state == GestureState.LOOKING:
            cv2.putText(frame, "Show Spider-Man hand", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        elif state == GestureState.DETECTED:
            cv2.putText(frame, "Flick, Move UP, or Hold to SHOOT!", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        elif state == GestureState.TRIGGERED:
            cv2.putText(frame, "THWIP!", (w//2 - 60, h//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 3)
        
        # Bottom info
        cv2.putText(frame, f"Webs: {len(self.web_renderer.active_webs)} | Symbiotes: {stats['active_balls']}", 
                    (10, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(frame, "q:quit r:reset g:reset-game p:pose +/-:threshold", 
                    (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        return frame
    
    def run(self):
        """Main application loop."""
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        
        cfg = self.config
        sym_cfg = ACTIVE_SYMBIOTE_CONFIG
        
        print("=" * 60)
        print("🕷️  SPIDER-MAN WEB SHOOTER")
        print("=" * 60)
        print(f"Trigger: {cfg.toggle_count_threshold} flicks / {cfg.sustained_hold_seconds}s hold")
        print(f"Symbiotes: spawn every {sym_cfg.spawn_interval}s, {sym_cfg.travel_time}s travel")
        print("")
        print("CONTROLS: q=quit r=reset g=reset-game p=pose +/-=threshold")
        print("=" * 60)
        
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            frame = cv2.flip(frame, 1)
            frame = self.process_frame(frame)
            cv2.imshow("Spider-Man Web Shooter", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.state_machine.reset()
                print("🔄 State machine reset")
            elif key == ord('g'):
                self.symbiote_manager.reset()
                self.trigger_count = 0
                print("🎮 Game reset")
            elif key == ord('p'):
                self.show_pose = not self.show_pose
            elif key == ord('n'):
                self.show_numbers = not self.show_numbers
            elif key in [ord('+'), ord('=')]:
                self.classifier.threshold = min(0.99, self.classifier.threshold + 0.05)
                print(f"🎯 Threshold: {self.classifier.threshold:.0%}")
            elif key == ord('-'):
                self.classifier.threshold = max(0.1, self.classifier.threshold - 0.05)
                print(f"🎯 Threshold: {self.classifier.threshold:.0%}")
        
        cap.release()
        cv2.destroyAllWindows()
        
        stats = self.symbiote_manager.get_stats()
        print("\n" + "=" * 60)
        print("📊 GAME OVER")
        print("=" * 60)
        print(f"  🕸️ Webs Shot: {self.trigger_count}")
        print(f"  💥 Symbiotes Destroyed: {stats['balls_destroyed']}")
        print(f"  💀 Hits Taken: {stats['hits_taken']}")
        print("=" * 60)


def main():
    app = SpiderManWebShooter()
    app.run()


if __name__ == "__main__":
    main()
