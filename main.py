import cv2
import os
from datetime import datetime
from hand_tracker import HandTracker
from gesture_detector import GestureDetector, GestureEvent
from gestures.spiderman import SpidermanGesture, ThumbsUpGesture

# Create snapshots directory
SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def on_gesture_detected(event: GestureEvent):
    """Callback when a gesture is detected."""
    print(f"🎯 Gesture: {event.name} | Confidence: {event.confidence:.2f} | Hand: {event.hand_index + 1}")


def save_snapshot(frame, prefix="snapshot"):
    """Save a snapshot with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SNAPSHOT_DIR}/{prefix}_{timestamp}.png"
    cv2.imwrite(filename, frame)
    print(f"📸 Snapshot saved: {filename}")
    return filename


def main():
    # Initialize components
    tracker = HandTracker()
    detector = GestureDetector()
    
    # Register gestures
    detector.register_gesture(SpidermanGesture())
    detector.register_gesture(ThumbsUpGesture())
    
    # Register callback
    detector.on_gesture(on_gesture_detected)
    
    # Start video capture
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    # Toggle for showing landmark numbers
    show_numbers = True
    
    print("=" * 50)
    print("🕷️  SPIDER-MAN GESTURE DETECTOR")
    print("=" * 50)
    print("Press 'q' to quit")
    print("Press 's' to take a snapshot")
    print("Press 'n' to toggle landmark numbers")
    print("Show Spider-Man gesture (palm down, index + pinky out)")
    print("=" * 50)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        
        # Detect hands
        results = tracker.detect(frame)
        
        # Draw landmarks with optional numbers
        frame = tracker.draw_landmarks(frame, results, show_numbers=show_numbers)
        
        # Detect gestures
        events = detector.process(results)
        
        # Print counter to console when gesture detected
        if events:
            for event in events:
                print(f"📊 COUNTER UPDATE - {event.name}: {detector.get_count(event.name)}")
        
        # Display gesture counts on screen
        y_offset = 30
        for gesture_name, count in detector.gesture_counts.items():
            text = f"{gesture_name}: {count}"
            cv2.putText(frame, text, (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            y_offset += 40
        
        # Show visual feedback for detected gestures
        if events:
            cv2.putText(frame, "GESTURE DETECTED!", (150, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        # Show numbers toggle status
        numbers_status = "Numbers: ON" if show_numbers else "Numbers: OFF"
        cv2.putText(frame, numbers_status, (10, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("Spider-Man Gesture Detector", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            save_snapshot(frame, "hand")
        elif key == ord('n'):
            show_numbers = not show_numbers
            print(f"🔢 Landmark numbers: {'ON' if show_numbers else 'OFF'}")
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Print final counts to console
    print("\n" + "=" * 50)
    print("📊 FINAL GESTURE COUNTS")
    print("=" * 50)
    for gesture_name, count in detector.gesture_counts.items():
        print(f"  {gesture_name}: {count}")
    print("=" * 50)


if __name__ == "__main__":
    main()
