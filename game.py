"""
Spider-Man: Not Noir - Main Game Loop

A survival game where you shoot symbiote balls with web gestures
before they turn the world grayscale (noir).

Controls:
- SPACE: Start game / Restart after game over
- Q: Quit
- S: Screenshot
- R: Reset state machine
- G: Reset game

Gesture:
- Spider-Man hand (thumb + index + pinky extended)
- Flick, move UP, or hold to shoot web
"""

import cv2
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from hand_tracker import HandTracker
from gesture_state_machine import GestureStateMachine, StateConfig, GestureState
from ffnn_classifier.run_classifier import FFNNClassifier
from symbiote import SymbioteManager
from symbiote_config import SymbioteConfig
from depth_config import ACTIVE_DEPTH_CONFIG
from web_renderer import WebEffectRenderer
from graphics_manager import GraphicsManager
from game_screen import GameScreenManager
from config import ACTIVE_CONFIG

# Create snapshots directory
SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def save_snapshot(frame, prefix="snapshot"):
    """Save a snapshot with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SNAPSHOT_DIR}/{prefix}_{timestamp}.png"
    cv2.imwrite(filename, frame)
    print(f"📸 Snapshot saved: {filename}")
    return filename


def main():
    # Frame settings
    FRAME_WIDTH = 1280
    FRAME_HEIGHT = 720
    
    # Initialize tracker with pose
    tracker = HandTracker(enable_pose=True)
    
    # FFNN Classifier (same as web_shooter_base.py)
    classifier = FFNNClassifier(
        model_path=Path(__file__).parent / "ffnn_classifier" / "model.pt",
        threshold=ACTIVE_CONFIG.detection_threshold
    )
    
    # Symbiote config with smaller end size
    symbiote_config = SymbioteConfig(
        spawn_interval=2.0,
        max_active=5,
        travel_time=3.0,
        start_size=1,
        end_size=50,  # Smaller than default 80
        hit_radius_multiplier=1.2,
        grayscale_radius_multiplier=1.5,
    )
    
    # Game systems
    symbiote_manager = SymbioteManager(symbiote_config, ACTIVE_DEPTH_CONFIG)
    web_renderer = WebEffectRenderer(ACTIVE_DEPTH_CONFIG)
    graphics_manager = GraphicsManager()
    game_screen = GameScreenManager(FRAME_WIDTH, FRAME_HEIGHT)
    
    # State machine (same config as web_shooter_base.py)
    state_config = StateConfig(
        toggle_count_threshold=ACTIVE_CONFIG.toggle_count_threshold,
        toggle_window_seconds=ACTIVE_CONFIG.toggle_window_seconds,
        upward_threshold=ACTIVE_CONFIG.upward_threshold,
        sustained_hold_seconds=ACTIVE_CONFIG.sustained_hold_seconds,
        cooldown_seconds=ACTIVE_CONFIG.cooldown_seconds
    )
    state_machine = GestureStateMachine(state_config)
    
    # Game state
    webs_shot = 0
    combo = 0
    last_destroy_time = 0
    COMBO_WINDOW = 2.0
    
    # Track last known hand/pose for web direction
    last_hand_landmarks = None
    last_pose_landmarks = None
    last_handedness = None
    
    def on_web_shoot():
        """Callback when web is shot."""
        nonlocal webs_shot, last_hand_landmarks, last_pose_landmarks, last_handedness
        webs_shot += 1
        
        # Shoot web using elbow→wrist direction (like web_shooter_base.py)
        if last_hand_landmarks is not None and last_pose_landmarks is not None:
            wrist = last_hand_landmarks[0]
            wrist_x = int(wrist.x * FRAME_WIDTH)
            wrist_y = int(wrist.y * FRAME_HEIGHT)
            
            # Get elbow based on handedness
            elbow = None
            if last_handedness == 'Left':
                elbow = last_pose_landmarks.left_elbow
            elif last_handedness == 'Right':
                elbow = last_pose_landmarks.right_elbow
            
            if elbow is not None:
                elbow_x = int(elbow[0] * FRAME_WIDTH)
                elbow_y = int(elbow[1] * FRAME_HEIGHT)
                
                # Shoot web!
                web_renderer.shoot_web(
                    elbow_x=elbow_x, elbow_y=elbow_y,
                    wrist_x=wrist_x, wrist_y=wrist_y,
                    frame_width=FRAME_WIDTH, frame_height=FRAME_HEIGHT
                )
    
    state_machine.on_trigger(on_web_shoot)
    
    # Start video capture
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    print("=" * 50)
    print("🕷️  SPIDER-MAN: NOT NOIR")
    print("=" * 50)
    print("Press SPACE to start the game")
    print("Press Q to quit")
    print("=" * 50)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        frame = cv2.flip(frame, 1)
        
        h, w = frame.shape[:2]
        
        # Handle key input
        key = cv2.waitKey(1) & 0xFF
        if not game_screen.handle_key(key):
            break
        
        if key == ord('s'):
            save_snapshot(frame, "spiderman")
        elif key == ord('r'):
            state_machine.reset()
            print("🔄 State machine reset")
        elif key == ord('g') and game_screen.state == "playing":
            # Reset game
            symbiote_manager.reset()
            web_renderer.active_webs.clear()
            graphics_manager.active_thwips.clear()
            webs_shot = 0
            combo = 0
            state_machine.reset()
            game_screen.start_game()
            print("🎮 Game reset")
        
        # Detect hands and pose
        hand_results = tracker.detect(frame)
        pose_results = tracker.detect_pose(frame)
        
        # Game logic only when playing
        if game_screen.state == "playing":
            current_time = time.time()
            
            # Detect Spider-Man gesture using FFNN classifier
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
                        
                        # Store for web shooting
                        last_hand_landmarks = hand_landmarks
                        last_pose_landmarks = pose_results
                        if hand_results.handedness and idx < len(hand_results.handedness):
                            last_handedness = hand_results.handedness[idx][0].category_name
                        break
            
            # Update state machine
            current_state = state_machine.update(spiderman_detected, wrist_y)
            
            # Update symbiotes
            hit_balls = symbiote_manager.update(w, h, None)
            
            # Check web collisions (all 3 lines like web_shooter_base.py)
            for web in web_renderer.active_webs:
                if web.is_expired:
                    continue
                
                # Check center line
                destroyed = symbiote_manager.check_web_collision(
                    web.start_x, web.start_y,
                    web.center_end_x, web.center_end_y,
                    web.progress
                )
                # Check left line
                if not destroyed:
                    destroyed = symbiote_manager.check_web_collision(
                        web.start_x, web.start_y,
                        web.left_end_x, web.left_end_y,
                        web.progress
                    )
                # Check right line
                if not destroyed:
                    destroyed = symbiote_manager.check_web_collision(
                        web.start_x, web.start_y,
                        web.right_end_x, web.right_end_y,
                        web.progress
                    )
                
                if destroyed:
                    # Combo system
                    if current_time - last_destroy_time <= COMBO_WINDOW:
                        combo += 1
                    else:
                        combo = 1
                    last_destroy_time = current_time
                    
                    # THWIP at destruction point
                    graphics_manager.trigger_thwip(destroyed.current_x, destroyed.current_y)
            
            # Apply grayscale effect (with BFS spreading)
            frame = symbiote_manager.render_grayscale_effect(frame)
            
            # Calculate coverage
            coverage = symbiote_manager.get_grayscale_coverage(w, h)
            
            # Update game screen stats
            game_screen.update_stats(
                webs_shot=webs_shot,
                balls_destroyed=symbiote_manager.balls_destroyed,
                hits_taken=symbiote_manager.hits_taken,
                combo=combo,
                grayscale_coverage=coverage
            )
            
            # Render game elements (same order as web_shooter_base.py)
            frame = symbiote_manager.render(frame)
            frame = symbiote_manager.render_hit_markers(frame)
            frame = web_renderer.update_and_render(frame)
            frame = graphics_manager.render_thwip_effects(frame)
            
            # Draw hand as glove
            if hand_results.hand_landmarks:
                for hand_landmarks in hand_results.hand_landmarks:
                    frame = graphics_manager.draw_spiderman_hand_filled(frame, hand_landmarks)
            
            # State indicator
            state_info = state_machine.get_state_info()
            state_color = state_machine.get_state_color()
            cv2.circle(frame, (w - 30, 70), 15, state_color, -1)
            
            # Confidence display
            if spiderman_detected:
                cv2.putText(frame, f"SPIDEY {confidence:.0%}", (w - 120, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        elif game_screen.state == "intro":
            # Show camera with hand overlay during intro
            if hand_results.hand_landmarks:
                for hand_landmarks in hand_results.hand_landmarks:
                    frame = graphics_manager.draw_spiderman_hand_filled(frame, hand_landmarks)
        
        elif game_screen.state == "game_over":
            # Keep grayscale effect visible
            frame = symbiote_manager.render_grayscale_effect(frame)
        
        # Render game screen overlay (intro/HUD/game over)
        frame = game_screen.render(frame)
        
        cv2.imshow("Spider-Man: Not Noir", frame)
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Print final stats
    if game_screen.final_score:
        score = game_screen.final_score
        print("\n" + "=" * 50)
        print("📊 FINAL RESULTS")
        print("=" * 50)
        print(f"  🏆 Final Score: {score.final_score}")
        print(f"  🕸️  Webs Shot: {score.webs_shot}")
        print(f"  💥 Symbiotes Destroyed: {score.balls_destroyed}")
        print(f"  ☠️  Hits Taken: {score.hits_taken}")
        print(f"  ⏱️  Survival Time: {int(score.duration_seconds)}s")
        print("=" * 50)


if __name__ == "__main__":
    main()
