"""
Game Mechanics Module

All game-related systems organized into submodules:
- enemies: Symbiote balls and infection system
- dr_strange: Portal rings and warp effects  
- screens: Game screens and HUD
- core: Main game loop
"""

from .enemies import SymbioteBall, SymbioteManager, InfectionSource, InfectionManager
from .dr_strange import (
    DrStrangeRing, 
    DrStrangeRingConfig, 
    DrStrangeRingManager,
    warp_portal_effect,
    apply_warp_to_completed_portals,
)
from .screens import GameScreenManager, GameStats, TrainingMode

__all__ = [
    # Enemies
    'SymbioteBall',
    'SymbioteManager',
    'InfectionSource',
    'InfectionManager',
    # Dr. Strange
    'DrStrangeRing',
    'DrStrangeRingConfig',
    'DrStrangeRingManager',
    'warp_portal_effect',
    'apply_warp_to_completed_portals',
    # Screens
    'GameScreenManager',
    'GameStats',
    'TrainingMode',
]
