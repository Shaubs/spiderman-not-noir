"""
Web Shooter Base - Shared application logic for web shooter variants.

Contains:
- BaseWebShooter: Common functionality for landmark and glove modes
- Tracker initialization
- Gesture detection and state machine
- Symbiote management
- Web collision detection
- UI rendering helpers

Subclassed by web_shooter.py (landmarks) and web_shooter_glove.py (glove)
"""

import cv2
import sys
import numpy as np
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod

from tracking import GestureStateMachine, StateConfig, GestureState
from classifiers import FFNNClassifier
from config import ACTIVE_CONFIG, GameConfig, ACTIVE_SYMBIOTE_CONFIG, ACTIVE_DEPTH_CONFIG, Scoreboard, ACTIVE_SCORE_CONFIG
from game_mechanics.enemies import SymbioteManager, InfectionManager
from rendering import GraphicsManager, WebEffectRenderer

# Tracker selection based on --fast flag
USE_HOLISTIC = '--fast' in sys.argv

if USE_HOLISTIC:
    from tracking import HolisticTracker as Tracker
else:
    from tracking import HandTracker as Tracker


# Pose landmark mapping (MediaPipe indices)
POSE_MAPPING = {
    'nose': 0, 'left_eye': 2, 'right_eye': 5, 'left_ear': 7, 'right_ear': 8,
    'left_shoulder': 11, 'right_shoulder': 12, 'left_elbow': 13, 'right_elbow': 14,
    'left_wrist': 15, 'right_wrist': 16, 'left_hip': 23, 'right_hip': 24,
    'left_knee': 25, 'right_knee': 26,
}


class BaseWebShooter(ABC):
    """
    Base class for Spider-Man web shooter application.
    
    Handles common functionality:
    - Tracker initialization (hand + pose)
    - FFNN classifier for gesture detection
    - State machine for trigger mechanics
    - Symbiote enemy management
    - Web collision detection
    - THWIP effects
    
    Subclasses implement:
    - draw_hand(): How to render the hand (landmarks vs glove)
    - get_controls_text(): Control hints for the mode
    - get_window_title(): Window title
    """
    
    def __init__(self, config: GameConfig = ACTIVE_CONFIG):
        self.config = config
        self.depth_config = ACTIVE_DEPTH_CONFIG
        
        # Initialize tracker
        if USE_HOLISTIC:
            self.tracker = Tracker(pose_frame_skip=2)
        else:
            self.tracker = Tracker(enable_pose=True)
        
        # Classifier
        self.classifier = FFNNClassifier(
            model_path=Path(__file__).parent / "ffnn_classifier" / "model.pt",
            threshold=config.detection_threshold
        )
        
        # Game components
        self.web_renderer = WebEffectRenderer(self.depth_config)
        self.symbiote_manager = SymbioteManager(ACTIVE_SYMBIOTE_CONFIG, self.depth_config)
        self.graphics = GraphicsManager()
        self.scoreboard = Scoreboard(config=ACTIVE_SCORE_CONFIG)
        self.infection_manager = InfectionManager(ACTIVE_SCORE_CONFIG)
        
        # State machine
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
        self.last_hand_landmarks = None
        self.last_pose_landmarks = None
        self.last_handedness = None
        self.last_frame_size = None
        self.frame_count = 0
        
        # Register trigger callback
        self.state_machine.on_trigger(self._on_web_shoot)
    
    @abstractmethod
    def draw_hand(self, frame: np.ndarray, hand_landmarks) -> np.ndarray:
        """Draw hand visualization. Implemented by subclasses."""
        pass
    
    @abstractmethod
    def draw_pose_if_enabled(self, frame: np.ndarray, pose_results) -> np.ndarray:
        """Draw pose landmarks if enabled. Implemented by subclasses."""
        pass
    
    @abstractmethod
    def get_controls_text(self) -> str:
        """Get control hints text for this mode."""
        pass
    
    @abstractmethod
    def get_window_title(self) -> str:
        """Get window title for this mode."""
        pass
    
    @abstractmethod
    def handle_extra_keys(self, key: int) -> bool:
        """Handle mode-specific key presses. Return True if handled."""
        pass
    
    def _pose_to_dict(self, pose) -> dict:
        """Convert PoseLandmarks dataclass to dict for symbiote targeting."""
        pose_dict = {}
        for attr_name, idx in POSE_MAPPING.items():
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
            
            wrist = landmarks[0]
            wrist_x = int(wrist.x * w)
            wrist_y = int(wrist.y * h)
            
            elbow = None
            if self.last_handedness == 'Left':
                elbow = pose.left_elbow
            elif self.last_handedness == 'Right':
                elbow = pose.right_elbow
            
            if elbow is not None:
                elbow_x = int(elbow[0] * w)
                elbow_y = int(elbow[1] * h)
                self.web_renderer.shoot_web(
                    elbow_x=elbow_x, elbow_y=elbow_y,
                    wrist_x=wrist_x, wrist_y=wrist_y,
                    frame_width=w, frame_height=h
                )
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process a single video frame."""
        h, w = frame.shape[:2]
        self.last_frame_size = (h, w)
        self.frame_count += 1
        
        # Detect hands and pose
        if USE_HOLISTIC:
            hand_results, pose_results = self.tracker.detect_all(frame)
        else:
            hand_results = self.tracker.detect(frame)
            pose_results = self.tracker.detect_pose(frame)
        
        # Convert pose for symbiote targeting
        pose_landmarks_dict = None
        if pose_results:
            pose_landmarks_dict = self._pose_to_dict(pose_results)
        
        # Draw pose (if enabled by subclass)
        frame = self.draw_pose_if_enabled(frame, pose_results)
        
        # Draw hands (subclass implementation)
        if hand_results.hand_landmarks:
            for hand_landmarks in hand_results.hand_landmarks:
                frame = self.draw_hand(frame, hand_landmarks)
        
        # Detect Spider-Man gesture
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
                    if hand_results.handedness and idx < len(hand_results.handedness):
                        self.last_handedness = hand_results.handedness[idx][0].category_name
                    break
        
        # Update state machine
        current_state = self.state_machine.update(spiderman_detected, wrist_y)
        state_info = self.state_machine.get_state_info()
        state_color = self.state_machine.get_state_color()
        
        # Update symbiotes
        hit_balls = self.symbiote_manager.update(w, h, pose_landmarks_dict)
        for ball in hit_balls:
            print(f"💀 HIT! Symbiote hit your {ball.hit_body_part}!")
            # Add infection source at hit location
            self.infection_manager.add_infection_source(ball.current_x, ball.current_y)
        
        # Update infection spread
        self.infection_manager.update(w, h)
        
        # Check web collisions
        for web in self.web_renderer.active_webs:
            destroyed_ball = self.symbiote_manager.check_web_collision(
                web.start_x, web.start_y, web.center_end_x, web.center_end_y, web.progress
            )
            if not destroyed_ball:
                destroyed_ball = self.symbiote_manager.check_web_collision(
                    web.start_x, web.start_y, web.left_end_x, web.left_end_y, web.progress
                )
            if not destroyed_ball:
                destroyed_ball = self.symbiote_manager.check_web_collision(
                    web.start_x, web.start_y, web.right_end_x, web.right_end_y, web.progress
                )
            if destroyed_ball:
                combo = self.scoreboard.record_destroy()
                print(f"🕸️ THWACK! Ball destroyed! Combo: x{combo} Total: {self.symbiote_manager.balls_destroyed}")
                # THWIP at collision position (ball location)
                self.graphics.trigger_thwip(destroyed_ball.current_x, destroyed_ball.current_y)
        
        # Render game elements
        frame = self.infection_manager.apply_infection(frame)  # BFS infection spread
        frame = self.symbiote_manager.render_grayscale_effect(frame)
        frame = self.symbiote_manager.render(frame)
        frame = self.symbiote_manager.render_hit_markers(frame)
        frame = self.web_renderer.update_and_render(frame)
        frame = self.graphics.render_thwip_effects(frame)
        
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
        
        # Trigger methods
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
        
        # Bottom info
        cv2.putText(frame, f"Webs: {len(self.web_renderer.active_webs)} | Symbiotes: {stats['active_balls']}", 
                    (10, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(frame, self.get_controls_text(), 
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
        
        # Start game tracking
        self.scoreboard.start_game()
        
        print("=" * 60)
        print(f"🕷️  {self.get_window_title()}")
        print("=" * 60)
        print(f"Trigger: {cfg.toggle_count_threshold} flicks / {cfg.sustained_hold_seconds}s hold")
        print(f"Symbiotes: spawn every {sym_cfg.spawn_interval}s, {sym_cfg.travel_time}s travel")
        print("")
        print(f"CONTROLS: {self.get_controls_text()}")
        print("=" * 60)
        
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            frame = cv2.flip(frame, 1)
            frame = self.process_frame(frame)
            cv2.imshow(self.get_window_title(), frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.state_machine.reset()
                self.infection_manager.reset()
                print("🔄 State machine reset")
            elif key == ord('g'):
                self.symbiote_manager.reset()
                self.infection_manager.reset()
                self.trigger_count = 0
                self.scoreboard.start_game()  # Restart scoring
                print("🎮 Game reset")
            elif key in [ord('+'), ord('=')]:
                self.classifier.threshold = min(0.99, self.classifier.threshold + 0.05)
                print(f"🎯 Threshold: {self.classifier.threshold:.0%}")
            elif key == ord('-'):
                self.classifier.threshold = max(0.1, self.classifier.threshold - 0.05)
                print(f"🎯 Threshold: {self.classifier.threshold:.0%}")
            else:
                # Let subclass handle extra keys
                self.handle_extra_keys(key)
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Record final score
        stats = self.symbiote_manager.get_stats()
        score = self.scoreboard.end_game(
            player_name="Player",
            webs_shot=self.trigger_count,
            balls_destroyed=stats['balls_destroyed'],
            hits_taken=stats['hits_taken'],
            difficulty="normal"
        )
        
        # Print final stats
        print("\n" + "=" * 60)
        print("📊 GAME OVER")
        print("=" * 60)
        print(f"  🕸️ Webs Shot: {self.trigger_count}")
        print(f"  💥 Symbiotes Destroyed: {stats['balls_destroyed']}")
        print(f"  💀 Hits Taken: {stats['hits_taken']}")
        print(f"  🏆 Final Score: {score.final_score}")
        print("=" * 60)
        
        # Show leaderboard
        leaderboard = self.scoreboard.get_leaderboard(5)
        if leaderboard:
            print("\n🏅 TOP 5 SCORES:")
            for i, s in enumerate(leaderboard, 1):
                print(f"  {i}. {s.final_score:,} pts - {s.balls_destroyed} kills, {s.hits_taken} hits")
