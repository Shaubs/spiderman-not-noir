#!/usr/bin/env python3
"""
Spider-Man Web Shooter - Landmarks Mode

Shows hand landmarks with Spider-Man styling (red connections, blue dots).

Usage:
    python web_shooter.py           # Use original HandTracker (2 models)
    python web_shooter.py --fast    # Use optimized HolisticTracker (1 model)

Controls:
    q - Quit
    r - Reset state machine
    g - Reset game (symbiotes)
    p - Toggle pose landmarks
    n - Toggle landmark numbers
    +/- - Adjust detection threshold
"""

import sys
import numpy as np

# Print tracker mode before imports
if '--fast' in sys.argv:
    print("🚀 Using OPTIMIZED HolisticTracker (single model)")
else:
    print("📦 Using original HandTracker (dual models)")

from web_shooter_base import BaseWebShooter
from config import ACTIVE_CONFIG


class SpiderManWebShooter(BaseWebShooter):
    """Web shooter with landmark-style hand rendering."""
    
    def __init__(self):
        super().__init__(ACTIVE_CONFIG)
        self.show_pose = self.config.show_pose_landmarks
        self.show_numbers = self.config.show_landmark_numbers
    
    def draw_hand(self, frame: np.ndarray, hand_landmarks) -> np.ndarray:
        """Draw Spider-Man styled landmarks."""
        return self.graphics.draw_spiderman_hand(frame, hand_landmarks, self.show_numbers)
    
    def draw_pose_if_enabled(self, frame: np.ndarray, pose_results) -> np.ndarray:
        """Draw pose landmarks if enabled."""
        if self.show_pose and pose_results:
            return self.tracker.draw_pose_landmarks(frame, pose_results, show_labels=True)
        return frame
    
    def get_controls_text(self) -> str:
        return "q:quit r:reset g:reset-game p:pose n:numbers +/-:threshold"
    
    def get_window_title(self) -> str:
        return "Spider-Man Web Shooter"
    
    def handle_extra_keys(self, key: int) -> bool:
        if key == ord('p'):
            self.show_pose = not self.show_pose
            return True
        elif key == ord('n'):
            self.show_numbers = not self.show_numbers
            return True
        return False


def main():
    app = SpiderManWebShooter()
    app.run()


if __name__ == "__main__":
    main()
