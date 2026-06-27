"""
Graphics Manager for Spider-Man Web Shooter

Handles:
- THWIP! PNG overlay (pre-loaded)
- Spider-Man styled hand landmarks
- Enhanced web line rendering with glow

All graphics optimized for minimal compute cost.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
import time


@dataclass
class ThwipEffect:
    """Active THWIP! effect instance."""
    x: int
    y: int
    created_at: float
    duration: float = 0.8


class GraphicsManager:
    """
    Manages all game graphics effects.
    
    Pre-loads assets at startup for minimal per-frame cost.
    """
    
    # Spider-Man colors
    SPIDERMAN_RED = (0, 0, 200)      # BGR
    SPIDERMAN_BLUE = (200, 50, 50)   # BGR
    SPIDERMAN_BLACK = (0, 0, 0)
    SPIDERMAN_WHITE = (255, 255, 255)
    
    # Finger landmark indices
    FINGERTIPS = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky tips
    
    # Hand connections for web pattern
    HAND_CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),        # Index
        (0, 9), (9, 10), (10, 11), (11, 12),   # Middle
        (0, 13), (13, 14), (14, 15), (15, 16), # Ring
        (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
        (5, 9), (9, 13), (13, 17)              # Palm web pattern
    ]
    
    def __init__(self, assets_path: Optional[Path] = None):
        if assets_path is None:
            # Assets folder is at project root, not in rendering/
            assets_path = Path(__file__).parent.parent / "assets"
        
        self.assets_path = assets_path
        
        # Pre-load THWIP image
        self.thwip_image: Optional[np.ndarray] = None
        self.thwip_sizes: dict = {}  # Pre-scaled versions
        self._load_thwip()
        
        # Active THWIP effects
        self.active_thwips: List[ThwipEffect] = []
    
    def _load_thwip(self):
        """Load and pre-scale THWIP image."""
        thwip_path = self.assets_path / "thwip.png"
        if thwip_path.exists():
            # Load with alpha channel
            self.thwip_image = cv2.imread(str(thwip_path), cv2.IMREAD_UNCHANGED)
            if self.thwip_image is not None:
                # Pre-scale to common sizes
                h, w = self.thwip_image.shape[:2]
                for scale in [0.3, 0.5, 0.8, 1.0]:
                    new_w, new_h = int(w * scale), int(h * scale)
                    scaled = cv2.resize(self.thwip_image, (new_w, new_h))
                    self.thwip_sizes[scale] = scaled
                print(f"✅ Loaded THWIP image: {w}x{h}")
            else:
                print("⚠️ Failed to load THWIP image")
        else:
            print(f"⚠️ THWIP image not found at {thwip_path}")
    
    def trigger_thwip(self, x: int, y: int, duration: float = 0.8):
        """Trigger a THWIP effect at position."""
        self.active_thwips.append(ThwipEffect(x=x, y=y, created_at=time.time(), duration=duration))
    
    def render_thwip_effects(self, frame: np.ndarray) -> np.ndarray:
        """Render all active THWIP effects."""
        current_time = time.time()
        
        # Remove expired effects
        self.active_thwips = [t for t in self.active_thwips 
                              if current_time - t.created_at < t.duration]
        
        if not self.thwip_sizes:
            return frame
        
        for thwip in self.active_thwips:
            age = current_time - thwip.created_at
            progress = age / thwip.duration
            
            # Fade out
            alpha_mult = 1.0 - progress
            
            # Scale based on age (start big, shrink slightly)
            if progress < 0.3:
                scale_key = 0.8
            elif progress < 0.6:
                scale_key = 0.5
            else:
                scale_key = 0.3
            
            img = self.thwip_sizes.get(scale_key, self.thwip_sizes.get(0.5))
            if img is None:
                continue
            
            frame = self._overlay_image(frame, img, thwip.x, thwip.y, alpha_mult)
        
        return frame
    
    def _overlay_image(self, frame: np.ndarray, overlay: np.ndarray, 
                       cx: int, cy: int, alpha_mult: float = 1.0) -> np.ndarray:
        """Overlay image with alpha blending at center position."""
        h, w = overlay.shape[:2]
        fh, fw = frame.shape[:2]
        
        # Calculate position (centered)
        x1 = cx - w // 2
        y1 = cy - h // 2
        x2 = x1 + w
        y2 = y1 + h
        
        # Clip to frame bounds
        ox1 = max(0, -x1)
        oy1 = max(0, -y1)
        ox2 = w - max(0, x2 - fw)
        oy2 = h - max(0, y2 - fh)
        
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(fw, x2)
        y2 = min(fh, y2)
        
        if x2 <= x1 or y2 <= y1:
            return frame
        
        # Get overlay region
        overlay_region = overlay[oy1:oy2, ox1:ox2]
        
        if overlay_region.shape[2] == 4:
            # Has alpha channel
            alpha = (overlay_region[:, :, 3] / 255.0) * alpha_mult
            alpha = alpha[:, :, np.newaxis]
            
            rgb = overlay_region[:, :, :3]
            
            # Blend
            frame[y1:y2, x1:x2] = (
                frame[y1:y2, x1:x2] * (1 - alpha) + rgb * alpha
            ).astype(np.uint8)
        else:
            # No alpha, just overlay
            frame[y1:y2, x1:x2] = overlay_region
        
        return frame
    
    def draw_spiderman_hand(self, frame: np.ndarray, landmarks: list, 
                            show_numbers: bool = False) -> np.ndarray:
        """
        Draw hand landmarks with Spider-Man styling.
        
        - Red fingertips
        - Blue other joints
        - Red web-pattern connections
        - Black outlines (comic style)
        """
        if not landmarks:
            return frame
        
        h, w = frame.shape[:2]
        
        # Draw connections first (web pattern)
        for start_idx, end_idx in self.HAND_CONNECTIONS:
            start = landmarks[start_idx]
            end = landmarks[end_idx]
            start_pt = (int(start.x * w), int(start.y * h))
            end_pt = (int(end.x * w), int(end.y * h))
            
            # Black outline
            cv2.line(frame, start_pt, end_pt, self.SPIDERMAN_BLACK, 4)
            # Red web line
            cv2.line(frame, start_pt, end_pt, self.SPIDERMAN_RED, 2)
        
        # Draw landmarks
        for idx, landmark in enumerate(landmarks):
            cx, cy = int(landmark.x * w), int(landmark.y * h)
            
            # Fingertips are red, others are blue
            if idx in self.FINGERTIPS:
                color = self.SPIDERMAN_RED
                radius = 8
            else:
                color = self.SPIDERMAN_BLUE
                radius = 6
            
            # Black outline
            cv2.circle(frame, (cx, cy), radius + 2, self.SPIDERMAN_BLACK, -1)
            # Colored fill
            cv2.circle(frame, (cx, cy), radius, color, -1)
            # White highlight
            cv2.circle(frame, (cx - 2, cy - 2), radius // 3, self.SPIDERMAN_WHITE, -1)
            
            # Landmark number
            if show_numbers:
                cv2.putText(frame, str(idx), (cx + 10, cy - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.SPIDERMAN_WHITE, 1)
        
        return frame
    
    def draw_spiderman_hand_filled(self, frame: np.ndarray, landmarks: list) -> np.ndarray:
        """
        Draw hand as a Spider-Man glove style.
        
        - Thick red connectors with glow (the glove)
        - No landmark dots/rings
        - Glow outline for visual pop
        
        NOTE: This is purely visual - does NOT affect gesture detection.
        Detection uses raw landmark coordinates before any rendering.
        """
        if not landmarks:
            return frame
        
        h, w = frame.shape[:2]
        
        # Get landmark coordinates
        pts = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in range(21)]
        
        # Fill palm polygon (1, 5, 9, 13, 17, 0)
        palm_indices = [1, 5, 9, 13, 17, 0]
        palm_pts = np.array([pts[i] for i in palm_indices], dtype=np.int32)
        cv2.fillPoly(frame, [palm_pts], self.SPIDERMAN_RED)
        
        # Draw connectors - single red color only
        for start_idx, end_idx in self.HAND_CONNECTIONS:
            start_pt = pts[start_idx]
            end_pt = pts[end_idx]
            
            # Red glove (single color, thick)
            cv2.line(frame, start_pt, end_pt, self.SPIDERMAN_RED, 20)
        
        return frame
