"""
Infection Spread System - BFS Rotten Oranges Algorithm

Grayscale pixels "infect" neighboring RGB pixels over time.
Uses BFS (Breadth-First Search) similar to the Rotten Oranges problem.

Each hit creates an infection source that spreads outward.
"""

import cv2
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import List, Tuple, Set
import time

from config import ScoreConfig, ACTIVE_SCORE_CONFIG


@dataclass
class InfectionSource:
    """A single infection source point."""
    x: int
    y: int
    created_at: float
    current_radius: int = 0
    max_radius: int = 100
    
    @property
    def age(self) -> float:
        return time.time() - self.created_at


class InfectionManager:
    """
    Manages BFS infection spread on the frame.
    
    Infected pixels (grayscale) spread to neighboring RGB pixels
    at a configurable rate.
    """
    
    def __init__(self, config: ScoreConfig = ACTIVE_SCORE_CONFIG):
        self.config = config
        self.infection_sources: List[InfectionSource] = []
        self.last_spread_time: float = 0
        
        # Pre-computed for efficiency
        self._infection_mask: np.ndarray = None
        self._mask_size: Tuple[int, int] = (0, 0)
    
    def add_infection_source(self, x: int, y: int):
        """Add a new infection source (e.g., where symbiote hit)."""
        if not self.config.infection_enabled:
            return
        
        source = InfectionSource(
            x=x, y=y,
            created_at=time.time(),
            max_radius=self.config.infection_max_radius
        )
        self.infection_sources.append(source)
    
    def update(self, frame_width: int, frame_height: int):
        """Update infection spread (call each frame)."""
        if not self.config.infection_enabled:
            return
        
        current_time = time.time()
        
        # Check if it's time to spread
        if current_time - self.last_spread_time >= self.config.infection_spread_rate:
            self._spread_infection()
            self.last_spread_time = current_time
        
        # Remove sources that reached max radius
        self.infection_sources = [
            s for s in self.infection_sources 
            if s.current_radius < s.max_radius
        ]
    
    def _spread_infection(self):
        """BFS spread - expand all infection sources by one step."""
        for source in self.infection_sources:
            if source.current_radius < source.max_radius:
                source.current_radius += self.config.infection_radius
    
    def apply_infection(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply infection effect to frame.
        
        Pixels within infection radius are converted to grayscale.
        Uses efficient masking instead of per-pixel BFS for performance.
        """
        if not self.config.infection_enabled or not self.infection_sources:
            return frame
        
        h, w = frame.shape[:2]
        
        # Create infection mask
        mask = np.zeros((h, w), dtype=np.uint8)
        
        for source in self.infection_sources:
            # Draw filled circle for this infection source
            cv2.circle(mask, (source.x, source.y), source.current_radius, 255, -1)
        
        # Apply grayscale to infected regions
        if np.any(mask > 0):
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            
            # Blend: infected areas become grayscale
            mask_3ch = np.stack([mask, mask, mask], axis=2) / 255.0
            frame = (frame * (1 - mask_3ch) + gray_bgr * mask_3ch).astype(np.uint8)
        
        return frame
    
    def get_infection_coverage(self, frame_width: int, frame_height: int) -> float:
        """Get percentage of frame that is infected."""
        if not self.infection_sources:
            return 0.0
        
        total_pixels = frame_width * frame_height
        infected_pixels = 0
        
        for source in self.infection_sources:
            # Approximate circle area
            infected_pixels += int(3.14159 * source.current_radius ** 2)
        
        return min(1.0, infected_pixels / total_pixels)
    
    def reset(self):
        """Clear all infection sources."""
        self.infection_sources = []
        self.last_spread_time = 0
    
    def render_debug(self, frame: np.ndarray) -> np.ndarray:
        """Render debug visualization of infection sources."""
        for source in self.infection_sources:
            # Draw infection boundary
            cv2.circle(frame, (source.x, source.y), source.current_radius, 
                      (0, 255, 0), 2)  # Green border
            # Draw source point
            cv2.circle(frame, (source.x, source.y), 5, (0, 0, 255), -1)  # Red center
        
        return frame
