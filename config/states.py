"""
Game State Constants

Enums and state definitions for game flow.
"""

from typing import List

# Game states (legacy list format)
GAME_STATES: List[str] = ["LOOKING", "DETECTED", "TRIGGERED", "COOLDOWN"]

__all__ = [
    'GAME_STATES',
]
