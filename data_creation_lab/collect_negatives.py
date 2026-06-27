#!/usr/bin/env python3
"""
Auto-Sequencing Multi-Gesture Sample Collection for FFNN Training.

Press SPACE once to start, then it auto-advances through all gestures and hands.

Sequence:
    For each gesture (Spider-Man → Loser → L Sign → Dr. Strange → Thumbs Up → Open Palm → Closed Fist → Random):
        1. RIGHT hand (30 seconds)
        2. LEFT hand (30 seconds)  
        3. BOTH hands (15 seconds)
        
    5-second countdown between each recording.

Controls:
    SPACE - Start auto-sequence / Skip current recording
    p     - Toggle pose landmark display
    n     - Toggle landmark numbers
    q     - Quit and save all collected data
"""

import sys
import cv2
import json
import time
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent))

from tracking import HandTracker


class GestureType(Enum):
    """Available gesture types for collection."""
    SPIDERMAN = ("spiderman", "Spider-Man (POSITIVE)", True)
    LOSER = ("loser", "Loser Sign (L forehead)", False)
    L_SIGN = ("l_sign", "L Sign (index+thumb 90°)", False)
    DR_STRANGE = ("dr_strange", "Dr. Strange (fingers spread)", False)
    THUMBS_UP = ("thumbs_up", "Thumbs Up", False)
    OPEN_PALM = ("open_palm", "Open Palm", False)
    CLOSED_FIST = ("closed_fist", "Closed Fist", False)
    RANDOM = ("random", "Random/Relaxed Hand", False)
    
    @property
    def folder_name(self) -> str:
        return self.value[0]
    
    @property
    def display_name(self) -> str:
        return self.value[1]
    
    @property
    def is_positive(self) -> bool:
        return self.value[2]


# Recording sequence: (gesture, hand, duration)
GESTURE_LIST = list(GestureType)
HAND_SEQUENCE = ["RIGHT", "LEFT", "BOTH"]
DURATION_PER_HAND = {"RIGHT": 30, "LEFT": 30, "BOTH": 15}


@dataclass
class GestureSample:
    """Single frame of gesture data."""
    timestamp: float
    landmarks: Optional[list[dict]]
    pose_landmarks: Optional[dict]
    handedness: str


@dataclass
class HandCounts:
    """Track samples per hand."""
    left: int = 0
    right: int = 0
    both: int = 0
    
    @property
    def total(self) -> int:
        return self.left + self.right + self.both


class AutoSequenceCollector:
    """Auto-sequencing collector that advances through gestures and hands."""
    
    TRIM_SECONDS = 2.0  # Reduced from 4.0 for faster testing
    COUNTDOWN_SECONDS = 5
    
    def __init__(self):
        self.tracker = HandTracker()
        
        # Build full sequence: [(gesture, hand), ...]
        self.sequence = []
        for gesture in GESTURE_LIST:
            for hand in HAND_SEQUENCE:
                self.sequence.append((gesture, hand))
        
        self.sequence_index = 0
        self.total_steps = len(self.sequence)
        
        # States
        self.state = "IDLE"  # IDLE, COUNTDOWN, RECORDING, COMPLETE
        self.countdown_start = 0
        self.recording_start = 0
        self.current_samples: list[GestureSample] = []
        
        # Collected data
        self.hand_counts: dict[GestureType, HandCounts] = {
            g: HandCounts() for g in GestureType
        }
        self.all_samples: dict[GestureType, dict[str, list[GestureSample]]] = {
            g: {"Left": [], "Right": [], "Both": []} for g in GestureType
        }
        
        # Display
        self.show_pose = True
        self.show_numbers = False
        
        # Output - save to ffnn_training_samples folder
        self.base_dir = Path(__file__).parent.parent / "ffnn_training_samples"
        self.base_dir.mkdir(exist_ok=True)
    
    @property
    def current_gesture(self) -> Optional[GestureType]:
        if self.sequence_index < len(self.sequence):
            return self.sequence[self.sequence_index][0]
        return None
    
    @property
    def current_hand(self) -> Optional[str]:
        if self.sequence_index < len(self.sequence):
            return self.sequence[self.sequence_index][1]
        return None
    
    @property
    def current_duration(self) -> int:
        if self.current_hand:
            return DURATION_PER_HAND[self.current_hand]
        return 30
    
    def start_sequence(self):
        """Start the auto-sequence from current position."""
        if self.state == "IDLE" and self.sequence_index < len(self.sequence):
            self.state = "COUNTDOWN"
            self.countdown_start = time.time()
            gesture, hand = self.sequence[self.sequence_index]
            print(f"\n⏳ GET READY: {gesture.display_name} - {hand} hand")
            print(f"   Starting in {self.COUNTDOWN_SECONDS} seconds...")
    
    def skip_current(self):
        """Skip to next in sequence."""
        if self.state == "RECORDING":
            self._finish_recording()
        self._advance_sequence()
    
    def _advance_sequence(self):
        """Move to next gesture/hand combination."""
        self.sequence_index += 1
        if self.sequence_index >= len(self.sequence):
            self.state = "COMPLETE"
            print("\n🎉 ALL RECORDINGS COMPLETE!")
        else:
            self.state = "COUNTDOWN"
            self.countdown_start = time.time()
            gesture, hand = self.sequence[self.sequence_index]
            print(f"\n⏳ NEXT: {gesture.display_name} - {hand} hand")
            print(f"   Starting in {self.COUNTDOWN_SECONDS} seconds...")
    
    def update(self, frame) -> Optional[GestureSample]:
        """Update state machine, returns sample if recording."""
        current_time = time.time()
        
        if self.state == "COUNTDOWN":
            elapsed = current_time - self.countdown_start
            if elapsed >= self.COUNTDOWN_SECONDS:
                # Start recording
                self.state = "RECORDING"
                self.recording_start = current_time
                self.current_samples = []
                gesture, hand = self.sequence[self.sequence_index]
                label = "POSITIVE" if gesture.is_positive else "NEGATIVE"
                print(f"\n🔴 RECORDING [{label}]: {gesture.display_name} - {hand} hand")
                print(f"   Duration: {self.current_duration} seconds")
        
        elif self.state == "RECORDING":
            elapsed = current_time - self.recording_start
            
            # Capture sample
            sample = self._capture_frame(frame)
            if sample:
                self.current_samples.append(sample)
            
            # Check if duration complete
            if elapsed >= self.current_duration:
                self._finish_recording()
                self._advance_sequence()
            
            return sample
        
        return None
    
    def _capture_frame(self, frame) -> Optional[GestureSample]:
        """Capture hand landmarks from frame."""
        result = self.tracker.detect(frame)
        
        if not result.hand_landmarks:
            return None
        
        num_hands = len(result.hand_landmarks)
        hand = result.hand_landmarks[0]
        
        if num_hands >= 2:
            handedness = "Both"
        else:
            # MediaPipe returns handedness as a list of Category objects
            # Each has .category_name which is "Left" or "Right"
            if result.handedness and len(result.handedness) > 0:
                # handedness[0] is a list of categories for first hand
                hand_cats = result.handedness[0]
                if hand_cats and len(hand_cats) > 0:
                    handedness = hand_cats[0].category_name  # "Left" or "Right"
                else:
                    handedness = "Unknown"
            else:
                handedness = "Unknown"
        
        landmarks = [
            {"id": i, "x": lm.x, "y": lm.y, "z": lm.z}
            for i, lm in enumerate(hand)
        ]
        
        # Capture pose
        pose_data = None
        pose_result = self.tracker.detect_pose(frame)
        if pose_result:
            def tuple_to_dict(t):
                return {"x": t[0], "y": t[1], "z": t[2]} if t else None
            
            pose_data = {
                "left_shoulder": tuple_to_dict(pose_result.left_shoulder),
                "right_shoulder": tuple_to_dict(pose_result.right_shoulder),
                "left_elbow": tuple_to_dict(pose_result.left_elbow),
                "right_elbow": tuple_to_dict(pose_result.right_elbow),
                "left_wrist": tuple_to_dict(pose_result.left_wrist),
                "right_wrist": tuple_to_dict(pose_result.right_wrist),
            }
        
        return GestureSample(
            timestamp=time.time(),
            landmarks=landmarks,
            pose_landmarks=pose_data,
            handedness=handedness
        )
    
    def _finish_recording(self):
        """Apply trim and save samples."""
        if not self.current_samples:
            print("⚠️  No samples captured")
            return
        
        gesture, expected_hand = self.sequence[self.sequence_index]
        
        # Apply trim
        first_ts = self.current_samples[0].timestamp
        last_ts = self.current_samples[-1].timestamp
        
        trimmed = [
            s for s in self.current_samples
            if (s.timestamp - first_ts >= self.TRIM_SECONDS and
                last_ts - s.timestamp >= self.TRIM_SECONDS)
        ]
        
        # Categorize by actual handedness detected
        left_samples = [s for s in trimmed if s.handedness == "Left"]
        right_samples = [s for s in trimmed if s.handedness == "Right"]
        both_samples = [s for s in trimmed if s.handedness == "Both"]
        
        # Add to collections
        self.all_samples[gesture]["Left"].extend(left_samples)
        self.all_samples[gesture]["Right"].extend(right_samples)
        self.all_samples[gesture]["Both"].extend(both_samples)
        
        self.hand_counts[gesture].left += len(left_samples)
        self.hand_counts[gesture].right += len(right_samples)
        self.hand_counts[gesture].both += len(both_samples)
        
        print(f"✅ Captured {len(trimmed)} samples (L:{len(left_samples)} R:{len(right_samples)} B:{len(both_samples)})")
        
        self.current_samples = []
    
    def save_all(self):
        """Save all collected data - separate files for each hand."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved = 0
        
        for gesture in GestureType:
            counts = self.hand_counts[gesture]
            if counts.total == 0:
                continue
            
            gesture_dir = self.base_dir / gesture.folder_name
            gesture_dir.mkdir(exist_ok=True)
            
            label = "POSITIVE" if gesture.is_positive else "NEGATIVE"
            
            # Save LEFT hand samples
            if counts.left > 0:
                left_data = {
                    "gesture": gesture.folder_name,
                    "display_name": gesture.display_name,
                    "is_positive": gesture.is_positive,
                    "hand": "left",
                    "recorded_at": datetime.now().isoformat(),
                    "trim_seconds": self.TRIM_SECONDS,
                    "num_samples": counts.left,
                    "samples": [
                        {
                            "timestamp": s.timestamp,
                            "hand_landmarks": s.landmarks,
                            "pose_landmarks": s.pose_landmarks,
                            "handedness": s.handedness
                        }
                        for s in self.all_samples[gesture]["Left"]
                    ]
                }
                left_file = gesture_dir / f"{gesture.folder_name}_left_{timestamp}.json"
                with open(left_file, 'w') as f:
                    json.dump(left_data, f, indent=2)
                print(f"💾 [{label}] {gesture.display_name} LEFT: {counts.left} → {left_file.name}")
                saved += 1
            
            # Save RIGHT hand samples
            if counts.right > 0:
                right_data = {
                    "gesture": gesture.folder_name,
                    "display_name": gesture.display_name,
                    "is_positive": gesture.is_positive,
                    "hand": "right",
                    "recorded_at": datetime.now().isoformat(),
                    "trim_seconds": self.TRIM_SECONDS,
                    "num_samples": counts.right,
                    "samples": [
                        {
                            "timestamp": s.timestamp,
                            "hand_landmarks": s.landmarks,
                            "pose_landmarks": s.pose_landmarks,
                            "handedness": s.handedness
                        }
                        for s in self.all_samples[gesture]["Right"]
                    ]
                }
                right_file = gesture_dir / f"{gesture.folder_name}_right_{timestamp}.json"
                with open(right_file, 'w') as f:
                    json.dump(right_data, f, indent=2)
                print(f"💾 [{label}] {gesture.display_name} RIGHT: {counts.right} → {right_file.name}")
                saved += 1
            
            # Save BOTH hands samples
            if counts.both > 0:
                both_data = {
                    "gesture": gesture.folder_name,
                    "display_name": gesture.display_name,
                    "is_positive": gesture.is_positive,
                    "hand": "both",
                    "recorded_at": datetime.now().isoformat(),
                    "trim_seconds": self.TRIM_SECONDS,
                    "num_samples": counts.both,
                    "samples": [
                        {
                            "timestamp": s.timestamp,
                            "hand_landmarks": s.landmarks,
                            "pose_landmarks": s.pose_landmarks,
                            "handedness": s.handedness
                        }
                        for s in self.all_samples[gesture]["Both"]
                    ]
                }
                both_file = gesture_dir / f"{gesture.folder_name}_both_{timestamp}.json"
                with open(both_file, 'w') as f:
                    json.dump(both_data, f, indent=2)
                print(f"💾 [{label}] {gesture.display_name} BOTH: {counts.both} → {both_file.name}")
                saved += 1
        
        return saved
    
    def get_progress_text(self) -> str:
        """Get progress indicator."""
        return f"Step {self.sequence_index + 1}/{self.total_steps}"


def draw_ui(frame, collector: AutoSequenceCollector):
    """Draw the UI overlay."""
    h, w = frame.shape[:2]
    current_time = time.time()
    
    # Background panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (500, 200), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    # Title with progress
    title = f"AUTO-SEQUENCE COLLECTION - {collector.get_progress_text()}"
    cv2.putText(frame, title, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    if collector.state == "IDLE":
        cv2.putText(frame, "Press SPACE to start auto-sequence", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Show what's coming
        if collector.current_gesture and collector.current_hand:
            cv2.putText(frame, f"First: {collector.current_gesture.display_name} - {collector.current_hand} hand",
                        (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    elif collector.state == "COUNTDOWN":
        elapsed = current_time - collector.countdown_start
        remaining = max(0, collector.COUNTDOWN_SECONDS - elapsed)
        
        # Big countdown number
        cv2.putText(frame, f"{int(remaining) + 1}", (w // 2 - 50, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 255, 255), 8)
        
        # What's coming
        gesture = collector.current_gesture
        hand = collector.current_hand
        label = "POSITIVE" if gesture.is_positive else "NEGATIVE"
        color = (0, 255, 255) if gesture.is_positive else (200, 200, 200)
        
        cv2.putText(frame, f"GET READY: {gesture.display_name}", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, f"{hand} HAND - {collector.current_duration}s", (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, f"[{label}]", (20, 155),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    elif collector.state == "RECORDING":
        elapsed = current_time - collector.recording_start
        remaining = max(0, collector.current_duration - elapsed)
        
        gesture = collector.current_gesture
        hand = collector.current_hand
        label = "POSITIVE" if gesture.is_positive else "NEGATIVE"
        
        # Blinking REC indicator
        if int(elapsed * 2) % 2 == 0:
            cv2.circle(frame, (30, 75), 12, (0, 0, 255), -1)
        cv2.putText(frame, "REC", (50, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Current gesture/hand
        cv2.putText(frame, f"{gesture.display_name} - {hand} [{label}]", (100, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Time remaining
        cv2.putText(frame, f"Time: {remaining:.1f}s", (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Samples captured
        cv2.putText(frame, f"Frames: {len(collector.current_samples)}", (20, 155),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Trim indicator
        if elapsed < collector.TRIM_SECONDS:
            cv2.putText(frame, f"TRIMMING ({collector.TRIM_SECONDS - elapsed:.1f}s)", 
                        (w // 2 - 100, h - 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        
        # Progress bar
        progress = elapsed / collector.current_duration
        bar_w = 400
        cv2.rectangle(frame, (20, 170), (20 + bar_w, 190), (100, 100, 100), -1)
        cv2.rectangle(frame, (20, 170), (20 + int(bar_w * progress), 190), (0, 255, 0), -1)
    
    elif collector.state == "COMPLETE":
        cv2.putText(frame, "ALL COMPLETE!", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, "Press Q to save and quit", (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    
    # Instructions at bottom
    if collector.state == "RECORDING":
        instructions = "SPACE=Skip | q=Save+Quit"
    else:
        instructions = "SPACE=Start | q=Save+Quit"
    cv2.putText(frame, instructions, (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)


def main():
    print("=" * 70)
    print("AUTO-SEQUENCE GESTURE COLLECTION FOR FFNN")
    print("=" * 70)
    print()
    print("This will automatically record all gestures in sequence:")
    print()
    for i, gesture in enumerate(GESTURE_LIST, 1):
        label = "POSITIVE" if gesture.is_positive else "NEGATIVE"
        print(f"  {i}. {gesture.display_name} [{label}]")
    print()
    print("For each gesture: RIGHT hand (30s) → LEFT hand (30s) → BOTH hands (15s)")
    print(f"Total steps: {len(GESTURE_LIST) * 3} recordings")
    print(f"Estimated time: ~{len(GESTURE_LIST) * (30 + 30 + 15 + 15) // 60} minutes")
    print()
    print("Press SPACE to start, then just follow the prompts!")
    print("=" * 70)
    
    collector = AutoSequenceCollector()
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("\n📷 Camera ready. Press SPACE to begin.\n")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        
        # Detect and draw
        result = collector.tracker.detect(frame)
        if result.hand_landmarks:
            collector.tracker.draw_landmarks(frame, result, show_numbers=collector.show_numbers)
        
        if collector.show_pose:
            pose_result = collector.tracker.detect_pose(frame)
            if pose_result:
                collector.tracker.draw_pose_landmarks(frame, pose_result)
        
        # Update state machine
        collector.update(frame)
        
        # Draw UI
        draw_ui(frame, collector)
        
        cv2.imshow("Auto-Sequence Collection", frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            if collector.state == "RECORDING":
                collector._finish_recording()
            break
        
        elif key == ord(' '):
            if collector.state == "IDLE":
                collector.start_sequence()
            elif collector.state == "RECORDING":
                collector.skip_current()
        
        elif key == ord('p'):
            collector.show_pose = not collector.show_pose
        
        elif key == ord('n'):
            collector.show_numbers = not collector.show_numbers
    
    # Save
    print("\n" + "=" * 70)
    print("SAVING DATA...")
    print("=" * 70)
    saved = collector.save_all()
    
    if saved == 0:
        print("⚠️  No data collected")
    
    # Summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    total_pos = 0
    total_neg = 0
    
    for gesture in GestureType:
        counts = collector.hand_counts[gesture]
        if counts.total > 0:
            label = "POSITIVE" if gesture.is_positive else "NEGATIVE"
            print(f"  [{label}] {gesture.display_name}:")
            print(f"      L:{counts.left} R:{counts.right} B:{counts.both} = {counts.total}")
            if gesture.is_positive:
                total_pos += counts.total
            else:
                total_neg += counts.total
    
    print()
    print(f"  TOTAL POSITIVE: {total_pos}")
    print(f"  TOTAL NEGATIVE: {total_neg}")
    print(f"  GRAND TOTAL:    {total_pos + total_neg}")
    print("=" * 70)
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
