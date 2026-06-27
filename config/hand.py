"""
Hand Landmark Constants

MediaPipe hand landmark connections and indices.
"""

from typing import List, Tuple

# Hand landmark connections (MediaPipe format)
HAND_CONNECTIONS: List[Tuple[int, int]] = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index finger
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle finger
    (0, 9), (9, 10), (10, 11), (11, 12),
    # Ring finger
    (0, 13), (13, 14), (14, 15), (15, 16),
    # Pinky finger
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm connections
    (5, 9), (9, 13), (13, 17)
]

# Palm polygon vertex indices (for filled palm rendering)
PALM_POLYGON: List[int] = [0, 1, 5, 9, 13, 17]

# Fingertip landmark indices
FINGERTIP_INDICES: List[int] = [4, 8, 12, 16, 20]

# Finger MCP (knuckle) indices
FINGER_MCP_INDICES: List[int] = [5, 9, 13, 17]

__all__ = [
    'HAND_CONNECTIONS',
    'PALM_POLYGON',
    'FINGERTIP_INDICES',
    'FINGER_MCP_INDICES',
]
