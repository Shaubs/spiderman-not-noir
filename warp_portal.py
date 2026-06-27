"""
Warp Portal Effect

Creates a swirling/warping effect for pixels inside a circular region,
simulating a Dr. Strange style portal effect.
"""

import cv2
import numpy as np
import math
from typing import Tuple, Optional


def warp_portal_effect(
    frame: np.ndarray,
    center_x: int,
    center_y: int,
    radius: int,
    rotation_angle: float = 0.0,
    warp_strength: float = 0.5,
    spiral_factor: float = 2.0
) -> np.ndarray:
    """
    Apply a swirling warp effect to pixels inside a circular region.
    
    Args:
        frame: Input BGR image
        center_x: X coordinate of portal center
        center_y: Y coordinate of portal center
        radius: Radius of the portal effect
        rotation_angle: Current rotation angle (for animation)
        warp_strength: How strong the warp effect is (0.0 to 1.0)
        spiral_factor: How many spiral turns (higher = more twisted)
    
    Returns:
        Frame with warp effect applied to the circular region
    """
    if radius <= 0:
        return frame
    
    h, w = frame.shape[:2]
    
    # Create output frame (copy of input)
    output = frame.copy()
    
    # Define bounding box for the effect (optimization - don't process entire frame)
    x_min = max(0, center_x - radius - 10)
    x_max = min(w, center_x + radius + 10)
    y_min = max(0, center_y - radius - 10)
    y_max = min(h, center_y + radius + 10)
    
    # Create coordinate grids for the region
    y_coords, x_coords = np.mgrid[y_min:y_max, x_min:x_max]
    
    # Calculate distance from center for each pixel
    dx = x_coords - center_x
    dy = y_coords - center_y
    distance = np.sqrt(dx**2 + dy**2)
    
    # Create mask for pixels inside the portal
    mask = distance <= radius
    
    if not np.any(mask):
        return frame
    
    # Calculate angle from center for each pixel
    angle = np.arctan2(dy, dx)
    
    # Normalized distance (0 at center, 1 at edge)
    norm_distance = np.clip(distance / radius, 0, 1)
    
    # Calculate warp amount - stronger near center, weaker at edges
    # Use smooth falloff for natural look
    warp_amount = (1 - norm_distance**2) * warp_strength
    
    # Calculate spiral twist - pixels rotate based on distance from center
    # Inner pixels rotate more than outer pixels
    twist = (1 - norm_distance) * spiral_factor * math.pi * warp_amount
    
    # Add animation rotation
    new_angle = angle + twist + rotation_angle * warp_amount
    
    # Calculate new distance with slight pull towards center
    pull_factor = 1 - warp_amount * 0.3  # Slight inward pull
    new_distance = distance * pull_factor
    
    # Calculate source coordinates (where to sample from)
    src_x = (center_x + new_distance * np.cos(new_angle)).astype(np.float32)
    src_y = (center_y + new_distance * np.sin(new_angle)).astype(np.float32)
    
    # Clamp to valid coordinates
    src_x = np.clip(src_x, 0, w - 1)
    src_y = np.clip(src_y, 0, h - 1)
    
    # Apply the warp only to masked pixels
    for local_y in range(y_max - y_min):
        for local_x in range(x_max - x_min):
            if mask[local_y, local_x]:
                sy = int(src_y[local_y, local_x])
                sx = int(src_x[local_y, local_x])
                output[y_min + local_y, x_min + local_x] = frame[sy, sx]
    
    return output


def warp_portal_effect_fast(
    frame: np.ndarray,
    center_x: int,
    center_y: int,
    radius: int,
    rotation_angle: float = 0.0,
    warp_strength: float = 0.5,
    spiral_factor: float = 2.0
) -> np.ndarray:
    """
    Faster version of warp effect using cv2.remap.
    
    Args:
        frame: Input BGR image
        center_x: X coordinate of portal center
        center_y: Y coordinate of portal center
        radius: Radius of the portal effect
        rotation_angle: Current rotation angle (for animation)
        warp_strength: How strong the warp effect is (0.0 to 1.0)
        spiral_factor: How many spiral turns (higher = more twisted)
    
    Returns:
        Frame with warp effect applied to the circular region
    """
    if radius <= 0:
        return frame
    
    h, w = frame.shape[:2]
    
    # Define bounding box
    x_min = max(0, center_x - radius - 5)
    x_max = min(w, center_x + radius + 5)
    y_min = max(0, center_y - radius - 5)
    y_max = min(h, center_y + radius + 5)
    
    region_w = x_max - x_min
    region_h = y_max - y_min
    
    if region_w <= 0 or region_h <= 0:
        return frame
    
    # Create coordinate grids
    y_coords, x_coords = np.mgrid[0:region_h, 0:region_w]
    x_coords = x_coords.astype(np.float32) + x_min
    y_coords = y_coords.astype(np.float32) + y_min
    
    # Calculate distance and angle from center
    dx = x_coords - center_x
    dy = y_coords - center_y
    distance = np.sqrt(dx**2 + dy**2)
    angle = np.arctan2(dy, dx)
    
    # Normalized distance
    norm_distance = np.clip(distance / radius, 0, 1)
    
    # Mask for inside portal
    inside_mask = distance <= radius
    
    # Calculate warp for pixels inside
    warp_amount = np.where(inside_mask, (1 - norm_distance**2) * warp_strength, 0)
    
    # Spiral twist
    twist = (1 - norm_distance) * spiral_factor * math.pi * warp_amount
    
    # New angle with animation
    new_angle = angle + twist + rotation_angle * warp_amount
    
    # Pull factor
    pull_factor = 1 - warp_amount * 0.3
    new_distance = distance * pull_factor
    
    # Source coordinates
    map_x = np.where(inside_mask, 
                     center_x + new_distance * np.cos(new_angle),
                     x_coords).astype(np.float32)
    map_y = np.where(inside_mask,
                     center_y + new_distance * np.sin(new_angle),
                     y_coords).astype(np.float32)
    
    # Clamp
    map_x = np.clip(map_x, 0, w - 1)
    map_y = np.clip(map_y, 0, h - 1)
    
    # Extract and warp the region
    region = frame[y_min:y_max, x_min:x_max]
    
    # Adjust map coordinates to be relative to region
    map_x_local = map_x - x_min
    map_y_local = map_y - y_min
    
    # Clamp local coordinates
    map_x_local = np.clip(map_x_local, 0, region_w - 1)
    map_y_local = np.clip(map_y_local, 0, region_h - 1)
    
    # Apply remap
    warped_region = cv2.remap(region, map_x_local, map_y_local, 
                               cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    
    # Blend warped region back
    output = frame.copy()
    
    # Create smooth blend mask for edge feathering
    blend_mask = np.zeros((region_h, region_w), dtype=np.float32)
    for y in range(region_h):
        for x in range(region_w):
            d = math.sqrt((x + x_min - center_x)**2 + (y + y_min - center_y)**2)
            if d < radius:
                # Smooth falloff at edges
                edge_factor = 1 - (d / radius)**4
                blend_mask[y, x] = edge_factor
    
    # Apply blend
    blend_mask_3ch = np.stack([blend_mask] * 3, axis=-1)
    output[y_min:y_max, x_min:x_max] = (
        warped_region * blend_mask_3ch + 
        region * (1 - blend_mask_3ch)
    ).astype(np.uint8)
    
    return output


def apply_warp_to_completed_portals(
    frame: np.ndarray,
    portals: list,
    rotation_angle: float,
    warp_strength: float = 0.6,
    spiral_factor: float = 3.0
) -> np.ndarray:
    """
    Apply warp effect to all completed portal circles.
    
    Args:
        frame: Input BGR image
        portals: List of (center_x, center_y, radius, creation_time) tuples
        rotation_angle: Current animation rotation angle
        warp_strength: Warp intensity (0.0 to 1.0)
        spiral_factor: Number of spiral turns
    
    Returns:
        Frame with warp effects applied to all portals
    """
    output = frame
    
    for portal in portals:
        center_x, center_y, radius, creation_time = portal
        
        # Apply warp effect to this portal
        output = warp_portal_effect_fast(
            output,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            rotation_angle=rotation_angle,
            warp_strength=warp_strength,
            spiral_factor=spiral_factor
        )
    
    return output
