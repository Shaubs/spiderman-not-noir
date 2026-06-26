"""
Symbiote Ball Configuration

Settings for the enemy symbiote balls that attack the player.
Adjust these to make the game easier or harder.

Note: Depth perception settings (wobble, z-axis) are in depth_config/z_config.py
"""

from dataclasses import dataclass


@dataclass
class SymbioteConfig:
    """Configuration for symbiote ball enemies."""
    
    # === SPAWNING ===
    
    # Seconds between ball spawns
    spawn_interval: float = 2.0
    
    # Maximum balls on screen at once
    max_active: int = 5
    
    # === MOVEMENT ===
    
    # How long a ball takes to reach the player (seconds)
    # Lower = faster balls = harder game
    travel_time: float = 3.0
    
    # === SIZE (perspective effect - ADR-010) ===
    
    # Starting size when ball spawns (far away)
    # Set to 1 for maximum depth perception
    start_size: int = 1
    
    # Final size when ball reaches player (close up)
    end_size: int = 80
    
    # === COLLISION ===
    
    # Multiplier for hit detection radius
    # Higher = easier to hit with webs
    hit_radius_multiplier: float = 1.2
    
    # === ANIMATION ===
    
    # How long the destruction animation lasts (seconds)
    destruction_fade_time: float = 0.3
    
    # How long hit markers stay on screen (seconds)
    hit_marker_duration: float = 2.0
    
    # === GRAYSCALE HIT EFFECT (ADR-010) ===
    
    # Radius multiplier for grayscale effect on player
    grayscale_radius_multiplier: float = 1.5
    
    # How long grayscale effect lasts (seconds)
    grayscale_duration: float = 3.0


# === DIFFICULTY PRESETS ===

EASY_SYMBIOTE = SymbioteConfig(
    spawn_interval=3.0,
    max_active=3,
    travel_time=4.0,
    start_size=1,      # ADR-010: Start at 1px for depth perception
    end_size=100,
    hit_radius_multiplier=1.5,
    grayscale_duration=2.0,
)

NORMAL_SYMBIOTE = SymbioteConfig(
    spawn_interval=2.0,
    max_active=5,
    travel_time=3.0,
    start_size=1,      # ADR-010: Start at 1px for depth perception
    end_size=80,
    hit_radius_multiplier=1.2,
    grayscale_duration=3.0,
)

HARD_SYMBIOTE = SymbioteConfig(
    spawn_interval=1.5,
    max_active=6,
    travel_time=2.5,
    start_size=1,      # ADR-010: Start at 1px for depth perception
    end_size=70,
    hit_radius_multiplier=1.0,
    grayscale_duration=4.0,
)

NIGHTMARE_SYMBIOTE = SymbioteConfig(
    spawn_interval=1.0,
    max_active=8,
    travel_time=2.0,
    start_size=1,      # ADR-010: Start at 1px for depth perception
    end_size=60,
    hit_radius_multiplier=0.8,
    grayscale_duration=5.0,
)

# === ACTIVE CONFIG ===
# Change this to switch difficulty
ACTIVE_SYMBIOTE_CONFIG = NORMAL_SYMBIOTE
