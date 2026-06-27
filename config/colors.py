"""
Color Constants

All color definitions used throughout the application.
Colors are provided in both hex (for display) and BGR (for OpenCV).
"""

from typing import Dict, Tuple, List

# === GLOVE COLORS ===
GLOVE_RED_HEX = "#CC0000"
GLOVE_RED_BGR = (0, 0, 204)  # BGR for OpenCV
GLOVE_CONNECTOR_HEX = "#CC0000"

# === WEB COLORS ===
WEB_WHITE_HEX = "#FFFFFF"
WEB_WHITE_BGR = (255, 255, 255)
WEB_GLOW_RGBA = "rgba(150, 150, 255, 0.5)"

# === SYMBIOTE COLORS ===
SYMBIOTE_DARK_HEX = "#1a0a2e"
SYMBIOTE_GLOW_START = "rgba(50, 0, 80, 0.8)"
SYMBIOTE_GLOW_END = "rgba(20, 0, 40, 0)"

# === UI COLORS ===
THWIP_YELLOW_HEX = "#FFFF00"
SCORE_GREEN_HEX = "#00FF00"
WARNING_RED_HEX = "#FF4444"

# === DR. STRANGE FIRE COLORS (BGR) ===
# Gradient from dark red/orange to bright yellow/white
FIRE_COLORS: List[Tuple[int, int, int]] = [
    (0, 0, 139),      # Dark red
    (0, 69, 255),     # Orange-red
    (0, 140, 255),    # Orange
    (0, 200, 255),    # Light orange
    (0, 255, 255),    # Yellow
    (180, 255, 255),  # Bright yellow/white
]

# === LEGACY COLORS DICT (for backward compatibility) ===
COLORS: Dict[str, any] = {
    # Glove colors
    "glove_red": GLOVE_RED_HEX,
    "glove_red_rgb": GLOVE_RED_BGR,
    "glove_connector": GLOVE_CONNECTOR_HEX,
    
    # Web colors
    "web_white": WEB_WHITE_HEX,
    "web_white_rgb": WEB_WHITE_BGR,
    "web_glow": WEB_GLOW_RGBA,
    
    # Symbiote colors
    "symbiote_dark": SYMBIOTE_DARK_HEX,
    "symbiote_glow_start": SYMBIOTE_GLOW_START,
    "symbiote_glow_end": SYMBIOTE_GLOW_END,
    
    # UI colors
    "thwip_yellow": THWIP_YELLOW_HEX,
    "score_green": SCORE_GREEN_HEX,
    "warning_red": WARNING_RED_HEX,
}

__all__ = [
    # Individual color constants
    'GLOVE_RED_HEX', 'GLOVE_RED_BGR', 'GLOVE_CONNECTOR_HEX',
    'WEB_WHITE_HEX', 'WEB_WHITE_BGR', 'WEB_GLOW_RGBA',
    'SYMBIOTE_DARK_HEX', 'SYMBIOTE_GLOW_START', 'SYMBIOTE_GLOW_END',
    'THWIP_YELLOW_HEX', 'SCORE_GREEN_HEX', 'WARNING_RED_HEX',
    'FIRE_COLORS',
    # Legacy dict
    'COLORS',
]
