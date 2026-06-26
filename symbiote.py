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
        """Choose a body part to target."""
        # Body parts with weights (face is more challenging to hit!)
        body_parts = [
            "face", "face",  # 2x weight for face (more dramatic)
            "head",
            "torso", "torso", "torso",  # 3x weight for torso (larger target)
            "left_arm", "right_arm",
            "left_leg", "right_leg"
        ]
        body_part = random.choice(body_parts)
        
        # If we have pose landmarks, use them for accurate targeting
        if pose_landmarks:
            # Map body parts to landmark indices
            # MediaPipe Pose: 0=nose, 2=left_eye, 5=right_eye, 7=left_ear, 8=right_ear
            # 11=left_shoulder, 12=right_shoulder, 13=left_elbow, 14=right_elbow
            # 23=left_hip, 24=right_hip, 25=left_knee, 26=right_knee
            landmark_map = {
                "face": 0,  # nose (center of face)
                "head": 0,  # nose
                "torso": (11, 12),  # between shoulders
                "chest": (11, 12),  # alias for torso
                "left_arm": 13,  # left elbow
                "right_arm": 14,  # right elbow
                "left_leg": 25,  # left knee
                "right_leg": 26,  # right knee
            }
            
            target_key = landmark_map.get(body_part)
            if target_key is not None:
                if isinstance(target_key, tuple):
                    # Average of two landmarks (e.g., torso = between shoulders)
                    if target_key[0] in pose_landmarks and target_key[1] in pose_landmarks:
                        lm1 = pose_landmarks[target_key[0]]
                        lm2 = pose_landmarks[target_key[1]]
                        target_x = int((lm1['x'] + lm2['x']) / 2 * frame_width)
                        target_y = int((lm1['y'] + lm2['y']) / 2 * frame_height)
                        return target_x, target_y, body_part
                elif target_key in pose_landmarks:
                    lm = pose_landmarks[target_key]
                    target_x = int(lm['x'] * frame_width)
                    target_y = int(lm['y'] * frame_height)
                    return target_x, target_y, body_part
        
        # Fallback: target center area with some randomness
        target_x = frame_width // 2 + random.randint(-100, 100)
        target_y = frame_height // 2 + random.randint(-150, 100)
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
        
        # Remove expired balls
        self.active_balls = [b for b in self.active_balls if not b.is_expired]
        
        # Grayscale regions are permanent (symbiote infection stays)
        # No cleanup needed - regions persist until game reset
        
        return hit_balls
    
    def render_grayscale_effect(self, frame: np.ndarray) -> np.ndarray:
        """
        Render grayscale effect on player where hit by symbiotes (ADR-010).
        
        Permanent grayscale - symbiote infection stays once hit.
        """
        if not self.grayscale_regions:
            return frame
        
        h, w = frame.shape[:2]
        
        # Convert entire frame to grayscale once
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_3ch = cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2BGR)
        
        for region in self.grayscale_regions:
            cx, cy = region['cx'], region['cy']
            radius = region['radius']
            
            # Permanent grayscale - no fade (symbiote infection stays)
            
            # Create circular mask
            y_coords, x_coords = np.ogrid[:h, :w]
            mask = (x_coords - cx) ** 2 + (y_coords - cy) ** 2 <= radius ** 2
            
            # Apply full grayscale (permanent)
            frame[mask] = gray_3ch[mask]
        
        return frame
    
    def render(self, frame: np.ndarray) -> np.ndarray:
        """Render all symbiote balls on frame."""
        for ball in self.active_balls:
            self._render_ball(frame, ball)
        return frame
    
    def _render_ball(self, frame: np.ndarray, ball: SymbioteBall):
        """Render a single symbiote ball with jelly effect."""
        x, y = ball.current_x, ball.current_y
        size = ball.current_size
        
        if ball.is_destroyed:
            # Destruction animation - ball splatters
            progress = ball.destruction_progress
            alpha = int(255 * (1 - progress))
            
            # Draw splattering particles
            for i in range(8):
                angle = i * math.pi / 4 + progress * math.pi
                offset = int(progress * size * 0.8)
                px = int(x + math.cos(angle) * offset)
                py = int(y + math.sin(angle) * offset)
                particle_size = max(3, int(size * 0.3 * (1 - progress)))
                cv2.circle(frame, (px, py), particle_size, (alpha//4, alpha//4, alpha//4), -1)
            
            # Fading center
            splat_size = int(size * (1 + progress * 0.5))
            cv2.circle(frame, (x, y), splat_size // 2, (alpha//3, alpha//3, alpha//3), -1)
        else:
            # Jelly ball effect - multiple layers for depth
            # Outer glow (dark purple tint)
            cv2.circle(frame, (x, y), size + 5, (40, 20, 40), -1)
            
            # Main body (black with slight transparency effect)
            cv2.circle(frame, (x, y), size, (20, 20, 20), -1)
            
            # Inner darker core
            cv2.circle(frame, (x, y), int(size * 0.7), (10, 10, 10), -1)
            
            # Highlight (jelly reflection) - offset for 3D effect
            highlight_x = x - int(size * 0.25)
            highlight_y = y - int(size * 0.25)
            highlight_size = max(3, int(size * 0.3))
            cv2.circle(frame, (highlight_x, highlight_y), highlight_size, (80, 80, 100), -1)
            
            # Small bright spot
            cv2.circle(frame, (highlight_x, highlight_y), max(2, highlight_size // 3), (120, 120, 140), -1)
            
            # Wobble effect - draw slightly offset circles for jelly look
            # Only apply wobble when ball is large enough to handle it
            if size >= 8:
                wobble = int(math.sin(time.time() * 10 + ball.created_at) * 3)
                axis_w = max(1, size + wobble)
                axis_h = max(1, size - wobble)
                cv2.ellipse(frame, (x, y), (axis_w, axis_h), 0, 0, 360, (30, 30, 30), 2)
    
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
    
    def get_stats(self) -> dict:
        """Get current game statistics."""
        return {
            'hits_taken': self.hits_taken,
            'balls_destroyed': self.balls_destroyed,
            'active_balls': len(self.active_balls),
            'total_hit_locations': len(self.hit_locations),
        }
