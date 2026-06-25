#!/usr/bin/env python3
"""
Spider-Man Web Shooter - Main Application

Integrates:
- FFNN classifier for Spider-Man hand detection
- State machine for gesture sequence
- Web effect rendering with trajectory from wrist through fingertips

Configuration:
    Edit config.py to adjust game speed/sensitivity
    Presets: FAST_CONFIG, NORMAL_CONFIG, SLOW_CONFIG

Usage:
    python web_shooter.py

Controls:
    q - Quit
    r - Reset state machine
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


@dataclass
class WebShot:
    """Represents an active web shot effect."""
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    created_at: float
    duration: float = ACTIVE_CONFIG.web_duration
    max_distance: float = 10.0  # meters (conceptual)
    
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


class WebEffectRenderer:
    """Renders web shooting effects on video frames."""
    
    def __init__(self):
        self.active_webs: List[WebShot] = []
    
    def shoot_web(self, wrist_x: int, wrist_y: int, 
                   middle_tip_x: int, middle_tip_y: int,
                   ring_tip_x: int, ring_tip_y: int,
                   frame_width: int, frame_height: int):
        """
        Create a new web shot from wrist through fingertips.
        
        The web direction is calculated from the wrist through the
        midpoint between middle and ring fingertips.
        """
        # Calculate midpoint between middle and ring fingertips
        target_x = (middle_tip_x + ring_tip_x) // 2
        target_y = (middle_tip_y + ring_tip_y) // 2
        
        # Calculate direction vector
        dx = target_x - wrist_x
        dy = target_y - wrist_y
        
        # Normalize and extend to edge of frame
        length = math.sqrt(dx**2 + dy**2)
        if length > 0:
            dx /= length
            dy /= length
        
        # Extend line to frame boundary
        max_extend = max(frame_width, frame_height) * 2
        end_x = int(wrist_x + dx * max_extend)
        end_y = int(wrist_y + dy * max_extend)
        
        # Create web shot
        web = WebShot(
            start_x=wrist_x,
            start_y=wrist_y,
            end_x=end_x,
            end_y=end_y,
            created_at=time.time()
        )
        self.active_webs.append(web)
    
    def update_and_render(self, frame: np.ndarray) -> np.ndarray:
        """Update web effects and render them on the frame."""
        # Remove expired webs
        self.active_webs = [w for w in self.active_webs if not w.is_expired]
        
        # Render each active web
        for web in self.active_webs:
            self._render_web(frame, web)
        
        return frame
    
    def _render_web(self, frame: np.ndarray, web: WebShot):
        """Render a single web shot."""
        # Calculate current web endpoint based on progress
        progress = web.progress
        current_end_x = int(web.start_x + (web.end_x - web.start_x) * progress)
        current_end_y = int(web.start_y + (web.end_y - web.start_y) * progress)
        
        # Calculate opacity (0-255)
        alpha = int(255 * web.opacity)
        
        # Draw web line with glow effect
        # Outer glow
        cv2.line(frame, 
                 (web.start_x, web.start_y), 
                 (current_end_x, current_end_y),
                 (alpha // 2, alpha // 2, alpha),  # Blue-ish glow
                 web.thickness + 4)
        
        # Main web line (white)
        cv2.line(frame,
                 (web.start_x, web.start_y),
                 (current_end_x, current_end_y),
                 (alpha, alpha, alpha),  # White
                 web.thickness)
        
        # Draw web origin point
        cv2.circle(frame, (web.start_x, web.start_y), 
                   web.thickness + 2, (0, 0, alpha), -1)
    
    @property
    def has_active_webs(self) -> bool:
        return len(self.active_webs) > 0


class SpiderManWebShooter:
    """Main web shooter application."""
    
    def __init__(self, config: GameConfig = ACTIVE_CONFIG):
        self.config = config
        
        # Initialize components
        self.tracker = HandTracker(enable_pose=True)
        self.classifier = FFNNClassifier(
            model_path=Path(__file__).parent / "ffnn_classifier" / "model.pt",
            threshold=config.detection_threshold
        )
        self.web_renderer = WebEffectRenderer()
        
        # Configure state machine with values from config (ADR-009)
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
        self.last_frame_size = None
        
        # Debug: track state history for UI
        self.state_checkmarks = {
            GestureState.LOOKING: False,
            GestureState.DETECTED: False,
            GestureState.TRIGGERED: False,
        }
        self.last_state = GestureState.LOOKING
        
        # Register trigger callback
        self.state_machine.on_trigger(self._on_web_shoot)
        print("DEBUG: SpiderManWebShooter initialized, callback registered")
    
    def _on_web_shoot(self):
        """Called when web shoot gesture is triggered."""
        self.trigger_count += 1
        print(f"🕸️  THWIP! Web #{self.trigger_count}")
        print(f"DEBUG: _on_web_shoot called!")
        print(f"DEBUG: last_hand_landmarks is None: {self.last_hand_landmarks is None}")
        print(f"DEBUG: last_frame_size is None: {self.last_frame_size is None}")
        
        # Create web effect if we have hand landmarks
        if self.last_hand_landmarks is not None and self.last_frame_size is not None:
            landmarks = self.last_hand_landmarks
            h, w = self.last_frame_size
            
            # Get key landmark positions
            wrist = landmarks[0]
            middle_tip = landmarks[12]
            ring_tip = landmarks[16]
            
            print(f"DEBUG: Shooting web from wrist ({wrist.x:.2f}, {wrist.y:.2f})")
            print(f"DEBUG: Frame size: {w}x{h}")
            
            self.web_renderer.shoot_web(
                wrist_x=int(wrist.x * w),
                wrist_y=int(wrist.y * h),
                middle_tip_x=int(middle_tip.x * w),
                middle_tip_y=int(middle_tip.y * h),
                ring_tip_x=int(ring_tip.x * w),
                ring_tip_y=int(ring_tip.y * h),
                frame_width=w,
                frame_height=h
            )
            print(f"DEBUG: Web created! Active webs: {len(self.web_renderer.active_webs)}")
        else:
            print("DEBUG: Cannot shoot web - missing landmarks or frame size")
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process a single video frame."""
        h, w = frame.shape[:2]
        self.last_frame_size = (h, w)
        
        # Detect hands
        hand_results = self.tracker.detect(frame)
        pose_results = self.tracker.detect_pose(frame)
        
        # Draw pose landmarks
        if self.show_pose:
            frame = self.tracker.draw_pose_landmarks(frame, pose_results, show_labels=True)
        
        # Draw hand landmarks
        frame = self.tracker.draw_landmarks(frame, hand_results, show_numbers=self.show_numbers)
        
        # Check for Spider-Man gesture using FFNN
        spiderman_detected = False
        wrist_y = None
        confidence = 0.0
        
        if hand_results.hand_landmarks:
            for hand_landmarks in hand_results.hand_landmarks:
                is_spiderman, conf = self.classifier.predict(hand_landmarks)
                if is_spiderman:
                    spiderman_detected = True
                    confidence = conf
                    wrist_y = hand_landmarks[0].y
                    self.last_hand_landmarks = hand_landmarks
                    break
        
        # Update state machine
        current_state = self.state_machine.update(spiderman_detected, wrist_y)
        state_info = self.state_machine.get_state_info()
        state_color = self.state_machine.get_state_color()
        
        # Debug: track state transitions
        if current_state != self.last_state:
            print(f"DEBUG: State transition: {self.last_state.name} → {current_state.name}")
            self.state_checkmarks[current_state] = True
            self.last_state = current_state
            
            # Reset checkmarks when going back to LOOKING
            if current_state == GestureState.LOOKING:
                self.state_checkmarks = {s: False for s in GestureState}
                self.state_checkmarks[GestureState.LOOKING] = True
        
        # Debug print every 30 frames
        if hasattr(self, 'frame_count'):
            self.frame_count += 1
        else:
            self.frame_count = 0
        
        if self.frame_count % 30 == 0 and spiderman_detected:
            wrist_str = f"{wrist_y:.3f}" if wrist_y is not None else "None"
            print(f"DEBUG: spiderman={spiderman_detected}, conf={confidence:.2f}, wrist_y={wrist_str}, state={current_state.name}")
        
        # Render web effects
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
        
        # State bar at top
        cv2.rectangle(frame, (0, 0), (w, 50), state_color, -1)
        cv2.putText(frame, f"State: {state_info['state']}", (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        
        # Trigger count
        cv2.putText(frame, f"Webs: {self.trigger_count}", (w - 150, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
        
        # Confidence bar
        if detected:
            bar_width = int(200 * confidence)
            cv2.rectangle(frame, (10, 55), (10 + bar_width, 70), (0, 255, 0), -1)
            cv2.rectangle(frame, (10, 55), (210, 70), (255, 255, 255), 1)
            cv2.putText(frame, f"{confidence:.1%}", (220, 68),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Trigger methods display (right side)
        checklist_x = w - 300
        checklist_y = 80
        cv2.putText(frame, "TRIGGER METHODS:", (checklist_x, checklist_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Get toggle count from state info
        toggle_count = state_info.get('toggle_count', 0)
        sustained_progress = state_info.get('sustained_progress', 0)
        cfg = self.config
        
        trigger_methods = [
            f"1. Rapid Flick ({toggle_count}/{cfg.toggle_count_threshold})",
            f"2. Move UP ({cfg.upward_threshold:.0%})", 
            f"3. Hold ({sustained_progress:.0%}/{cfg.sustained_hold_seconds}s)",
        ]
        
        for i, label in enumerate(trigger_methods):
            y = checklist_y + 25 + i * 25
            
            # Highlight active conditions
            if i == 0 and toggle_count >= cfg.toggle_count_threshold - 1:  # Close to rapid toggle
                color = (0, 255, 255)  # Yellow
            elif i == 2 and sustained_progress > 0.5:  # Close to sustained
                color = (0, 255, 255)  # Yellow
            elif detected:
                color = (200, 200, 200)  # Light gray when detected
            else:
                color = (128, 128, 128)  # Gray
            
            cv2.putText(frame, label, (checklist_x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Show current state
        state_y = checklist_y + 100
        cv2.putText(frame, f"State: {state.name}", (checklist_x, state_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, state_color, 2)
        
        # Show last trigger reason if triggered recently
        last_reason = state_info.get('last_trigger_reason', '')
        if last_reason:
            cv2.putText(frame, f"Last: {last_reason}", (checklist_x, state_y + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # State-specific instructions (left side)
        y_offset = 100
        if state == GestureState.LOOKING:
            cv2.putText(frame, "Show Spider-Man hand (palm down)", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        elif state == GestureState.DETECTED:
            cv2.putText(frame, "DETECTED! Trigger methods:", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, "- Flick wrist quickly (rapid toggle)", (10, y_offset + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            cv2.putText(frame, "- Move hand UP (armed motion)", (10, y_offset + 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            cv2.putText(frame, f"- Hold steady ({sustained_progress:.0%}/100%)", (10, y_offset + 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        elif state == GestureState.TRIGGERED:
            cv2.putText(frame, "THWIP!", (w//2 - 80, h//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 4)
        
        # Wrist position indicator (vertical bar on right edge)
        if wrist_y is not None:
            wrist_screen_y = int(wrist_y * h)
            # Current wrist position (green)
            cv2.line(frame, (w - 50, wrist_screen_y), (w - 10, wrist_screen_y), 
                     (0, 255, 0), 4)
            cv2.putText(frame, "WRIST", (w - 50, wrist_screen_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
            # Initial position marker (red)
            if state_info['initial_wrist_y'] is not None:
                initial_y = int(state_info['initial_wrist_y'] * h)
                cv2.line(frame, (w - 50, initial_y), (w - 10, initial_y),
                         (0, 0, 255), 2)
                cv2.putText(frame, "START", (w - 50, initial_y + 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            
            # Target line for upward motion (using config threshold)
            if state_info['initial_wrist_y'] is not None:
                target_y = int((state_info['initial_wrist_y'] - self.config.upward_threshold) * h)
                cv2.line(frame, (w - 50, target_y), (w - 10, target_y),
                         (0, 255, 0), 1)
                cv2.putText(frame, "UP TARGET", (w - 70, target_y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)
        
        # Debug info
        cv2.putText(frame, f"Active webs: {len(self.web_renderer.active_webs)}", 
                    (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Controls hint
        cv2.putText(frame, "q:quit r:reset p:pose n:nums +/-:threshold", 
                    (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        return frame
    
    def run(self):
        """Main application loop."""
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("Error: Could not open camera")
            return
        
        cfg = self.config
        print("=" * 60)
        print("🕷️  SPIDER-MAN WEB SHOOTER")
        print("=" * 60)
        print("Powered by Feed Forward Neural Network (99.4% F1 Score)")
        print("")
        print("CURRENT CONFIG:")
        print(f"  Toggle threshold: {cfg.toggle_count_threshold} flicks in {cfg.toggle_window_seconds}s")
        print(f"  Sustained hold: {cfg.sustained_hold_seconds}s")
        print(f"  Upward motion: {cfg.upward_threshold:.0%} of frame")
        print(f"  Cooldown: {cfg.cooldown_seconds}s")
        print(f"  Detection threshold: {cfg.detection_threshold:.0%}")
        print("")
        print("TRIGGER METHODS (any one fires the web):")
        print(f"  1. RAPID FLICK: Toggle {cfg.toggle_count_threshold}+ times in {cfg.toggle_window_seconds}s")
        print(f"  2. ARMED MOTION: Move hand UP {cfg.upward_threshold:.0%} while holding")
        print(f"  3. SUSTAINED HOLD: Hold steady for {cfg.sustained_hold_seconds}s")
        print("")
        print("CONTROLS:")
        print("  q - Quit")
        print("  r - Reset state machine")
        print("  p - Toggle pose landmarks")
        print("  n - Toggle landmark numbers")
        print("  +/- - Adjust detection threshold")
        print("")
        print("Edit config.py to change game speed (FAST/NORMAL/SLOW)")
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
            elif key == ord('p'):
                self.show_pose = not self.show_pose
                print(f"🦴 Pose landmarks: {'ON' if self.show_pose else 'OFF'}")
            elif key == ord('n'):
                self.show_numbers = not self.show_numbers
                print(f"🔢 Landmark numbers: {'ON' if self.show_numbers else 'OFF'}")
            elif key in [ord('+'), ord('=')]:
                self.classifier.threshold = min(0.99, self.classifier.threshold + 0.05)
                print(f"🎯 Threshold: {self.classifier.threshold:.0%}")
            elif key == ord('-'):
                self.classifier.threshold = max(0.1, self.classifier.threshold - 0.05)
                print(f"🎯 Threshold: {self.classifier.threshold:.0%}")
        
        cap.release()
        cv2.destroyAllWindows()
        
        print("\n" + "=" * 60)
        print("📊 SESSION SUMMARY")
        print("=" * 60)
        print(f"  🕸️ Total Webs Shot: {self.trigger_count}")
        print("=" * 60)


def main():
    app = SpiderManWebShooter()
    app.run()


if __name__ == "__main__":
    main()
