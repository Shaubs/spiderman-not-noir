"""
Unified Configuration Module

Centralizes all game configuration in one place.
Import from here for all config needs.

Example:
    from config import FRAME_WIDTH, FRAME_HEIGHT, FIRE_COLORS
    from config import GameConfig, ACTIVE_CONFIG
    from config import SymbioteConfig, ACTIVE_SYMBIOTE_CONFIG
"""

# === COLORS ===
from .colors import (
    COLORS,
    FIRE_COLORS,
    GLOVE_RED_HEX, GLOVE_RED_BGR, GLOVE_CONNECTOR_HEX,
    WEB_WHITE_HEX, WEB_WHITE_BGR, WEB_GLOW_RGBA,
    SYMBIOTE_DARK_HEX, SYMBIOTE_GLOW_START, SYMBIOTE_GLOW_END,
    THWIP_YELLOW_HEX, SCORE_GREEN_HEX, WARNING_RED_HEX,
)

# === DIMENSIONS ===
from .dimensions import (
    FRAME_WIDTH, FRAME_HEIGHT,
    HAND_CONNECTOR_THICKNESS, HAND_LANDMARK_RADIUS,
    WEB_LINE_THICKNESS, WEB_GLOW_THICKNESS,
    SYMBIOTE_GLOW_RADIUS_OFFSET,
)

# === HAND LANDMARKS ===
from .hand import (
    HAND_CONNECTIONS,
    PALM_POLYGON,
    FINGERTIP_INDICES,
    FINGER_MCP_INDICES,
)

# === WEB SHOT ===
from .web import (
    WEB_SPREAD_ANGLE,
    WEB_LINE_COUNT,
)

# === GAME STATES ===
from .states import GAME_STATES

# === GAME CONFIG ===
from .game import (
    GameConfig,
    FAST_CONFIG, NORMAL_CONFIG, SLOW_CONFIG,
    ACTIVE_CONFIG,
)

# === SYMBIOTE CONFIG ===
from .symbiote import (
    SymbioteConfig,
    EASY_SYMBIOTE, NORMAL_SYMBIOTE, HARD_SYMBIOTE, NIGHTMARE_SYMBIOTE,
    ACTIVE_SYMBIOTE_CONFIG,
)

# === SCORE CONFIG ===
from .score import (
    ScoreConfig,
    GameScore,
    Scoreboard,
    ACTIVE_SCORE_CONFIG,
)

# === DEPTH CONFIG ===
from .depth import (
    DepthConfig,
    DEFAULT_DEPTH, SUBTLE_DEPTH, DRAMATIC_DEPTH, STATIC_DEPTH,
    ACTIVE_DEPTH_CONFIG,
)


__all__ = [
    # Colors
    'COLORS', 'FIRE_COLORS',
    'GLOVE_RED_HEX', 'GLOVE_RED_BGR', 'GLOVE_CONNECTOR_HEX',
    'WEB_WHITE_HEX', 'WEB_WHITE_BGR', 'WEB_GLOW_RGBA',
    'SYMBIOTE_DARK_HEX', 'SYMBIOTE_GLOW_START', 'SYMBIOTE_GLOW_END',
    'THWIP_YELLOW_HEX', 'SCORE_GREEN_HEX', 'WARNING_RED_HEX',
    
    # Dimensions
    'FRAME_WIDTH', 'FRAME_HEIGHT',
    'HAND_CONNECTOR_THICKNESS', 'HAND_LANDMARK_RADIUS',
    'WEB_LINE_THICKNESS', 'WEB_GLOW_THICKNESS',
    'SYMBIOTE_GLOW_RADIUS_OFFSET',
    
    # Hand landmarks
    'HAND_CONNECTIONS', 'PALM_POLYGON',
    'FINGERTIP_INDICES', 'FINGER_MCP_INDICES',
    
    # Web shot
    'WEB_SPREAD_ANGLE', 'WEB_LINE_COUNT',
    
    # States
    'GAME_STATES',
    
    # Game config
    'GameConfig',
    'FAST_CONFIG', 'NORMAL_CONFIG', 'SLOW_CONFIG',
    'ACTIVE_CONFIG',
    
    # Symbiote config
    'SymbioteConfig',
    'EASY_SYMBIOTE', 'NORMAL_SYMBIOTE', 'HARD_SYMBIOTE', 'NIGHTMARE_SYMBIOTE',
    'ACTIVE_SYMBIOTE_CONFIG',
    
    # Score config
    'ScoreConfig', 'GameScore', 'Scoreboard',
    'ACTIVE_SCORE_CONFIG',
    
    # Depth config
    'DepthConfig',
    'DEFAULT_DEPTH', 'SUBTLE_DEPTH', 'DRAMATIC_DEPTH', 'STATIC_DEPTH',
    'ACTIVE_DEPTH_CONFIG',
]
