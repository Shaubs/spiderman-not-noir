"""
Dr. Strange Portal Ring System

A magical portal ring that spawns randomly during the game.
Only one ring can exist at a time. The ring travels towards the player
similar to symbiote balls but with a distinctive fire/orange portal effect.

The player must intercept the ring with their hand (using Dr. Strange gesture)
to capture it, otherwise it passes through and disappears.
"""

import cv2
import math
import time
import random
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from config import DepthConfig, ACTIVE_DEPTH_CONFIG, FIRE_COLORS


@dataclass
class DrStrangeRingConfig:
    """Configuration for the Dr. Strange portal ring."""
    
    # === SPAWNING ===
    
    # Minimum time between ring spawns (seconds)
    min_spawn_interval: float = 15.0
    
    # Maximum time between ring spawns (seconds)
    max_spawn_interval: float = 15.0
    
    # === MOVEMENT ===
    
    # How long the ring takes to reach the player (seconds)
    travel_time: float = 4.0
    
    # === SIZE ===
    
    # Starting radius when ring spawns (far away)
    start_radius: int = 5
    
    # Final radius when ring reaches player (close up)
    end_radius: int = 60
    
    # === INTERACTION ===
    
    # Radius multiplier for capture detection
    capture_radius_multiplier: float = 1.5
    
    # Time window to capture the ring (seconds before it expires)
    capture_window: float = 1.0
    
    # === ANIMATION ===
    
    # How long the capture/miss animation lasts
    animation_duration: float = 0.5


# Default configuration
DEFAULT_RING_CONFIG = DrStrangeRingConfig()

# FIRE_COLORS imported from config/colors.py


@dataclass
class DrStrangeRing:
    """Represents a Dr. Strange portal ring flying towards the player."""
    
    # Target position
    target_x: int
    target_y: int
    
    # Starting position (edge of screen)
    start_x: int
    start_y: int
    
    # Timing
    created_at: float
    travel_time: float
    
    # Size range
    start_radius: int
    end_radius: int
    
    # Config reference
    config: DrStrangeRingConfig
    depth_config: DepthConfig = field(default_factory=lambda: ACTIVE_DEPTH_CONFIG)
    
    # Unique phase for wobble/animation
    wobble_phase: float = field(default_factory=lambda: random.random() * 2 * math.pi)
    rotation_angle: float = 0.0
    
    # State
    is_captured: bool = False
    is_missed: bool = False
    captured_at: Optional[float] = None
    missed_at: Optional[float] = None
    
    @property
    def age(self) -> float:
        return time.time() - self.created_at
    
    @property
    def progress(self) -> float:
        """0.0 (spawned) to 1.0 (reached player)."""
        return min(1.0, self.age / self.travel_time)
    
    @property
    def z_depth(self) -> float:
        """Current Z-depth (1.0 = far, 0.0 = at player)."""
        return self.depth_config.z_from_progress(self.progress)
    
    @property
    def has_reached_player(self) -> bool:
        return self.progress >= 1.0 and not self.is_captured
    
    @property
    def current_radius(self) -> int:
        """Ring grows as it approaches (perspective effect)."""
        return int(self.start_radius + (self.end_radius - self.start_radius) * self.progress)
    
    @property
    def _base_x(self) -> float:
        """Linear X position without wobble."""
        return self.start_x + (self.target_x - self.start_x) * self.progress
    
    @property
    def _base_y(self) -> float:
        """Linear Y position without wobble."""
        return self.start_y + (self.target_y - self.start_y) * self.progress
    
    @property
    def _wobble_offset(self) -> tuple:
        """Calculate wobble offset perpendicular to travel direction."""
        if not self.depth_config.wobble_enabled:
            return (0.0, 0.0)
        
        # Direction vector (normalized)
        dx = self.target_x - self.start_x
        dy = self.target_y - self.start_y
        length = math.sqrt(dx * dx + dy * dy)
        
        if length == 0:
            return (0.0, 0.0)
        
        # Perpendicular unit vector (rotate 90 degrees)
        perp_x = -dy / length
        perp_y = dx / length
        
        # Get wobble magnitude from depth config
        wobble = self.depth_config.calculate_wobble(
            self.age, self.progress, self.wobble_phase
        )
        
        return (perp_x * wobble, perp_y * wobble)
    
    @property
    def current_x(self) -> int:
        """Current X position with wobble."""
        wobble_x, _ = self._wobble_offset
        return int(self._base_x + wobble_x)
    
    @property
    def current_y(self) -> int:
        """Current Y position with wobble."""
        _, wobble_y = self._wobble_offset
        return int(self._base_y + wobble_y)
    
    @property
    def is_expired(self) -> bool:
        """Ring is expired if animation complete after capture/miss."""
        if self.is_captured and self.captured_at:
            return time.time() - self.captured_at > self.config.animation_duration
        if self.is_missed and self.missed_at:
            return time.time() - self.missed_at > self.config.animation_duration
        # Also expire if it passed the player without being captured
        if self.has_reached_player and not self.is_captured:
            self.is_missed = True
            self.missed_at = time.time()
        return False
    
    @property
    def animation_progress(self) -> float:
        """0.0 to 1.0 for capture/miss animation."""
        if self.is_captured and self.captured_at:
            return min(1.0, (time.time() - self.captured_at) / self.config.animation_duration)
        if self.is_missed and self.missed_at:
            return min(1.0, (time.time() - self.missed_at) / self.config.animation_duration)
        return 0.0
    
    def is_in_capture_zone(self) -> bool:
        """Check if ring is close enough to be captured."""
        # Ring is capturable anytime during its journey (after it starts moving)
        return self.progress >= 0.1  # Capturable after first 10% of journey


class DrStrangeRingManager:
    """Manages the Dr. Strange portal ring - spawning, collision, rendering."""
    
    def __init__(self, config: DrStrangeRingConfig = DEFAULT_RING_CONFIG,
                 depth_config: DepthConfig = ACTIVE_DEPTH_CONFIG):
        self.config = config
        self.depth_config = depth_config
        self.active_ring: Optional[DrStrangeRing] = None
        self.last_spawn_time: float = time.time()
        self.next_spawn_delay: float = self._random_spawn_delay()
        self.rings_captured: int = 0
        self.rings_missed: int = 0
        self.ring_caught: bool = False  # Once caught, never spawn again
    
    def _random_spawn_delay(self) -> float:
        """Generate a random delay until the next ring spawn."""
        return random.uniform(self.config.min_spawn_interval, self.config.max_spawn_interval)
    
    def should_spawn(self) -> bool:
        """Check if it's time to spawn a new ring."""
        if self.ring_caught:
            return False  # Never spawn again after caught
        if self.active_ring is not None:
            return False  # Only one ring at a time
        
        elapsed = time.time() - self.last_spawn_time
        return elapsed >= self.next_spawn_delay
    
    def spawn_ring(self, frame_width: int, frame_height: int):
        """Spawn a new Dr. Strange portal ring."""
        if self.active_ring is not None:
            return  # Only one ring at a time
        
        # Choose random target position (center-ish area)
        margin_x = int(frame_width * 0.2)
        margin_y = int(frame_height * 0.2)
        target_x = random.randint(margin_x, frame_width - margin_x)
        target_y = random.randint(margin_y, frame_height - margin_y)
        
        # Spawn from random edge
        start_x, start_y = self._choose_spawn_point(frame_width, frame_height)
        
        self.active_ring = DrStrangeRing(
            target_x=target_x,
            target_y=target_y,
            start_x=start_x,
            start_y=start_y,
            created_at=time.time(),
            travel_time=self.config.travel_time,
            start_radius=self.config.start_radius,
            end_radius=self.config.end_radius,
            config=self.config,
            depth_config=self.depth_config,
        )
        
        self.last_spawn_time = time.time()
        self.next_spawn_delay = self._random_spawn_delay()
    
    def _choose_spawn_point(self, frame_width: int, frame_height: int) -> tuple:
        """Choose spawn point at edge of screen."""
        edge = random.choice(['top', 'left', 'right', 'top_left', 'top_right'])
        
        if edge == 'top':
            return random.randint(100, frame_width - 100), 0
        elif edge == 'left':
            return 0, random.randint(50, frame_height // 2)
        elif edge == 'right':
            return frame_width, random.randint(50, frame_height // 2)
        elif edge == 'top_left':
            return random.randint(0, 50), random.randint(0, 50)
        else:  # top_right
            return random.randint(frame_width - 50, frame_width), random.randint(0, 50)
    
    def check_hand_capture(self, hand_x: int, hand_y: int, 
                           dr_strange_gesture_active: bool) -> bool:
        """
        Check if the player's hand (with Dr. Strange gesture) captures the ring.
        
        Args:
            hand_x, hand_y: Hand position (center between landmarks 16 and 20)
            dr_strange_gesture_active: Whether the Dr. Strange gesture is active
        
        Returns:
            True if ring was captured, False otherwise
        """
        if self.active_ring is None or not dr_strange_gesture_active:
            return False
        
        ring = self.active_ring
        if ring.is_captured or ring.is_missed:
            return False
        
        # Check if ring is in capture zone
        if not ring.is_in_capture_zone():
            return False
        
        # Check distance from hand to ring center
        ring_x, ring_y = ring.current_x, ring.current_y
        distance = math.sqrt((hand_x - ring_x)**2 + (hand_y - ring_y)**2)
        capture_radius = ring.current_radius * self.config.capture_radius_multiplier
        
        if distance <= capture_radius:
            ring.is_captured = True
            ring.captured_at = time.time()
            self.rings_captured += 1
            self.ring_caught = True  # Never spawn again
            return True
        
        return False
    
    def update(self, frame_width: int, frame_height: int):
        """Update ring state - call this every frame."""
        # Check if we should spawn a new ring
        if self.should_spawn():
            self.spawn_ring(frame_width, frame_height)
        
        # Update active ring
        if self.active_ring is not None:
            ring = self.active_ring
            
            # Update rotation angle
            ring.rotation_angle += 0.1
            
            # Check if ring has reached player without being captured
            if ring.has_reached_player and not ring.is_captured and not ring.is_missed:
                ring.is_missed = True
                ring.missed_at = time.time()
                self.rings_missed += 1
            
            # Remove expired ring
            if ring.is_expired:
                self.active_ring = None
    
    def render(self, frame: np.ndarray) -> np.ndarray:
        """Render the active ring on the frame."""
        if self.active_ring is None:
            return frame
        
        ring = self.active_ring
        cx, cy = ring.current_x, ring.current_y
        radius = ring.current_radius
        angle = ring.rotation_angle
        
        # Handle capture animation
        if ring.is_captured:
            # Shrink and brighten on capture
            anim_progress = ring.animation_progress
            radius = int(radius * (1 - anim_progress * 0.5))  # Shrink
            # Draw capture flash
            flash_radius = int(radius + 30 * (1 - anim_progress))
            cv2.circle(frame, (cx, cy), flash_radius, FIRE_COLORS[5], -1)
            return frame
        
        # Handle miss animation
        if ring.is_missed:
            # Fade out on miss
            anim_progress = ring.animation_progress
            alpha = 1.0 - anim_progress
            if alpha <= 0:
                return frame
            # Draw fading ring
            for i, r_offset in enumerate([6, 4, 2, 0]):
                color = FIRE_COLORS[(i + 2) % len(FIRE_COLORS)]
                faded_color = tuple(int(c * alpha) for c in color)
                cv2.circle(frame, (cx, cy), radius + r_offset, faded_color, 2)
            return frame
        
        # Normal rendering - fire portal ring
        
        # Outer glow rings
        for i, r_offset in enumerate([10, 7, 4]):
            color = FIRE_COLORS[i % len(FIRE_COLORS)]
            cv2.circle(frame, (cx, cy), radius + r_offset, color, 1)
        
        # Main ring with fire gradient
        cv2.circle(frame, (cx, cy), radius + 3, FIRE_COLORS[2], 2)
        cv2.circle(frame, (cx, cy), radius + 1, FIRE_COLORS[4], 2)
        cv2.circle(frame, (cx, cy), radius, FIRE_COLORS[5], 2)
        
        # Rotating fire particles around the ring
        num_particles = 10
        for i in range(num_particles):
            particle_angle = angle + (i * 2 * math.pi / num_particles)
            particle_x = int(cx + radius * math.cos(particle_angle))
            particle_y = int(cy + radius * math.sin(particle_angle))
            color = FIRE_COLORS[(i + int(angle * 2)) % len(FIRE_COLORS)]
            cv2.circle(frame, (particle_x, particle_y), 4, color, -1)
        
        # Inner rotating sparks (opposite direction)
        for i in range(6):
            spark_angle = -angle * 1.5 + (i * 2 * math.pi / 6)
            spark_x = int(cx + (radius * 0.6) * math.cos(spark_angle))
            spark_y = int(cy + (radius * 0.6) * math.sin(spark_angle))
            cv2.circle(frame, (spark_x, spark_y), 3, FIRE_COLORS[5], -1)
        
        # Pulsing center glow
        pulse = 3 + 2 * math.sin(angle * 2)
        cv2.circle(frame, (cx, cy), int(pulse), FIRE_COLORS[5], -1)
        
        # Draw "CATCH IT!" indicator when in capture zone
        if ring.is_in_capture_zone():
            # Draw at top of screen for visibility
            cv2.putText(frame, ">> CATCH THE RING! <<", (cx - 100, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, FIRE_COLORS[5], 2)
            # Also draw near the ring
            cv2.putText(frame, "CATCH!", (cx - 30, cy - radius - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, FIRE_COLORS[5], 2)
        
        return frame
    
    def reset(self):
        """Reset the manager state (for new game)."""
        self.active_ring = None
        self.last_spawn_time = time.time()
        self.next_spawn_delay = self._random_spawn_delay()
        self.rings_captured = 0
        self.rings_missed = 0
        self.ring_caught = False  # Allow spawning again after reset
