#!/usr/bin/env python3
"""
Spider-Man Web Shooter - Glove Mode

Shows hand as a filled red glove (no landmarks visible).

Usage:
    python web_shooter_glove.py           # Use original HandTracker (2 models)
    python web_shooter_glove.py --fast    # Use optimized HolisticTracker (1 model)

Controls:
    q - Quit
    r - Reset state machine
    g - Reset game (symbiotes)
    +/- - Adjust detection threshold
"""

import sys
import numpy as np

# Print tracker mode before imports
if '--fast' in sys.argv:
    print("🚀 Using OPTIMIZED HolisticTracker (single model)")
else:
    print("📦 Using original HandTracker (dual models)")

from .web_shooter_base import BaseWebShooter
from config import ACTIVE_CONFIG


class SpiderManWebShooterGlove(BaseWebShooter):
    """Web shooter with filled glove-style hand rendering (no landmarks)."""
    
    def __init__(self):
        super().__init__(ACTIVE_CONFIG)
    
    def draw_hand(self, frame: np.ndarray, hand_landmarks) -> np.ndarray:
        """Draw filled red glove (no landmarks)."""
        return self.graphics.draw_spiderman_hand_filled(frame, hand_landmarks)
    
    def draw_pose_if_enabled(self, frame: np.ndarray, pose_results) -> np.ndarray:
        """No pose landmarks in glove mode."""
        return frame
    
    def get_controls_text(self) -> str:
        return "q:quit r:reset g:reset-game +/-:threshold"
    
    def get_window_title(self) -> str:
        return "Spider-Man Web Shooter (Glove)"
    
    def handle_extra_keys(self, key: int) -> bool:
        # No extra keys in glove mode
        return False


def main():
    app = SpiderManWebShooterGlove()
    app.run()


if __name__ == "__main__":
    main()
