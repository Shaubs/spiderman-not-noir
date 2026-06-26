"""
Web Effect Renderer - Shared module for web shooting effects.

Contains:
- WebLine: Single line in web spread
- WebShot: Active web shot with 3-line spread
- WebEffectRenderer: Renders particle/dot trail comic book style webs

Used by both web_shooter.py and web_shooter_glove.py
"""

import cv2
import time
import math
import numpy as np
from dataclasses import dataclass
from typing import List

from config import ACTIVE_CONFIG
from depth_config import ACTIVE_DEPTH_CONFIG


@dataclass
class WebLine:
    """A single line in the web spread."""
    start_x: int
    start_y: int
    end_x: int
    end_y: int


@dataclass
class WebShot:
    """Represents an active web shot effect (ADR-010: 3-line spread)."""
    start_x: int
    start_y: int
    center_end_x: int
    center_end_y: int
    left_end_x: int
    left_end_y: int
    right_end_x: int
    right_end_y: int
    created_at: float
    duration: float = ACTIVE_CONFIG.web_duration
    
    @property
    def age(self) -> float:
        return time.time() - self.created_at
    
    @property
    def is_expired(self) -> bool:
        return self.age > self.duration
    
    @property
    def progress(self) -> float:
        """0.0 to 1.0 representing web travel progress."""
        return min(1.0, self.age / self.duration)
    
    @property
    def opacity(self) -> float:
        """Fade out as web travels."""
        return max(0.0, 1.0 - (self.age / self.duration) ** 0.5)
    
    @property
    def thickness(self) -> int:
        """Start thick, end thin."""
        base_thickness = ACTIVE_CONFIG.web_thickness
        return max(1, int(base_thickness * (1.0 - self.progress * 0.8)))
    
    def get_lines(self) -> List[WebLine]:
        """Get all 3 web lines for collision detection."""
        return [
            WebLine(self.start_x, self.start_y, self.left_end_x, self.left_end_y),
            WebLine(self.start_x, self.start_y, self.center_end_x, self.center_end_y),
            WebLine(self.start_x, self.start_y, self.right_end_x, self.right_end_y),
        ]


class WebEffectRenderer:
    """
    Renders web shooting effects on video frames.
    
    Features:
    - 3-line spread (ADR-010)
    - Particle/dot trail comic book style
    - ~2ms rendering for 3 lines
    """
    
    def __init__(self, depth_config=ACTIVE_DEPTH_CONFIG):
        self.active_webs: List[WebShot] = []
        self.depth_config = depth_config
    
    def shoot_web(self, elbow_x: int, elbow_y: int, 
                   wrist_x: int, wrist_y: int,
                   frame_width: int, frame_height: int) -> WebShot:
        """Create a new web shot with 3-line spread from WRIST using elbow→wrist direction."""
        dx = wrist_x - elbow_x
        dy = wrist_y - elbow_y
        
        length = math.sqrt(dx**2 + dy**2)
        if length > 0:
            dx /= length
            dy /= length
        
        center_angle = math.atan2(dy, dx)
        spread_rad = math.radians(self.depth_config.web_spread_angle)
        left_angle = center_angle - spread_rad
        right_angle = center_angle + spread_rad
        
        max_extend = max(frame_width, frame_height) * 2
        
        center_end_x = int(wrist_x + math.cos(center_angle) * max_extend)
        center_end_y = int(wrist_y + math.sin(center_angle) * max_extend)
        left_end_x = int(wrist_x + math.cos(left_angle) * max_extend)
        left_end_y = int(wrist_y + math.sin(left_angle) * max_extend)
        right_end_x = int(wrist_x + math.cos(right_angle) * max_extend)
        right_end_y = int(wrist_y + math.sin(right_angle) * max_extend)
        
        web = WebShot(
            start_x=wrist_x,
            start_y=wrist_y,
            center_end_x=center_end_x,
            center_end_y=center_end_y,
            left_end_x=left_end_x,
            left_end_y=left_end_y,
            right_end_x=right_end_x,
            right_end_y=right_end_y,
            created_at=time.time()
        )
        self.active_webs.append(web)
        return web
    
    def update_and_render(self, frame: np.ndarray) -> np.ndarray:
        """Update web effects and render them on the frame."""
        self.active_webs = [w for w in self.active_webs if not w.is_expired]
        for web in self.active_webs:
            self._render_web(frame, web)
        return frame
    
    def _render_web(self, frame: np.ndarray, web: WebShot):
        """Render a 3-line web shot with glow effect (simple lines)."""
        progress = web.progress
        alpha = int(255 * web.opacity)
        
        lines = [
            (web.left_end_x, web.left_end_y),
            (web.center_end_x, web.center_end_y),
            (web.right_end_x, web.right_end_y),
        ]
        
        # Calculate thickness that decreases with progress
        glow_thickness = max(1, int(8 * (1 - progress * 0.5)))
        core_thickness = max(1, int(4 * (1 - progress * 0.5)))
        
        for end_x, end_y in lines:
            current_end_x = int(web.start_x + (end_x - web.start_x) * progress)
            current_end_y = int(web.start_y + (end_y - web.start_y) * progress)
            
            # Outer glow (blue tint)
            cv2.line(frame, (web.start_x, web.start_y), (current_end_x, current_end_y),
                     (alpha // 2, alpha // 2, alpha), glow_thickness)
            # Core line (white)
            cv2.line(frame, (web.start_x, web.start_y), (current_end_x, current_end_y),
                     (alpha, alpha, alpha), core_thickness)
            # Bright center
            if core_thickness > 2:
                cv2.line(frame, (web.start_x, web.start_y), (current_end_x, current_end_y),
                         (255, 255, 255), max(1, core_thickness // 2))
        
        # Origin point with glow
        cv2.circle(frame, (web.start_x, web.start_y), web.thickness + 4,
                   (alpha // 3, alpha // 3, alpha // 2), -1)
        cv2.circle(frame, (web.start_x, web.start_y), web.thickness + 2,
                   (0, 0, alpha), -1)
        cv2.circle(frame, (web.start_x - 2, web.start_y - 2), web.thickness // 2,
                   (alpha, alpha, alpha), -1)
