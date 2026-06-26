"""
Training Mode - Practice web shooting before the real game.

Allows players to:
- Learn the Spider-Man hand gesture
- Practice triggering web shots
- Understand the state indicator colors
- Build confidence before facing symbiotes
"""

import cv2
import numpy as np
import time
from pathlib import Path
from typing import Optional

from hand_tracker import HandTracker
from gesture_state_machine import GestureStateMachine, StateConfig, GestureState
from ffnn_classifier.run_classifier import FFNNClassifier
from web_renderer import WebEffectRenderer
from graphics_manager import GraphicsManager
from depth_config import ACTIVE_DEPTH_CONFIG
from config import ACTIVE_CONFIG


class TrainingMode:
    """
    Training mode for practicing web shooting.
    
    No symbiotes, no scoring - just practice the gesture and trigger mechanics.
    """
    
    # Colors (BGR)
    RED = (0, 0, 200)
    BLUE = (200, 50, 50)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    YELLOW = (0, 255, 255)
    GREEN = (0, 255, 0)
    DARK_OVERLAY = (20, 20, 20)
    
    INSTRUCTIONS = [
        "SPIDER-MAN HAND:",
        "  - Extend THUMB, INDEX, PINKY",
        "  - Curl MIDDLE and RING",
        "",
        "TRIGGER A WEB:",
        "  - FLICK hand quickly",
        "  - Move UP while holding",
        "  - HOLD gesture 0.5s",
        "",
        "STATE INDICATOR:",
        "  GRAY = Looking...",
        "  YELLOW = Ready to fire!",
        "  GREEN = Web shot!",
    ]
    
    def __init__(self, frame_width: int = 1280, frame_height: int = 720):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.webs_shot = 0
        
        # Animation
        self.blink_state = True
        self.last_blink_time = time.time()
    
    def reset(self):
        """Reset training state."""
        self.webs_shot = 0
    
    def increment_webs(self):
        """Called when a web is shot during training."""
        self.webs_shot += 1
    
    def render(self, frame: np.ndarray, spiderman_detected: bool = False, 
               confidence: float = 0.0, state_color: tuple = (128, 128, 128)) -> np.ndarray:
        """Render training overlay on frame."""
        h, w = frame.shape[:2]
        
        # Semi-transparent overlay on right side for instructions
        overlay = frame.copy()
        cv2.rectangle(overlay, (w // 2, 0), (w, h), self.DARK_OVERLAY, -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        
        # Title
        title = "TRAINING MODE"
        title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_DUPLEX, 1.5, 3)[0]
        title_x = w // 2 + (w // 2 - title_size[0]) // 2
        cv2.putText(frame, title, (title_x, 60),
                    cv2.FONT_HERSHEY_DUPLEX, 1.5, self.YELLOW, 3)
        
        # Subtitle
        subtitle = "Practice shooting webs!"
        sub_size = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        sub_x = w // 2 + (w // 2 - sub_size[0]) // 2
        cv2.putText(frame, subtitle, (sub_x, 95),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.WHITE, 2)
        
        # Instructions
        inst_x = w // 2 + 30
        inst_y = 140
        
        for line in self.INSTRUCTIONS:
            if line == "":
                inst_y += 10
            elif line.startswith("  "):
                cv2.putText(frame, line, (inst_x, inst_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.WHITE, 1)
                inst_y += 22
            else:
                cv2.putText(frame, line, (inst_x, inst_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.YELLOW, 1)
                inst_y += 26
        
        # State indicator (larger, more visible)
        cv2.circle(frame, (w - 50, 70), 25, state_color, -1)
        cv2.circle(frame, (w - 50, 70), 25, self.WHITE, 2)
        
        # Confidence display
        if spiderman_detected:
            cv2.putText(frame, f"DETECTED {confidence:.0%}", (w - 130, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.GREEN, 1)
        
        # Webs shot counter (big and prominent)
        webs_text = f"WEBS SHOT: {self.webs_shot}"
        webs_size = cv2.getTextSize(webs_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
        webs_x = w // 2 + (w // 2 - webs_size[0]) // 2
        cv2.putText(frame, webs_text, (webs_x, h - 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, self.GREEN, 3)
        
        # Encouragement based on webs shot
        if self.webs_shot == 0:
            msg = "Try shooting your first web!"
            msg_color = self.WHITE
        elif self.webs_shot < 3:
            msg = "Great start! Keep practicing!"
            msg_color = self.WHITE
        elif self.webs_shot < 5:
            msg = "You're getting the hang of it!"
            msg_color = self.YELLOW
        elif self.webs_shot < 10:
            msg = "Excellent! You're a natural!"
            msg_color = self.YELLOW
        else:
            msg = "READY FOR BATTLE!"
            msg_color = self.GREEN
        
        msg_size = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        msg_x = w // 2 + (w // 2 - msg_size[0]) // 2
        cv2.putText(frame, msg, (msg_x, h - 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, msg_color, 2)
        
        # Blinking prompt
        if time.time() - self.last_blink_time > 0.5:
            self.blink_state = not self.blink_state
            self.last_blink_time = time.time()
        
        if self.blink_state:
            prompt = ">>> PRESS ENTER when ready to FIGHT! <<<"
            prompt_size = cv2.getTextSize(prompt, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            prompt_x = w // 2 + (w // 2 - prompt_size[0]) // 2
            cv2.putText(frame, prompt, (prompt_x, h - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.GREEN, 2)
        
        return frame


def run_training_standalone():
    """
    Run training mode as a standalone program.
    
    Usage: python training_mode.py
    """
    FRAME_WIDTH = 1280
    FRAME_HEIGHT = 720
    
    # Initialize components
    tracker = HandTracker(enable_pose=True)
    classifier = FFNNClassifier(
        model_path=Path(__file__).parent / "ffnn_classifier" / "model.pt",
        threshold=ACTIVE_CONFIG.detection_threshold
    )
    
    # State machine
    state_config = StateConfig(
        toggle_count_threshold=ACTIVE_CONFIG.toggle_count_threshold,
        toggle_window_seconds=ACTIVE_CONFIG.toggle_window_seconds,
        upward_threshold=ACTIVE_CONFIG.upward_threshold,
        sustained_hold_seconds=ACTIVE_CONFIG.sustained_hold_seconds,
        cooldown_seconds=ACTIVE_CONFIG.cooldown_seconds
    )
    state_machine = GestureStateMachine(state_config)
    
    # Renderers
    web_renderer = WebEffectRenderer(ACTIVE_DEPTH_CONFIG)
    graphics_manager = GraphicsManager()
    training = TrainingMode(FRAME_WIDTH, FRAME_HEIGHT)
    
    # Track state for web shooting
    last_hand_landmarks = None
    last_pose_landmarks = None
    last_handedness = None
    
    def on_web_shoot():
        nonlocal last_hand_landmarks, last_pose_landmarks, last_handedness
        training.increment_webs()
        
        if last_hand_landmarks is not None and last_pose_landmarks is not None:
            wrist = last_hand_landmarks[0]
            wrist_x = int(wrist.x * FRAME_WIDTH)
            wrist_y = int(wrist.y * FRAME_HEIGHT)
            
            elbow = None
            if last_handedness == 'Left':
                elbow = last_pose_landmarks.left_elbow
            elif last_handedness == 'Right':
                elbow = last_pose_landmarks.right_elbow
            
            if elbow is not None:
                elbow_x = int(elbow[0] * FRAME_WIDTH)
                elbow_y = int(elbow[1] * FRAME_HEIGHT)
                web_renderer.shoot_web(
                    elbow_x=elbow_x, elbow_y=elbow_y,
                    wrist_x=wrist_x, wrist_y=wrist_y,
                    frame_width=FRAME_WIDTH, frame_height=FRAME_HEIGHT
                )
    
    state_machine.on_trigger(on_web_shoot)
    
    # Video capture
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    print("=" * 50)
    print("🕷️  SPIDER-MAN TRAINING MODE")
    print("=" * 50)
    print("Practice your web shooting!")
    print("Press ENTER when ready to exit")
    print("Press Q to quit")
    print("=" * 50)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        frame = cv2.flip(frame, 1)
        
        # Detect hands and pose
        hand_results = tracker.detect(frame)
        pose_results = tracker.detect_pose(frame)
        
        # Detect Spider-Man gesture
        spiderman_detected = False
        wrist_y = None
        confidence = 0.0
        
        if hand_results.hand_landmarks:
            for idx, hand_landmarks in enumerate(hand_results.hand_landmarks):
                is_spiderman, conf = classifier.predict(hand_landmarks)
                if is_spiderman:
                    spiderman_detected = True
                    confidence = conf
                    wrist_y = hand_landmarks[0].y
                    
                    last_hand_landmarks = hand_landmarks
                    last_pose_landmarks = pose_results
                    if hand_results.handedness and idx < len(hand_results.handedness):
                        last_handedness = hand_results.handedness[idx][0].category_name
                    break
        
        # Update state machine
        state_machine.update(spiderman_detected, wrist_y)
        state_color = state_machine.get_state_color()
        
        # Render web effects
        frame = web_renderer.update_and_render(frame)
        frame = graphics_manager.render_thwip_effects(frame)
        
        # Draw hand
        if hand_results.hand_landmarks:
            for hand_landmarks in hand_results.hand_landmarks:
                frame = graphics_manager.draw_spiderman_hand_filled(frame, hand_landmarks)
        
        # Render training overlay
        frame = training.render(frame, spiderman_detected, confidence, state_color)
        
        cv2.imshow("Spider-Man Training", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 13:  # Q or Enter
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\n🕸️  Training complete! You shot {training.webs_shot} webs.")


if __name__ == "__main__":
    run_training_standalone()
