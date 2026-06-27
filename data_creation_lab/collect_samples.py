"""
Data Collection Lab for Gesture Training

This module captures hand and pose landmark data for training the Random Forest classifier.
Features:
- Press 's' to start/stop recording
- Automatically trims first and last 4 seconds of each recording
- Saves samples with hand landmarks + pose landmarks
- Visual feedback during recording
"""

import cv2
import os
import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracking import HandTracker, PoseLandmarks


@dataclass
class FrameSample:
    """Single frame of captured data."""
    timestamp: float
    hand_landmarks: Optional[List[dict]] = None
    pose_landmarks: Optional[dict] = None
    handedness: Optional[str] = None  # 'Left' or 'Right'


class DataCollector:
    """Collects and processes gesture training data."""
    
    TRIM_SECONDS = 4  # Seconds to trim from start and end
    
    def __init__(self, output_dir: str = "data_creation_lab/samples"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.tracker = HandTracker(enable_pose=True)
        self.recording = False
        self.samples: List[FrameSample] = []
        self.record_start_time: float = 0
        self.fps = 30  # Approximate FPS for calculations
        
    def start_recording(self):
        """Start recording samples."""
        self.recording = True
        self.samples = []
        self.record_start_time = time.time()
        print("\n🔴 RECORDING STARTED")
        print(f"   First {self.TRIM_SECONDS}s will be trimmed (get ready)")
        print(f"   Last {self.TRIM_SECONDS}s will be trimmed (move to press 's')")
        
    def stop_recording(self) -> int:
        """Stop recording and trim samples."""
        self.recording = False
        record_duration = time.time() - self.record_start_time
        
        print(f"\n⏹️  RECORDING STOPPED")
        print(f"   Total duration: {record_duration:.1f}s")
        print(f"   Raw samples: {len(self.samples)}")
        
        # Trim first and last 4 seconds
        trimmed_samples = self._trim_samples()
        
        print(f"   After trimming: {len(trimmed_samples)} samples")
        
        if len(trimmed_samples) > 0:
            self._save_samples(trimmed_samples)
        else:
            print("   ⚠️  No samples left after trimming! Record longer.")
        
        return len(trimmed_samples)
    
    def _trim_samples(self) -> List[FrameSample]:
        """Remove first and last TRIM_SECONDS of samples."""
        if not self.samples:
            return []
        
        start_time = self.samples[0].timestamp
        end_time = self.samples[-1].timestamp
        
        trim_start = start_time + self.TRIM_SECONDS
        trim_end = end_time - self.TRIM_SECONDS
        
        if trim_start >= trim_end:
            return []  # Recording too short
        
        return [s for s in self.samples if trim_start <= s.timestamp <= trim_end]
    
    def _save_samples(self, samples: List[FrameSample]):
        """Save samples to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"spiderman_samples_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Convert to serializable format
        data = {
            "gesture": "spiderman_palm_up",
            "recorded_at": datetime.now().isoformat(),
            "num_samples": len(samples),
            "trim_seconds": self.TRIM_SECONDS,
            "samples": []
        }
        
        for sample in samples:
            sample_dict = {
                "timestamp": sample.timestamp,
                "hand_landmarks": sample.hand_landmarks,
                "pose_landmarks": sample.pose_landmarks,
                "handedness": sample.handedness
            }
            data["samples"].append(sample_dict)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"   ✅ Saved to: {filepath}")
        return filepath
    
    def capture_frame(self, frame) -> FrameSample:
        """Capture landmarks from a single frame."""
        hand_results = self.tracker.detect(frame)
        pose_results = self.tracker.detect_pose(frame)
        
        sample = FrameSample(timestamp=time.time())
        
        # Extract hand landmarks
        if hand_results.hand_landmarks:
            hand_lm = hand_results.hand_landmarks[0]  # First hand
            sample.hand_landmarks = [
                {"id": i, "x": lm.x, "y": lm.y, "z": lm.z}
                for i, lm in enumerate(hand_lm)
            ]
            
            # Get handedness if available
            if hand_results.handedness:
                sample.handedness = hand_results.handedness[0][0].category_name
        
        # Extract pose landmarks
        if pose_results:
            sample.pose_landmarks = {
                "left_shoulder": pose_results.left_shoulder,
                "right_shoulder": pose_results.right_shoulder,
                "left_elbow": pose_results.left_elbow,
                "right_elbow": pose_results.right_elbow,
                "left_wrist": pose_results.left_wrist,
                "right_wrist": pose_results.right_wrist
            }
        
        return sample
    
    def add_sample(self, sample: FrameSample):
        """Add a sample to the recording buffer."""
        if self.recording:
            self.samples.append(sample)
    
    def get_recording_info(self) -> dict:
        """Get current recording status info."""
        if not self.recording:
            return {"recording": False}
        
        elapsed = time.time() - self.record_start_time
        usable = max(0, elapsed - 2 * self.TRIM_SECONDS)
        
        return {
            "recording": True,
            "elapsed": elapsed,
            "usable_time": usable,
            "sample_count": len(self.samples),
            "in_trim_zone": elapsed < self.TRIM_SECONDS
        }


def draw_recording_overlay(frame, info: dict):
    """Draw recording status overlay on frame."""
    h, w = frame.shape[:2]
    
    if not info["recording"]:
        # Not recording - show instructions
        cv2.putText(frame, "Press 'S' to start recording", (10, h - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return frame
    
    # Recording indicator
    color = (0, 0, 255)  # Red
    if info["in_trim_zone"]:
        color = (0, 165, 255)  # Orange - in trim zone
        cv2.putText(frame, "GET READY...", (w//2 - 80, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    # Flashing record indicator
    if int(time.time() * 2) % 2:
        cv2.circle(frame, (30, 30), 15, color, -1)
    cv2.putText(frame, "REC", (55, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    
    # Time info
    elapsed_text = f"Elapsed: {info['elapsed']:.1f}s"
    usable_text = f"Usable: {info['usable_time']:.1f}s"
    samples_text = f"Samples: {info['sample_count']}"
    
    cv2.putText(frame, elapsed_text, (10, h - 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, usable_text, (10, h - 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(frame, samples_text, (10, h - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Instructions
    cv2.putText(frame, "Press 'S' to stop", (w - 180, h - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return frame


def main():
    """Main data collection loop."""
    collector = DataCollector()
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    show_pose = True
    show_numbers = False
    
    print("=" * 60)
    print("🧪 DATA COLLECTION LAB - Spider-Man Gesture")
    print("=" * 60)
    print("")
    print("INSTRUCTIONS:")
    print("  1. Position your hand with PALM FACING UP")
    print("  2. Make Spider-Man gesture (index + pinky extended)")
    print("  3. Press 'S' to START recording")
    print("  4. Hold the gesture steady")
    print("  5. Press 'S' again to STOP")
    print("")
    print(f"  ⏱️  First {DataCollector.TRIM_SECONDS}s and last {DataCollector.TRIM_SECONDS}s are auto-trimmed")
    print("")
    print("CONTROLS:")
    print("  's' - Start/Stop recording")
    print("  'p' - Toggle pose landmarks")
    print("  'n' - Toggle hand numbers")
    print("  'q' - Quit")
    print("=" * 60)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        
        # Capture sample
        sample = collector.capture_frame(frame)
        collector.add_sample(sample)
        
        # Draw landmarks
        hand_results = collector.tracker.detect(frame)
        if show_pose:
            pose_results = collector.tracker.detect_pose(frame)
            frame = collector.tracker.draw_pose_landmarks(frame, pose_results)
        frame = collector.tracker.draw_landmarks(frame, hand_results, show_numbers=show_numbers)
        
        # Draw recording overlay
        info = collector.get_recording_info()
        frame = draw_recording_overlay(frame, info)
        
        # Show hand detected status
        if sample.hand_landmarks:
            cv2.putText(frame, "Hand: DETECTED", (frame.shape[1] - 180, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "Hand: NOT FOUND", (frame.shape[1] - 180, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        cv2.imshow("Data Collection Lab", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            if collector.recording:
                collector.stop_recording()
            else:
                collector.start_recording()
        elif key == ord('p'):
            show_pose = not show_pose
        elif key == ord('n'):
            show_numbers = not show_numbers
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
