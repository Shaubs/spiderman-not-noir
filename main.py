import cv2
import os
from datetime import datetime
from tracking import HandTracker, GestureDetector, GestureEvent, GestureStateMachine, StateConfig, GestureState
from gestures.spiderman import SpidermanGesture, ThumbsUpGesture

# Create snapshots directory
SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# Trigger counter
trigger_count = 0


def on_gesture_detected(event: GestureEvent):
    """Callback when a static gesture is detected."""
    pass  # Silenced - state machine handles this now


def on_web_shoot():
    """Callback when full web-shooting gesture sequence is triggered."""
    global trigger_count
    trigger_count += 1
    print(f"🕸️  WEB SHOOT! (Total: {trigger_count})")


def save_snapshot(frame, prefix="snapshot"):
    """Save a snapshot with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SNAPSHOT_DIR}/{prefix}_{timestamp}.png"
    cv2.imwrite(filename, frame)
    print(f"📸 Snapshot saved: {filename}")
    return filename


def main():
    global trigger_count
    
    # Initialize components (with pose detection enabled)
    tracker = HandTracker(enable_pose=True)
    detector = GestureDetector()
    
    # Configure state machine
    state_config = StateConfig(
        upward_threshold=0.06,      # Hand must move up ~6% of screen
        downward_threshold=0.04,    # Hand must move down ~4% of screen
        timeout_seconds=1.5,        # Reset if no progress in 1.5s
        cooldown_seconds=0.5        # Wait 0.5s between triggers
    )
    state_machine = GestureStateMachine(state_config)
    state_machine.on_trigger(on_web_shoot)
    
    # Register gestures
    spiderman_gesture = SpidermanGesture()
    detector.register_gesture(spiderman_gesture)
    detector.register_gesture(ThumbsUpGesture())
    
    # Register callback
    detector.on_gesture(on_gesture_detected)
    
    # Start video capture
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    # Toggles
    show_numbers = False
    show_pose = True  # Show elbow/wrist pose landmarks
    
    print("=" * 50)
    print("🕷️  SPIDER-MAN WEB SHOOTER")
    print("=" * 50)
    print("Press 'q' to quit")
    print("Press 's' to take a snapshot")
    print("Press 'n' to toggle landmark numbers")
    print("Press 'p' to toggle pose landmarks (elbow/wrist)")
    print("Press 'r' to reset state machine")
    print("")
    print("GESTURE SEQUENCE:")
    print("1. Show Spider-Man hand (palm down, index + pinky out)")
    print("2. Move hand UP")
    print("3. Move hand DOWN → 🕸️ WEB SHOOT!")
    print("=" * 50)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        
        # Detect hands and pose
        hand_results = tracker.detect(frame)
        pose_results = tracker.detect_pose(frame)
        
        # Draw pose landmarks (elbow, wrist, shoulder)
        if show_pose:
            frame = tracker.draw_pose_landmarks(frame, pose_results, show_labels=True)
        
        # Draw hand landmarks
        frame = tracker.draw_landmarks(frame, hand_results, show_numbers=show_numbers)
        
        # Detect static gestures
        events = detector.process(hand_results)
        
        # Check for Spider-Man gesture and get wrist position
        spiderman_detected = False
        wrist_y = None
        
        if hand_results.hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(hand_results.hand_landmarks):
                # Check if this hand has Spider-Man gesture
                confidence = spiderman_gesture.detect(hand_landmarks)
                if confidence is not None:
                    spiderman_detected = True
                    wrist_y = hand_landmarks[0].y  # Wrist Y position (normalized 0-1)
                    break
        
        # Update state machine
        current_state = state_machine.update(spiderman_detected, wrist_y)
        
        # Get state info for display
        state_info = state_machine.get_state_info()
        state_color = state_machine.get_state_color()
        
        # Draw state indicator (colored bar at top)
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), state_color, -1)
        cv2.putText(frame, f"State: {state_info['state']}", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        
        # Draw trigger count
        cv2.putText(frame, f"Web Shoots: {trigger_count}", (frame.shape[1] - 200, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        
        # Draw state-specific feedback
        y_offset = 80
        if current_state == GestureState.LOOKING:
            cv2.putText(frame, "Show Spider-Man hand...", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        elif current_state == GestureState.DETECTED:
            cv2.putText(frame, "Hand detected! Move UP", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        elif current_state == GestureState.ARMED:
            cv2.putText(frame, "ARMED! Move DOWN to shoot!", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        elif current_state == GestureState.TRIGGERED:
            cv2.putText(frame, "WEB SHOOT!", (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        
        # Show wrist position indicator if hand detected
        if wrist_y is not None:
            h = frame.shape[0]
            wrist_screen_y = int(wrist_y * h)
            cv2.line(frame, (frame.shape[1] - 30, wrist_screen_y), 
                     (frame.shape[1] - 10, wrist_screen_y), (0, 255, 0), 3)
            
            # Show initial position line if in DETECTED or ARMED state
            if state_info['initial_wrist_y'] is not None:
                initial_screen_y = int(state_info['initial_wrist_y'] * h)
                cv2.line(frame, (frame.shape[1] - 30, initial_screen_y),
                         (frame.shape[1] - 10, initial_screen_y), (255, 0, 0), 2)
        
        # Show numbers toggle status
        numbers_status = "Numbers: ON" if show_numbers else "Numbers: OFF"
        cv2.putText(frame, numbers_status, (10, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Show pose toggle status
        pose_status = "Pose: ON" if show_pose else "Pose: OFF"
        cv2.putText(frame, pose_status, (120, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("Spider-Man Web Shooter", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            save_snapshot(frame, "hand")
        elif key == ord('n'):
            show_numbers = not show_numbers
            print(f"🔢 Landmark numbers: {'ON' if show_numbers else 'OFF'}")
        elif key == ord('p'):
            show_pose = not show_pose
            print(f"🦴 Pose landmarks: {'ON' if show_pose else 'OFF'}")
        elif key == ord('r'):
            state_machine.reset()
            print("🔄 State machine reset")
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Print final counts to console
    print("\n" + "=" * 50)
    print("📊 FINAL RESULTS")
    print("=" * 50)
    print(f"  🕸️ Web Shoots: {trigger_count}")
    print("=" * 50)


if __name__ == "__main__":
    main()
