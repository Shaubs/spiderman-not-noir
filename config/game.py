"""
Game Configuration

Main game settings including trigger thresholds, cooldowns, and detection settings.

Adjust these values to make the game faster or slower.
Lower values = faster/more sensitive
Higher values = slower/more deliberate

Presets:
- FAST: Quick responsive gameplay, may have accidental triggers
- NORMAL: Balanced gameplay
- SLOW: Deliberate, precise control required
"""

from dataclasses import dataclass


@dataclass
class GameConfig:
    """All tunable game parameters in one place."""
    
    # === TRIGGER THRESHOLDS ===
    
    # Rapid Toggle Trigger
    # How many times detection must toggle (DETECTED↔LOOKING) to fire
    toggle_count_threshold: int = 2  # Lower = easier to trigger with flicks
    
    # Time window to count toggles (seconds)
    toggle_window_seconds: float = 0.5  # Shorter = need faster flicks
    
    # Sustained Hold Trigger
    # How long to hold steady to fire (seconds)
    sustained_hold_seconds: float = 0.4  # Shorter = fires quicker when holding
    
    # Armed Motion Trigger
    # How far UP to move hand to fire (normalized, 0-1 scale)
    # 0.03 = 3% of frame height
    upward_threshold: float = 0.04  # Lower = less movement needed
    
    # === COOLDOWN ===
    
    # Time between shots (seconds)
    # Prevents rapid-fire accidental triggers
    cooldown_seconds: float = 0.3  # Shorter = faster shooting
    
    # === CLASSIFIER ===
    
    # Confidence threshold for Spider-Man hand detection
    detection_threshold: float = 0.7  # Lower = more sensitive, more false positives
    
    # === WEB EFFECT ===
    
    # How long the web effect lasts on screen (seconds)
    web_duration: float = 0.5  # Shorter = snappier effect
    
    # Starting thickness of web line (pixels)
    web_thickness: int = 5
    
    # === DISPLAY ===
    
    # Show pose landmarks (shoulder, elbow, wrist)
    show_pose_landmarks: bool = True
    
    # Show landmark numbers on hand
    show_landmark_numbers: bool = False


# === PRESETS ===
# Note: Symbiote settings are in symbiote.py

FAST_CONFIG = GameConfig(
    toggle_count_threshold=2,
    toggle_window_seconds=0.4,
    sustained_hold_seconds=0.3,
    upward_threshold=0.03,
    cooldown_seconds=0.2,
    detection_threshold=0.65,
    web_duration=0.4,
)

NORMAL_CONFIG = GameConfig(
    toggle_count_threshold=2,
    toggle_window_seconds=0.5,
    sustained_hold_seconds=0.4,
    upward_threshold=0.04,
    cooldown_seconds=0.3,
    detection_threshold=0.7,
    web_duration=0.5,
)

SLOW_CONFIG = GameConfig(
    toggle_count_threshold=3,
    toggle_window_seconds=1.0,
    sustained_hold_seconds=1.0,
    upward_threshold=0.06,
    cooldown_seconds=0.8,
    detection_threshold=0.75,
    web_duration=0.8,
)

# === ACTIVE CONFIG ===
# Change this to switch presets: FAST_CONFIG, NORMAL_CONFIG, or SLOW_CONFIG
# Or customize GameConfig() directly
ACTIVE_CONFIG = FAST_CONFIG

__all__ = [
    'GameConfig',
    'FAST_CONFIG', 'NORMAL_CONFIG', 'SLOW_CONFIG',
    'ACTIVE_CONFIG',
]
