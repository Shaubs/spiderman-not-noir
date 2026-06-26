"""
Z-Axis Depth Configuration

Explicit Z-coordinate system for depth perception in the 2D game.

Coordinate System:
  - X: horizontal (0 = left, w = right)
  - Y: vertical (0 = top, h = bottom)  
  - Z: depth (0.0 = at player/screen, 1.0 = far away)

The Z-axis is simulated through:
  1. SIZE: Objects appear smaller when far, larger when close
  2. TIME: Objects take time to travel from far to near
  
This module provides conversions between Z, size, and time.
"""

from dataclasses import dataclass
import math


@dataclass
class DepthConfig:
    """Configuration for Z-axis depth simulation."""
    
    # === Z-AXIS RANGE ===
    z_far: float = 1.0           # Depth when spawned (far away)
    z_near: float = 0.0          # Depth at player (screen plane)
    
    # === SIZE MAPPING ===
    # Objects appear smaller when far, larger when close
    size_at_far: int = 1         # 1 pixel at z=1.0 (far)
    size_at_near: int = 80       # 80 pixels at z=0.0 (close)
    
    # === TIME MAPPING ===
    travel_time: float = 3.0     # Seconds to traverse z_far → z_near
    
    # === WOBBLE MOTION ===
    wobble_enabled: bool = True
    wobble_amplitude: float = 20.0   # Max pixels of lateral wobble
    wobble_frequency: float = 3.0    # Oscillations per second (Hz)
    wobble_decay: bool = True        # Amplitude decreases as approaching
    
    # === WEB SPREAD ===
    web_spread_angle: float = 10.0   # Degrees from center line (narrower cone)
    web_line_count: int = 3          # Number of web lines (1, 3, 5, etc.)
    
    def z_from_progress(self, progress: float) -> float:
        """
        Convert time progress (0-1) to z-depth (1-0).
        
        Progress 0.0 = just spawned (far)
        Progress 1.0 = reached player (close)
        """
        return self.z_far - (self.z_far - self.z_near) * progress
    
    def progress_from_z(self, z: float) -> float:
        """
        Convert z-depth to time progress.
        
        Z 1.0 = far (progress 0.0)
        Z 0.0 = close (progress 1.0)
        """
        if self.z_far == self.z_near:
            return 1.0
        return (self.z_far - z) / (self.z_far - self.z_near)
    
    def size_from_z(self, z: float) -> int:
        """
        Convert z-depth to visual size (pixels).
        
        Z 1.0 (far) → size_at_far (1 pixel)
        Z 0.0 (close) → size_at_near (80 pixels)
        """
        normalized = (self.z_far - z) / (self.z_far - self.z_near)
        return int(self.size_at_far + (self.size_at_near - self.size_at_far) * normalized)
    
    def size_from_progress(self, progress: float) -> int:
        """
        Convert time progress directly to size.
        
        Progress 0.0 → 1 pixel
        Progress 1.0 → 80 pixels
        """
        return int(self.size_at_far + (self.size_at_near - self.size_at_far) * progress)
    
    def z_from_size(self, size: int) -> float:
        """
        Convert visual size back to z-depth.
        
        Useful for determining depth of an object by its apparent size.
        """
        if self.size_at_near == self.size_at_far:
            return self.z_near
        normalized = (size - self.size_at_far) / (self.size_at_near - self.size_at_far)
        return self.z_far - (self.z_far - self.z_near) * normalized
    
    def calculate_wobble(self, time_elapsed: float, progress: float, 
                          unique_phase: float = 0.0) -> float:
        """
        Calculate wobble offset for organic ball motion.
        
        Args:
            time_elapsed: Seconds since ball was created
            progress: Travel progress (0.0 to 1.0)
            unique_phase: Unique offset for this ball (prevents sync)
        
        Returns:
            Pixel offset perpendicular to travel direction
        """
        if not self.wobble_enabled:
            return 0.0
        
        # Amplitude decreases as ball approaches (more focused on target)
        amplitude = self.wobble_amplitude
        if self.wobble_decay:
            amplitude *= (1.0 - progress)
        
        # Sinusoidal oscillation
        phase = time_elapsed * self.wobble_frequency * 2 * math.pi + unique_phase
        return math.sin(phase) * amplitude
    
    def get_web_angles(self) -> list:
        """
        Get angles for multi-line web spread.
        
        Returns list of angles in radians relative to center direction.
        Example for 3 lines with 15° spread: [-0.2618, 0, 0.2618]
        """
        if self.web_line_count == 1:
            return [0.0]
        
        spread_rad = math.radians(self.web_spread_angle)
        angles = []
        
        # Generate symmetric angles around center
        half_count = (self.web_line_count - 1) // 2
        for i in range(-half_count, half_count + 1):
            angle = i * spread_rad / half_count if half_count > 0 else 0
            angles.append(angle)
        
        return angles


# === PRESETS ===

# Default balanced depth config
DEFAULT_DEPTH = DepthConfig(
    z_far=1.0,
    z_near=0.0,
    size_at_far=1,
    size_at_near=80,
    travel_time=3.0,
    wobble_enabled=True,
    wobble_amplitude=20.0,
    wobble_frequency=3.0,
    wobble_decay=True,
    web_spread_angle=15.0,
    web_line_count=3,
)

# More subtle depth (smaller size range)
SUBTLE_DEPTH = DepthConfig(
    z_far=1.0,
    z_near=0.0,
    size_at_far=5,
    size_at_near=60,
    travel_time=3.0,
    wobble_enabled=True,
    wobble_amplitude=10.0,
    wobble_frequency=2.0,
    wobble_decay=True,
    web_spread_angle=10.0,
    web_line_count=3,
)

# Dramatic depth (extreme size range)
DRAMATIC_DEPTH = DepthConfig(
    z_far=1.0,
    z_near=0.0,
    size_at_far=1,
    size_at_near=100,
    travel_time=2.5,
    wobble_enabled=True,
    wobble_amplitude=30.0,
    wobble_frequency=4.0,
    wobble_decay=True,
    web_spread_angle=20.0,
    web_line_count=5,
)

# No wobble (straight trajectories)
STATIC_DEPTH = DepthConfig(
    z_far=1.0,
    z_near=0.0,
    size_at_far=1,
    size_at_near=80,
    travel_time=3.0,
    wobble_enabled=False,
    wobble_amplitude=0.0,
    wobble_frequency=0.0,
    wobble_decay=False,
    web_spread_angle=15.0,
    web_line_count=3,
)

# === ACTIVE CONFIG ===
# Change this to switch presets
ACTIVE_DEPTH_CONFIG = DEFAULT_DEPTH
