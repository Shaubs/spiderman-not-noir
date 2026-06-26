"""
Symbiote Ball System

Manages enemy symbiote balls that fly towards the player.
The player must shoot them with webs before they hit.

ADR-010: Implements wobble motion and depth perception.
"""

import cv2
import math
import time
import random
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING

from symbiote_config import SymbioteConfig, ACTIVE_SYMBIOTE_CONFIG
from depth_config import DepthConfig, ACTIVE_DEPTH_CONFIG

if TYPE_CHECKING:
    from web_shooter import WebShot


@dataclass
class SymbioteBall:
    """Represents a symbiote ball flying towards the player."""
    # Target position (where on player it's aiming)
    target_x: int
    target_y: int
    # Starting position (edge of screen, appears small)
    start_x: int
    start_y: int
    # Timing
    created_at: float
    travel_time: float
    # Size range
    start_size: int
    end_size: int
    # Config references
    config: SymbioteConfig
    depth_config: DepthConfig = field(default_factory=lambda: ACTIVE_DEPTH_CONFIG)
    # Unique phase for wobble (prevents all balls wobbling in sync)
    wobble_phase: float = field(default_factory=lambda: random.random() * 2 * math.pi)
    # State
    is_destroyed: bool = False
    destroyed_at: Optional[float] = None
    hit_player: bool = False
    hit_body_part: str = ""  # e.g., "head", "torso", "left_arm", etc.
    
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
        return self.progress >= 1.0 and not self.is_destroyed
    
    @property
    def current_size(self) -> int:
        """Ball grows as it approaches (perspective effect)."""
        return int(self.start_size + (self.end_size - self.start_size) * self.progress)
    
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
        """Ball is expired if destroyed and fade animation complete, or if it hit player."""
        if self.is_destroyed and self.destroyed_at:
            return time.time() - self.destroyed_at > self.config.destruction_fade_time
        return self.hit_player
    
    @property
    def destruction_progress(self) -> float:
        """0.0 to 1.0 for destruction animation."""
        if not self.is_destroyed or not self.destroyed_at:
            return 0.0
        return min(1.0, (time.time() - self.destroyed_at) / self.config.destruction_fade_time)


class SymbioteManager:
    """Manages symbiote balls - spawning, collision, rendering."""
    
    # BFS Infection spread settings (rotten oranges style)
    INFECTION_SPREAD_INTERVAL = 0.5  # seconds between spread iterations
    INFECTION_SPREAD_AMOUNT = 15     # pixels to spread per iteration
    
    def __init__(self, config: SymbioteConfig = ACTIVE_SYMBIOTE_CONFIG,
                 depth_config: DepthConfig = ACTIVE_DEPTH_CONFIG):
        self.config = config
        self.depth_config = depth_config
        self.active_balls: List[SymbioteBall] = []
        self.last_spawn_time: float = time.time()
        self.hits_taken: int = 0
        self.balls_destroyed: int = 0
        self.hit_locations: List[dict] = []  # Records where player was hit
        # ADR-010: Grayscale hit regions
        self.grayscale_regions: List[dict] = []  # {cx, cy, radius, created, duration}
        
        # OPTIMIZATION: Cached grayscale mask (computed once per frame size)
        self._cached_grayscale_mask: Optional[np.ndarray] = None
        self._cached_frame_size: Optional[tuple] = None
        self._mask_dirty: bool = True  # Flag to rebuild mask
        
        # BFS infection spread timing
        self._last_infection_spread: float = time.time()
        
    def spawn_ball(self, frame_width: int, frame_height: int, 
                   pose_landmarks: Optional[dict] = None):
        """Spawn a new symbiote ball targeting the player."""
        if len(self.active_balls) >= self.config.max_active:
            return
        
        # Choose a target on the player's body
        target_x, target_y, body_part = self._choose_target(
            frame_width, frame_height, pose_landmarks
        )
        
        # Spawn from random edge of screen (appears to come from distance)
        start_x, start_y = self._choose_spawn_point(frame_width, frame_height)
        
        ball = SymbioteBall(
            target_x=target_x,
            target_y=target_y,
            start_x=start_x,
            start_y=start_y,
            created_at=time.time(),
            travel_time=self.config.travel_time,
            start_size=self.config.start_size,
            end_size=self.config.end_size,
            config=self.config,
            depth_config=self.depth_config,
        )
        ball.hit_body_part = body_part
        self.active_balls.append(ball)
    
    def _choose_target(self, frame_width: int, frame_height: int,
                       pose_landmarks: Optional[dict]) -> tuple:
        """Choose a random target position anywhere on screen."""
        # Random position anywhere on screen (not targeting person specifically)
        # Favor center-ish area but allow full screen coverage
        margin_x = int(frame_width * 0.1)
        margin_y = int(frame_height * 0.1)
        
        target_x = random.randint(margin_x, frame_width - margin_x)
        target_y = random.randint(margin_y, frame_height - margin_y)
        
        # Label for display (generic since not targeting body)
        body_part = "screen"
        
        return target_x, target_y, body_part
    
    def _choose_spawn_point(self, frame_width: int, frame_height: int) -> tuple:
        """Choose spawn point at edge of screen."""
        # Spawn from corners or edges (gives sense of depth)
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
    
    def check_web_collision(self, web_start_x: int, web_start_y: int,
                            web_end_x: int, web_end_y: int,
                            web_progress: float) -> Optional[SymbioteBall]:
        """
        Check if a web intersects with any symbiote ball.
        
        Args:
            web_start_x, web_start_y: Web origin point
            web_end_x, web_end_y: Web target point (full extension)
            web_progress: How far the web has traveled (0.0 to 1.0)
        
        Returns:
            The destroyed ball, or None if no collision
        """
        # Calculate current web endpoint
        current_end_x = int(web_start_x + (web_end_x - web_start_x) * web_progress)
        current_end_y = int(web_start_y + (web_end_y - web_start_y) * web_progress)
        
        for ball in self.active_balls:
            if ball.is_destroyed:
                continue
            
            # Get current ball position and size
            ball_x, ball_y = ball.current_x, ball.current_y
            ball_radius = ball.current_size * self.config.hit_radius_multiplier
            
            # Check if web line intersects ball
            if self._line_circle_intersection(
                web_start_x, web_start_y,
                current_end_x, current_end_y,
                ball_x, ball_y, ball_radius
            ):
                ball.is_destroyed = True
                ball.destroyed_at = time.time()
                self.balls_destroyed += 1
                return ball
        return None
    
    def _line_circle_intersection(self, x1: int, y1: int, x2: int, y2: int,
                                    cx: int, cy: int, radius: float) -> bool:
        """Check if line segment intersects circle."""
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
    
    def update(self, frame_width: int, frame_height: int, 
               pose_landmarks: Optional[dict] = None) -> List[SymbioteBall]:
        """
        Update all balls, spawn new ones, check for player hits.
        
        Returns:
            List of balls that hit the player this frame
        """
        current_time = time.time()
        
        # Spawn new ball if interval passed
        if current_time - self.last_spawn_time >= self.config.spawn_interval:
            self.spawn_ball(frame_width, frame_height, pose_landmarks)
            self.last_spawn_time = current_time
        
        # Check for balls that hit player
        hit_balls = []
        for ball in self.active_balls:
            if ball.has_reached_player and not ball.hit_player:
                ball.hit_player = True
                self.hits_taken += 1
                hit_balls.append(ball)
                self.hit_locations.append({
                    'time': current_time,
                    'body_part': ball.hit_body_part,
                    'x': ball.target_x,
                    'y': ball.target_y
                })
                # ADR-010: Add grayscale region for hit effect
                self.grayscale_regions.append({
                    'cx': ball.target_x,
                    'cy': ball.target_y,
                    'radius': int(ball.end_size * self.config.grayscale_radius_multiplier),
                    'created': current_time,
                    'duration': self.config.grayscale_duration
                })
                # Mark mask as needing rebuild
                self._mask_dirty = True
        
        # Remove expired balls
        self.active_balls = [b for b in self.active_balls if not b.is_expired]
        
        # BFS Infection spread - expand grayscale regions every 0.5 seconds
        if current_time - self._last_infection_spread >= self.INFECTION_SPREAD_INTERVAL:
            self._spread_infection()
            self._last_infection_spread = current_time
        
        return hit_balls
    
    def _spread_infection(self):
        """
        BFS-style infection spread (Rotten Oranges algorithm).
        
        Each grayscale region expands outward by INFECTION_SPREAD_AMOUNT pixels,
        simulating the symbiote infection spreading across the frame.
        """
        if not self.grayscale_regions:
            return
        
        # Expand each region's radius
        for region in self.grayscale_regions:
            region['radius'] += self.INFECTION_SPREAD_AMOUNT
        
        # Mark mask as dirty so it gets rebuilt
        self._mask_dirty = True
    
    def render_grayscale_effect(self, frame: np.ndarray) -> np.ndarray:
        """
        Render grayscale effect on player where hit by symbiotes (ADR-010).
        
        OPTIMIZED:
        - Cached mask: Only rebuild when new regions added
        - Bounding box: Only convert affected areas to grayscale
        - Skip already-gray: Regions don't re-compute overlap
        """
        if not self.grayscale_regions:
            return frame
        
        h, w = frame.shape[:2]
        
        # Check if we need to rebuild the cached mask
        if self._mask_dirty or self._cached_frame_size != (h, w):
            self._rebuild_grayscale_mask(h, w)
        
        # If no mask (shouldn't happen), return
        if self._cached_grayscale_mask is None:
            return frame
        
        # OPTIMIZATION: Find bounding box of all grayscale regions
        # Only convert that section to grayscale, not full frame
        min_x, min_y = w, h
        max_x, max_y = 0, 0
        
        for region in self.grayscale_regions:
            cx, cy, r = region['cx'], region['cy'], region['radius']
            min_x = min(min_x, max(0, cx - r))
            min_y = min(min_y, max(0, cy - r))
            max_x = max(max_x, min(w, cx + r))
            max_y = max(max_y, min(h, cy + r))
        
        # Ensure valid bounds
        if min_x >= max_x or min_y >= max_y:
            return frame
        
        # OPTIMIZATION: Only convert bounding box region to grayscale
        roi = frame[min_y:max_y, min_x:max_x]
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray_3ch_roi = cv2.cvtColor(gray_roi, cv2.COLOR_GRAY2BGR)
        
        # Apply cached mask (only the ROI portion)
        mask_roi = self._cached_grayscale_mask[min_y:max_y, min_x:max_x]
        frame[min_y:max_y, min_x:max_x][mask_roi] = gray_3ch_roi[mask_roi]
        
        return frame
    
    def _rebuild_grayscale_mask(self, h: int, w: int):
        """
        Rebuild the cached grayscale mask.
        
        OPTIMIZATION: Only called when new regions added or frame size changes.
        All regions are combined into one mask for efficient application.
        """
        # Create combined mask for all regions
        combined_mask = np.zeros((h, w), dtype=bool)
        
        # Pre-compute coordinate grids once
        y_coords, x_coords = np.ogrid[:h, :w]
        
        for region in self.grayscale_regions:
            cx, cy = region['cx'], region['cy']
            radius = region['radius']
            
            # OPTIMIZATION: Only compute for bounding box, not full frame
            r = radius
            y_min, y_max = max(0, cy - r), min(h, cy + r + 1)
            x_min, x_max = max(0, cx - r), min(w, cx + r + 1)
            
            # Create local mask for this region
            local_y = y_coords[y_min:y_max, 0:1]
            local_x = x_coords[0:1, x_min:x_max]
            local_mask = (local_x - cx) ** 2 + (local_y - cy) ** 2 <= radius ** 2
            
            # OR into combined mask (union of all regions)
            combined_mask[y_min:y_max, x_min:x_max] |= local_mask
        
        self._cached_grayscale_mask = combined_mask
        self._cached_frame_size = (h, w)
        self._mask_dirty = False
    
    def render(self, frame: np.ndarray) -> np.ndarray:
        """Render all symbiote balls on frame."""
        for ball in self.active_balls:
            self._render_ball(frame, ball)
        return frame
    
    def _render_ball(self, frame: np.ndarray, ball: SymbioteBall):
        """
        Render a single symbiote ball.
        
        OPTIMIZED: Reduced from 6 draw calls to 3 draw calls per ball.
        - Combined outer glow + main body → single gradient circle
        - Simplified highlight → single bright spot
        - Removed inner core (minimal visual impact)
        """
        x, y = ball.current_x, ball.current_y
        size = ball.current_size
        
        if ball.is_destroyed:
            # Destruction animation - simplified to 4 particles instead of 8
            progress = ball.destruction_progress
            alpha = int(255 * (1 - progress))
            
            # Draw 4 splattering particles (reduced from 8)
            for i in range(4):
                angle = i * math.pi / 2 + progress * math.pi
                offset = int(progress * size * 0.8)
                px = int(x + math.cos(angle) * offset)
                py = int(y + math.sin(angle) * offset)
                particle_size = max(3, int(size * 0.3 * (1 - progress)))
                cv2.circle(frame, (px, py), particle_size, (alpha//4, alpha//4, alpha//4), -1)
            
            # Fading center
            splat_size = int(size * (1 + progress * 0.5))
            cv2.circle(frame, (x, y), splat_size // 2, (alpha//3, alpha//3, alpha//3), -1)
        else:
            # OPTIMIZED: Simplified jelly ball (3 draw calls instead of 6)
            
            # 1. Main body with glow effect (single circle)
            cv2.circle(frame, (x, y), size + 3, (30, 20, 30), -1)  # Dark purple-ish glow
            cv2.circle(frame, (x, y), size, (15, 15, 15), -1)       # Main black body
            
            # 2. Single highlight (combined reflection spot)
            if size >= 6:
                highlight_x = x - int(size * 0.25)
                highlight_y = y - int(size * 0.25)
                highlight_size = max(2, int(size * 0.25))
                cv2.circle(frame, (highlight_x, highlight_y), highlight_size, (100, 100, 120), -1)
            
            # 3. Wobble outline (only for larger balls)
            if size >= 10:
                wobble = int(math.sin(time.time() * 10 + ball.created_at) * 2)
                axis_w = max(1, size + wobble)
                axis_h = max(1, size - wobble)
                cv2.ellipse(frame, (x, y), (axis_w, axis_h), 0, 0, 360, (40, 40, 40), 1)
    
    def render_hit_markers(self, frame: np.ndarray) -> np.ndarray:
        """Render recent hit location markers."""
        current_time = time.time()
        recent_hits = [hit for hit in self.hit_locations 
                       if current_time - hit['time'] < self.config.hit_marker_duration]
        
        for hit in recent_hits:
            age = current_time - hit['time']
            alpha = int(255 * (1 - age / self.config.hit_marker_duration))
            cv2.circle(frame, (hit['x'], hit['y']), 30, (0, 0, alpha), 3)
            cv2.putText(frame, hit['body_part'].upper(), (hit['x'] - 30, hit['y'] - 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, alpha), 2)
        
        return frame
    
    def reset(self):
        """Reset the symbiote manager state."""
        self.active_balls.clear()
        self.hits_taken = 0
        self.balls_destroyed = 0
        self.hit_locations.clear()
        self.grayscale_regions.clear()
        self.last_spawn_time = time.time()
        self._last_infection_spread = time.time()
        # Clear cached mask
        self._cached_grayscale_mask = None
        self._cached_frame_size = None
        self._mask_dirty = True
    
    def get_stats(self) -> dict:
        """Get current game statistics."""
        return {
            'hits_taken': self.hits_taken,
            'balls_destroyed': self.balls_destroyed,
            'active_balls': len(self.active_balls),
            'total_hit_locations': len(self.hit_locations),
        }
    
    def get_grayscale_coverage(self, frame_width: int, frame_height: int) -> float:
        """
        Calculate the percentage of the frame covered by grayscale regions.
        
        Returns:
            Float from 0.0 to 1.0 representing coverage percentage.
        """
        if not self.grayscale_regions:
            return 0.0
        
        # If we have a cached mask, count the True pixels
        if self._cached_grayscale_mask is not None:
            h, w = self._cached_grayscale_mask.shape
            covered_pixels = np.sum(self._cached_grayscale_mask)
            total_pixels = h * w
            return min(1.0, covered_pixels / total_pixels)
        
        # Fallback: estimate from circle areas (may overcount overlaps)
        total_pixels = frame_width * frame_height
        covered_pixels = 0
        
        for region in self.grayscale_regions:
            r = region['radius']
            # Circle area = pi * r^2
            covered_pixels += int(3.14159 * r * r)
        
        return min(1.0, covered_pixels / total_pixels)
