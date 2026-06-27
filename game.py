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
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

from hand_tracker import HandTracker
from gesture_state_machine import GestureStateMachine, StateConfig, GestureState
from ffnn_classifier.run_classifier import FFNNClassifier
from multi_gesture_classifier.run_classifier import MultiGestureClassifier
from symbiote import SymbioteManager
from symbiote_config import SymbioteConfig
from depth_config import ACTIVE_DEPTH_CONFIG
from web_renderer import WebEffectRenderer
from graphics_manager import GraphicsManager
from game_screen import GameScreenManager
from training_mode import TrainingMode
from dr_strange_ring import DrStrangeRingManager
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
    
    # Multi-gesture classifier for Dr. Strange detection
    try:
        multi_classifier = MultiGestureClassifier(
            model_path=Path(__file__).parent / "multi_gesture_classifier" / "multi_gesture_model.pt"
        )
        dr_strange_enabled = True
    except FileNotFoundError:
        print("⚠️ Multi-gesture model not found. Dr. Strange detection disabled.")
        multi_classifier = None
        dr_strange_enabled = False
    
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
    training_mode = TrainingMode(FRAME_WIDTH, FRAME_HEIGHT)
    dr_strange_ring_manager = DrStrangeRingManager()  # Portal ring that spawns randomly
    
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
    
    # Dr. Strange detection state
    dr_strange_unlocked = False  # Dr. Strange powers only available after catching ring
    dr_strange_active = False
    dr_strange_display_until = 0
    dr_strange_hold_start = None  # When Dr. Strange gesture started
    dr_strange_magic_active = False  # Magic circle active after 1.5s hold
    dr_strange_hand_landmarks = None  # Store landmarks for magic circle
    dr_strange_circle_angle = 0.0  # Rotation angle for magic circle
    dr_strange_path = []  # List of (x, y, timestamp) points tracing the path
    DR_STRANGE_PATH_MAX_POINTS = 150  # Maximum points to keep in path
    DR_STRANGE_PATH_FADE_TIME = 5.0  # Seconds before path points fade (increased for more time to close loop)
    DR_STRANGE_LOOP_THRESHOLD = 40  # Distance in pixels to consider loop closed
    DR_STRANGE_MIN_LOOP_POINTS = 20  # Minimum points needed before loop detection
    dr_strange_completed_portals = []  # List of completed portal circles [(center_x, center_y, radius, creation_time), ...]
    
    # Portal restoration state (when portal is completed)
    portal_restoration_active = False
    portal_restoration_start_time = 0
    portal_restoration_center = (0, 0)
    portal_restoration_progress = 0.0  # 0.0 to 1.0
    PORTAL_RESTORATION_INTERVAL = 0.25  # seconds between restoration steps
    last_restoration_step_time = 0
    
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
        
        # Track state changes to reset training mode when entering training
        prev_state = game_screen.state
        
        # Handle key input
        key = cv2.waitKey(1) & 0xFF
        if not game_screen.handle_key(key):
            break
        
        # Reset training mode when entering training state
        if game_screen.state == "training" and prev_state != "training":
            training_mode.reset()
        
        if key == ord('s'):
            save_snapshot(frame, "spiderman")
        elif key == ord('r'):
            state_machine.reset()
            print("🔄 State machine reset")
        elif key == ord('g') and game_screen.state == "playing":
            # Reset game
            symbiote_manager.reset()
            dr_strange_ring_manager.reset()  # Reset portal ring
            dr_strange_unlocked = False  # Reset Dr. Strange unlock
            dr_strange_completed_portals = []  # Clear completed portals
            portal_restoration_active = False  # Reset restoration state
            portal_restoration_progress = 0.0
            web_renderer.active_webs.clear()
            graphics_manager.active_thwips.clear()
            webs_shot = 0
            combo = 0
            state_machine.reset()
            training_mode.reset()
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
            dr_strange_detected = False
            wrist_y = None
            confidence = 0.0
            
            if hand_results.hand_landmarks:
                for idx, hand_landmarks in enumerate(hand_results.hand_landmarks):
                    # Check Spider-Man gesture first
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
                    
                    # Check Dr. Strange gesture if not Spider-Man (only if unlocked by catching ring)
                    if dr_strange_enabled and multi_classifier and dr_strange_unlocked:
                        is_dr_strange, dr_conf = multi_classifier.predict_dr_strange(hand_landmarks)
                        if is_dr_strange and dr_conf > 0.7:
                            dr_strange_detected = True
                            dr_strange_hand_landmarks = hand_landmarks  # Store for magic circle
                            
                            # Track hold time
                            if dr_strange_hold_start is None:
                                dr_strange_hold_start = current_time
                                dr_strange_active = True
                                dr_strange_display_until = current_time + 2.0
                                print("🔮 Dr. Strange move activated!")
                            
                            # Check if held for 1.5 seconds
                            hold_duration = current_time - dr_strange_hold_start
                            if hold_duration >= 1.5 and not dr_strange_magic_active:
                                dr_strange_magic_active = True
                                print("✨ Magic circle activated!")
                        else:
                            # Reset hold if gesture lost
                            dr_strange_hold_start = None
                            dr_strange_magic_active = False
                            dr_strange_hand_landmarks = None
                            dr_strange_path = []  # Clear path
            
            # Reset Dr. Strange state if no hands detected
            if not hand_results.hand_landmarks or not dr_strange_detected:
                dr_strange_hold_start = None
                dr_strange_magic_active = False
                dr_strange_hand_landmarks = None
                dr_strange_path = []  # Clear path
            
            # Update state machine (only if Dr. Strange not active - no webs during magic)
            if not dr_strange_detected:
                current_state = state_machine.update(spiderman_detected, wrist_y)
            else:
                current_state = state_machine.update(False, wrist_y)  # Disable trigger when Dr. Strange active
            
            # Update symbiotes (stop spawning if portal restoration active)
            if not portal_restoration_active:
                hit_balls = symbiote_manager.update(w, h, None)
            else:
                # During restoration, don't spawn new symbiotes, just update existing
                hit_balls = symbiote_manager.update_without_spawn(w, h)
            
            # Update Dr. Strange portal ring (spawns randomly)
            dr_strange_ring_manager.update(w, h)
            
            # Check if hand can capture the portal ring (using landmarks 16 and 20)
            if dr_strange_ring_manager.active_ring is not None:
                # For capturing, use center between landmarks 16 (ring finger) and 20 (pinky)
                if hand_results.hand_landmarks:
                    for hand_landmarks in hand_results.hand_landmarks:
                        lm16 = hand_landmarks[16]  # Ring finger tip
                        lm20 = hand_landmarks[20]  # Pinky tip
                        # Center between landmarks 16 and 20
                        hand_x = int((lm16.x + lm20.x) / 2 * w)
                        hand_y = int((lm16.y + lm20.y) / 2 * h)
                        # Check capture with hand position (gesture not required to catch)
                        if dr_strange_ring_manager.check_hand_capture(hand_x, hand_y, True):
                            dr_strange_unlocked = True
                            print("🌀 Portal ring captured! Dr. Strange powers UNLOCKED!")
            
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
            # During portal restoration, gradually restore color from edges to center
            if portal_restoration_active:
                # Update restoration progress every 0.25 seconds
                if current_time - last_restoration_step_time >= PORTAL_RESTORATION_INTERVAL:
                    last_restoration_step_time = current_time
                    
                    # Shrink grayscale regions towards center
                    symbiote_manager.shrink_grayscale_towards_point(
                        portal_restoration_center[0], 
                        portal_restoration_center[1],
                        shrink_amount=30
                    )
                    
                    current_coverage = symbiote_manager.get_grayscale_coverage(w, h)
                    active_balls = len(symbiote_manager.active_balls)
                    print(f"✨ Reality restoring... {int((1.0 - current_coverage) * 100)}% | Symbiotes remaining: {active_balls}")
                
                # Check if restoration complete:
                # 1. ALL pixels are RGB (coverage = 0)
                # 2. No grayscale regions left
                # 3. ALL symbiotes have reached the portal center (no active balls)
                current_coverage = symbiote_manager.get_grayscale_coverage(w, h)
                all_symbiotes_absorbed = len(symbiote_manager.active_balls) == 0
                
                if current_coverage <= 0.0 and len(symbiote_manager.grayscale_regions) == 0 and all_symbiotes_absorbed:
                    portal_restoration_active = False
                    print("🏆 REALITY FULLY RESTORED! YOU WIN!")
                    game_screen.trigger_win()
                    game_screen.trigger_win()
            
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
            frame = dr_strange_ring_manager.render(frame)  # Dr. Strange portal ring
            
            # Only render webs if Dr. Strange is NOT detected
            if not dr_strange_detected:
                frame = web_renderer.update_and_render(frame)
            else:
                # Clear webs when Dr. Strange is active (magic replaces webs)
                web_renderer.active_webs.clear()
            
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
            
            # Dr. Strange unlock status indicator
            if dr_strange_unlocked:
                cv2.putText(frame, "DR. STRANGE: UNLOCKED", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
            else:
                cv2.putText(frame, "Catch the portal ring!", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
            
            # Dr. Strange activation display
            if dr_strange_active and current_time < dr_strange_display_until:
                # Orange glow text for Dr. Strange
                text = "DR. STRANGE MOVE ACTIVATED!"
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 1.2, 2)[0]
                text_x = (w - text_size[0]) // 2
                text_y = 150
                # Glow effect
                cv2.putText(frame, text, (text_x, text_y),
                            cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 100, 255), 4)  # Orange glow
                cv2.putText(frame, text, (text_x, text_y),
                            cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 165, 255), 2)  # Orange core
            elif current_time >= dr_strange_display_until:
                dr_strange_active = False
            
            # Dr. Strange Magic Circle (after 1.5s hold)
            if dr_strange_magic_active and dr_strange_hand_landmarks is not None:
                # Update rotation angle
                dr_strange_circle_angle += 0.08  # Rotate speed
                
                # Get landmarks 16 (ring finger tip) and 20 (pinky tip)
                lm16 = dr_strange_hand_landmarks[16]  # Ring finger tip
                lm20 = dr_strange_hand_landmarks[20]  # Pinky tip
                
                # Convert to pixel coordinates
                x16 = int(lm16.x * w)
                y16 = int(lm16.y * h)
                x20 = int(lm20.x * w)
                y20 = int(lm20.y * h)
                
                # Calculate center point between landmarks 16 and 20
                center_x = (x16 + x20) // 2
                center_y = (y16 + y20) // 2
                
                # Add current position to path
                dr_strange_path.append((center_x, center_y, current_time))
                
                # Check if loop is closed (current position near start position)
                if len(dr_strange_path) >= DR_STRANGE_MIN_LOOP_POINTS:
                    start_x, start_y, _ = dr_strange_path[0]
                    distance_to_start = math.sqrt((center_x - start_x)**2 + (center_y - start_y)**2)
                    
                    if distance_to_start < DR_STRANGE_LOOP_THRESHOLD:
                        # Loop completed! Calculate the bounding circle
                        all_x = [p[0] for p in dr_strange_path]
                        all_y = [p[1] for p in dr_strange_path]
                        portal_center_x = (min(all_x) + max(all_x)) // 2
                        portal_center_y = (min(all_y) + max(all_y)) // 2
                        portal_radius = max(max(all_x) - min(all_x), max(all_y) - min(all_y)) // 2
                        portal_radius = max(30, portal_radius)  # Minimum radius of 30px
                        
                        # Add to completed portals
                        dr_strange_completed_portals.append((portal_center_x, portal_center_y, portal_radius, current_time))
                        
                        # Clear the path
                        dr_strange_path = []
                        
                        # Start portal restoration effect!
                        portal_restoration_active = True
                        portal_restoration_start_time = current_time
                        portal_restoration_center = (portal_center_x, portal_center_y)
                        portal_restoration_progress = 0.0
                        last_restoration_step_time = current_time
                        
                        # Redirect all symbiotes to portal center
                        symbiote_manager.redirect_balls_to_point(portal_center_x, portal_center_y)
                        
                        print("🏆 PORTAL COMPLETE! Restoring reality...")
                
                # Limit path length
                if len(dr_strange_path) > DR_STRANGE_PATH_MAX_POINTS:
                    dr_strange_path = dr_strange_path[-DR_STRANGE_PATH_MAX_POINTS:]
                
                # Fire/orange color palette (BGR format)
                FIRE_COLORS = [
                    (0, 50, 139),    # Dark red/brown
                    (0, 69, 190),    # Deep orange
                    (0, 100, 220),   # Orange
                    (0, 140, 255),   # Bright orange
                    (30, 180, 255),  # Yellow-orange
                    (50, 200, 255),  # Light orange/yellow
                ]
                
                # Draw the traced path with fading fire effect
                if len(dr_strange_path) > 1:
                    for i in range(1, len(dr_strange_path)):
                        px1, py1, t1 = dr_strange_path[i - 1]
                        px2, py2, t2 = dr_strange_path[i]
                        
                        # Calculate age and fade
                        age = current_time - t1
                        fade = max(0, 1.0 - (age / DR_STRANGE_PATH_FADE_TIME))
                        
                        if fade > 0:
                            # Color based on position in path (newer = brighter)
                            color_idx = min(5, int((i / len(dr_strange_path)) * 6))
                            color = FIRE_COLORS[color_idx]
                            
                            # Fade the color
                            faded_color = tuple(int(c * fade) for c in color)
                            
                            # Line thickness based on age (newer = thicker)
                            thickness = max(1, int(3 * fade))
                            
                            cv2.line(frame, (px1, py1), (px2, py2), faded_color, thickness)
                    
                    # Draw fire particles along the path
                    for i, (px, py, t) in enumerate(dr_strange_path[::3]):  # Every 3rd point
                        age = current_time - t
                        fade = max(0, 1.0 - (age / DR_STRANGE_PATH_FADE_TIME))
                        if fade > 0.3:
                            # Flickering particles
                            offset_x = int(3 * math.sin(dr_strange_circle_angle * 3 + i))
                            offset_y = int(3 * math.cos(dr_strange_circle_angle * 3 + i))
                            color = FIRE_COLORS[(i + int(dr_strange_circle_angle * 2)) % len(FIRE_COLORS)]
                            faded_color = tuple(int(c * fade) for c in color)
                            cv2.circle(frame, (px + offset_x, py + offset_y), 2, faded_color, -1)
                    
                    # Draw start point indicator (where to close the loop)
                    if len(dr_strange_path) >= DR_STRANGE_MIN_LOOP_POINTS:
                        start_x, start_y, _ = dr_strange_path[0]
                        distance_to_start = math.sqrt((center_x - start_x)**2 + (center_y - start_y)**2)
                        
                        # Pulsing indicator at start point
                        pulse_size = int(8 + 4 * math.sin(dr_strange_circle_angle * 4))
                        
                        # Change color based on proximity (green when close)
                        if distance_to_start < DR_STRANGE_LOOP_THRESHOLD * 2:
                            # Getting close - yellow/green pulse
                            indicator_color = (0, 255, 200)  # Cyan/green
                            cv2.circle(frame, (start_x, start_y), pulse_size + 5, (0, 255, 100), 2)
                        else:
                            # Show where to return
                            indicator_color = FIRE_COLORS[5]
                        
                        cv2.circle(frame, (start_x, start_y), pulse_size, indicator_color, 2)
                        cv2.circle(frame, (start_x, start_y), 3, indicator_color, -1)
                
                # Main magic circle (radius 10px minimum, can grow)
                base_radius = 10
                pulse = 2 * math.sin(dr_strange_circle_angle * 2)  # Pulsing effect
                main_radius = int(base_radius + pulse)
                
                # Draw outer glow rings
                for i, radius_offset in enumerate([12, 10, 8, 6]):
                    color = FIRE_COLORS[i % len(FIRE_COLORS)]
                    cv2.circle(frame, (center_x, center_y), main_radius + radius_offset, color, 1)
                
                # Draw main circle with fire gradient
                cv2.circle(frame, (center_x, center_y), main_radius + 4, FIRE_COLORS[2], 2)
                cv2.circle(frame, (center_x, center_y), main_radius + 2, FIRE_COLORS[4], 2)
                cv2.circle(frame, (center_x, center_y), main_radius, FIRE_COLORS[5], 2)
                
                # Draw revolving fire particles around the center
                num_particles = 8
                for i in range(num_particles):
                    angle = dr_strange_circle_angle + (i * 2 * math.pi / num_particles)
                    # Particles at different radii
                    particle_radius = main_radius + 6 + (i % 3) * 3
                    particle_x = int(center_x + particle_radius * math.cos(angle))
                    particle_y = int(center_y + particle_radius * math.sin(angle))
                    color = FIRE_COLORS[(i + int(dr_strange_circle_angle * 2)) % len(FIRE_COLORS)]
                    cv2.circle(frame, (particle_x, particle_y), 3, color, -1)
                
                # Inner revolving sparks (opposite direction)
                for i in range(6):
                    angle = -dr_strange_circle_angle * 1.5 + (i * 2 * math.pi / 6)
                    spark_x = int(center_x + (main_radius - 2) * math.cos(angle))
                    spark_y = int(center_y + (main_radius - 2) * math.sin(angle))
                    color = FIRE_COLORS[5]  # Brightest
                    cv2.circle(frame, (spark_x, spark_y), 2, color, -1)
                
                # Draw connecting lines to landmarks with gradient
                cv2.line(frame, (center_x, center_y), (x16, y16), FIRE_COLORS[3], 1)
                cv2.line(frame, (center_x, center_y), (x20, y20), FIRE_COLORS[3], 1)
                
                # Small fire dots at landmarks
                cv2.circle(frame, (x16, y16), 4, FIRE_COLORS[4], -1)
                cv2.circle(frame, (x20, y20), 4, FIRE_COLORS[4], -1)
            
            # Draw completed portals (persist on screen)
            FIRE_COLORS = [
                (0, 50, 139),    # Dark red/brown
                (0, 69, 190),    # Deep orange
                (0, 100, 220),   # Orange
                (0, 140, 255),   # Bright orange
                (30, 180, 255),  # Yellow-orange
                (50, 200, 255),  # Light orange/yellow
            ]
            
            for portal in dr_strange_completed_portals:
                px, py, pr, pt = portal
                portal_age = current_time - pt
                
                # Portal animation angle (each portal rotates independently)
                portal_angle = dr_strange_circle_angle + portal_age * 2
                
                # Outer glow rings
                for i, radius_offset in enumerate([8, 5, 2]):
                    color = FIRE_COLORS[(i + 2) % len(FIRE_COLORS)]
                    cv2.circle(frame, (px, py), pr + radius_offset, color, 2)
                
                # Main portal ring
                cv2.circle(frame, (px, py), pr, FIRE_COLORS[5], 3)
                cv2.circle(frame, (px, py), pr - 3, FIRE_COLORS[4], 2)
                
                # Rotating particles around completed portal
                num_particles = 12
                for i in range(num_particles):
                    angle = portal_angle + (i * 2 * math.pi / num_particles)
                    particle_x = int(px + pr * math.cos(angle))
                    particle_y = int(py + pr * math.sin(angle))
                    color = FIRE_COLORS[(i + int(portal_angle * 2)) % len(FIRE_COLORS)]
                    cv2.circle(frame, (particle_x, particle_y), 4, color, -1)
                
                # Inner rotating sparks
                for i in range(8):
                    angle = -portal_angle * 1.5 + (i * 2 * math.pi / 8)
                    spark_x = int(px + (pr * 0.7) * math.cos(angle))
                    spark_y = int(py + (pr * 0.7) * math.sin(angle))
                    cv2.circle(frame, (spark_x, spark_y), 3, FIRE_COLORS[5], -1)
                
                # Center glow
                cv2.circle(frame, (px, py), 5, FIRE_COLORS[5], -1)
        
        elif game_screen.state == "intro":
            # Show camera with hand overlay during intro
            if hand_results.hand_landmarks:
                for hand_landmarks in hand_results.hand_landmarks:
                    frame = graphics_manager.draw_spiderman_hand_filled(frame, hand_landmarks)
        
        elif game_screen.state == "training":
            # Training mode - practice web shooting without symbiotes
            current_time = time.time()
            
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
                        
                        # Store for web shooting
                        last_hand_landmarks = hand_landmarks
                        last_pose_landmarks = pose_results
                        if hand_results.handedness and idx < len(hand_results.handedness):
                            last_handedness = hand_results.handedness[idx][0].category_name
                        break
            
            # Update state machine (this fires webs via callback)
            old_webs = webs_shot
            current_state = state_machine.update(spiderman_detected, wrist_y)
            
            # Track training webs using TrainingMode
            if webs_shot > old_webs:
                training_mode.increment_webs()
            
            # Render web effects (no symbiotes in training)
            frame = web_renderer.update_and_render(frame)
            frame = graphics_manager.render_thwip_effects(frame)
            
            # Draw hand
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
            
            # Render training mode overlay
            frame = training_mode.render(frame)
        
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
