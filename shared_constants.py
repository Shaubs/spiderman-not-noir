"""
Shared constants between Python backend and JavaScript frontend.
Run this file directly to export to JSON for frontend.

Usage:
    python shared_constants.py
"""

# Hand landmark connections (MediaPipe format)
HAND_CONNECTIONS = [
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
PALM_POLYGON = [0, 1, 5, 9, 13, 17]

# Fingertip landmark indices
FINGERTIP_INDICES = [4, 8, 12, 16, 20]

# Finger MCP (knuckle) indices
FINGER_MCP_INDICES = [5, 9, 13, 17]

# Colors used in rendering
COLORS = {
    # Glove colors
    "glove_red": "#CC0000",
    "glove_red_rgb": (0, 0, 204),  # BGR for OpenCV
    "glove_connector": "#CC0000",
    
    # Web colors
    "web_white": "#FFFFFF",
    "web_white_rgb": (255, 255, 255),
    "web_glow": "rgba(150, 150, 255, 0.5)",
    
    # Symbiote colors
    "symbiote_dark": "#1a0a2e",
    "symbiote_glow_start": "rgba(50, 0, 80, 0.8)",
    "symbiote_glow_end": "rgba(20, 0, 40, 0)",
    
    # UI colors
    "thwip_yellow": "#FFFF00",
    "score_green": "#00FF00",
    "warning_red": "#FF4444",
}

# Web shot configuration
WEB_SPREAD_ANGLE = 10  # degrees between web lines
WEB_LINE_COUNT = 3
WEB_LINE_THICKNESS = 3
WEB_GLOW_THICKNESS = 8

# Hand rendering configuration
HAND_CONNECTOR_THICKNESS = 20
HAND_LANDMARK_RADIUS = 5

# Symbiote configuration
SYMBIOTE_GLOW_RADIUS_OFFSET = 10

# Frame dimensions (default)
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Game states
GAME_STATES = ["LOOKING", "DETECTED", "TRIGGERED", "COOLDOWN"]


def export_to_json():
    """Export constants to JSON for frontend consumption."""
    import json
    from pathlib import Path
    
    # Filter out RGB values (OpenCV-specific)
    colors_for_js = {
        k: v for k, v in COLORS.items() 
        if not k.endswith("_rgb")
    }
    
    data = {
        "HAND_CONNECTIONS": HAND_CONNECTIONS,
        "PALM_POLYGON": PALM_POLYGON,
        "FINGERTIP_INDICES": FINGERTIP_INDICES,
        "FINGER_MCP_INDICES": FINGER_MCP_INDICES,
        "COLORS": colors_for_js,
        "WEB_SPREAD_ANGLE": WEB_SPREAD_ANGLE,
        "WEB_LINE_COUNT": WEB_LINE_COUNT,
        "WEB_LINE_THICKNESS": WEB_LINE_THICKNESS,
        "WEB_GLOW_THICKNESS": WEB_GLOW_THICKNESS,
        "HAND_CONNECTOR_THICKNESS": HAND_CONNECTOR_THICKNESS,
        "HAND_LANDMARK_RADIUS": HAND_LANDMARK_RADIUS,
        "SYMBIOTE_GLOW_RADIUS_OFFSET": SYMBIOTE_GLOW_RADIUS_OFFSET,
        "FRAME_WIDTH": FRAME_WIDTH,
        "FRAME_HEIGHT": FRAME_HEIGHT,
        "GAME_STATES": GAME_STATES,
    }
    
    # Ensure output directory exists
    output_dir = Path(__file__).parent / "streaming_poc" / "frontend" / "src" / "lib"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "constants.json"
    output_file.write_text(json.dumps(data, indent=2))
    print(f"✅ Exported constants to {output_file}")
    
    return data


if __name__ == "__main__":
    export_to_json()
