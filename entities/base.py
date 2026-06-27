"""
Base Entity Classes

Provides abstract base classes for game entities with common functionality:
- FlyingEntity: Objects that fly from spawn point to target with depth/wobble
- EntityManager: Manages spawning, updating, and removing entities
"""

import math
import time
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, TypeVar, Generic

from config import DepthConfig, ACTIVE_DEPTH_CONFIG


@dataclass
class FlyingEntity(ABC):
    """
    Base class for entities that fly towards the player.
    
    Provides common functionality for:
    - Position tracking (start → target with progress)
    - Depth perception (z-axis simulation via size)
    - Wobble motion for organic movement
    - Timing and lifecycle management
    
    Subclasses must implement:
    - is_expired: When to remove the entity
    - current_size (or current_radius): Visual size based on progress
    """
    
    # === POSITION ===
    target_x: int
    target_y: int
    start_x: int
    start_y: int
    
    # === TIMING ===
    created_at: float
    travel_time: float
    
    # === CONFIG ===
    depth_config: DepthConfig = field(default_factory=lambda: ACTIVE_DEPTH_CONFIG)
    
    # === WOBBLE ===
    wobble_phase: float = field(default_factory=lambda: random.random() * 2 * math.pi)
    
    @property
    def age(self) -> float:
        """Time since entity was created."""
        return time.time() - self.created_at
    
    @property
    def progress(self) -> float:
        """Travel progress from 0.0 (spawned) to 1.0 (reached target)."""
        return min(1.0, self.age / self.travel_time)
    
    @property
    def z_depth(self) -> float:
        """Current Z-depth (1.0 = far, 0.0 = at player)."""
        return self.depth_config.z_from_progress(self.progress)
    
    @property
    def has_reached_target(self) -> bool:
        """Whether entity has reached its target position."""
        return self.progress >= 1.0
    
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
        
        # Direction vector
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
    @abstractmethod
    def is_expired(self) -> bool:
        """Whether entity should be removed from the game."""
        pass
    
    def distance_to(self, x: int, y: int) -> float:
        """Calculate distance from current position to a point."""
        dx = self.current_x - x
        dy = self.current_y - y
        return math.sqrt(dx * dx + dy * dy)


# Type variable for generic EntityManager
T = TypeVar('T', bound=FlyingEntity)


class EntityManager(ABC, Generic[T]):
    """
    Base class for managing collections of entities.
    
    Provides common functionality for:
    - Spawning entities at intervals
    - Updating active entities
    - Removing expired entities
    - Tracking statistics
    
    Subclasses must implement:
    - spawn_entity: Create and add a new entity
    - _choose_spawn_point: Select spawn location
    - _choose_target: Select target location
    """
    
    def __init__(self, spawn_interval: float = 2.0, max_active: int = 5):
        self.spawn_interval = spawn_interval
        self.max_active = max_active
        self.active_entities: List[T] = []
        self.last_spawn_time: float = time.time()
    
    @abstractmethod
    def spawn_entity(self, frame_width: int, frame_height: int, **kwargs) -> Optional[T]:
        """Create and add a new entity. Returns the created entity or None."""
        pass
    
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
    
    def _choose_target(self, frame_width: int, frame_height: int) -> tuple:
        """Choose target position (default: random center-ish area)."""
        margin_x = int(frame_width * 0.1)
        margin_y = int(frame_height * 0.1)
        target_x = random.randint(margin_x, frame_width - margin_x)
        target_y = random.randint(margin_y, frame_height - margin_y)
        return target_x, target_y
    
    def should_spawn(self) -> bool:
        """Check if it's time to spawn a new entity."""
        if len(self.active_entities) >= self.max_active:
            return False
        return time.time() - self.last_spawn_time >= self.spawn_interval
    
    def update(self, frame_width: int, frame_height: int, **kwargs) -> List[T]:
        """
        Update all entities, spawn new ones if needed, remove expired.
        
        Returns:
            List of entities that reached the player this frame
        """
        # Spawn new entity if needed
        if self.should_spawn():
            self.spawn_entity(frame_width, frame_height, **kwargs)
            self.last_spawn_time = time.time()
        
        # Find entities that reached player
        reached_player = [e for e in self.active_entities 
                         if e.has_reached_target and not e.is_expired]
        
        # Remove expired entities
        self.active_entities = [e for e in self.active_entities if not e.is_expired]
        
        return reached_player
    
    def reset(self):
        """Reset manager state for new game."""
        self.active_entities.clear()
        self.last_spawn_time = time.time()
    
    @property
    def count(self) -> int:
        """Number of active entities."""
        return len(self.active_entities)


def line_circle_intersection(x1: int, y1: int, x2: int, y2: int,
                              cx: int, cy: int, radius: float) -> bool:
    """
    Check if a line segment intersects with a circle.
    
    Useful for web/projectile collision detection with circular entities.
    
    Args:
        x1, y1: Line segment start point
        x2, y2: Line segment end point
        cx, cy: Circle center
        radius: Circle radius
    
    Returns:
        True if line intersects circle
    """
    # Vector from start to end
    dx = x2 - x1
    dy = y2 - y1
    
    # Vector from start to circle center
    fx = x1 - cx
    fy = y1 - cy
    
    a = dx * dx + dy * dy
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - radius * radius
    
    if a == 0:
        # Line is a point
        return math.sqrt(fx * fx + fy * fy) <= radius
    
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return False
    
    discriminant = math.sqrt(discriminant)
    t1 = (-b - discriminant) / (2 * a)
    t2 = (-b + discriminant) / (2 * a)
    
    # Check if intersection is within line segment
    return (0 <= t1 <= 1) or (0 <= t2 <= 1) or (t1 < 0 and t2 > 1)
