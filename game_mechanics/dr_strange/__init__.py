"""
Dr. Strange Portal System

Magical portal rings and warp effects.
"""

from .ring import DrStrangeRing, DrStrangeRingConfig, DrStrangeRingManager
from .warp_portal import warp_portal_effect, apply_warp_to_completed_portals

__all__ = [
    'DrStrangeRing',
    'DrStrangeRingConfig',
    'DrStrangeRingManager',
    'warp_portal_effect',
    'apply_warp_to_completed_portals',
]
